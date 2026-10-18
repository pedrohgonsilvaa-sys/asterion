"""Telegram callbacks for S25 — A Ponte que Espera."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s25 import S25Service
from asterion.bot.creation_handlers import present
from asterion.bot.s25_ui import render_s25


def s25_router(service: S25Service, images: dict[str, str]) -> Router:
    router = Router(name="s25")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s25(view), images, edit=True)

    @router.callback_query(F.data.startswith("s25:"))
    async def action(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            if parts == ["s25", "doren"]:
                view = await service.doren(query.from_user.id)
            elif parts == ["s25", "offer"]:
                view = await service.offer(query.from_user.id)
            elif parts == ["s25", "resume"]:
                view = await service.resume(query.from_user.id)
            elif parts == ["s25", "objective"]:
                view = await service.objective(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "accept":
                view = await service.accept(query.from_user.id, int(parts[2]))
            elif len(parts) == 3 and parts[1] == "reaccept":
                view = await service.accept(
                    query.from_user.id, int(parts[2]), reaccept=True
                )
            elif len(parts) == 3 and parts[1] == "track":
                view = await service.toggle_tracking(query.from_user.id, int(parts[2]))
            elif parts == ["s25", "abandon"]:
                view = await service.abandon_confirmation(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "abandon_confirm":
                view = await service.abandon(query.from_user.id, int(parts[2]))
            elif len(parts) == 4 and parts[1] == "action":
                view = await service.advance(
                    query.from_user.id, int(parts[2]), parts[3]
                )
            else:
                await query.answer()
                return
        except (TypeError, ValueError):
            await query.answer()
            return
        await show(query, view)

    return router
