from decimal import Decimal
from uuid import UUID

from asterion.domain.arts import (
    ATIRADOR_ART_IDS,
    CONJURADOR_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Combat, Effect, Fighter, act, start_combat
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.path_arts import PATH_ART_ACTIONS
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(
    character_class: str,
    path_id: str,
    art_ids: tuple[str, ...],
    *,
    enemy_ids: tuple[str, ...] = ("enemy",),
    include_ally: bool = False,
) -> Combat:
    player = Fighter(
        id="player",
        name="Player",
        level=38,
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
            level=38,
            stats=CombatStats(D(1000), D(100), D(0), D(0), crit=D(0), evasion=D(0)),
            hp=D(1000),
            side="enemy",
            takes_turn=False,
        )
        for enemy_id in enemy_ids
    }
    fighters["player"] = player
    if include_ally:
        fighters["ally"] = Fighter(
            id="ally",
            name="Ally",
            level=38,
            stats=CombatStats(D(1000), D(0), D(0), D(0), evasion=D(0)),
            hp=D(500),
            side="player",
            takes_turn=False,
        )
    actions = class_player_actions(character_class, art_ids, selected_path=path_id)
    return start_combat(
        Combat(
            UUID("b38b1f12-83c4-42fa-ade3-6ba98ea72101"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
        )
    )


def _event(combat: Combat, action_id: str, target: str | None = None):
    return next(
        event
        for event in reversed(combat.events)
        if event.action == action_id and (target is None or event.target == target)
    )


def test_b3_b_definitions_bind_level_38_class_path_and_weapon_requirements():
    expected = (
        (ATIRADOR_ART_IDS["rajada_controlada"], "vigia", "atirador", True),
        (RASTREADOR_ART_IDS["chuva_de_rastros"], "vigia", "rastreador", True),
        (CONJURADOR_ART_IDS["convergencia_arcana"], "tecelao", "conjurador", False),
        (RUNICO_ART_IDS["runa_de_retorno"], "tecelao", "runico", False),
    )
    for art_id, character_class, path_id, weapon_required in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.min_level == 38
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert bool(definition.weapon_requirement) is weapon_required
        assert art_id in PATH_ART_ACTIONS


def test_rajada_controlada_resolves_three_hits_and_generates_at_most_one_mira():
    art_id = ATIRADOR_ART_IDS["rajada_controlada"]
    combat = _battle("vigia", "atirador", (art_id,))
    result = act(combat, art_id, target_id="enemy")
    events = [event for event in result.events if event.action == art_id]
    assert len(events) == 3
    assert [event.calculated_damage for event in events] == [
        direct_damage(D(100), D("0.45"), D(0), 38)
    ] * 3
    assert result.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 1
    assert result.fighters["player"].action_use_counts[art_id] == 1

    many_miras = _battle("vigia", "atirador", (art_id,))
    many_miras.fighters["enemy"].path_state["aim_from"] = {
        "player": {
            "stacks": 3,
            "remaining": 2,
            "applied_opportunity": 0,
            "trigger": "fixture",
        }
    }
    capped = act(many_miras, art_id, target_id="enemy")
    capped_events = [event for event in capped.events if event.action == art_id]
    assert all(event.path_per_bonus == D(9) for event in capped_events)
    assert capped.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 4

    restored = decode(encode(capped), capped.id, capped.ruleset, capped.version)
    assert restored.player_actions[art_id].hit_count == 3
    assert restored.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 4


def test_chuva_de_rastros_grants_one_mira_per_eligible_target_without_exceeding_cap():
    art_id = RASTREADOR_ART_IDS["chuva_de_rastros"]
    combat = _battle(
        "vigia", "rastreador", (art_id,), enemy_ids=("e1", "e2", "e3", "e4")
    )
    combat.fighters["e1"].path_state["aim_from"] = {
        "player": {"stacks": 1, "remaining": 1, "applied_opportunity": 0}
    }
    combat.fighters["e2"].path_state["aim_from"] = {
        "player": {"stacks": 2, "remaining": 1, "applied_opportunity": 0}
    }
    combat.fighters["e3"].path_state["aim_from"] = {
        "player": {"stacks": 1, "remaining": 1, "applied_opportunity": 0}
    }
    result = act(combat, art_id)
    events = [event for event in result.events if event.action == art_id]
    assert {event.target for event in events} == {"e1", "e2", "e3", "e4"}
    expected_damage = direct_damage(D(100), D("0.70"), D(0), 38)
    assert all(event.calculated_damage == expected_damage for event in events)
    assert result.fighters["e1"].path_state["aim_from"]["player"]["stacks"] == 2
    assert result.fighters["e2"].path_state["aim_from"]["player"]["stacks"] == 2
    assert result.fighters["e3"].path_state["aim_from"]["player"]["stacks"] == 2
    assert "aim_from" not in result.fighters["e4"].path_state


def test_convergencia_arcana_consumes_one_trama_for_three_hits_and_respects_origin():
    art_id = CONJURADOR_ART_IDS["convergencia_arcana"]
    empowered = _battle("tecelao", "conjurador", (art_id,))
    empowered.fighters["player"].path_state["trama_state"] = {
        "origin_art": CONJURADOR_ART_IDS["estilhaco_do_veu"],
        "remaining": 2,
        "applied_opportunity": 0,
    }
    consumed = act(empowered, art_id, target_id="enemy")
    events = [event for event in consumed.events if event.action == art_id]
    assert len(events) == 3
    assert all(event.path_power_multiplier == D("1.15") for event in events)
    assert all(
        event.calculated_damage == direct_damage(D(100), D("0.50") * D("1.15"), D(0), 38)
        for event in events
    )
    assert "trama_state" not in consumed.fighters["player"].path_state
    assert consumed.fighters["player"].action_use_counts[art_id] == 1

    same_origin = _battle("tecelao", "conjurador", (art_id,))
    same_origin.fighters["player"].path_state["trama_state"] = {
        "origin_art": art_id,
        "remaining": 2,
        "applied_opportunity": 0,
    }
    repeated = act(same_origin, art_id, target_id="enemy")
    assert all(
        event.path_power_multiplier == D(1)
        for event in repeated.events
        if event.action == art_id
    )
    assert repeated.fighters["player"].path_state["trama_state"]["origin_art"] == art_id


def test_runa_de_retorno_heals_and_purifies_one_removable_effect_then_generates_trama():
    art_id = RUNICO_ART_IDS["runa_de_retorno"]
    combat = _battle("tecelao", "runico", (art_id,), include_ally=True)
    ally = combat.fighters["ally"]
    ally.effects.extend(
        (
            Effect("removable", "attack", D("0.20"), 2, 0),
            Effect(
                "fixed", "defense", D("0.10"), 2, 0,
                removable=False, unremovable=True, fixed_mechanic=True,
            ),
        )
    )
    result = act(combat, art_id, target_id="ally")
    event = _event(result, art_id, "ally")
    assert event.effective_healing == D(70)
    assert event.removed_effect_ids == ("removable",)
    assert [effect.id for effect in result.fighters["ally"].effects] == ["fixed"]
    trama = result.fighters["player"].path_state["trama_state"]
    assert trama["origin_art"] == art_id
    assert trama["remaining"] == 2


def test_runa_de_retorno_consumes_runic_trama_once_and_removal_never_requires_heal_value():
    art_id = RUNICO_ART_IDS["runa_de_retorno"]
    combat = _battle("tecelao", "runico", (art_id,), include_ally=True)
    actor = combat.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": RUNICO_ART_IDS["runa_de_guarda"],
        "remaining": 2,
        "applied_opportunity": 0,
    }
    ally = combat.fighters["ally"]
    ally.hp = ally.stats.hp
    ally.effects.append(Effect("debuff", "attack", D("0.10"), 2, 0))
    result = act(combat, art_id, target_id="ally")
    event = _event(result, art_id, "ally")
    assert event.effective_healing == D(0)
    assert event.path_power_multiplier == D("1.15")
    assert event.removed_effect_ids == ("debuff",)
    assert "trama_state" not in result.fighters["player"].path_state
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.player_actions[art_id].effect_removal.kind == "purification"
