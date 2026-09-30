from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.combat import (
    Action,
    ActionEffect,
    Effect,
    _advance_to_player,
    _perform,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    class_stats,
    racial_stats,
    resolve_combat_stats,
)
from asterion.domain.economy import path_switch_cost
from asterion.domain.equipment_stats import (
    EquipmentConfigurationSnapshot,
    EquipmentStatContribution,
    equipment_configuration_from_data,
)
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.prologue import PROFILE

D = Decimal


def _battle(character_class: str, selected_path: str | None = None):
    stats = resolve_combat_stats(character_class, 10, "remanescente")
    state = PROFILE.create(
        UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5"),
        "Luiken",
        character_class,
        "remanescente",
        stats.hp,
    )
    state.tutorial = None
    state.fighters["player"].selected_path = selected_path
    state.fighters["player"].stats = replace(
        state.fighters["player"].stats,
        hp=D(1000),
        attack=D(100),
        defense=D(0),
        agility=D(100),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    state.fighters["player"].hp = D(1000)
    state.fighters["enemy"].stats = replace(
        state.fighters["enemy"].stats,
        hp=D(10000),
        attack=D(100),
        defense=D(100),
        agility=D(0),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    state.fighters["enemy"].hp = D(10000)
    state.fighters["enemy"].side = "enemy"
    state.ruleset = CURRENT_COMBAT_RULESET
    state.player_actions = {
        "attack": Action("attack", "Ataque Básico", D(1)),
        "art": Action("class_art.test", "Arte de Teste", D(1)),
    }
    state.enemy_actions = {"hit": Action("enemy.test", "Golpe", D(1))}
    state.ai_cycle = ("hit",)
    return state


@pytest.mark.parametrize("path_id", tuple(PATH_DEFINITIONS))
def test_path_stat_modifiers_apply_to_only_the_class_stat_portion(path_id):
    path = PATH_DEFINITIONS[path_id]
    base = resolve_combat_stats(path.character_class, 10, "remanescente")
    without_path = resolve_combat_stats(path.character_class, 10, "remanescente")
    with_path = resolve_combat_stats(
        path.character_class,
        10,
        "remanescente",
        selected_path=path_id,
    )
    assert without_path.values() == base.values()
    assert with_path.hp == base.hp * (D(1) + path.hp)
    assert with_path.attack == base.attack * (D(1) + path.attack)
    assert with_path.defense == base.defense * (D(1) + path.defense)
    assert with_path.agility == base.agility * (D(1) + path.agility)


def test_path_switch_cost_uses_shared_rounded_level_unit():
    assert path_switch_cost(10) == 380
    assert path_switch_cost(60) == 1500


def test_path_modifier_precedes_equipment_and_final_racial_modifier():
    base = class_stats("sentinela", 10)
    path = PATH_DEFINITIONS["bastiao"]
    equipment = EquipmentStatContribution(hp=D(120), attack=D(40), defense=D(25), agility=D(5))
    expected = racial_stats(
        replace(
            base,
            hp=base.hp * (D(1) + path.hp) + equipment.hp,
            attack=base.attack * (D(1) + path.attack) + equipment.attack,
            defense=base.defense * (D(1) + path.defense) + equipment.defense,
            agility=base.agility * (D(1) + path.agility) + equipment.agility,
        ),
        "remanescente",
    )
    actual = resolve_combat_stats(
        "sentinela", 10, "remanescente", equipment, selected_path="bastiao"
    )
    assert actual == expected


def test_equipment_combat_snapshot_roundtrips_selected_path_and_legacy_defaults():
    snapshot = EquipmentConfigurationSnapshot(7, selected_path="rastreador")
    encoded = snapshot.to_data(CURRENT_COMBAT_RULESET)
    assert equipment_configuration_from_data(encoded) == snapshot
    legacy = equipment_configuration_from_data(
        {"combat_configuration_version": 6, "ruleset_version": CURRENT_COMBAT_RULESET}
    )
    assert legacy.selected_path is None


def test_bastiao_barrier_bonus_and_defender_retaliation_fortaleza_do_not_stack():
    state = _battle("sentinela", "bastiao")
    player = state.fighters["player"]
    enemy = state.fighters["enemy"]
    player.defending = True
    enemy.stats = replace(enemy.stats, attack=D(10), defense=D(0))
    state.enemy_actions["hit"] = Action("hit", "Golpe", D(1))

    _perform(state, "enemy", "hit")
    assert player.retaliation_charges == 1
    first_barrier = player.barrier
    assert first_barrier == D(44)
    assert player.barrier_source == "path.bastiao.fortaleza"

    _perform(state, "enemy", "hit")
    # The second attack consumes the existing barrier, without adding another
    # Fortaleza barrier to the remaining amount.
    assert player.barrier == first_barrier - D(5)
    fortaleza_events = [
        event for event in state.mechanic_events if event.action == "path.bastiao.fortaleza"
    ]
    assert len(fortaleza_events) == 1


def test_bastiao_increases_barrier_actions_by_ten_percent():
    state = _battle("sentinela", "bastiao")
    state.player_actions["barrier"] = Action(
        "class_art.sentinela.path.test",
        "Barreira",
        D(0),
        target_mode="self",
        self_barrier_coefficient=D("0.50"),
        self_barrier_duration=2,
    )
    _perform(state, "player", "barrier")
    assert state.fighters["player"].barrier == D(55)
    assert state.events[-1].path_power_multiplier == D("1.10")


def test_devastador_threshold_aggregates_multihit_real_hp_damage_and_basic_does_not_consume():
    state = _battle("sentinela", "devastador")
    state.enemy_actions["hit"] = Action(
        "enemy.multi", "Golpes", D("0.40"), hit_count=2
    )
    state.order = ("enemy", "player")
    state.turn_index = 0
    _advance_to_player(state)
    charge = state.fighters["player"].path_state.get("devastador_charge")
    assert charge is not None

    _perform(state, "player", "attack")
    assert state.fighters["player"].path_state.get("devastador_charge") == charge

    _perform(state, "player", "art")
    assert state.events[-1].path_final_damage_bonus == D("0.12")
    assert "devastador.impacto_consumido" in state.events[-1].path_triggers
    assert "devastador_charge" not in state.fighters["player"].path_state


def test_devastador_does_not_charge_for_damage_absorbed_by_barrier():
    state = _battle("sentinela", "devastador")
    player = state.fighters["player"]
    player.barrier = D(200)
    player.barrier_remaining = 2
    state.enemy_actions["hit"] = Action("enemy.hit", "Golpe", D(1))
    state.order = ("enemy", "player")
    state.turn_index = 0

    _advance_to_player(state)

    assert player.hp == D(1000)
    assert "devastador_charge" not in player.path_state


def test_carrasco_and_oportunismo_stack_per_target_for_aoe():
    state = _battle("errante", "carrasco")
    second = replace(
        state.fighters["enemy"],
        id="enemy-2",
        name="Outro Eco",
        hp=D(10000),
        side="enemy",
        effects=[],
        cooldowns={},
        path_state={},
    )
    state.fighters["enemy"].hp = D(4000)
    state.fighters["enemy"].effects.append(Effect("slow", "attack", D("0.10"), 2, 0))
    second.effects.append(
        Effect("stun", "action_restriction", D(1), 1, 0, hard_cc=True)
    )
    state.fighters["enemy-2"] = second
    state.player_actions["art"] = Action(
        "class_art.errante.sweep", "Arte em Área", D(1), target_mode="all_opponents"
    )

    _perform(state, "player", "art")

    events = [event for event in state.events if event.actor == "player"]
    by_target = {event.target: event for event in events}
    assert by_target["enemy"].path_final_damage_bonus == D("0.16")
    assert set(by_target["enemy"].path_triggers) >= {
        "oportunismo",
        "carrasco.sentenca",
    }
    assert by_target["enemy-2"].path_final_damage_bonus == D("0.08")
    assert "oportunismo" in by_target["enemy-2"].path_triggers


def test_carrasco_checks_each_multihit_against_target_hp_before_that_hit():
    state = _battle("errante", "carrasco")
    target = state.fighters["enemy"]
    target.stats = replace(target.stats, hp=D(410), defense=D(0))
    target.hp = D(170)
    state.player_actions["art"] = Action(
        "class_art.errante.multi", "Corte Múltiplo", D("0.10"), hit_count=2
    )

    _perform(state, "player", "art")

    events = [event for event in state.events if event.actor == "player"]
    assert events[0].path_final_damage_bonus == D(0)
    assert events[1].path_final_damage_bonus == D("0.08")
    assert "carrasco.sentenca" not in events[0].path_triggers
    assert "carrasco.sentenca" in events[1].path_triggers


def test_sabotador_extends_only_removable_non_cc_debuffs_and_does_not_change_dots():
    state = _battle("errante", "sabotador")
    state.player_actions["art"] = Action(
        "class_art.errante.test",
        "Interferência",
        D(0),
        target_effects=(
            ActionEffect("short", "attack", D("0.10"), 1, "debuff"),
            ActionEffect("cc", "agility", D("0.10"), 1, "debuff", hard_cc=True),
        ),
    )
    _perform(state, "player", "art")
    effects = {effect.id: effect for effect in state.fighters["enemy"].effects}
    assert effects["short"].remaining == 2
    assert effects["cc"].remaining == 1

    dot_state = _battle("errante", "sabotador")
    dot_state.player_actions["art"] = Action(
        "class_art.errante.dot", "Ferida", D(1), native_dot_kind="bleed", native_dot_stacks=1
    )
    _perform(dot_state, "player", "art")
    assert dot_state.dot_states["enemy"][0].remaining == 2


def test_sabotador_duration_caps_at_three_and_does_not_extend_unremovable_effects():
    state = _battle("errante", "sabotador")
    state.player_actions["art"] = Action(
        "class_art.errante.test",
        "Interferência",
        D(0),
        target_effects=(
            ActionEffect("one", "attack", D("0.10"), 1, "debuff"),
            ActionEffect("two", "defense", D("0.10"), 2, "debuff"),
            ActionEffect("three", "agility", D("0.10"), 3, "debuff"),
            ActionEffect(
                "fixed", "agility", D("0.10"), 1, "debuff", unremovable=True
            ),
        ),
    )
    _perform(state, "player", "art")
    effects = {effect.id: effect for effect in state.fighters["enemy"].effects}
    assert {key: effects[key].remaining for key in ("one", "two", "three", "fixed")} == {
        "one": 2,
        "two": 3,
        "three": 3,
        "fixed": 1,
    }


def test_atirador_mira_builds_four_stacks_and_applies_per_and_crit():
    state = _battle("vigia", "atirador")
    state.fighters["player"].stats = replace(
        state.fighters["player"].stats, crit=D(20)
    )
    for _ in range(4):
        _perform(state, "player", "attack")

    event = state.events[-1]
    assert event.aim_stacks == 4
    assert event.path_per_bonus == D(9)
    assert event.path_crit_bonus == D(0)
    assert state.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 4
    assert "vigia.mira_gerada" in event.path_triggers

    _perform(state, "player", "attack")
    assert state.events[-1].path_crit_bonus == D(6)


def test_mira_baseline_caps_at_three_and_misses_do_not_generate():
    baseline = _battle("vigia")
    for _ in range(4):
        _perform(baseline, "player", "attack")
    assert baseline.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 3

    missed = _battle("vigia", "atirador")
    missed.fighters["enemy"].stats = replace(missed.fighters["enemy"].stats, evasion=D(100))
    _perform(missed, "player", "attack")
    assert missed.events[-1].dodged
    assert missed.fighters["enemy"].path_state.get("aim_from", {}).get("player") is None


def test_rastreador_mira_accepts_direct_dot_and_agility_triggers_without_duplicate_stack():
    state = _battle("vigia", "rastreador")
    state.player_actions["art"] = Action(
        "class_art.vigia.dot",
        "Arte com DoT",
        D(1),
        native_dot_kind="poison",
        native_dot_stacks=1,
    )
    _perform(state, "player", "art")
    assert state.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 1

    state.player_actions["art"] = Action(
        "class_art.vigia.agility",
        "Redução de AGI",
        D(0),
        target_effects=(ActionEffect("slow", "agility", D("0.10"), 2, "debuff"),),
    )
    _perform(state, "player", "art")
    assert state.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 2


def test_rastreador_keeps_three_targets_without_clearing_marks_when_switching():
    state = _battle("vigia", "rastreador")
    for target_id in ("enemy", "enemy-2", "enemy-3", "enemy-4"):
        if target_id != "enemy":
            state.fighters[target_id] = replace(
                state.fighters["enemy"],
                id=target_id,
                name=target_id,
                hp=D(10000),
                side="enemy",
                effects=[],
                cooldowns={},
                path_state={},
            )
        _perform(state, "player", "attack", target_id=target_id)
    marks = {
        fighter.id
        for fighter in state.fighters.values()
        if fighter.path_state.get("aim_from", {}).get("player", {}).get("stacks")
    }
    assert marks == {"enemy", "enemy-2", "enemy-3"}


@pytest.mark.parametrize(
    ("path_id", "damage_bonus", "support_bonus"),
    [("conjurador", D("1.15"), D("1.06")), ("runico", D("1.06"), D("1.15"))],
)
def test_tecelao_path_replaces_baseline_chain_bonus(path_id, damage_bonus, support_bonus):
    state = _battle("tecelao", path_id)
    state.player_actions["prepare"] = Action(
        "class_art.tecelao.prepare", "Prepara Trama", D("0.1"), prepares_chain="thread"
    )
    state.player_actions["damage"] = Action(
        "class_art.tecelao.damage",
        "Dano",
        D("0.5"),
        consumes_chain="thread",
        chain_power_bonus=D("0.10"),
    )
    state.player_actions["support_prepare"] = Action(
        "class_art.tecelao.support.prepare",
        "Prepara Suporte",
        D(0),
        target_mode="self",
        prepares_chain="support",
    )
    state.player_actions["support"] = Action(
        "class_art.tecelao.support",
        "Cura",
        D(0),
        target_mode="self",
        heal_coefficient=D("0.5"),
        consumes_chain="support",
        chain_power_bonus=D("0.10"),
    )

    _perform(state, "player", "prepare")
    _perform(state, "player", "damage")
    assert state.events[-1].damage_power_multiplier == damage_bonus
    state.fighters["player"].hp = D(500)
    _perform(state, "player", "support_prepare")
    _perform(state, "player", "support")
    assert state.events[-1].healing_power_multiplier == support_bonus


def test_oraculo_pressagio_generates_refreshes_and_consumes_by_type_and_target():
    state = _battle("oraculo", "agoureiro")
    state.player_actions["signal"] = Action(
        "class_art.oraculo.sinal_funesto",
        "Sinal Funesto",
        D(0),
        attack_debuff=D("0.08"),
        duration=2,
        effect_id="sinal",
    )
    state.player_actions["attack_art"] = Action(
        "class_art.oraculo.ruina_predita", "Ruína Predita", D(1)
    )
    state.player_actions["buff"] = Action(
        "class_art.oraculo.vislumbre",
        "Vislumbre",
        D(0),
        target_mode="self",
        self_effects=(ActionEffect("vislumbre", "agility", D("0.10"), 2, "buff"),),
    )
    state.player_actions["barrier"] = Action(
        "class_art.oraculo.veu_premonitorio",
        "Véu",
        D(0),
        target_mode="self",
        self_barrier_coefficient=D("0.70"),
        self_barrier_duration=2,
    )

    _perform(state, "player", "signal")
    _perform(state, "player", "signal")
    offensive = state.fighters["player"].path_state["omen_offensive"]["enemy"]
    assert offensive["remaining"] == 2
    _perform(state, "player", "attack_art")
    assert state.events[-1].path_power_multiplier == D("1.16")

    _perform(state, "player", "buff")
    assert "enemy" not in state.fighters["player"].path_state["omen_defensive"]
    assert "player" in state.fighters["player"].path_state["omen_defensive"]
    _perform(state, "player", "barrier")
    assert state.events[-1].barrier_value == D(78)
    assert state.events[-1].path_power_multiplier == D("1.12")

    baseline = _battle("oraculo")
    baseline.player_actions.update(
        {
            "signal": state.player_actions["signal"],
            "attack_art": state.player_actions["attack_art"],
        }
    )
    _perform(baseline, "player", "signal")
    _perform(baseline, "player", "attack_art")
    assert baseline.events[-1].path_power_multiplier == D("1.12")


def test_luminar_fulgor_and_julgamento_alternate_without_consuming_and_regenerating_together():
    state = _battle("luminar", "guardiao")
    state.player_actions["damage_art"] = Action(
        "class_art.luminar.fulgor", "Fulgor", D(1)
    )
    state.player_actions["support_art"] = Action(
        "class_art.luminar.renovacao",
        "Renovação",
        D(0),
        target_mode="self",
        heal_coefficient=D("0.85"),
    )
    state.player_actions["barrier_art"] = Action(
        "class_art.luminar.egide_solar",
        "Égide Solar",
        D(0),
        target_mode="self",
        self_barrier_coefficient=D("0.90"),
        self_barrier_duration=2,
    )

    _perform(state, "player", "damage_art")
    assert state.events[-1].path_triggers[-1] == "luminar.fulgor_gerado"
    _perform(state, "player", "support_art")
    assert state.events[-1].path_power_multiplier == D("1.15")
    assert state.events[-1].path_triggers == ("luminar.fulgor_consumido",)
    assert "luminar_state" not in state.fighters["player"].path_state
    _perform(state, "player", "damage_art")
    assert state.events[-1].path_power_multiplier == D(1)
    assert state.events[-1].path_triggers == ("luminar.fulgor_gerado",)
    _perform(state, "player", "barrier_art")
    assert state.events[-1].path_power_multiplier == D("1.15")
    assert state.events[-1].path_triggers == ("luminar.fulgor_consumido",)
    assert "luminar_state" not in state.fighters["player"].path_state
    _perform(state, "player", "support_art")
    assert state.events[-1].path_triggers == ("luminar.julgamento_gerado",)
    _perform(state, "player", "damage_art")
    assert state.events[-1].path_power_multiplier == D("1.06")
    assert state.events[-1].path_triggers == ("luminar.julgamento_consumido",)


def test_inquisidor_replaces_luminar_baselines_for_fulgor_and_julgamento():
    state = _battle("luminar", "inquisidor")
    state.player_actions.update(
        {
            "damage_art": Action("class_art.luminar.fulgor", "Fulgor", D(1)),
            "support_art": Action(
                "class_art.luminar.renovacao",
                "Renovação",
                D(0),
                target_mode="self",
                heal_coefficient=D("0.85"),
            ),
            "barrier_art": Action(
                "class_art.luminar.egide_solar",
                "Égide Solar",
                D(0),
                target_mode="self",
                self_barrier_coefficient=D("0.90"),
                self_barrier_duration=2,
            ),
        }
    )
    _perform(state, "player", "support_art")
    assert state.events[-1].path_triggers == ("luminar.julgamento_gerado",)
    _perform(state, "player", "damage_art")
    assert state.events[-1].path_power_multiplier == D("1.15")
    assert state.events[-1].path_triggers == ("luminar.julgamento_consumido",)

    _perform(state, "player", "damage_art")
    assert state.events[-1].path_triggers == ("luminar.fulgor_gerado",)
    _perform(state, "player", "support_art")
    assert state.events[-1].path_power_multiplier == D("1.06")
    assert state.events[-1].path_triggers == ("luminar.fulgor_consumido",)
    _perform(state, "player", "damage_art")
    assert state.events[-1].path_power_multiplier == D(1)
    assert state.events[-1].path_triggers == ("luminar.fulgor_gerado",)

    _perform(state, "player", "barrier_art")
    assert state.events[-1].path_power_multiplier == D("1.06")
    assert state.events[-1].path_triggers == ("luminar.fulgor_consumido",)
    assert "luminar_state" not in state.fighters["player"].path_state


def test_invocador_manifestation_alternation_is_generic_and_triada_encarnada_is_neutral():
    state = _battle("oraculo", "invocador")
    state.player_actions["wolf"] = Action(
        "synthetic.manifestation.wolf", "Lobo", D("0.2"), manifestation_kind="lobo"
    )
    state.player_actions["owl"] = Action(
        "synthetic.manifestation.owl", "Coruja", D("0.2"), manifestation_kind="coruja"
    )
    state.player_actions["triad"] = Action(
        "synthetic.triada_encarnada",
        "Tríade Encarnada",
        D(0),
        target_mode="self",
        manifestation_kind="triade_encarnada",
    )

    _perform(state, "player", "wolf")
    _perform(state, "player", "owl")
    assert state.events[-1].path_power_multiplier == D("1.12")
    before = dict(state.fighters["player"].path_state["manifestation_state"])
    _perform(state, "player", "triad")
    assert state.fighters["player"].path_state["manifestation_state"] == before


def test_snapshot_roundtrip_preserves_path_resources_and_old_payload_defaults():
    from asterion.infrastructure.db.combat_codec import decode, encode

    state = _battle("vigia", "atirador")
    for _ in range(2):
        _perform(state, "player", "attack")
    payload = encode(state)
    restored = decode(payload, state.id, state.ruleset, state.version)
    assert restored == state
    payload["fighters"]["player"].pop("selected_path")
    payload["fighters"]["player"].pop("path_state")
    for event in payload["events"]:
        event.pop("path_power_multiplier", None)
        event.pop("path_final_damage_bonus", None)
        event.pop("path_per_bonus", None)
        event.pop("path_crit_bonus", None)
        event.pop("path_triggers", None)
        event.pop("aim_stacks", None)
    legacy = decode(payload, state.id, state.ruleset, state.version)
    assert legacy.fighters["player"].selected_path is None
    assert legacy.fighters["player"].path_state == {}
    assert legacy.events[0].path_power_multiplier == D(1)
    assert legacy.events[0].path_final_damage_bonus == D(0)
