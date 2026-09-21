from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import CallbackQuery, Message

from asterion.application.p1 import P1Service
from asterion.bot.combat_ui import CombatCallback, P1CombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.p1_ui import render_p1


def p1_router(service: P1Service, images: dict[str, str]) -> Router:
    router = Router(name="p1")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query, view):
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p1(view), images, edit=True)

    @router.callback_query(F.data.startswith("p1fight:"))
    async def fight(query: CallbackQuery):
        try:
            cb = P1CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await service.action(query.from_user.id, cb.activity_id, cb.version, cb.action)
        await show(query, view)

    @router.callback_query(F.data.startswith("fight:"))
    async def shared_fight(query: CallbackQuery):
        """Route legacy fight callbacks to P1 only when their activity is P1."""
        try:
            cb = CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await service.action(query.from_user.id, cb.activity_id, cb.version, cb.action)
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("p1:"))
    async def mutate(query: CallbackQuery):
        parts = query.data.split(":")
        if len(parts) < 3:
            await query.answer()
            return
        try:
            version = int(parts[1])
        except ValueError:
            await query.answer()
            return
        action = parts[2]
        actor = query.from_user.id
        if action == "follow":
            view = await service.follow_road(actor, version)
        elif action == "examine" and len(parts) == 4:
            view = await service.examine(actor, parts[3], version)
        elif action == "retry":
            view = await service.retry(actor, version)
        elif action == "refuge":
            view = await service.enter_refuge(actor, version)
        elif action == "alda":
            view = await service.follow_alda(actor, version)
        elif action == "oren":
            view = await service.go_brazier(actor, version)
        elif action == "activate":
            view = await service.activate_brazier(actor, version)
        else:
            view = await service.resume(actor)
        await show(query, view)

    return router
