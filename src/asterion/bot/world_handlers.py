from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.p1 import P1Service
from asterion.application.world import WorldService
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.p1_ui import render_p1
from asterion.bot.world_ui import render_world


def world_router(
    service: WorldService, images: dict[str, str], p1: P1Service | None = None
) -> Router:
    router = Router(name="world")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(message: Message):
        if p1 is not None:
            p1_view = await p1.resume(message.from_user.id) if message.from_user else None
            if p1_view is not None and p1_view.combat is not None:
                await present(message, render_p1(p1_view), images)
                return
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

    @router.callback_query(F.data == "world:adventure")
    async def adventure(query: CallbackQuery):
        await query.answer()
        if isinstance(query.message, Message):
            screen = Screen(
                "🗺️ Aventura",
                "adventure",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Missões", callback_data="world:missions")],
                        [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
                    ]
                ),
            )
            await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data == "world:missions")
    async def missions(query: CallbackQuery):
        await query.answer()
        if isinstance(query.message, Message):
            screen = Screen(
                "📜 Missões",
                "missions",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Principal", callback_data="world:principal")],
                        [InlineKeyboardButton(text="← Aventura", callback_data="world:adventure")],
                    ]
                ),
            )
            await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data == "world:principal")
    async def principal(query: CallbackQuery):
        await query.answer()
        if isinstance(query.message, Message):
            screen = Screen(
                "📜 Vozes na Estrada",
                "mission_p1",
                InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Ver Objetivo", callback_data="world:objective"
                            )
                        ],
                        [InlineKeyboardButton(text="← Missões", callback_data="world:missions")],
                    ]
                ),
            )
            await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data == "world:objective")
    async def objective(query: CallbackQuery):
        await query.answer()
        if isinstance(query.message, Message) and p1 is not None:
            view = await p1.resume(query.from_user.id)
            if view is not None:
                await present(query.message, render_p1(view), images, edit=True)

    @router.callback_query(F.data.startswith("menu:"))
    async def noop(query: CallbackQuery):
        await query.answer()

    return router
