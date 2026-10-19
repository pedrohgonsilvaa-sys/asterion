"""Telegram callbacks for S35 — O Registro que Discorda."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.altos_missions import AltosMissionView
from asterion.application.s35 import S35Service
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.bot.creation_handlers import present
from asterion.bot.s35_ui import render_s35


def s35_router(service: S35Service, images: dict[str, str]) -> Router:
    router = Router(name="s35")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is None or not isinstance(query.message, Message):
            return
        screen = (
            render_altos_mission(view)
            if isinstance(view, AltosMissionView)
            else render_s35(view)
        )
        await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data.startswith("s35:"))
    async def action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if parts in (["s35", "roven"], ["s35", "eris"]):
                view = await service.giver(query.from_user.id)
            elif parts == ["s35", "offer"]:
                view = await service.offer(query.from_user.id)
            elif parts in (["s35", "resume"], ["s35", "objective"]):
                view = await service.resume(query.from_user.id)
            elif len(parts) == 3 and parts[1] == "accept":
                view = await service.accept(query.from_user.id, int(parts[2]))
            elif len(parts) == 3 and parts[1] == "reaccept":
                view = await service.accept(
                    query.from_user.id, int(parts[2]), reaccept=True
                )
            elif len(parts) == 3 and parts[1] == "track":
                view = await service.toggle_tracking(query.from_user.id, int(parts[2]))
            elif parts == ["s35", "abandon"]:
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
