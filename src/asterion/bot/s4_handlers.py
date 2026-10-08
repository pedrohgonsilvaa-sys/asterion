"""Intent-only Telegram callbacks for S4."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.s4 import S4_WATCH_POINTS, S4Service
from asterion.bot.combat_ui import S4CombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.s4_ui import render_s4


def s4_router(service: S4Service, images: dict[str, str]) -> Router:
    router = Router(name="s4")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("s4:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw == "s4:offer":
            view = await service.offer(actor)
        elif raw == "s4:resume":
            view = await service.resume(actor)
            if view is None:
                view = await service.oren(actor)
        elif raw == "s4:detail":
            view = await service.detail(actor)
        elif raw == "s4:oren":
            view = await service.oren(actor)
        elif raw == "s4:abandon":
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
                elif operation == "watch" and len(parts) == 4:
                    try:
                        index = int(parts[3])
                    except ValueError:
                        index = 0
                    if 1 <= index <= len(S4_WATCH_POINTS):
                        view = await service.action(
                            actor, version, "watch", S4_WATCH_POINTS[index - 1]
                        )
                elif (
                    operation in {"orientation", "turn", "examine", "report", "retry", "track"}
                    and len(parts) == 3
                ):
                    action = {"turn": "turn_point"}.get(operation, operation)
                    if action == "retry":
                        view = await service.retry(actor, version)
                    elif action == "track":
                        view = await service.toggle_tracking(actor, version)
                    else:
                        view = await service.action(actor, version, action)
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
                elif operation == "abandon" and len(parts) == 4 and parts[3] == "confirm":
                    view = await service.abandon(actor, version)
        if view is None:
            view = await service.resume(actor)
            if view is None and raw not in {"s4:resume", "s4:offer", "s4:oren"}:
                view = await service.oren(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s4(view), images, edit=True)

    @router.callback_query(F.data.startswith("s4fight:"))
    async def combat(query: CallbackQuery):
        try:
            data = S4CombatCallback.unpack(query.data or "")
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
            await present(query.message, render_s4(view), images, edit=True)

    return router
