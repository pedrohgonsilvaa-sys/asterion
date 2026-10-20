from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import (
    Action,
    ActionCondition,
    ActionConditionalModifier,
    ActionEffect,
    ActionResourceUse,
    DotState,
    Effect,
    _begin_turn,
    _clear_class_mechanics_for_death,
    _deal_combat_damage,
    _finish_combat,
    _grant_aim,
    _grant_retaliation,
    _perform,
    _tick_path_resources,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)


def _battle(character_class: str, selected_path: str | None = None):
    stats = resolve_combat_stats(character_class, 10, "remanescente")
    state = PROFILE.create(
        UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5"),
        "Teste",
        character_class,
        "remanescente",
        stats.hp,
    )
    state.tutorial = None
    player = state.fighters["player"]
    player.selected_path = selected_path
    player.stats = replace(
        player.stats,
        hp=D(1000),
        attack=D(100),
        defense=D(0),
        agility=D(100),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    player.hp = D(1000)
    enemy = state.fighters["enemy"]
    enemy.stats = replace(
        enemy.stats,
        hp=D(10000),
        attack=D(100),
        defense=D(100),
        agility=D(0),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    enemy.hp = D(10000)
    enemy.side = "enemy"
    state.ruleset = CURRENT_COMBAT_RULESET
    state.player_actions = {
        "attack": Action("attack", "Ataque Básico", D(1)),
        "art": Action("class_art.test", "Arte de Teste", D(1)),
    }
    state.enemy_actions = {"hit": Action("enemy.test", "Golpe", D(1))}
    state.ai_cycle = ("hit",)
    return state


def _add_enemy(state, fighter_id: str):
    state.fighters[fighter_id] = replace(
        state.fighters["enemy"],
        id=fighter_id,
        name=fighter_id,
        hp=D(10000),
        effects=[],
        cooldowns={},
        action_chains={},
        path_state={},
        action_use_counts={},
        side="enemy",
    )
    return state.fighters[fighter_id]


def _last_event(state, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.actor == "player" and event.action == action_id and event.target
    )


def _grant_retaliation_to_player(state):
    _grant_retaliation(
        state,
        target_key="player",
        source_actor=state.fighters["enemy"],
        source_event_id="test:defender",
    )


def test_vigilia_triggers_once_on_threshold_crossing_and_on_initial_low_hp():
    state = _battle("sentinela")
    sentinel = state.fighters["player"]
    sentinel.talent_ids = ("talent.sentinela.vigilia",)
    sentinel.hp = D(550)
    _deal_combat_damage(state, "player", D(100), source_key="enemy")
    assert sentinel.retaliation_charges == 1
    assert sentinel.path_state["vigilia_retaliation_triggered"] is True

    assert _perform(state, "player", "attack", target_id="enemy")
    assert sentinel.retaliation_charges == 0
    _deal_combat_damage(state, "player", D(100), source_key="enemy")
    assert sentinel.retaliation_charges == 0

    initial = _battle("sentinela")
    initial.fighters["player"].talent_ids = ("talent.sentinela.vigilia",)
    initial.fighters["player"].hp = D(450)
    _begin_turn(initial)
    assert initial.fighters["player"].retaliation_charges == 1


def test_retaliacao_persistente_renews_one_capped_charge_and_guarda_integra():
    state = _battle("sentinela")
    sentinel = state.fighters["player"]
    sentinel.talent_ids = (
        "talent.sentinela.retaliacao_persistente",
        "talent.sentinela.guarda_integra",
    )
    _grant_retaliation_to_player(state)
    _grant_retaliation_to_player(state)
    assert sentinel.retaliation_charges == 1
    assert sentinel.retaliation_remaining == 2

    sentinel.defending = True
    assert _perform(state, "enemy", "hit", target_id="player")
    assert "guard_integrity_debuff" in sentinel.path_state
    state.enemy_actions["debuff"] = Action(
        "enemy.debuff",
        "Golpe e Debuff",
        D(0),
        attack_debuff=D("0.10"),
        duration=2,
    )
    assert _perform(state, "enemy", "debuff", target_id="player")
    reduced = next(effect for effect in sentinel.effects if effect.id == "enemy.debuff")
    assert reduced.magnitude == D("0.09")
    assert "guard_integrity_debuff" not in sentinel.path_state


def test_retaliacao_does_not_consume_on_ally_target_and_multi_hit_consumes_once():
    state = _battle("sentinela")
    _grant_retaliation_to_player(state)
    state.player_actions["ally_hit"] = Action(
        "class_art.sentinela.ally_hit",
        "Golpe aliado inválido",
        D(1),
        target_mode="ally",
    )
    assert _perform(state, "player", "ally_hit", target_id="player")
    assert state.fighters["player"].retaliation_charges == 1

    state.player_actions["multi"] = Action(
        "class_art.sentinela.multi",
        "Golpes",
        D("0.20"),
        hit_count=3,
    )
    assert _perform(state, "player", "multi", target_id="enemy")
    assert state.fighters["player"].retaliation_charges == 0
    consumed = [event for event in state.mechanic_events if event.retaliation_event == "consumed"]
    assert len(consumed) == 1
    hit_events = [event for event in state.events if event.action == "multi"]
    assert len(hit_events) == 3
    assert all(event.retaliation_used for event in hit_events)


def test_oportunismo_snapshots_normal_negative_effects_and_does_not_retroactively_enable():
    state = _battle("errante")
    state.player_actions["art"] = Action(
        "class_art.errante.test",
        "Golpe que prepara",
        D("0.50"),
        attack_debuff=D("0.10"),
        duration=2,
    )
    assert _perform(state, "player", "art", target_id="enemy")
    first = _last_event(state, "art")
    assert first.path_final_damage_bonus == ZERO
    assert any(effect.kind == "debuff" for effect in state.fighters["enemy"].effects)

    assert _perform(state, "player", "art", target_id="enemy")
    assert _last_event(state, "art").path_final_damage_bonus == D("0.08")

    fixed = _battle("errante")
    fixed.fighters["enemy"].effects.append(
        Effect(
            "fixed.mark",
            "attack",
            D("0.10"),
            2,
            0,
            kind="debuff",
            fixed_mechanic=True,
        )
    )
    assert _perform(fixed, "player", "attack", target_id="enemy")
    assert _last_event(fixed, "attack").path_final_damage_bonus == ZERO

    dot = _battle("errante")
    dot.dot_states["enemy"] = [DotState("poison", 1, 2, D(20), "player")]
    assert _perform(dot, "player", "attack", target_id="enemy")
    assert _last_event(dot, "attack").path_final_damage_bonus == D("0.08")


def test_oportunismo_talents_and_aoe_are_resolved_per_target_once_per_action():
    state = _battle("errante")
    actor = state.fighters["player"]
    actor.talent_ids = (
        "talent.errante.oportunismo_ampliado",
        "talent.errante.brecha_exposta",
        "talent.errante.ritmo_predatorio",
    )
    state.fighters["enemy"].effects.append(
        Effect("slow", "agility", D("0.10"), 2, 0, kind="debuff", removable=False)
    )
    _add_enemy(state, "enemy-2")
    state.player_actions["aoe"] = Action(
        "class_art.errante.aoe", "Área", D("0.20"), target_mode="all_opponents"
    )
    assert _perform(state, "player", "aoe")
    events = [event for event in state.events if event.action == "aoe"]
    by_target = {event.target: event for event in events}
    assert by_target["enemy"].path_final_damage_bonus == D("0.10")
    assert by_target["enemy"].path_per_bonus == D(4)
    assert by_target["enemy-2"].path_final_damage_bonus == ZERO
    assert actor.effects[-1].id == "class_mechanic.errante.ritmo_predatorio.agility"

    multi = _battle("errante")
    multi.player_actions["multi"] = Action(
        "class_art.errante.multi",
        "Multi-hit que aplica Debuff",
        D("0.20"),
        attack_debuff=D("0.10"),
        duration=2,
        hit_count=2,
    )
    assert _perform(multi, "player", "multi", target_id="enemy")
    assert all(
        event.path_final_damage_bonus == ZERO
        for event in multi.events
        if event.action == "multi"
    )


def test_mira_ticks_by_vigia_and_generates_through_barrier_not_miss():
    state = _battle("vigia")
    actor = state.fighters["player"]
    actor.opportunity = 4
    target = state.fighters["enemy"]
    target.opportunity = 40
    assert _grant_aim(state, "player", "enemy", trigger="direct") == 1
    _tick_path_resources(state, "player")
    assert target.path_state["aim_from"]["player"]["remaining"] == 2
    actor.opportunity += 1
    _tick_path_resources(state, "player")
    assert target.path_state["aim_from"]["player"]["remaining"] == 1

    barrier = _battle("vigia")
    barrier.fighters["enemy"].barrier = D(10000)
    barrier.fighters["enemy"].barrier_remaining = 2
    assert _perform(barrier, "player", "attack", target_id="enemy")
    assert barrier.fighters["enemy"].hp == D(10000)
    assert barrier.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 1

    missed = _battle("vigia")
    missed.fighters["enemy"].stats = replace(
        missed.fighters["enemy"].stats, evasion=D(100)
    )
    assert _perform(missed, "player", "attack", target_id="enemy")
    assert "aim_from" not in missed.fighters["enemy"].path_state


def test_mira_aoe_primary_exception_rastros_and_acquisition_extras():
    state = _battle("vigia")
    _add_enemy(state, "enemy-2")
    state.player_actions["aoe"] = Action(
        "class_art.vigia.voleio", "Voleio", D("0.20"), target_mode="all_opponents"
    )
    assert _perform(state, "player", "aoe")
    assert all("aim_from" not in state.fighters[key].path_state for key in ("enemy", "enemy-2"))

    rain = _battle("vigia", "rastreador")
    _add_enemy(rain, "enemy-2")
    rain.player_actions["rain"] = Action(
        "path_art.vigia.chuva_de_rastros",
        "Chuva de Rastros",
        D("0.20"),
        target_mode="all_opponents",
    )
    assert _perform(rain, "player", "rain")
    assert all(
        rain.fighters[key].path_state["aim_from"]["player"]["stacks"] == 1
        for key in ("enemy", "enemy-2")
    )

    quick = _battle("vigia", "atirador")
    quick.fighters["player"].talent_ids = ("talent.vigia.aquisicao_rapida",)
    assert _perform(quick, "player", "attack", target_id="enemy")
    assert quick.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 2
    assert quick.fighters["player"].path_state["aim_acquisition_used"]["enemy"] is True


def test_mira_target_switch_visao_persistente_and_terminal_consumption():
    state = _battle("vigia")
    _add_enemy(state, "enemy-2")
    state.fighters["player"].talent_ids = ("talent.vigia.visao_persistente",)
    assert _perform(state, "player", "attack", target_id="enemy")
    assert _perform(state, "player", "attack", target_id="enemy-2")
    old_mark = state.fighters["enemy"].path_state["aim_from"]["player"]
    assert (old_mark["stacks"], old_mark["remaining"]) == (1, 1)

    terminal = _battle("vigia", "atirador")
    terminal.fighters["enemy"].path_state["aim_from"] = {
        "player": {
            "stacks": 4,
            "remaining": 2,
            "applied_opportunity": terminal.fighters["player"].opportunity,
        }
    }
    terminal.player_actions["terminal"] = Action(
        "class_art.vigia.disparo_terminal",
        "Disparo Terminal",
        D("1.75"),
        resource_uses=(
            ActionResourceUse(
                "aim",
                minimum=4,
                consume=4,
                consume_at="after_resolution",
                target_selector="primary_target",
                required=True,
            ),
        ),
        conditional_modifiers=(
            ActionConditionalModifier(
                "atirador.disparo_terminal",
                ActionCondition(
                    "class_resource_at_least", resource="aim", minimum=4
                ),
                "crit_bonus",
                D(15),
                target_scope="primary_target",
            ),
        ),
    )
    assert _perform(terminal, "player", "terminal", target_id="enemy")
    assert "aim_from" not in terminal.fighters["enemy"].path_state
    terminal_event = _last_event(terminal, "terminal")
    assert terminal_event.path_crit_bonus == D(21)
    assert terminal_event.class_resource_changes == (("aim", "enemy", 4, 0),)
    insufficient = _battle("vigia", "atirador")
    insufficient.player_actions["terminal"] = terminal.player_actions["terminal"]
    assert not _perform(insufficient, "player", "terminal", target_id="enemy")
    assert insufficient.fighters["enemy"].path_state.get("aim_from") is None
    assert "terminal" not in insufficient.fighters["player"].cooldowns


def test_cacada_metodica_prepares_one_followup_after_hitting_max_mira():
    state = _battle("vigia")
    state.fighters["player"].talent_ids = ("talent.vigia.cacada_metodica",)
    state.fighters["enemy"].path_state["aim_from"] = {
        "player": {"stacks": 3, "remaining": 2, "applied_opportunity": 0}
    }
    assert _perform(state, "player", "attack", target_id="enemy")
    assert state.fighters["player"].path_state["aim_next_per"]["magnitude"] == 3
    assert _perform(state, "player", "attack", target_id="enemy")
    assert _last_event(state, "attack").path_per_bonus == D(3)
    assert state.fighters["player"].path_state["aim_next_per"]["remaining"] == 2


def test_trama_generates_from_utility_art_and_only_different_eligible_art_consumes():
    state = _battle("tecelao")
    state.player_actions["weave"] = Action(
        "class_art.tecelao.weave",
        "Tecer",
        D(0),
        target_mode="self",
        self_effects=(ActionEffect("focus", "defense", D("0.05"), 1, "buff"),),
    )
    assert _perform(state, "player", "weave")
    actor = state.fighters["player"]
    assert actor.path_state["trama_state"]["origin_art"] == "class_art.tecelao.weave"
    actor.path_state["trama_state"]["remaining"] = 1
    assert _perform(state, "player", "weave")
    assert actor.path_state["trama_state"]["remaining"] == 1

    state.player_actions["damage"] = Action(
        "class_art.tecelao.damage", "Fio de Dano", D("0.50")
    )
    assert _perform(state, "player", "damage", target_id="enemy")
    assert _last_event(state, "damage").path_power_multiplier == D("1.10")
    assert "trama_state" not in actor.path_state


def test_trama_path_bonus_expiry_renewal_and_combat_codec():
    state = _battle("tecelao", "runico")
    actor = state.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": "class_art.tecelao.prepare",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    state.player_actions["barrier"] = Action(
        "class_art.tecelao.barrier",
        "Barreira",
        D(0),
        target_mode="self",
        self_barrier_coefficient=D("0.50"),
        self_barrier_duration=2,
    )
    assert _perform(state, "player", "barrier")
    assert state.events[-1].barrier_power_multiplier == D("1.15")
    assert "trama_state" not in actor.path_state

    actor.talent_ids = ("talent.tecelao.fio_persistente",)
    actor.opportunity = 3
    actor.path_state["trama_state"] = {
        "origin_art": "class_art.tecelao.first",
        "remaining": 1,
        "applied_opportunity": 2,
    }
    _tick_path_resources(state, "player")
    assert actor.path_state["trama_state"]["remaining"] == 1
    assert actor.path_state["trama_expiry_renewed"] is True

    actor.path_state["omen_offensive"] = {"enemy": {"remaining": 2}}
    actor.path_state["luminar_state"] = {"kind": "fulgor", "remaining": 1}
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state == actor.path_state


def test_pressagio_generation_and_barrier_does_not_generate_from_existing_state_alone():
    state = _battle("oraculo")
    state.player_actions["simple"] = Action(
        "class_art.oraculo.damage", "Dano simples", D("0.50")
    )
    assert _perform(state, "player", "simple", target_id="enemy")
    assert "omen_offensive" not in state.fighters["player"].path_state

    state.player_actions["negative"] = Action(
        "class_art.oraculo.negative",
        "Aplica Debuff",
        D("0.40"),
        target_effects=(ActionEffect("slow", "agility", D("0.10"), 2, "debuff"),),
    )
    assert _perform(state, "player", "negative", target_id="enemy")
    assert "enemy" in state.fighters["player"].path_state["omen_offensive"]

    support = _battle("oraculo")
    support.player_actions["buff"] = Action(
        "class_art.oraculo.buff",
        "Buff próprio",
        D(0),
        target_mode="self",
        self_effects=(ActionEffect("buff", "defense", D("0.10"), 2, "buff"),),
    )
    assert _perform(support, "player", "buff")
    assert "player" in support.fighters["player"].path_state["omen_defensive"]

    shield = _battle("oraculo")
    shield.fighters["player"].barrier = D(100)
    shield.fighters["player"].barrier_remaining = 2
    shield.player_actions["simple"] = Action(
        "class_art.oraculo.damage", "Dano simples", D("0.50")
    )
    assert _perform(shield, "player", "simple", target_id="enemy")
    assert "omen_defensive" not in shield.fighters["player"].path_state


def test_pressagio_consumes_on_commit_and_can_be_regenerated_after_resolution():
    state = _battle("oraculo", "agoureiro")
    actor = state.fighters["player"]
    actor.path_state["omen_offensive"] = {
        "enemy": {"remaining": 2, "applied_opportunity": actor.opportunity}
    }
    state.player_actions["signal"] = Action(
        "class_art.oraculo.signal",
        "Sinal e dano",
        D("0.50"),
        attack_debuff=D("0.10"),
        duration=2,
    )
    assert _perform(state, "player", "signal", target_id="enemy")
    assert _last_event(state, "signal").path_power_multiplier == D("1.16")
    assert actor.path_state["omen_offensive"]["enemy"]["remaining"] == 2

    miss = _battle("oraculo")
    miss.fighters["enemy"].stats = replace(miss.fighters["enemy"].stats, evasion=D(100))
    miss.fighters["player"].path_state["omen_offensive"] = {
        "enemy": {"remaining": 2, "applied_opportunity": 0}
    }
    miss.player_actions["damage"] = Action(
        "class_art.oraculo.damage", "Dano", D("0.50")
    )
    assert _perform(miss, "player", "damage", target_id="enemy")
    assert _last_event(miss, "damage").dodged is True
    assert "omen_offensive" not in miss.fighters["player"].path_state


def test_pressagio_duration_and_flexivel_expire_on_oraculo_opportunities():
    state = _battle("oraculo")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.oraculo.sinal_persistente",)
    state.player_actions["signal"] = Action(
        "class_art.oraculo.signal",
        "Sinal",
        D("0.20"),
        attack_debuff=D("0.10"),
        duration=2,
    )
    assert _perform(state, "player", "signal", target_id="enemy")
    assert actor.path_state["omen_offensive"]["enemy"]["remaining"] == 3

    actor.talent_ids = ("talent.oraculo.pressagio_flexivel",)
    actor.opportunity = 5
    actor.path_state["omen_offensive"] = {
        "enemy": {"remaining": 1, "applied_opportunity": 4}
    }
    _tick_path_resources(state, "player")
    assert actor.path_state["omen_offensive"]["enemy"]["remaining"] == 1
    assert actor.path_state["omen_flexible_used"] is True


def test_luminar_states_alternate_exclusively_and_consume_even_on_miss_or_overheal():
    state = _battle("luminar", "guardiao")
    actor = state.fighters["player"]
    state.player_actions["damage"] = Action(
        "class_art.luminar.damage", "Dano", D("0.50")
    )
    state.player_actions["heal"] = Action(
        "class_art.luminar.heal",
        "Cura",
        D(0),
        target_mode="self",
        heal_coefficient=D("0.50"),
    )
    assert _perform(state, "player", "damage", target_id="enemy")
    assert actor.path_state["luminar_state"]["kind"] == "fulgor"
    actor.hp = actor.stats.hp
    actor.talent_ids = ("talent.luminar.fluxo_restaurador",)
    assert _perform(state, "player", "heal")
    assert "luminar_state" not in actor.path_state
    assert not any(effect.id.endswith("fluxo_restaurador.defense") for effect in actor.effects)
    assert state.events[-1].effective_healing == ZERO

    judgment = _battle("luminar", "inquisidor")
    judgment.fighters["player"].path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    judgment.fighters["enemy"].stats = replace(
        judgment.fighters["enemy"].stats, evasion=D(100)
    )
    judgment.player_actions["damage"] = Action(
        "class_art.luminar.damage", "Dano", D("0.50")
    )
    assert _perform(judgment, "player", "damage", target_id="enemy")
    assert _last_event(judgment, "damage").dodged is True
    assert "luminar_state" not in judgment.fighters["player"].path_state


def test_luminar_contraluz_perfeita_only_adds_penetration_to_julgamento():
    state = _battle("luminar", "guardiao")
    actor = state.fighters["player"]
    actor.talent_ids = ("talent.luminar.contraluz_perfeita",)
    actor.path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    state.player_actions["damage"] = Action(
        "class_art.luminar.damage", "Dano", D("0.50")
    )
    assert _perform(state, "player", "damage", target_id="enemy")
    event = _last_event(state, "damage")
    assert event.path_power_multiplier == D("1.06")
    assert event.path_per_bonus == D(2)


def test_death_and_combat_end_clear_owner_and_target_class_states():
    state = _battle("vigia", "rastreador")
    actor = state.fighters["player"]
    _grant_retaliation_to_player(state)
    actor.path_state["trama_state"] = {"remaining": 1, "origin_art": "class_art.x"}
    actor.path_state["omen_offensive"] = {"enemy": {"remaining": 1}}
    state.fighters["enemy"].path_state["aim_from"] = {
        "player": {"stacks": 2, "remaining": 2}
    }
    _clear_class_mechanics_for_death(state, "player")
    assert actor.retaliation_charges == 0
    assert "trama_state" not in actor.path_state
    assert "omen_offensive" not in actor.path_state
    assert "aim_from" not in state.fighters["enemy"].path_state

    actor.path_state["luminar_state"] = {"kind": "fulgor", "remaining": 1}
    state.fighters["enemy"].path_state["aim_from"] = {
        "player": {"stacks": 1, "remaining": 1}
    }
    _finish_combat(state, "victory")
    assert state.result == "victory"
    assert not actor.path_state
    assert "aim_from" not in state.fighters["enemy"].path_state


def test_declared_hp_and_target_effect_conditions_use_action_start_snapshot():
    state = _battle("errante")
    actor = state.fighters["player"]
    action = Action(
        "class_art.errante.snapshot",
        "Ação Condicional",
        D("0.50"),
        attack_debuff=D("0.10"),
        duration=2,
        conditional_modifiers=(
            ActionConditionalModifier(
                "errante.test.debuff_bonus",
                ActionCondition("target_has_normal_negative_effect"),
                "final_damage_bonus",
                D("0.10"),
            ),
        ),
    )
    state.player_actions["conditional"] = action
    assert _perform(state, "player", "conditional", target_id="enemy")
    assert _last_event(state, "conditional").path_final_damage_bonus == ZERO

    assert _perform(state, "player", "conditional", target_id="enemy")
    assert _last_event(state, "conditional").path_final_damage_bonus == D("0.18")

    actor.hp = D(499)
    state.player_actions["low_hp"] = Action(
        "path_art.sentinela.devastador.ruptor.test",
        "Ruptura Condicional de Teste",
        D("0.50"),
        conditional_modifiers=(
            ActionConditionalModifier(
                "devastador.test.low_hp_power",
                ActionCondition("actor_hp_fraction_below", threshold=D("0.50")),
                "damage_power",
                D("0.10"),
                operation="multiply",
            ),
        ),
    )
    assert _perform(state, "player", "low_hp", target_id="enemy")
    assert _last_event(state, "low_hp").path_power_multiplier == D("1.10")


def test_optional_mira_bonus_does_not_block_when_condition_is_missing():
    state = _battle("vigia", "atirador")
    target = state.fighters["enemy"]
    target.path_state["aim_from"] = {
        "player": {
            "stacks": 1,
            "remaining": 2,
            "applied_opportunity": state.fighters["player"].opportunity,
        }
    }
    state.player_actions["calculated"] = Action(
        "class_art.vigia.tiro_calculado.test",
        "Tiro Calculado de Teste",
        D("1.25"),
        conditional_modifiers=(
            ActionConditionalModifier(
                "vigia.test.two_aim_crit",
                ActionCondition("class_resource_at_least", resource="aim", minimum=2),
                "crit_bonus",
                D(10),
                target_scope="primary_target",
            ),
        ),
    )
    assert _perform(state, "player", "calculated", target_id="enemy")
    assert _last_event(state, "calculated").path_crit_bonus == ZERO
    assert target.path_state["aim_from"]["player"]["stacks"] == 2

    assert _perform(state, "player", "calculated", target_id="enemy")
    assert _last_event(state, "calculated").path_crit_bonus == D(10)


def test_declared_required_mira_blocks_before_commit_and_consumes_once_after_multihit():
    state = _battle("vigia", "atirador")
    target = state.fighters["enemy"]
    state.player_actions["terminal_test"] = Action(
        "class_art.vigia.terminal_test",
        "Finalização Sintética",
        D("0.50"),
        hit_count=3,
        cooldown=2,
        resource_uses=(
            ActionResourceUse(
                "aim",
                minimum=4,
                consume=4,
                consume_at="after_resolution",
                target_selector="primary_target",
                required=True,
            ),
        ),
        conditional_modifiers=(
            ActionConditionalModifier(
                "vigia.test.four_aim_crit",
                ActionCondition("class_resource_at_least", resource="aim", minimum=4),
                "crit_bonus",
                D(15),
                target_scope="primary_target",
            ),
        ),
    )
    target.path_state["aim_from"] = {
        "player": {"stacks": 3, "remaining": 2, "applied_opportunity": 0}
    }
    assert not _perform(state, "player", "terminal_test", target_id="enemy")
    assert target.path_state["aim_from"]["player"]["stacks"] == 3
    assert "terminal_test" not in state.fighters["player"].cooldowns
    assert not state.events

    target.path_state["aim_from"]["player"]["stacks"] = 4
    assert _perform(state, "player", "terminal_test", target_id="enemy")
    events = [event for event in state.events if event.action == "terminal_test"]
    assert len(events) == 3
    assert all(event.path_crit_bonus == D(21) for event in events)
    assert all(event.aim_stacks == 4 for event in events)
    assert "aim_from" not in target.path_state
    assert events[0].class_resource_changes == (("aim", "enemy", 4, 0),)
    assert all(not event.class_resource_changes for event in events[1:])


def test_declared_resource_consumption_reuses_trama_and_pressagio_machines():
    tecelao = _battle("tecelao", "conjurador")
    actor = tecelao.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": "class_art.tecelao.origin",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    tecelao.player_actions["different"] = Action(
        "class_art.tecelao.different",
        "Arte Diferente",
        D("0.50"),
        resource_uses=(
            ActionResourceUse(
                "trama", minimum=1, consume=1, consume_at="commit"
            ),
        ),
    )
    assert _perform(tecelao, "player", "different", target_id="enemy")
    assert _last_event(tecelao, "different").path_power_multiplier == D("1.15")
    assert "trama_state" not in actor.path_state

    oracle = _battle("oraculo", "agoureiro")
    _add_enemy(oracle, "enemy-2")
    oracle_actor = oracle.fighters["player"]
    for target_key in ("enemy", "enemy-2"):
        oracle_actor.path_state.setdefault("omen_offensive", {})[
            oracle.fighters[target_key].id
        ] = {"remaining": 2, "applied_opportunity": oracle_actor.opportunity}
    oracle.player_actions["aoe_signal"] = Action(
        "class_art.oraculo.aoe_signal",
        "Sinal em Área",
        D("0.25"),
        attack_debuff=D("0.10"),
        duration=2,
        target_mode="all_opponents",
        resource_uses=(
            ActionResourceUse(
                "omen_offensive",
                minimum=1,
                consume=1,
                consume_at="commit",
                target_selector="each_target",
                consumption_scope="per_target",
            ),
        ),
    )
    assert _perform(oracle, "player", "aoe_signal", target_id="enemy")
    events = [event for event in oracle.events if event.action == "aoe_signal"]
    assert len(events) == 2
    assert all(event.path_power_multiplier == D("1.16") for event in events)
    # The original marks are consumed once each; the post-resolution trigger
    # creates a new offensive omen only on the explicitly selected primary.
    assert "enemy-2" not in oracle_actor.path_state["omen_offensive"]
    assert "enemy" in oracle_actor.path_state["omen_offensive"]


