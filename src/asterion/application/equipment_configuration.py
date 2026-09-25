"""Authoritative equipment loading and HP reconciliation for activity boundaries."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.combat_math import CombatStats, resolve_combat_stats
from asterion.domain.equipment import EquipmentSlot, assignment_for_item_slot, parse_equipment_slot
from asterion.domain.equipment_stats import (
    EquipmentConfigurationError,
    EquipmentConfigurationSnapshot,
    item_snapshot_from_persisted,
)
from asterion.infrastructure.db.models import Character, CharacterEquipmentSlot, EquipmentItem

D = Decimal


async def load_equipment_configuration(
    session: AsyncSession,
    character: Character,
    *,
    lock_rows: bool = True,
) -> EquipmentConfigurationSnapshot:
    """Load and validate the character's equipped item instances in one transaction.

    The caller must already hold the Character row lock. All activity creation and
    equipment mutation paths lock Character first, which serializes this read with
    equipment changes and configuration version increments.
    """
    if not session.in_transaction():
        raise RuntimeError("Equipment configuration loading requires an open transaction.")
    slots_statement = (
        select(CharacterEquipmentSlot)
        .where(CharacterEquipmentSlot.character_id == character.id)
        .order_by(CharacterEquipmentSlot.slot)
    )
    if lock_rows:
        slots_statement = slots_statement.with_for_update()
    rows = list((await session.scalars(slots_statement)).all())
    assignments: dict[EquipmentSlot, UUID] = {}
    for row in rows:
        slot = parse_equipment_slot(row.slot)
        if slot is None or slot in assignments:
            raise EquipmentConfigurationError("Invalid equipped slot state.")
        assignments[slot] = row.equipment_item_id
    item_ids = tuple(sorted(set(assignments.values()), key=str))
    if not item_ids:
        return EquipmentConfigurationSnapshot(character.combat_configuration_version)

    items_statement = (
        select(EquipmentItem)
        .where(
            EquipmentItem.id.in_(item_ids),
            EquipmentItem.character_id == character.id,
        )
        .order_by(EquipmentItem.id)
    )
    if lock_rows:
        items_statement = items_statement.with_for_update()
    item_rows = list((await session.scalars(items_statement)).all())
    item_by_id = {item.id: item for item in item_rows}
    if len(item_by_id) != len(item_ids):
        raise EquipmentConfigurationError("An equipped item is missing or not owned.")
    entries = [(slot, item_by_id[item_id]) for slot, item_id in assignments.items()]
    return build_equipment_configuration(
        character,
        entries,
        version=character.combat_configuration_version,
    )


def build_equipment_configuration(
    character: Character,
    entries: list[tuple[EquipmentSlot, EquipmentItem]],
    *,
    version: int | None = None,
) -> EquipmentConfigurationSnapshot:
    """Build validated pure configuration from already-authoritative item rows."""
    snapshots = []
    mythic_count = 0
    for slot, item in entries:
        if item.character_id != character.id:
            raise EquipmentConfigurationError("Equipped item ownership mismatch.")
        if item.item_level > character.level:
            raise EquipmentConfigurationError("Equipped item level requirement is not met.")
        assignment = assignment_for_item_slot(item.slot)
        if assignment is None or assignment.slot != slot:
            raise EquipmentConfigurationError("Item slot does not match its equipped slot.")
        if item.rarity.casefold() in {"mítico", "mythic"}:
            mythic_count += 1
        snapshots.append(
            item_snapshot_from_persisted(
                item_instance_id=str(item.id),
                equipped_slot=slot.value,
                item_slot=item.slot,
                item_level=item.item_level,
                rarity=item.rarity,
                payload=item.payload or {},
            )
        )
    if mythic_count > 1:
        raise EquipmentConfigurationError("More than one Mythic item is equipped.")
    result = EquipmentConfigurationSnapshot(
        character.combat_configuration_version if version is None else version,
        tuple(sorted(snapshots, key=lambda item: item.slot)),
    )
    result.contribution()
    return result


def resolve_character_combat_stats(
    character: Character, configuration: EquipmentConfigurationSnapshot
) -> CombatStats:
    return resolve_combat_stats(
        character.character_class,
        character.level,
        character.race,
        configuration.contribution(),
    )


def reconcile_character_hp(
    character: Character,
    configuration: EquipmentConfigurationSnapshot,
) -> CombatStats:
    """Reconcile legacy persisted max HP at a safe boundary, preserving its ratio."""
    stats = resolve_character_combat_stats(character, configuration)
    new_max_hp = stats.hp
    old_max_hp = D(character.max_hp)
    old_hp = D(character.hp)
    if old_max_hp <= 0:
        raise EquipmentConfigurationError("Character has invalid persisted maximum HP.")
    if new_max_hp == old_max_hp:
        return stats
    if old_hp == 0:
        new_hp = D(0)
    else:
        new_hp = max(
            D(1),
            _floor_scaled_hp(old_hp, new_max_hp, old_max_hp),
        )
    character.max_hp = new_max_hp
    character.hp = min(new_hp, new_max_hp)
    return stats


def hp_after_equipment_change(character: Character, new_max_hp: Decimal) -> Decimal:
    """Return HP after an effective equipment change, without mutating the row."""
    old_max_hp = D(character.max_hp)
    old_hp = D(character.hp)
    if old_max_hp <= 0:
        raise EquipmentConfigurationError("Character has invalid persisted maximum HP.")
    if old_hp == 0:
        return D(0)
    if D(new_max_hp) == old_max_hp:
        return min(old_hp, old_max_hp)
    return min(
        D(new_max_hp),
        max(
            D(1),
            _floor_scaled_hp(old_hp, D(new_max_hp), old_max_hp),
        ),
    )


def _floor_scaled_hp(hp: Decimal, new_max_hp: Decimal, old_max_hp: Decimal) -> Decimal:
    exact_ratio = Fraction(hp) * Fraction(new_max_hp) / Fraction(old_max_hp)
    return D(exact_ratio.numerator // exact_ratio.denominator)
