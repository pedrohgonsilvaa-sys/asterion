"""Intent-only Telegram callbacks for P4."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.p4 import P4_STRUCTURES, P4Service
from asterion.bot.creation_handlers import present
from asterion.bot.p4_ui import render_p4


def p4_router(service: P4Service, images: dict[str, str]) -> Router:
    router = Router(name="p4")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("p4:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw == "p4:offer":
            view = await service.offer(actor)
        elif raw == "p4:resume":
            view = await service.resume(actor)
            if view is None:
                view = await service.alda(actor)
        elif raw == "p4:alda":
            view = await service.alda(actor)
        elif len(parts) >= 3:
            try:
                version = int(parts[1])
            except ValueError:
                version = None
            operation = parts[2]
            if version is not None:
                if operation == "accept" and len(parts) == 3:
                    view = await service.accept(actor, version)
                elif operation == "structure" and len(parts) == 4:
                    try:
                        index = int(parts[3])
                    except ValueError:
                        index = 0
                    if 1 <= index <= len(P4_STRUCTURES):
                        view = await service.action(
                            actor, version, "structure", P4_STRUCTURES[index - 1]
                        )
                elif operation == "report" and len(parts) == 4:
                    view = await service.action(actor, version, f"report_{parts[3]}")
                elif operation in {"path", "enter", "retry", "safe", "return"} and len(parts) == 3:
                    action = {"safe": "safe_route"}.get(operation, operation)
                    view = await service.action(actor, version, action)
        if view is None:
            view = await service.resume(actor)
            if view is None and raw not in {"p4:resume", "p4:offer", "p4:alda"}:
                view = await service.alda(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p4(view), images, edit=True)

    return router
