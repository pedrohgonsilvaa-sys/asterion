"""Authoritative equip and unequip operations for existing EquipmentItems."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment_configuration import (
    build_equipment_configuration,
    hp_after_equipment_change,
    reconcile_character_hp,
    resolve_character_combat_stats,
)
from asterion.domain.equipment import (
    EquipmentSlot,
    assign_equipment_instance_id,
    assignment_for_item_slot,
    parse_equipment_slot,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    EquipmentItem,
)


class EquipmentMutationStatus(StrEnum):
    CHANGED = "changed"
    ALREADY_EQUIPPED = "already_equipped"
    ALREADY_EMPTY = "already_empty"
    BLOCKED_BY_TWO_HANDED = "blocked_by_two_handed"


class EquipmentMutationCode(StrEnum):
    ITEM_UNAVAILABLE = "item_unavailable"
    INVALID_ITEM = "invalid_item"
    INVALID_SLOT = "invalid_slot"
    ITEM_LEVEL_REQUIRED = "item_level_required"
    SECONDARY_BLOCKED_BY_TWO_HANDED = "secondary_blocked_by_two_handed"
    ITEM_EQUIPPED_IN_OTHER_SLOT = "item_equipped_in_other_slot"
    MYTHIC_LIMIT = "mythic_limit"
    STALE_CONFIGURATION = "stale_configuration"
    INVALID_CURRENT_CONFIGURATION = "invalid_current_configuration"


class EquipmentMutationRejected(RuntimeError):
    """Typed rejection for an invalid or stale equipment mutation."""

    def __init__(self, code: EquipmentMutationCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class EquipmentMutationResult:
    status: EquipmentMutationStatus
    slot: EquipmentSlot
    item_instance_id: UUID | None
    combat_configuration_version: int

    @property
    def changed(self) -> bool:
        return self.status == EquipmentMutationStatus.CHANGED


class EquipmentService:
    """Serialize equipment mutations through Character and the shared guard."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def equip_item(
        self,
        actor: int,
        item_instance_id: UUID,
        *,
        expected_configuration_version: int | None = None,
    ) -> EquipmentMutationResult | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            item = await session.scalar(
                select(EquipmentItem)
                .where(
                    EquipmentItem.id == item_instance_id,
                    EquipmentItem.character_id == character.id,
                )
                .with_for_update()
            )
            if item is None:
                raise EquipmentMutationRejected(EquipmentMutationCode.ITEM_UNAVAILABLE)

            assignment = assignment_for_item_slot(item.slot)
            if assignment is None:
                raise EquipmentMutationRejected(EquipmentMutationCode.INVALID_ITEM)
            payload_slot = (item.payload or {}).get("slot")
            if payload_slot is not None:
                payload_assignment = assignment_for_item_slot(str(payload_slot))
                if payload_assignment != assignment:
                    raise EquipmentMutationRejected(EquipmentMutationCode.INVALID_ITEM)
            if item.item_level < 1 or item.item_level > 60:
                raise EquipmentMutationRejected(EquipmentMutationCode.INVALID_ITEM)
            if character.level < item.item_level:
                raise EquipmentMutationRejected(EquipmentMutationCode.ITEM_LEVEL_REQUIRED)

            rows, current, equipped_items = await self._load_equipped(session, character.id)
            assignment_by_id = {
                equipped_id: assignment_for_item_slot(equipped_item.slot)
                for equipped_id, equipped_item in equipped_items.items()
            }
            current_item_slot = next(
                (
                    slot
                    for slot, equipped_id in current.items()
                    if equipped_id == item.id
                ),
                None,
            )
            if current_item_slot is not None:
                if current_item_slot == assignment.slot:
                    return EquipmentMutationResult(
                        EquipmentMutationStatus.ALREADY_EQUIPPED,
                        assignment.slot,
                        item.id,
                        character.combat_configuration_version,
                    )
                raise EquipmentMutationRejected(
                    EquipmentMutationCode.ITEM_EQUIPPED_IN_OTHER_SLOT
                )

            if (
                assignment.slot == EquipmentSlot.SECUNDARIA
                and (main_assignment := assignment_by_id.get(current.get(EquipmentSlot.PRINCIPAL)))
                is not None
                and main_assignment.two_handed
            ):
                raise EquipmentMutationRejected(
                    EquipmentMutationCode.SECONDARY_BLOCKED_BY_TWO_HANDED
                )

            final = dict(current)
            final[assignment.slot] = item.id
            if assignment.two_handed:
                final.pop(EquipmentSlot.SECUNDARIA, None)

            final_items = dict(equipped_items)
            final_items[item.id] = item
            if sum(1 for equipped_id in final.values() if _is_mythic(final_items[equipped_id])) > 1:
                raise EquipmentMutationRejected(EquipmentMutationCode.MYTHIC_LIMIT)

            if final == current:
                return EquipmentMutationResult(
                    EquipmentMutationStatus.ALREADY_EQUIPPED,
                    assignment.slot,
                    item.id,
                    character.combat_configuration_version,
                )

            try:
                current_configuration = build_equipment_configuration(
                    character,
                    [(slot, equipped_items[item_id]) for slot, item_id in current.items()],
                    version=character.combat_configuration_version,
                )
                reconcile_character_hp(character, current_configuration)
                configuration = build_equipment_configuration(
                    character,
                    [(slot, final_items[item_id]) for slot, item_id in final.items()],
                    version=character.combat_configuration_version + 1,
                )
                new_stats = resolve_character_combat_stats(character, configuration)
                new_hp = hp_after_equipment_change(character, new_stats.hp)
            except ValueError as exc:
                raise EquipmentMutationRejected(
                    EquipmentMutationCode.INVALID_CURRENT_CONFIGURATION
                ) from exc
            await self._write_equipped(session, character.id, rows, current, final)
            character.combat_configuration_version += 1
            character.max_hp = new_stats.hp
            character.hp = new_hp
            await session.flush()
            return EquipmentMutationResult(
                EquipmentMutationStatus.CHANGED,
                assignment.slot,
                item.id,
                character.combat_configuration_version,
            )

    async def unequip_slot(
        self,
        actor: int,
        slot: EquipmentSlot | str,
        *,
        expected_configuration_version: int | None = None,
    ) -> EquipmentMutationResult | None:
        target = parse_equipment_slot(slot)
        if target is None:
            raise EquipmentMutationRejected(EquipmentMutationCode.INVALID_SLOT)

        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            rows, current, equipped_items = await self._load_equipped(session, character.id)
            item_id = current.get(target)
            if item_id is None:
                main_id = current.get(EquipmentSlot.PRINCIPAL)
                main = equipped_items.get(main_id)
                main_assignment = (
                    assignment_for_item_slot(main.slot) if main is not None else None
                )
                status = (
                    EquipmentMutationStatus.BLOCKED_BY_TWO_HANDED
                    if target == EquipmentSlot.SECUNDARIA
                    and main_assignment is not None
                    and main_assignment.two_handed
                    else EquipmentMutationStatus.ALREADY_EMPTY
                )
                return EquipmentMutationResult(
                    status,
                    target,
                    None,
                    character.combat_configuration_version,
                )

            final = dict(current)
            del final[target]
            try:
                current_configuration = build_equipment_configuration(
                    character,
                    [(slot, equipped_items[item_id]) for slot, item_id in current.items()],
                    version=character.combat_configuration_version,
                )
                reconcile_character_hp(character, current_configuration)
                configuration = build_equipment_configuration(
                    character,
                    [(slot, equipped_items[item_id]) for slot, item_id in final.items()],
                    version=character.combat_configuration_version + 1,
                )
                new_stats = resolve_character_combat_stats(character, configuration)
                new_hp = hp_after_equipment_change(character, new_stats.hp)
            except ValueError as exc:
                raise EquipmentMutationRejected(
                    EquipmentMutationCode.INVALID_CURRENT_CONFIGURATION
                ) from exc
            await self._write_equipped(session, character.id, rows, current, final)
            character.combat_configuration_version += 1
            character.max_hp = new_stats.hp
            character.hp = new_hp
            await session.flush()
            return EquipmentMutationResult(
                EquipmentMutationStatus.CHANGED,
                target,
                None,
                character.combat_configuration_version,
            )

    async def _lock_character(self, session: AsyncSession, actor: int) -> Character | None:
        character_id = await session.scalar(
            select(Character.id).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )
        if character_id is None:
            return None
        return await lock_for_combat_configuration_mutation(session, character_id)

    @staticmethod
    def _check_version(
        character: Character, expected_configuration_version: int | None
    ) -> None:
        if (
            expected_configuration_version is not None
            and expected_configuration_version != character.combat_configuration_version
        ):
            raise EquipmentMutationRejected(EquipmentMutationCode.STALE_CONFIGURATION)

    async def _load_equipped(
        self, session: AsyncSession, character_id: UUID
    ) -> tuple[
        list[CharacterEquipmentSlot],
        dict[EquipmentSlot, UUID],
        dict[UUID, EquipmentItem],
    ]:
        rows = list(
            (
                await session.scalars(
                    select(CharacterEquipmentSlot)
                    .where(CharacterEquipmentSlot.character_id == character_id)
                    .order_by(CharacterEquipmentSlot.slot)
                    .with_for_update()
                )
            ).all()
        )
        current: dict[EquipmentSlot, UUID] = {}
        for row in rows:
            slot = parse_equipment_slot(row.slot)
            if slot is None or slot in current:
                raise EquipmentMutationRejected(
                    EquipmentMutationCode.INVALID_CURRENT_CONFIGURATION
                )
            current[slot] = row.equipment_item_id

        item_ids = tuple(sorted(set(current.values()), key=str))
        if not item_ids:
            return rows, current, {}
        items = (
            await session.scalars(
                select(EquipmentItem)
                .where(
                    EquipmentItem.id.in_(item_ids),
                    EquipmentItem.character_id == character_id,
                )
                .order_by(EquipmentItem.id)
                .with_for_update()
            )
        ).all()
        equipped_items = {item.id: item for item in items}
        if len(equipped_items) != len(item_ids):
            raise EquipmentMutationRejected(
                EquipmentMutationCode.INVALID_CURRENT_CONFIGURATION
            )
        for slot, item_id in current.items():
            assignment = assignment_for_item_slot(equipped_items[item_id].slot)
            if assignment is None or assignment.slot != slot:
                raise EquipmentMutationRejected(
                    EquipmentMutationCode.INVALID_CURRENT_CONFIGURATION
                )
        main_id = current.get(EquipmentSlot.PRINCIPAL)
        main = equipped_items.get(main_id)
        main_assignment = assignment_for_item_slot(main.slot) if main is not None else None
        if main_assignment is not None and main_assignment.two_handed:
            if EquipmentSlot.SECUNDARIA in current:
                raise EquipmentMutationRejected(
                    EquipmentMutationCode.INVALID_CURRENT_CONFIGURATION
                )
        return rows, current, equipped_items

    @staticmethod
    async def _write_equipped(
        session: AsyncSession,
        character_id: UUID,
        rows: list[CharacterEquipmentSlot],
        current: dict[EquipmentSlot, UUID],
        final: dict[EquipmentSlot, UUID],
    ) -> None:
        row_by_slot = {parse_equipment_slot(row.slot): row for row in rows}
        for slot, row in row_by_slot.items():
            if final.get(slot) != row.equipment_item_id:
                await session.delete(row)
        await session.flush()
        for slot, item_id in final.items():
            if current.get(slot) != item_id:
                session.add(
                    CharacterEquipmentSlot(
                        character_id=character_id,
                        slot=slot.value,
                        equipment_item_id=item_id,
                    )
                )


def _is_mythic(item: EquipmentItem) -> bool:
    return item.rarity.casefold() in {"mítico", "mythic"}


def equipment_instance_payload(
    payload: dict, *, instance_id: UUID | None = None
) -> tuple[UUID, dict]:
    """Prepare persisted payload using the EquipmentItem primary key as identity."""
    return assign_equipment_instance_id(payload, instance_id=instance_id)
