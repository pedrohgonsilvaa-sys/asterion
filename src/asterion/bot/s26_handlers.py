"""Telegram callbacks for S26 — Turno sem Fim."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s26 import S26Service
from asterion.bot.creation_handlers import present
from asterion.bot.s26_ui import render_s26


def s26_router(service: S26Service, images: dict[str, str]) -> Router:
    router = Router(name="s26")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s26(view), images, edit=True)

    @router.callback_query(F.data.startswith("s26:"))
    async def action(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            if parts == ["s26", "hesa"]:
                view = await service.giver(query.from_user.id)
            elif parts == ["s26", "offer"]:
                view = await service.offer(query.from_user.id)
            elif parts == ["s26", "resume"]:
                view = await service.resume(query.from_user.id)
            elif parts == ["s26", "objective"]:
                view = await service.objective(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "accept":
                view = await service.accept(query.from_user.id, int(parts[2]))
            elif len(parts) == 3 and parts[1] == "reaccept":
                view = await service.accept(
                    query.from_user.id, int(parts[2]), reaccept=True
                )
            elif len(parts) == 3 and parts[1] == "track":
                view = await service.toggle_tracking(query.from_user.id, int(parts[2]))
            elif parts == ["s26", "abandon"]:
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
