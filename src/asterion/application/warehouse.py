"""Public, transactional Warehouse transfer and Pending recovery service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment import equipment_instance_payload
from asterion.application.inventory_capacity import (
    INVENTORY_CAPACITY,
    WAREHOUSE_CAPACITY,
    inventory_slot_counts,
    inventory_slots,
    warehouse_slots,
)
from asterion.application.safe_location import current_permanent_brazier
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    ConsumableStack,
    EquipmentItem,
    MaterialStack,
    PendingItem,
    RuneStack,
    WarehouseEquipmentItem,
    WarehouseMaterialStack,
    WarehouseOperation,
)

OPERATION_TTL = timedelta(minutes=5)
MATERIAL_STACK_LIMIT = 999
CONSUMABLE_STACK_LIMIT = 99


class WarehouseRejected(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class WarehouseEntry:
    id: str
    kind: str
    title: str
    quantity: int = 1
    bound: bool = False
    rarity: str | None = None
    slot: str | None = None
    item_level: int | None = None
    source_key: str | None = None
    eligible: bool = True
    reason: str | None = None
    payload: dict | None = None


@dataclass(frozen=True, slots=True)
class WarehouseView:
    kind: str
    character_id: UUID
    accessible: bool
    location: str | None
    inventory_used: int
    warehouse_used: int
    entries: tuple[WarehouseEntry, ...] = ()
    operation_id: UUID | None = None
    direction: str | None = None
    item_kind: str | None = None
    title: str | None = None
    quantity: int = 0
    status: str | None = None
    origin: str | None = None


@dataclass(frozen=True, slots=True)
class WarehouseResult:
    status: str
    direction: str
    kind: str
    quantity: int
    operation_id: UUID


class WarehouseService:
    """Moves whole equipment/material stacks while preserving their identities."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def root(self, actor: int) -> WarehouseView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            safe = await current_permanent_brazier(session, character.id)
            counts = await inventory_slot_counts(session, character.id)
            stored = []
            if safe is not None:
                stored.extend(await self._warehouse_entries(session, character.id))
            return WarehouseView(
                kind="warehouse_root",
                character_id=character.id,
                accessible=safe is not None,
                location=safe[1] if safe else None,
                inventory_used=sum(counts.values()),
                warehouse_used=len(stored),
                entries=tuple(stored),
            )

    async def inventory_sources(self, actor: int, kind: str) -> WarehouseView | None:
        if kind not in {"equipment", "material"}:
            raise WarehouseRejected("INVALID_KIND")
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            safe = await current_permanent_brazier(session, character.id)
            if safe is None:
                raise WarehouseRejected("SAFE_LOCATION_REQUIRED")
            counts = await inventory_slot_counts(session, character.id)
            if kind == "equipment":
                rows = (
                    await session.scalars(
                        select(EquipmentItem)
                        .where(EquipmentItem.character_id == character.id)
                        .order_by(EquipmentItem.item_name, EquipmentItem.id)
                    )
                ).all()
                equipped = set(
                    (
                        await session.scalars(
                            select(CharacterEquipmentSlot.equipment_item_id).where(
                                CharacterEquipmentSlot.character_id == character.id
                            )
                        )
                    ).all()
                )
                entries = tuple(
                    WarehouseEntry(
                        id=str(row.id),
                        kind=kind,
                        title=row.item_name,
                        rarity=row.rarity,
                        slot=row.slot,
                        item_level=row.item_level,
                        bound=row.bound,
                        source_key=row.source_key,
                        eligible=(
                            row.id not in equipped
                            and not bool((row.payload or {}).get("locked"))
                        ),
                        reason=(
                            "EQUIPPED"
                            if row.id in equipped
                            else "LOCKED" if bool((row.payload or {}).get("locked")) else None
                        ),
                        payload=dict(row.payload or {}),
                    )
                    for row in rows
                )
            else:
                rows = (
                    await session.scalars(
                        select(MaterialStack)
                        .where(
                            MaterialStack.character_id == character.id,
                            MaterialStack.quantity > 0,
                        )
                        .order_by(MaterialStack.material_id, MaterialStack.bound, MaterialStack.id)
                    )
                ).all()
                entries = tuple(
                    WarehouseEntry(
                        id=str(row.id),
                        kind=kind,
                        title=row.material_id,
                        quantity=row.quantity,
                        bound=row.bound,
                    )
                    for row in rows
                )
            return WarehouseView(
                kind="warehouse_inventory_sources",
                character_id=character.id,
                accessible=True,
                location=safe[1],
                inventory_used=sum(counts.values()),
                warehouse_used=await warehouse_slots(session, character.id),
                entries=entries,
            )

    async def prepare_transfer(
        self, actor: int, direction: str, kind: str, source_id: UUID
    ) -> WarehouseView | None:
        if direction not in {"deposit", "withdraw"} or kind not in {"equipment", "material"}:
            raise WarehouseRejected("INVALID_OPERATION")
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            safe = await current_permanent_brazier(session, character.id)
            if safe is None:
                raise WarehouseRejected("SAFE_LOCATION_REQUIRED")
            record, snapshot, title, quantity, source_key = await self._transfer_source(
                session, character.id, direction, kind, source_id, lock=True
            )
            if direction == "deposit":
                if kind == "equipment":
                    if await self._is_equipped(session, character.id, source_id):
                        raise WarehouseRejected("EQUIPPED")
                    if bool((record.payload or {}).get("locked")):
                        raise WarehouseRejected("LOCKED")
                if await warehouse_slots(session, character.id) >= WAREHOUSE_CAPACITY:
                    raise WarehouseRejected("WAREHOUSE_FULL")
            elif await inventory_slots(session, character.id) >= INVENTORY_CAPACITY:
                raise WarehouseRejected("INVENTORY_FULL")
            operation = self._new_operation(
                character.id,
                direction,
                kind,
                str(source_id),
                source_key,
                quantity,
                snapshot,
            )
            session.add(operation)
            counts = await inventory_slot_counts(session, character.id)
            return WarehouseView(
                kind="warehouse_operation",
                character_id=character.id,
                accessible=True,
                location=safe[1],
                inventory_used=sum(counts.values()),
                warehouse_used=await warehouse_slots(session, character.id),
                operation_id=operation.id,
                direction=direction,
                item_kind=kind,
                title=title,
                quantity=quantity,
                status="preview",
            )

    async def prepare_pending_claim(self, actor: int, pending_id: UUID) -> WarehouseView | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            pending = await session.scalar(
                select(PendingItem)
                .where(PendingItem.id == pending_id, PendingItem.character_id == character.id)
                .with_for_update()
            )
            if pending is None:
                raise WarehouseRejected("PENDING_UNAVAILABLE")
            amount = await self._pending_recoverable_quantity(session, character.id, pending)
            if amount <= 0:
                raise WarehouseRejected("INVENTORY_FULL")
            title = self._pending_title(pending)
            snapshot = self._pending_snapshot(pending)
            operation = self._new_operation(
                character.id,
                "claim_pending",
                pending.kind,
                str(pending.id),
                pending.source_key,
                amount,
                snapshot,
            )
            session.add(operation)
            counts = await inventory_slot_counts(session, character.id)
            safe = await current_permanent_brazier(session, character.id)
            return WarehouseView(
                kind="warehouse_operation",
                character_id=character.id,
                accessible=True,
                location=safe[1] if safe else None,
                inventory_used=sum(counts.values()),
                warehouse_used=await warehouse_slots(session, character.id),
                operation_id=operation.id,
                direction="claim_pending",
                item_kind=pending.kind,
                title=title,
                quantity=amount,
                status="preview",
                origin=pending.source_key,
            )

    async def operation(self, actor: int, operation_id: UUID) -> WarehouseView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            operation = await session.scalar(
                select(WarehouseOperation).where(
                    WarehouseOperation.id == operation_id,
                    WarehouseOperation.character_id == character.id,
                )
            )
            if operation is None:
                return None
            counts = await inventory_slot_counts(session, character.id)
            safe = await current_permanent_brazier(session, character.id)
            return WarehouseView(
                kind="warehouse_operation",
                character_id=character.id,
                accessible=True,
                location=safe[1] if safe else None,
                inventory_used=sum(counts.values()),
                warehouse_used=await warehouse_slots(session, character.id),
                operation_id=operation.id,
                direction=operation.direction,
                item_kind=operation.kind,
                title=operation.source_key or operation.kind,
                quantity=operation.quantity,
                status=operation.status,
                origin=operation.source_key,
            )

    async def cancel(self, actor: int, operation_id: UUID) -> str:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return "NOT_FOUND"
            operation = await self._operation(session, character.id, operation_id, lock=True)
            if operation is None:
                return "NOT_FOUND"
            if operation.status == "committed":
                return "ALREADY_COMMITTED"
            if operation.status != "preview":
                return operation.status.upper()
            operation.status = "cancelled"
            operation.completed_at = datetime.now(UTC)
            return "CANCELLED"

    async def confirm(self, actor: int, operation_id: UUID) -> WarehouseResult:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                raise WarehouseRejected("CHARACTER_UNAVAILABLE")
            operation = await self._operation(session, character.id, operation_id, lock=True)
            if operation is None:
                raise WarehouseRejected("OPERATION_UNAVAILABLE")
            if operation.status == "committed":
                return WarehouseResult(
                    "ALREADY_COMMITTED", operation.direction, operation.kind,
                    operation.quantity, operation.id
                )
            if operation.status != "preview":
                return WarehouseResult(
                    operation.status.upper(), operation.direction, operation.kind,
                    operation.quantity, operation.id
                )
            now = datetime.now(UTC)
            if operation.expires_at <= now:
                operation.status = "expired"
                operation.completed_at = now
                return WarehouseResult(
                    "EXPIRED", operation.direction, operation.kind,
                    operation.quantity, operation.id
                )
            safe = await current_permanent_brazier(session, character.id)
            if operation.direction in {"deposit", "withdraw"} and safe is None:
                operation.status = "stale"
                operation.completed_at = now
                return WarehouseResult(
                    "SAFE_LOCATION_REQUIRED", operation.direction, operation.kind,
                    operation.quantity, operation.id
                )
            try:
                if operation.direction == "claim_pending":
                    await self._commit_pending_claim(session, character.id, operation)
                else:
                    await self._commit_transfer(session, character.id, operation)
            except WarehouseRejected as exc:
                if exc.code == "STALE_PREVIEW":
                    operation.status = "stale"
                    operation.completed_at = now
                    return WarehouseResult(
                        "STALE", operation.direction, operation.kind,
                        operation.quantity, operation.id
                    )
                raise
            operation.status = "committed"
            operation.completed_at = now
            return WarehouseResult(
                "COMMITTED", operation.direction, operation.kind,
                operation.quantity, operation.id
            )

    async def _commit_transfer(
        self, session: AsyncSession, character_id: UUID, operation: WarehouseOperation
    ) -> None:
        try:
            source_id = UUID(operation.source_id)
        except ValueError as exc:
            raise WarehouseRejected("STALE_PREVIEW") from exc
        record, snapshot, _title, quantity, _source_key = await self._transfer_source(
            session, character_id, operation.direction, operation.kind, source_id, lock=True
        )
        if _fingerprint(snapshot) != operation.fingerprint or quantity != operation.quantity:
            raise WarehouseRejected("STALE_PREVIEW")
        if operation.direction == "deposit":
            if operation.kind == "equipment":
                if await self._is_equipped(session, character_id, source_id):
                    raise WarehouseRejected("STALE_PREVIEW")
                if bool((record.payload or {}).get("locked")):
                    raise WarehouseRejected("STALE_PREVIEW")
                if await warehouse_slots(session, character_id) >= WAREHOUSE_CAPACITY:
                    raise WarehouseRejected("WAREHOUSE_FULL")
                session.add(
                    WarehouseEquipmentItem(
                        id=record.id,
                        character_id=record.character_id,
                        source_key=record.source_key,
                        item_name=record.item_name,
                        rarity=record.rarity,
                        slot=record.slot,
                        item_level=record.item_level,
                        bound=record.bound,
                        payload=dict(record.payload or {}),
                    )
                )
                await session.delete(record)
            else:
                if await warehouse_slots(session, character_id) >= WAREHOUSE_CAPACITY:
                    raise WarehouseRejected("WAREHOUSE_FULL")
                session.add(
                    WarehouseMaterialStack(
                        id=record.id,
                        character_id=record.character_id,
                        material_id=record.material_id,
                        quantity=record.quantity,
                        bound=record.bound,
                    )
                )
                await session.delete(record)
            return
        if operation.kind == "equipment":
            if await inventory_slots(session, character_id) >= INVENTORY_CAPACITY:
                raise WarehouseRejected("INVENTORY_FULL")
            session.add(
                EquipmentItem(
                    id=record.id,
                    character_id=record.character_id,
                    source_key=record.source_key,
                    item_name=record.item_name,
                    rarity=record.rarity,
                    slot=record.slot,
                    item_level=record.item_level,
                    bound=record.bound,
                    payload=dict(record.payload or {}),
                )
            )
            await session.delete(record)
        else:
            if await inventory_slots(session, character_id) >= INVENTORY_CAPACITY:
                raise WarehouseRejected("INVENTORY_FULL")
            session.add(
                MaterialStack(
                    id=record.id,
                    character_id=record.character_id,
                    material_id=record.material_id,
                    quantity=record.quantity,
                    bound=record.bound,
                )
            )
            await session.delete(record)

    async def _legacy_commit_pending_claim(
        self, session: AsyncSession, character_id: UUID, operation: WarehouseOperation
    ) -> None:
        pending = await session.scalar(
            select(PendingItem)
            .where(
                PendingItem.id == UUID(operation.source_id),
                PendingItem.character_id == character_id,
            )
            .with_for_update()
        )
        if (
            pending is None
            or _fingerprint(self._pending_snapshot(pending)) != operation.fingerprint
        ):
            raise WarehouseRejected("STALE_PREVIEW")
        remaining = operation.quantity
        payload = dict(pending.payload or {})
        if pending.kind == "equipment":
            if (
                remaining != pending.quantity
                or await inventory_slots(session, character_id) >= INVENTORY_CAPACITY
            ):
                raise WarehouseRejected("STALE_PREVIEW")
            item_id, item_payload = equipment_instance_payload(payload)
            existing = await session.get(EquipmentItem, item_id)
            if (
                existing is not None
                or await session.get(WarehouseEquipmentItem, item_id) is not None
            ):
                raise WarehouseRejected("STALE_PREVIEW")
            session.add(
                EquipmentItem(
                    id=item_id,
                    character_id=character_id,
                    source_key=pending.source_key,
                    item_name=item_payload["item_name"],
                    rarity=item_payload["rarity"],
                    slot=item_payload["slot"],
                    item_level=item_payload["item_level"],
                    bound=bool(item_payload.get("bound", False)),
                    payload=item_payload,
                )
            )
            await session.delete(pending)
            return
        if pending.kind == "material":
            material_id = str(payload.get("material_id", ""))
            bound = bool(payload.get("bound", False))
            stacks = (
                await session.scalars(
                    select(MaterialStack)
                    .where(
                        MaterialStack.character_id == character_id,
                        MaterialStack.material_id == material_id,
                        MaterialStack.bound.is_(bound),
                        MaterialStack.quantity > 0,
                    )
                    .order_by(MaterialStack.id)
                    .with_for_update()
                )
            ).all()
            for stack in stacks:
                take = min(remaining, MATERIAL_STACK_LIMIT - stack.quantity)
                if take > 0:
                    stack.quantity += take
                    remaining -= take
                if remaining == 0:
                    break
            if remaining > 0:
                free = max(0, INVENTORY_CAPACITY - await inventory_slots(session, character_id))
                while remaining > 0 and free > 0:
                    take = min(remaining, MATERIAL_STACK_LIMIT)
                    session.add(
                        MaterialStack(
                            character_id=character_id,
                            material_id=material_id,
                            quantity=take,
                            bound=bound,
                        )
                    )
                    remaining -= take
                    free -= 1
        elif pending.kind == "consumable":
            consumable_id = str(payload.get("consumable_id", ""))
            stack = await session.scalar(
                select(ConsumableStack)
                .where(
                    ConsumableStack.character_id == character_id,
                    ConsumableStack.consumable_id == consumable_id,
                )
                .with_for_update()
            )
            if stack is None:
                if await inventory_slots(session, character_id) < INVENTORY_CAPACITY:
                    take = min(remaining, CONSUMABLE_STACK_LIMIT)
                    session.add(
                        ConsumableStack(
                            id=pending.id,
                            character_id=character_id,
                            consumable_id=consumable_id,
                            quantity=take,
                        )
                    )
                    remaining -= take
            else:
                take = min(remaining, CONSUMABLE_STACK_LIMIT - stack.quantity)
                if take > 0:
                    stack.quantity += take
                    remaining -= take
        elif pending.kind == "rune":
            values = {
                "family": payload.get("family"),
                "rarity": payload.get("rarity"),
                "grade": int(payload.get("grade", 1)),
                "potency": payload.get("potency"),
                "bound": bool(payload.get("bound", False)),
            }
            stack = await session.scalar(
                select(RuneStack)
                .where(
                    RuneStack.character_id == character_id,
                    RuneStack.family == values["family"],
                    RuneStack.rarity == values["rarity"],
                    RuneStack.grade == values["grade"],
                    RuneStack.bound.is_(values["bound"]),
                )
                .with_for_update()
            )
            if stack is not None:
                if stack.potency != values["potency"]:
                    raise WarehouseRejected("STALE_PREVIEW")
                stack.quantity += remaining
                remaining = 0
            elif await inventory_slots(session, character_id) < INVENTORY_CAPACITY:
                session.add(
                    RuneStack(
                        id=pending.id,
                        character_id=character_id,
                        **values,
                        quantity=remaining,
                    )
                )
                remaining = 0
        else:
            raise WarehouseRejected("UNSUPPORTED_PENDING_KIND")
        if remaining == 0:
            await session.delete(pending)
        else:
            pending.quantity -= operation.quantity - remaining
            if pending.quantity <= 0:
                await session.delete(pending)

    async def _legacy_pending_recoverable_quantity(
        self, session: AsyncSession, character_id: UUID, pending: PendingItem
    ) -> int:
        payload = dict(pending.payload or {})
        if pending.kind == "equipment":
            item_id, _ = equipment_instance_payload(payload)
            exists = await session.scalar(
                select(EquipmentItem.id).where(EquipmentItem.id == item_id)
            )
            if (
                exists is not None
                or await inventory_slots(session, character_id) >= INVENTORY_CAPACITY
            ):
                return 0
            return pending.quantity
        if pending.kind == "material":
            return await self._recoverable_stack_quantity(
                session,
                character_id,
                pending.quantity,
                MaterialStack,
                "material_id",
                payload.get("material_id"),
                bool(payload.get("bound", False)),
                MATERIAL_STACK_LIMIT,
            )
        if pending.kind == "consumable":
            existing = await session.scalar(
                select(ConsumableStack).where(
                    ConsumableStack.character_id == character_id,
                    ConsumableStack.consumable_id == payload.get("consumable_id"),
                )
            )
            if existing is not None:
                return min(pending.quantity, max(0, CONSUMABLE_STACK_LIMIT - existing.quantity))
            if await inventory_slots(session, character_id) < INVENTORY_CAPACITY:
                return min(pending.quantity, CONSUMABLE_STACK_LIMIT)
            return 0
        if pending.kind == "rune":
            stack = await session.scalar(
                select(RuneStack).where(
                    RuneStack.character_id == character_id,
                    RuneStack.family == payload.get("family"),
                    RuneStack.rarity == payload.get("rarity"),
                    RuneStack.grade == payload.get("grade", 1),
                    RuneStack.bound.is_(bool(payload.get("bound", False))),
                )
            )
            if stack is not None:
                return pending.quantity if stack.potency == payload.get("potency") else 0
            return (
                pending.quantity
                if await inventory_slots(session, character_id) < INVENTORY_CAPACITY
                else 0
            )
        return 0

    async def _recoverable_stack_quantity(
        self,
        session: AsyncSession,
        character_id: UUID,
        quantity: int,
        model,
        identity_field: str,
        identity: str | None,
        bound: bool,
        limit: int,
    ) -> int:
        if not identity:
            return 0
        query = select(model).where(
            model.character_id == character_id,
            getattr(model, identity_field) == identity,
            model.bound.is_(bound),
            model.quantity > 0,
        )
        rows = (await session.scalars(query)).all()
        room = sum(max(0, limit - row.quantity) for row in rows)
        free = max(0, INVENTORY_CAPACITY - await inventory_slots(session, character_id))
        return min(quantity, room + free * limit)

    async def _legacy_transfer_source(
        self,
        session: AsyncSession,
        character_id: UUID,
        direction: str,
        kind: str,
        source_id: UUID,
        *,
        lock: bool,
    ):
        if direction == "deposit" and kind == "equipment":
            statement = select(EquipmentItem).where(
                EquipmentItem.id == source_id,
                EquipmentItem.character_id == character_id,
            )
            if lock:
                statement = statement.with_for_update()
            row = await session.scalar(statement)
            if row is None:
                raise WarehouseRejected("ITEM_UNAVAILABLE")
            snapshot = self._equipment_snapshot(row)
            return row, snapshot, row.item_name, 1, row.source_key
        if direction == "deposit" and kind == "material":
            statement = select(MaterialStack).where(
                MaterialStack.id == source_id,
                MaterialStack.character_id == character_id,
                MaterialStack.quantity > 0,
            )
            if lock:
                statement = statement.with_for_update()
            row = await session.scalar(statement)
            if row is None:
                raise WarehouseRejected("ITEM_UNAVAILABLE")
            snapshot = self._material_snapshot(row)
            return row, snapshot, row.material_id, row.quantity, None
        if direction == "withdraw" and kind == "equipment":
            statement = select(WarehouseEquipmentItem).where(
                WarehouseEquipmentItem.id == source_id,
                WarehouseEquipmentItem.character_id == character_id,
            )
            if lock:
                statement = statement.with_for_update()
            row = await session.scalar(statement)
            if row is None:
                raise WarehouseRejected("ITEM_UNAVAILABLE")
            snapshot = self._warehouse_equipment_snapshot(row)
            return row, snapshot, row.item_name, 1, row.source_key
        if direction == "withdraw" and kind == "material":
            statement = select(WarehouseMaterialStack).where(
                WarehouseMaterialStack.id == source_id,
                WarehouseMaterialStack.character_id == character_id,
                WarehouseMaterialStack.quantity > 0,
            )
            if lock:
                statement = statement.with_for_update()
            row = await session.scalar(statement)
            if row is None:
                raise WarehouseRejected("ITEM_UNAVAILABLE")
            snapshot = self._warehouse_material_snapshot(row)
            return row, snapshot, row.material_id, row.quantity, None
        raise WarehouseRejected("INVALID_OPERATION")

    async def _commit_pending_claim(self, session, character_id, operation):
        pending = await session.scalar(
            select(PendingItem)
            .where(
                PendingItem.id == UUID(operation.source_id),
                PendingItem.character_id == character_id,
            )
            .with_for_update()
        )
        if (
            pending is None
            or _fingerprint(self._pending_snapshot(pending)) != operation.fingerprint
        ):
            raise WarehouseRejected("STALE_PREVIEW")
        if operation.quantity > pending.quantity or await self._pending_recoverable_quantity(
            session, character_id, pending
        ) < operation.quantity:
            raise WarehouseRejected("STALE_PREVIEW")
        await self._deliver_pending_quantity(session, character_id, pending, operation.quantity)

    async def _deliver_pending_quantity(self, session, character_id, pending, quantity):
        """Deliver only the previewed quantity; keep any remainder in the original queue row."""
        payload = dict(pending.payload or {})
        remaining = quantity
        if pending.kind == "equipment":
            if (
                quantity != pending.quantity
                or await inventory_slots(session, character_id) >= INVENTORY_CAPACITY
            ):
                raise WarehouseRejected("STALE_PREVIEW")
            item_id, item_payload = equipment_instance_payload(payload)
            if (
                await session.get(EquipmentItem, item_id) is not None
                or await session.get(WarehouseEquipmentItem, item_id) is not None
            ):
                raise WarehouseRejected("STALE_PREVIEW")
            session.add(EquipmentItem(
                id=item_id, character_id=character_id, source_key=pending.source_key,
                item_name=item_payload["item_name"], rarity=item_payload["rarity"],
                slot=item_payload["slot"], item_level=item_payload["item_level"],
                bound=bool(item_payload.get("bound", False)), payload=item_payload,
            ))
            await session.delete(pending)
            return
        if pending.kind == "material":
            material_id = str(payload.get("material_id", ""))
            bound = bool(payload.get("bound", False))
            rows = (await session.scalars(
                select(MaterialStack).where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.material_id == material_id,
                    MaterialStack.bound.is_(bound), MaterialStack.quantity > 0,
                ).order_by(MaterialStack.id).with_for_update()
            )).all()
            for row in rows:
                take = min(remaining, MATERIAL_STACK_LIMIT - row.quantity)
                row.quantity += take
                remaining -= take
                if not remaining:
                    break
            free = max(0, INVENTORY_CAPACITY - await inventory_slots(session, character_id))
            while remaining and free:
                take = min(remaining, MATERIAL_STACK_LIMIT)
                session.add(MaterialStack(
                    character_id=character_id, material_id=material_id,
                    quantity=take, bound=bound,
                ))
                remaining -= take
                free -= 1
        elif pending.kind == "consumable":
            if bool(payload.get("bound", False)):
                raise WarehouseRejected("UNSUPPORTED_PENDING_KIND")
            consumable_id = str(payload.get("consumable_id", ""))
            row = await session.scalar(select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == consumable_id,
            ).with_for_update())
            if row is None:
                if await inventory_slots(session, character_id) < INVENTORY_CAPACITY:
                    take = min(remaining, CONSUMABLE_STACK_LIMIT)
                    session.add(ConsumableStack(
                        id=pending.id, character_id=character_id,
                        consumable_id=consumable_id, quantity=take,
                    ))
                    remaining -= take
            else:
                take = min(remaining, CONSUMABLE_STACK_LIMIT - row.quantity)
                row.quantity += take
                remaining -= take
        elif pending.kind == "rune":
            values = {
                "family": payload.get("family"), "rarity": payload.get("rarity"),
                "grade": int(payload.get("grade", 1)), "potency": payload.get("potency"),
                "bound": bool(payload.get("bound", False)),
            }
            row = await session.scalar(select(RuneStack).where(
                RuneStack.character_id == character_id,
                RuneStack.family == values["family"], RuneStack.rarity == values["rarity"],
                RuneStack.grade == values["grade"], RuneStack.bound.is_(values["bound"]),
            ).with_for_update())
            if row is not None:
                if row.potency != values["potency"]:
                    raise WarehouseRejected("STALE_PREVIEW")
                row.quantity += remaining
                remaining = 0
            elif await inventory_slots(session, character_id) < INVENTORY_CAPACITY:
                session.add(RuneStack(
                    id=pending.id, character_id=character_id, **values, quantity=remaining,
                ))
                remaining = 0
        else:
            raise WarehouseRejected("UNSUPPORTED_PENDING_KIND")
        pending.quantity -= quantity - remaining
        if pending.quantity <= 0:
            await session.delete(pending)
        if remaining:
            raise WarehouseRejected("CAPACITY_CHANGED")

    async def _pending_recoverable_quantity(self, session, character_id, pending):
        payload = dict(pending.payload or {})
        if pending.kind == "equipment":
            item_id, _ = equipment_instance_payload(payload)
            if (
                await session.get(EquipmentItem, item_id) is not None
                or await session.get(WarehouseEquipmentItem, item_id) is not None
            ):
                return 0
            return (
                pending.quantity
                if await inventory_slots(session, character_id) < INVENTORY_CAPACITY
                else 0
            )
        if pending.kind == "material":
            return await self._recoverable_stack_quantity(
                session, character_id, pending.quantity, MaterialStack,
                "material_id", payload.get("material_id"), bool(payload.get("bound", False)),
                MATERIAL_STACK_LIMIT,
            )
        if pending.kind == "consumable":
            if bool(payload.get("bound", False)):
                return 0
            row = await session.scalar(select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == payload.get("consumable_id"),
            ))
            if row is not None:
                if (
                    row.quantity <= 0
                    and await inventory_slots(session, character_id) >= INVENTORY_CAPACITY
                ):
                    return 0
                return min(pending.quantity, max(0, CONSUMABLE_STACK_LIMIT - row.quantity))
            return (
                min(pending.quantity, CONSUMABLE_STACK_LIMIT)
                if await inventory_slots(session, character_id) < INVENTORY_CAPACITY
                else 0
            )
        if pending.kind == "rune":
            row = await session.scalar(select(RuneStack).where(
                RuneStack.character_id == character_id,
                RuneStack.family == payload.get("family"),
                RuneStack.rarity == payload.get("rarity"),
                RuneStack.grade == payload.get("grade", 1),
                RuneStack.bound.is_(bool(payload.get("bound", False))),
            ))
            if row is not None:
                if (
                    row.quantity <= 0
                    and await inventory_slots(session, character_id) >= INVENTORY_CAPACITY
                ):
                    return 0
                return pending.quantity if row.potency == payload.get("potency") else 0
            return (
                pending.quantity
                if await inventory_slots(session, character_id) < INVENTORY_CAPACITY
                else 0
            )
        return 0

    async def _recoverable_stack_quantity(
        self, session, character_id, quantity, model, key, value, bound, limit
    ):
        if not value:
            return 0
        rows = (await session.scalars(select(model).where(
            model.character_id == character_id,
            getattr(model, key) == value,
            model.bound.is_(bound), model.quantity > 0,
        ))).all()
        room = sum(max(0, limit - row.quantity) for row in rows)
        free = max(0, INVENTORY_CAPACITY - await inventory_slots(session, character_id))
        return min(quantity, room + free * limit)

    async def _transfer_source(self, session, character_id, direction, kind, source_id, *, lock):
        model = {
            ("deposit", "equipment"): EquipmentItem,
            ("deposit", "material"): MaterialStack,
            ("withdraw", "equipment"): WarehouseEquipmentItem,
            ("withdraw", "material"): WarehouseMaterialStack,
        }.get((direction, kind))
        if model is None:
            raise WarehouseRejected("INVALID_OPERATION")
        statement = select(model).where(model.id == source_id, model.character_id == character_id)
        if model in {MaterialStack, WarehouseMaterialStack}:
            statement = statement.where(model.quantity > 0)
        if lock:
            statement = statement.with_for_update()
        row = await session.scalar(statement)
        if row is None:
            raise WarehouseRejected("ITEM_UNAVAILABLE")
        if kind == "equipment":
            snapshot = self._equipment_snapshot(row)
            return row, snapshot, row.item_name, 1, row.source_key
        snapshot = self._material_snapshot(row)
        return row, snapshot, row.material_id, row.quantity, None

    async def _lock_character(self, session, actor):
        character_id = await session.scalar(select(Character.id).where(
            Character.telegram_id == actor, Character.server_id == self.server_id,
        ))
        if character_id is None:
            return None
        try:
            return await lock_for_combat_configuration_mutation(session, character_id)
        except CombatConfigurationLocked as exc:
            raise WarehouseRejected("FOREGROUND_LOCKED") from exc

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id,
        ))

    async def _warehouse_entries(self, session, character_id):
        equipment = (
            await session.scalars(
                select(WarehouseEquipmentItem)
                .where(WarehouseEquipmentItem.character_id == character_id)
                .order_by(WarehouseEquipmentItem.item_name, WarehouseEquipmentItem.id)
            )
        ).all()
        materials = (
            await session.scalars(
                select(WarehouseMaterialStack)
                .where(
                    WarehouseMaterialStack.character_id == character_id,
                    WarehouseMaterialStack.quantity > 0,
                )
                .order_by(
                    WarehouseMaterialStack.material_id,
                    WarehouseMaterialStack.bound,
                    WarehouseMaterialStack.id,
                )
            )
        ).all()
        return [
            WarehouseEntry(
                str(row.id), "equipment", row.item_name, 1, row.bound,
                row.rarity, row.slot, row.item_level, row.source_key,
                payload=dict(row.payload or {}),
            )
            for row in equipment
        ] + [
            WarehouseEntry(str(row.id), "material", row.material_id, row.quantity, row.bound)
            for row in materials
        ]

    async def _is_equipped(self, session, character_id, item_id):
        return await session.scalar(select(CharacterEquipmentSlot.equipment_item_id).where(
            CharacterEquipmentSlot.character_id == character_id,
            CharacterEquipmentSlot.equipment_item_id == item_id,
        )) is not None

    async def _operation(self, session, character_id, operation_id, *, lock):
        statement = select(WarehouseOperation).where(
            WarehouseOperation.id == operation_id,
            WarehouseOperation.character_id == character_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    @staticmethod
    def _new_operation(character_id, direction, kind, source_id, source_key, quantity, snapshot):
        now = datetime.now(UTC)
        return WarehouseOperation(
            id=uuid4(), character_id=character_id, direction=direction, kind=kind,
            source_id=source_id, source_key=source_key, quantity=quantity,
            fingerprint=_fingerprint(snapshot), snapshot=snapshot,
            status="preview", created_at=now,
            expires_at=now + OPERATION_TTL,
        )

    @staticmethod
    def _equipment_snapshot(row):
        return {
            "id": str(row.id), "character_id": str(row.character_id),
            "source_key": row.source_key, "item_name": row.item_name,
            "rarity": row.rarity, "slot": row.slot, "item_level": row.item_level,
            "bound": bool(row.bound), "payload": dict(row.payload or {}),
        }

    @staticmethod
    def _warehouse_equipment_snapshot(row):
        return WarehouseService._equipment_snapshot(row)

    @staticmethod
    def _material_snapshot(row):
        return {
            "id": str(row.id), "character_id": str(row.character_id),
            "material_id": row.material_id, "quantity": row.quantity, "bound": bool(row.bound),
        }

    @staticmethod
    def _warehouse_material_snapshot(row):
        return WarehouseService._material_snapshot(row)

    @staticmethod
    def _pending_snapshot(row):
        return {
            "id": str(row.id), "character_id": str(row.character_id),
            "source_key": row.source_key, "kind": row.kind,
            "payload": dict(row.payload or {}), "quantity": row.quantity,
        }

    @staticmethod
    def _pending_title(row):
        payload = dict(row.payload or {})
        return str(payload.get("item_name") or payload.get("material_id")
                   or payload.get("consumable_id") or payload.get("family")
                   or "Entrega Pendente")


def _fingerprint(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(payload).hexdigest()
