"""Reusable character progression rules for resolution boundaries."""

from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.equipment_stats import (
    EquipmentConfigurationSnapshot,
    EquipmentStatContribution,
)


def level_xp(level: int) -> int:
    """Return the exact XP required to advance from ``level``."""
    value = Decimal(4000 + 750 * level + 43 * level * level)
    return int(value.quantize(Decimal("1E2"), rounding=ROUND_HALF_UP))


def consolidate_level(
    character,
    equipment: EquipmentStatContribution | None = None,
    selected_path: str | None = None,
    talent_ids: tuple[str, ...] = (),
) -> int:
    """Consolidate all earned XP at a valid activity boundary.

    XP is stored as progress inside the current level. Level 60 is a hard
    cap, so any surplus that cannot produce another level is intentionally
    discarded rather than hidden in the character row. Current HP is also
    normalized to whole points so legacy fractional health cannot survive a
    progression boundary.
    """
    character.hp = max(
        Decimal(0),
        Decimal(character.hp).to_integral_value(rounding=ROUND_FLOOR),
    )
    advanced = 0
    while character.level < 60 and character.xp >= level_xp(character.level):
        character.xp -= level_xp(character.level)
        character.level += 1
        character.max_hp = resolve_combat_stats(
            character.character_class,
            character.level,
            character.race,
            equipment,
            selected_path,
            talent_ids,
        ).hp
        character.hp = min(character.hp, character.max_hp)
        advanced += 1
    if character.level >= 60:
        character.level = 60
        character.xp = 0
    return advanced


async def consolidate_character_level(
    session,
    character,
    equipment_configuration: EquipmentConfigurationSnapshot | None = None,
) -> int:
    """Progress using the authoritative equipped configuration inside the caller transaction."""
    configuration = equipment_configuration or await load_equipment_configuration(
        session, character
    )
    return consolidate_level(
        character,
        configuration.contribution(),
        configuration.selected_path,
        tuple(talent_id for _, talent_id in configuration.talent_choices),
    )
