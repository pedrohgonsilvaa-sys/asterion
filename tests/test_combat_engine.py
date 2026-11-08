from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.combat import (
    Effect,
    _perform,
    act,
    allowed_actions,
    apply_effect,
    initiative,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    LEGACY_COMBAT_RULESET,
    CombatRng,
    Stats,
    direct_damage,
    resolve_combat_stats,
)
from asterion.domain.creation import CLASSES, RACES
from asterion.domain.prologue import FIRST_ARTS, PROFILE, first_art
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
COMBAT_ID = UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5")


def battle(cls="sentinela", race="velado", combat_id=COMBAT_ID):
    stats = resolve_combat_stats(cls, 1, race)
    return PROFILE.create(combat_id, "Luiken", cls, race, stats.hp)


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("race", RACES)
@pytest.mark.parametrize("basics", [("attack", "defend"), ("defend", "attack")])
def test_all_thirty_combinations_complete_both_tutorial_orders(cls, race, basics):
    state = battle(cls, race)
    assert set(allowed_actions(state)) == {"attack", "defend"}
    original = deepcopy(state)
    for index, action in enumerate(basics):
        state = act(state, action)
        assert state.events[-1].action == ("bite" if action == "attack" else "charge")
        assert allowed_actions(state) == ((basics[1],) if index == 0 else ("art",))
        assert state.fighters["player"].hp > 0
    state = act(state, "art")
    if not state.result:
        assert state.events[-1].action == "bite" and state.ai_position == 1
        assert state.tutorial_stage == "normal"
    for _ in range(20):
        if state.result:
            break
        state = act(state, "attack")
    assert state.result == "victory"
    assert state.fighters["player"].hp > 0
    assert state.fighters["enemy"].hp == 0
    assert original.version == 0 and original.events == []
    assert allowed_actions(state) == ()


@pytest.mark.parametrize(
    "cls, coefficient",
    [
        ("sentinela", "1.10"),
        ("errante", "1.15"),
        ("vigia", "1.15"),
        ("tecelao", "1.20"),
        ("oraculo", "1.05"),
        ("luminar", "1.10"),
    ],
)
def test_six_first_arts_have_official_coefficients(cls, coefficient):
    action = first_art(cls, 1)
    assert action.coefficient == D(coefficient)
    assert action.name == FIRST_ARTS[cls][0]


def test_art_kill_stops_before_enemy_response():
    state = act(act(battle(), "attack"), "defend")
    state.fighters["enemy"].hp = D(1)
    event_count = len(state.events)
    result = act(state, "art")
    assert result.result == "victory"
    assert len(result.events) == event_count + 1
    assert result.events[-1].actor == "player"


def test_normal_ai_starts_with_bite_and_cycles_without_random_choice():
    state = battle()
    state.fighters["enemy"].hp = D(10000)
    state = act(act(act(state, "defend"), "attack"), "art")
    assert state.events[-1].action == "bite"
    for action in ("bite", "charge", "bite", "bite", "charge"):
        state = act(state, "attack")
        assert state.events[-1].action == action


def test_blocked_opportunity_cooldown_is_enforced_by_engine():
    state = act(act(battle(), "attack"), "defend")
    state.fighters["enemy"].hp = D(10000)
    state = act(state, "art")
    assert "art" not in allowed_actions(state)
    assert act(state, "art") is state
    state = act(state, "attack")
    assert "art" in allowed_actions(state)


def test_oracle_debuff_affects_exactly_two_future_enemy_opportunities():
    state = act(act(battle("oraculo"), "attack"), "defend")
    state.fighters["enemy"].hp = D(10000)
    state = act(state, "art")
    enemy = state.fighters["enemy"]
    assert enemy.stat("attack") == 46
    assert len(enemy.effects) == 1 and enemy.effects[0].remaining == 1
    assert enemy.effects[0].magnitude == D("0.08")
    state = act(state, "attack")
    assert state.fighters["enemy"].effects == []
    assert state.fighters["enemy"].stat("attack") == 50


