"""Reusable character progression rules for resolution boundaries."""

from decimal import ROUND_HALF_UP, Decimal

from asterion.domain.combat_math import resolve_combat_stats


def level_xp(level: int) -> int:
    """Return the exact XP required to advance from ``level``."""
    value = Decimal(4000 + 750 * level + 43 * level * level)
    return int(value.quantize(Decimal("1E2"), rounding=ROUND_HALF_UP))


def consolidate_level(character) -> int:
    """Consolidate all earned XP at a valid activity boundary.

    XP is stored as progress inside the current level.  Level 60 is a hard
    cap, so any surplus that cannot produce another level is intentionally
    discarded rather than hidden in the character row.
    """
    advanced = 0
    while character.level < 60 and character.xp >= level_xp(character.level):
        character.xp -= level_xp(character.level)
        character.level += 1
        character.max_hp = resolve_combat_stats(
            character.character_class, character.level, character.race
        ).hp
        character.hp = min(character.hp, character.max_hp)
        advanced += 1
    if character.level >= 60:
        character.level = 60
        character.xp = 0
    return advanced
