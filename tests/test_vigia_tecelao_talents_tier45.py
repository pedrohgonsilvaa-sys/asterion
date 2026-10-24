from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.domain.combat import (
    Action,
    ActionEffect,
    Combat,
    CombatStats,
    DotState,
    Effect,
    Fighter,
    _end_turn,
    _perform,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
HUNDRED = D(100)
TEN_THOUSAND = D(10000)

PONTO_FRACO = "talent.vigia.ponto_fraco"
COURO_DE_CAMPO = "talent.vigia.couro_de_campo"
LEITURA_DE_MOVIMENTO = "talent.vigia.leitura_de_movimento"
RUPTURA_PROFUNDA = "talent.tecelao.ruptura_profunda"
TECELAGEM_DEFENSIVA = "talent.tecelao.tecelagem_defensiva"
ECO_DE_ALTERNANCIA = "talent.tecelao.eco_de_alternancia"
TRAMA_AGRESSIVA = "talent.tecelao.trama_agressiva"


def _battle(*, character_class, path=None, talents=(), enemy_count=2):
    player = Fighter(
        "player.entity",
        "Player",
        45,
        CombatStats(HUNDRED * 10, HUNDRED, ZERO, HUNDRED, ZERO, ZERO),
        HUNDRED * 10,
        character_class=character_class,
        selected_path=path,
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
            CombatStats(TEN_THOUSAND, HUNDRED, ZERO, D(1), ZERO, ZERO),
            TEN_THOUSAND,
            side="enemy",
            takes_turn=False,
        )
    actions = {
        "attack": Action("attack", "Ataque", D("0.20")),
        "sweep": Action(
            "class_art.vigia.sweep_probe",
            "Varredura",
            D("0.20"),
            target_mode="all_opponents",
        ),
        "slow": Action(
            "path_art.vigia.laco_de_caca",
            "Laço de Caça",
            D("0.20"),
            target_effects=(
                ActionEffect("enemy.agility_slow", "agility", D("0.20"), 2, "debuff"),
            ),
        ),
        "direct_a": Action(
            "path_art.tecelao.direct_a", "Trama A", D("0.20")
        ),
        "direct_b": Action(
            "path_art.tecelao.direct_b", "Trama B", D("0.20")
        ),
        "utility": Action(
            "class_art.tecelao.utility_probe",
            "Utilidade",
            ZERO,
            target_mode="self",
            self_effects=(ActionEffect("self.focus", "agility", D("0.01"), 1),),
        ),
        "barrier": Action(
            "path_art.tecelao.barrier_probe",
            "Barreira própria",
            ZERO,
            target_mode="self",
            self_barrier_coefficient=D("0.50"),
            self_barrier_duration=2,
        ),
    }
    state = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        fighters,
        actions,
        {"hit": Action("enemy.hit", "Golpe", D("0.20"))},
        ("hit",),
    )
    return start_combat(state)


def _event(state, action, target_id):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action and event.target == target_id
    )


def _set_aim(state, target_key, stacks, *, remaining=2):
    source = state.fighters["player"]
    state.fighters[target_key].path_state.setdefault("aim_from", {})[
        source.id
    ] = {
        "stacks": stacks,
        "remaining": remaining,
        "applied_opportunity": source.opportunity,
        "trigger": "direct",
    }


@pytest.mark.parametrize(
    ("stacks", "expected", "after_stacks"),
    ((2, ZERO, 3), (3, D(2), 4), (4, D(8), 4)),
)
def test_ponto_fraco_adds_two_crit_points_at_three_valid_miras(
    stacks, expected, after_stacks
):
    state = _battle(
        character_class="vigia",
        path="atirador",
        talents=(PONTO_FRACO,),
        enemy_count=1,
    )
    _set_aim(state, "enemy-0", stacks)
    assert _perform(state, "player", "attack", target_id="enemy-0")
    event = _event(state, "attack", "enemy-0.entity")
    assert event.path_crit_bonus == expected
    assert (
        state.fighters["enemy-0"].path_state["aim_from"]["player.entity"]["stacks"]
        == after_stacks
    )


def test_ponto_fraco_ignores_expired_mira():
    state = _battle(
        character_class="vigia",
        path="atirador",
        talents=(PONTO_FRACO,),
        enemy_count=1,
    )
    _set_aim(state, "enemy-0", 4, remaining=0)
    assert _perform(state, "player", "attack", target_id="enemy-0")
    assert _event(state, "attack", "enemy-0.entity").path_crit_bonus == ZERO