def test_defender_expires_on_next_turn_and_cannot_be_consecutive():
    state = battle()
    state.tutorial = None
    defended = act(state, "defend")
    assert defended.fighters["player"].defending is False
    assert "defend" not in allowed_actions(defended)
    assert act(defended, "defend") is defended
    attacked = act(defended, "attack")
    assert "defend" in allowed_actions(attacked)


def test_initiative_uses_agility_and_freezes_within_round():
    state = battle()
    assert state.order == ("player", "enemy")
    state.fighters["player"].effects.append(Effect("slow", "agility", D("0.9"), 3, 1))
    assert initiative(state) == ("enemy", "player")
    assert state.order == ("player", "enemy")
    result = act(state, "attack")
    # Enemy finishes round 1, then acts first in round 2 after AGI recomputation.
    assert [(e.round, e.actor) for e in result.events] == [
        (1, "player"),
        (1, "enemy"),
        (2, "enemy"),
    ]
    assert result.order == ("enemy", "player")


def test_equal_agility_priority_stable_for_entire_combat():
    state = battle()
    state.fighters["enemy"].stats = state.fighters["player"].stats
    order = initiative(state)
    for round_number in (1, 2, 100):
        state.round = round_number
        assert initiative(state) == order
    other = deepcopy(state)
    other.id = UUID(int=1)
    assert initiative(other) == initiative(other)


def test_racial_duration_and_magnitude_are_target_owned_and_reproducible():
    for race in ("velado", "alvorano"):
        state = battle(race=race)
        clone = deepcopy(state)
        effect = Effect("test", "attack", D("0.08"), 2, 0)
        apply_effect(state, state.fighters["player"], effect)
        apply_effect(clone, clone.fighters["player"], effect)
        assert encode(state) == encode(clone)
        applied = state.fighters["player"].effects[0]
        assert applied.applied_opportunity == 1
        if race == "alvorano":
            assert applied.magnitude == D("0.0704") and applied.remaining == 2
        else:
            assert applied.remaining in (1, 2) and state.rng_cursor == 1


def test_velado_excludes_ineligible_effects_and_one_turn_effects():
    state = battle(race="velado")
    target = state.fighters["player"]
    for effect_id, eligible, duration in (
        ("ineligible", False, 2),
        ("one-turn", True, 1),
    ):
        apply_effect(
            state,
            target,
            Effect(effect_id, "attack", D("0.1"), duration, 0, duration_eligible=eligible),
        )
        assert target.effects[-1].id == effect_id
        assert target.effects[-1].remaining == duration
    assert state.rng_cursor == 0


def test_hemario_heals_actual_damage_only_and_caps_per_action():
    state = battle(race="hemario")
    player = state.fighters["player"]
    player.hp = player.stats.hp * D("0.40")
    state.fighters["enemy"].hp = D("2.5")
    result = act(state, "attack")
    assert result.events[-1].healed == D("0")
    assert result.fighters["player"].hp == player.hp
    state.fighters["enemy"].hp = D(10000)
    player.stats = Stats(player.stats.hp, D(10000), player.stats.defense, player.stats.agility)
    result = act(state, "attack")
    assert result.events[0].healed == D("21")


def test_hemario_vampirism_floors_fractional_heal_and_keeps_positive_integer():
    state = battle(race="hemario")
    player = state.fighters["player"]
    player.hp = player.stats.hp * D("0.40") - D("10")
    state.fighters["enemy"].hp = D("10000")
    player.stats = Stats(player.stats.hp, D("100"), player.stats.defense, player.stats.agility)
    result = act(state, "attack")
    assert result.events[0].healed == D("8")


def test_hemario_above_threshold_does_not_heal():
    state = battle(race="hemario")
    result = act(state, "attack")
    assert result.events[0].healed == 0


def test_snapshot_roundtrip_reproduces_actions_and_criticals():
    state = battle("oraculo", "remanescente")
    for action in ("attack", "defend", "art", "attack", "attack"):
        restored = decode(encode(state), state.id, state.ruleset, state.version)
        assert restored == state
        expected = act(state, action)
        assert act(restored, action) == expected
        state = expected


