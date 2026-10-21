"""Independent source behavior for temporary combat barriers."""

import json
from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from asterion.domain.combat import (
    Action,
    Combat,
    DotState,
    Fighter,
    _advance_barrier_sources,
    _apply_barrier,
    _deal_combat_damage,
    _end_turn,
    _perform,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import PlayerCombatantSpec, create_player_versus_player_combat
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
COMBAT_ID = UUID("6a0ce571-c7a6-4d27-a3da-80763b2bdb8f")


def _fighter(fighter_id: str, *, hp: int = 500) -> Fighter:
    return Fighter(
        id=fighter_id,
        name=fighter_id,
        level=20,
        stats=CombatStats(D(hp), D(100), D(0), D(20), crit=D(0)),
        hp=D(hp),
        side="player" if fighter_id == "player" else "enemy",
    )


def _combat(*, hp: int = 500, pvp: bool = False) -> Combat:
    return Combat(
        COMBAT_ID,
        CURRENT_COMBAT_RULESET,
        {"player": _fighter("player", hp=hp), "enemy": _fighter("enemy")},
        {"attack": Action("attack", "Ataque", D(1))},
        {},
        (),
        pvp_mode=pvp,
    )


def _grant(
    combat: Combat,
    *,
    applier: str,
    effect: str,
    value: int,
    duration: int = 2,
    target_key: str = "player",
    opportunity: int = 0,
) -> Decimal:
    return _apply_barrier(
        combat.fighters[target_key],
        applier_id=applier,
        effect_definition_id=effect,
        value=value,
        duration=duration,
        applied_opportunity=opportunity,
        round_number=combat.round,
    )


def test_distinct_sources_coexist_and_absorb_fifo_before_real_hp_damage():
    state = _combat()
    player = state.fighters["player"]
    _grant(state, applier="a", effect="shield.a", value=50)
    _grant(state, applier="b", effect="shield.b", value=35)

    assert player.barrier == D(85)
    assert [layer.remaining for layer in player.barriers] == [2, 2]

    absorbed_sources: list[str] = []
    hp_damage, absorbed = _deal_combat_damage(
        state, "player", 70, source_key="enemy", absorbed_sources=absorbed_sources
    )
    assert (hp_damage, absorbed) == (D(0), D(70))
    assert absorbed_sources == ["a:shield.a", "b:shield.b"]
    assert [(layer.source_label, layer.value) for layer in player.barriers] == [
        ("b:shield.b", D(15))
    ]

    hp_damage, absorbed = _deal_combat_damage(state, "player", 25, source_key="enemy")
    assert (hp_damage, absorbed) == (D(10), D(15))
    assert player.hp == D(490)
    assert player.barrier == 0


def test_source_identity_is_applier_and_effect_and_same_source_replaces():
    state = _combat()
    player = state.fighters["player"]
    _grant(state, applier="a", effect="x", value=50, duration=4)
    _grant(state, applier="b", effect="x", value=20, duration=3)
    _grant(state, applier="a", effect="y", value=15, duration=1)
    assert player.barrier == D(85)

    _grant(state, applier="a", effect="x", value=35, duration=2)
    assert [(layer.identity, layer.value, layer.remaining) for layer in player.barriers] == [
        (("a", "x"), D(35), 2),
        (("b", "x"), D(20), 3),
        (("a", "y"), D(15), 1),
    ]
    assert player.barrier == D(70)


def test_barrier_durations_expire_independently_and_refresh_only_its_source():
    state = _combat()
    player = state.fighters["player"]
    _grant(state, applier="a", effect="x", value=50, duration=1)
    _grant(state, applier="b", effect="y", value=35, duration=3)

    player.opportunity = 1
    expired = _advance_barrier_sources(player)
    assert [layer.source_label for layer in expired] == ["a:x"]
    assert [(layer.source_label, layer.remaining) for layer in player.barriers] == [
        ("b:y", 2)
    ]
    _grant(state, applier="b", effect="y", value=25, duration=4, opportunity=1)
    _grant(state, applier="c", effect="z", value=10, duration=2, opportunity=1)
    assert [(layer.source_label, layer.remaining) for layer in player.barriers] == [
        ("b:y", 4),
        ("c:z", 2),
    ]

    _grant(state, applier="a", effect="long", value=12, duration=3, opportunity=1)
    _grant(state, applier="d", effect="short", value=8, duration=1, opportunity=1)
    player.opportunity = 2
    expired = _advance_barrier_sources(player)
    assert [layer.source_label for layer in expired] == ["d:short"]
    assert any(layer.source_label == "a:long" and layer.remaining == 2 for layer in player.barriers)


def test_pvp_uses_aggregate_35_percent_cap_and_trims_on_max_hp_reduction():
    state = _combat(hp=100, pvp=True)
    player = state.fighters["player"]
    assert _grant(state, applier="a", effect="x", value=30) == D(30)
    assert _grant(state, applier="b", effect="y", value=20) == D(5)
    assert player.barrier == D(35)

    # A maximum-HP reduction cuts newest sources first, preserving older FIFO priority.
    player.stats = replace(player.stats, hp=D(80))
    assert player.barrier == D(28)
    assert [(layer.source_label, layer.value) for layer in player.barriers] == [
        ("a:x", D(28))
    ]


def test_pve_has_no_new_universal_barrier_cap():
    state = _combat(hp=100)
    _grant(state, applier="a", effect="x", value=50)
    _grant(state, applier="b", effect="y", value=35)
    assert state.fighters["player"].barrier == D(85)
    assert state.fighters["player"].barrier_cap_fraction is None


def test_pvp_exhaustion_reduces_only_new_grant():
    state = _combat(hp=100, pvp=True)
    player = state.fighters["player"]
    _grant(state, applier="a", effect="old", value=20)
    state.round = 20
    assert _grant(state, applier="b", effect="new", value=100) == D(15)
    assert [(layer.source_label, layer.value) for layer in player.barriers] == [
        ("a:old", D(20)),
        ("b:new", D(15)),
    ]
    state.round = 25
    assert _grant(state, applier="c", effect="later", value=100) == 0
    assert player.barrier == D(35)


def test_dot_tick_absorbs_multiple_barrier_sources_and_persists_event_details():
    state = start_combat(_combat())
    player = state.fighters["player"]
    _grant(state, applier="a", effect="x", value=50)
    _grant(state, applier="b", effect="y", value=35)
    state.dot_states[player.id] = [
        DotState("poison", 1, 2, D(100), state.fighters["enemy"].id)
    ]

    _end_turn(state)

    dot_event = next(event for event in state.mechanic_events if event.action == "dot:poison:tick")
    assert dot_event.barrier_absorbed == D(12)
    assert dot_event.damage == 0
    assert dot_event.barrier_total_after == D(73)
    assert dot_event.barrier_absorbed_sources == ("a:x",)
    assert player.hp == D(500)
    assert player.barrier == D(73)


def test_barriers_absorb_each_multihit_and_aoe_target_without_shared_layers():
    state = _combat()
    state.fighters["enemy2"] = _fighter("enemy2")
    state.player_actions["multi"] = Action(
        "test.multi", "Multi", D("0.50"), hit_count=2
    )
    state.player_actions["sweep"] = Action(
        "test.sweep", "Sweep", D("0.50"), target_mode="all_opponents"
    )
    for enemy_key in ("enemy", "enemy2"):
        _grant(state, applier="shield-a", effect=f"{enemy_key}.a", value=20, target_key=enemy_key)
        _grant(state, applier="shield-b", effect=f"{enemy_key}.b", value=20, target_key=enemy_key)

    assert _perform(state, "player", "multi", target_id="enemy")
    multihit_events = [event for event in state.events if event.action == "multi"]
    assert len(multihit_events) == 2
    assert len({event.action_instance_id for event in multihit_events}) == 1
    assert sum((event.barrier_absorbed for event in multihit_events), D(0)) == D(40)
    assert state.fighters["enemy"].barrier == 0
    assert state.fighters["enemy2"].barrier == D(40)

    assert _perform(state, "player", "sweep")
    aoe_events = [event for event in state.events if event.action == "sweep"]
    assert {event.target for event in aoe_events} == {"enemy", "enemy2"}
    assert state.fighters["enemy2"].barrier < D(40)
    assert state.fighters["enemy"].barrier == 0


def test_barrier_source_keeps_the_actual_applier_when_applied_to_an_ally():
    state = _combat()
    _grant(
        state,
        applier="support-character",
        effect="class_art.luminar.luz_restauradora",
        value=35,
        target_key="enemy",
    )
    ally = state.fighters["enemy"]
    assert ally.barrier == D(35)
    assert ally.barriers[0].identity == (
        "support-character",
        "class_art.luminar.luz_restauradora",
    )


def test_enemy_vampirism_counts_only_direct_damage_that_reaches_hp():
    fully_absorbed = _combat()
    attacker = fully_absorbed.fighters["enemy"]
    attacker.hp = D(400)
    fully_absorbed.enemy_actions["drain"] = Action(
        "enemy.drain",
        "Drenagem",
        D(1),
        vampirism_fraction=D("0.50"),
    )
    _grant(fully_absorbed, applier="caster", effect="large", value=1000)
    assert _perform(fully_absorbed, "enemy", "drain", target_id="player")
    assert attacker.hp == D(400)
    absorbed_event = next(
        event for event in fully_absorbed.events if event.action == "drain"
    )
    assert absorbed_event.effective_damage == 0

    partially_absorbed = _combat()
    attacker = partially_absorbed.fighters["enemy"]
    attacker.hp = D(400)
    partially_absorbed.enemy_actions["drain"] = Action(
        "enemy.drain",
        "Drenagem",
        D(1),
        vampirism_fraction=D("0.50"),
    )
    _grant(partially_absorbed, applier="caster", effect="small", value=10)
    assert _perform(partially_absorbed, "enemy", "drain", target_id="player")
    event = next(event for event in partially_absorbed.events if event.action == "drain")
    expected_healing = (event.effective_damage * D("0.50")).to_integral_value(
        rounding="ROUND_FLOOR"
    )
    assert event.effective_damage > 0
    assert attacker.hp == D(400) + expected_healing
    assert event.healed == expected_healing


def test_codec_round_trip_preserves_layers_and_legacy_scalar_snapshots():
    state = _combat()
    _grant(state, applier="a", effect="x", value=50, duration=1)
    _grant(state, applier="b", effect="y", value=35, duration=3)
    encoded = encode(state)
    restored = decode(encoded, state.id, state.ruleset, state.version)
    player = restored.fighters["player"]
    assert [(layer.identity, layer.value, layer.remaining) for layer in player.barriers] == [
        (("a", "x"), D(50), 1),
        (("b", "y"), D(35), 3),
    ]
    assert player.barrier == D(85)

    legacy = json.loads(json.dumps(encoded))
    legacy_fighter = legacy["fighters"]["player"]
    legacy_fighter.pop("barrier_layers")
    legacy_fighter["barrier"] = "47"
    legacy_fighter["barrier_remaining"] = 2
    legacy_fighter["barrier_applied_opportunity"] = 4
    legacy_fighter["barrier_source"] = "old:scalar-source"
    legacy_fighter["barrier_debuff_magnitude_reduction"] = "0.10"
    legacy_restored = decode(legacy, state.id, state.ruleset, state.version)
    legacy_player = legacy_restored.fighters["player"]
    assert legacy_player.barrier == D(47)
    assert len(legacy_player.barriers) == 1
    assert legacy_player.barriers[0].legacy is True
    assert legacy_player.barriers[0].identity is None
    assert legacy_player.barriers[0].remaining == 2
    assert legacy_player.barriers[0].applied_opportunity == 4
    assert legacy_player.barriers[0].source_label == "old:scalar-source"
    assert legacy_player.barriers[0].debuff_magnitude_reduction == D("0.10")


def test_player_versus_player_combat_marks_pvp_cap_mode():
    roster = PlayerCombatantSpec(
        "left",
        "left-character",
        "Left",
        "sentinela",
        "remanescente",
        5,
        D(100),
        EquipmentConfigurationSnapshot(0),
        (),
    )
    opponent = replace(roster, fighter_key="right", character_id="right-character")
    state = create_player_versus_player_combat(uuid4(), (roster,), (opponent,))
    assert state.pvp_mode is True
    assert all(fighter.barrier_cap_fraction == D("0.35") for fighter in state.fighters.values())


@pytest.mark.asyncio
async def test_postgres_jsonb_snapshot_preserves_barrier_layers(database):
    state = _combat()
    _grant(state, applier="caster-a", effect="spell-a", value=50, duration=1)
    _grant(state, applier="caster-b", effect="spell-b", value=35, duration=3)
    payload = json.dumps(encode(state))

    async with database[0].begin() as connection:
        revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
        persisted = await connection.scalar(
            text("SELECT CAST(:snapshot AS jsonb)"), {"snapshot": payload}
        )

    assert revision == "20261010_0027"
    restored = decode(persisted, state.id, state.ruleset, state.version)
    assert restored.fighters["player"].barrier == D(85)
    assert [layer.remaining for layer in restored.fighters["player"].barriers] == [1, 3]