def test_declared_luminar_hybrid_consumes_one_state_without_generating_opposite():
    state = _battle("luminar", "guardiao")
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    actor.hp = D(800)
    state.player_actions["hybrid"] = Action(
        "class_art.luminar.hybrid_test",
        "Arte Híbrida Sintética",
        D("0.20"),
        heal_coefficient=D("0.20"),
        target_mode="self",
        resource_uses=(
            ActionResourceUse(
                "luminar_state",
                minimum=1,
                consume=1,
                consume_at="commit",
                state_kind="fulgor",
            ),
        ),
        conditional_modifiers=(
            ActionConditionalModifier(
                "luminar.test.fulgo_healing",
                ActionCondition(
                    "class_resource_at_least",
                    resource="luminar_state",
                    state_kind="fulgor",
                ),
                "healing_power",
                D("0.10"),
                operation="multiply",
            ),
        ),
    )
    assert _perform(state, "player", "hybrid")
    event = _last_event(state, "hybrid")
    assert event.calculated_healing == D(22)
    assert "luminar_state" not in actor.path_state
    assert event.class_resource_changes == (("luminar_state", "player", 1, 0),)
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.player_actions["hybrid"].resource_uses == state.player_actions[
        "hybrid"
    ].resource_uses
    assert restored.events[-1].class_resource_changes == event.class_resource_changes


