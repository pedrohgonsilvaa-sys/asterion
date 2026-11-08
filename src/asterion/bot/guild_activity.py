"""Record authenticated activity for the 168h Guild Leader succession (GDD §30.3)."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from asterion.application.guilds import GuildService

logger = logging.getLogger(__name__)

# Technical throttle, not a game rule: one database write per player per minute
# is plenty for a rule measured in days.
ACTIVITY_WRITE_INTERVAL_SECONDS = 60.0


class GuildActivityMiddleware(BaseMiddleware):
    """Outer update middleware. Never blocks or breaks the update it observes."""

    def __init__(
        self,
        guilds: GuildService,
        *,
        clock: Callable[[], float] = time.monotonic,
        interval: float = ACTIVITY_WRITE_INTERVAL_SECONDS,
    ):
        self.guilds = guilds
        self.clock = clock
        self.interval = interval
        self._last_write: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and not getattr(user, "is_bot", False):
            now = self.clock()
            last = self._last_write.get(user.id)
            if last is None or now - last >= self.interval:
                self._last_write[user.id] = now
                try:
                    await self.guilds.record_activity(user.id)
                except Exception:  # noqa: BLE001 - activity must never break gameplay
                    logger.exception("guild activity write failed")
        return await handler(event, data)
