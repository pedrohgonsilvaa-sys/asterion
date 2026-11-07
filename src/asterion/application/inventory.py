"""Read-only Inventory and Pending views used by Telegram system navigation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.consumables import daily_consumable_cycle
from asterion.application.inventory_capacity import (
    INVENTORY_CAPACITY,
    PENDING_CAPACITY,
    inventory_slot_counts,
)
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

REGIONAL_RUNE_TITLES = {
    "Meridiano": "Runa do Meridiano",
    "Prumo": "Runa do Prumo",
    "Horizonte": "Runa do Horizonte",
    "Marco": "Runa do Marco",
    "Distância": "Runa da Distância",
    "Abrigo": "Runa do Abrigo",
    "Desvio": "Runa do Desvio",
    "Referência": "Runa da Referência",
    "Dique": "Runa do Dique",
    "Contenção": "Runa da Contenção",
    "Junco": "Runa do Junco",
    "Triagem": "Runa da Triagem",
    "Emergência": "Runa da Emergência",
    "Restituição": "Runa da Restituição",
    "Margem": "Runa da Margem",
    "Válvula": "Runa da Válvula",
}

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
    "material.vde.nucleo_no_antigo": "Núcleo do Nó Antigo",
    "material.nareth.bronze_de_marco": "Bronze de Marco",
    "material.nareth.couro_de_horizonte": "Couro de Horizonte",
    "material.nareth.erva_de_vento": "Erva de Vento",
    "material.nareth.po_de_eixo": "Pó de Eixo",
    "material.nareth.catalisador_elite_iii": "Catalisador de Elite III",
    "material.nareth.fragmento_aprimoramento_iii": "Fragmento de Aprimoramento III",
    "material.varzeas.ferro_de_salmoura": "Ferro de Salmoura",
    "material.varzeas.couro_de_varzea": "Couro de Várzea",
    "material.varzeas.junco_ferruginoso": "Junco Ferruginoso",
    "material.varzeas.soro_antigo": "Soro Antigo",
    "material.varzeas.catalisador_elite_iv": "Catalisador de Elite IV",
    "material.varzeas.fragmento_aprimoramento_iv": "Fragmento de Aprimoramento IV",
    "material.varzeas.nucleo_enfermaria_afundada": "Núcleo da Enfermaria Afundada",
    "material.varzeas.nucleo_cisterna_transferencia": "Núcleo da Cisterna de Transferência",
    "material.varzeas.nucleo_matriz_rubra": "Núcleo da Matriz Rubra",
    "material.altos.ferro_contrapeso": "Ferro de Contrapeso",
    "material.altos.couro_escarpa": "Couro de Escarpa",
    "material.altos.liquen_pedreira": "Líquen de Pedreira",
    "material.altos.cinza_basalto": "Cinza de Basalto",
    "material.special.altos.core.colosso_cinereo": "Núcleo do Colosso Cinéreo",
    "material.special.altos.core.pedreira_contrapeso": "Núcleo da Pedreira do Contrapeso",
    "material.tdo.catalisador_elite_v": "Catalisador de Elite V",
    "material.tdo.catalisador_elite_vi": "Catalisador de Elite VI",
    "material.tdo.fragmento_aprimoramento_v": "Fragmento de Aprimoramento V",
    "material.tdo.fragmento_aprimoramento_vi": "Fragmento de Aprimoramento VI",
    "material.confins.ferro_baliza": "Ferro de Baliza",
    "material.confins.couro_marcha": "Couro de Marcha",
    "material.confins.musgo_limiar": "Musgo de Limiar",
    "material.confins.po_referencia": "Pó de Referência",
    "material.special.confins.core.arquivo_retorno": "Núcleo do Arquivo do Retorno",
    "material.special.confins.core.camara_contradicoes": "Núcleo da Câmara das Contradições",
    "material.nareth.nucleo_arconte_invertido": "Núcleo do Arconte Invertido",
    "material.nareth.nucleo_galerias_meridiano": "Núcleo das Galerias do Meridiano",
    "material.nareth.nucleo_observatorio_afundado": "Núcleo do Observatório Afundado",
    "material.special.altos.core.bastilha_profunda": "Núcleo da Bastilha Profunda",
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


# GDD 23.2 names five delivery origins. Market and Service have no delivery yet;
# when they do, their source keys must start with these prefixes.
ORIGIN_PREFIXES = (
    (("activity:", "explore:", "dungeon:", "dungeon."), "Loot"),
    (("market:",), "Mercado"),
    (("craft:",), "Crafting"),
    (("service:",), "Serviço"),
)


def origin_label(source_key: str) -> str:
    """Translate an internal delivery source into the category shown to the player."""

    for prefixes, label in ORIGIN_PREFIXES:
        if source_key.startswith(prefixes):
            return label
    return "Recompensa"


def consumable_inventory_entry(
    item_id: str, quantity: int, source_id: UUID | None = None
) -> InventoryEntry:
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
                **({"warehouse_source_id": str(source_id)} if source_id else {}),
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
            pending = int(
                await session.scalar(
                    select(func.count(PendingItem.id)).where(
                        PendingItem.character_id == character.id
                    )
                )
                or 0
            )
            blocked = int(
                await session.scalar(
                    select(func.count(BlockedDelivery.id)).where(
                        BlockedDelivery.character_id == character.id,
                        BlockedDelivery.status == "pending",
                    )
                )
                or 0
            )
            return InventoryView(
                kind="inventory_root",
                character_id=character.id,
                used_slots=sum(counts.values()),
                equipment_slots=counts["equipment"],
                consumable_slots=counts["consumables"],
                material_slots=counts["materials"],
                rune_slots=counts["runes"],
                pending_count=pending,
                blocked_delivery_count=blocked,
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
            blocked_rows = (
                await session.scalars(
                    select(BlockedDelivery)
                    .where(
                    BlockedDelivery.character_id == character.id,
                    BlockedDelivery.status == "pending",
                    )
                    .order_by(BlockedDelivery.created_at, BlockedDelivery.id)
                )
            ).all()
            blocked = len(blocked_rows)
            entries = tuple(self.pending_entry(row) for row in rows) + tuple(
                self._blocked_entry(row) for row in blocked_rows
            )
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
        return await inventory_slot_counts(session, character_id)

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
                    payload={**dict(row.payload or {}), "warehouse_source_id": str(row.id)},
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
            return [
                consumable_inventory_entry(row.consumable_id, row.quantity, row.id)
                for row in rows
            ]
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
                    payload={"warehouse_source_id": str(row.id)},
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
                title=REGIONAL_RUNE_TITLES.get(row.family, f"Runa de {row.family}"),
                quantity=row.quantity,
                rarity=row.rarity,
                grade=row.grade,
                bound=row.bound,
                payload={"warehouse_source_id": str(row.id)},
            )
            for row in rows
        ]

    @staticmethod
    def pending_entry(row: PendingItem | BlockedDelivery) -> InventoryEntry:
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
                payload={**payload, "origin": row.source_key},
            )
        if row.kind == "rune":
            family = payload.get("family", "Desconhecida")
            return InventoryEntry(
                kind="rune",
                key=str(row.id),
                title=REGIONAL_RUNE_TITLES.get(family, f"Runa de {family}"),
                quantity=row.quantity,
                rarity=payload.get("rarity"),
                grade=payload.get("grade", 1),
                bound=bool(payload.get("bound", False)),
                payload={**payload, "origin": row.source_key},
            )
        if row.kind == "material":
            material_id = payload.get("material_id", "material")
            return InventoryEntry(
                kind="material",
                key=str(row.id),
                title=MATERIAL_LABELS.get(material_id, material_id),
                quantity=row.quantity,
                bound=bool(payload.get("bound", False)),
                payload={**payload, "origin": row.source_key},
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
                payload={**payload, "origin": row.source_key},
            )
        return InventoryEntry(
            kind=row.kind,
            key=str(row.id),
            title="Entrega Pendente",
            quantity=row.quantity,
            payload={**payload, "origin": row.source_key},
        )

    @staticmethod
    def _blocked_entry(row: BlockedDelivery) -> InventoryEntry:
        payload = dict(row.payload or {})
        return InventoryEntry(
            kind="blocked_delivery",
            key=str(row.id),
            title=InventoryService.pending_entry(row).title,
            quantity=row.quantity,
            rarity=payload.get("rarity"),
            slot=payload.get("slot"),
            item_level=payload.get("item_level"),
            grade=payload.get("grade"),
            bound=bool(payload.get("bound", False)),
            payload={
                **payload,
                "origin": row.source_key,
                "delivery_kind": row.kind,
                "blocked": True,
            },
        )
