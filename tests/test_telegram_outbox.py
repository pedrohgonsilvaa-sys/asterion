"""Telegram notices through the Outbox: enqueue, send, expiry and permanent errors."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import partial
from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.methods import SendMessage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from asterion.application.outbox import OutboxDispatcher
from asterion.bot.telegram_outbox import (
    TOPIC,
    OutboundTelegram,
    TelegramOutbox,
    send_outbox_message,
)
from asterion.infrastructure.db.models import OutboxMessage

MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Aceitar", callback_data="x:a")]]
)


async def _rows(sessions):
    async with sessions() as session:
        return list((await session.scalars(select(OutboxMessage))).all())


async def test_enqueue_is_idempotent_by_key_and_ordered_by_chat(database):
    sessions = database[1]
    outbox = TelegramOutbox(sessions)
    assert await outbox.send(7, "oi", key="k1", reply_markup=MARKUP) == 1
    assert await outbox.send(7, "oi", key="k1", reply_markup=MARKUP) == 0
    assert await outbox.send(None, "ninguém", key="k2") == 0
    rows = await _rows(sessions)
    assert len(rows) == 1
    row = rows[0]
    assert (row.topic, row.dedup_key, row.aggregate_key) == (TOPIC, "k1", "telegram:7")
    assert row.payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "x:a"
    assert "parse_mode" not in row.payload  # keeps the bot's default


async def test_handler_sends_with_keyboard_and_drops_expired():
    bot = AsyncMock()
    now = datetime(2026, 11, 11, 12, tzinfo=UTC)
    fresh = OutboundTelegram(
        7, "oi", "k", MARKUP, parse_mode=None, expires_at=now + timedelta(seconds=5)
    )
    await send_outbox_message(fresh.payload(), bot=bot, now=now)
    kwargs = bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 7 and kwargs["parse_mode"] is None
    assert kwargs["reply_markup"] == MARKUP

    bot.reset_mock()
    stale = OutboundTelegram(7, "oi", "k", expires_at=now)
    await send_outbox_message(stale.payload(), bot=bot, now=now)
    bot.send_message.assert_not_awaited()


async def test_blocked_bot_is_dead_at_once_and_flood_wait_is_honoured(database):
    sessions = database[1]
    outbox = TelegramOutbox(sessions)
    await outbox.send(1, "a", key="blocked")
    await outbox.send(2, "b", key="flood")
    method = SendMessage(chat_id=1, text="x")
    bot = AsyncMock()

    async def send_message(chat_id, **_kwargs):
        if chat_id == 1:
            raise TelegramForbiddenError(method=method, message="bot was blocked by the user")
        raise TelegramRetryAfter(method=method, message="flood", retry_after=900)

    bot.send_message.side_effect = send_message
    dispatcher = OutboxDispatcher(sessions, {TOPIC: partial(send_outbox_message, bot=bot)})
    report = await dispatcher.run_maintenance()
    assert (report.delivered, report.retried, report.dead) == (0, 1, 1)
    rows = {row.dedup_key: row for row in await _rows(sessions)}
    assert rows["blocked"].status == "dead" and rows["blocked"].attempt_count == 1
    assert "TelegramForbiddenError" in rows["blocked"].last_error
    flood = rows["flood"]
    assert flood.status == "pending"
    assert flood.available_at - datetime.now(UTC) > timedelta(minutes=14)
