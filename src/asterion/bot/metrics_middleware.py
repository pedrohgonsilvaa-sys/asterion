"""Outer update middleware that counts Telegram updates and times their handling (B6)."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from asterion.infrastructure.metrics import TELEGRAM_UPDATE_SECONDS, TELEGRAM_UPDATES


class MetricsMiddleware(BaseMiddleware):
    """Registered before every other middleware, so it sees the whole handling time."""

    def __init__(self, clock: Callable[[], float] = time.perf_counter):
        self.clock = clock

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        kind = _update_type(event)
        started = self.clock()
        try:
            result = await handler(event, data)
        except Exception:
            TELEGRAM_UPDATES.inc(type=kind, outcome="error")
            raise
        else:
            TELEGRAM_UPDATES.inc(type=kind, outcome="ok")
            return result
        finally:
            TELEGRAM_UPDATE_SECONDS.observe(max(self.clock() - started, 0.0), type=kind)


def _update_type(event: TelegramObject) -> str:
    if isinstance(event, Update):
        try:
            return event.event_type
        except Exception:
            return "unknown"
    return type(event).__name__.lower()