def test_couro_de_campo_reduces_dot_ticks_not_direct_damage():
    def tick(talents):
        state = _battle(character_class="vigia", talents=talents, enemy_count=1)
        state.order = ("player", "enemy-0")
        state.turn_index = 0
        player = state.fighters["player"]
        state.dot_states[player.id] = [
            DotState("poison", 1, 2, HUNDRED, state.fighters["enemy-0"].id)
        ]
        _end_turn(state)
        return next(
            event.calculated_damage
            for event in state.mechanic_events
            if event.action == "dot:poison:tick"
        )

    assert tick((COURO_DE_CAMPO,)) == int(
        (D(tick(())) * D("0.92")).to_integral_value(rounding="ROUND_FLOOR")
    )


def test_leitura_de_movimento_triggers_only_after_successful_agility_debuff():
    state = _battle(
        character_class="vigia",
        path="rastreador",
        talents=(LEITURA_DE_MOVIMENTO,),
        enemy_count=1,
    )
    assert _perform(state, "player", "slow", target_id="enemy-0")
    buff_id = "class_mechanic.vigia.leitura_de_movimento.agility"
    assert any(effect.id == buff_id for effect in state.fighters["player"].effects)

    blocked = _battle(
        character_class="vigia",
        path="rastreador",
        talents=(LEITURA_DE_MOVIMENTO,),
        enemy_count=1,
    )
    blocked.fighters["enemy-0"].ward_charges = 1
    blocked.fighters["enemy-0"].ward_remaining = 2
    assert _perform(blocked, "player", "slow", target_id="enemy-0")
    assert not any(effect.id == buff_id for effect in blocked.fighters["player"].effects)


def test_ruptura_profunda_is_three_percent_per_target_from_action_start_dot_snapshot():
    state = _battle(
        character_class="tecelao",
        path="conjurador",
        talents=(RUPTURA_PROFUNDA,),
    )
    state.dot_states[state.fighters["enemy-0"].id] = [
        DotState("bleed", 1, 2, HUNDRED, state.fighters["player"].id)
    ]
    state.fighters["enemy-1"].effects.append(
        Effect("enemy.attack_down", "attack", D("0.10"), 2, 0, kind="debuff")
    )
    assert _perform(state, "player", "sweep")
    dot_target = _event(state, "sweep", "enemy-0.entity")
    debuff_only_target = _event(state, "sweep", "enemy-1.entity")
    assert dot_target.path_power_multiplier == D("1.03")
    assert "tecelao.ruptura_profunda" in dot_target.path_triggers
    assert debuff_only_target.path_power_multiplier == D(1)
    assert "tecelao.ruptura_profunda" not in debuff_only_target.path_triggers


def test_tecelagem_defensiva_scales_only_first_positive_barrier_action_and_codec():
    state = _battle(
        character_class="tecelao",
        path="runico",
        talents=(TECELAGEM_DEFENSIVA,),
        enemy_count=1,
    )
    assert _perform(state, "player", "barrier")
    first = _event(state, "barrier", "player.entity")
    assert first.barrier_value == D(55)
    marker = state.fighters["player"].path_state["tecelao_defensive_barrier_used"]
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state[
        "tecelao_defensive_barrier_used"
    ] == marker

    assert _perform(state, "player", "barrier")
    second = _event(state, "barrier", "player.entity")
    assert second.barrier_value == D(50)


def test_eco_de_alternancia_preparation_applies_and_is_consumed_with_next_trama_spend():
    state = _battle(
        character_class="tecelao",
        path="conjurador",
        talents=(ECO_DE_ALTERNANCIA, TRAMA_AGRESSIVA),
        enemy_count=1,
    )
    assert _perform(state, "player", "direct_a", target_id="enemy-0")
    assert isinstance(state.fighters["player"].path_state.get("trama_state"), dict)
    assert _perform(state, "player", "direct_b", target_id="enemy-0")
    assert state.fighters["player"].path_state["trama_next_per"]["magnitude"] == 3
    first_preparation = state.fighters["player"].path_state["trama_next_per"][
        "source_action_instance_id"
    ]
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state["trama_next_per"][
        "source_action_instance_id"
    ] == first_preparation

    # A utility Arte lets the actor generate a fresh Trama without spending the
    # pending "next offensive" precision. The following hit legitimately spends
    # both states in one committed action.
    assert _perform(state, "player", "utility")
    assert isinstance(state.fighters["player"].path_state.get("trama_state"), dict)
    assert isinstance(state.fighters["player"].path_state.get("trama_next_per"), dict)
    assert _perform(state, "player", "direct_a", target_id="enemy-0")
    event = _event(state, "direct_a", "enemy-0.entity")
    assert event.path_per_bonus == D(3)
    assert "tecelao.proximo_dano_consumido" in event.path_triggers
    new_preparation = state.fighters["player"].path_state["trama_next_per"]
    assert new_preparation["source_action_instance_id"] == event.action_instance_id
    assert "trama_state" not in state.fighters["player"].path_state
