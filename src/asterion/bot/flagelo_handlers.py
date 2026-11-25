"""Telegram adapters de O Despertar dos Flagelos.

Callbacks ``flg:*``. A notificação de nascimento/morte (§18) sai pelo Transactional Outbox:
o serviço grava ``flagelo.community_notice`` na mesma transação do fato (uma linha por
ocorrência, ``dedup_key`` única) e o handler abaixo envia ao grupo/tópico da comunidade.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.flagelos import NOTICE_TOPIC, FlageloError, FlageloService
from asterion.application.outbox import OUTBOX_HANDLERS, OutboxRetryLater, PermanentOutboxError
from asterion.bot.creation_handlers import present
from asterion.bot.flagelo_ui import (
    ACTION_REGISTERED,
    error_text,
    render_ally_targets,
    render_combat,
    render_hub,
    render_notice,
)

logger = logging.getLogger(__name__)

DEEP_LINK = "flagelo"
_ACTIONS = {"atk": ("attack", None), "def": ("defend", None)}
_ART_SLOTS = {"art1": 1, "art2": 2, "art3": 3}


def flagelo_router(service: FlageloService, images: dict[str, str]) -> Router:
    router = Router(name="flagelo")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, screen) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def fail(query: CallbackQuery, error: FlageloError) -> None:
        await query.answer(error_text(error.code, error.seconds), show_alert=True)

    async def combat(query: CallbackQuery) -> None:
        screen = await service.combat_screen(query.from_user.id)
        names = await service.names([item.get("character", "") for item in screen.history])
        await show(query, render_combat(screen, names))

    @router.message(CommandStart(deep_link=True, magic=F.args == DEEP_LINK))
    async def deep_link(message: Message) -> None:
        try:
            view = await service.hub(message.from_user.id)
        except FlageloError as error:
            await message.answer(error_text(error.code, error.seconds))
            return
        await present(message, render_hub(view), images)

    @router.callback_query(F.data == "flg:hub")
    async def hub(query: CallbackQuery) -> None:
        try:
            view = await service.hub(query.from_user.id)
        except FlageloError as error:
            await fail(query, error)
            return
        await show(query, render_hub(view))

    @router.callback_query(F.data == "flg:enter")
    async def enter(query: CallbackQuery) -> None:
        try:
            await service.enter(query.from_user.id)
            await combat(query)
        except FlageloError as error:
            await fail(query, error)

    @router.callback_query(F.data == "flg:fight")
    async def fight(query: CallbackQuery) -> None:
        try:
            await combat(query)
        except FlageloError as error:
            if error.code == "not_in_combat":
                await show(query, render_hub(await service.hub(query.from_user.id)))
                return
            await fail(query, error)

    @router.callback_query(F.data == "flg:leave")
    async def leave(query: CallbackQuery) -> None:
        try:
            await service.leave(query.from_user.id)
            await show(query, render_hub(await service.hub(query.from_user.id)))
        except FlageloError as error:
            await fail(query, error)

    async def register(query: CallbackQuery, kind: str, number: int, target: str | None):
        action_type, slot = _ACTIONS.get(kind) or ("art", _ART_SLOTS[kind])
        await service.register_action(
            query.from_user.id, number, action_type, art_slot=slot, target_ref=target
        )

    @router.callback_query(F.data.startswith("flg:a:"))
    async def act(query: CallbackQuery) -> None:
        try:
            _, _, kind, number = (query.data or "").split(":")
            if kind not in _ACTIONS and kind not in _ART_SLOTS:
                raise ValueError
            if kind in _ART_SLOTS:
                mode = await service.art_target_mode(query.from_user.id, _ART_SLOTS[kind])
                if mode == "ally":
                    allies = await service.allies(query.from_user.id)
                    if not allies:
                        await query.answer(
                            "Não há aliado disponível para essa Arte.", show_alert=True
                        )
                        return
                    await show(query, render_ally_targets(allies, kind, int(number)))
                    return
            await register(query, kind, int(number), None)
            await combat(query)
        except FlageloError as error:
            await fail(query, error)
        except ValueError:
            await query.answer(error_text("invalid_action"), show_alert=True)

    @router.callback_query(F.data.startswith("flg:t:"))
    async def target(query: CallbackQuery) -> None:
        try:
            _, _, kind, number, code = (query.data or "").split(":")
            if kind not in _ART_SLOTS or not code.startswith("c") or len(code) != 33:
                raise ValueError
            await register(query, kind, int(number), f"c:{code[1:]}")
            await combat(query)
        except FlageloError as error:
            await fail(query, error)
        except ValueError:
            await query.answer(error_text("invalid_action"), show_alert=True)

    return router


def register_flagelo_notices(service: FlageloService, chat_id: int | None, topic_id: int | None):
    """Liga o tópico ``flagelo.community_notice`` do Outbox ao grupo da comunidade.

    Sem ``community_chat_id`` configurado o aviso é descartado (registrado no log). O Outbox
    entrega pelo menos uma vez; o ``dedup_key`` já impede gravar o mesmo aviso duas vezes.
    """

    async def deliver(payload: Mapping[str, Any], *, bot: Any = None) -> None:
        if chat_id is None:
            logger.info("flagelo notice %s dropped: no community chat", payload.get("kind"))
            return
        found = await service.notice_payload(UUID(str(payload["event_id"])))
        if found is None:
            raise PermanentOutboxError("flagelo event not found")
        name, short_name, region = found
        if bot is None:
            from asterion.bot.runtime import get_bot_runtime

            bot = get_bot_runtime().bot
        kwargs: dict[str, Any] = {
            "chat_id": chat_id,
            "text": render_notice(str(payload["kind"]), name, short_name, region),
        }
        if topic_id is not None:
            kwargs["message_thread_id"] = topic_id
        # Aponta para o hub do evento no privado do bot (mesmo padrão de link do Chamado).
        me = await bot.get_me()
        if me.username:
            kwargs["reply_markup"] = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="⚔️ O Despertar dos Flagelos",
                            url=f"https://t.me/{me.username}?start={DEEP_LINK}",
                        )
                    ]
                ]
            )
        try:
            await bot.send_message(**kwargs)
        except TelegramRetryAfter as error:
            raise OutboxRetryLater(error.retry_after, str(error)) from error
        except (TelegramForbiddenError, TelegramNotFound, TelegramBadRequest) as error:
            raise PermanentOutboxError(f"{type(error).__name__}: {error}") from error

    OUTBOX_HANDLERS[NOTICE_TOPIC] = deliver
    return deliver


__all__ = ["flagelo_router", "register_flagelo_notices", "ACTION_REGISTERED"]
