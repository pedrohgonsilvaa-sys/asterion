"""Telegram intent callbacks for the S6 secondary mission."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.s6 import S6_MARKS, S6Service
from asterion.bot.creation_handlers import present
from asterion.bot.s6_ui import render_s6


def s6_router(service: S6Service, images: dict[str, str]) -> Router:
    router = Router(name="s6")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("s6:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw == "s6:offer":
            view = await service.offer(actor)
        elif raw == "s6:oren":
            view = await service.oren(actor)
        elif raw == "s6:resume" or raw == "s6:detail":
            view = await service.resume(actor)
        elif len(parts) >= 3:
            try:
                version = int(parts[1])
            except ValueError:
                version = None
            operation = parts[2]
            if version is not None:
                if operation in {"accept", "reaccept"} and len(parts) == 3:
                    view = await service.accept(actor, version, reaccept=operation == "reaccept")
                elif operation == "abandon" and len(parts) == 3:
                    view = await service.abandon(actor, version)
                elif operation == "track" and len(parts) == 3:
                    view = await service.toggle_tracking(actor, version)
                elif operation == "review" and len(parts) == 3:
                    view = await service.action(actor, version, "review")
                elif operation == "shelter" and len(parts) == 3:
                    view = await service.action(actor, version, "shelter")
                elif operation == "start_boss" and len(parts) == 3:
                    view = await service.action(actor, version, "start_boss")
                elif operation == "group" and len(parts) == 3:
                    try:
                        view = await service.propose_group_combat(actor, version)
                    except GroupError:
                        await query.answer(
                            "Não foi possível preparar o Grupo. Atualize a tela.",
                            show_alert=True,
                        )
                        return
                elif operation == "record" and len(parts) == 3:
                    view = await service.action(actor, version, "last_record")
                elif operation == "retry" and len(parts) == 3:
                    view = await service.action(actor, version, "retry")
                elif operation == "report" and len(parts) == 3:
                    view = await service.action(actor, version, "report")
                elif operation == "mark" and len(parts) == 4:
                    try:
                        index = int(parts[3])
                    except ValueError:
                        index = 0
                    if 1 <= index <= len(S6_MARKS):
                        view = await service.action(actor, version, "mark", S6_MARKS[index - 1])
        if view is None:
            view = await service.resume(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s6(view), images, edit=True)

    return router
