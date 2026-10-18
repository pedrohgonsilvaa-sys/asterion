"""Telegram callbacks for S27 — Cabo Partido."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s27 import S27Service
from asterion.bot.creation_handlers import present
from asterion.bot.s27_ui import render_s27


def s27_router(service: S27Service, images: dict[str, str]) -> Router:
    router = Router(name="s27")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s27(view), images, edit=True)

    @router.callback_query(F.data.startswith("s27:"))
    async def action(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            if parts == ["s27", "doren"]:
                view = await service.giver(query.from_user.id)
            elif parts == ["s27", "offer"]:
                view = await service.offer(query.from_user.id)
            elif parts == ["s27", "resume"]:
                view = await service.resume(query.from_user.id)
            elif parts == ["s27", "objective"]:
                view = await service.objective(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "accept":
                view = await service.accept(query.from_user.id, int(parts[2]))
            elif len(parts) == 3 and parts[1] == "reaccept":
                view = await service.accept(
                    query.from_user.id, int(parts[2]), reaccept=True
                )
            elif len(parts) == 3 and parts[1] == "track":
                view = await service.toggle_tracking(query.from_user.id, int(parts[2]))
            elif parts == ["s27", "abandon"]:
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