def test_forged_actions_do_not_advance_rng_hp_version_or_tutorial():
    state = battle()
    for action in ("art", "bite", "charge", "reward", "attack:99999", "", "defend:2"):
        assert act(state, action) is state


def test_current_ruleset_uses_total_crit_percentage_points():
    state = battle(race="velado")
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    actor.stats = replace(actor.stats, attack=D(100), crit=D(100))
    target.stats = replace(target.stats, defense=D(0), evasion=D(0), block=D(0))
    target.hp = D(1000)

    _perform(state, "player", "attack")

    event = state.events[-1]
    assert state.ruleset == CURRENT_COMBAT_RULESET
    assert event.critical and event.damage == 150
    assert state.rng_cursor == 1


def test_percent_point_attributes_do_not_inherit_multiplicative_effect_semantics():
    state = battle()
    player = state.fighters["player"]
    player.stats = replace(player.stats, per=D(10))
    player.effects.append(Effect("per-effect", "per", D("0.5"), 2, player.opportunity))
    assert player.stat("per") == D(10)


def test_dodge_stops_hit_before_crit_block_barrier_or_hp():
    state = battle()
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    actor.stats = replace(actor.stats, attack=D(100), crit=D(100))
    target.stats = replace(
        target.stats, defense=D(0), evasion=D(100), block=D(100)
    )
    target.hp = D(1000)
    target.barrier = D(100)
    target.barrier_remaining = 2
    starting_hp, starting_barrier = target.hp, target.barrier

    _perform(state, "player", "attack")

    event = state.events[-1]
    assert event.dodged and not event.critical and not event.blocked
    assert event.damage == 0
    assert target.hp == starting_hp and target.barrier == starting_barrier
    assert state.rng_cursor == 1
    assert state.evasion_streaks == {"enemy": 1}


def test_failed_dodge_roll_continues_to_crit_pipeline():
    state = battle(combat_id=UUID(int=0))
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    actor.stats = replace(actor.stats, attack=D(100), crit=D(0))
    target.stats = replace(target.stats, defense=D(0), evasion=D(50), block=D(0))
    target.hp = D(1000)
    state.rng_cursor = 0

    _perform(state, "player", "attack")

    event = state.events[-1]
    assert not event.dodged and not event.critical and event.damage == 100
    assert target.hp == D(900)
    assert state.rng_cursor == 1


def test_zero_crit_chance_does_not_consume_a_crit_draw():
    state = battle()
    state.fighters["player"].stats = replace(
        state.fighters["player"].stats, attack=D(100), crit=D(0)
    )
    state.fighters["enemy"].stats = replace(
        state.fighters["enemy"].stats, defense=D(0), evasion=D(0), block=D(0)
    )

    _perform(state, "player", "attack")

    assert not state.events[-1].critical
    assert state.rng_cursor == 0


def test_two_consecutive_dodges_force_next_eligible_attack_to_hit_and_reset_streak():
    state = battle()
    state.tutorial = None
    player = state.fighters["player"]
    enemy = state.fighters["enemy"]
    player.stats = replace(player.stats, attack=D(10), crit=D(0))
    enemy.stats = replace(enemy.stats, hp=D(100000), defense=D(0), evasion=D(100))
    enemy.hp = D(100000)

    outcomes = []
    for _ in range(4):
        previous_count = len(state.events)
        state = act(state, "attack")
        player_event = next(
            event for event in state.events[previous_count:] if event.actor == "player"
        )
        outcomes.append(player_event.dodged)

    assert outcomes == [True, True, False, True]
    assert state.evasion_streaks["enemy"] == 1


