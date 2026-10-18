"""Telegram callbacks for S29 — Os que Disseram Não."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s29 import S29Service
from asterion.bot.creation_handlers import present
from asterion.bot.s29_ui import render_s29


def s29_router(service: S29Service, images: dict[str, str]) -> Router:
    router = Router(name="s29")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s29(view), images, edit=True)

    @router.callback_query(F.data.startswith("s29:"))
    async def action(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            if parts == ["s29", "maro"]:
                view = await service.giver(query.from_user.id)
            elif parts == ["s29", "offer"]:
                view = await service.offer(query.from_user.id)
            elif parts == ["s29", "resume"]:
                view = await service.resume(query.from_user.id)
            elif parts == ["s29", "objective"]:
                view = await service.objective(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "accept":
                view = await service.accept(query.from_user.id, int(parts[2]))
            elif len(parts) == 3 and parts[1] == "reaccept":
                view = await service.accept(
                    query.from_user.id, int(parts[2]), reaccept=True
                )
            elif len(parts) == 3 and parts[1] == "track":
                view = await service.toggle_tracking(query.from_user.id, int(parts[2]))
            elif parts == ["s29", "abandon"]:
                view = await service.abandon_confirmation(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "abandon_confirm":
                view = await service.abandon(query.from_user.id, int(parts[2]))
            elif len(parts) >= 4 and parts[1] == "action":
                view = await service.advance(
                    query.from_user.id,
                    int(parts[2]),
                    ":".join(parts[3:]),
                )
            else:
                await query.answer()
                return
        except (TypeError, ValueError):
            await query.answer()
            return
        await show(query, view)

    return router
