"""Operator suspensions (GDD §36: flags are reviewed by people; this is the human decision).

Rows are never deleted: lifting a suspension sets `revoked_at`, so the history stays auditable.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.infrastructure.db.models import AccountSanction

# Technical cache so a suspended player does not cost one query per tap.
CACHE_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class SanctionView:
    id: str
    telegram_id: int
    reason: str
    created_by: str
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


def _view(row: AccountSanction) -> SanctionView:
    return SanctionView(
        str(row.id),
        row.telegram_id,
        row.reason,
        row.created_by,
        row.created_at,
        row.expires_at,
        row.revoked_at,
    )


def _active(now: datetime):
    return (
        AccountSanction.revoked_at.is_(None),
        (AccountSanction.expires_at.is_(None)) | (AccountSanction.expires_at > now),
    )


class SanctionService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.sessions = sessions
        self._clock = clock
        self._now = now
        self._cache: dict[int, tuple[float, bool]] = {}

    async def is_suspended(self, telegram_id: int) -> bool:
        cached = self._cache.get(telegram_id)
        if cached is not None and self._clock() - cached[0] < CACHE_SECONDS:
            return cached[1]
        async with self.sessions() as session:
            found = await session.scalar(
                select(AccountSanction.id)
                .where(AccountSanction.telegram_id == telegram_id, *_active(self._now()))
                .limit(1)
            )
        result = found is not None
        self._cache[telegram_id] = (self._clock(), result)
        return result

    async def suspend(
        self, telegram_id: int, *, reason: str, by: str, hours: int | None = None
    ) -> SanctionView:
        now = self._now()
        row = AccountSanction(
            telegram_id=telegram_id,
            reason=reason[:300],
            created_by=by[:64],
            created_at=now,
            expires_at=now + timedelta(hours=hours) if hours else None,
        )
        async with self.sessions.begin() as session:
            session.add(row)
        self._cache.pop(telegram_id, None)
        return _view(row)

    async def lift(self, telegram_id: int, *, by: str) -> int:
        now = self._now()
        async with self.sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(AccountSanction)
                    .where(AccountSanction.telegram_id == telegram_id, *_active(now))
                    .with_for_update()
                )
            ).all()
            for row in rows:
                row.revoked_at = now
                row.revoked_by = by[:64]
        self._cache.pop(telegram_id, None)
        return len(rows)

    async def active(self) -> list[SanctionView]:
        async with self.sessions() as session:
            rows = await session.scalars(
                select(AccountSanction)
                .where(*_active(self._now()))
                .order_by(AccountSanction.created_at)
            )
            return [_view(row) for row in rows]

    async def history(self, telegram_id: int) -> list[SanctionView]:
        async with self.sessions() as session:
            rows = await session.scalars(
                select(AccountSanction)
                .where(AccountSanction.telegram_id == telegram_id)
                .order_by(AccountSanction.created_at)
            )
            return [_view(row) for row in rows]
