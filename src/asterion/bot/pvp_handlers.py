"""Telegram adapters for Duelo and Arena da Vigília (GDD v1.6.0 §14, §39.4)."""

from __future__ import annotations

from collections.abc import Iterable

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.pvp import (
    PvpCombatView,
    PvpError,
    PvpHubView,
    PvpNotice,
    PvpOutcome,
    PvpService,
)
from asterion.bot.combat_ui import PvpCombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.guilds_ui import unpack
from asterion.bot.pvp_ui import (
    error_text,
    render_arena,
    render_duel_prompt,
    render_level_ranking,
    render_pvp,
    render_ranking,
    render_surrender_confirm,
    render_vigil,
)
from asterion.bot.text_prompt import (
    PROMPTS,
    HasPrompt,
    PendingPrompt,
    consume_reply,
    show_on_prompt,
)


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

    async def show(query: CallbackQuery, screen) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data.in_({"pvp:hub", "pvp:ref", "pvp:vig"}))
    async def hub(query: CallbackQuery) -> None:
        """Arena (§7.1) e Arena da Vigília (§7.2); uma atividade aberta tem prioridade."""
        try:
            view = await service.resume(query.from_user.id)
        except PvpError as error:
            await fail(query, error)
            return
        if isinstance(view, PvpHubView) and view.invite is None:
            if query.data == "pvp:hub":
                await show(query, render_arena())
                return
            ranking = await service.ranking(query.from_user.id)
            position = ranking.own.position if ranking.own is not None else None
            await show(query, render_vigil(view, position=position))
            return
        await finish(query, PvpOutcome(view))

    @router.callback_query(F.data.regexp(r"^pvp:rank(:\d+)?$"))
    async def ranking(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            view = await service.ranking(
                query.from_user.id, page=int(parts[2]) if len(parts) == 3 else 0
            )
        except PvpError as error:
            await fail(query, error)
            return
        await show(query, render_ranking(view))

    @router.callback_query(F.data.regexp(r"^rank:level(:\d+)?$"))
    async def level_ranking(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        view = await service.level_ranking(page=int(parts[2]) if len(parts) == 3 else 0)
        await show(query, render_level_ranking(view))

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
        """Duelo (§7.4): edita a tela atual e espera o nome digitado."""
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_duel_prompt(), images, edit=True)
            PROMPTS.open(query.from_user.id, "pvp:duel", query.message)

    @router.message(F.text, HasPrompt("pvp:duel"))
    async def duel_name(message: Message, prompt: PendingPrompt) -> None:
        text = message.text or ""
        await consume_reply(message)
        PROMPTS.close(message.from_user.id)
        try:
            view = await service.duel_preview(message.from_user.id, text)
        except PvpError as error:
            message_id = await show_on_prompt(
                message, prompt, render_duel_prompt(error_text(error.code)), images
            )
            PROMPTS.follow(message.from_user.id, prompt, message_id=message_id)
            return
        await show_on_prompt(message, prompt, render_pvp(view), images)

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
