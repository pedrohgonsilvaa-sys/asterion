"""Block checks and Recentes shared by the services that bring two players together.

Every function runs inside the caller's transaction. This module imports only the
ORM, so Grupo, Guilda, Troca and PvP can use it without importing each other.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from itertools import permutations
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.social import RECENT_WINDOW
from asterion.infrastructure.db.models import CharacterBlock, RecentContact


async def blocked_between(session: AsyncSession, first: UUID, second: UUID) -> bool:
    """§31: a block in either direction stops direct interactions between the two."""
    found = await session.scalar(
        select(CharacterBlock.blocker_character_id)
        .where(
            or_(
                (CharacterBlock.blocker_character_id == first)
                & (CharacterBlock.blocked_character_id == second),
                (CharacterBlock.blocker_character_id == second)
                & (CharacterBlock.blocked_character_id == first),
            )
        )
        .limit(1)
    )
    return found is not None


async def record_recent_contacts(
    session: AsyncSession, character_ids: Iterable[UUID], now: datetime
) -> None:
    """Refresh §31 Recentes. Rows are written in key order, which rules out deadlocks."""
    ids = sorted(set(character_ids))
    if len(ids) < 2:
        return
    rows = [
        {"character_id": first, "other_character_id": second, "last_seen_at": now}
        for first, second in sorted(permutations(ids, 2))
    ]
    statement = insert(RecentContact).values(rows)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[RecentContact.character_id, RecentContact.other_character_id],
            set_={"last_seen_at": statement.excluded.last_seen_at},
        )
    )
    await session.execute(
        delete(RecentContact).where(
            RecentContact.character_id.in_(ids),
            RecentContact.last_seen_at < now - RECENT_WINDOW,
        )
    )
