"""Telegram adapters de A Ruptura do Véu (substitui o World Event regional antigo)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.world_event_veu import VeuEventError, VeuEventService, VeuNotice
from asterion.application.world_event_veu_views import VeuEventViews
from asterion.bot.creation_handlers import present
from asterion.bot.telegram_outbox import TelegramOutbox, notice_message
from asterion.bot.world_event_veu_ui import (
    ACTION_REGISTERED,
    error_text,
    render_notice,
    render_nucleus,
    render_panel,
    render_participants,
    render_targets,
)
from asterion.domain import world_event_veu as ev

_ACTIONS = {"atk": ("attack", None), "def": ("defend", None)}
_ART_SLOTS = {"art1": 1, "art2": 2, "art3": 3}


async def deliver_veu_notices(
    outbox: TelegramOutbox,
    views: VeuEventViews,
    notices: Iterable[VeuNotice],
    *,
    now: datetime,
) -> None:
    """Avisos de 10 e 5 min: uma mensagem por jogador com a categoria Eventos ligada."""
    pending = list(notices)
    if not pending:
        return
    recipients = await views.notice_recipients()
    messages = [
        notice_message(
            f"veu_event:{notice.minutes}", chat_id, render_notice(notice.minutes), now=now
        )
        for notice in pending
        for chat_id in recipients
    ]
    await outbox.send_many(messages)


def veu_event_router(
    service: VeuEventService, views: VeuEventViews, images: dict[str, str]
) -> Router:
    router = Router(name="veu_event")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, screen) -> None:
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def fail(query: CallbackQuery, error: VeuEventError) -> None:
        await query.answer(error_text(error.code), show_alert=True)

    @router.callback_query(F.data.in_({"veu:hub", "wev:hub"}))
    async def hub(query: CallbackQuery) -> None:
        try:
            view = await views.panel(query.from_user.id)
        except VeuEventError as error:
            await fail(query, error)
            return
        await show(query, render_panel(view))

    @router.callback_query(F.data == "veu:back")
    async def back(query: CallbackQuery) -> None:
        """↩️ Núcleos: sai do Núcleo sem punição e sem sair do Evento (§14.6)."""
        try:
            panel = await views.panel(query.from_user.id)
            if panel.occurrence_id is not None and panel.current_nucleus is not None:
                await service.leave_nucleus(
                    panel.occurrence_id, await views.character_id(query.from_user.id)
                )
            view = await views.panel(query.from_user.id)
        except VeuEventError as error:
            await fail(query, error)
            return
        await show(query, render_panel(view))

    async def join_and_enter(actor: int, key: str) -> None:
        panel = await views.panel(actor)
        if panel.occurrence_id is None:
            raise VeuEventError("event_not_running")
        character_id = await views.character_id(actor)
        await service.join(panel.occurrence_id, character_id)
        await service.enter_nucleus(panel.occurrence_id, character_id, key)

    @router.callback_query(F.data.startswith("veu:n:"))
    async def nucleus(query: CallbackQuery) -> None:
        key = (query.data or "").rsplit(":", 1)[1]
        if key not in ev.NUCLEI_BY_KEY:
            await query.answer(error_text("nucleus_not_available"), show_alert=True)
            return
        try:
            await join_and_enter(query.from_user.id, key)
            screen = await views.nucleus_screen(query.from_user.id, key)
        except VeuEventError as error:
            await fail(query, error)
            return
        await show(query, render_nucleus(screen))

    async def register(query: CallbackQuery, kind: str, key: str, number: int, target) -> bool:
        current = await views.current_round(key)
        if current is None or current[1].round_number != number:
            await query.answer(error_text("decision_window_closed"), show_alert=True)
            return False
        occurrence_id, round_ = current
        character_id = await views.character_id(query.from_user.id)
        action_type, slot = ("attack", None)
        if kind in _ACTIONS:
            action_type, slot = _ACTIONS[kind]
        else:
            action_type, slot = "art", _ART_SLOTS[kind]
        await service.register_action(
            round_.id, character_id, action_type, art_slot=slot, target_ref=target
        )
        await query.answer(ACTION_REGISTERED)
        return True

    @router.callback_query(F.data.startswith("veu:a:"))
    async def act(query: CallbackQuery) -> None:
        try:
            _, _, kind, key, number = (query.data or "").split(":")
            if kind not in _ACTIONS and kind not in _ART_SLOTS:
                raise ValueError
            screen = await views.nucleus_screen(query.from_user.id, key)
            alive = [enemy for enemy in screen.enemies if not enemy.defeated]
            if kind != "def" and len(alive) > 1:
                await query.answer()
                if isinstance(query.message, Message):
                    await present(
                        query.message, render_targets(screen, kind), images, edit=True
                    )
                return
            target = alive[0].code if alive and kind != "def" else None
            await register(query, kind, key, int(number), target)
        except VeuEventError as error:
            await fail(query, error)
        except ValueError:
            await query.answer(error_text("unknown"), show_alert=True)

    @router.callback_query(F.data.startswith("veu:t:"))
    async def target(query: CallbackQuery) -> None:
        try:
            _, _, kind, key, number, code = (query.data or "").split(":")
            if kind not in _ACTIONS and kind not in _ART_SLOTS:
                raise ValueError
            if await register(query, kind, key, int(number), code):
                screen = await views.nucleus_screen(query.from_user.id, key)
                if isinstance(query.message, Message):
                    await present(query.message, render_nucleus(screen), images, edit=True)
        except VeuEventError as error:
            await fail(query, error)
        except ValueError:
            await query.answer(error_text("unknown"), show_alert=True)

    @router.callback_query(F.data.startswith("veu:p:"))
    async def participants(query: CallbackQuery) -> None:
        try:
            _, _, key, page = (query.data or "").split(":")
            result = await views.participants_page(query.from_user.id, key, int(page))
        except VeuEventError as error:
            await fail(query, error)
            return
        except ValueError:
            await query.answer(error_text("unknown"), show_alert=True)
            return
        await show(query, render_participants(result))

    return router
