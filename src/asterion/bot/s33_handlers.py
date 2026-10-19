"""Telegram callbacks for S33 — Nomes em Ordem Errada."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s33 import S33Service, S33View
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.bot.creation_handlers import present
from asterion.bot.s33_ui import render_s33


def s33_router(service: S33Service, images: dict[str, str]) -> Router:
    router = Router(name="s33")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is None or not isinstance(query.message, Message):
            return
        screen = render_s33(view) if isinstance(view, S33View) else render_altos_mission(view)
        await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data.startswith("s33:"))
    async def action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if parts == ["s33", "roven"]:
                view = await service.giver(query.from_user.id)
            elif parts == ["s33", "offer"]:
                view = await service.offer(query.from_user.id)
            elif parts == ["s33", "resume"]:
                view = await service.resume(query.from_user.id)
            elif parts == ["s33", "objective"]:
                view = await service.resume(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "accept":
                view = await service.accept(query.from_user.id, int(parts[2]))
            elif len(parts) == 3 and parts[1] == "reaccept":
                view = await service.accept(
                    query.from_user.id, int(parts[2]), reaccept=True
                )
            elif len(parts) == 3 and parts[1] == "track":
                view = await service.toggle_tracking(query.from_user.id, int(parts[2]))
            elif parts == ["s33", "abandon"]:
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
