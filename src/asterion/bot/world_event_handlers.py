"""Telegram adapters for Eventos Mundiais (GDD v1.6.0 §21)."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.world_events import (
    WorldEventError,
    WorldEventNotice,
    WorldEventService,
    WorldEventView,
)
from asterion.bot.combat_ui import WorldEventCombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.guilds_ui import unpack
from asterion.bot.telegram_outbox import TelegramOutbox, enqueue_notices
from asterion.bot.world_event_ui import (
    error_text,
    render_withdraw_confirm,
    render_world_event,
)


async def deliver_world_event_notices(
    outbox: TelegramOutbox, notices: Iterable[WorldEventNotice]
) -> None:
    """Best effort: the result is durable and can be reopened in Eventos."""
    await enqueue_notices(outbox, "world_event", notices, render_world_event)


def world_event_router(service: WorldEventService, images: dict[str, str]) -> Router:
    router = Router(name="world_events")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def finish(query: CallbackQuery, view: WorldEventView) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_world_event(view), images, edit=True)

    async def fail(query: CallbackQuery, error: WorldEventError) -> None:
        await query.answer(error_text(error.code, error.seconds), show_alert=True)

    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def resume_foreground(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler
        view = await service.foreground(message.from_user.id)
        if view is None:
            raise SkipHandler
        await present(message, render_world_event(view), images)

    @router.callback_query(F.data == "wev:hub")
    async def hub(query: CallbackQuery) -> None:
        try:
            view = await service.hub(query.from_user.id)
        except WorldEventError as error:
            await fail(query, error)
            return
        await finish(query, view)

    @router.callback_query(F.data == "wev:last")
    async def last(query: CallbackQuery) -> None:
        try:
            view = await service.last_result(query.from_user.id)
        except WorldEventError as error:
            await fail(query, error)
            return
        await finish(query, view)

    async def by_token(query: CallbackQuery, method) -> None:
        try:
            token = (query.data or "").rsplit(":", 1)[1]
            occurrence_id: UUID = unpack(token)
            view = await method(query.from_user.id, occurrence_id)
        except WorldEventError as error:
            await fail(query, error)
            return
        except (IndexError, ValueError):
            await query.answer(error_text("not_found"), show_alert=True)
            return
        await finish(query, view)

    @router.callback_query(F.data.startswith("wev:in:"))
    async def enter(query: CallbackQuery) -> None:
        await by_token(query, service.enter)

    @router.callback_query(F.data.startswith("wev:go:"))
    async def fight(query: CallbackQuery) -> None:
        await by_token(query, service.fight)

    @router.callback_query(F.data.startswith("wev:out:"))
    async def withdraw_confirm(query: CallbackQuery) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            token = (query.data or "").rsplit(":", 1)[1]
            await present(query.message, render_withdraw_confirm(token), images, edit=True)

    @router.callback_query(F.data.startswith("wev:oy:"))
    async def withdraw(query: CallbackQuery) -> None:
        await by_token(query, service.withdraw)

    @router.callback_query(WorldEventCombatCallback.filter())
    async def combat(query: CallbackQuery, callback_data: WorldEventCombatCallback) -> None:
        try:
            view = await service.action(
                query.from_user.id,
                UUID(callback_data.activity),
                callback_data.combat_version,
                callback_data.action_index,
                callback_data.target,
            )
        except WorldEventError as error:
            await fail(query, error)
            return
        await finish(query, view)

    return router