def test_declared_retaliation_is_required_then_consumed_once_at_commit():
    state = _battle("sentinela", "bastiao")
    state.player_actions["retaliation_art"] = Action(
        "class_art.sentinela.retaliation_test",
        "Ataque com Retaliação",
        D("0.50"),
        cooldown=2,
        resource_uses=(
            ActionResourceUse(
                "retaliation",
                minimum=1,
                consume=1,
                consume_at="commit",
                required=True,
            ),
        ),
    )
    assert not _perform(state, "player", "retaliation_art", target_id="enemy")
    assert not state.events
    assert not state.fighters["player"].cooldowns

    _grant_retaliation_to_player(state)
    assert _perform(state, "player", "retaliation_art", target_id="enemy")
    assert state.fighters["player"].retaliation_charges == 0
    assert _last_event(state, "retaliation_art").class_resource_changes == (
        ("retaliation", state.fighters["player"].id, 1, 0),
    )


def test_conditional_modifier_scope_can_be_action_wide_or_per_target():
    state = _battle("vigia", "atirador")
    _add_enemy(state, "enemy-2")
    state.fighters["enemy"].effects.append(
        Effect(
            "existing.weakness",
            "attack",
            D("0.10"),
            2,
            0,
            kind="debuff",
        )
    )
    condition = ActionCondition("target_has_normal_negative_effect")
    state.player_actions["per_target"] = Action(
        "class_art.errante.per_target_test",
        "Ataque em Área por Alvo",
        D("0.20"),
        target_mode="all_opponents",
        conditional_modifiers=(
            ActionConditionalModifier(
                "test.per_target",
                condition,
                "final_damage_bonus",
                D("0.10"),
                target_scope="per_target",
                evaluation_scope="per_target",
            ),
        ),
    )
    assert _perform(state, "player", "per_target", target_id="enemy")
    per_target = {
        event.target: event.path_final_damage_bonus
        for event in state.events
        if event.action == "per_target"
    }
    assert per_target == {"enemy": D("0.10"), "enemy-2": ZERO}

    state.player_actions["per_action"] = Action(
        "class_art.errante.per_action_test",
        "Ataque em Área por Ação",
        D("0.20"),
        target_mode="all_opponents",
        conditional_modifiers=(
            ActionConditionalModifier(
                "test.per_action",
                condition,
                "final_damage_bonus",
                D("0.10"),
                target_scope="per_target",
                evaluation_scope="per_action",
            ),
        ),
    )
    assert _perform(state, "player", "per_action", target_id="enemy")
    per_action = {
        event.target: event.path_final_damage_bonus
        for event in state.events
        if event.action == "per_action"
    }
    assert per_action == {"enemy": D("0.10"), "enemy-2": D("0.10")}


def test_resource_contract_rejects_ambiguous_luminar_and_aoe_consumption():
    import pytest

    with pytest.raises(ValueError, match="identify Fulgor or Julgamento"):
        ActionResourceUse("luminar_state", consume=1, consume_at="commit")
    with pytest.raises(ValueError, match="identify Fulgor or Julgamento"):
        ActionCondition("class_resource_at_least", resource="luminar_state")
    with pytest.raises(ValueError, match="per-target scope explicitly"):
        ActionResourceUse(
            "omen_offensive",
            consume=1,
            consume_at="commit",
            target_selector="each_target",
        )
