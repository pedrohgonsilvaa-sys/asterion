"""GDD §43.5: Transactional Outbox dispatcher.

Game code writes an `OutboxMessage` in the same transaction as the game state.
This dispatcher delivers it later, at least once:

* `claim` marks a batch `processing` with `FOR UPDATE SKIP LOCKED` and a lease
  (`available_at` moved ahead), so several instances never take the same row.
  A worker that dies leaves the row `processing`; it is claimed again when the
  lease expires.
* Delivery runs outside any database transaction.
* Success -> `delivered`. Failure -> `pending` with a later `available_at`
  (backoff), or `dead` once `MAX_ATTEMPTS` is spent.
* Order: a message waits while an earlier one with the same `aggregate_key` is
  still `pending` or `processing`. `dead` and `delivered` do not block.

Handlers are delivered at least once, so they must tolerate a repeat and can use
`dedup_key` for that. Topics register their handler in `OUTBOX_HANDLERS`.

A handler raises `PermanentOutboxError` when a retry cannot help (the row goes
straight to `dead`) and `OutboxRetryLater` when the receiver names its own wait.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from asterion.infrastructure.db.models import OutboxMessage

logger = logging.getLogger(__name__)

PENDING = "pending"
PROCESSING = "processing"
DELIVERED = "delivered"
DEAD = "dead"

# Policy (author delegated): 5 attempts, then `dead`. Wait after the Nth failure.
MAX_ATTEMPTS = 5
RETRY_DELAYS = (
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=10),
    timedelta(hours=1),
)
# A claimed row is invisible to other workers for this long.
LEASE = timedelta(minutes=2)
HANDLER_TIMEOUT_SECONDS = 60.0
BATCH_SIZE = 20
MAX_ERROR_LENGTH = 2000

class PermanentOutboxError(Exception):
    """Delivery can never succeed (for example, the user blocked the bot)."""


class OutboxRetryLater(Exception):
    """The receiver asked to wait `seconds` before the next attempt."""

    def __init__(self, seconds: float, message: str = ""):
        super().__init__(message or f"retry after {seconds}s")
        self.seconds = seconds


OutboxHandler = Callable[[Mapping[str, Any]], Awaitable[None]]

# topic -> async handler(payload). Real topics register here when they exist.
OUTBOX_HANDLERS: dict[str, OutboxHandler] = {}


@dataclass(frozen=True)
class OutboxReport:
    delivered: int = 0
    retried: int = 0
    dead: int = 0


@dataclass(frozen=True)
class _Claimed:
    id: Any
    topic: str
    payload: dict[str, Any]
    attempt_count: int


def retry_delay(attempt_count: int) -> timedelta:
    """Wait after failure number `attempt_count` (1-based)."""
    return RETRY_DELAYS[min(attempt_count, len(RETRY_DELAYS)) - 1]


class OutboxDispatcher:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        handlers: Mapping[str, OutboxHandler] | None = None,
        *,
        batch_size: int = BATCH_SIZE,
    ):
        self.sessions = sessions
        self.handlers = OUTBOX_HANDLERS if handlers is None else handlers
        self.batch_size = batch_size

    async def run_maintenance(self) -> OutboxReport:
        """One pass: claim a batch and deliver it. Used by the scheduler job."""
        claimed = await self._claim()
        delivered = retried = dead = 0
        for message in claimed:
            outcome = await self._deliver(message)
            if outcome == DELIVERED:
                delivered += 1
            elif outcome == DEAD:
                dead += 1
            else:
                retried += 1
        return OutboxReport(delivered, retried, dead)

    async def _claim(self) -> list[_Claimed]:
        earlier = aliased(OutboxMessage)
        blocked = (
            select(earlier.id)
            .where(
                earlier.aggregate_key == OutboxMessage.aggregate_key,
                earlier.status.in_((PENDING, PROCESSING)),
                (earlier.created_at < OutboxMessage.created_at)
                | (
                    (earlier.created_at == OutboxMessage.created_at)
                    & (earlier.id < OutboxMessage.id)
                ),
            )
            .exists()
        )
        async with self.sessions.begin() as session:
            ids = (
                await session.scalars(
                    select(OutboxMessage.id)
                    .where(
                        ((OutboxMessage.status == PENDING) | (OutboxMessage.status == PROCESSING)),
                        OutboxMessage.available_at <= func.now(),
                        ~blocked,
                    )
                    .order_by(OutboxMessage.created_at, OutboxMessage.id)
                    .limit(self.batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            if not ids:
                return []
            rows = (
                await session.execute(
                    update(OutboxMessage)
                    .where(OutboxMessage.id.in_(ids))
                    .values(
                        status=PROCESSING,
                        attempt_count=OutboxMessage.attempt_count + 1,
                        available_at=func.now() + LEASE,
                    )
                    .returning(
                        OutboxMessage.id,
                        OutboxMessage.topic,
                        OutboxMessage.payload,
                        OutboxMessage.attempt_count,
                    )
                )
            ).all()
        return [_Claimed(r.id, r.topic, r.payload, r.attempt_count) for r in rows]

    async def _deliver(self, message: _Claimed) -> str:
        handler = self.handlers.get(message.topic)
        try:
            if handler is None:
                raise LookupError(f"no handler registered for topic {message.topic!r}")
            await asyncio.wait_for(handler(message.payload), HANDLER_TIMEOUT_SECONDS)
        except Exception as error:  # noqa: BLE001 - any handler failure is a retry
            return await self._fail(message, error)
        async with self.sessions.begin() as session:
            await session.execute(
                update(OutboxMessage)
                .where(OutboxMessage.id == message.id)
                .values(status=DELIVERED, delivered_at=func.now(), last_error=None)
            )
        return DELIVERED

    async def _fail(self, message: _Claimed, error: BaseException) -> str:
        text = f"{type(error).__name__}: {error}"[:MAX_ERROR_LENGTH]
        # A receiver's own wait (flood control) is not a failure: it refunds the attempt.
        waiting = isinstance(error, OutboxRetryLater)
        exhausted = not waiting and (
            message.attempt_count >= MAX_ATTEMPTS or isinstance(error, PermanentOutboxError)
        )
        values: dict[str, Any] = {"last_error": text}
        if exhausted:
            values["status"] = DEAD
        else:
            delay = retry_delay(message.attempt_count)
            if isinstance(error, OutboxRetryLater):
                delay = timedelta(seconds=max(error.seconds, 1))
                values["attempt_count"] = OutboxMessage.attempt_count - 1
            values["status"] = PENDING
            values["available_at"] = func.now() + delay
        async with self.sessions.begin() as session:
            await session.execute(
                update(OutboxMessage).where(OutboxMessage.id == message.id).values(**values)
            )
        if exhausted:
            logger.warning(
                "outbox message %s (%s) is dead after %d attempts: %s",
                message.id,
                message.topic,
                message.attempt_count,
                text,
            )
            return DEAD
        logger.info(
            "outbox message %s (%s) failed attempt %d: %s",
            message.id,
            message.topic,
            message.attempt_count,
            text,
        )
        return PENDING


@dataclass(frozen=True)
class OutboxStats:
    counts: dict[str, int]
    oldest_open_age_seconds: float | None


async def outbox_stats(sessions: async_sessionmaker[AsyncSession]) -> OutboxStats:
    """Rows per status and the age of the oldest row still waiting (pending/processing)."""
    async with sessions() as session:
        rows = (
            await session.execute(
                select(OutboxMessage.status, func.count()).group_by(OutboxMessage.status)
            )
        ).all()
        age = await session.scalar(
            select(func.extract("epoch", func.now() - func.min(OutboxMessage.created_at))).where(
                OutboxMessage.status.in_((PENDING, PROCESSING))
            )
        )
    counts = {PENDING: 0, PROCESSING: 0, DELIVERED: 0, DEAD: 0}
    counts.update({status: int(n) for status, n in rows})
    return OutboxStats(counts, None if age is None else float(age))


async def requeue_dead(
    sessions: async_sessionmaker[AsyncSession], ids: list[Any] | None = None
) -> int:
    """Send `dead` rows back to `pending` with a fresh attempt budget. Returns the count."""
    statement = (
        update(OutboxMessage)
        .where(OutboxMessage.status == DEAD)
        .values(status=PENDING, attempt_count=0, available_at=func.now())
    )
    if ids is not None:
        statement = statement.where(OutboxMessage.id.in_(ids))
    async with sessions.begin() as session:
        result = await session.execute(statement)
    return int(result.rowcount or 0)
