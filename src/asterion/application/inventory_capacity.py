"""Shared, authoritative item-slot accounting for Inventory."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.legacy_marks import (
    INVENTORY_BONUS,
    PENDING_BONUS,
    WAREHOUSE_BONUS,
    LegacyMarkId,
)
from asterion.infrastructure.db.models import (
    CharacterLegacyMark,
    ConsumableStack,
    EquipmentItem,
    MaterialStack,
    RuneStack,
    WarehouseConsumableStack,
    WarehouseEquipmentItem,
    WarehouseMaterialStack,
    WarehouseRuneStack,
)

INVENTORY_CAPACITY = 60
WAREHOUSE_CAPACITY = 100
PENDING_CAPACITY = 20


async def has_legacy_mark(session: AsyncSession, character_id: UUID, mark: LegacyMarkId) -> bool:
    found = await session.scalar(
        select(CharacterLegacyMark.mark_id).where(
            CharacterLegacyMark.character_id == character_id,
            CharacterLegacyMark.mark_id == mark.value,
        )
    )
    return found is not None


async def inventory_capacity(session: AsyncSession, character_id: UUID) -> int:
    """Inventory slots for this character, including Bolsa Funda."""
    bonus = await has_legacy_mark(session, character_id, LegacyMarkId.BOLSA_FUNDA)
    return INVENTORY_CAPACITY + (INVENTORY_BONUS if bonus else 0)


async def warehouse_capacity(session: AsyncSession, character_id: UUID) -> int:
    """Warehouse slots for this character, including Armazém Amplo."""
    bonus = await has_legacy_mark(session, character_id, LegacyMarkId.ARMAZEM_AMPLO)
    return WAREHOUSE_CAPACITY + (WAREHOUSE_BONUS if bonus else 0)


async def pending_capacity(session: AsyncSession, character_id: UUID) -> int:
    """Pending Delivery slots for this character, including Entregas Guardadas."""
    bonus = await has_legacy_mark(session, character_id, LegacyMarkId.ENTREGAS_GUARDADAS)
    return PENDING_CAPACITY + (PENDING_BONUS if bonus else 0)


async def inventory_slot_counts(session: AsyncSession, character_id: UUID) -> dict[str, int]:
    """Count positive stack rows and equipment once, across all item delivery paths."""

    models = {
        "equipment": (EquipmentItem, False),
        "consumables": (ConsumableStack, True),
        "materials": (MaterialStack, True),
        "runes": (RuneStack, True),
    }
    result: dict[str, int] = {}
    for category, (model, positive_only) in models.items():
        statement = select(func.count(model.id)).where(model.character_id == character_id)
        if positive_only:
            statement = statement.where(model.quantity > 0)
        result[category] = int(await session.scalar(statement) or 0)
    return result


async def inventory_slots(session: AsyncSession, character_id: UUID) -> int:
    return sum((await inventory_slot_counts(session, character_id)).values())


async def warehouse_slots(session: AsyncSession, character_id: UUID) -> int:
    equipment = await session.scalar(
        select(func.count(WarehouseEquipmentItem.id)).where(
            WarehouseEquipmentItem.character_id == character_id
        )
    )
    total = int(equipment or 0)
    for model in (WarehouseMaterialStack, WarehouseConsumableStack, WarehouseRuneStack):
        count = await session.scalar(
            select(func.count(model.id)).where(
                model.character_id == character_id,
                model.quantity > 0,
            )
        )
        total += int(count or 0)
    return total
