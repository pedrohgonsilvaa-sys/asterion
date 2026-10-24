from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.domain.combat import (
    Action,
    ActionEffect,
    Combat,
    DotState,
    Effect,
    Fighter,
    _deal_combat_damage,
    _end_turn,
    _perform,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    direct_damage,
)
from asterion.domain.talents import (
    TALENT_DEFINITIONS,
    _static_talent_secondary_modifier_totals,
)

D = Decimal
ZERO = D(0)
HUNDRED = D(100)
ONE_THOUSAND = D(1000)

PONTA = "talent.sentinela.ponta_penetrante"
POSTURA = "talent.sentinela.postura_de_ferro"
VIGILIA = "talent.sentinela.vigilia"
FIO = "talent.errante.fio_perfurante"
PELE = "talent.errante.pele_endurecida"
RITMO = "talent.errante.ritmo_predatorio"


def _battle(
    *,
    character_class="sentinela",
    talents=(),
    hp=ONE_THOUSAND,
    max_hp=ONE_THOUSAND,
    race="remanescente",
    pvp=False,
    enemy_count=1,
    player_attack=HUNDRED,
    player_defense=ZERO,
):
    player = Fighter(
        "player.entity",
        "Player",
        45,
        CombatStats(max_hp, player_attack, player_defense, D(100), D(0), D(0)),
        hp,
        race=race,
        character_class=character_class,
        talent_ids=tuple(talents),
        takes_turn=True,
    )
    fighters = {"player": player}
    for index in range(enemy_count):
        key = f"enemy-{index}"
        fighters[key] = Fighter(
            f"{key}.entity",
            key,
            45,
            CombatStats(D(10000), D(100), D(0), D(1), D(0), D(0)),
            D(10000),
            side="enemy",
            takes_turn=False,
        )
    actions = {
        "attack": Action("attack", "Ataque", D("0.20")),
        "aoe": Action(
            "path_art.errante.ritmo_probe",
            "Ataque em área",
            D("0.20"),
            target_mode="all_opponents",
        ),
    }
    enemy_actions = {
        "hit": Action("enemy.hit", "Golpe", D("0.20")),
    }
    state = Combat(
        uuid4(), CURRENT_COMBAT_RULESET, fighters, actions, enemy_actions, ("hit",),
        pvp_mode=pvp,
    )
    return start_combat(state)


def _event(state, action, target, actor=None):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action
        and event.target == target
        and (actor is None or event.actor_entity_id == actor)
    )


@pytest.mark.parametrize("talent_id", (PONTA, FIO))
def test_tier45_static_precision_is_two_percentage_points(talent_id):
    definition = TALENT_DEFINITIONS[talent_id]
    assert definition.per_points == D(2)
    totals = _static_talent_secondary_modifier_totals((definition,))
    assert totals == (D(2), D(0), D(0), D(0))


@pytest.mark.parametrize(
    ("pvp", "round_number", "race", "talents", "expected_reduction"),
    (
        (False, 1, "remanescente", (), D("0.45")),
        (False, 1, "remanescente", (POSTURA,), D("0.47")),
        (False, 1, "cinereo", (), D("0.52")),
        (False, 1, "cinereo", (POSTURA,), D("0.54")),
        (True, 25, "remanescente", (), D("0.30")),
        (True, 25, "remanescente", (POSTURA,), D("0.32")),
        (True, 25, "cinereo", (), D("0.37")),
        (True, 25, "cinereo", (POSTURA,), D("0.39")),
    ),
)
def test_postura_de_ferro_adds_two_points_only_to_defender_mitigation(
    pvp, round_number, race, talents, expected_reduction
):
    state = _battle(character_class="sentinela", talents=talents, race=race, pvp=pvp)
    state.round = round_number
    target = state.fighters["player"]
    target.defending = True
    assert _perform(state, "enemy-0", "hit", target_id=target.id)
    event = _event(state, "hit", target.id)
    expected = direct_damage(
        D(100), D("0.20"), D(0), 45, mitigation=expected_reduction
    )
    assert event.calculated_damage == expected
    assert event.target_defending


