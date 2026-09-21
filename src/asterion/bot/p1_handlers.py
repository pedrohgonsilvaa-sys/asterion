from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.p1 import P1Service
from asterion.bot.creation_handlers import present
from asterion.bot.p1_ui import render_p1


def p1_router(service: P1Service, images: dict[str, str]) -> Router:
    router = Router(name="p1")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view):
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p1(view), images, edit=True)

    @router.callback_query(F.data == "p1:follow")
    async def follow(query: CallbackQuery):
        await show(query, await service.follow_road(query.from_user.id, 0))

    @router.callback_query(F.data.startswith("p1:examine:"))
    async def examine(query: CallbackQuery):
        signal = query.data.rsplit(":", 1)[-1]
        current = await service.resume(query.from_user.id)
        await show(
            query,
            await service.examine(
                query.from_user.id, signal, current.state_version if current else -1
            ),
        )

    return router
