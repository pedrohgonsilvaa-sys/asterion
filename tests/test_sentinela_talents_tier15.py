from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import pytest

from asterion.domain.combat import Action, Combat, Fighter, act, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    class_stats,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
COMBAT_ID = UUID("01234567-89ab-cdef-0123-456789abcdef")
PONTA = "talent.sentinela.ponta_revidada"
PLACAS = "talent.sentinela.placas_internas"
GUARDA = "talent.sentinela.guarda_preparada"


def _battle(
    *,
    talents: tuple[str, ...] = (),
    evasion: Decimal = ZERO,
    retaliation: bool = False,
    pvp: bool = False,
    enemy_hit_count: int = 1,
) -> Combat:
    player = Fighter(
        "player.entity",
        "Sentinela",
        34,
        CombatStats(D(1000), D(120), D(80), D(100), per=D(0), crit=D(0)),
        D(1000),
        race="remanescente",
        character_class="sentinela",
        talent_ids=talents,
        retaliation_charges=int(retaliation),
        retaliation_remaining=int(retaliation),
        retaliation_activation_id="test:retaliation" if retaliation else "",
        retaliation_source_type="defender" if retaliation else "",
        retaliation_source_event_id="test:defender" if retaliation else "",
        retaliation_source_actor_id="enemy.entity" if retaliation else "",
    )
    enemy = Fighter(
        "enemy.entity",
        "Eco",
        34,
        CombatStats(D(5000), D(100), D(100), D(10), per=D(0), crit=D(0), evasion=evasion),
        D(5000),
        side="enemy",
    )
    return start_combat(
        Combat(
            id=COMBAT_ID,
            ruleset=CURRENT_COMBAT_RULESET,
            fighters={"player": player, "enemy": enemy},
            player_actions={
                "attack": Action("attack", "Ataque Básico", D(1)),
                "test_art": Action(
                    "class_art.sentinela.talent_test",
                    "Arte de teste",
                    D(1),
                ),
                "wall_a": Action(
                    "wall_a",
                    "Barreira A",
                    D(0),
                    target_mode="ally",
                    target_barrier_coefficient=D("0.50"),
                    target_barrier_duration=2,
                ),
                "wall_b": Action(
                    "wall_b",
                    "Barreira B",
                    D(0),
                    target_mode="ally",
                    target_barrier_coefficient=D("0.50"),
                    target_barrier_duration=3,
                ),
            },
            enemy_actions={
                "smash": Action(
                    "smash", "Golpe", D("1.00"), hit_count=enemy_hit_count
                ),
                "hold": Action("hold", "Aguardar", D(0), target_mode="self"),
            },
            ai_cycle=("smash",),
            pvp_mode=pvp,
        )
    )


def _player_event(state: Combat, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.actor_entity_id == state.fighters["player"].id
        and event.action == action_id
    )


def _prime_guard(state: Combat) -> Combat:
    guarded = act(state, "defend")
    incoming = next(
        event
        for event in guarded.events
        if event.actor_entity_id == guarded.fighters["enemy"].id
        and event.action == "smash"
    )
    assert incoming.defender_prevented_damage > 0
    pending = guarded.fighters["player"].path_state["guard_prepared_barrier"]
    assert pending["remaining"] == 2
    assert pending["applied_opportunity"] <= guarded.fighters["player"].opportunity
    return guarded


@pytest.mark.parametrize(
    ("action_id", "event_action", "retaliation", "expected_penetration"),
    [
        ("attack", "attack", True, D(4)),
        ("attack", "attack", False, D(0)),
        ("test_art", "test_art", True, D(4)),
    ],
)
def test_ponta_revidada_adds_four_percentage_points_only_to_committed_retaliation_action(
    action_id, event_action, retaliation, expected_penetration
):
    state = _battle(talents=(PONTA,), retaliation=retaliation)
    resolved = act(state, action_id, target_id="enemy")
    event = _player_event(resolved, event_action)
    if retaliation:
        from asterion.domain.combat_math import direct_damage

        expected = direct_damage(
            D(120), D(1), D(100), 34, penetration=expected_penetration
        )
    else:
        from asterion.domain.combat_math import direct_damage

        expected = direct_damage(D(120), D(1), D(100), 34)
    assert event.calculated_damage == expected


def test_ponta_revidada_does_not_become_a_persistent_stat_or_apply_to_defender():
    state = _battle(talents=(PONTA,), retaliation=True)
    defended = act(state, "defend")
    assert defended.fighters["player"].retaliation_charges == 1
    assert defended.fighters["player"].stats.per == D(0)
    attacked = act(defended, "attack", target_id="enemy")
    assert attacked.fighters["player"].retaliation_charges == 0
    assert attacked.fighters["player"].stats.per == D(0)


