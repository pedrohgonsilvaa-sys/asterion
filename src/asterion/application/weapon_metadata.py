"""Persistence-aware, exact-identity resolution for equipment weapon metadata."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.equipment import assignment_for_item_slot
from asterion.domain.weapon_metadata import (
    WeaponDefinition,
    resolve_weapon_metadata,
    weapon_definition,
    weapon_type_id_for_recipe,
    weapon_type_id_for_reward_source,
)
from asterion.infrastructure.db.models import (
    CharacterEquipmentSlot,
    CraftingReceipt,
    EquipmentItem,
)


class WeaponMetadataPersistenceError(ValueError):
    """A canonical weapon identity conflicts with its persisted equipment slot."""


async def resolve_equipment_weapon(
    session: AsyncSession, item: EquipmentItem
) -> WeaponDefinition | None:
    """Resolve by a canonical ID or exact provenance, never by display text."""
    payload = item.payload or {}
    resolution = resolve_weapon_metadata(payload)
    if resolution.definition is not None:
        definition = resolution.definition
    elif "weapon_type_id" in payload:
        return None
    else:
        weapon_type_id = weapon_type_id_for_reward_source(item.source_key)
        if weapon_type_id is None and (
            item.source_key.startswith("craft:")
            and item.source_key.endswith(":equipment")
        ):
            receipt_source_key = item.source_key.removesuffix(":equipment")
            recipe_id = await session.scalar(
                select(CraftingReceipt.recipe_id).where(
                    CraftingReceipt.character_id == item.character_id,
                    CraftingReceipt.source_key == receipt_source_key,
                    CraftingReceipt.status == "committed",
                )
            )
            weapon_type_id = weapon_type_id_for_recipe(recipe_id)
        definition = weapon_definition(weapon_type_id)
    if definition is None:
        return None
    expected_assignment = assignment_for_item_slot(definition.persisted_item_slot)
    actual_assignment = assignment_for_item_slot(item.slot)
    if actual_assignment != expected_assignment:
        raise WeaponMetadataPersistenceError(
            "Canonical weapon metadata conflicts with the persisted item slot."
        )
    return definition


async def equipped_weapon_definitions(
    session: AsyncSession, character_id: UUID
) -> tuple[WeaponDefinition, ...]:
    """Return only exact canonical weapons currently equipped in legal slots."""
    rows = (
        await session.execute(
            select(CharacterEquipmentSlot.slot, EquipmentItem)
            .join(
                EquipmentItem,
                EquipmentItem.id == CharacterEquipmentSlot.equipment_item_id,
            )
            .where(
                CharacterEquipmentSlot.character_id == character_id,
                EquipmentItem.character_id == character_id,
            )
            .order_by(CharacterEquipmentSlot.slot)
        )
    ).all()
    definitions: list[WeaponDefinition] = []
    for equipped_slot, item in rows:
        definition = await resolve_equipment_weapon(session, item)
        if definition is None:
            continue
        assignment = assignment_for_item_slot(item.slot)
        if assignment is None or assignment.slot.value != equipped_slot:
            raise WeaponMetadataPersistenceError(
                "Canonical weapon metadata conflicts with its equipped slot."
            )
        definitions.append(definition)
    return tuple(definitions)


async def equipped_weapon_compatibility_tags(
    session: AsyncSession, character_id: UUID
) -> frozenset[str]:
    return frozenset(
        tag
        for definition in await equipped_weapon_definitions(session, character_id)
        for tag in definition.compatibility_tags
    )