def test_dodge_streak_and_future_rng_survive_snapshot_reconnect():
    state = battle()
    state.tutorial = None
    state.fighters["enemy"].stats = replace(
        state.fighters["enemy"].stats, hp=D(100000), defense=D(0), evasion=D(100)
    )
    state.fighters["enemy"].hp = D(100000)
    state.fighters["player"].stats = replace(
        state.fighters["player"].stats, attack=D(10), crit=D(0)
    )
    state = act(state, "attack")
    assert state.evasion_streaks["enemy"] == 1

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.evasion_streaks.get("enemy") == 1
    expected, actual = act(state, "attack"), act(restored, "attack")
    assert actual == expected
    assert actual.evasion_streaks["enemy"] == 2
    previous_count = len(expected.events)
    expected, actual = act(expected, "attack"), act(actual, "attack")
    assert actual == expected
    forced_hit = next(
        event
        for event in actual.events[previous_count:]
        if event.actor == "player"
    )
    assert not forced_hit.dodged and actual.evasion_streaks["enemy"] == 0


def test_block_combines_with_cinereo_defender_before_barrier():
    state = battle()
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    actor.stats = replace(actor.stats, attack=D(100), crit=D(0), per=D(0))
    target.stats = replace(target.stats, defense=D(0), evasion=D(0), block=D(100))
    target.race = "cinereo"
    target.defending = True
    target.hp = D(1000)
    target.barrier = D(100)
    target.barrier_remaining = 2

    _perform(state, "player", "attack")

    event = state.events[-1]
    assert event.blocked and not event.dodged and not event.critical
    assert event.damage == 35  # (52% × 35%) compounds to 65% capped mitigation.
    assert target.barrier == D(65) and target.hp == D(1000)
    assert state.rng_cursor == 1


def test_legacy_ruleset_ignores_new_secondary_attributes_and_keeps_legacy_crit_draw():
    state = battle()
    state.ruleset = LEGACY_COMBAT_RULESET
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    actor.stats = replace(actor.stats, attack=D(100), per=D(30), crit=D(100))
    target.stats = replace(target.stats, defense=D(100), evasion=D(100), block=D(100))
    target.hp = D(1000)
    expected_crit = CombatRng(state.id, state.rng_cursor).chance(
        D("0.05"), "critical:player:attack"
    )
    expected_damage = direct_damage(D(100), D(1), D(100), 1, critical=expected_crit)

    _perform(state, "player", "attack")

    event = state.events[-1]
    assert not event.dodged and not event.blocked
    assert event.critical is expected_crit and event.damage == expected_damage
    assert state.rng_cursor == 1


def test_four_stat_legacy_snapshot_decodes_without_changing_source_payload():
    state = battle()
    payload = encode(state)
    payload.pop("evasion_streaks", None)
    for fighter in payload["fighters"].values():
        for stat in ("per", "crit", "evasion", "block"):
            fighter["stats"].pop(stat)
    for event in payload["events"]:
        event.pop("dodged", None)
        event.pop("blocked", None)
    original = deepcopy(payload)

    restored = decode(payload, state.id, LEGACY_COMBAT_RULESET, state.version)

    assert payload == original
    assert restored.evasion_streaks == {}
    assert all(
        (fighter.stats.per, fighter.stats.crit, fighter.stats.evasion, fighter.stats.block)
        == (D(0), D(5), D(0), D(0))
        for fighter in restored.fighters.values()
    )


def test_combat_codec_serializes_set_fields_in_stable_order():
    state = battle()
    state.phase_triggered_ids = {"colosso.phase_iii", "colosso.phase_ii"}

    payload = encode(state)

    assert payload["phase_triggered_ids"] == [
        "colosso.phase_ii",
        "colosso.phase_iii",
    ]
    restored = decode(payload, state.id, state.ruleset, state.version)
    assert encode(restored) == payload


def test_extended_stats_and_evasion_state_roundtrip_losslessly_as_decimal_text():
    state = battle()
    player = state.fighters["player"]
    player.stats = replace(
        player.stats,
        per=D("12.25"),
        crit=D("7.75"),
        evasion=D("1.25"),
        block=D("2.50"),
    )
    state.evasion_streaks = {"player": 2}
    payload = encode(state)

    assert payload["fighters"]["player"]["stats"]["per"] == "12.25"
    assert payload["fighters"]["player"]["stats"]["crit"] == "7.75"
    restored = decode(payload, state.id, state.ruleset, state.version)
    assert encode(restored) == payload
