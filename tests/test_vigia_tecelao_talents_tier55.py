from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.arts import ATIRADOR_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, _begin_turn, _deal_combat_damage, _perform
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TalentSelectionError,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(character_class: str, path: str | None = None):
    state = PROFILE.create(
        UUID("94554639-3451-4508-972b-8cb1121f29f7"),
        "Teste",
        character_class,
        "remanescente",
        D(1000),
    )
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    actor = state.fighters["player"]
    actor.selected_path = path
    actor.stats = replace(
        actor.stats,
        hp=D(1000),
        attack=D(100),
        defense=D(100),
        agility=D(100),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    actor.hp = D(1000)
    enemy = state.fighters["enemy"]
    enemy.stats = replace(
        enemy.stats,
        hp=D(1000),
        attack=D(100),
        defense=D(0),
        agility=D(0),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    enemy.hp = D(1000)
    enemy.side = "enemy"
    state.player_actions = {
        "attack": Action("attack", "Ataque Básico", D(1)),
        "art": Action("class_art.test", "Arte de Teste", D(1)),
        "barrier": Action(
            "class_art.tecelao.barrier",
            "Barreira de Teste",
            D(0),
            target_mode="self",
            self_barrier_coefficient=D(1),
            self_barrier_duration=2,
        ),
    }
    state.enemy_actions = {"hit": Action("enemy.hit", "Golpe", D(1))}
    state.ai_cycle = ("hit",)
    return state


def _event(state, action: str):
    return next(event for event in reversed(state.events) if event.action == action)


def test_nv55_effects_are_internal_while_public_gate_remains_closed():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    for talent_id in (
        "talent.vigia.disparo_implacavel",
        "talent.vigia.ultimo_horizonte",
        "talent.vigia.cacada_metodica",
        "talent.tecelao.sobrecarga_controlada",
        "talent.tecelao.veu_de_emergencia",
        "talent.tecelao.trama_precisa",
    ):
        character_class = talent_id.split(".")[1]
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids(character_class, 55, (talent_id,))


@pytest.mark.parametrize(
    ("character_class", "talent", "threshold"),
    (("vigia", "disparo_implacavel", D("0.35")),),
)
def test_low_hp_direct_talents_use_inclusive_target_snapshot(
    character_class, talent, threshold
):
    state = _battle(character_class)
    state.fighters["player"].talent_ids = (f"talent.{character_class}.{talent}",)
    state.fighters["enemy"].hp = D(1000) * threshold

    assert _perform(state, "player", "art", target_id="enemy")
    assert _event(state, "art").path_power_multiplier == D("1.04")

    above = _battle(character_class)
    above.fighters["player"].talent_ids = (
        f"talent.{character_class}.{talent}",
    )
    above.fighters["enemy"].hp = D(1000) * threshold + D("0.01")
    assert _perform(above, "player", "art", target_id="enemy")
    assert _event(above, "art").path_power_multiplier == D(1)


def test_ultimo_horizonte_is_live_defense_and_reverses_after_healing():
    state = _battle("vigia", "atirador")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.vigia.ultimo_horizonte",)

    actor.hp = D("350.01")
    assert actor.stat("defense") == D(100)
    actor.hp = D(350)
    assert actor.stat("defense") == D(106)
    actor.hp = D("349.99")
    assert actor.stat("defense") == D(106)
    actor.hp = D(351)
    assert actor.stat("defense") == D(100)


@pytest.mark.parametrize(
    ("path", "maximum"), (("atirador", 4), ("rastreador", 2), (None, 3))
)
def test_cacada_metodica_uses_path_max_mira_snapshot_once_per_action(path, maximum):
    state = _battle("vigia", path)
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.vigia.cacada_metodica",)
    target = state.fighters["enemy"]
    target.path_state["aim_from"] = {
        "player": {
            "stacks": maximum,
            "remaining": 2,
            "applied_opportunity": target.opportunity,
        }
    }

    assert _perform(state, "player", "attack", target_id="enemy")
    assert actor.path_state["aim_next_per"]["magnitude"] == 3

    assert _perform(state, "player", "attack", target_id="enemy")
    expected_per = D(15) if path == "atirador" else D(3)
    assert _event(state, "attack").path_per_bonus == expected_per


def test_cacada_metodica_does_not_prepare_when_hit_only_reaches_mira_cap():
    state = _battle("vigia", "atirador")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.vigia.cacada_metodica",)
    state.fighters["enemy"].path_state["aim_from"] = {
        "player": {"stacks": 3, "remaining": 2, "applied_opportunity": 0}
    }

    assert _perform(state, "player", "attack", target_id="enemy")

    assert "aim_next_per" not in actor.path_state


def test_cacada_metodica_uses_four_mira_before_disparo_terminal_consumes_them():
    state = _battle("vigia", "atirador")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.vigia.cacada_metodica",)
    art_id = ATIRADOR_ART_IDS["disparo_terminal"]
    state.player_actions.update(
        class_player_actions("vigia", (art_id,), selected_path="atirador")
    )
    state.fighters["enemy"].path_state["aim_from"] = {
        "player": {"stacks": 4, "remaining": 2, "applied_opportunity": 0}
    }

    assert _perform(state, "player", art_id, target_id="enemy")

    assert "aim_from" not in state.fighters["enemy"].path_state
    assert actor.path_state["aim_next_per"]["magnitude"] == 3
    assert _event(state, art_id).path_crit_bonus == D(21)


@pytest.mark.parametrize(
    ("path", "target_hp", "talents", "expected"),
    (
        ("conjurador", D(400), ("sobrecarga_controlada", "trama_agressiva"), D("1.2168")),
        ("conjurador", D(400), ("sobrecarga_controlada",), D("1.196")),
        ("conjurador", D("400.01"), ("sobrecarga_controlada",), D("1.15")),
        ("runico", D(400), ("sobrecarga_controlada",), D("1.1024")),
    ),
)
def test_sobrecarga_controlada_multiplies_consumed_trama_power_relatively(
    path, target_hp, talents, expected
):
    state = _battle("tecelao", path)
    actor = state.fighters["player"]
    actor.talent_ids = tuple(f"talent.tecelao.{slug}" for slug in talents)
    actor.path_state["trama_state"] = {
        "origin_art": "class_art.tecelao.other",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    state.fighters["enemy"].hp = target_hp

    assert _perform(state, "player", "art", target_id="enemy")

    assert _event(state, "art").path_power_multiplier == expected
    assert "trama_state" not in actor.path_state


def test_trama_precisa_defensive_power_is_relative_after_path_consumption():
    state = _battle("tecelao", "runico")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.tecelao.trama_precisa",)
    actor.path_state["trama_state"] = {
        "origin_art": "class_art.tecelao.other",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    assert _perform(state, "player", "barrier")

    event = _event(state, "barrier")
    assert event.barrier_power_multiplier == D("1.173")
    assert event.class_resource_changes == (("trama", "player", 1, 0),)


@pytest.mark.parametrize(
    ("character_class", "talent", "marker", "source"),
    (
        (
            "tecelao",
            "veu_de_emergencia",
            "tecelao_veu_de_emergencia_used",
            "class_mechanic.tecelao.veu_de_emergencia.barrier",
        ),
    ),
)
def test_emergency_barrier_triggers_once_at_inclusive_threshold_and_survives_codec(
    character_class, talent, marker, source
):
    state = _battle(character_class)
    actor = state.fighters["player"]
    actor.talent_ids = (f"talent.{character_class}.{talent}",)
    _deal_combat_damage(state, "player", D(700), source_key="enemy")

    assert actor.hp == D(300)
    assert actor.barrier == D(60)
    barrier = next(
        layer for layer in actor.barrier_layers if layer.effect_definition_id == source
    )
    assert barrier.remaining == 1
    assert actor.path_state[marker] == str(state.id)

    resumed = decode(encode(state), state.id, state.ruleset, state.version)
    resumed_actor = resumed.fighters["player"]
    assert resumed_actor.barrier == D(60)
    assert resumed_actor.path_state[marker] == str(state.id)
    resumed_actor.hp = D(500)
    _deal_combat_damage(resumed, "player", D(260), source_key="enemy")
    assert resumed_actor.hp == D(300)
    assert resumed_actor.barrier == D(0)
    assert not any(
        layer.effect_definition_id == source for layer in resumed_actor.barrier_layers
    )


def test_veu_de_emergencia_observes_low_hp_at_combat_start():
    state = _battle("tecelao")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.tecelao.veu_de_emergencia",)
    actor.hp = D(300)

    _begin_turn(state)

    assert actor.barrier == D(60)
    assert actor.path_state["tecelao_veu_de_emergencia_used"] == str(state.id)
