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
from asterion.application.inventory import (
    MATERIAL_LABELS,
    REGIONAL_RUNE_TITLES,
    InventoryService,
    consumable_inventory_entry,
)
from asterion.application.inventory_capacity import (
    INVENTORY_CAPACITY,
    WAREHOUSE_CAPACITY,
    inventory_capacity,
    inventory_slot_counts,
    inventory_slots,
    warehouse_capacity,
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
    WarehouseConsumableStack,
    WarehouseEquipmentItem,
    WarehouseMaterialStack,
    WarehouseOperation,
    WarehouseRuneStack,
)

OPERATION_TTL = timedelta(minutes=5)
MATERIAL_STACK_LIMIT = 999
CONSUMABLE_STACK_LIMIT = 99

INVENTORY_MODELS = {
    "equipment": EquipmentItem,
    "material": MaterialStack,
    "consumable": ConsumableStack,
    "rune": RuneStack,
}
STORED_MODELS = {
    "equipment": WarehouseEquipmentItem,
    "material": WarehouseMaterialStack,
    "consumable": WarehouseConsumableStack,
    "rune": WarehouseRuneStack,
}
COPIED_FIELDS = {
    "equipment": (
        "id",
        "character_id",
        "source_key",
        "item_name",
        "rarity",
        "slot",
        "item_level",
        "bound",
        "payload",
    ),
    "material": ("id", "character_id", "material_id", "quantity", "bound"),
    "consumable": ("id", "character_id", "consumable_id", "quantity"),
    "rune": (
        "id",
        "character_id",
        "family",
        "rarity",
        "grade",
        "potency",
        "quantity",
        "bound",
    ),
}
STACK_LIMITS = {
    "material": MATERIAL_STACK_LIMIT,
    "consumable": CONSUMABLE_STACK_LIMIT,
    "rune": None,
}
STACK_IDENTITY = {
    "material": ("material_id", "bound"),
    "consumable": ("consumable_id",),
    "rune": ("family", "rarity", "grade", "bound"),
}
STACK_ORDER = {
    "material": ("material_id", "bound", "id"),
    "consumable": ("consumable_id", "id"),
    "rune": ("family", "rarity", "grade", "bound", "id"),
}


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
    grade: int | None = None


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
    source_id: UUID | None = None
    inventory_capacity: int = INVENTORY_CAPACITY
    warehouse_capacity: int = WAREHOUSE_CAPACITY


@dataclass(frozen=True, slots=True)
class WarehouseResult:
    status: str
    direction: str
    kind: str
    quantity: int
    operation_id: UUID


