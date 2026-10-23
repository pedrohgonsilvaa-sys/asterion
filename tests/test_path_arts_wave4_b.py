from decimal import Decimal
from uuid import UUID

from asterion.bot.character_progression_ui import _art_mechanics_lines
from asterion.domain.arts import (
    ATIRADOR_ART_IDS,
    CONJURADOR_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Combat, DotState, Effect, Fighter, act, start_combat
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
        hp=D(800),
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
            UUID("b4b1f012-83c4-42fa-ade3-6ba98ea72101"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
        )
    )


def _events(combat: Combat, action_id: str):
    return [event for event in combat.events if event.action == action_id]


def test_b4_b_art_definitions_are_level_52_path_bound_and_have_weapon_contracts():
    expected = (
        (ATIRADOR_ART_IDS["disparo_terminal"], "vigia", "atirador", True),
        (RASTREADOR_ART_IDS["predacao_persistente"], "vigia", "rastreador", True),
        (CONJURADOR_ART_IDS["rasgo_conjurado"], "tecelao", "conjurador", False),
        (RUNICO_ART_IDS["circulo_runico"], "tecelao", "runico", False),
    )
    for art_id, character_class, path_id, weapon_required in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.min_level == 52
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert bool(definition.weapon_requirement) is weapon_required
        assert art_id in PATH_ART_ACTIONS


def test_b4_ui_describes_new_thresholds_resource_use_and_area_targeting():
    atirador = class_player_actions(
        "vigia", (ATIRADOR_ART_IDS["disparo_terminal"],), selected_path="atirador"
    )
    terminal_lines = _art_mechanics_lines(atirador[ATIRADOR_ART_IDS["disparo_terminal"]])
    assert any("+15 p.p. CRIT" in line for line in terminal_lines)
    assert any("Consome 4 Miras" in line and "após a resolução" in line for line in terminal_lines)

    rastreador = class_player_actions(
        "vigia",
        (RASTREADOR_ART_IDS["predacao_persistente"],),
        selected_path="rastreador",
    )
    predation_lines = _art_mechanics_lines(
        rastreador[RASTREADOR_ART_IDS["predacao_persistente"]]
    )
    assert any(
        "tipo distinto de DoT/Debuff" in line and "máximo +16%" in line
        for line in predation_lines
    )

    conjurador = class_player_actions(
        "tecelao", (CONJURADOR_ART_IDS["rasgo_conjurado"],), selected_path="conjurador"
    )
    assert any(
        "Todos os Inimigos" in line
        for line in _art_mechanics_lines(conjurador[CONJURADOR_ART_IDS["rasgo_conjurado"]])
    )
    runico = class_player_actions(
        "tecelao", (RUNICO_ART_IDS["circulo_runico"],), selected_path="runico"
    )
    assert any(
        "Todos os Aliados" in line
        for line in _art_mechanics_lines(runico[RUNICO_ART_IDS["circulo_runico"]])
    )


def test_disparo_terminal_requires_four_action_start_miras_and_consumes_after_resolution():
    art_id = ATIRADOR_ART_IDS["disparo_terminal"]
    for stacks in (0, 1, 2, 3):
        combat = _battle("vigia", "atirador", (art_id,))
        if stacks:
            combat.fighters["enemy"].path_state["aim_from"] = {
                "player": {
                    "stacks": stacks,
                    "remaining": 2,
                    "applied_opportunity": 0,
                    "trigger": "fixture",
                }
            }
        rejected = act(combat, art_id, target_id="enemy")
        assert rejected is combat
        assert art_id not in combat.fighters["player"].cooldowns
        if stacks:
            assert combat.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == stacks

    ready = _battle("vigia", "atirador", (art_id,))
    ready.fighters["enemy"].path_state["aim_from"] = {
        "player": {
            "stacks": 4,
            "remaining": 2,
            "applied_opportunity": 0,
            "trigger": "fixture",
        }
    }
    result = act(ready, art_id, target_id="enemy")
    event = next(event for event in _events(result, art_id) if event.target == "enemy")

    assert event.aim_stacks == 4
    assert event.path_crit_bonus == D(21)  # Mira Perfeita +6 and Disparo Terminal +15.
    assert event.path_triggers
    assert event.class_resource_changes == (("aim", "enemy", 4, 0),)
    assert "aim_from" not in result.fighters["enemy"].path_state
    assert result.fighters["player"].cooldowns[art_id] > 0
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert "aim_from" not in restored.fighters["enemy"].path_state
    assert (
        restored.fighters["player"].cooldowns[art_id]
        == result.fighters["player"].cooldowns[art_id]
    )


