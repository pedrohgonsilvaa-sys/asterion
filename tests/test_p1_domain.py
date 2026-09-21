from decimal import Decimal
from uuid import uuid4

from asterion.domain.prologue import p1_combat_profile


def test_p1_enemy_profile_is_derived_without_tutorial():
    combat = p1_combat_profile(uuid4(), "Heroa", "sentinela", "remanescente", Decimal("702"))
    enemy = combat.fighters["enemy"]
    assert (enemy.stats.hp, enemy.stats.attack, enemy.stats.defense, enemy.stats.agility) == (
        Decimal("406"),
        Decimal("91"),
        Decimal("60"),
        Decimal("87"),
    )
    assert combat.tutorial is None
    assert combat.enemy_actions["bite"].coefficient == Decimal("1")
    assert combat.enemy_actions["charge"].coefficient == Decimal("1.10")
