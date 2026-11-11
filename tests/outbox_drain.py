"""Test helper: deliver queued Telegram Outbox messages through a test bot."""

from __future__ import annotations

from functools import partial

from asterion.application.outbox import OutboxDispatcher, OutboxReport
from asterion.bot.telegram_outbox import TOPIC, send_outbox_message


async def drain_telegram_outbox(sessions, bot) -> None:
    dispatcher = OutboxDispatcher(sessions, {TOPIC: partial(send_outbox_message, bot=bot)})
    while await dispatcher.run_maintenance() != OutboxReport():
        pass


class RecordingOutbox:
    """Stands in for `TelegramOutbox` where a test only checks what is enqueued."""

    def __init__(self):
        self.messages = []

    async def send_many(self, messages) -> int:
        batch = list(messages)
        self.messages.extend(batch)
        return len(batch)
