"""Shared, authoritative item-slot accounting for Inventory."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.infrastructure.db.models import (
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
