"""Authoritative checks for a character currently at a discovered permanent brazier."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.road import BRAZIER_DETAILS
from asterion.infrastructure.db.models import Brazier, WorldState


async def current_permanent_brazier(
    session: AsyncSession, character_id: UUID
) -> tuple[str, str] | None:
    """Return (brazier id, location) only when the character is physically there.

    Temporary Dungeon braziers are not present in BRAZIER_DETAILS and therefore
    cannot grant access to the character Warehouse.
    """

    world = await session.scalar(
        select(WorldState).where(WorldState.character_id == character_id)
    )
    if world is None:
        return None
    candidates = sorted(
        brazier_id
        for brazier_id, (location, _label) in BRAZIER_DETAILS.items()
        if location == world.location
    )
    if not candidates:
        return None
    discovered = await session.scalar(
        select(Brazier.brazier_id)
        .where(
            Brazier.character_id == character_id,
            Brazier.brazier_id.in_(candidates),
        )
        .order_by(Brazier.brazier_id)
        .limit(1)
    )
    if discovered is None:
        return None
    return discovered, world.location
