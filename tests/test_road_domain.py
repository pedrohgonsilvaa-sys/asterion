from decimal import Decimal
from uuid import UUID, uuid4

from asterion.domain.combat import act, allowed_actions
from asterion.domain.road import (
    CATEGORY,
    CREATURES,
    enemy_xp,
    road_enemy_stats,
    road_pool,
    select_creature,
    select_variant,
)


def test_road_pool_gates_and_weights_are_authoritative():
    assert [c.creature_id for c in road_pool(1)] == ["dog_cinereo", "corvo_fuligem"]
    assert [c.creature_id for c in road_pool(2)] == [
        "dog_cinereo",
        "corvo_fuligem",
        "peregrino_calcinado",
    ]
    assert [c.creature_id for c in road_pool(3)] == [c.creature_id for c in CREATURES]
    assert sum(c.weight for c in road_pool(1)) == 67


def test_road_enemy_regression_vectors():
    dog, crow, pilgrim, alpha = CREATURES
    assert road_enemy_stats(dog, 1).values() == tuple(Decimal(v) for v in (406, 91, 60, 87))
    assert road_enemy_stats(crow, 1).values() == tuple(Decimal(v) for v in (406, 91, 60, 87))
    assert road_enemy_stats(pilgrim, 2).values() == tuple(Decimal(v) for v in (462, 85, 68, 74))
    assert road_enemy_stats(alpha, 3).values() == tuple(Decimal(v) for v in (912, 123, 73, 97))


def test_enemy_xp_and_variant_are_deterministic():
    assert enemy_xp(1, "common") == 240
    assert enemy_xp(5, "common") == 320
    dog = CREATURES[0]
    first = select_creature("stable-seed", 1)
    assert first == select_creature("stable-seed", 1)
    assert select_variant("stable-seed", dog) == select_variant("stable-seed", dog)
    assert CATEGORY["common"].hp == Decimal("0.70")


def test_road_combat_has_normal_actions_and_no_tutorial():
    from asterion.domain.road import create_road_combat

    state = create_road_combat(
        uuid4(), "Heroa", "sentinela", "remanescente", Decimal(702), CREATURES[0], 1, None
    )
    assert state.tutorial is None
    assert {"attack", "defend", "art"}.issubset(set(allowed_actions(state)))


def test_prepared_alpha_resolves_once_after_response_window():
    from asterion.domain.road import create_road_combat

    state = create_road_combat(
        UUID(int=7), "Heroa", "sentinela", "remanescente", Decimal(702), CREATURES[3], 3, None
    )
    # Advance until the deterministic AI prepares its leap, then provide the response.
    for _ in range(8):
        actions = allowed_actions(state)
        if not actions:
            break
        state = act(state, "defend" if "defend" in actions else actions[0])
        if state.prepared_action:
            break
    assert state.prepared_action in {None, "leap"}


def test_all_class_race_pairs_have_a_legal_victory_path():
    from asterion.domain.combat_math import class_stats, racial_stats
    from asterion.domain.road import create_road_combat

    races = ("remanescente", "velado", "cinereo", "hemario", "alvorano")
    classes = ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
    for character_class in classes:
        for race in races:
            hp = racial_stats(class_stats(character_class, 1), race).hp
            state = create_road_combat(
                uuid4(), "Heroa", character_class, race, hp, CREATURES[0], 1, None
            )
            for _ in range(80):
                if state.result:
                    break
                actions = allowed_actions(state)
                assert actions
                state = act(state, "art" if "art" in actions else "attack")
            assert state.result == "victory", (character_class, race)
