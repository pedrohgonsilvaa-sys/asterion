"""Marcas de Legado: earn slots through Ascensão, activate, and redistribute (§16.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account import _has_foreground
from asterion.application.inventory_capacity import (
    INVENTORY_CAPACITY,
    PENDING_CAPACITY,
    WAREHOUSE_CAPACITY,
    inventory_slots,
    warehouse_slots,
)
from asterion.application.legacy_mark_effects import BASE_DOCTRINES
from asterion.application.safe_location import current_permanent_brazier
from asterion.domain.legacy_marks import (
    LEGACY_MARKS,
    LEGACY_MARKS_BY_ID,
    RESPEC_COOLDOWN,
    RESPEC_COST_CROWNS,
    LegacyMark,
    LegacyMarkId,
    mark_slots,
)
from asterion.domain.market import LISTING_SLOTS
from asterion.infrastructure.db.models import (
    Character,
    CharacterDoctrine,
    CharacterLegacyMark,
    MarketListing,
    PendingItem,
    PlayerShop,
)


class LegacyMarkRejected(StrEnum):
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    ALREADY_ACTIVE = "already_active"
    NOT_ACTIVE = "not_active"
    NO_FREE_SLOT = "no_free_slot"
    SAFE_LOCATION_REQUIRED = "safe_location_required"
    ACTIVITY_LOCKED = "activity_locked"
    RESPEC_COOLDOWN = "respec_cooldown"
    NOT_ENOUGH_CROWNS = "not_enough_crowns"
    INVENTORY_IN_USE = "inventory_in_use"
    WAREHOUSE_IN_USE = "warehouse_in_use"
    PENDING_IN_USE = "pending_in_use"
    LISTINGS_IN_USE = "listings_in_use"
    DOCTRINES_IN_USE = "doctrines_in_use"


@dataclass(frozen=True, slots=True)
class LegacyMarkEntry:
    mark: LegacyMark
    active: bool


@dataclass(frozen=True, slots=True)
class LegacyMarksView:
    legacy_level: int
    slots: int
    active_count: int
    crowns: int
    location: str | None
    respec_available_at: datetime | None
    entries: tuple[LegacyMarkEntry, ...]

    @property
    def free_slots(self) -> int:
        return max(0, self.slots - self.active_count)


@dataclass(frozen=True, slots=True)
class LegacyMarkOutcome:
    succeeded: bool
    reason: LegacyMarkRejected | None
    view: LegacyMarksView


class LegacyMarksService:
    """Every write locks Character first, matching the Ascensão and capacity writers.

    Activating a Marca into a free slot is free. Removing one is the GDD respec:
    5.000 Coroas, a 7-day Recarga, a permanent Braseiro, no foreground activity,
    and never into a state where current use exceeds the capacity left behind.
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int, *, now: datetime | None = None) -> LegacyMarksView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor, lock=False)
            if character is None:
                return None
            return await self._view(session, character, now or datetime.now(UTC))

    async def activate(
        self, actor: int, mark_id: str, *, now: datetime | None = None
    ) -> LegacyMarkOutcome | None:
        now = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            reason = await self._activation_blocker(session, character, mark_id)
            if reason is None:
                session.add(
                    CharacterLegacyMark(
                        character_id=character.id, mark_id=mark_id, activated_at=now
                    )
                )
                await session.flush()
            view = await self._view(session, character, now)
            return LegacyMarkOutcome(reason is None, reason, view)

    async def remove(
        self, actor: int, mark_id: str, *, now: datetime | None = None
    ) -> LegacyMarkOutcome | None:
        now = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            reason = await self._removal_blocker(session, character, mark_id, now)
            if reason is None:
                row = await session.get(
                    CharacterLegacyMark, (character.id, mark_id), with_for_update=True
                )
                await session.delete(row)
                character.crowns -= RESPEC_COST_CROWNS
                character.legacy_mark_respec_at = now
                await session.flush()
            view = await self._view(session, character, now)
            return LegacyMarkOutcome(reason is None, reason, view)

    async def removal_blocker(
        self, actor: int, mark_id: str, *, now: datetime | None = None
    ) -> LegacyMarkRejected | None:
        """Read-only preview of `remove`, used by the confirmation screen."""
        async with self.sessions() as session:
            character = await self._character(session, actor, lock=False)
            if character is None:
                return LegacyMarkRejected.UNKNOWN
            return await self._removal_blocker(
                session, character, mark_id, now or datetime.now(UTC)
            )

    async def _activation_blocker(
        self, session: AsyncSession, character: Character, mark_id: str
    ) -> LegacyMarkRejected | None:
        mark = _known_mark(mark_id)
        if mark is None:
            return LegacyMarkRejected.UNKNOWN
        if not mark.available:
            return LegacyMarkRejected.UNAVAILABLE
        active = await self._active_ids(session, character.id)
        if mark.id in active:
            return LegacyMarkRejected.ALREADY_ACTIVE
        if len(active) >= mark_slots(character.legacy_level):
            return LegacyMarkRejected.NO_FREE_SLOT
        return None

    async def _removal_blocker(
        self, session: AsyncSession, character: Character, mark_id: str, now: datetime
    ) -> LegacyMarkRejected | None:
        mark = _known_mark(mark_id)
        if mark is None:
            return LegacyMarkRejected.UNKNOWN
        if mark.id not in await self._active_ids(session, character.id):
            return LegacyMarkRejected.NOT_ACTIVE
        if await current_permanent_brazier(session, character.id) is None:
            return LegacyMarkRejected.SAFE_LOCATION_REQUIRED
        if await _has_foreground(session, character.id):
            return LegacyMarkRejected.ACTIVITY_LOCKED
        available_at = _respec_available_at(character, now)
        if available_at is not None:
            return LegacyMarkRejected.RESPEC_COOLDOWN
        if character.crowns < RESPEC_COST_CROWNS:
            return LegacyMarkRejected.NOT_ENOUGH_CROWNS
        return await _usage_blocker(session, character.id, mark.id, now)

    async def _view(
        self, session: AsyncSession, character: Character, now: datetime
    ) -> LegacyMarksView:
        active = await self._active_ids(session, character.id)
        safe = await current_permanent_brazier(session, character.id)
        return LegacyMarksView(
            legacy_level=character.legacy_level,
            slots=mark_slots(character.legacy_level),
            active_count=len(active),
            crowns=character.crowns,
            location=safe[1] if safe else None,
            respec_available_at=_respec_available_at(character, now),
            entries=tuple(LegacyMarkEntry(mark, mark.id in active) for mark in LEGACY_MARKS),
        )

    @staticmethod
    async def _active_ids(session: AsyncSession, character_id: UUID) -> set[LegacyMarkId]:
        rows = await session.scalars(
            select(CharacterLegacyMark.mark_id).where(
                CharacterLegacyMark.character_id == character_id
            )
        )
        return {LegacyMarkId(row) for row in rows}

    async def _character(
        self, session: AsyncSession, actor: int, *, lock: bool
    ) -> Character | None:
        statement = select(Character).where(
            Character.telegram_id == actor,
            Character.server_id == self.server_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)


