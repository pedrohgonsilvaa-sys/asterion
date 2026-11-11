"""Telegram messages sent through the Transactional Outbox (GDD §43.5).

Notices that scheduler jobs produce (Arena/Duel, Guild Battle, World Event, Oath,
Expedition) are not sent inline any more. They become an
`OutboxMessage` with topic `telegram.send_message`, and the dispatcher job sends
them with retry. Approved by the author on 2026-11-11.

* `dedup_key` makes the enqueue idempotent: the same key is stored once.
* `aggregate_key` is the chat, so one player's notices arrive in order.
* `expires_at` (from the screen's own deadline) drops a notice that would arrive
  after its prompt is over, such as a 45s Arena invite or a 60s turn.
* Blocked bot, deleted chat or a bad request are permanent: the row goes to
  `dead` without retry. Telegram's flood wait is honoured as the retry delay.

Telegram has no idempotency key, so a crash between a successful send and the
`delivered` mark can still repeat one message (at least once).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.outbox import (
    OUTBOX_HANDLERS,
    OutboxRetryLater,
    PermanentOutboxError,
)
from asterion.infrastructure.db.models import OutboxMessage

logger = logging.getLogger(__name__)

TOPIC = "telegram.send_message"
_UNSET = object()


class _Screen(Protocol):
    text: str
    keyboard: InlineKeyboardMarkup | None
    parse_mode: str | None


@dataclass(frozen=True, slots=True)
class OutboundTelegram:
    chat_id: int
    text: str
    dedup_key: str
    reply_markup: InlineKeyboardMarkup | None = None
    # `_UNSET` keeps the bot's default parse mode; `None` sends plain text.
    parse_mode: Any = _UNSET
    expires_at: datetime | None = None

    def payload(self) -> dict[str, Any]:
        data: dict[str, Any] = {"chat_id": self.chat_id, "text": self.text}
        if self.reply_markup is not None:
            data["reply_markup"] = self.reply_markup.model_dump(mode="json", exclude_none=True)
        if self.parse_mode is not _UNSET:
            data["parse_mode"] = self.parse_mode
        if self.expires_at is not None:
            data["expires_at"] = self.expires_at.isoformat()
        return data


def screen_digest(text: str, markup: InlineKeyboardMarkup | None) -> str:
    raw = json.dumps(
        [text, markup.model_dump(mode="json", exclude_none=True) if markup else None],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


VOLATILE_FIELDS = frozenset({"seconds_left", "deadline"})
DEDUP_WINDOW_SECONDS = 600


def view_digest(view: object, markup: InlineKeyboardMarkup | None) -> str:
    """Hash of what the notice says, without the countdown that changes every run."""
    state = dataclasses.asdict(view) if dataclasses.is_dataclass(view) else repr(view)
    if isinstance(state, dict):
        state = {k: v for k, v in state.items() if k not in VOLATILE_FIELDS}
    raw = json.dumps(
        [state, markup.model_dump(mode="json", exclude_none=True) if markup else None],
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def dedup_window(now: datetime) -> str:
    """Repeats of one run fall in the same window, so they share the key."""
    return str(int(now.timestamp()) // DEDUP_WINDOW_SECONDS)


def screen_deadline(view: object, now: datetime) -> datetime | None:
    """The prompt's own deadline: `seconds_left` (Arena, Duel, turns) or `deadline`."""
    seconds = getattr(view, "seconds_left", None)
    if isinstance(seconds, int) and seconds > 0:
        return now + timedelta(seconds=seconds)
    deadline = getattr(view, "deadline", None)
    return deadline if isinstance(deadline, datetime) else None


def notice_message(
    source: str,
    chat_id: int,
    screen: _Screen,
    *,
    view: object | None = None,
    now: datetime,
) -> OutboundTelegram:
    """A job notice. The key is stable: source, chat, content and a 10 min window."""
    digest = (
        view_digest(view, screen.keyboard)
        if view is not None
        else screen_digest(screen.text, screen.keyboard)
    )
    return OutboundTelegram(
        chat_id=chat_id,
        text=screen.text,
        reply_markup=screen.keyboard,
        parse_mode=screen.parse_mode,
        dedup_key=f"{source}:{dedup_window(now)}:{chat_id}:{digest}",
        expires_at=screen_deadline(view, now) if view is not None else None,
    )


class TelegramOutbox:
    """Writes Telegram messages to the Outbox instead of sending them."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def send(
        self,
        chat_id: int | None,
        text: str,
        *,
        key: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        expires_at: datetime | None = None,
    ) -> int:
        if chat_id is None:
            return 0
        return await self.send_many(
            [
                OutboundTelegram(
                    chat_id=chat_id,
                    text=text,
                    dedup_key=key,
                    reply_markup=reply_markup,
                    expires_at=expires_at,
                )
            ]
        )

    async def send_many(self, messages: Iterable[OutboundTelegram]) -> int:
        """Enqueue in one transaction. Returns how many were new."""
        rows = [
            {
                "topic": TOPIC,
                "dedup_key": message.dedup_key[:200],
                "aggregate_key": f"telegram:{message.chat_id}",
                "payload": message.payload(),
            }
            for message in messages
        ]
        if not rows:
            return 0
        async with self.sessions.begin() as session:
            result = await session.execute(
                insert(OutboxMessage)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["dedup_key"])
                .returning(OutboxMessage.id)
            )
            return len(result.all())


async def enqueue_notices(
    outbox: TelegramOutbox,
    source: str,
    notices: Iterable[Any],
    render: Any,
    *,
    now: datetime | None = None,
) -> int:
    """Render job/peer notices (`telegram_id` + `view`) and enqueue them in one batch."""
    current = now or datetime.now(UTC)
    return await outbox.send_many(
        notice_message(
            source,
            notice.telegram_id,
            render(notice.view),
            view=notice.view,
            now=current,
        )
        for notice in notices
    )


async def send_outbox_message(
    payload: Mapping[str, Any], *, bot: Any = None, now: datetime | None = None
) -> None:
    """Outbox handler for `telegram.send_message`."""
    expires_at = payload.get("expires_at")
    current = now or datetime.now(UTC)
    if expires_at and datetime.fromisoformat(expires_at) <= current:
        logger.info("outbox telegram notice to %s expired; dropped", payload["chat_id"])
        return
    if bot is None:
        from asterion.bot.runtime import get_bot_runtime

        bot = get_bot_runtime().bot
    kwargs: dict[str, Any] = {"chat_id": payload["chat_id"], "text": payload["text"]}
    if "reply_markup" in payload:
        kwargs["reply_markup"] = InlineKeyboardMarkup.model_validate(payload["reply_markup"])
    if "parse_mode" in payload:
        kwargs["parse_mode"] = payload["parse_mode"]
    try:
        await bot.send_message(**kwargs)
    except TelegramRetryAfter as error:
        raise OutboxRetryLater(error.retry_after, str(error)) from error
    except (TelegramForbiddenError, TelegramNotFound, TelegramBadRequest) as error:
        raise PermanentOutboxError(f"{type(error).__name__}: {error}") from error


OUTBOX_HANDLERS[TOPIC] = send_outbox_message
