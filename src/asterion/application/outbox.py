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
`dedup_key` for that. The registry starts empty: topics register their handler.
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
        exhausted = message.attempt_count >= MAX_ATTEMPTS
        values: dict[str, Any] = {"last_error": text}
        if exhausted:
            values["status"] = DEAD
        else:
            values["status"] = PENDING
            values["available_at"] = func.now() + retry_delay(message.attempt_count)
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
