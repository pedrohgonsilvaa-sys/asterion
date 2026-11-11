"""Telegram adapters for the Juramento (GDD v1.6.0 §22.1)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.oaths import OathError, OathNotice, OathService, OathView
from asterion.bot.combat_ui import OathCombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.oath_ui import error_text, render_abandon_confirm, render_oath
from asterion.bot.telegram_outbox import TelegramOutbox, enqueue_notices


async def deliver_oath_notices(outbox: TelegramOutbox, notices: Iterable[OathNotice]) -> None:
    """Best effort: every state stays reachable from the Juramento screen."""
    await enqueue_notices(outbox, "oath", notices, render_oath)


async def runtime_oath_notifier(notices: Sequence[OathNotice]) -> None:
    from asterion.infrastructure.db.session import SessionFactory

    await deliver_oath_notices(TelegramOutbox(SessionFactory), notices)


def oath_router(service: OathService, images: dict[str, str]) -> Router:
    router = Router(name="oaths")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def finish(query: CallbackQuery, view: OathView) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_oath(view), images, edit=True)

    async def run(query: CallbackQuery, method) -> None:
        try:
            view = await method(query.from_user.id)
        except OathError as error:
            await query.answer(error_text(error.code), show_alert=True)
            return
        await finish(query, view)

    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def resume_foreground(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler
        view = await service.foreground(message.from_user.id)
        if view is None:
            raise SkipHandler
        await present(message, render_oath(view), images)

    @router.callback_query(F.data == "oath:hub")
    async def hub(query: CallbackQuery) -> None:
        await run(query, service.hub)

    @router.callback_query(F.data == "oath:last")
    async def last(query: CallbackQuery) -> None:
        await run(query, service.last_result)

    @router.callback_query(F.data == "oath:solo")
    async def solo(query: CallbackQuery) -> None:
        await run(query, service.start_solo)

    @router.callback_query(F.data == "oath:go")
    async def resume(query: CallbackQuery) -> None:
        view = await service.foreground(query.from_user.id)
        if view is None:
            await run(query, service.hub)
            return
        await finish(query, view)

    @router.callback_query(F.data == "oath:out")
    async def abandon_confirm(query: CallbackQuery) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_abandon_confirm(), images, edit=True)

    @router.callback_query(F.data == "oath:outy")
    async def abandon(query: CallbackQuery) -> None:
        await run(query, service.abandon)

    @router.callback_query(OathCombatCallback.filter())
    async def combat(query: CallbackQuery, callback_data: OathCombatCallback) -> None:
        try:
            view = await service.action(
                query.from_user.id,
                UUID(callback_data.activity),
                callback_data.combat_version,
                callback_data.action_index,
                callback_data.target,
            )
        except OathError as error:
            await query.answer(error_text(error.code), show_alert=True)
            return
        await finish(query, view)

    return router
