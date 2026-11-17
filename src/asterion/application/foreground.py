"""Cheap, read-only checks for active player foreground work."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.infrastructure.db.models import (
    Character,
    ClassTrialState,
    DungeonLobby,
    DungeonLobbyMember,
    DungeonMatchQueue,
    DungeonRun,
    DungeonRunMember,
    GameActivity,
    HuntRound,
)

ACTIVE_LOBBY_MEMBER_STATES = ("invited", "joined", "queued", "matched", "confirmed")


def _active_foreground_for(character_id):
    """Build one SQL predicate covering every foreground source."""
    return or_(
        select(GameActivity.id)
        .where(
            GameActivity.character_id == character_id,
            GameActivity.status == "active",
        )
        .exists(),
        select(HuntRound.id)
        .where(
            HuntRound.character_id == character_id,
            HuntRound.status.in_(("preparing", "active", "interrupted")),
        )
        .exists(),
        select(DungeonRunMember.run_id)
        .join(DungeonRun, DungeonRun.id == DungeonRunMember.run_id)
        .where(
            DungeonRunMember.character_id == character_id,
            DungeonRunMember.status.in_(("active", "defeated")),
            DungeonRun.status == "active",
        )
        .exists(),
        select(DungeonLobbyMember.lobby_id)
        .join(DungeonLobby, DungeonLobby.id == DungeonLobbyMember.lobby_id)
        .where(
            DungeonLobbyMember.character_id == character_id,
            DungeonLobbyMember.status.in_(ACTIVE_LOBBY_MEMBER_STATES),
            DungeonLobby.status.in_(("forming", "confirming")),
        )
        .exists(),
        select(DungeonMatchQueue.character_id)
        .where(
            DungeonMatchQueue.character_id == character_id,
            DungeonMatchQueue.status.in_(("queued", "matched")),
        )
        .exists(),
        select(ClassTrialState.character_id)
        .where(
            ClassTrialState.character_id == character_id,
            ClassTrialState.status == "active",
        )
        .exists(),
    )


async def has_foreground(session: AsyncSession, character_id) -> bool:
    """Check all foreground sources with one database round-trip."""
    found = await session.scalar(
        select(Character.id).where(
            Character.id == character_id,
            _active_foreground_for(Character.id),
        )
    )
    return found is not None


async def has_foreground_for_actor(
    sessions: async_sessionmaker[AsyncSession], actor: int, server_id: str
) -> bool:
    """Resolve the actor and check foreground state in one SQL statement."""
    async with sessions() as session:
        found = await session.scalar(
            select(Character.id).where(
                Character.telegram_id == actor,
                Character.server_id == server_id,
                _active_foreground_for(Character.id),
            )
        )
    return found is not None
