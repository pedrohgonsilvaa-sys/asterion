"""Read-only Inventory and Pending views used by Telegram system navigation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.consumables import daily_consumable_cycle
from asterion.application.vigor import reconcile_character_vigor, utcnow
from asterion.domain.consumables import VIGOR_USABLE_AT_OR_BELOW, ConsumableFamily
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.equipment import assignment_for_item_slot
from asterion.infrastructure.db.models import (
    BlockedDelivery,
    Character,
    CharacterEquipmentSlot,
    ConsumableStack,
    EquipmentItem,
    GameActivity,
    MaterialStack,
    PendingItem,
    RuneStack,
)

INVENTORY_CAPACITY = 60
PENDING_CAPACITY = 20

VALID_CATEGORIES = ("equipment", "consumables", "materials", "runes")

MATERIAL_LABELS = {
    "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
    "material.tdo.couro_escoriado": "Couro Escoriado",
    "material.tdo.erva_cinzenta": "Erva Cinzenta",
    "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
    "material.tdo.catalisador_elite_i": "Catalisador de Elite I",
    "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
    "material.tdo.nucleo_vigia_partido": "Núcleo do Vigia Partido",
    "material.vde.nucleo_matriarca_das_raizes": "Núcleo da Matriarca das Raízes",
    "material.tdo.nucleo_cripta_ocaso": "Núcleo da Cripta do Ocaso",
    "material.tdo.nucleo_galerias_vigia": "Núcleo das Galerias do Vigia",
    "material.vde.ferro_enredado": "Ferro Enredado",
    "material.vde.couro_musgoso": "Couro Musgoso",
    "material.vde.erva_de_turfa": "Erva de Turfa",
    "material.vde.resina_enredada": "Resina Enredada",
    "material.vde.catalisador_elite_ii": "Catalisador de Elite II",
    "material.vde.fragmento_aprimoramento_ii": "Fragmento de Aprimoramento II",
    "material.vde.nucleo_fosso_raizes": "Núcleo do Fosso das Raízes",
}

@dataclass(frozen=True)
class InventoryEntry:
    kind: str
    key: str
    title: str
    quantity: int = 1
    rarity: str | None = None
    slot: str | None = None
    item_level: int | None = None
    grade: int | None = None
    bound: bool = False
    payload: dict | None = None
    equipped_slot: str | None = None

    @property
    def equipped(self) -> bool:
        return self.equipped_slot is not None


@dataclass(frozen=True)
class InventoryView:
    kind: str
    character_id: UUID
    used_slots: int
    capacity: int = INVENTORY_CAPACITY
    equipment_slots: int = 0
    consumable_slots: int = 0
    material_slots: int = 0
    rune_slots: int = 0
    category: str | None = None
    entries: tuple[InventoryEntry, ...] = ()
    pending_count: int = 0
    pending_capacity: int = PENDING_CAPACITY
    blocked_delivery_count: int = 0
    vigor: int | None = None
    max_vigor: int = 100
    vigor_usable: bool = False
    secondary_blocked_by_two_handed: bool = False


def consumable_inventory_entry(item_id: str, quantity: int) -> InventoryEntry:
    """Resolve existing stock IDs through the canonical item catalog."""
    item = consumable_definition(item_id)
    return InventoryEntry(
        kind="consumable",
        key=item_id,
        title=item.name if item is not None else item_id,
        quantity=quantity,
        grade=item.grade if item is not None else None,
        payload=(
            {
                "family": item.family.value,
                "region": item.region,
                "use_context": item.use_context.value,
                "target": item.target.value,
                "round_eligible": item.round_eligible,
            }
            if item is not None
            else None
        ),
    )


class InventoryService:
    """Server-authoritative read model for Inventory and Pending navigation.

    This block deliberately exposes no mutation that the Sources have not defined.
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id

    async def root(self, actor: int) -> InventoryView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            counts = await self._counts(session, character.id)
            return InventoryView(
                kind="inventory_root",
                character_id=character.id,
                used_slots=sum(counts.values()),
                equipment_slots=counts["equipment"],
                consumable_slots=counts["consumables"],
                material_slots=counts["materials"],
                rune_slots=counts["runes"],
            )

    async def category(self, actor: int, category: str) -> InventoryView | None:
        if category not in VALID_CATEGORIES:
            return None
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            counts = await self._counts(session, character.id)
            entries = await self._entries(session, character.id, category)
            secondary_blocked = any(
                entry.equipped_slot == "Principal"
                and (assignment := assignment_for_item_slot(entry.slot or "")) is not None
                and assignment.two_handed
                for entry in entries
            )
            return InventoryView(
                kind="inventory_category",
                character_id=character.id,
                used_slots=sum(counts.values()),
                equipment_slots=counts["equipment"],
                consumable_slots=counts["consumables"],
                material_slots=counts["materials"],
                rune_slots=counts["runes"],
                category=category,
                entries=tuple(entries),
                secondary_blocked_by_two_handed=secondary_blocked,
            )

    async def consumable_detail(self, actor: int, item_id: str) -> InventoryView | None:
        item = consumable_definition(item_id)
        if item is None:
            return None
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if character is None:
                return None
            await reconcile_character_vigor(session, character)
            counts = await self._counts(session, character.id)
            quantity = await session.scalar(
                select(ConsumableStack.quantity).where(
                    ConsumableStack.character_id == character.id,
                    ConsumableStack.consumable_id == item_id,
                )
            )
            entry = consumable_inventory_entry(item_id, int(quantity or 0))
            vigor_usable = False
            if item.family == ConsumableFamily.VIGOR:
                active = await session.scalar(
                    select(GameActivity.id).where(
                        GameActivity.character_id == character.id,
                        GameActivity.status == "active",
                    )
                )
                vigor_usable = bool(
                    entry.quantity > 0
                    and character.vigor <= VIGOR_USABLE_AT_OR_BELOW
                    and character.vigor_consumable_cycle
                    != daily_consumable_cycle(utcnow())
                    and active is None
                )
            return InventoryView(
                kind="inventory_consumable_detail",
                character_id=character.id,
                used_slots=sum(counts.values()),
                consumable_slots=counts["consumables"],
                category="consumables",
                entries=(entry,),
                vigor=character.vigor,
                max_vigor=character.max_vigor,
                vigor_usable=vigor_usable,
            )

    async def pending(self, actor: int) -> InventoryView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            counts = await self._counts(session, character.id)
            rows = (
                await session.scalars(
                    select(PendingItem)
                    .where(PendingItem.character_id == character.id)
                    .order_by(PendingItem.source_key, PendingItem.id)
                )
            ).all()
            blocked = await session.scalar(
                select(func.count(BlockedDelivery.id)).where(
                    BlockedDelivery.character_id == character.id,
                    BlockedDelivery.status == "pending",
                )
            ) or 0
            entries = tuple(self._pending_entry(row) for row in rows)
            return InventoryView(
                kind="pending_root",
                character_id=character.id,
                used_slots=sum(counts.values()),
                equipment_slots=counts["equipment"],
                consumable_slots=counts["consumables"],
                material_slots=counts["materials"],
                rune_slots=counts["runes"],
                entries=entries,
                pending_count=len(rows),
                blocked_delivery_count=int(blocked),
            )

    async def _character(self, session: AsyncSession, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _counts(self, session: AsyncSession, character_id: UUID) -> dict[str, int]:
        equipment = await session.scalar(
            select(func.count(EquipmentItem.id)).where(
                EquipmentItem.character_id == character_id
            )
        ) or 0
        consumables = await session.scalar(
            select(func.count(ConsumableStack.id)).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.quantity > 0,
            )
        ) or 0
        materials = await session.scalar(
            select(func.count(MaterialStack.id)).where(
                MaterialStack.character_id == character_id,
                MaterialStack.quantity > 0,
            )
        ) or 0
        runes = await session.scalar(
            select(func.count(RuneStack.id)).where(
                RuneStack.character_id == character_id,
                RuneStack.quantity > 0,
            )
        ) or 0
        return {
            "equipment": int(equipment),
            "consumables": int(consumables),
            "materials": int(materials),
            "runes": int(runes),
        }

    async def _entries(
        self,
        session: AsyncSession,
        character_id: UUID,
        category: str,
    ) -> list[InventoryEntry]:
        if category == "equipment":
            rows = (
                await session.scalars(
                    select(EquipmentItem)
                    .where(EquipmentItem.character_id == character_id)
                    .order_by(EquipmentItem.item_name, EquipmentItem.id)
                )
            ).all()
            equipped_slots = {
                equipment_item_id: slot
                for slot, equipment_item_id in (
                    await session.execute(
                        select(
                            CharacterEquipmentSlot.slot,
                            CharacterEquipmentSlot.equipment_item_id,
                        ).where(CharacterEquipmentSlot.character_id == character_id)
                    )
                ).all()
            }
            return [
                InventoryEntry(
                    kind="equipment",
                    key=str(row.id),
                    title=row.item_name,
                    rarity=row.rarity,
                    slot=row.slot,
                    item_level=row.item_level,
                    bound=row.bound,
                    payload=dict(row.payload or {}),
                    equipped_slot=equipped_slots.get(row.id),
                )
                for row in rows
            ]
        if category == "consumables":
            rows = (
                await session.scalars(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character_id,
                        ConsumableStack.quantity > 0,
                    )
                    .order_by(ConsumableStack.consumable_id)
                )
            ).all()
            return [consumable_inventory_entry(row.consumable_id, row.quantity) for row in rows]
        if category == "materials":
            rows = (
                await session.scalars(
                    select(MaterialStack)
                    .where(
                        MaterialStack.character_id == character_id,
                        MaterialStack.quantity > 0,
                    )
                    .order_by(MaterialStack.material_id, MaterialStack.bound, MaterialStack.id)
                )
            ).all()
            return [
                InventoryEntry(
                    kind="material",
                    key=row.material_id,
                    title=MATERIAL_LABELS.get(row.material_id, row.material_id),
                    quantity=row.quantity,
                    bound=row.bound,
                )
                for row in rows
            ]
        rows = (
            await session.scalars(
                select(RuneStack)
                .where(
                    RuneStack.character_id == character_id,
                    RuneStack.quantity > 0,
                )
                .order_by(
                    RuneStack.family,
                    RuneStack.rarity,
                    RuneStack.grade,
                    RuneStack.bound,
                    RuneStack.id,
                )
            )
        ).all()
        return [
            InventoryEntry(
                kind="rune",
                key=str(row.id),
                title=f"Runa de {row.family}",
                quantity=row.quantity,
                rarity=row.rarity,
                grade=row.grade,
                bound=row.bound,
            )
            for row in rows
        ]

    def _pending_entry(self, row: PendingItem) -> InventoryEntry:
        payload = dict(row.payload or {})
        if row.kind == "equipment":
            return InventoryEntry(
                kind="equipment",
                key=str(row.id),
                title=payload.get("item_name", "Equipamento"),
                quantity=row.quantity,
                rarity=payload.get("rarity"),
                slot=payload.get("slot"),
                item_level=payload.get("item_level"),
                bound=bool(payload.get("bound", False)),
                payload=payload,
            )
        if row.kind == "rune":
            family = payload.get("family", "Desconhecida")
            return InventoryEntry(
                kind="rune",
                key=str(row.id),
                title=f"Runa de {family}",
                quantity=row.quantity,
                rarity=payload.get("rarity"),
                grade=payload.get("grade", 1),
                bound=bool(payload.get("bound", False)),
                payload=payload,
            )
        if row.kind == "material":
            material_id = payload.get("material_id", "material")
            return InventoryEntry(
                kind="material",
                key=str(row.id),
                title=MATERIAL_LABELS.get(material_id, material_id),
                quantity=row.quantity,
                bound=bool(payload.get("bound", False)),
                payload=payload,
            )
        if row.kind == "consumable":
            consumable_id = payload.get("consumable_id", "")
            definition = consumable_definition(consumable_id)
            return InventoryEntry(
                kind="consumable",
                key=str(row.id),
                title=definition.name if definition is not None else "Consumível",
                quantity=row.quantity,
                grade=definition.grade if definition is not None else None,
                bound=bool(payload.get("bound", False)),
                payload=payload,
            )
        return InventoryEntry(
            kind=row.kind,
            key=str(row.id),
            title="Entrega Pendente",
            quantity=row.quantity,
            payload=payload,
        )
