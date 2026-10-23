from copy import deepcopy
from decimal import Decimal
from uuid import UUID

from asterion.bot.character_progression_ui import _art_category, _art_mechanics_lines
from asterion.domain.arts import (
    AGOUREIRO_ART_IDS,
    GUARDIAO_ART_IDS,
    INQUISIDOR_ART_IDS,
    INVOCADOR_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Combat,
    DotState,
    Effect,
    Fighter,
    act,
    player_actions_for,
    start_combat,
)
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
        level=52,
        stats=CombatStats(D(1000), D(100), D(100), D(100), crit=D(0), evasion=D(0)),
        hp=D(700),
        character_class=character_class,
        selected_path=path_id,
        side="player",
        takes_turn=True,
    )
    fighters = {
        enemy_id: Fighter(
            id=enemy_id,
            name=f"Enemy {enemy_id}",
            level=52,
            stats=CombatStats(D(10000), D(100), D(0), D(0), crit=D(0), evasion=D(0)),
            hp=D(10000),
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
            level=52,
            stats=CombatStats(D(1000), D(0), D(0), D(0), crit=D(0), evasion=D(0)),
            hp=D(400),
            side="player",
            takes_turn=False,
        )
    actions = class_player_actions(character_class, art_ids, selected_path=path_id)
    return start_combat(
        Combat(
            UUID("b4c1f012-83c4-42fa-ade3-6ba98ea72101"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
        )
    )


def _event(combat: Combat, action_id: str, target_id: str | None = None):
    return next(
        event
        for event in reversed(combat.events)
        if event.action == action_id and (target_id is None or event.target == target_id)
    )


def test_b4_c_art_definitions_are_level_52_path_bound_and_executable():
    expected = (
        (AGOUREIRO_ART_IDS["eclipse_previsto"], "oraculo", "agoureiro"),
        (INVOCADOR_ART_IDS["triade_encarnada"], "oraculo", "invocador"),
        (GUARDIAO_ART_IDS["aurora_guardia"], "luminar", "guardiao"),
        (INQUISIDOR_ART_IDS["veredito"], "luminar", "inquisidor"),
    )
    for art_id, character_class, path_id in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.min_level == 52
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert not definition.weapon_requirement
        assert art_id in PATH_ART_ACTIONS


def test_eclipse_previsto_debuff_requires_consuming_the_offensive_omen_on_same_target():
    art_id = AGOUREIRO_ART_IDS["eclipse_previsto"]
    plain = act(_battle("oraculo", "agoureiro", (art_id,)), art_id, target_id="enemy")
    plain_event = _event(plain, art_id, "enemy")
    assert plain_event.calculated_damage == direct_damage(D(100), D("1.50"), D(0), 52)
    assert not any(effect.id == art_id for effect in plain.fighters["enemy"].effects)
    assert "omen_offensive" not in plain.fighters["player"].path_state

    combat = _battle("oraculo", "agoureiro", (art_id,))
    actor = combat.fighters["player"]
    actor.path_state["omen_offensive"] = {
        "enemy": {"remaining": 2, "applied_opportunity": 0},
    }
    result = act(combat, art_id, target_id="enemy")
    event = _event(result, art_id, "enemy")
    debuff = next(effect for effect in result.fighters["enemy"].effects if effect.id == art_id)
    assert event.path_power_multiplier == D("1.16")
    assert event.applied_effect_stat == "healing_received"
    assert event.applied_effect_magnitude == D("0.15")
    assert debuff.remaining == 2
    # The consumed mark can be regenerated after resolution because this action
    # successfully applies an ordinary Debuff; the new mark is not the old one.
    assert result.fighters["player"].path_state["omen_offensive"]["enemy"]["remaining"] == 2

    wrong_target = _battle("oraculo", "agoureiro", (art_id,), enemy_ids=("a", "b"))
    wrong_target.fighters["player"].path_state["omen_offensive"] = {
        "b": {"remaining": 3, "applied_opportunity": 0},
    }
    missed = act(wrong_target, art_id, target_id="a")
    wrong_event = _event(missed, art_id, "a")
    assert wrong_event.path_power_multiplier == D(1)
    assert not any(effect.id == art_id for effect in missed.fighters["a"].effects)
    assert missed.fighters["player"].path_state["omen_offensive"]["b"]["remaining"] == 2

    defensive = _battle("oraculo", "agoureiro", (art_id,))
    defensive.fighters["player"].path_state["omen_defensive"] = {
        "enemy": {"remaining": 2, "applied_opportunity": 0},
    }
    unqualified = act(defensive, art_id, target_id="enemy")
    assert not any(effect.id == art_id for effect in unqualified.fighters["enemy"].effects)
    assert unqualified.fighters["player"].path_state["omen_defensive"]["enemy"]["remaining"] == 1


def test_triade_encarnada_uses_last_form_without_creating_or_updating_a_manifestation():
    triad = INVOCADOR_ART_IDS["triade_encarnada"]
    lobo = INVOCADOR_ART_IDS["lobo"]
    coruja = INVOCADOR_ART_IDS["coruja"]
    urso = INVOCADOR_ART_IDS["urso"]
    initial = _battle("oraculo", "invocador", (triad, lobo, coruja))
    assert triad not in player_actions_for(initial)
    assert act(initial, triad, target_id="enemy") is initial

    for first, expected_kind in ((lobo, "lobo"), (coruja, "coruja"), (urso, "urso")):
        equipped = (triad, first)
        combat = _battle("oraculo", "invocador", equipped)
        first_target = "player" if first == urso else "enemy"
        prepared = act(combat, first, target_id=first_target)
        actor = prepared.fighters["player"]
        actor.path_state.pop("omen_offensive", None)
        actor.path_state.pop("omen_defensive", None)
        before = deepcopy(actor.path_state["manifestation_state"])
        dynamic_action = player_actions_for(prepared)[triad]
        if expected_kind == "lobo":
            assert dynamic_action.coefficient == D("1.55")
            target_id = "enemy"
        elif expected_kind == "coruja":
            assert dynamic_action.coefficient == D("0.95")
            assert dynamic_action.attack_debuff == D("0.20")
            target_id = "enemy"
        else:
            assert dynamic_action.target_barrier_coefficient == D("1.20")
            target_id = "player"

        restored = decode(encode(prepared), prepared.id, prepared.ruleset, prepared.version)
        assert player_actions_for(restored)[triad] == dynamic_action
        result = act(restored, triad, target_id=target_id)
        event = _event(result, triad, target_id)
        assert "invocador.triade" not in event.path_triggers
        after = result.fighters["player"].path_state["manifestation_state"]
        assert after["kind"] == expected_kind
        assert after["applied_opportunity"] == before["applied_opportunity"]
        assert after["expires_opportunity"] == before["expires_opportunity"]
        assert event.path_power_multiplier == D(1)
        if expected_kind == "lobo":
            assert event.calculated_damage == direct_damage(D(100), D("1.55"), D(0), 52)
        elif expected_kind == "coruja":
            assert event.calculated_damage == direct_damage(D(100), D("0.95"), D(0), 52)
            effect = next(
                effect for effect in result.fighters["enemy"].effects if effect.id == triad
            )
            assert effect.stat == "agility" and effect.magnitude == D("0.20")
            assert effect.remaining == 2
        else:
            assert event.barrier_value == D(120)
            assert event.barrier_duration == 2
        assert len(result.fighters) == len(combat.fighters)


def test_triade_encarnada_is_unavailable_after_expired_last_manifestation():
    triad = INVOCADOR_ART_IDS["triade_encarnada"]
    combat = _battle("oraculo", "invocador", (triad,))
    combat.fighters["player"].path_state["manifestation_state"] = {
        "kind": "urso",
        "remaining": 1,
        "applied_opportunity": 0,
        "expires_opportunity": -1,
    }
    assert triad not in player_actions_for(combat)
    assert act(combat, triad, target_id="player") is combat


def test_aurora_guardia_heals_all_living_allies_and_consumes_fulgor_once():
    art_id = GUARDIAO_ART_IDS["aurora_guardia"]
    combat = _battle("luminar", "guardiao", (art_id,), include_ally=True)
    combat.fighters["player"].path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    combat.fighters["ally"].hp = D(100)

    result = act(combat, art_id)
    events = [event for event in result.events if event.action == art_id]

    assert {event.target for event in events} == {"player", "ally"}
    assert all(event.path_power_multiplier == D("1.15") for event in events)
    assert all(event.effective_healing > 0 for event in events)
    assert sum(
        row[2]
        for event in events
        for row in event.class_resource_changes
        if row[0] == "luminar_state"
    ) == 1
    assert "luminar_state" not in result.fighters["player"].path_state
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["ally"].hp == result.fighters["ally"].hp

    generated = act(_battle("luminar", "guardiao", (art_id,), include_ally=True), art_id)
    assert generated.fighters["player"].path_state["luminar_state"]["kind"] == "julgamento"


def test_veredito_requires_a_live_normal_debuff_and_keeps_julgamento_power_independent():
    art_id = INQUISIDOR_ART_IDS["veredito"]
    active = _battle("luminar", "inquisidor", (art_id,))
    active.fighters["enemy"].effects.append(Effect("atk_down", "attack", D("0.1"), 2, 0))
    active.fighters["player"].path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 2,
        "applied_opportunity": 0,
    }
    result = act(active, art_id, target_id="enemy")
    event = _event(result, art_id, "enemy")
    assert event.path_crit_bonus == D(10)
    assert event.path_power_multiplier == D("1.15")
    assert result.fighters["player"].path_state.get("luminar_state") is None

    for effects, dots in (
        ((), (DotState("bleed", 1, 2, D(100), "fixture"),)),
        ((Effect("expired", "attack", D("0.1"), 0, 0),), ()),
        ((Effect("fixed", "attack", D("0.1"), 2, 0, fixed_mechanic=True),), ()),
    ):
        no_debuff = _battle("luminar", "inquisidor", (art_id,))
        no_debuff.fighters["enemy"].effects.extend(effects)
        no_debuff.dot_states["enemy"] = list(dots)
        unqualified = act(no_debuff, art_id, target_id="enemy")
        assert _event(unqualified, art_id, "enemy").path_crit_bonus == D(0)


def test_b4_c_ui_describes_omen_debuff_veredito_and_dynamic_triad_forms():
    eclipse = class_player_actions(
        "oraculo", (AGOUREIRO_ART_IDS["eclipse_previsto"],), selected_path="agoureiro"
    )[AGOUREIRO_ART_IDS["eclipse_previsto"]]
    assert any(
        "Ao consumir Presságio Ofensivo" in line and "Cura recebida" in line
        for line in _art_mechanics_lines(eclipse)
    )
    veredito = class_player_actions(
        "luminar", (INQUISIDOR_ART_IDS["veredito"],), selected_path="inquisidor"
    )[INQUISIDOR_ART_IDS["veredito"]]
    assert any(
        "Debuff normal válido" in line and "+10 p.p. CRIT" in line
        for line in _art_mechanics_lines(veredito)
    )
    triad = class_player_actions(
        "oraculo", (INVOCADOR_ART_IDS["triade_encarnada"],), selected_path="invocador"
    )[INVOCADOR_ART_IDS["triade_encarnada"]]
    lines = _art_mechanics_lines(triad)
    assert _art_category(triad) == "Manifestação"
    assert any("Lobo" in line and "155% ATQ" in line for line in lines)
    assert any("Coruja" in line and "−20% AGI" in line for line in lines)
    assert any("Urso" in line and "120% ATQ" in line for line in lines)
