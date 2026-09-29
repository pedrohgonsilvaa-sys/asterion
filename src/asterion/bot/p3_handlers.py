"""Telegram callbacks for P3; backend views remain the only progress authority."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.p3 import P3_FRAGMENTS, P3Service
from asterion.application.road import CHARNECA, REFUGE
from asterion.application.s3 import S3Service
from asterion.bot.creation_handlers import present
from asterion.bot.p3_ui import render_p3
from asterion.bot.s3_ui import render_s3


def p3_router(
    service: P3Service, images: dict[str, str], *, s3: S3Service | None = None
) -> Router:
    router = Router(name="p3")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("p3:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw == "p3:oren":
            view = await service.oren(actor)
        elif raw == "p3:offer":
            view = await service.offer(actor)
        elif raw == "p3:resume":
            view = await service.resume(actor)
            if view is None:
                view = await service.oren(actor)
        elif len(parts) == 4 and parts[1] == "s3route":
            try:
                s3_version = int(parts[2])
            except ValueError:
                s3_version = None
            destination = {
                "refuge": REFUGE,
                "charneca": CHARNECA,
                "bosque": "Bosque Calcinado",
            }.get(parts[3])
            if s3_version is not None and destination is not None:
                await service.s3_campaign_route(actor, s3_version, destination)
                s3_view = await s3.resume(actor) if s3 is not None else None
                if s3_view is not None:
                    await query.answer()
                    if isinstance(query.message, Message):
                        await present(query.message, render_s3(s3_view), images, edit=True)
                    return
                view = await service.resume(actor)
        elif len(parts) >= 3:
            try:
                version = int(parts[1])
            except ValueError:
                version = None
            operation = parts[2]
            if version is not None:
                if operation == "accept" and len(parts) == 3:
                    view = await service.accept(actor, version)
                elif operation == "route" and len(parts) == 4:
                    destination = {"charneca": CHARNECA, "refuge": REFUGE}.get(parts[3])
                    if destination is not None:
                        view = await service.mission_route(actor, version, destination)
                elif operation == "enter" and len(parts) == 3:
                    view = await service.enter_bosque(actor, version)
                elif operation == "fragment" and len(parts) == 4:
                    try:
                        index = int(parts[3])
                    except ValueError:
                        index = 0
                    if 1 <= index <= len(P3_FRAGMENTS):
                        view = await service.examine_fragment(
                            actor, P3_FRAGMENTS[index - 1], version
                        )
                elif operation == "retry" and len(parts) == 3:
                    view = await service.retry(actor, version)
                elif operation == "carved" and len(parts) == 3:
                    view = await service.examine_carved_fragment(actor, version)
                elif operation == "oren" and len(parts) == 3:
                    view = await service.talk_to_oren(actor, version)
                elif operation == "choose" and len(parts) == 4:
                    view = await service.choose_reward(actor, version, parts[3])

        if view is None:
            view = await service.resume(actor)
            if view is None and raw not in {"p3:resume", "p3:oren", "p3:offer"}:
                view = await service.oren(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p3(view), images, edit=True)

    return router
