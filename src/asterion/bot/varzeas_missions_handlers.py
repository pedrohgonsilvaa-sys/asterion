"""Telegram callbacks for the Várzeas opening missions."""

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.varzeas_missions import P19_ID, S19_ID, VarzeasMissionService
from asterion.bot.creation_handlers import present
from asterion.bot.varzeas_missions_ui import render_varzeas_mission


def varzeas_missions_router(service: VarzeasMissionService, images: dict[str, str]) -> Router:
    router = Router(name="varzeas_missions")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def resume_from_command(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler()
        view = await service.resume_active(message.from_user.id)
        if view is None:
            raise SkipHandler()
        await present(message, render_varzeas_mission(view), images)

    @router.callback_query(F.data.startswith("varzeas:"))
    async def mission_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) < 3 or parts[2] not in {P19_ID, S19_ID}:
            raise SkipHandler()
        await query.answer()
        if not isinstance(query.message, Message):
            return
        if parts[1] == "mission" and len(parts) == 3:
            view = await service.resume(query.from_user.id, parts[2])
        elif parts[1] == "start" and len(parts) == 3:
            view = await service.start(query.from_user.id, parts[2])
        elif parts[1] == "action" and len(parts) == 5:
            try:
                version = int(parts[3])
            except ValueError:
                raise SkipHandler() from None
            view = await service.advance(query.from_user.id, parts[2], version, parts[4])
        else:
            raise SkipHandler()
        if view is not None:
            await present(query.message, render_varzeas_mission(view), images, edit=True)

    return router
