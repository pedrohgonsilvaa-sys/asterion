"""Intent-only Telegram callbacks for S5."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s5 import S5_LIGHT_POINTS, S5Service
from asterion.bot.combat_ui import S5CombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.s5_ui import render_s5


def s5_router(service: S5Service, images: dict[str, str]) -> Router:
    router = Router(name="s5")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("s5:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw == "s5:offer":
            view = await service.offer(actor)
        elif raw == "s5:resume":
            view = await service.resume(actor)
            if view is None:
                view = await service.oren(actor)
        elif raw == "s5:detail":
            view = await service.detail(actor)
        elif raw == "s5:oren":
            view = await service.oren(actor)
        elif raw == "s5:abandon":
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
                elif operation == "light" and len(parts) == 4:
                    try:
                        index = int(parts[3])
                    except ValueError:
                        index = 0
                    if 1 <= index <= len(S5_LIGHT_POINTS):
                        view = await service.action(
                            actor, version, "light_point", S5_LIGHT_POINTS[index - 1]
                        )
                elif (
                    operation in {"investigate", "record", "report", "retry", "track"}
                    and len(parts) == 3
                ):
                    if operation == "retry":
                        view = await service.retry(actor, version)
                    elif operation == "track":
                        view = await service.toggle_tracking(actor, version)
                    else:
                        view = await service.action(actor, version, operation)
                elif operation == "abandon" and len(parts) == 4 and parts[3] == "confirm":
                    view = await service.abandon(actor, version)
        if view is None:
            view = await service.resume(actor)
            if view is None and raw not in {"s5:resume", "s5:offer", "s5:oren"}:
                view = await service.oren(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s5(view), images, edit=True)

    @router.callback_query(F.data.startswith("s5fight:"))
    async def combat(query: CallbackQuery):
        try:
            data = S5CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await service.action_combat(
            query.from_user.id, data.activity_id, data.version, data.action
        )
        if view is None:
            view = await service.resume(query.from_user.id)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s5(view), images, edit=True)

    return router