def test_ponta_revidada_uses_snapshot_and_consumes_on_dodge_or_full_barrier():
    dodged = _battle(talents=(PONTA,), retaliation=True, evasion=D(100))
    dodged = act(dodged, "attack", target_id="enemy")
    assert _player_event(dodged, "attack").dodged
    assert dodged.fighters["player"].retaliation_charges == 0

    barriered = _battle(talents=(PONTA,), retaliation=True)
    enemy = barriered.fighters["enemy"]
    enemy.barrier = D(10000)
    enemy.barrier_remaining = 2
    enemy.barrier_source = "test:barrier"
    barriered = act(barriered, "attack", target_id="enemy")
    event = _player_event(barriered, "attack")
    assert event.barrier_absorbed >= event.calculated_damage
    assert barriered.fighters["player"].retaliation_charges == 0


def test_placas_internas_is_defined_and_authoritatively_available_at_level_15():
    definition = TALENT_DEFINITIONS[PLACAS]
    assert definition.level == 15
    assert definition.defense_percent == D("0.02")
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15})
    assert validate_active_talent_ids("sentinela", 15, (PLACAS,)) == (PLACAS,)
    assert validate_talent_choices("sentinela", 15, ((1, PLACAS),)) == ((1, PLACAS),)
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("sentinela", 14, (PLACAS,))


def test_placas_internas_composes_with_path_equipment_and_single_final_rounding():
    equipment = EquipmentStatContribution(
        defense=D("13.25"),
        rune_percent=(D(0), D(0), D("0.035"), D(0), D(0), D(0), D(0), D(0)),
        rune_points=(D(0), D(0), D("0.4"), D(0), D(0), D(0), D(0), D(0)),
        enchantment_percent=(D(0), D(0), D("0.025"), D(0), D(0), D(0), D(0), D(0)),
        enchantment_points=(D(0), D(0), D("0.3"), D(0), D(0), D(0), D(0), D(0)),
    )
    definition = TALENT_DEFINITIONS[PLACAS]
    modifiers = _static_talent_modifier_totals([definition])
    baseline_modifiers = (D(0), D(0), D(0), D(0))
    baseline = _resolve_combat_stats_with_static_talent_modifiers(
        "sentinela", 34, "remanescente", equipment, "bastiao", baseline_modifiers
    )
    actual = _resolve_combat_stats_with_static_talent_modifiers(
        "sentinela", 34, "remanescente", equipment, "bastiao", modifiers
    )

    base_defense = class_stats("sentinela", 34).defense
    path = PATH_DEFINITIONS["bastiao"]
    raw = (
        (base_defense * (D(1) + path.defense) * D("1.02") + equipment.defense)
        * (D(1) + equipment.rune_percent[2])
        + equipment.rune_points[2]
    )
    raw = (raw * (D(1) + equipment.enchantment_percent[2])
           + equipment.enchantment_points[2]) * D("1.015")
    expected = raw.quantize(D(1), rounding=ROUND_HALF_UP)

    assert actual.defense == expected
    assert actual.defense > baseline.defense
    assert (actual.hp, actual.attack, actual.agility) == (
        baseline.hp,
        baseline.attack,
        baseline.agility,
    )
    public = resolve_combat_stats(
        "sentinela", 34, "remanescente", equipment, "bastiao", (PLACAS,)
    )
    assert public == actual


def test_placas_internas_static_result_survives_combat_snapshot_roundtrip():
    definition = TALENT_DEFINITIONS[PLACAS]
    stats = _resolve_combat_stats_with_static_talent_modifiers(
        "sentinela",
        34,
        "remanescente",
        None,
        None,
        _static_talent_modifier_totals([definition]),
    )
    state = _battle()
    state.fighters["player"].stats = stats
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].stats == stats


def test_guarda_preparada_requires_actual_defender_reduction_and_is_idempotent_per_action():
    state = _battle(talents=(GUARDA,), enemy_hit_count=3)
    guarded = _prime_guard(state)
    assert guarded.fighters["player"].retaliation_charges == 1
    assert len(
        [event for event in guarded.mechanic_events if event.retaliation_event == "granted"]
    ) == 1

    no_reduction = _battle(talents=(GUARDA,))
    no_reduction.fighters["player"].stats = replace(
        no_reduction.fighters["player"].stats, evasion=D(100)
    )
    no_reduction = act(no_reduction, "defend")
    assert "guard_prepared_barrier" not in no_reduction.fighters["player"].path_state


