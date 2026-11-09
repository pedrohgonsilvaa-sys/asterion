"""Telegram adapters for the Expedição (GDD v1.6.0 §22.2)."""

from __future__ import annotations

from collections.abc import Iterable

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from asterion.application.expeditions import (
    ExpeditionError,
    ExpeditionNotice,
    ExpeditionService,
    ExpeditionView,
)
from asterion.bot.creation_handlers import present
from asterion.bot.expedition_ui import error_text, render_expedition
from asterion.bot.guilds_ui import unpack


async def deliver_expedition_notices(bot: Bot, notices: Iterable[ExpeditionNotice]) -> None:
    """Best effort: the state stays reachable from the Expedição screen."""
    for notice in notices:
        screen = render_expedition(notice.view)
        try:
            await bot.send_message(
                notice.telegram_id,
                screen.text,
                reply_markup=screen.keyboard,
                parse_mode=screen.parse_mode,
            )
        except TelegramAPIError:
            continue


def expedition_router(service: ExpeditionService, images: dict[str, str]) -> Router:
    router = Router(name="expeditions")
    router.callback_query.filter(F.message.chat.type == "private")

    async def finish(query: CallbackQuery, view: ExpeditionView) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_expedition(view), images, edit=True)

    async def fail(query: CallbackQuery, code: str) -> None:
        await query.answer(error_text(code), show_alert=True)

    @router.callback_query(F.data == "exp:hub")
    async def hub(query: CallbackQuery) -> None:
        try:
            await finish(query, await service.hub(query.from_user.id))
        except ExpeditionError as error:
            await fail(query, error.code)

    @router.callback_query(F.data == "exp:last")
    async def last(query: CallbackQuery) -> None:
        try:
            await finish(query, await service.last_result(query.from_user.id))
        except ExpeditionError as error:
            await fail(query, error.code)

    @router.callback_query(F.data.startswith("exp:t:"))
    async def toggle(query: CallbackQuery) -> None:
        try:
            token = (query.data or "").rsplit(":", 1)[1]
            view = await service.toggle_roster(query.from_user.id, unpack(token))
        except ExpeditionError as error:
            await fail(query, error.code)
            return
        except (IndexError, ValueError):
            await fail(query, "not_found")
            return
        await finish(query, view)

    @router.callback_query(F.data.startswith("exp:c:"))
    async def choose(query: CallbackQuery) -> None:
        try:
            _, _, token, stage, option = (query.data or "").split(":")
            view = await service.choose(query.from_user.id, unpack(token), int(stage), int(option))
        except ExpeditionError as error:
            await fail(query, error.code)
            return
        except ValueError:
            await fail(query, "not_found")
            return
        await finish(query, view)

    return router
