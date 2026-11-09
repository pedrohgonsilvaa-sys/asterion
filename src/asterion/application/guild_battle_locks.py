"""Batalha de Guildas locks read by other services (GDD v1.6.0 §15, §30.3).

Kept apart from ``guild_battle`` so the Guild, Legacy and upkeep modules can
import it without pulling the combat stack.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.infrastructure.db.models import GuildBattleRegistration, GuildBattleRosterEntry

OPEN_REGISTRATION = ("registered", "paired")


async def character_roster_locked(session: AsyncSession, character_id: UUID) -> bool:
    """§15: from pairing until the result, the roster cannot lose eligibility."""
    row = await session.scalar(
        select(GuildBattleRosterEntry.registration_id)
        .join(
            GuildBattleRegistration,
            GuildBattleRegistration.id == GuildBattleRosterEntry.registration_id,
        )
        .where(
            GuildBattleRosterEntry.character_id == character_id,
            GuildBattleRosterEntry.status != "replaced",
            GuildBattleRegistration.status == "paired",
        )
        .limit(1)
    )
    return row is not None


async def guild_has_open_battle(session: AsyncSession, guild_id: UUID) -> bool:
    """§30.3: an Inscrição or a Batalha in progress holds the final dissolution."""
    row = await session.scalar(
        select(GuildBattleRegistration.id)
        .where(
            GuildBattleRegistration.guild_id == guild_id,
            GuildBattleRegistration.status.in_(OPEN_REGISTRATION),
        )
        .limit(1)
    )
    return row is not None
