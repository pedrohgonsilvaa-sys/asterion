from decimal import ROUND_FLOOR, Decimal
from uuid import UUID

from asterion.domain.arts import (
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    DEVASTADOR_ART_IDS,
    SABOTADOR_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Combat, DotState, Effect, Fighter, act, start_combat
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.path_arts import PATH_ART_ACTIONS
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(character_class: str, path_id: str, art_ids: tuple[str, ...]) -> Combat:
    player = Fighter(
        id="player",
        name="Player",
        level=52,
        stats=CombatStats(D(1000), D(100), D(100), D(100), crit=D(0), evasion=D(0)),
        hp=D(1000),
        character_class=character_class,
        selected_path=path_id,
        side="player",
        takes_turn=True,
    )
    fighters = {
        "player": player,
        "ally-a": Fighter(
            id="ally-a",
            name="Ally A",
            level=52,
            stats=CombatStats(D(1000), D(50), D(50), D(50), crit=D(0), evasion=D(0)),
            hp=D(1000),
            side="player",
            takes_turn=False,
        ),
        "ally-b": Fighter(
            id="ally-b",
            name="Ally B",
            level=52,
            stats=CombatStats(D(1000), D(50), D(50), D(50), crit=D(0), evasion=D(0)),
            hp=D(1000),
            side="player",
            takes_turn=False,
        ),
        "enemy": Fighter(
            id="enemy",
            name="Enemy",
            level=52,
            stats=CombatStats(D(1000), D(100), D(0), D(0), crit=D(0), evasion=D(0)),
            hp=D(1000),
            side="enemy",
            takes_turn=False,
        ),
    }
    actions = class_player_actions(character_class, art_ids, selected_path=path_id)
    return start_combat(
        Combat(
            UUID("b4a1f012-83c4-42fa-ade3-6ba98ea72101"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
        )
    )


def _events(combat: Combat, action_id: str):
    return [event for event in combat.events if event.action == action_id]


def test_b4_a_art_definitions_are_level_52_path_bound_and_executable():
    expected = (
        (BASTIAO_ART_IDS["ultima_muralha"], "sentinela", "bastiao", False),
        (DEVASTADOR_ART_IDS["ruptor"], "sentinela", "devastador", True),
        (CARRASCO_ART_IDS["ceifa"], "errante", "carrasco", True),
        (SABOTADOR_ART_IDS["colapso_preparado"], "errante", "sabotador", True),
    )
    for art_id, character_class, path_id, weapon_required in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.min_level == 52
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert bool(definition.weapon_requirement) is weapon_required
        assert art_id in PATH_ART_ACTIONS


def test_ultima_muralha_applies_one_fortified_barrier_to_each_living_ally():
    art_id = BASTIAO_ART_IDS["ultima_muralha"]
    combat = _battle("sentinela", "bastiao", (art_id,))
    combat.fighters["ally-b"].hp = D(0)

    result = act(combat, art_id)

    events = _events(result, art_id)
    assert {event.target for event in events} == {"player", "ally-a"}
    # Fortaleza's +10% barrier applies once to each target: floor(100*.65*1.10).
    assert all(event.barrier_value == D(71) for event in events)
    assert all(event.barrier_duration == 2 for event in events)
    assert all(event.barrier_applied_source for event in events)
    assert result.fighters["player"].barrier == D(71)
    assert result.fighters["ally-a"].barrier == D(71)
    assert result.fighters["ally-b"].barrier == D(0)
    assert result.fighters["player"].cooldowns[art_id] > 0
    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["player"].barrier == D(71)
    assert restored.fighters["ally-a"].barrier == D(71)
    assert (
        restored.fighters["player"].cooldowns[art_id]
        == result.fighters["player"].cooldowns[art_id]
    )


def test_ruptor_uses_strict_pre_action_actor_hp_below_fifty_percent():
    art_id = DEVASTADOR_ART_IDS["ruptor"]
    for hp, expected_multiplier in (
        (D("499.99"), D("1.10")),
        (D(500), D(1)),
        (D("500.01"), D(1)),
    ):
        combat = _battle("sentinela", "devastador", (art_id,))
        combat.fighters["player"].hp = hp
        result = act(combat, art_id, target_id="enemy")
        event = next(event for event in _events(result, art_id) if event.target == "enemy")
        assert event.path_power_multiplier == expected_multiplier
        assert event.calculated_damage == direct_damage(
            D(100), D("1.70") * expected_multiplier, D(0), 52
        )


def test_ruptor_consumes_existing_retaliation_once_without_rearming_it():
    art_id = DEVASTADOR_ART_IDS["ruptor"]
    combat = _battle("sentinela", "devastador", (art_id,))
    actor = combat.fighters["player"]
    actor.hp = D(490)
    actor.retaliation_charges = 1
    actor.retaliation_remaining = 1
    actor.retaliation_activation_id = "test:retaliation"

    result = act(combat, art_id, target_id="enemy")
    event = next(event for event in _events(result, art_id) if event.target == "enemy")

    assert event.retaliation_used is True
    assert result.fighters["player"].retaliation_charges == 0
    assert result.fighters["player"].path_state.get("retaliation") is None


def test_ceifa_uses_target_hp_snapshot_and_adds_ten_crit_points_at_forty_percent():
    art_id = CARRASCO_ART_IDS["ceifa"]
    for hp, expected_bonus in (
        (D("400.01"), D(0)),
        (D(400), D(10)),
        (D("399.99"), D(10)),
    ):
        combat = _battle("errante", "carrasco", (art_id,))
        combat.fighters["enemy"].hp = hp
        result = act(combat, art_id, target_id="enemy")
        event = next(event for event in _events(result, art_id) if event.target == "enemy")
        assert event.path_crit_bonus == expected_bonus
        expected_sentenca = D("0.08") if hp <= D(400) else D(0)
        assert event.path_final_damage_bonus == expected_sentenca
        base_damage = direct_damage(
            D(100), D("1.65"), D(0), 52, critical=event.critical
        )
        assert event.calculated_damage == int(
            (D(base_damage) * (D(1) + expected_sentenca)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )


def test_colapso_preparado_counts_distinct_live_normal_effects_not_stacks():
    art_id = SABOTADOR_ART_IDS["colapso_preparado"]
    for effects, dots, expected_multiplier in (
        ((), (), D(1)),
        ((Effect("atk_down", "attack", D("0.1"), 2, 0, stacks=3),), (), D("1.10")),
        (
            (
                Effect("atk_down", "attack", D("0.1"), 2, 0, stacks=3),
                Effect("agi_down", "agility", D("0.1"), 2, 0),
            ),
            (DotState("bleed", 2, 2, D(100), "test"),),
            D("1.30"),
        ),
        (
            (
                Effect("atk_down", "attack", D("0.1"), 2, 0),
                Effect("expired", "defense", D("0.1"), 0, 0),
                Effect("fixed", "defense", D("0.1"), 2, 0, fixed_mechanic=True),
            ),
            (
                DotState("bleed", 3, 2, D(100), "test"),
                DotState("poison", 1, 2, D(100), "test"),
            ),
            D("1.30"),
        ),
    ):
        combat = _battle("errante", "sabotador", (art_id,))
        combat.fighters["enemy"].effects.extend(effects)
        combat.dot_states["enemy"] = list(dots)
        result = act(combat, art_id, target_id="enemy")
        event = next(event for event in _events(result, art_id) if event.target == "enemy")
        assert event.path_power_multiplier == expected_multiplier
        raw_damage = direct_damage(
            D(100), D("1.20") * expected_multiplier, D(0), 52
        )
        opportunism = D("0.08") if expected_multiplier > 1 else D(0)
        expected_damage = int(
            (D(raw_damage) * (D(1) + opportunism)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        assert event.path_final_damage_bonus == opportunism
        assert event.calculated_damage == expected_damage
