from decimal import Decimal
from uuid import uuid4

from asterion.domain.prologue import p1_combat_profile

CLASSES = ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
RACES = ("remanescente", "velado", "cinereo", "hemario", "alvorano")


def test_all_class_race_profiles_are_deterministic_and_normal():
    for character_class in CLASSES:
        for race in RACES:
            first = p1_combat_profile(uuid4(), "Heroa", character_class, race, Decimal("700"))
            second = p1_combat_profile(first.id, "Heroa", character_class, race, Decimal("700"))
            assert first.tutorial is None
            assert first.fighters["enemy"].stats.hp == Decimal("406")
            assert first.enemy_actions["bite"].coefficient == Decimal("1")
            assert first.enemy_actions["charge"].coefficient == Decimal("1.10")
            assert first.player_actions.keys() == second.player_actions.keys()
