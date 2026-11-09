"""The Crônica as the competitive cycle of Arena and Batalha de Guildas (GDD §5.3).

Shared by the Arena, the Batalha de Guildas and the Crônica service, so none of
them imports the others. A cycle has two steps: the entry closes at T, and the
real finalization (T+2h) archives the Classificação, applies the Renome soft
reset and starts the next cycle's standings. Between them, new Arena entries and
new Inscrições for battles at or after T are refused; anything already started
finishes normally.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.infrastructure.db.models import ChronicleCycle


def advisory_key(name: str) -> int:
    raw = int.from_bytes(sha256(name.encode()).digest()[:8], "big")
    return raw - (1 << 64) if raw >= (1 << 63) else raw


async def entry_closed(session: AsyncSession, server_id: str, at: datetime) -> bool:
    """True while a Crônica reached T at ``at`` and is not finalized yet."""
    found = await session.scalar(
        select(ChronicleCycle.chronicle_id)
        .where(
            ChronicleCycle.server_id == server_id,
            ChronicleCycle.end_at <= at,
            ChronicleCycle.finalized_at.is_(None),
        )
        .limit(1)
    )
    return found is not None


async def current_cycle_started_at(session: AsyncSession, server_id: str) -> datetime | None:
    """Start of the current competitive cycle: the last finalization, if any."""
    return await session.scalar(
        select(func.max(ChronicleCycle.finalized_at)).where(ChronicleCycle.server_id == server_id)
    )
