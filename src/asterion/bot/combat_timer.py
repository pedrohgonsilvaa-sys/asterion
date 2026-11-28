"""Silent 10 s turn watch for Foreground combat.

The engine owns the turn: ``Combat.turn_deadline`` is stamped when a player's turn
opens and every action checks it (``domain/combat.act``). The countdown is no longer
shown: this watch sleeps until the deadline, then asks the service to apply the
existing timeout rule (the overdue turn is spent once, by ``act``/``expire_turn``).
The HUD is therefore edited only when the turn actually changes (a player action or
a timeout), never once per second.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import logging
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
# Returned by ``CombatTicker.write`` when the render was not sent (identical to the
# last one, or superseded by a newer read of the combat).
SKIPPED = object()
# Monotonic tickets: a render takes its ticket *before* reading the combat, so a
# higher ticket always means a read that happened later.
_tickets = itertools.count()


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


def fingerprint(screen: Screen) -> str:
    """Everything the message would show; an identical fingerprint needs no edit."""
    keyboard = screen.keyboard.model_dump_json(exclude_none=True) if screen.keyboard else ""
    return f"{screen.parse_mode}\x1f{screen.text}\x1f{keyboard}"


class CombatTicker:
    """One countdown task per combat message; a new watch replaces the old one.

    Every write to a live combat message (the countdown *and* the action handlers'
    re-renders) goes through ``write``: one at a time per message, never twice the
    same content, and never an older read after a newer one.
    """

    def __init__(self, *, sleep: Callable[[float], Awaitable[object]] = asyncio.sleep):
        self._tasks: dict[tuple[int, int], asyncio.Task] = {}
        self._sleep = sleep
        self._locks: dict[tuple[int, int], asyncio.Lock] = {}
        self._ticket: dict[tuple[int, int], int] = {}
        self._written: dict[tuple[int, int], str] = {}

    def begin(self) -> int:
        return next(_tickets)

    def tracks(self, chat_id: int, message_id: int) -> bool:
        key = (chat_id, message_id)
        return key in self._tasks or key in self._written

    def seed(self, chat_id: int, message_id: int, screen: Screen) -> None:
        """Remember what a freshly sent message shows, so the countdown does not repeat it."""
        self._written[(chat_id, message_id)] = fingerprint(screen)

    def release(self, chat_id: int, message_id: int) -> None:
        """Forget a message once it leaves the live countdown (its state is no longer needed)."""
        key = (chat_id, message_id)
        self._ticket.pop(key, None)
        self._written.pop(key, None)
        lock = self._locks.get(key)
        if lock is None or not lock.locked():
            self._locks.pop(key, None)

    async def write(
        self,
        chat_id: int,
        message_id: int,
        ticket: int,
        screen: Screen,
        edit: Callable[[], Awaitable[object]],
        *,
        force: bool = False,
    ):
        """Run ``edit`` for ``screen`` unless it is stale (or, without ``force``, redundant).

        Writes to one message are serialized by its lock. A write is skipped when a
        render with a later ticket already reached the message (its read is newer) or,
        unless ``force``, when the message already shows exactly this content. Action
        and callback renders use ``force``: a stale tap still redraws the current HUD.
        The countdown never forces, so its restart does not repeat the action's render.
        """
        key = (chat_id, message_id)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            current = fingerprint(screen)
            if ticket < self._ticket.get(key, -1):
                return SKIPPED
            if not force and self._written.get(key) == current:
                self._ticket[key] = ticket
                return SKIPPED
            result = await edit()
            if result is not None:
                self._ticket[key] = ticket
                self._written[key] = current
            return result

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
        caption = True
        for _ in range(MAX_TICKS):
            ticket = self.begin()
            tick = await refresh()
            if tick is None:
                return
            left = _seconds(tick.combat)

            async def edit(screen=tick.screen, mode=caption):
                return await self._edit(bot, chat_id, message_id, screen, mode)

            result = await self.write(chat_id, message_id, ticket, tick.screen, edit)
            if result is None:
                return
            if result is not SKIPPED:
                caption = result
            if left is None:
                # Combat over or no timed turn open: nothing left to count.
                return
            if left <= 0:
                # Deadline reached: the existing server-side timeout rule spends it.
                await self._sleep(_SETTLE)
                await expire()
                continue
            # Nothing is displayed per second: sleep straight to the deadline.
            await self._sleep(left + _SETTLE)

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
        ticker.release(chat.id, message_id)
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
    "SKIPPED",
    "TIMEOUT_ACTION",
    "CombatTicker",
    "Tick",
    "fingerprint",
    "on_present",
    "register",
    "ticker",
    "turn_clock",
    "watch_combat_message",
]