def test_predacao_persistente_counts_distinct_live_dot_and_debuff_types_to_sixteen_percent():
    art_id = RASTREADOR_ART_IDS["predacao_persistente"]
    cases = (
        ((), (), D(1)),
        ((Effect("attack_down", "attack", D("0.1"), 2, 0),), (), D("1.08")),
        (
            (Effect("attack_down", "attack", D("0.1"), 2, 0),),
            (DotState("bleed", 3, 2, D(100), "fixture"),),
            D("1.16"),
        ),
        (
            (
                Effect("attack_down", "attack", D("0.1"), 2, 0),
                Effect("expired", "agility", D("0.1"), 0, 0),
                Effect("fixed", "defense", D("0.1"), 2, 0, fixed_mechanic=True),
            ),
            (
                DotState("bleed", 3, 2, D(100), "fixture"),
                DotState("poison", 2, 2, D(100), "fixture"),
            ),
            D("1.16"),
        ),
    )
    for effects, dots, expected_multiplier in cases:
        combat = _battle("vigia", "rastreador", (art_id,))
        combat.fighters["enemy"].effects.extend(effects)
        combat.dot_states["enemy"] = list(dots)
        result = act(combat, art_id, target_id="enemy")
        event = next(event for event in _events(result, art_id) if event.target == "enemy")
        assert event.path_power_multiplier == expected_multiplier
        assert event.calculated_damage == direct_damage(
            D(100), D("1.35") * expected_multiplier, D(0), 52
        )
        assert result.fighters["enemy"].path_state["aim_from"]["player"]["stacks"] == 1


def test_rasgo_conjurado_consumes_one_trama_for_the_area_action_not_per_enemy():
    art_id = CONJURADOR_ART_IDS["rasgo_conjurado"]
    combat = _battle("tecelao", "conjurador", (art_id,), enemy_ids=("e1", "e2", "e3"))
    combat.fighters["player"].path_state["trama_state"] = {
        "origin_art": CONJURADOR_ART_IDS["estilhaco_do_veu"],
        "remaining": 2,
        "applied_opportunity": 0,
    }

    result = act(combat, art_id)
    events = _events(result, art_id)

    assert {event.target for event in events} == {"e1", "e2", "e3"}
    assert all(event.path_power_multiplier == D("1.15") for event in events)
    assert all(
        event.calculated_damage == direct_damage(D(100), D("1.25") * D("1.15"), D(0), 52)
        for event in events
    )
    assert "trama_state" not in result.fighters["player"].path_state
    assert result.fighters["player"].action_use_counts[art_id] == 1
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert "trama_state" not in restored.fighters["player"].path_state

    same_origin = _battle("tecelao", "conjurador", (art_id,))
    same_origin.fighters["player"].path_state["trama_state"] = {
        "origin_art": art_id,
        "remaining": 2,
        "applied_opportunity": 0,
    }
    repeated = act(same_origin, art_id)
    assert all(event.path_power_multiplier == D(1) for event in _events(repeated, art_id))
    assert repeated.fighters["player"].path_state["trama_state"]["origin_art"] == art_id

    generated = act(_battle("tecelao", "conjurador", (art_id,), enemy_ids=("e1", "e2")), art_id)
    assert generated.fighters["player"].path_state["trama_state"]["origin_art"] == art_id


def test_circulo_runico_applies_fortified_area_barrier_and_consumes_one_trama():
    art_id = RUNICO_ART_IDS["circulo_runico"]
    combat = _battle("tecelao", "runico", (art_id,), include_ally=True)
    combat.fighters["player"].path_state["trama_state"] = {
        "origin_art": RUNICO_ART_IDS["runa_de_guarda"],
        "remaining": 2,
        "applied_opportunity": 0,
    }

    result = act(combat, art_id)
    events = _events(result, art_id)

    assert {event.target for event in events} == {"player", "ally"}
    assert all(event.barrier_value == D(69) for event in events)
    assert all(event.barrier_duration == 2 for event in events)
    assert "trama_state" not in result.fighters["player"].path_state
    assert result.fighters["player"].action_use_counts[art_id] == 1
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["ally"].barrier == D(69)

    generated = act(_battle("tecelao", "runico", (art_id,), include_ally=True), art_id)
    assert generated.fighters["player"].path_state["trama_state"]["origin_art"] == art_id
