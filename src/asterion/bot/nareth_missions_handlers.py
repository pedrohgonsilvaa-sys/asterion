"""Telegram callbacks for P13 and S13 in Planícies de Nareth."""

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.nareth_missions import P13_ID, S13_ID, NarethMissionService
from asterion.bot.creation_handlers import present
from asterion.bot.nareth_missions_ui import render_nareth_mission


def nareth_missions_router(
    service: NarethMissionService, images: dict[str, str]
) -> Router:
    router = Router(name="nareth_missions")
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
        await present(message, render_nareth_mission(view), images, edit=False)

    @router.callback_query(F.data.startswith("nareth:"))
    async def mission_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) < 3 or parts[1] not in {"mission", "start", "action", "ex"}:
            raise SkipHandler()
        quest_id = parts[2] if parts[1] in {"mission", "start"} else (
            parts[2] if len(parts) >= 5 else ""
        )
        if quest_id not in {P13_ID, S13_ID}:
            raise SkipHandler()
        try:
            if parts[1] == "mission" and len(parts) == 3:
                view = await service.resume(query.from_user.id, quest_id)
            elif parts[1] == "start" and len(parts) == 3:
                view = await service.start(query.from_user.id, quest_id)
            elif parts[1] == "action" and len(parts) == 5:
                view = await service.advance(
                    query.from_user.id,
                    quest_id,
                    int(parts[3]),
                    parts[4],
                )
            elif parts[1] == "ex" and len(parts) == 5:
                view = await service.examine(
                    query.from_user.id,
                    quest_id,
                    int(parts[3]),
                    parts[4],
                )
            else:
                raise ValueError("invalid Nareth mission callback")
        except (TypeError, ValueError):
            view = await service.resume(query.from_user.id, quest_id)
        if view is None:
            raise SkipHandler()
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_nareth_mission(view), images, edit=True)

    return router
