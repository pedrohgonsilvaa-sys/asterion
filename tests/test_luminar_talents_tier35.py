from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4

import pytest

from asterion.domain.arts import GUARDIAO_ART_IDS, LUMINAR_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    act,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    talent_points_at_level,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

VEREDITO_ARDENTE = "talent.luminar.veredito_ardente"
CURA_PRUDENTE = "talent.luminar.cura_prudente"
CICLO_LUMINOSO = "talent.luminar.ciclo_luminoso"
SOLAR = LUMINAR_ART_IDS["explosao_solar"]
LUZ = LUMINAR_ART_IDS["luz_restauradora"]
RENOVACAO = LUMINAR_ART_IDS["renovacao"]
AURORA_GUARDIA = GUARDIAO_ART_IDS["aurora_guardia"]
VEREDITO = "path_art.luminar.inquisidor.veredito"


def _fighter(
    fighter_id: str,
    *,
    name: str,
    hp: D,
    max_hp: D,
    side: str,
    character_class: str = "",
    takes_turn: bool = False,
) -> Fighter:
    return Fighter(
        fighter_id,
        name,
        35,
        CombatStats(max_hp, D(100), D(100), D(100)),
        hp,
        character_class=character_class,
        side=side,
        takes_turn=takes_turn,
        required_for_victory=False,
    )


def _combat(
    *,
    path: str | None = None,
    arts: tuple[str, ...] = (SOLAR,),
    talents: tuple[str, ...] = (),
    hp: D = D(1000),
    enemy_count: int = 3,
    ally_hps: tuple[D, ...] = (),
) -> Combat:
    stats = resolve_combat_stats("luminar", 35, "remanescente", selected_path=path)
    player_state = PROFILE.create(
        uuid4(), "Luminar", "luminar", "remanescente", stats.hp
    )
    player_state.tutorial = None
    player_state.ruleset = CURRENT_COMBAT_RULESET
    actor = player_state.fighters["player"]
    actor.level = 35
    actor.character_class = "luminar"
    actor.selected_path = path
    actor.talent_ids = talents
    actor.side = "player"
    actor.takes_turn = True
    actor.stats = replace(
        stats,
        hp=D(1000),
        attack=D(100),
        defense=D(100),
        agility=D(100),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    actor.hp = hp

    fighters = {"player": actor}
    for index, ally_hp in enumerate(ally_hps):
        key = f"ally-{index}"
        fighters[key] = _fighter(
            key,
            name=f"Ally {index}",
            hp=ally_hp,
            max_hp=D(1000),
            side="player",
        )
    for index in range(enemy_count):
        key = f"enemy-{index}"
        fighters[key] = _fighter(
            key,
            name=key,
            hp=D(10000),
            max_hp=D(10000),
            side="enemy",
        )

    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        fighters,
        class_player_actions("luminar", arts, path),
        {"wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")},
        ("wait",),
    )
    if ally_hps:
        state.party_mode = True
        state.manual_sides = ("player",)
    return start_combat(state)


def _events(state: Combat, action_id: str):
    actor_id = state.fighters["player"].id
    return [
        event
        for event in state.events
        if event.actor_entity_id == actor_id and event.action == action_id
    ]


def _set_state(state: Combat, kind: str, remaining: int = 2) -> None:
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": kind,
        "remaining": remaining,
        "applied_opportunity": actor.opportunity,
    }


def test_luminar_tier35_catalog_is_public_after_joint_release():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert talent_points_at_level(35) == 7
    expected = {
        VEREDITO_ARDENTE: "Veredito Ardente",
        CURA_PRUDENTE: "Cura Prudente",
        CICLO_LUMINOSO: "Ciclo Luminoso",
    }
    for talent_id, name in expected.items():
        definition = TALENT_DEFINITIONS[talent_id]
        assert (definition.name, definition.level, definition.character_class) == (
            name,
            35,
            "luminar",
        )
        for level in (34,):
            with pytest.raises(TalentSelectionError):
                validate_active_talent_ids("luminar", level, (talent_id,))
        assert validate_active_talent_ids("luminar", 35, (talent_id,)) == (talent_id,)
        assert validate_active_talent_ids("luminar", 60, (talent_id,)) == (talent_id,)


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        (None, D("1.122")),
        ("guardiao", D("1.0812")),
        ("inquisidor", D("1.173")),
    ),
)
def test_veredito_ardente_multiplies_only_julgamento_empowered_direct_power(
    path, expected
):
    state = _combat(
        path=path,
        arts=(SOLAR,),
        talents=(VEREDITO_ARDENTE,),
        enemy_count=3,
    )
    _set_state(state, "julgamento")

    result = act(state, SOLAR)
    events = _events(result, SOLAR)

    assert len(events) == 3
    assert {event.path_power_multiplier for event in events} == {expected}
    assert all("luminar.julgamento_consumido" in event.path_triggers for event in events)
    assert sum(bool(event.class_resource_changes) for event in events) == 1
    assert "luminar_state" not in result.fighters["player"].path_state
    assert all("luminar.fulgor_gerado" not in event.path_triggers for event in events)


