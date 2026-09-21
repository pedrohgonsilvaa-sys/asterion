from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import act, allowed_actions
from asterion.domain.prologue import p1_combat_profile

CLASSES = ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
RACES = ("remanescente", "velado", "cinereo", "hemario", "alvorano")


def _key(state):
    player, enemy = state.fighters["player"], state.fighters["enemy"]
    return (
        state.version,
        player.hp,
        enemy.hp,
        player.opportunity,
        tuple(sorted(player.cooldowns.items())),
        state.ai_position,
        state.rng_cursor,
    )


def _can_win(state, seen, depth=0):
    if state.result == "victory":
        return True
    if state.result or depth >= 35:
        return False
    key = _key(state)
    if key in seen:
        return False
    seen.add(key)
    for action in allowed_actions(state):
        if _can_win(act(state, action), seen, depth + 1):
            return True
    return False


def test_all_class_race_combinations_have_a_real_victory_path():
    for index, character_class in enumerate(CLASSES):
        for race_index, race in enumerate(RACES):
            state = p1_combat_profile(
                UUID(int=index * 5 + race_index + 1),
                "Heroa",
                character_class,
                race,
                Decimal("700"),
            )
            assert _can_win(state, set()), f"no victory path for {character_class}/{race}"