def test_vigilia_triggers_once_on_exact_threshold_crossing_and_not_barrier_damage():
    state = _battle(character_class="sentinela", talents=(VIGILIA,), hp=D(600))
    player = state.fighters["player"]
    _deal_combat_damage(state, "player", D(50), source_key="enemy-0")
    assert not player.path_state.get("vigilia_retaliation_triggered")
    _deal_combat_damage(state, "player", D(50), source_key="enemy-0")
    assert player.hp == D(500)
    assert player.path_state.get("vigilia_retaliation_triggered") is True
    retaliation = (player.retaliation_charges, player.retaliation_remaining)
    for _ in range(3):
        _deal_combat_damage(state, "player", D(10), source_key="enemy-0")
    assert (player.retaliation_charges, player.retaliation_remaining) == retaliation

    shielded = _battle(character_class="sentinela", talents=(VIGILIA,), hp=D(600))
    fighter = shielded.fighters["player"]
    fighter.barrier = D(500)
    fighter.barrier_remaining = 2
    _deal_combat_damage(shielded, "player", D(200), source_key="enemy-0")
    assert fighter.hp == D(600)
    assert not fighter.path_state.get("vigilia_retaliation_triggered")


def test_vigilia_observes_low_hp_at_combat_entry_and_records_one_combat_use():
    initial = _battle(character_class="sentinela", talents=(VIGILIA,), hp=D(500))
    player = initial.fighters["player"]
    assert player.path_state.get("vigilia_retaliation_triggered") is True


def test_pele_endurecida_reduces_only_errante_dot_ticks_by_eight_percent():
    def tick(talents):
        state = _battle(character_class="errante", talents=talents)
        state.order = ("player", "enemy-0")
        state.turn_index = 0
        state.dot_states[state.fighters["player"].id] = [
            DotState("poison", 1, 2, D(100), state.fighters["enemy-0"].id)
        ]
        _end_turn(state)
        event = next(event for event in state.mechanic_events if event.action == "dot:poison:tick")
        return event.calculated_damage

    baseline = tick(())
    protected = tick((PELE,))
    assert baseline > protected > 0
    assert protected == int(
        (D(baseline) * D("0.92")).to_integral_value(rounding="ROUND_FLOOR")
    )


def test_ritmo_predatorio_arms_once_after_action_start_oportunismo():
    debuff = Effect("enemy.weakness", "attack", D("0.10"), 2, 0, kind="debuff")
    state = _battle(character_class="errante", talents=(RITMO,), enemy_count=2)
    for key in ("enemy-0", "enemy-1"):
        state.fighters[key].effects.append(debuff)
    assert _perform(state, "player", "aoe")
    actor = state.fighters["player"]
    buff_id = "class_mechanic.errante.ritmo_predatorio.agility"
    buffs = [effect for effect in actor.effects if effect.id == buff_id]
    assert len(buffs) == 1
    assert buffs[0].magnitude == D("0.05")
    assert buffs[0].remaining == 1
    opportunity_events = [event for event in state.events if event.action == "aoe"]
    assert len(opportunity_events) == 2
    assert all(event.path_final_damage_bonus == D("0.08") for event in opportunity_events)


def test_ritmo_predatorio_does_not_trigger_from_debuff_created_by_same_action():
    state = _battle(character_class="errante", talents=(RITMO,))
    action_id = "path_art.errante.ritmo_probe"
    state.player_actions[action_id] = Action(
        action_id,
        "Aplica debuff",
        D("0.20"),
        target_effects=(
            # The effect is created after the action-start Oportunismo snapshot.
            ActionEffect("enemy.new_slow", "agility", D("0.10"), 2, "debuff"),
        ),
    )
    assert _perform(state, "player", action_id, target_id="enemy-0")
    assert not any(
        effect.id == "class_mechanic.errante.ritmo_predatorio.agility"
        for effect in state.fighters["player"].effects
    )
