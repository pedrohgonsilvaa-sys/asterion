"""Flood guard and suspension guard: outer update middlewares, before any game handler."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from asterion.application.sanctions import SanctionService

logger = logging.getLogger(__name__)

SLOW_DOWN_TEXT = "Devagar, aventureiro. Espere um instante."
SUSPENDED_TEXT = "Esta conta está suspensa. Fale com a administração."
_MAX_TRACKED = 20_000


class FloodGuardMiddleware(BaseMiddleware):
    """Token bucket per player, in memory (one bot process). Drops updates over the limit."""

    def __init__(
        self,
        *,
        burst: int,
        per_second: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.burst = float(burst)
        self.per_second = per_second
        self.clock = clock
        self._buckets: dict[int, tuple[float, float]] = {}

    def allow(self, user_id: int) -> bool:
        now = self.clock()
        tokens, stamp = self._buckets.get(user_id, (self.burst, now))
        tokens = min(self.burst, tokens + (now - stamp) * self.per_second)
        allowed = tokens >= 1.0
        self._buckets[user_id] = (tokens - 1.0 if allowed else tokens, now)
        if len(self._buckets) > _MAX_TRACKED:
            horizon = self.burst / self.per_second
            self._buckets = {k: v for k, v in self._buckets.items() if now - v[1] < horizon}
        return allowed

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or getattr(user, "is_bot", False) or self.allow(user.id):
            return await handler(event, data)
        await _tell(event, SLOW_DOWN_TEXT, popup_only=True)
        return None


class SuspensionMiddleware(BaseMiddleware):
    """Blocks suspended accounts. A database failure lets the update through (fail open)."""

    def __init__(self, sanctions: SanctionService):
        self.sanctions = sanctions

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and not getattr(user, "is_bot", False):
            try:
                suspended = await self.sanctions.is_suspended(user.id)
            except Exception:  # noqa: BLE001 - a guard outage must not take the game down
                logger.exception("suspension check failed")
                suspended = False
            if suspended:
                await _tell(event, SUSPENDED_TEXT, popup_only=False)
                return None
        return await handler(event, data)


async def _tell(event: TelegramObject, text: str, *, popup_only: bool) -> None:
    """Best effort notice. Plain messages are answered only for suspensions, not for floods."""
    if not isinstance(event, Update):
        return
    try:
        if event.callback_query is not None:
            await event.callback_query.answer(text, show_alert=not popup_only)
        elif event.message is not None and not popup_only:
            await event.message.answer(text)
    except Exception:  # noqa: BLE001
        logger.debug("guard notice failed", exc_info=True)
