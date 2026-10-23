from decimal import Decimal
from uuid import UUID

from asterion.bot.character_progression_ui import _art_mechanics_lines
from asterion.domain.arts import (
    AGOUREIRO_ART_IDS,
    GUARDIAO_ART_IDS,
    INQUISIDOR_ART_IDS,
    INVOCADOR_ART_IDS,
    ORACULO_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Combat, Effect, Fighter, act, start_combat
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.path_arts import PATH_ART_ACTIONS
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)


def _battle(
    character_class: str,
    path_id: str,
    art_ids: tuple[str, ...],
    *,
    enemy_evasion: Decimal = ZERO,
    include_ally: bool = False,
) -> Combat:
    player = Fighter(
        id="player",
        name="Player",
        level=38,
        stats=CombatStats(D(1000), D(100), D(100), D(100), crit=D(0), evasion=D(0)),
        hp=D(500),
        character_class=character_class,
        selected_path=path_id,
        takes_turn=True,
    )
    fighters = {
        "enemy": Fighter(
            id="enemy",
            name="Enemy",
            level=38,
            stats=CombatStats(
                D(2000), D(100), D(0), D(0), crit=D(0), evasion=enemy_evasion
            ),
            hp=D(2000),
            side="enemy",
            takes_turn=False,
        ),
        "player": player,
    }
    ai_target_cycle = ("player",)
    if include_ally:
        fighters["ally"] = Fighter(
            id="ally",
            name="Ally",
            level=38,
            stats=CombatStats(D(1000), D(0), D(0), D(0), evasion=D(0)),
            hp=D(400),
            side="player",
            takes_turn=False,
        )
        ai_target_cycle = ("ally",)
    actions = class_player_actions(character_class, art_ids, selected_path=path_id)
    return start_combat(
        Combat(
            UUID("b38c1f12-83c4-42fa-ade3-6ba98ea72101"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
            ai_target_cycle=ai_target_cycle,
        )
    )


def _event(combat: Combat, action_id: str, target: str | None = None):
    return next(
        event
        for event in reversed(combat.events)
        if event.action == action_id and (target is None or event.target == target)
    )


def test_b3_c_definitions_are_level_38_path_bound_and_executable():
    expected = (
        (AGOUREIRO_ART_IDS["condenacao"], "oraculo", "agoureiro"),
        (INVOCADOR_ART_IDS["urso"], "oraculo", "invocador"),
        (GUARDIAO_ART_IDS["purgacao_luminosa"], "luminar", "guardiao"),
        (INQUISIDOR_ART_IDS["purga_ardente"], "luminar", "inquisidor"),
    )
    for art_id, character_class, path_id in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.min_level == 38
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert not definition.weapon_requirement
        assert art_id in PATH_ART_ACTIONS


def test_condenacao_ui_explains_its_future_agoureiro_action_bonus():
    condemn = AGOUREIRO_ART_IDS["condenacao"]
    followup = AGOUREIRO_ART_IDS["mau_agouro"]
    actions = class_player_actions(
        "oraculo", (condemn, followup), selected_path="agoureiro"
    )
    for art_id in (condemn, followup):
        lines = _art_mechanics_lines(actions[art_id])
        assert any(
            "próxima Arte do Agoureiro" in line and "+20%" in line for line in lines
        )


def test_condenacao_prepares_one_agoureiro_art_for_twenty_percent_power():
    condemn = AGOUREIRO_ART_IDS["condenacao"]
    followup = AGOUREIRO_ART_IDS["mau_agouro"]
    combat = _battle("oraculo", "agoureiro", (condemn, followup))

    prepared = act(combat, condemn, target_id="enemy")
    first_event = _event(prepared, condemn, "enemy")
    assert first_event.calculated_damage == direct_damage(D(100), D("0.80"), D(0), 38)
    assert first_event.chain_window_after == 2
    assert prepared.fighters["player"].action_chains[
        "oraculo.agoureiro.condemnacao"
    ]["remaining"] == 2

    restored = decode(encode(prepared), prepared.id, prepared.ruleset, prepared.version)
    assert restored.fighters["player"].action_chains[
        "oraculo.agoureiro.condemnacao"
    ]["remaining"] == 2
    empowered = act(restored, followup, target_id="enemy")
    event = _event(empowered, followup, "enemy")
    assert event.chain_consumed is True
    assert event.damage_power_multiplier == D("1.20")
    assert event.calculated_damage == direct_damage(D(100), D("0.95") * D("1.20"), D(0), 38)
    assert "oraculo.agoureiro.condemnacao" not in empowered.fighters["player"].action_chains


def test_invalid_agoureiro_followup_does_not_consume_condemnacao_preparation():
    condemn = AGOUREIRO_ART_IDS["condenacao"]
    followup = AGOUREIRO_ART_IDS["destino_lento"]
    combat = _battle("oraculo", "agoureiro", (condemn, followup))
    prepared = act(combat, condemn, target_id="enemy")
    invalid = act(prepared, followup, target_id="missing")
    assert invalid is prepared
    assert "oraculo.agoureiro.condemnacao" in prepared.fighters["player"].action_chains
    assert followup not in prepared.fighters["player"].cooldowns


def test_condemnacao_chain_only_empowers_an_agoureiro_path_art_and_omen_is_independent():
    condemn = AGOUREIRO_ART_IDS["condenacao"]
    mau_agouro = AGOUREIRO_ART_IDS["mau_agouro"]
    class_art = ORACULO_ART_IDS["sinal_funesto"]
    combat = _battle("oraculo", "agoureiro", (condemn, mau_agouro, class_art))
    combat.fighters["player"].path_state["omen_offensive"] = {
        "enemy": {"remaining": 2, "applied_opportunity": 0, "source_action_id": "test"}
    }

    prepared = act(combat, condemn, target_id="enemy")
    first = _event(prepared, condemn, "enemy")
    assert first.path_power_multiplier == D("1.16")
    assert first.class_resource_changes == (("omen_offensive", "enemy", 1, 0),)
    assert not prepared.fighters["player"].path_state.get("omen_offensive", {})
    assert "oraculo.agoureiro.condemnacao" in prepared.fighters["player"].action_chains

    class_result = act(prepared, class_art, target_id="enemy")
    class_event = _event(class_result, class_art, "enemy")
    assert class_event.chain_consumed is False
    assert "oraculo.agoureiro.condemnacao" in class_result.fighters["player"].action_chains

    path_result = act(class_result, mau_agouro, target_id="enemy")
    path_event = _event(path_result, mau_agouro, "enemy")
    assert path_event.chain_consumed is True
    assert path_event.damage_power_multiplier == D("1.20")
    assert "oraculo.agoureiro.condemnacao" not in path_result.fighters["player"].action_chains


def test_urso_is_a_self_barrier_manifestation_with_triada_and_omen_without_pet():
    lobo = INVOCADOR_ART_IDS["lobo"]
    coruja = INVOCADOR_ART_IDS["coruja"]
    urso = INVOCADOR_ART_IDS["urso"]
    for first in (lobo, coruja):
        combat = _battle("oraculo", "invocador", (lobo, coruja, urso))
        before_count = len(combat.fighters)
        prepared = act(combat, first, target_id="enemy")
        result = act(prepared, urso, target_id="player")
        event = _event(result, urso, "player")
        assert event.barrier_value == D(112)
        assert event.barrier_duration == 2
        assert event.path_power_multiplier == D("1.12")
        assert "invocador.triade" in event.path_triggers
        assert result.fighters["player"].barrier == D(112)
        assert result.fighters["player"].path_state["manifestation_state"]["kind"] == "urso"
        assert result.fighters["player"].path_state["omen_defensive"]["player"]["remaining"] > 0
        assert len(result.fighters) == before_count
        restored = decode(encode(result), result.id, result.ruleset, result.version)
        assert restored.fighters["player"].path_state["manifestation_state"]["kind"] == "urso"
        assert restored.fighters["player"].barrier == D(112)

    repeated = _battle("oraculo", "invocador", (urso,))
    repeated.fighters["player"].path_state["manifestation_state"] = {
        "kind": "urso",
        "remaining": 2,
        "applied_opportunity": 0,
        "expires_opportunity": 5,
    }
    repeated_result = act(repeated, urso, target_id="player")
    repeated_event = _event(repeated_result, urso, "player")
    assert repeated_event.barrier_value == D(100)
    assert repeated_event.path_power_multiplier == D(1)
    assert "invocador.triade" not in repeated_event.path_triggers


def test_purgacao_luminosa_heals_purifies_one_effect_and_uses_fulgor_once():
    art_id = GUARDIAO_ART_IDS["purgacao_luminosa"]
    combat = _battle("luminar", "guardiao", (art_id,), include_ally=True)
    actor = combat.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    ally = combat.fighters["ally"]
    ally.effects.extend(
        (
            Effect("debuff", "attack", D("0.10"), 2, 0),
            Effect("fixed", "defense", D("0.10"), 2, 0, unremovable=True),
        )
    )

    result = act(combat, art_id, target_id="ally")
    event = _event(result, art_id, "ally")
    assert event.path_power_multiplier == D("1.15")
    assert event.effective_healing > 0
    assert event.removed_effect_ids == ("debuff",)
    assert [effect.id for effect in result.fighters["ally"].effects] == ["fixed"]
    assert event.class_resource_changes == (("luminar_state", "player", 1, 0),)
    assert "luminar_state" not in result.fighters["player"].path_state
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["ally"].hp == result.fighters["ally"].hp


def test_purgacao_luminosa_without_eligible_effect_still_heals_and_generates_julgamento():
    art_id = GUARDIAO_ART_IDS["purgacao_luminosa"]
    combat = _battle("luminar", "guardiao", (art_id,), include_ally=True)
    result = act(combat, art_id, target_id="ally")
    event = _event(result, art_id, "ally")
    assert event.effective_healing > 0
    assert event.effect_removal_result == "no_eligible_effect"
    assert result.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"


def test_purgacao_luminosa_zero_effective_healing_still_consumes_fulgor_and_purifies():
    art_id = GUARDIAO_ART_IDS["purgacao_luminosa"]
    combat = _battle("luminar", "guardiao", (art_id,), include_ally=True)
    actor = combat.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    ally = combat.fighters["ally"]
    ally.hp = ally.stats.hp
    ally.effects.append(Effect("debuff", "attack", D("0.10"), 2, 0))

    result = act(combat, art_id, target_id="ally")
    event = _event(result, art_id, "ally")
    assert event.effective_healing == D(0)
    assert event.removed_effect_ids == ("debuff",)
    assert event.class_resource_changes == (("luminar_state", "player", 1, 0),)
    assert "luminar_state" not in result.fighters["player"].path_state


def test_purga_ardente_dispels_one_positive_effect_after_damage_and_consumes_julgamento():
    art_id = INQUISIDOR_ART_IDS["purga_ardente"]
    combat = _battle("luminar", "inquisidor", (art_id,))
    combat.fighters["player"].path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    target = combat.fighters["enemy"]
    target.effects.extend(
        (
            Effect("removable", "attack", D("0.10"), 2, 0, kind="buff"),
            Effect(
                "fixed", "defense", D("0.10"), 2, 0,
                kind="buff", unremovable=True, fixed_mechanic=True,
            ),
        )
    )

    result = act(combat, art_id, target_id="enemy")
    event = _event(result, art_id, "enemy")
    assert event.calculated_damage == direct_damage(D(100), D("1.20") * D("1.15"), D(0), 38)
    assert event.path_power_multiplier == D("1.15")
    assert event.removed_effect_ids == ("removable",)
    assert [effect.id for effect in result.fighters["enemy"].effects] == ["fixed"]
    assert event.effect_removal_component == "dispel"
    assert event.class_resource_changes == (("luminar_state", "player", 1, 0),)
    assert "luminar_state" not in result.fighters["player"].path_state
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["enemy"].effects[0].id == "fixed"


def test_purga_ardente_requires_a_successful_hit_for_dispel_and_generates_fulgor():
    art_id = INQUISIDOR_ART_IDS["purga_ardente"]
    combat = _battle("luminar", "inquisidor", (art_id,), enemy_evasion=D(100))
    combat.fighters["enemy"].effects.append(
        Effect("buff", "attack", D("0.10"), 2, 0, kind="buff")
    )
    result = act(combat, art_id, target_id="enemy")
    event = _event(result, art_id, "enemy")
    assert event.dodged is True
    assert event.effect_removal_result == "missed"
    assert result.fighters["enemy"].effects[0].id == "buff"
    assert result.fighters["player"].path_state["luminar_state"]["kind"] == "fulgor"


def test_purga_ardente_with_no_dissipatable_buff_keeps_damage_action_valid():
    art_id = INQUISIDOR_ART_IDS["purga_ardente"]
    combat = _battle("luminar", "inquisidor", (art_id,))
    combat.fighters["enemy"].effects.append(
        Effect("fixed", "attack", D("0.10"), 2, 0, kind="buff", fixed_mechanic=True)
    )
    result = act(combat, art_id, target_id="enemy")
    event = _event(result, art_id, "enemy")
    assert event.calculated_damage == direct_damage(D(100), D("1.20"), D(0), 38)
    assert event.effect_removal_result == "no_eligible_effect"
    assert result.fighters["enemy"].effects[0].id == "fixed"
    assert result.fighters["player"].path_state["luminar_state"]["kind"] == "fulgor"
