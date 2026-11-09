"""Dádiva Diária and the delivery shared by every Benefícios reward (GDD §32.1, §49.10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.consumables import daily_consumable_cycle
from asterion.application.item_escrow import return_to_owner
from asterion.domain.engagement import DAILY_GIFT, Bundle, bundle_materials, material_name
from asterion.infrastructure.db.models import Character, DailyGiftClaim, WorldState


class EngagementError(ValueError):
    """A Benefícios action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GrantedItem:
    name: str
    quantity: int


@dataclass(frozen=True, slots=True)
class Granted:
    crowns: int
    items: tuple[GrantedItem, ...]


@dataclass(frozen=True, slots=True)
class DailyGiftView:
    next_day: int
    claimed_today: bool


@dataclass(frozen=True, slots=True)
class DailyGiftResult:
    day: int
    already_claimed: bool
    granted: Granted | None


async def grant_bundle(
    session: AsyncSession, character: Character, bundle: Bundle, source_key: str
) -> Granted:
    """Coroas plus bound materials. The caller holds the Character lock.

    Items that do not fit go to Pending, then to a durable delivery hold.
    """
    character.crowns += bundle.crowns
    region = await session.scalar(
        select(WorldState.region).where(WorldState.character_id == character.id)
    )
    items = []
    for material_id, quantity in sorted(bundle_materials(bundle, region).items()):
        await return_to_owner(
            session,
            character,
            "material",
            {"material_id": material_id, "bound": True},
            quantity,
            f"{source_key}:{material_id}",
        )
        items.append(GrantedItem(material_name(material_id), quantity))
    return Granted(bundle.crowns, tuple(items))


class DailyGiftService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int, *, now: datetime | None = None) -> DailyGiftView:
        cycle = daily_consumable_cycle(now or datetime.now(UTC))
        async with self.sessions() as session:
            await self._character(session, actor)
            claimed = await session.get(DailyGiftClaim, (actor, self.server_id, cycle))
            total = await self._claim_count(session, actor)
            return DailyGiftView(_next_day(total), claimed is not None)

    async def claim(self, actor: int, *, now: datetime | None = None) -> DailyGiftResult:
        """§32.1: idempotent per account, server and daily cycle; a missed day only waits."""
        now = now or datetime.now(UTC)
        cycle = daily_consumable_cycle(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            existing = await session.get(DailyGiftClaim, (actor, self.server_id, cycle))
            if existing is not None:
                return DailyGiftResult(existing.claim_day, True, None)
            day = _next_day(await self._claim_count(session, actor))
            session.add(
                DailyGiftClaim(
                    telegram_id=actor,
                    server_id=self.server_id,
                    cycle_date=cycle,
                    claim_day=day,
                    character_id=character.id,
                    claimed_at=now,
                )
            )
            granted = await grant_bundle(
                session, character, DAILY_GIFT[day - 1], f"benefit:daily:{cycle.isoformat()}"
            )
            return DailyGiftResult(day, False, granted)

    async def _claim_count(self, session, actor: int) -> int:
        return int(
            await session.scalar(
                select(func.count(DailyGiftClaim.cycle_date)).where(
                    DailyGiftClaim.telegram_id == actor,
                    DailyGiftClaim.server_id == self.server_id,
                )
            )
            or 0
        )

    async def _character(self, session, actor: int, *, lock: bool = False) -> Character:
        statement = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        character = await session.scalar(statement.with_for_update() if lock else statement)
        if character is None:
            raise EngagementError("no_character")
        return character


def _next_day(total_claims: int) -> int:
    return total_claims % len(DAILY_GIFT) + 1
