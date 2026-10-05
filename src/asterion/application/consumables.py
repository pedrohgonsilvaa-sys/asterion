"""Transactional out-of-combat Consumable actions."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.vigor import add_vigor_state, reconcile_character_vigor, utcnow
from asterion.domain.consumables import (
    VIGOR_RESTORE,
    VIGOR_USABLE_AT_OR_BELOW,
    ConsumableFamily,
    definition,
)
from asterion.infrastructure.db.models import Character, ConsumableStack, GameActivity

DAILY_RESET_ZONE = ZoneInfo("America/Sao_Paulo")
DAILY_RESET_TIME = time(6, 0)


def daily_consumable_cycle(now: datetime) -> date:
    """Return the cycle date whose 06:00 boundary applies to this instant."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    local = now.astimezone(DAILY_RESET_ZONE)
    cycle = local.date()
    if local.timetz().replace(tzinfo=None) < DAILY_RESET_TIME:
        cycle -= timedelta(days=1)
    return cycle


class ConsumableService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def use_vigor_potion(
        self,
        actor: int,
        item_id: str,
        *,
        now: datetime | None = None,
    ) -> int | None:
        item = definition(item_id)
        if item is None or item.family != ConsumableFamily.VIGOR:
            return None
        now = now or utcnow()
        cycle = daily_consumable_cycle(now)
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character)
                .where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
                .with_for_update()
            )
            if character is not None:
                await reconcile_character_vigor(session, character, now=now)
            if (
                character is None
                or character.vigor > VIGOR_USABLE_AT_OR_BELOW
                or character.vigor_consumable_cycle == cycle
            ):
                return None
            active = await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == character.id,
                    GameActivity.status == "active",
                )
            )
            if active is not None:
                return None
            stack = await session.scalar(
                select(ConsumableStack)
                .where(
                    ConsumableStack.character_id == character.id,
                    ConsumableStack.consumable_id == item_id,
                    ConsumableStack.quantity > 0,
                )
                .with_for_update()
            )
            if stack is None:
                return None
            stack.quantity -= 1
            add_vigor_state(character, VIGOR_RESTORE, now=now)
            character.vigor_consumable_cycle = cycle
            return character.vigor
