"""Intent-only aiogram adapter for authoritative Foreground combat."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.prologue import PrologueService
from asterion.bot.combat_ui import CombatCallback, render_combat
from asterion.bot.creation_handlers import present


def combat_router(service: PrologueService, images: dict[str, str]) -> Router:
    router = Router(name="foreground_combat")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data == "prologue:continue")
    async def enter(query: CallbackQuery):
        view = await service.enter(query.from_user.id)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_combat(view), images, edit=True)

    @router.callback_query(F.data.startswith("fight:"))
    async def action(query: CallbackQuery):
        try:
            data = CombatCallback.unpack(query.data or "")
            activity_id = data.activity_id
        except (ValueError, TypeError):
            await query.answer()
            return
        view = await service.action(query.from_user.id, activity_id, data.version, data.action)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_combat(view), images, edit=True)

    return router
