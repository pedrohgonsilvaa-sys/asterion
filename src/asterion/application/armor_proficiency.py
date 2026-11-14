"""Proficiências de Armadura: persistence, equip eligibility and the Treinador (Armaduras tab)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.weapon_proficiency import TRAINER_LOCATION
from asterion.domain.armor_proficiency import (
    ARMOR_TERMS,
    INITIAL_ARMOR_CLASS,
    ArmorTerms,
    parse_armor_class,
)
from asterion.domain.regional_equipment import ARMOR_CLASSES, armor_class_of
from asterion.infrastructure.db.models import (
    Character,
    CharacterArmorProficiency,
    EquipmentItem,
    WorldState,
)


async def owned_armor_classes(session: AsyncSession, character_id: UUID) -> frozenset[str]:
    rows = await session.scalars(
        select(CharacterArmorProficiency.armor_class).where(
            CharacterArmorProficiency.character_id == character_id
        )
    )
    return frozenset(rows.all()) | {INITIAL_ARMOR_CLASS}


def item_armor_class(item: EquipmentItem) -> str | None:
    payload = item.payload or {}
    return armor_class_of(
        slot=item.slot,
        template_id=payload.get("template_id"),
        item_name=payload.get("item_name"),
    )


async def armor_proficiency_missing(
    session: AsyncSession,
    character: Character,
    item: EquipmentItem,
    owned: frozenset[str] | None = None,
) -> str | None:
    """Return the armor class the character lacks for this item, else None."""
    armor_class = item_armor_class(item)
    if armor_class is None:
        return None
    if owned is None:
        owned = await owned_armor_classes(session, character.id)
    return None if armor_class in owned else armor_class


class ArmorTrainingRejected(StrEnum):
    UNKNOWN_CLASS = "unknown_class"
    LOCATION_REQUIRED = "location_required"
    LEVEL_REQUIRED = "level_required"
    NOT_ENOUGH_CROWNS = "not_enough_crowns"


@dataclass(frozen=True, slots=True)
class ArmorTrainerEntry:
    terms: ArmorTerms
    owned: bool


@dataclass(frozen=True, slots=True)
class ArmorTrainerView:
    level: int
    crowns: int
    at_trainer: bool
    entries: tuple[ArmorTrainerEntry, ...]


@dataclass(frozen=True, slots=True)
class ArmorTrainingOutcome:
    learned: bool
    already_owned: bool
    reason: ArmorTrainingRejected | None
    view: ArmorTrainerView


class ArmorTrainerService:
    """Atomic, idempotent purchase. The Character row is locked first, like equip."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> ArmorTrainerView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor, lock=False)
            if character is None:
                return None
            return await self._view(session, character)

    async def learn(self, actor: int, armor_class_value: str) -> ArmorTrainingOutcome | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            owned = await owned_armor_classes(session, character.id)
            armor_class = parse_armor_class(armor_class_value)
            reason: ArmorTrainingRejected | None = None
            if armor_class is None:
                reason = ArmorTrainingRejected.UNKNOWN_CLASS
            elif armor_class in owned:
                return ArmorTrainingOutcome(
                    False, True, None, await self._view(session, character)
                )
            elif await self._location(session, character.id) != TRAINER_LOCATION:
                reason = ArmorTrainingRejected.LOCATION_REQUIRED
            else:
                terms = ARMOR_TERMS[armor_class]
                if character.level < terms.min_level:
                    reason = ArmorTrainingRejected.LEVEL_REQUIRED
                elif character.crowns < terms.cost_crowns:
                    reason = ArmorTrainingRejected.NOT_ENOUGH_CROWNS
                else:
                    character.crowns -= terms.cost_crowns
                    session.add(
                        CharacterArmorProficiency(
                            character_id=character.id,
                            armor_class=armor_class,
                            cost_crowns=terms.cost_crowns,
                        )
                    )
                    await session.flush()
            return ArmorTrainingOutcome(
                reason is None, False, reason, await self._view(session, character)
            )

    async def _view(self, session: AsyncSession, character: Character) -> ArmorTrainerView:
        owned = await owned_armor_classes(session, character.id)
        location = await self._location(session, character.id)
        return ArmorTrainerView(
            level=character.level,
            crowns=character.crowns,
            at_trainer=location == TRAINER_LOCATION,
            entries=tuple(
                ArmorTrainerEntry(ARMOR_TERMS[name], name in owned) for name in ARMOR_CLASSES
            ),
        )

    @staticmethod
    async def _location(session: AsyncSession, character_id: UUID) -> str | None:
        return await session.scalar(
            select(WorldState.location).where(WorldState.character_id == character_id)
        )

    async def _character(
        self, session: AsyncSession, actor: int, *, lock: bool
    ) -> Character | None:
        statement = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)
