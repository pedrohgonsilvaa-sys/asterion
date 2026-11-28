"""Discard (Descartar): removes a whole inventory entry for good.

The discarded quantity is the full stack shown on the item detail (``×N``); the item never
goes to the Warehouse or Pending. Nothing is reserved: the confirmation screen carries the
quantity the player saw, and the commit refuses if the stack changed in between.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment import EquipmentService
from asterion.application.inventory_capacity import (
    inventory_capacity,
    inventory_slot_counts,
    warehouse_capacity,
    warehouse_slots,
)
from asterion.application.warehouse import (
    INVENTORY_MODELS,
    WarehouseRejected,
    _stack_title,
)
from asterion.domain.equipment import parse_equipment_slot
from asterion.infrastructure.db.models import Character, CharacterEquipmentSlot

DISCARD_KINDS = frozenset(INVENTORY_MODELS)


@dataclass(frozen=True, slots=True)
class DiscardView:
    kind: str
    item_id: UUID
    title: str
    quantity: int
    inventory_used: int
    inventory_capacity: int
    warehouse_used: int
    warehouse_capacity: int
    key: str | None = None
    bound: bool = False
    equipped: bool = False


@dataclass(frozen=True, slots=True)
class DiscardResult:
    status: str
    kind: str
    title: str
    quantity: int


class DiscardService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str) -> None:
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def preview(self, actor: int, kind: str, item_id: UUID) -> DiscardView | None:
        if kind not in DISCARD_KINDS:
            raise WarehouseRejected("INVALID_OPERATION")
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            row = await _find(session, kind, character.id, item_id, lock=False)
            if row is None:
                raise WarehouseRejected("ITEM_UNAVAILABLE")
            counts = await inventory_slot_counts(session, character.id)
            return DiscardView(
                kind=kind,
                item_id=item_id,
                title=_title(kind, row),
                quantity=_quantity(kind, row),
                inventory_used=sum(counts.values()),
                inventory_capacity=await inventory_capacity(session, character.id),
                warehouse_used=await warehouse_slots(session, character.id),
                warehouse_capacity=await warehouse_capacity(session, character.id),
                key=row.material_id if kind == "material" else None,
                bound=bool(getattr(row, "bound", False)),
                equipped=kind == "equipment"
                and await _equipped_slot(session, character.id, item_id) is not None,
            )

    async def confirm(
        self, actor: int, kind: str, item_id: UUID, expected_quantity: int
    ) -> DiscardResult:
        if kind not in DISCARD_KINDS:
            raise WarehouseRejected("INVALID_OPERATION")
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if character is None:
                raise WarehouseRejected("CHARACTER_UNAVAILABLE")
            try:
                await lock_for_combat_configuration_mutation(session, character.id)
            except CombatConfigurationLocked as exc:
                raise WarehouseRejected("FOREGROUND_LOCKED") from exc
            row = await _find(session, kind, character.id, item_id, lock=True)
            if row is None:
                raise WarehouseRejected("ITEM_UNAVAILABLE")
            quantity = _quantity(kind, row)
            if quantity != expected_quantity:
                raise WarehouseRejected("STALE_PREVIEW")
            if kind == "equipment":
                slot = await _equipped_slot(session, character.id, item_id)
                if slot is not None:
                    # Discarding an equipped piece takes it off first, in this same transaction.
                    await EquipmentService(self.sessions, self.server_id).unequip_in_session(
                        session, character, parse_equipment_slot(slot)
                    )
            title = _title(kind, row)
            await session.delete(row)
            return DiscardResult("DISCARDED", kind, title, quantity)

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )


async def _find(session: AsyncSession, kind: str, character_id: UUID, item_id: UUID, *, lock):
    model = INVENTORY_MODELS[kind]
    statement = select(model).where(model.id == item_id, model.character_id == character_id)
    if kind != "equipment":
        statement = statement.where(model.quantity > 0)
    if lock:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def _equipped_slot(session: AsyncSession, character_id: UUID, item_id: UUID) -> str | None:
    return await session.scalar(
        select(CharacterEquipmentSlot.slot).where(
            CharacterEquipmentSlot.character_id == character_id,
            CharacterEquipmentSlot.equipment_item_id == item_id,
        )
    )


def _title(kind: str, row) -> str:
    return row.item_name if kind == "equipment" else _stack_title(kind, row)


def _quantity(kind: str, row) -> int:
    return 1 if kind == "equipment" else row.quantity
