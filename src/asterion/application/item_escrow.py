"""Moves negotiable items in and out of Market and Direct Trade escrow.

An item in escrow leaves the Inventory tables and lives only in the snapshot of
its listing or trade (GDD v1.6.0 §43.2: one item, one flow). No other system can
equip, spend, deposit or dismantle it, because for them the item is simply gone.
Equipment keeps its instance id and source key across owners.

Callers hold the row lock of every character involved before calling these.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.inventory import (
    MATERIAL_LABELS,
    REGIONAL_RUNE_TITLES,
    consumable_inventory_entry,
)
from asterion.application.inventory_capacity import (
    inventory_capacity,
    inventory_slots,
    pending_capacity,
)
from asterion.domain.equipment import assign_equipment_instance_id
from asterion.domain.market import MYTHIC_RARITY, market_unlocked
from asterion.infrastructure.db.models import (
    BlockedDelivery,
    Character,
    CharacterEquipmentSlot,
    ConsumableStack,
    EquipmentItem,
    MaterialStack,
    PendingItem,
    RuneStack,
)

ITEM_KINDS = ("equipment", "material", "consumable", "rune")
MATERIAL_STACK_LIMIT = 999
CONSUMABLE_STACK_LIMIT = 99

_STACK_MODELS = {"material": MaterialStack, "consumable": ConsumableStack, "rune": RuneStack}
_MYTHIC_LABELS = {MYTHIC_RARITY.casefold(), "mitico", "mythic"}


class EscrowError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EscrowedItem:
    kind: str
    snapshot: dict[str, Any]
    title: str
    rarity: str | None
    quantity: int


@dataclass(frozen=True, slots=True)
class NegotiableEntry:
    id: UUID
    kind: str
    title: str
    quantity: int
    rarity: str | None
    eligible: bool
    reason: str | None


async def require_trading_character(
    session: AsyncSession,
    actor: int,
    server_id: str,
    *,
    error: type[ValueError],
    lock: bool = False,
    guard: bool = False,
) -> Character:
    """The actor's Character, once past the Prologue (author decision 2026-11-08).

    `guard` also refuses while a combat configuration lock is in force (§43.2);
    use it for every action that takes an item out of the Inventory.
    """
    statement = select(Character).where(
        Character.telegram_id == actor, Character.server_id == server_id
    )
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    character = await session.scalar(statement)
    if character is None:
        raise error("character_missing")
    if guard:
        try:
            await lock_for_combat_configuration_mutation(session, character.id)
        except CombatConfigurationLocked as exc:
            raise error("foreground_locked") from exc
        await session.refresh(character)
    if not market_unlocked(character.stage):
        raise error("market_locked")
    return character


def is_mythic(rarity: str | None) -> bool:
    return bool(rarity) and rarity.casefold() in _MYTHIC_LABELS


def equipment_block_reason(item: EquipmentItem, *, equipped: bool) -> str | None:
    """§24.3 and §23: why this equipment cannot enter a Shop or a Trade."""
    payload = item.payload or {}
    if equipped:
        return "item_equipped"
    if item.bound or payload.get("bound"):
        return "item_bound"
    if payload.get("locked"):
        return "item_locked"
    components = [payload.get("rune"), payload.get("enchantment")]
    components.extend((payload.get("runes") or {}).values())
    if any(isinstance(part, dict) and part.get("bound") for part in components):
        return "item_component_bound"
    return None


def _stack_title(kind: str, row: Any) -> str:
    if kind == "consumable":
        return consumable_inventory_entry(row.consumable_id, row.quantity).title
    if kind == "rune":
        return REGIONAL_RUNE_TITLES.get(row.family, f"Runa de {row.family}")
    return MATERIAL_LABELS.get(row.material_id, row.material_id)


def _stack_snapshot(kind: str, row: Any) -> dict[str, Any]:
    if kind == "material":
        return {"material_id": row.material_id, "bound": row.bound}
    if kind == "consumable":
        return {"consumable_id": row.consumable_id, "bound": False}
    return {
        "family": row.family,
        "rarity": row.rarity,
        "grade": row.grade,
        "potency": row.potency,
        "bound": row.bound,
    }


async def _equipped_ids(session: AsyncSession, character_id: UUID) -> set[UUID]:
    rows = await session.scalars(
        select(CharacterEquipmentSlot.equipment_item_id).where(
            CharacterEquipmentSlot.character_id == character_id
        )
    )
    return set(rows.all())


async def negotiable_entries(
    session: AsyncSession, character_id: UUID, kind: str
) -> tuple[NegotiableEntry, ...]:
    """Inventory items of one kind, each marked sellable or with the reason it is not."""
    if kind == "equipment":
        equipped = await _equipped_ids(session, character_id)
        items = (
            await session.scalars(
                select(EquipmentItem)
                .where(EquipmentItem.character_id == character_id)
                .order_by(EquipmentItem.item_name, EquipmentItem.id)
            )
        ).all()
        entries = []
        for item in items:
            reason = equipment_block_reason(item, equipped=item.id in equipped)
            entries.append(
                NegotiableEntry(item.id, kind, item.item_name, 1, item.rarity, not reason, reason)
            )
        return tuple(entries)
    model = _STACK_MODELS.get(kind)
    if model is None:
        raise EscrowError("invalid_kind")
    rows = (
        await session.scalars(
            select(model)
            .where(model.character_id == character_id, model.quantity > 0)
            .order_by(model.id)
        )
    ).all()
    entries = []
    for row in rows:
        reason = "item_bound" if getattr(row, "bound", False) else None
        entries.append(
            NegotiableEntry(
                row.id,
                kind,
                _stack_title(kind, row),
                row.quantity,
                getattr(row, "rarity", None),
                not reason,
                reason,
            )
        )
    return tuple(entries)


async def take_from_inventory(
    session: AsyncSession, character_id: UUID, kind: str, source_id: UUID, quantity: int
) -> EscrowedItem:
    """Remove a negotiable item or part of a stack and return what was taken."""
    if kind == "equipment":
        item = await session.scalar(
            select(EquipmentItem)
            .where(EquipmentItem.id == source_id, EquipmentItem.character_id == character_id)
            .with_for_update()
        )
        if item is None:
            raise EscrowError("item_unavailable")
        if quantity != 1:
            raise EscrowError("invalid_quantity")
        equipped = source_id in await _equipped_ids(session, character_id)
        reason = equipment_block_reason(item, equipped=equipped)
        if reason:
            raise EscrowError(reason)
        taken = EscrowedItem(
            kind=kind,
            snapshot={
                "id": str(item.id),
                "source_key": item.source_key,
                "item_name": item.item_name,
                "rarity": item.rarity,
                "slot": item.slot,
                "item_level": item.item_level,
                "bound": False,
                "payload": dict(item.payload or {}),
            },
            title=item.item_name,
            rarity=item.rarity,
            quantity=1,
        )
        await session.delete(item)
        await session.flush()
        return taken
    model = _STACK_MODELS.get(kind)
    if model is None:
        raise EscrowError("invalid_kind")
    row = await session.scalar(
        select(model)
        .where(model.id == source_id, model.character_id == character_id, model.quantity > 0)
        .with_for_update()
    )
    if row is None:
        raise EscrowError("item_unavailable")
    if getattr(row, "bound", False):
        raise EscrowError("item_bound")
    if not 1 <= quantity <= row.quantity:
        raise EscrowError("invalid_quantity")
    taken = EscrowedItem(
        kind=kind,
        snapshot=_stack_snapshot(kind, row),
        title=_stack_title(kind, row),
        rarity=getattr(row, "rarity", None),
        quantity=quantity,
    )
    row.quantity -= quantity
    if row.quantity == 0:
        await session.delete(row)
    await session.flush()
    return taken


async def _free_slots(session: AsyncSession, character_id: UUID) -> int:
    capacity = await inventory_capacity(session, character_id)
    return max(0, capacity - await inventory_slots(session, character_id))


async def _deliver_material(session, character_id, snapshot, quantity) -> int:
    bound = bool(snapshot.get("bound", False))
    rows = (
        await session.scalars(
            select(MaterialStack)
            .where(
                MaterialStack.character_id == character_id,
                MaterialStack.material_id == snapshot["material_id"],
                MaterialStack.bound.is_(bound),
                MaterialStack.quantity > 0,
            )
            .order_by(MaterialStack.id)
            .with_for_update()
        )
    ).all()
    remaining = quantity
    for row in rows:
        take = min(remaining, MATERIAL_STACK_LIMIT - row.quantity)
        row.quantity += take
        remaining -= take
    free = await _free_slots(session, character_id)
    while remaining and free:
        take = min(remaining, MATERIAL_STACK_LIMIT)
        session.add(
            MaterialStack(
                character_id=character_id,
                material_id=snapshot["material_id"],
                quantity=take,
                bound=bound,
            )
        )
        remaining -= take
        free -= 1
    return remaining


async def _deliver_consumable(session, character_id, snapshot, quantity) -> int:
    row = await session.scalar(
        select(ConsumableStack)
        .where(
            ConsumableStack.character_id == character_id,
            ConsumableStack.consumable_id == snapshot["consumable_id"],
        )
        .with_for_update()
    )
    if row is None or row.quantity == 0:
        if await _free_slots(session, character_id) == 0:
            return quantity
    take = min(quantity, CONSUMABLE_STACK_LIMIT - (row.quantity if row else 0))
    if row is None:
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id=snapshot["consumable_id"],
                quantity=take,
            )
        )
    else:
        row.quantity += take
    return quantity - take


async def _deliver_rune(session, character_id, snapshot, quantity) -> int:
    bound = bool(snapshot.get("bound", False))
    row = await session.scalar(
        select(RuneStack)
        .where(
            RuneStack.character_id == character_id,
            RuneStack.family == snapshot["family"],
            RuneStack.rarity == snapshot["rarity"],
            RuneStack.grade == snapshot["grade"],
            RuneStack.bound.is_(bound),
        )
        .with_for_update()
    )
    if row is not None and row.potency != snapshot["potency"]:
        return quantity
    if (row is None or row.quantity == 0) and await _free_slots(session, character_id) == 0:
        return quantity
    if row is None:
        session.add(
            RuneStack(
                character_id=character_id,
                family=snapshot["family"],
                rarity=snapshot["rarity"],
                grade=snapshot["grade"],
                potency=snapshot["potency"],
                quantity=quantity,
                bound=bound,
            )
        )
    else:
        row.quantity += quantity
    return 0


async def _deliver_equipment(session, character_id, snapshot, *, new_owner: bool) -> int:
    if await _free_slots(session, character_id) == 0:
        return 1
    payload = dict(snapshot["payload"])
    if new_owner:
        payload.pop("favorite", None)
    session.add(
        EquipmentItem(
            id=UUID(snapshot["id"]),
            character_id=character_id,
            source_key=snapshot["source_key"],
            item_name=snapshot["item_name"],
            rarity=snapshot["rarity"],
            slot=snapshot["slot"],
            item_level=snapshot["item_level"],
            bound=bool(snapshot.get("bound", False)),
            payload=payload,
        )
    )
    return 0


async def deliver_to_inventory(
    session: AsyncSession,
    character_id: UUID,
    kind: str,
    snapshot: dict[str, Any],
    quantity: int,
    *,
    new_owner: bool,
) -> int:
    """Put an item in the Inventory; returns the quantity that did not fit."""
    if kind == "equipment":
        remaining = await _deliver_equipment(session, character_id, snapshot, new_owner=new_owner)
    elif kind == "material":
        remaining = await _deliver_material(session, character_id, snapshot, quantity)
    elif kind == "consumable":
        remaining = await _deliver_consumable(session, character_id, snapshot, quantity)
    elif kind == "rune":
        remaining = await _deliver_rune(session, character_id, snapshot, quantity)
    else:
        raise EscrowError("invalid_kind")
    await session.flush()
    return remaining


def _pending_payload(kind: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    if kind != "equipment":
        return dict(snapshot)
    fields = {key: snapshot[key] for key in ("item_name", "rarity", "slot", "item_level", "bound")}
    _, payload = assign_equipment_instance_id(
        {**snapshot["payload"], **fields}, instance_id=UUID(snapshot["id"])
    )
    return payload


async def return_to_owner(
    session: AsyncSession,
    character: Character,
    kind: str,
    snapshot: dict[str, Any],
    quantity: int,
    source_key: str,
) -> str:
    """§28.13 return: Inventory first, then Pending, then a durable delivery hold.

    `source_key` starts with "market:" so the Pending screen names its origin.
    """
    remaining = await deliver_to_inventory(
        session, character.id, kind, snapshot, quantity, new_owner=False
    )
    if remaining == 0:
        return "inventory"
    payload = _pending_payload(kind, snapshot)
    pending_count = await session.scalar(
        select(func.count(PendingItem.id)).where(PendingItem.character_id == character.id)
    )
    if int(pending_count or 0) < await pending_capacity(session, character.id):
        session.add(
            PendingItem(
                character_id=character.id,
                source_key=source_key,
                kind=kind,
                payload=payload,
                quantity=remaining,
            )
        )
        await session.flush()
        return "pending"
    session.add(
        BlockedDelivery(
            character_id=character.id,
            source_key=source_key,
            kind=kind,
            payload=payload,
            quantity=remaining,
        )
    )
    character.delivery_blocked = True
    await session.flush()
    return "blocked"
