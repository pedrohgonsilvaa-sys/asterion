"""Read the Obra levels that apply to a character right now (§30.2).

A plain read with no row lock: callers may already hold the Character lock, and
the Guild service locks Guild before Character, so locking here would invert the
order. A level only grows when a Construção completes, so a read that races with
that completion at worst applies the previous level once.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.guild_works import NO_WORKS, WorkLevels
from asterion.infrastructure.db.models import Guild, GuildMember, GuildProject


async def guild_work_levels(session: AsyncSession, guild_id: UUID) -> WorkLevels:
    rows = (
        await session.execute(
            select(GuildProject.kind, func.count())
            .join(Guild, Guild.id == GuildProject.guild_id)
            .where(
                GuildProject.guild_id == guild_id,
                GuildProject.status == "completed",
                Guild.status == "active",
            )
            .group_by(GuildProject.kind)
        )
    ).all()
    if not rows:
        return NO_WORKS
    return WorkLevels.from_levels({kind: int(count) for kind, count in rows})


async def character_work_levels(session: AsyncSession, character_id: UUID) -> WorkLevels:
    guild_id = await session.scalar(
        select(GuildMember.guild_id).where(GuildMember.character_id == character_id)
    )
    if guild_id is None:
        return NO_WORKS
    return await guild_work_levels(session, guild_id)
