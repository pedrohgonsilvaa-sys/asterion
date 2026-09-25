"""Read-only equipment views for the Telegram character and inventory screens."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.domain.equipment import (
    EquipmentSlot,
    assignment_for_item_slot,
    parse_equipment_slot,
)
from asterion.domain.equipment_stats import (
    EquipmentConfigurationError,
    EquipmentStatContribution,
    equipment_stat_contribution,
    item_snapshot_from_persisted,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    EquipmentItem,
)

RARITY_LABELS = {
    "comum": "Comum",
    "common": "Comum",
    "raro": "Raro",
    "rare": "Raro",
    "épico": "Épico",
    "epic": "Épico",
    "lendário": "Lendário",
    "legendary": "Lendário",
    "mítico": "Mítico",
    "mythic": "Mítico",
}


class EquipmentViewUnavailable(ValueError):
    """Stored equipment is missing, malformed, or not owned by the character."""


@dataclass(frozen=True, slots=True)
class EquipmentItemView:
    item_instance_id: UUID
    name: str
    rarity: str
    item_slot: str
    slot: EquipmentSlot
    item_level: int
    enhancement: int
    bound: bool
    contribution: EquipmentStatContribution
    equipped_slot: EquipmentSlot | None = None
    lore: str | None = None
    eligible: bool = True

    @property
    def equipped(self) -> bool:
        return self.equipped_slot is not None

    @property
    def two_handed(self) -> bool:
        assignment = assignment_for_item_slot(self.item_slot)
        return bool(assignment and assignment.two_handed)


@dataclass(frozen=True, slots=True)
class EquipmentSlotView:
    slot: EquipmentSlot
    item: EquipmentItemView | None = None
    blocked_by_two_handed: bool = False


@dataclass(frozen=True, slots=True)
class EquipmentRootView:
    character_id: UUID
    character_level: int
    combat_configuration_version: int
    slots: tuple[EquipmentSlotView, ...]


@dataclass(frozen=True, slots=True)
class EquipmentDetailView:
    character_id: UUID
    character_level: int
    combat_configuration_version: int
    item: EquipmentItemView


@dataclass(frozen=True, slots=True)
class EquipmentCandidatesView:
    character_id: UUID
    character_level: int
    combat_configuration_version: int
    slot: EquipmentSlot
    candidates: tuple[EquipmentItemView, ...]
    blocked_by_two_handed: bool = False


class EquipmentViewService:
    """Read-only Equipment UI model, scoped by Telegram actor and server."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def root(self, actor: int) -> EquipmentRootView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            slots = await self._equipped_state(session, character)
            by_slot = {
                slot: self._item_view(row, slot, character.level)
                for slot, row in slots.items()
            }
            main = by_slot.get(EquipmentSlot.PRINCIPAL)
            blocked = bool(main and main.two_handed)
            slot_views = tuple(
                EquipmentSlotView(
                    slot=slot,
                    item=by_slot.get(slot),
                    blocked_by_two_handed=(slot == EquipmentSlot.SECUNDARIA and blocked),
                )
                for slot in EquipmentSlot
            )
            self._validate_configuration(by_slot)
            return EquipmentRootView(
                character.id,
                character.level,
                character.combat_configuration_version,
                slot_views,
            )

    async def detail(self, actor: int, item_instance_id: UUID) -> EquipmentDetailView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            item = await session.scalar(
                select(EquipmentItem).where(
                    EquipmentItem.id == item_instance_id,
                    EquipmentItem.character_id == character.id,
                )
            )
            if item is None:
                return None
            slot_rows = (
                await session.execute(
                    select(
                        CharacterEquipmentSlot.slot,
                        CharacterEquipmentSlot.equipment_item_id,
                    ).where(
                        CharacterEquipmentSlot.character_id == character.id,
                        CharacterEquipmentSlot.equipment_item_id == item.id,
                    )
                )
            ).all()
            if len(slot_rows) > 1:
                raise EquipmentViewUnavailable("Equipment item occupies multiple slots.")
            equipped_slot = (
                parse_equipment_slot(slot_rows[0].slot) if slot_rows else None
            )
            if slot_rows and equipped_slot is None:
                raise EquipmentViewUnavailable("Invalid persisted equipment slot.")
            view = self._item_view(item, equipped_slot, character.level)
            return EquipmentDetailView(
                character.id,
                character.level,
                character.combat_configuration_version,
                view,
            )

    async def candidates(
        self, actor: int, slot: EquipmentSlot | str
    ) -> EquipmentCandidatesView | None:
        target = parse_equipment_slot(slot)
        if target is None:
            return None
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            equipped = await self._equipped_state(session, character)
            main = equipped.get(EquipmentSlot.PRINCIPAL)
            secondary_blocked = bool(main and assignment_for_item_slot(main.slot).two_handed)
            if target == EquipmentSlot.SECUNDARIA and secondary_blocked:
                return EquipmentCandidatesView(
                    character.id,
                    character.level,
                    character.combat_configuration_version,
                    target,
                    (),
                    blocked_by_two_handed=True,
                )

            equipped_by_slot = {
                slot: self._item_view(row, slot, character.level)
                for slot, row in equipped.items()
            }
            current_ids = {view.item_instance_id for view in equipped_by_slot.values()}
            rows = (
                await session.scalars(
                    select(EquipmentItem)
                    .where(EquipmentItem.character_id == character.id)
                    .order_by(EquipmentItem.item_name, EquipmentItem.id)
                )
            ).all()
            candidates: list[EquipmentItemView] = []
            for row in rows:
                if row.id in current_ids:
                    continue
                assignment = assignment_for_item_slot(row.slot)
                if assignment is None or assignment.slot != target:
                    continue
                if row.item_level > character.level:
                    continue
                try:
                    item_view = self._item_view(row, None, character.level)
                except EquipmentViewUnavailable:
                    # Malformed legacy rows are not offered as valid actions. The
                    # authoritative EquipmentService still validates every commit.
                    continue
                final = dict(equipped_by_slot)
                final[target] = item_view
                if item_view.two_handed:
                    final.pop(EquipmentSlot.SECUNDARIA, None)
                if sum(candidate.rarity == "Mítico" for candidate in final.values()) > 1:
                    continue
                candidates.append(item_view)

            return EquipmentCandidatesView(
                character.id,
                character.level,
                character.combat_configuration_version,
                target,
                tuple(candidates),
            )

    async def _character(self, session: AsyncSession, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _equipped_state(
        self, session: AsyncSession, character: Character
    ) -> dict[EquipmentSlot, EquipmentItem]:
        slot_rows = (
            await session.scalars(
                select(CharacterEquipmentSlot)
                .where(CharacterEquipmentSlot.character_id == character.id)
                .order_by(CharacterEquipmentSlot.slot)
            )
        ).all()
        equipment_slots: dict[EquipmentSlot, UUID] = {}
        for row in slot_rows:
            slot = parse_equipment_slot(row.slot)
            if slot is None or slot in equipment_slots:
                raise EquipmentViewUnavailable("Invalid persisted equipment slots.")
            equipment_slots[slot] = row.equipment_item_id
        item_ids = tuple(equipment_slots.values())
        if not item_ids:
            return {}
        rows = (
            await session.scalars(
                select(EquipmentItem)
                .where(
                    EquipmentItem.id.in_(item_ids),
                    EquipmentItem.character_id == character.id,
                )
                .order_by(EquipmentItem.id)
            )
        ).all()
        by_id = {item.id: item for item in rows}
        if len(by_id) != len(item_ids):
            raise EquipmentViewUnavailable("Equipped item is missing or not owned.")
        by_slot: dict[EquipmentSlot, EquipmentItem] = {}
        for slot, item_id in equipment_slots.items():
            item = by_id[item_id]
            assignment = assignment_for_item_slot(item.slot)
            if assignment is None or assignment.slot != slot:
                raise EquipmentViewUnavailable("Item slot does not match equipped slot.")
            by_slot[slot] = item
        return by_slot

    def _item_view(
        self,
        item: EquipmentItem,
        equipped_slot: EquipmentSlot | None,
        character_level: int,
    ) -> EquipmentItemView:
        assignment = assignment_for_item_slot(item.slot)
        if assignment is None:
            raise EquipmentViewUnavailable("Unknown equipment slot.")
        rarity = _localized_rarity(item.rarity)
        try:
            snapshot = item_snapshot_from_persisted(
                item_instance_id=str(item.id),
                equipped_slot=(equipped_slot or assignment.slot).value,
                item_slot=item.slot,
                item_level=item.item_level,
                rarity=rarity,
                payload=item.payload or {},
            )
            contribution = equipment_stat_contribution(snapshot)
        except EquipmentConfigurationError as exc:
            raise EquipmentViewUnavailable("Stored equipment cannot be displayed safely.") from exc
        raw_lore = (item.payload or {}).get("lore")
        lore = raw_lore.strip() if isinstance(raw_lore, str) and raw_lore.strip() else None
        return EquipmentItemView(
            item_instance_id=item.id,
            name=item.item_name,
            rarity=rarity,
            item_slot=item.slot,
            slot=assignment.slot,
            item_level=item.item_level,
            enhancement=snapshot.enhancement,
            bound=item.bound,
            contribution=contribution,
            equipped_slot=equipped_slot,
            lore=lore,
            eligible=character_level >= item.item_level,
        )

    def _validate_configuration(self, items: dict[EquipmentSlot, EquipmentItemView]) -> None:
        mythic_count = sum(item.rarity == "Mítico" for item in items.values())
        main = items.get(EquipmentSlot.PRINCIPAL)
        if mythic_count > 1 or (
            main is not None
            and main.two_handed
            and EquipmentSlot.SECUNDARIA in items
        ):
            raise EquipmentViewUnavailable("Invalid equipped configuration.")


def _localized_rarity(value: str) -> str:
    label = RARITY_LABELS.get(value.casefold())
    if label is None:
        raise EquipmentViewUnavailable("Unknown equipment rarity.")
    return label
