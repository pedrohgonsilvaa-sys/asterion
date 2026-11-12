"""Telegram routes for Marcas de Legado."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.legacy_marks import LegacyMarksService
from asterion.bot.creation_handlers import present
from asterion.bot.legacy_marks_ui import (
    REJECTION_TEXT,
    render_legacy_mark_detail,
    render_legacy_mark_removal,
    render_legacy_marks,
)


def legacy_marks_router(service: LegacyMarksService, images: dict[str, str]) -> Router:
    router = Router(name="legacy_marks")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data == "lmk:root")
    async def marks_root(query: CallbackQuery):
        await query.answer()
        view = await service.view(query.from_user.id)
        if view is None or not isinstance(query.message, Message):
            return
        await present(query.message, render_legacy_marks(view), images, edit=True)

    @router.callback_query(F.data.startswith("lmk:d:"))
    async def mark_detail(query: CallbackQuery):
        await query.answer()
        view = await service.view(query.from_user.id)
        if view is None or not isinstance(query.message, Message):
            return
        mark_id = query.data.removeprefix("lmk:d:")
        await present(query.message, render_legacy_mark_detail(view, mark_id), images, edit=True)

    @router.callback_query(F.data.startswith("lmk:on:"))
    async def mark_activate(query: CallbackQuery):
        mark_id = query.data.removeprefix("lmk:on:")
        outcome = await service.activate(query.from_user.id, mark_id)
        if outcome is None or not isinstance(query.message, Message):
            await query.answer()
            return
        if outcome.succeeded:
            await query.answer("Marca ativada.")
            notice = None
        else:
            notice = REJECTION_TEXT[outcome.reason]
            await query.answer(notice, show_alert=True)
        await present(
            query.message,
            render_legacy_mark_detail(outcome.view, mark_id, notice),
            images,
            edit=True,
        )

    @router.callback_query(F.data.startswith("lmk:off:"))
    async def mark_remove_preview(query: CallbackQuery):
        mark_id = query.data.removeprefix("lmk:off:")
        view = await service.view(query.from_user.id)
        if view is None or not isinstance(query.message, Message):
            await query.answer()
            return
        blocker = await service.removal_blocker(query.from_user.id, mark_id)
        if blocker is not None:
            notice = REJECTION_TEXT[blocker]
            await query.answer(notice, show_alert=True)
            await present(
                query.message, render_legacy_mark_detail(view, mark_id, notice), images, edit=True
            )
            return
        await query.answer()
        await present(query.message, render_legacy_mark_removal(view, mark_id), images, edit=True)

    @router.callback_query(F.data.startswith("lmk:offok:"))
    async def mark_remove_confirm(query: CallbackQuery):
        mark_id = query.data.removeprefix("lmk:offok:")
        outcome = await service.remove(query.from_user.id, mark_id)
        if outcome is None or not isinstance(query.message, Message):
            await query.answer()
            return
        if outcome.succeeded:
            await query.answer("Marca removida.")
            notice = "Marca removida. A vaga está livre."
        else:
            notice = REJECTION_TEXT[outcome.reason]
            await query.answer(notice, show_alert=True)
        await present(
            query.message,
            render_legacy_mark_detail(outcome.view, mark_id, notice),
            images,
            edit=True,
        )

    return router
