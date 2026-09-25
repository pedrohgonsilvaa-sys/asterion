from copy import deepcopy
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.combat import Effect, act, allowed_actions, apply_effect, initiative
from asterion.domain.combat_math import Stats
from asterion.domain.creation import CLASSES, RACES
from asterion.domain.prologue import FIRST_ARTS, PROFILE, first_art
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
COMBAT_ID = UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5")


def battle(cls="sentinela", race="velado", combat_id=COMBAT_ID):
    from asterion.domain.combat_math import class_stats, racial_stats

    stats = racial_stats(class_stats(cls, 1), race)
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