def _known_mark(mark_id: str) -> LegacyMark | None:
    try:
        return LEGACY_MARKS_BY_ID[LegacyMarkId(mark_id)]
    except ValueError:
        return None


def _respec_available_at(character: Character, now: datetime) -> datetime | None:
    if character.legacy_mark_respec_at is None:
        return None
    ready = character.legacy_mark_respec_at + RESPEC_COOLDOWN
    return ready if ready > now else None


async def _usage_blocker(
    session: AsyncSession, character_id: UUID, mark: LegacyMarkId, now: datetime
) -> LegacyMarkRejected | None:
    """§16.1: a Marca never leaves current use above the capacity left behind."""
    if mark is LegacyMarkId.BOLSA_FUNDA:
        if await inventory_slots(session, character_id) > INVENTORY_CAPACITY:
            return LegacyMarkRejected.INVENTORY_IN_USE
    elif mark is LegacyMarkId.ARMAZEM_AMPLO:
        if await warehouse_slots(session, character_id) > WAREHOUSE_CAPACITY:
            return LegacyMarkRejected.WAREHOUSE_IN_USE
    elif mark is LegacyMarkId.ENTREGAS_GUARDADAS:
        pending = await session.scalar(
            select(func.count(PendingItem.id)).where(PendingItem.character_id == character_id)
        )
        if int(pending or 0) > PENDING_CAPACITY:
            return LegacyMarkRejected.PENDING_IN_USE
    elif mark is LegacyMarkId.BANCA_EXTRA:
        listings = await session.scalar(
            select(func.count(MarketListing.id))
            .join(PlayerShop, PlayerShop.id == MarketListing.shop_id)
            .where(
                PlayerShop.owner_character_id == character_id,
                MarketListing.status == "active",
                MarketListing.expires_at > now,
            )
        )
        if int(listings or 0) > LISTING_SLOTS:
            return LegacyMarkRejected.LISTINGS_IN_USE
    elif mark is LegacyMarkId.SEXTA_DOUTRINA:
        doctrines = await session.scalar(
            select(func.count())
            .select_from(CharacterDoctrine)
            .where(CharacterDoctrine.character_id == character_id)
        )
        if int(doctrines or 0) > BASE_DOCTRINES:
            return LegacyMarkRejected.DOCTRINES_IN_USE
    return None
