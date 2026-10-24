from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import (
    Action,
    _deal_combat_damage,
    _perform,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(character_class: str, path: str | None = None):
    state = PROFILE.create(
        UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5"),
        "Teste",
        character_class,
        "remanescente",
        D(1000),
    )
    state.tutorial = None
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
    state.ruleset = CURRENT_COMBAT_RULESET
    state.player_actions = {
        "attack": Action("attack", "Ataque Básico", D(1)),
        "art": Action("class_art.test", "Arte de Teste", D(1)),
    }
    state.enemy_actions = {
        "hit": Action("enemy.hit", "Golpe", D(1)),
        "debuff": Action(
            "enemy.debuff",
            "Debuff",
            D(0),
            attack_debuff=D("0.20"),
            duration=2,
        ),
    }
    state.ai_cycle = ("hit",)
    return state


def _last_event(state, action: str):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action and event.target
    )


def test_punicao_final_uses_inclusive_action_start_target_hp_and_only_direct_damage():
    state = _battle("sentinela", "bastiao")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.sentinela.punicao_final",)
    target = state.fighters["enemy"]
    target.hp = D(400)
    assert _perform(state, "player", "art", target_id="enemy")
    assert _last_event(state, "art").path_power_multiplier == D("1.04")

    above = _battle("sentinela")
    above.fighters["player"].talent_ids = actor.talent_ids
    above.fighters["enemy"].hp = D("400.01")
    assert _perform(above, "player", "art", target_id="enemy")
    assert _last_event(above, "art").path_power_multiplier == D(1)


def test_fim_proximo_is_independent_of_oportunismo_and_uses_inclusive_35_percent():
    state = _battle("errante", "carrasco")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.errante.fim_proximo",)
    state.fighters["enemy"].hp = D(350)
    assert _perform(state, "player", "art", target_id="enemy")
    assert _last_event(state, "art").path_power_multiplier == D("1.04")

    above = _battle("errante")
    above.fighters["player"].talent_ids = actor.talent_ids
    above.fighters["enemy"].hp = D("350.01")
    assert _perform(above, "player", "art", target_id="enemy")
    assert _last_event(above, "art").path_power_multiplier == D(1)


def test_persistencia_is_live_defense_at_inclusive_35_percent_and_reversible():
    state = _battle("sentinela")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.sentinela.persistencia",)
    actor.hp = D(350)
    assert actor.stat("defense") == D(107)
    actor.hp = D(351)
    assert actor.stat("defense") == D(100)
    actor.hp = D(300)
    assert actor.stat("defense") == D(107)


def test_guarda_integra_arms_after_defend_and_reduces_only_next_removable_debuff():
    state = _battle("sentinela")
    sentinel = state.fighters["player"]
    sentinel.talent_ids = ("talent.sentinela.guarda_integra",)
    assert _perform(state, "player", "defend")
    assert state.fighters["player"].path_state["guard_integrity_debuff"][
        "combat_id"
    ] == str(state.id)
    assert _perform(state, "enemy", "debuff", target_id="player")
    first = next(effect for effect in sentinel.effects if effect.id == "enemy.debuff")
    assert first.magnitude == D("0.18")
    assert "guard_integrity_debuff" not in sentinel.path_state

    assert _perform(state, "enemy", "debuff", target_id="player")
    effects = [effect for effect in sentinel.effects if effect.id == "enemy.debuff"]
    assert effects[-1].magnitude == D("0.20")


def test_primeiro_desvio_reduces_only_first_positive_direct_component_before_barrier():
    baseline = _battle("errante")
    assert _perform(baseline, "enemy", "hit", target_id="player")
    unprotected_damage = _last_event(baseline, "hit").damage

    state = _battle("errante")
    target = state.fighters["player"]
    target.talent_ids = ("talent.errante.primeiro_desvio",)
    assert _perform(state, "enemy", "hit", target_id="player")
    first = _last_event(state, "hit")
    assert first.damage < unprotected_damage
    assert target.path_state["errante_primeiro_desvio_used"] == str(state.id)
    first_hp = target.hp

    assert _perform(state, "enemy", "hit", target_id="player")
    second = _last_event(state, "hit")
    assert second.damage == unprotected_damage
    assert target.hp == first_hp - second.effective_damage


def test_instinto_de_fuga_is_one_combat_trigger_and_adds_percentage_points():
    state = _battle("errante")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.errante.instinto_de_fuga",)
    _deal_combat_damage(state, "player", D(700), source_key="enemy")
    assert actor.hp == D(300)
    assert actor.stat("evasion") == D(10)
    trigger = next(
        effect
        for effect in actor.effects
        if effect.id == "class_mechanic.errante.instinto_de_fuga.evasion"
    )
    assert trigger.stat_modifier_mode == "percentage_points"
    actor.hp = D(500)
    _deal_combat_damage(state, "player", D(300), source_key="enemy")
    assert actor.stat("evasion") == D(10)
    assert actor.path_state["errante_instinto_de_fuga_used"] == str(state.id)

    resumed = decode(encode(state), state.id, state.ruleset, state.version)
    resumed_actor = resumed.fighters["player"]
    assert resumed_actor.path_state["errante_instinto_de_fuga_used"] == str(state.id)
    assert resumed_actor.stat("evasion") == D(10)


def test_instinto_de_fuga_arms_on_first_combat_observation_at_low_hp():
    state = _battle("errante")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.errante.instinto_de_fuga",)
    actor.hp = D(300)
    from asterion.domain.combat import _begin_turn

    _begin_turn(state)
    assert actor.stat("evasion") == D(10)
