"""Telegram adapters for Duelo and Arena da Vigília (GDD v1.6.0 §14, §39.4)."""

from __future__ import annotations

from collections.abc import Iterable

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ForceReply, Message

from asterion.application.pvp import (
    PvpCombatView,
    PvpError,
    PvpNotice,
    PvpOutcome,
    PvpService,
)
from asterion.bot.combat_ui import PvpCombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.guilds_ui import unpack
from asterion.bot.market_ui import with_ref
from asterion.bot.pvp_ui import (
    DUEL_PROMPT_REF,
    error_text,
    render_pvp,
    render_ranking,
    render_surrender_confirm,
)

DUEL_PROMPT = with_ref("Envie o nome do personagem que você quer desafiar.", DUEL_PROMPT_REF)


async def deliver_notices(bot: Bot, notices: Iterable[PvpNotice]) -> None:
    """Best effort: the state is durable and every screen can be reopened."""
    for notice in notices:
        screen = render_pvp(notice.view)
        try:
            await bot.send_message(
                notice.telegram_id,
                screen.text,
                reply_markup=screen.keyboard,
                parse_mode=screen.parse_mode,
            )
        except TelegramAPIError:
            continue


def pvp_router(service: PvpService, images: dict[str, str]) -> Router:
    router = Router(name="pvp")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def finish(query: CallbackQuery, outcome: PvpOutcome) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_pvp(outcome.view), images, edit=True)
        await deliver_notices(query.bot, outcome.notices)

    async def fail(query: CallbackQuery, error: PvpError) -> None:
        await query.answer(error_text(error.code), show_alert=True)

    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def resume_foreground(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler
        view = await service.foreground(message.from_user.id)
        if view is None:
            raise SkipHandler
        await present(message, render_pvp(view), images)

    @router.callback_query(F.data.in_({"pvp:hub", "pvp:ref"}))
    async def hub(query: CallbackQuery) -> None:
        try:
            view = await service.resume(query.from_user.id)
        except PvpError as error:
            await fail(query, error)
            return
        await finish(query, PvpOutcome(view))

    @router.callback_query(F.data == "pvp:rank")
    async def ranking(query: CallbackQuery) -> None:
        try:
            view = await service.ranking(query.from_user.id)
        except PvpError as error:
            await fail(query, error)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_ranking(view), images, edit=True)

    @router.callback_query(F.data == "pvp:q")
    async def enter_queue(query: CallbackQuery) -> None:
        try:
            outcome = await service.enter_queue(query.from_user.id)
        except PvpError as error:
            await fail(query, error)
            return
        await finish(query, outcome)

    @router.callback_query(F.data == "pvp:leave")
    async def leave_queue(query: CallbackQuery) -> None:
        try:
            outcome = await service.leave_queue(query.from_user.id)
        except PvpError as error:
            await fail(query, error)
            return
        await finish(query, outcome)

    @router.callback_query(F.data == "pvp:duel")
    async def duel_prompt(query: CallbackQuery) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await query.message.answer(DUEL_PROMPT, reply_markup=ForceReply(selective=True))

    @router.message(
        F.text,
        F.reply_to_message.text.func(lambda text: text == DUEL_PROMPT),
        F.reply_to_message.from_user.is_bot,
    )
    async def duel_name(message: Message) -> None:
        if message.from_user is None:
            return
        try:
            view = await service.duel_preview(message.from_user.id, message.text or "")
        except PvpError as error:
            await message.answer(error_text(error.code))
            return
        await present(message, render_pvp(view), images)

    async def by_token(query: CallbackQuery, method) -> None:
        try:
            token = (query.data or "").rsplit(":", 1)[1]
            outcome = await method(query.from_user.id, unpack(token))
        except PvpError as error:
            await fail(query, error)
            return
        except (IndexError, ValueError):
            await query.answer(error_text("not_found"), show_alert=True)
            return
        await finish(query, outcome)

    @router.callback_query(F.data.startswith("pvp:dch:"))
    async def challenge(query: CallbackQuery) -> None:
        await by_token(query, service.challenge)

    @router.callback_query(F.data.startswith("pvp:ok:"))
    async def accept(query: CallbackQuery) -> None:
        await by_token(query, service.accept)

    @router.callback_query(F.data.startswith("pvp:no:"))
    async def decline(query: CallbackQuery) -> None:
        await by_token(query, service.decline)

    @router.callback_query(F.data.startswith("pvp:sur:"))
    async def surrender_confirm(query: CallbackQuery) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            token = (query.data or "").rsplit(":", 1)[1]
            await present(query.message, render_surrender_confirm(token), images, edit=True)

    @router.callback_query(F.data.startswith("pvp:suy:"))
    async def surrender(query: CallbackQuery) -> None:
        await by_token(query, service.surrender)

    @router.callback_query(PvpCombatCallback.filter())
    async def fight(query: CallbackQuery, callback_data: PvpCombatCallback) -> None:
        try:
            view = await service.resume(query.from_user.id)
            if (
                not isinstance(view, PvpCombatView)
                or view.battle.activity_id.hex != callback_data.activity
            ):
                await finish(query, PvpOutcome(view))
                return
            outcome = await service.action(
                query.from_user.id,
                view.match_id,
                callback_data.combat_version,
                callback_data.action_index,
                callback_data.target,
            )
        except PvpError as error:
            await fail(query, error)
            return
        await finish(query, outcome)

    return router
