from decimal import ROUND_FLOOR, Decimal
from uuid import UUID

from asterion.domain.arts import (
    ATIRADOR_ART_IDS,
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    CONJURADOR_ART_IDS,
    DEVASTADOR_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    SABOTADOR_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, Combat, Fighter, _perform, act, start_combat
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.path_arts import PATH_ART_ACTIONS
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(
    character_class: str,
    path_id: str,
    art_ids: tuple[str, ...],
    *,
    include_ally: bool = False,
    enemy_ids: tuple[str, ...] = ("enemy",),
) -> Combat:
    player = Fighter(
        id="player",
        name="Player",
        level=22,
        stats=CombatStats(D(1000), D(100), D(100), D(100), crit=D(0), evasion=D(0)),
        hp=D(1000),
        character_class=character_class,
        selected_path=path_id,
        takes_turn=True,
    )
    fighters = {
        enemy_id: Fighter(
            id=enemy_id,
            name=f"Enemy {enemy_id}",
            level=22,
            stats=CombatStats(
                D(1000), D(100), D(0), D(0), crit=D(0), evasion=D(0)
            ),
            hp=D(1000),
            side="enemy",
            takes_turn=False,
        )
        for enemy_id in enemy_ids
    }
    fighters["player"] = player
    ai_target_cycle = ("player",)
    if include_ally:
        fighters["ally"] = Fighter(
            id="ally",
            name="Ally",
            level=22,
            stats=CombatStats(D(1000), D(0), D(0), D(0), evasion=D(0)),
            hp=D(1000),
            side="player",
            takes_turn=False,
        )
        ai_target_cycle = ("ally",)
    actions = class_player_actions(
        character_class,
        art_ids,
        selected_path=path_id,
    )
    return start_combat(
        Combat(
            UUID("a81c7af2-8340-4f6a-a4e3-c40d1d410012"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
            ai_target_cycle=ai_target_cycle,
        )
    )


def test_b2_lot_a_path_art_definitions_are_level_22_and_path_bound():
    expected = (
        (BASTIAO_ART_IDS["interpor"], "sentinela", "bastiao", False),
        (DEVASTADOR_ART_IDS["golpe_de_ruptura"], "sentinela", "devastador", True),
        (CARRASCO_ART_IDS["hemorragia"], "errante", "carrasco", True),
        (SABOTADOR_ART_IDS["fio_cortado"], "errante", "sabotador", True),
    )
    for art_id, character_class, path_id, weapon_required in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert definition.min_level == 22
        assert bool(definition.weapon_requirement) is weapon_required
        assert art_id in PATH_ART_ACTIONS


def test_interpor_protects_selected_ally_once_before_barrier_and_survives_codec():
    art_id = BASTIAO_ART_IDS["interpor"]
    combat = _battle(
        "sentinela",
        "bastiao",
        (art_id,),
        include_ally=True,
    )
    protected = act(combat, art_id, target_id="ally")
    effect = next(
        effect
        for effect in protected.fighters["ally"].effects
        if effect.stat == "interpor_next_direct"
    )
    assert effect.magnitude == D("0.25")
    assert effect.remaining == 2
    assert not any(
        candidate.stat == "interpor_next_direct"
        for candidate in protected.fighters["player"].effects
    )

    restored = decode(encode(protected), protected.id, protected.ruleset, protected.version)
    assert next(
        candidate
        for candidate in restored.fighters["ally"].effects
        if candidate.stat == "interpor_next_direct"
    ).remaining == 2
    restored.enemy_actions["incoming"] = Action("incoming", "Incoming", D(1))
    assert _perform(restored, "enemy", "incoming", target_id="ally")
    hit = restored
    event = next(event for event in hit.events if event.action == "incoming")
    assert event.calculated_damage == int(
        (D(direct_damage(D(100), D(1), D(0), 22)) * D("0.75")).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    assert "sentinela.interpor_consumido" in event.path_triggers
    assert not any(
        effect.stat == "interpor_next_direct" for effect in hit.fighters["ally"].effects
    )


def test_interpor_self_target_uses_one_reduction_and_never_reduces_dot_ticks():
    art_id = BASTIAO_ART_IDS["interpor"]
    combat = _battle("sentinela", "bastiao", (art_id,))
    protected = act(combat, art_id, target_id="player")
    assert any(
        effect.stat == "interpor_next_direct" for effect in protected.fighters["player"].effects
    )
    protected.enemy_actions["incoming"] = Action("incoming", "Incoming", D(1))
    assert _perform(protected, "enemy", "incoming", target_id="player")
    hit = protected
    event = next(event for event in hit.events if event.action == "incoming")
    assert event.calculated_damage == int(
        (
            D(direct_damage(D(100), D(1), D(100), 22)) * D("0.75")
        ).to_integral_value(rounding=ROUND_FLOOR)
    )
    assert not any(
        effect.stat == "interpor_next_direct" for effect in hit.fighters["player"].effects
    )


def test_golpe_de_ruptura_uses_retaliation_power_once_on_valid_commit():
    art_id = DEVASTADOR_ART_IDS["golpe_de_ruptura"]
    regular = _battle("sentinela", "devastador", (art_id,))
    regular_result = act(regular, art_id, target_id="enemy")
    regular_event = next(event for event in regular_result.events if event.action == art_id)
    assert regular_event.calculated_damage == direct_damage(
        D(100), D("1.25"), D(0), 22
    )

    empowered = _battle("sentinela", "devastador", (art_id,))
    empowered.fighters["player"].retaliation_charges = 1
    empowered.fighters["player"].retaliation_remaining = 1
    empowered.fighters["player"].retaliation_activation_id = "test:retaliation"
    empowered_result = act(empowered, art_id, target_id="enemy")
    event = next(event for event in empowered_result.events if event.action == art_id)
    assert event.path_power_multiplier == D("1.20")
    assert event.calculated_damage == direct_damage(D(100), D("1.50"), D(0), 22)
    assert event.retaliation_used
    assert empowered_result.fighters["player"].retaliation_charges == 0


def test_hemorragia_applies_two_canonical_bleed_stacks_once():
    art_id = CARRASCO_ART_IDS["hemorragia"]
    combat = _battle("errante", "carrasco", (art_id,))
    result = act(combat, art_id, target_id="enemy")
    event = next(event for event in result.events if event.action == art_id)
    dots = result.dot_states["enemy"]
    assert event.dot_kind == "bleed"
    assert len(dots) == 1
    assert dots[0].kind == "bleed"
    assert dots[0].stacks == 2
    assert dots[0].remaining == 2
    assert len(dots[0].stack_snapshots) == 2


def test_fio_cortado_applies_sabotador_interference_to_atk_debuff_duration():
    art_id = SABOTADOR_ART_IDS["fio_cortado"]
    combat = _battle("errante", "sabotador", (art_id,))
    result = act(combat, art_id, target_id="enemy")
    event = next(event for event in result.events if event.action == art_id)
    effect = next(effect for effect in result.fighters["enemy"].effects if effect.id == art_id)
    assert event.effective_damage > 0
    assert effect.stat == "attack"
    assert effect.kind == "debuff"
    assert effect.magnitude == D("0.12")
    assert effect.remaining == 3


def test_fixar_alvo_adds_one_extra_mira_and_atirador_per_is_calculated_next_action():
    fixar_alvo = ATIRADOR_ART_IDS["fixar_alvo"]
    tiro_perfurante = ATIRADOR_ART_IDS["tiro_perfurante"]
    combat = _battle("vigia", "atirador", (fixar_alvo, tiro_perfurante))
    aimed = act(combat, fixar_alvo, target_id="enemy")
    entry = aimed.fighters["enemy"].path_state["aim_from"]["player"]
    assert entry["stacks"] == 2
    assert entry["remaining"] == 2
    aim_event = next(event for event in aimed.events if event.action == fixar_alvo)
    assert aim_event.aim_stacks == 2

    followup = act(aimed, tiro_perfurante, target_id="enemy")
    followup_event = next(event for event in followup.events if event.action == tiro_perfurante)
    # The snapshot grants Mira Perfeita from two existing stacks; the action's
    # own successful hit then generates the normal third stack.
    assert followup_event.aim_stacks == 3
    assert followup_event.path_per_bonus == D(6)


def test_fixar_alvo_respects_atirador_cap_of_four_miras():
    art_id = ATIRADOR_ART_IDS["fixar_alvo"]
    combat = _battle("vigia", "atirador", (art_id,))
    combat.fighters["enemy"].path_state["aim_from"] = {
        "player": {
            "stacks": 3,
            "remaining": 1,
            "applied_opportunity": 0,
            "trigger": "test",
        }
    }
    result = act(combat, art_id, target_id="enemy")
    assert result.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 4


def test_laco_de_caca_applies_agility_reduction_and_rastros_multiple_generates_one_mira():
    art_id = RASTREADOR_ART_IDS["laco_de_caca"]
    combat = _battle("vigia", "rastreador", (art_id,))
    result = act(combat, art_id, target_id="enemy")
    target = result.fighters["enemy"]
    effect = next(effect for effect in target.effects if effect.id == art_id)
    event = next(event for event in result.events if event.action == art_id)
    assert event.calculated_damage == direct_damage(D(100), D("0.80"), D(0), 22)
    assert effect.stat == "agility"
    assert effect.kind == "debuff"
    assert effect.magnitude == D("0.20")
    assert effect.remaining == 2
    assert target.path_state["aim_from"]["player"]["stacks"] == 1
    # The direct-hit Mira and Rastros Múltiplos share one per-action grant.
    assert event.path_triggers.count("vigia.mira_gerada") == 1
    assert "rastreador.mira_gerada" not in event.path_triggers


def test_incendio_trancado_applies_one_burn_per_target_and_one_trama_per_action():
    art_id = CONJURADOR_ART_IDS["incendio_trancado"]
    enemies = ("e1", "e2", "e3")
    combat = _battle("tecelao", "conjurador", (art_id,), enemy_ids=enemies)
    result = act(combat, art_id)
    events = [event for event in result.events if event.action == art_id]
    assert {event.target for event in events} == set(enemies)
    expected_damage = direct_damage(D(100), D("0.75"), D(0), 22)
    assert all(event.calculated_damage == expected_damage for event in events)
    for enemy in enemies:
        dot = result.dot_states[enemy][0]
        assert dot.kind == "burn" and dot.stacks == 1 and dot.remaining == 2
    trama = result.fighters["player"].path_state["trama_state"]
    assert trama["origin_art"] == art_id
    assert trama["remaining"] == 2
    assert trama["applied_opportunity"] == result.fighters["player"].opportunity - 1

    empowered = _battle("tecelao", "conjurador", (art_id,), enemy_ids=enemies)
    empowered.fighters["player"].path_state["trama_state"] = {
        "origin_art": "path_art.tecelao.conjurador.estilhaco_do_veu",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    consumed = act(empowered, art_id)
    empowered_events = [event for event in consumed.events if event.action == art_id]
    assert len(empowered_events) == 3
    assert all(event.path_power_multiplier == D("1.15") for event in empowered_events)
    assert "trama_state" not in consumed.fighters["player"].path_state


def test_runa_de_ruptura_applies_defense_debuff_and_respects_trama_origin():
    art_id = RUNICO_ART_IDS["runa_de_ruptura"]
    combat = _battle("tecelao", "runico", (art_id,))
    first = act(combat, art_id, target_id="enemy")
    effect = next(effect for effect in first.fighters["enemy"].effects if effect.id == art_id)
    assert effect.stat == "defense"
    assert effect.magnitude == D("0.10")
    assert effect.remaining == 2
    assert first.fighters["player"].path_state["trama_state"]["origin_art"] == art_id

    same_origin = _battle("tecelao", "runico", (art_id,))
    same_origin.fighters["player"].path_state["trama_state"] = {
        "origin_art": art_id,
        "remaining": 2,
        "applied_opportunity": 0,
    }
    repeated = act(same_origin, art_id, target_id="enemy")
    assert repeated.fighters["player"].path_state["trama_state"]["remaining"] == 1
    repeated_event = next(event for event in repeated.events if event.action == art_id)
    assert repeated_event.path_power_multiplier == D(1)

    other_origin = _battle("tecelao", "runico", (art_id,))
    other_origin.fighters["player"].path_state["trama_state"] = {
        "origin_art": "path_art.tecelao.runico.runa_de_guarda",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    consumed = act(other_origin, art_id, target_id="enemy")
    consumed_event = next(event for event in consumed.events if event.action == art_id)
    assert consumed_event.path_power_multiplier == D("1.06")
    assert next(
        effect for effect in consumed.fighters["enemy"].effects if effect.id == art_id
    ).magnitude == D("0.10")
    assert "trama_state" not in consumed.fighters["player"].path_state