def test_guarda_preparada_boosts_only_the_next_barrier_action_and_expires_after_two_turns():
    state = _prime_guard(_battle(talents=(GUARDA,)))
    state.ai_cycle = ("hold",)
    state = act(state, "wall_a", target_id="player.entity")
    first = _player_event(state, "wall_a")
    assert first.barrier_power_multiplier == D("1.06")
    assert "sentinela.guarda_preparada" in first.path_triggers
    assert first.barrier_value == D("63")
    assert "guard_prepared_barrier" not in state.fighters["player"].path_state

    state = act(state, "wall_b", target_id="player.entity")
    second = _player_event(state, "wall_b")
    assert second.barrier_power_multiplier == D(1)
    assert len(state.fighters["player"].barrier_layers) == 2
    assert {
        layer.identity for layer in state.fighters["player"].barrier_layers
    } == {("player.entity", "wall_a"), ("player.entity", "wall_b")}
    from asterion.domain.combat import _deal_combat_damage

    actual_damage, absorbed = _deal_combat_damage(
        state, "player", D(80), source_key="enemy"
    )
    assert actual_damage == ZERO
    assert absorbed == D(80)
    assert state.fighters["player"].barrier == D(43)

    expiring = _prime_guard(_battle(talents=(GUARDA,)))
    fighter = expiring.fighters["player"]
    applied = fighter.path_state["guard_prepared_barrier"]["applied_opportunity"]
    fighter.opportunity = applied + 1
    from asterion.domain.combat import _tick_path_resources

    _tick_path_resources(expiring, "player")
    assert fighter.path_state["guard_prepared_barrier"]["remaining"] == 1
    fighter.opportunity = applied + 2
    _tick_path_resources(expiring, "player")
    assert "guard_prepared_barrier" not in fighter.path_state


def test_guarda_preparada_invalid_barrier_target_does_not_consume_pending_trigger():
    state = _prime_guard(_battle(talents=(GUARDA,)))
    rejected = act(state, "wall_a", target_id="not-in-encounter")
    assert rejected.version == state.version
    assert rejected.events == state.events
    assert rejected.fighters["player"].cooldowns == state.fighters["player"].cooldowns
    assert "guard_prepared_barrier" in state.fighters["player"].path_state


def test_guarda_preparada_refreshes_same_source_and_respects_pvp_aggregate_cap():
    state = _prime_guard(_battle(talents=(GUARDA,)))
    state.ai_cycle = ("hold",)
    state = act(state, "wall_a", target_id="player.entity")
    first = _player_event(state, "wall_a")
    assert first.barrier_power_multiplier == D("1.06")
    state = act(state, "wall_a", target_id="player.entity")
    second = _player_event(state, "wall_a")
    assert second.barrier_power_multiplier == D(1)
    assert len(state.fighters["player"].barrier_layers) == 1
    assert second.barrier_value == D("60")

    pvp = _prime_guard(_battle(talents=(GUARDA,), pvp=True))
    fighter = pvp.fighters["player"]
    fighter.barrier = D(350)
    fighter.barrier_remaining = 3
    fighter.barrier_source = "preexisting"
    pvp.ai_cycle = ("hold",)
    pvp = act(pvp, "wall_a", target_id="player.entity")
    assert pvp.fighters["player"].barrier <= fighter.stats.hp * D("0.35")
    assert _player_event(pvp, "wall_a").barrier_power_multiplier == D("1.06")
    assert "guard_prepared_barrier" not in pvp.fighters["player"].path_state


def test_guarda_preparada_pending_state_persists_and_clears_on_combat_end_or_death():
    state = _prime_guard(_battle(talents=(GUARDA,)))
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state["guard_prepared_barrier"] == state.fighters[
        "player"
    ].path_state["guard_prepared_barrier"]

    from asterion.domain.combat import _finish_combat

    _finish_combat(restored, "victory")
    assert "guard_prepared_barrier" not in restored.fighters["player"].path_state

    defeated = _prime_guard(_battle(talents=(GUARDA,)))
    from asterion.domain.combat import _deal_combat_damage

    _deal_combat_damage(defeated, "player", D(10000), source_key="enemy")
    dead = defeated.fighters["player"]
    assert "guard_prepared_barrier" not in dead.path_state


def test_tier_15_choices_are_valid_but_tier_25_remains_closed():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15})
    for slot, talent_id in enumerate((PONTA, PLACAS, GUARDA), 1):
        assert validate_active_talent_ids("sentinela", 15, (talent_id,)) == (talent_id,)
        assert validate_talent_choices("sentinela", 15, ((slot, talent_id),)) == (
            (slot, talent_id),
        )

    valid_nv5 = "talent.sentinela.aco_desperto"
    assert validate_active_talent_ids("sentinela", 15, (valid_nv5,)) == (valid_nv5,)
    tier25 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "sentinela" and definition.level == 25
    )
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("sentinela", 60, (tier25,))
