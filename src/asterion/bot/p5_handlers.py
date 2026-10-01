"""Intent-only Telegram callbacks for P5."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.p5 import P5_ELEMENTS, P5Service
from asterion.application.p6 import P6Service
from asterion.bot.creation_handlers import present
from asterion.bot.p5_ui import render_p5
from asterion.bot.p6_ui import render_p6


def p5_router(service: P5Service, images: dict[str, str], *, p6: P6Service | None = None) -> Router:
    router = Router(name="p5")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("p5:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw == "p5:offer":
            view = await service.offer(actor)
        elif raw == "p5:resume" or raw == "p5:detail":
            view = await service.resume(actor)
            if view is None:
                view = await service.offer(actor)
        elif raw == "p5:alda":
            view = await service.alda(actor)
        elif raw == "p5:oren":
            view = await service.oren(actor)
        elif len(parts) >= 3:
            try:
                version = int(parts[1])
            except ValueError:
                version = None
            operation = parts[2]
            if version is not None:
                if operation == "accept" and len(parts) == 3:
                    view = await service.accept(actor, version)
                elif operation == "follow" and len(parts) == 3:
                    view = await service.action(actor, version, "follow_structures")
                elif operation == "door" and len(parts) == 3:
                    view = await service.action(actor, version, "find_door")
                elif operation == "retry" and len(parts) == 3:
                    view = await service.action(actor, version, "retry")
                elif operation == "symbol" and len(parts) == 3:
                    view = await service.action(actor, version, "record_symbol")
                elif operation == "element" and len(parts) == 4:
                    try:
                        index = int(parts[3])
                    except ValueError:
                        index = 0
                    if 1 <= index <= len(P5_ELEMENTS):
                        view = await service.action(
                            actor, version, "element", P5_ELEMENTS[index - 1]
                        )
                elif operation == "report" and len(parts) == 4:
                    person = parts[3]
                    if person in {"alda", "oren"}:
                        view = await service.action(actor, version, f"report_{person}")

        if view is None:
            view = await service.resume(actor)
            if view is None and raw not in {"p5:offer", "p5:resume", "p5:detail"}:
                view = await service.offer(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            p6_view = (
                await p6.resume(actor)
                if p6 is not None and view.status == "completed"
                else None
            )
            screen = (
                render_p6(p6_view)
                if p6_view is not None and p6_view.status == "active"
                else render_p5(view)
            )
            await present(query.message, screen, images, edit=True)

    return router
