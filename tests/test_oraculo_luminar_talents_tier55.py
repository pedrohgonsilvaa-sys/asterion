from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.combat import Action, _begin_turn, _deal_combat_damage, _perform
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import IMPLEMENTED_TALENT_LEVELS, validate_active_talent_ids
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(character_class: str, path: str | None = None):
    state = PROFILE.create(
        UUID("4d64caf2-9c1c-4717-a1d7-987046bd1130"),
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
        "art": Action("class_art.test", "Arte de Teste", D(1)),
        "barrier": Action(
            "class_art.oraculo.barrier",
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


def test_nv55_oraculo_and_luminar_effects_are_supported_by_public_gate():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    for character_class, slugs in (
        ("oraculo", ("fim_anunciado", "ultima_visao", "sinais_convergentes")),
        ("luminar", ("sentenca_solar", "ultimo_alvorecer", "contraluz_perfeita")),
    ):
        for slug in slugs:
            talent_id = f"talent.{character_class}.{slug}"
            assert validate_active_talent_ids(character_class, 55, (talent_id,)) == (talent_id,)


@pytest.mark.parametrize(
    ("character_class", "talent"),
    (("oraculo", "fim_anunciado"), ("luminar", "sentenca_solar")),
)
def test_finisher_talents_apply_direct_power_at_inclusive_35_percent_snapshot(
    character_class, talent
):
    state = _battle(character_class)
    state.fighters["player"].talent_ids = (f"talent.{character_class}.{talent}",)
    state.fighters["enemy"].hp = D(350)

    assert _perform(state, "player", "art", target_id="enemy")
    assert _event(state, "art").path_power_multiplier == D("1.04")

    above = _battle(character_class)
    above.fighters["player"].talent_ids = (
        f"talent.{character_class}.{talent}",
    )
    above.fighters["enemy"].hp = D("350.01")
    assert _perform(above, "player", "art", target_id="enemy")
    assert _event(above, "art").path_power_multiplier == D(1)


def test_ultima_visao_is_one_combat_barrier_without_creating_defensive_omen():
    state = _battle("oraculo")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.oraculo.ultima_visao",)
    _deal_combat_damage(state, "player", D(700), source_key="enemy")

    assert actor.hp == D(300)
    assert actor.barrier == D(60)
    assert actor.path_state["oraculo_ultima_visao_used"] == str(state.id)
    assert "omen_defensive" not in actor.path_state

    resumed = decode(encode(state), state.id, state.ruleset, state.version)
    target = resumed.fighters["player"]
    assert target.barrier == D(60)
    assert target.path_state["oraculo_ultima_visao_used"] == str(state.id)
    target.hp = D(500)
    _deal_combat_damage(resumed, "player", D(260), source_key="enemy")
    assert target.hp == D(300)
    assert target.barrier == D(0)


def test_ultima_visao_observes_low_hp_at_combat_start():
    state = _battle("oraculo")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.oraculo.ultima_visao",)
    actor.hp = D(300)

    _begin_turn(state)

    assert actor.barrier == D(60)
    assert actor.path_state["oraculo_ultima_visao_used"] == str(state.id)


def test_ultimo_alvorecer_is_restricted_non_triggering_heal_and_one_combat_use():
    state = _battle("luminar", "guardiao")
    actor = state.fighters["player"]
    actor.talent_ids = (
        "talent.luminar.ultimo_alvorecer",
        "talent.luminar.fluxo_restaurador",
        "talent.luminar.cura_prudente",
    )
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    actor.hp = D(350)

    _deal_combat_damage(state, "player", D(50), source_key="enemy")

    assert actor.hp == D(350)
    assert actor.path_state["luminar_state"]["kind"] == "fulgor"
    assert actor.path_state["luminar_ultimo_alvorecer_used"] == str(state.id)
    assert not any("fluxo_restaurador" in effect.id for effect in actor.effects)
    assert not any("cura_prudente" in effect.id for effect in actor.effects)
    heal_events = [
        event
        for event in state.mechanic_events
        if event.effect_id == "class_mechanic.luminar.ultimo_alvorecer.heal"
    ]
    assert len(heal_events) == 1 and heal_events[0].healed == D(50)

    resumed = decode(encode(state), state.id, state.ruleset, state.version)
    resumed_actor = resumed.fighters["player"]
    assert resumed_actor.path_state["luminar_ultimo_alvorecer_used"] == str(state.id)
    resumed_actor.hp = D(500)
    _deal_combat_damage(resumed, "player", D(250), source_key="enemy")
    assert resumed_actor.hp == D(250)
    assert len(
        [
            event
            for event in resumed.mechanic_events
            if event.effect_id == "class_mechanic.luminar.ultimo_alvorecer.heal"
        ]
    ) == 1


def test_ultimo_alvorecer_does_not_resurrect_when_threshold_crossing_is_lethal():
    state = _battle("luminar")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.luminar.ultimo_alvorecer",)
    actor.hp = D(30)

    _deal_combat_damage(state, "player", D(30), source_key="enemy")

    assert actor.hp == D(0)
    assert actor.path_state["luminar_ultimo_alvorecer_used"] == str(state.id)


def test_sinais_convergentes_splits_offensive_and_defensive_consumption():
    offensive = _battle("oraculo", "agoureiro")
    actor = offensive.fighters["player"]
    actor.talent_ids = ("talent.oraculo.sinais_convergentes",)
    actor.path_state["omen_offensive"] = {
        "enemy": {"remaining": 2, "applied_opportunity": actor.opportunity}
    }

    assert _perform(offensive, "player", "art", target_id="enemy")
    attack_event = _event(offensive, "art")
    assert attack_event.path_crit_bonus == D(2)
    assert "pressagio.ofensivo_consumido" in attack_event.path_triggers

    defensive = _battle("oraculo", "invocador")
    actor = defensive.fighters["player"]
    actor.talent_ids = ("talent.oraculo.sinais_convergentes",)
    actor.path_state["omen_defensive"] = {
        actor.id: {"remaining": 2, "applied_opportunity": actor.opportunity}
    }

    assert _perform(defensive, "player", "barrier")
    barrier_event = _event(defensive, "barrier")
    assert barrier_event.barrier_power_multiplier == D("1.1536")
    assert "pressagio.defensivo_consumido" in barrier_event.path_triggers
