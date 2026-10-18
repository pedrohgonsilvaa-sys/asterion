"""Telegram callbacks for S30 — A Ordem que Restou."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s30 import S30Service, S30View
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.bot.creation_handlers import present
from asterion.bot.s30_ui import render_s30


def s30_router(service: S30Service, images: dict[str, str]) -> Router:
    router = Router(name="s30")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is None or not isinstance(query.message, Message):
            return
        screen = render_s30(view) if isinstance(view, S30View) else render_altos_mission(view)
        await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data.startswith("s30:"))
    async def action(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            if parts == ["s30", "sel"]:
                view = await service.giver(query.from_user.id)
            elif parts == ["s30", "offer"]:
                view = await service.offer(query.from_user.id)
            elif parts == ["s30", "resume"]:
                view = await service.resume(query.from_user.id)
            elif parts == ["s30", "objective"]:
                view = await service.objective(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "accept":
                view = await service.accept(query.from_user.id, int(parts[2]))
            elif len(parts) == 3 and parts[1] == "reaccept":
                view = await service.accept(
                    query.from_user.id, int(parts[2]), reaccept=True
                )
            elif len(parts) == 3 and parts[1] == "track":
                view = await service.toggle_tracking(query.from_user.id, int(parts[2]))
            elif parts == ["s30", "abandon"]:
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
            await query.answer("A ação expirou ou o estado da missão mudou.", show_alert=True)
            return
        await show(query, view)

    return router