class WarehouseService:
    """Moves items and stack quantities while preserving their identities."""

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
                inventory_capacity=await inventory_capacity(session, character.id),
                warehouse_capacity=await warehouse_capacity(session, character.id),
                warehouse_used=len(stored),
                entries=tuple(stored),
            )

    async def inventory_sources(self, actor: int, kind: str) -> WarehouseView | None:
        if kind not in INVENTORY_MODELS:
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
                        eligible=row.id not in equipped,
                        reason="EQUIPPED" if row.id in equipped else None,
                        payload=dict(row.payload or {}),
                    )
                    for row in rows
                )
            else:
                entries = tuple(
                    await self._stack_entries(
                        session, INVENTORY_MODELS[kind], kind, character.id
                    )
                )
            return WarehouseView(
                kind="warehouse_inventory_sources",
                character_id=character.id,
                accessible=True,
                location=safe[1],
                inventory_used=sum(counts.values()),
                inventory_capacity=await inventory_capacity(session, character.id),
                warehouse_capacity=await warehouse_capacity(session, character.id),
                warehouse_used=await warehouse_slots(session, character.id),
                entries=entries,
                item_kind=kind,
            )

    async def transfer_quantity(
        self, actor: int, direction: str, kind: str, source_id: UUID
    ) -> WarehouseView | None:
        """Read the stack a player is choosing an amount from; nothing is reserved yet."""

        if direction not in {"deposit", "withdraw"} or kind not in STACK_ORDER:
            raise WarehouseRejected("INVALID_OPERATION")
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            safe = await current_permanent_brazier(session, character.id)
            if safe is None:
                raise WarehouseRejected("SAFE_LOCATION_REQUIRED")
            _record, _snapshot, title, quantity, _source_key = await self._transfer_source(
                session, character.id, direction, kind, source_id, lock=False
            )
            counts = await inventory_slot_counts(session, character.id)
            return WarehouseView(
                kind="warehouse_quantity",
                character_id=character.id,
                accessible=True,
                location=safe[1],
                inventory_used=sum(counts.values()),
                inventory_capacity=await inventory_capacity(session, character.id),
                warehouse_capacity=await warehouse_capacity(session, character.id),
                warehouse_used=await warehouse_slots(session, character.id),
                direction=direction,
                item_kind=kind,
                title=title,
                quantity=quantity,
                source_id=source_id,
            )

    async def prepare_transfer(
        self,
        actor: int,
        direction: str,
        kind: str,
        source_id: UUID,
        quantity: int | None = None,
    ) -> WarehouseView | None:
        if direction not in {"deposit", "withdraw"} or kind not in INVENTORY_MODELS:
            raise WarehouseRejected("INVALID_OPERATION")
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            safe = await current_permanent_brazier(session, character.id)
            if safe is None:
                raise WarehouseRejected("SAFE_LOCATION_REQUIRED")
            record, snapshot, title, available, source_key = await self._transfer_source(
                session, character.id, direction, kind, source_id, lock=True
            )
            amount = available if quantity is None else quantity
            if not 1 <= amount <= available:
                raise WarehouseRejected("INVALID_QUANTITY")
            if kind != "equipment":
                await self._stack_plan(session, character.id, direction, kind, record, amount)
            elif direction == "deposit":
                if await self._is_equipped(session, character.id, source_id):
                    raise WarehouseRejected("EQUIPPED")
                if await warehouse_slots(session, character.id) >= (
                    await warehouse_capacity(session, character.id)
                ):
                    raise WarehouseRejected("WAREHOUSE_FULL")
            elif await inventory_slots(session, character.id) >= (
                await inventory_capacity(session, character.id)
            ):
                raise WarehouseRejected("INVENTORY_FULL")
            operation = self._new_operation(
                character.id,
                direction,
                kind,
                str(source_id),
                source_key,
                amount,
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
                inventory_capacity=await inventory_capacity(session, character.id),
                warehouse_capacity=await warehouse_capacity(session, character.id),
                warehouse_used=await warehouse_slots(session, character.id),
                operation_id=operation.id,
                direction=direction,
                item_kind=kind,
                title=title,
                quantity=amount,
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
            title = InventoryService.pending_entry(pending).title
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
                inventory_capacity=await inventory_capacity(session, character.id),
                warehouse_capacity=await warehouse_capacity(session, character.id),
                warehouse_used=await warehouse_slots(session, character.id),
                operation_id=operation.id,
                direction="claim_pending",
                item_kind=pending.kind,
                title=title,
                quantity=amount,
                status="preview",
                origin=pending.source_key,
            )

    async def cancel(self, actor: int, operation_id: UUID) -> str:
        async with self.sessions.begin() as session:
            # Cancelling moves no item, so an activity in progress must not block it.
            character = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
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
        direction, kind, amount = operation.direction, operation.kind, operation.quantity
        record, snapshot, _title, available, _source_key = await self._transfer_source(
            session, character_id, direction, kind, source_id, lock=True
        )
        if _fingerprint(snapshot) != operation.fingerprint or amount > available:
            raise WarehouseRejected("STALE_PREVIEW")
        target = STORED_MODELS[kind] if direction == "deposit" else INVENTORY_MODELS[kind]
        if kind == "equipment":
            if direction == "deposit":
                if await self._is_equipped(session, character_id, source_id):
                    raise WarehouseRejected("STALE_PREVIEW")
                if await warehouse_slots(session, character_id) >= (
                    await warehouse_capacity(session, character_id)
                ):
                    raise WarehouseRejected("WAREHOUSE_FULL")
            elif await inventory_slots(session, character_id) >= (
                await inventory_capacity(session, character_id)
            ):
                raise WarehouseRejected("INVENTORY_FULL")
            session.add(_copy(target, kind, record))
            await session.delete(record)
            return
        merges, leftover = await self._stack_plan(
            session, character_id, direction, kind, record, amount
        )
        for row, take in merges:
            row.quantity += take
        if leftover:
            stack = _copy(target, kind, record)
            if leftover != record.quantity:
                stack.id = uuid4()
            stack.quantity = leftover
            session.add(stack)
        record.quantity -= amount
        if record.quantity == 0:
            await session.delete(record)

    async def _stack_plan(self, session, character_id, direction, kind, record, amount):
        """Validate the destination; return top-ups and what needs a new stack."""

        deposit = direction == "deposit"
        model = STORED_MODELS[kind] if deposit else INVENTORY_MODELS[kind]
        rows = (
            await session.scalars(
                select(model)
                .where(
                    model.character_id == character_id,
                    *(
                        getattr(model, field) == getattr(record, field)
                        for field in STACK_IDENTITY[kind]
                    ),
                )
                .order_by(model.id)
                .with_for_update()
            )
        ).all()
        if kind == "rune":
            matching = [row for row in rows if row.potency == record.potency]
            if not deposit and len(matching) != len(rows):
                raise WarehouseRejected("STACK_CONFLICT")
            rows = matching
        limit = STACK_LIMITS[kind]
        merges = []
        remaining = amount
        for row in rows:
            take = remaining if limit is None else min(remaining, limit - row.quantity)
            if row.quantity > 0 and take > 0:
                merges.append((row, take))
                remaining -= take
        if not remaining:
            return merges, 0
        if not deposit and kind == "consumable" and any(row.quantity > 0 for row in rows):
            raise WarehouseRejected("STACK_FULL")
        if deposit:
            if await warehouse_slots(session, character_id) >= (
                await warehouse_capacity(session, character_id)
            ):
                raise WarehouseRejected("WAREHOUSE_FULL")
        elif await inventory_slots(session, character_id) >= (
            await inventory_capacity(session, character_id)
        ):
            raise WarehouseRejected("INVENTORY_FULL")
        empty = next((row for row in rows if row.quantity <= 0), None)
        if empty is not None:
            merges.append((empty, remaining))
            return merges, 0
        return merges, remaining

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
                or await inventory_slots(session, character_id) >= (
                    await inventory_capacity(session, character_id)
                )
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
            capacity = await inventory_capacity(session, character_id)
            free = max(0, capacity - await inventory_slots(session, character_id))
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
                if await inventory_slots(session, character_id) < (
                    await inventory_capacity(session, character_id)
                ):
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
            elif await inventory_slots(session, character_id) < (
                await inventory_capacity(session, character_id)
            ):
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
                if await inventory_slots(session, character_id) < (
                    await inventory_capacity(session, character_id)
                )
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
                    and await inventory_slots(session, character_id) >= (
                        await inventory_capacity(session, character_id)
                    )
                ):
                    return 0
                return min(pending.quantity, max(0, CONSUMABLE_STACK_LIMIT - row.quantity))
            return (
                min(pending.quantity, CONSUMABLE_STACK_LIMIT)
                if await inventory_slots(session, character_id) < (
                    await inventory_capacity(session, character_id)
                )
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
                    and await inventory_slots(session, character_id) >= (
                        await inventory_capacity(session, character_id)
                    )
                ):
                    return 0
                return pending.quantity if row.potency == payload.get("potency") else 0
            return (
                pending.quantity
                if await inventory_slots(session, character_id) < (
                    await inventory_capacity(session, character_id)
                )
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
        capacity = await inventory_capacity(session, character_id)
        free = max(0, capacity - await inventory_slots(session, character_id))
        return min(quantity, room + free * limit)

    async def _transfer_source(self, session, character_id, direction, kind, source_id, *, lock):
        models = {"deposit": INVENTORY_MODELS, "withdraw": STORED_MODELS}.get(direction, {})
        model = models.get(kind)
        if model is None:
            raise WarehouseRejected("INVALID_OPERATION")
        statement = select(model).where(model.id == source_id, model.character_id == character_id)
        if kind != "equipment":
            statement = statement.where(model.quantity > 0)
        if lock:
            statement = statement.with_for_update()
        row = await session.scalar(statement)
        if row is None:
            raise WarehouseRejected("ITEM_UNAVAILABLE")
        snapshot = self._snapshot(kind, row)
        if kind == "equipment":
            return row, snapshot, row.item_name, 1, row.source_key
        return row, snapshot, _stack_title(kind, row), row.quantity, None

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
        entries = [
            WarehouseEntry(
                str(row.id), "equipment", row.item_name, 1, row.bound,
                row.rarity, row.slot, row.item_level, row.source_key,
                payload=dict(row.payload or {}),
            )
            for row in equipment
        ]
        for kind in STACK_ORDER:
            entries.extend(
                await self._stack_entries(session, STORED_MODELS[kind], kind, character_id)
            )
        return entries

    async def _stack_entries(self, session, model, kind, character_id):
        rows = (
            await session.scalars(
                select(model)
                .where(model.character_id == character_id, model.quantity > 0)
                .order_by(*(getattr(model, column) for column in STACK_ORDER[kind]))
            )
        ).all()
        return [
            WarehouseEntry(
                str(row.id),
                kind,
                _stack_title(kind, row),
                row.quantity,
                bool(getattr(row, "bound", False)),
                rarity=getattr(row, "rarity", None),
                grade=_stack_grade(kind, row),
            )
            for row in rows
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
    def _snapshot(kind, row):
        values = {field: getattr(row, field) for field in COPIED_FIELDS[kind]}
        values["id"] = str(row.id)
        values["character_id"] = str(row.character_id)
        if kind == "equipment":
            values["payload"] = dict(row.payload or {})
        return values

    @staticmethod
    def _pending_snapshot(row):
        return {
            "id": str(row.id), "character_id": str(row.character_id),
            "source_key": row.source_key, "kind": row.kind,
            "payload": dict(row.payload or {}), "quantity": row.quantity,
        }


def _copy(model, kind, record):
    return model(**{field: getattr(record, field) for field in COPIED_FIELDS[kind]})


def _stack_title(kind: str, row) -> str:
    if kind == "consumable":
        return consumable_inventory_entry(row.consumable_id, row.quantity).title
    if kind == "rune":
        return REGIONAL_RUNE_TITLES.get(row.family, f"Runa de {row.family}")
    return MATERIAL_LABELS.get(row.material_id, row.material_id)


def _stack_grade(kind: str, row) -> int | None:
    if kind == "consumable":
        return consumable_inventory_entry(row.consumable_id, row.quantity).grade
    return row.grade if kind == "rune" else None


def _fingerprint(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(payload).hexdigest()