def test_veredito_ardente_does_not_apply_without_julgamento_or_on_rejected_action():
    without_state = _combat(talents=(VEREDITO_ARDENTE,))
    result = act(without_state, SOLAR)
    event = _events(result, SOLAR)[0]
    assert event.path_power_multiplier == D(1)
    assert "luminar.julgamento_consumido" not in event.path_triggers

    state = _combat(
        path="inquisidor", arts=(VEREDITO,), talents=(VEREDITO_ARDENTE,)
    )
    _set_state(state, "julgamento")
    assert act(state, VEREDITO, target_id="missing-target") is state
    assert state.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"
    assert VEREDITO not in state.fighters["player"].cooldowns
    assert not _events(state, VEREDITO)


@pytest.mark.parametrize(
    ("target_hp", "expected_multiplier", "expected_heal"),
    (
        (D("399.9"), D("1.05"), D(73)),
        (D(400), D("1.05"), D(73)),
        (D("400.1"), D(1), D(70)),
    ),
)
def test_cura_prudente_uses_inclusive_target_hp_snapshot(
    target_hp, expected_multiplier, expected_heal
):
    state = _combat(
        arts=(LUZ,),
        talents=(CURA_PRUDENTE,),
        hp=D(800),
        ally_hps=(target_hp,),
    )
    target_id = state.fighters["ally-0"].id

    result = act(state, LUZ, target_id=target_id)
    event = next(
        event for event in _events(result, LUZ) if event.target == target_id
    )

    assert event.path_power_multiplier == expected_multiplier
    assert event.calculated_healing == expected_heal
    assert event.barrier_power_multiplier == D(1)
    assert ("luminar.cura_prudente" in event.path_triggers) is (expected_multiplier > 1)
    assert result.fighters["player"].hp == D(800)  # The caster's HP does not set eligibility.


def test_cura_prudente_evaluates_each_aurora_guardia_recipient_independently():
    state = _combat(
        path="guardiao",
        arts=(AURORA_GUARDIA,),
        talents=(CURA_PRUDENTE,),
        hp=D(800),
        ally_hps=(D(400),),
    )

    result = act(state, AURORA_GUARDIA)
    events = _events(result, AURORA_GUARDIA)

    assert len(events) == 2
    assert {event.path_power_multiplier for event in events} == {D(1), D("1.05")}
    assert {event.calculated_healing for event in events} == {D(55), D(57)}
    assert sum("luminar.cura_prudente" in event.path_triggers for event in events) == 1


def test_ciclo_luminoso_extends_one_expiration_and_codec_preserves_shared_combat_quota():
    state = _combat(
        talents=(CICLO_LUMINOSO, "talent.luminar.contraluz_persistente")
    )
    generated = act(state, SOLAR)
    actor = generated.fighters["player"]
    assert actor.path_state["luminar_state"]["kind"] == "fulgor"
    assert actor.path_state["luminar_state"]["remaining"] == 3

    first = act(generated, "attack", target_id=generated.fighters["enemy-0"].id)
    second = act(first, "attack", target_id=first.fighters["enemy-0"].id)
    extended = act(second, "attack", target_id=second.fighters["enemy-0"].id)
    actor = extended.fighters["player"]
    assert actor.path_state["luminar_state"]["remaining"] == 1
    assert actor.path_state["luminar_cycle_used"] is True

    restored = decode(encode(extended), extended.id, extended.ruleset, extended.version)
    assert restored.fighters["player"].path_state == actor.path_state
    expired = act(restored, "attack", target_id=restored.fighters["enemy-0"].id)
    assert "luminar_state" not in expired.fighters["player"].path_state
    assert expired.fighters["player"].path_state["luminar_cycle_used"] is True


