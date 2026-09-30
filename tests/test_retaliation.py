from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    _grant_retaliation,
    act,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
COMBAT_ID = UUID("00112233-4455-6677-8899-aabbccddeeff")
ZERO = D(0)


def retaliation_battle(*, barrier: Decimal = ZERO, duration_bonus: int = 0) -> Combat:
    player = Fighter(
        "player",
        "Sentinela",
        10,
        CombatStats(D(1000), D(120), D(80), D(100)),
        D(1000),
        race="remanescente",
        character_class="sentinela",
        retaliation_duration_bonus=duration_bonus,
    )
    enemy = Fighter(
        "enemy.entity",
        "Eco",
        10,
        CombatStats(D(5000), D(180), D(20), D(10)),
        D(5000),
    )
    combat = Combat(
        id=COMBAT_ID,
        ruleset=CURRENT_COMBAT_RULESET,
        fighters={"player": player, "enemy": enemy},
        player_actions={
            "attack": Action("attack", "Ataque Básico", D(1)),
            "wall": Action(
                "wall",
                "Muralha",
                D(0),
                self_barrier_coefficient=D("0.70"),
                self_barrier_duration=2,
            ),
        },
        enemy_actions={"smash": Action("smash", "Golpe", D("1.40"))},
        ai_cycle=("smash",),
    )
    combat = start_combat(combat)
    if barrier:
        combat.fighters["player"].barrier = barrier
        combat.fighters["player"].barrier_remaining = 2
        combat.fighters["player"].barrier_applied_opportunity = combat.fighters[
            "player"
        ].opportunity
        combat.fighters["player"].barrier_source = "test:barrier"
    return combat


def enemy_resolution(state: Combat):
    return next(
        event
        for event in state.events
        if event.actor == "enemy" and event.action == "smash"
    )


def test_defender_positive_direct_reduction_grants_one_retaliation():
    state = act(retaliation_battle(), "defend")
    player = state.fighters["player"]
    incoming = enemy_resolution(state)

    assert incoming.defender_prevented_damage > 0
    assert incoming.defender_mitigation_applied is True
    assert player.retaliation_charges == 1
    assert player.retaliation_remaining == 1
    assert player.retaliation_source_type == "defender"
    assert player.retaliation_source_actor_id == "enemy.entity"
    assert [event.retaliation_event for event in state.mechanic_events] == ["granted"]


def test_barrier_absorbing_all_remaining_damage_does_not_block_retaliation():
    state = retaliation_battle(barrier=D(5000))
    starting_hp = state.fighters["player"].hp
    state = act(state, "defend")
    incoming = enemy_resolution(state)

    assert incoming.defender_prevented_damage > 0
    assert incoming.barrier_absorbed > 0
    assert state.fighters["player"].hp == starting_hp
    assert state.fighters["player"].retaliation_charges == 1


def test_dodge_means_defender_prevented_nothing_and_grants_no_retaliation():
    state = retaliation_battle()
    player = state.fighters["player"]
    player.stats = replace(player.stats, evasion=D(100))
    state = act(state, "defend")
    incoming = enemy_resolution(state)

    assert incoming.dodged is True
    assert incoming.defender_prevented_damage == 0
    assert state.fighters["player"].retaliation_charges == 0
    assert state.mechanic_events == []


def test_block_can_coexist_with_defender_retaliation():
    state = retaliation_battle()
    player = state.fighters["player"]
    player.stats = replace(player.stats, block=D(100))
    state = act(state, "defend")
    incoming = enemy_resolution(state)

    assert incoming.blocked is True
    assert incoming.defender_prevented_damage > 0
    assert state.fighters["player"].retaliation_charges == 1


def test_basic_attack_consumes_at_commit_and_records_action_context():
    state = act(retaliation_battle(), "defend")
    activation_id = state.fighters["player"].retaliation_activation_id
    state = act(state, "attack")
    event = next(
        event for event in state.events if event.actor == "player" and event.action == "attack"
    )

    assert event.retaliation_used is True
    assert event.retaliation_valid is True
    assert event.retaliation_activation_id == activation_id
    assert event.retaliation_source_type == "defender"
    assert state.fighters["player"].retaliation_charges == 0
    assert [event.retaliation_event for event in state.mechanic_events][-2:] == [
        "consumed",
        "action_resolved",
    ]


def test_dodge_after_action_commit_still_consumes_retaliation():
    state = act(retaliation_battle(), "defend")
    enemy = state.fighters["enemy"]
    enemy.stats = replace(enemy.stats, evasion=D(100))
    state = act(state, "attack")
    event = next(
        event for event in state.events if event.actor == "player" and event.action == "attack"
    )

    assert event.dodged is True
    assert event.retaliation_used is True
    assert state.fighters["player"].retaliation_charges == 0


def test_pure_barrier_does_not_consume_and_one_turn_retaliation_expires():
    state = act(retaliation_battle(), "defend")
    state = act(state, "wall")

    assert state.fighters["player"].retaliation_charges == 0
    assert "consumed" not in [event.retaliation_event for event in state.mechanic_events]
    assert "expired" in [event.retaliation_event for event in state.mechanic_events]


def test_rejected_action_does_not_consume_retaliation():
    state = act(retaliation_battle(), "defend")
    state.fighters["player"].cooldowns["attack"] = state.fighters["player"].opportunity + 10
    activation_id = state.fighters["player"].retaliation_activation_id

    result = act(state, "attack")

    assert result is state
    assert result.fighters["player"].retaliation_charges == 1
    assert result.fighters["player"].retaliation_activation_id == activation_id


def test_retaliation_persistent_adds_only_duration_and_survives_first_nonoffensive_turn():
    state = act(retaliation_battle(duration_bonus=1), "defend")
    player = state.fighters["player"]
    assert player.retaliation_charges == 1
    assert player.retaliation_remaining == 2

    state = act(state, "wall")
    player = state.fighters["player"]
    assert player.retaliation_charges == 1
    assert player.retaliation_remaining == 1


def test_refresh_keeps_one_charge_same_activation_and_never_reduces_duration():
    state = retaliation_battle(duration_bonus=1)
    player = state.fighters["player"]
    enemy = state.fighters["enemy"]
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=enemy,
        source_event_id="event-1",
    )
    activation_id = player.retaliation_activation_id
    player.retaliation_remaining = 2

    _grant_retaliation(
        state,
        target_key="player",
        source_actor=enemy,
        source_event_id="event-2",
    )

    assert player.retaliation_charges == 1
    assert player.retaliation_remaining == 2
    assert player.retaliation_activation_id == activation_id
    assert player.retaliation_source_event_id == "event-2"
    assert [event.retaliation_event for event in state.mechanic_events] == [
        "granted",
        "refreshed",
    ]


def test_codec_roundtrip_preserves_retaliation_and_lifecycle_events():
    state = act(retaliation_battle(), "defend")

    restored = decode(encode(state), state.id, state.ruleset, state.version)

    assert restored == state
    assert restored.fighters["player"].retaliation_charges == 1
    assert restored.mechanic_events[-1].retaliation_event == "granted"
