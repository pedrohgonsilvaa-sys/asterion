"""Intent-only Telegram callbacks for S3."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.s3 import S3_TRACKS, S3Service
from asterion.bot.creation_handlers import present
from asterion.bot.s3_ui import render_s3


def s3_router(service: S3Service, images: dict[str, str]) -> Router:
    router = Router(name="s3")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("s3:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw == "s3:offer":
            view = await service.offer(actor)
        elif raw == "s3:resume":
            view = await service.resume(actor)
            if view is None:
                view = await service.alda(actor)
        elif raw == "s3:detail":
            view = await service.detail(actor)
        elif raw == "s3:alda":
            view = await service.alda(actor)
        elif raw == "s3:abandon":
            view = await service.abandon_confirmation(actor)
        elif len(parts) >= 3:
            try:
                version = int(parts[1])
            except ValueError:
                version = None
            operation = parts[2]
            if version is not None:
                if operation in {"accept", "reaccept"} and len(parts) == 3:
                    view = await service.accept(actor, version, reaccept=operation == "reaccept")
                elif operation == "route" and len(parts) == 3:
                    view = await service.interact(actor, version, "route")
                elif operation == "track" and len(parts) == 4:
                    try:
                        index = int(parts[3])
                    except ValueError:
                        index = 0
                    if 1 <= index <= len(S3_TRACKS):
                        view = await service.interact(actor, version, "track", S3_TRACKS[index - 1])
                elif operation == "retry" and len(parts) == 3:
                    view = await service.retry(actor, version)
                elif operation == "group" and len(parts) == 3:
                    try:
                        view = await service.propose_group_combat(actor, version)
                    except GroupError:
                        await query.answer(
                            "Não foi possível preparar o Grupo.", show_alert=True
                        )
                        return
                elif operation == "solo" and len(parts) == 3:
                    view = await service.start_solo_combat(actor, version)
                elif operation in {"cargo", "report"} and len(parts) == 3:
                    view = await service.interact(actor, version, operation)
                elif operation == "track" and len(parts) == 3:
                    view = await service.toggle_tracking(actor, version)
                elif operation == "abandon" and len(parts) == 4 and parts[3] == "confirm":
                    view = await service.abandon(actor, version)
        if view is None:
            view = await service.resume(actor)
            if view is None and raw not in {"s3:resume", "s3:offer", "s3:alda"}:
                view = await service.alda(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s3(view), images, edit=True)

    return router
