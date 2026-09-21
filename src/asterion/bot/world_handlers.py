from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from asterion.application.world import WorldService
from asterion.bot.creation_handlers import present
from asterion.bot.world_ui import render_world


def world_router(service: WorldService, images: dict[str, str]) -> Router:
    router = Router(name="world")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(message: Message):
        view = await service.resume(message.from_user.id) if message.from_user else None
        if view:
            await present(message, render_world(view), images)

    @router.message(Command("menu"))
    async def menu(message: Message):
        await show(message)

    @router.callback_query(F.data == "world:rest")
    async def rest(query: CallbackQuery):
        view = await service.rest(query.from_user.id)
        await query.answer()
        if view and isinstance(query.message, Message):
            await present(query.message, render_world(view), images, edit=True)

    @router.callback_query(F.data.startswith("menu:"))
    async def noop(query: CallbackQuery):
        await query.answer()

    return router
