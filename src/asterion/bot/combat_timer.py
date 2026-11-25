"""Live turn countdown for Foreground combat (Bloco UI 1 §7).

The engine owns the turn: ``Combat.turn_deadline`` is stamped when a player's turn
opens and every action checks it (``domain/combat.act``). This module never keeps a
clock of its own. Once per second it re-reads the authoritative combat through the
service, re-renders the HUD (``🌐 Turno N · ⏱️ 9s``) and edits only the message
text/caption. When the deadline has passed it asks the service to apply the existing
timeout rule (the overdue turn is spent once, by ``act``/``expire_turn``), and the
next read shows the fresh turn at ``10s``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Message

from asterion.bot.creation_ui import Screen
from asterion.domain import turn_clock
from asterion.domain.combat import Combat, turn_seconds_left

logger = logging.getLogger(__name__)

# Action id the engine does not know: ``act`` resolves it as the timeout of an
# overdue turn, and as a no-op while the turn is still open, so it can never be
# mistaken for a real player choice.
TIMEOUT_ACTION = "timeout"
# A tick never outlives a turn that nobody resolves (e.g. the service vanished).
MAX_TICKS = 600
_SETTLE = 0.05


@dataclass(frozen=True, slots=True)
class Tick:
    screen: Screen
    combat: Combat | None


Refresh = Callable[[], Awaitable[Tick | None]]
Expire = Callable[[], Awaitable[object]]


def _seconds(combat: Combat | None) -> float | None:
    if combat is None or combat.result:
        return None
    return turn_seconds_left(combat)


class CombatTicker:
    """One countdown task per combat message; a new watch replaces the old one."""

    def __init__(self, *, sleep: Callable[[float], Awaitable[object]] = asyncio.sleep):
        self._tasks: dict[tuple[int, int], asyncio.Task] = {}
        self._sleep = sleep

    def stop(self, chat_id: int, message_id: int) -> None:
        task = self._tasks.pop((chat_id, message_id), None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    def watch(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
        refresh: Refresh,
        expire: Expire,
    ) -> asyncio.Task:
        self.stop(chat_id, message_id)
        task = asyncio.create_task(
            self._run(bot, chat_id, message_id, refresh, expire),
            name=f"combat-timer:{chat_id}:{message_id}",
        )
        self._tasks[(chat_id, message_id)] = task
        task.add_done_callback(
            lambda done, key=(chat_id, message_id): (
                self._tasks.pop(key, None) if self._tasks.get(key) is done else None
            )
        )
        return task

    async def _run(self, bot, chat_id, message_id, refresh, expire) -> None:
        shown: str | None = None
        caption = True
        for _ in range(MAX_TICKS):
            tick = await refresh()
            if tick is None:
                return
            left = _seconds(tick.combat)
            if tick.screen.text != shown:
                caption = await self._edit(bot, chat_id, message_id, tick.screen, caption)
                if caption is None:
                    return
                shown = tick.screen.text
            if left is None:
                # Combat over or no timed turn open: nothing left to count.
                return
            if left <= 0:
                # Deadline reached: the existing server-side timeout rule spends it.
                await self._sleep(_SETTLE)
                await expire()
                continue
            # Wake on the next whole second so the display steps 10s → 9s → … → 0s.
            fraction = left - math.floor(left)
            await self._sleep((fraction if fraction > 0 else 1.0) + _SETTLE)

    async def _edit(self, bot, chat_id, message_id, screen: Screen, caption: bool):
        """Edit only the words and buttons: the picture of the encounter stays put."""
        for attempt in (caption, not caption):
            try:
                if attempt:
                    await bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=message_id,
                        caption=screen.text,
                        reply_markup=screen.keyboard,
                        parse_mode=screen.parse_mode,
                    )
                else:
                    await bot.edit_message_text(
                        text=screen.text,
                        chat_id=chat_id,
                        message_id=message_id,
                        reply_markup=screen.keyboard,
                        parse_mode=screen.parse_mode,
                    )
                return attempt
            except TelegramRetryAfter as exc:
                await self._sleep(float(exc.retry_after))
                return attempt
            except TelegramBadRequest as exc:
                reason = exc.message.lower()
                if "not modified" in reason:
                    return attempt
                if "no caption" in reason or "no text" in reason:
                    continue
                logger.info("combat timer stopped: %s", exc.message)
                return None
        return None


ticker = CombatTicker()

# context -> factory(message, activity_id) -> (refresh, expire). Each combat router
# registers the services it already owns; contexts without a factory keep the
# static timer text (their own schedulers resolve timeouts, e.g. PvP and Groups).
TimerFactory = Callable[[Message, UUID], tuple[Refresh, Expire]]
_FACTORIES: dict[str, TimerFactory] = {}
# Off until a real bot process starts (polling or webhook): unit tests that drive
# handlers with fake messages never spawn background countdowns.
_ENABLED = False


def enable(value: bool = True) -> None:
    global _ENABLED
    _ENABLED = value


def register(context: str, factory: TimerFactory) -> None:
    _FACTORIES[context] = factory


def on_present(message: Message | None, message_id: int | None, screen: Screen) -> None:
    """Called by ``present`` after a screen is shown: restart or stop the countdown."""
    if message is None or message_id is None:
        return
    chat = getattr(message, "chat", None)
    if chat is None:
        return
    if not screen.timer:
        ticker.stop(chat.id, message_id)
        return
    context, _, activity_hex = screen.timer.partition(":")
    factory = _FACTORIES.get(context)
    if not _ENABLED or factory is None or getattr(chat, "type", "private") != "private":
        return
    try:
        activity_id = UUID(hex=activity_hex)
    except ValueError:
        return
    refresh, expire = factory(message, activity_id)
    watch_combat_message(message, refresh, expire, message_id=message_id)


def watch_combat_message(
    message: Message | None,
    refresh: Refresh,
    expire: Expire,
    *,
    message_id: int | None = None,
) -> None:
    """Start (or restart) the countdown of the combat shown in ``message``."""
    if message is None or message.bot is None:
        return
    with contextlib.suppress(RuntimeError):
        ticker.watch(
            message.bot,
            message.chat.id,
            message_id or message.message_id,
            refresh,
            expire,
        )


__all__ = [
    "TIMEOUT_ACTION",
    "CombatTicker",
    "Tick",
    "on_present",
    "register",
    "ticker",
    "turn_clock",
    "watch_combat_message",
]