def test_ciclo_luminoso_quota_is_shared_after_fulgor_consumption_and_not_reused():
    state = _combat(
        arts=(SOLAR, LUZ, RENOVACAO),
        talents=(CICLO_LUMINOSO,),
        hp=D(500),
    )
    state = act(state, SOLAR)
    consumed = act(state, LUZ, target_id=state.fighters["player"].id)
    assert "luminar_state" not in consumed.fighters["player"].path_state
    assert "luminar_cycle_used" not in consumed.fighters["player"].path_state

    generated = act(consumed, RENOVACAO, target_id=consumed.fighters["player"].id)
    actor = generated.fighters["player"]
    assert actor.path_state["luminar_state"]["kind"] == "julgamento"
    assert actor.path_state["luminar_state"]["remaining"] == 2

    first = act(generated, "attack", target_id=generated.fighters["enemy-0"].id)
    second = act(first, "attack", target_id=first.fighters["enemy-0"].id)
    assert second.fighters["player"].path_state["luminar_cycle_used"] is True
    assert second.fighters["player"].path_state["luminar_state"]["remaining"] == 1
    restored = decode(encode(second), second.id, second.ruleset, second.version)
    consumed_extended = act(restored, SOLAR)
    consumed_event = _events(consumed_extended, SOLAR)[-1]
    assert "luminar.julgamento_consumido" in consumed_event.path_triggers
    assert "luminar_state" not in consumed_extended.fighters["player"].path_state
    assert consumed_extended.fighters["player"].path_state["luminar_cycle_used"] is True

    # Once the cooldown clears, another Fulgor expires normally: the one
    # combat-scoped extension has already been spent by Judgment.
    ready = consumed_extended
    for _ in range(3):
        ready = act(ready, "attack", target_id=ready.fighters["enemy-0"].id)
    generated_fulgor = act(ready, SOLAR)
    state_entry = generated_fulgor.fighters["player"].path_state["luminar_state"]
    assert state_entry["kind"] == "fulgor"
    assert state_entry["remaining"] == 2
    first = act(generated_fulgor, "attack", target_id=generated_fulgor.fighters["enemy-0"].id)
    expired_again = act(first, "attack", target_id=first.fighters["enemy-0"].id)
    assert "luminar_state" not in expired_again.fighters["player"].path_state
    assert expired_again.fighters["player"].path_state["luminar_cycle_used"] is True


def test_luminar_nv35_effects_coexist_across_damage_healing_and_expiration():
    state = _combat(
        arts=(SOLAR, LUZ),
        talents=(VEREDITO_ARDENTE, CURA_PRUDENTE, CICLO_LUMINOSO),
        ally_hps=(D(400),),
    )
    _set_state(state, "julgamento")

    damage = act(state, SOLAR)
    damage_event = _events(damage, SOLAR)[0]
    assert damage_event.path_power_multiplier == D("1.122")
    assert "luminar_state" not in damage.fighters["player"].path_state

    healed = act(damage, LUZ, target_id=damage.fighters["ally-0"].id)
    heal_event = _events(healed, LUZ)[0]
    assert heal_event.path_power_multiplier == D("1.05")
    assert heal_event.calculated_healing == D(73)
    assert healed.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"

    first = act(healed, "attack", target_id=healed.fighters["enemy-0"].id)
    second = act(first, "attack", target_id=first.fighters["enemy-0"].id)
    assert second.fighters["player"].path_state["luminar_cycle_used"] is True
    assert second.fighters["player"].path_state["luminar_state"]["remaining"] == 1


def test_luminar_same_state_reapplication_does_not_spend_cycle_allowance():
    state = _combat(talents=(CICLO_LUMINOSO,))
    _set_state(state, "fulgor", remaining=1)

    result = act(state, SOLAR)
    actor = result.fighters["player"]

    assert actor.path_state["luminar_state"]["kind"] == "fulgor"
    assert actor.path_state["luminar_state"]["remaining"] == 2
    assert "luminar_cycle_used" not in actor.path_state
