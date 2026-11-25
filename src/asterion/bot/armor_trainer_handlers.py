"""Telegram routes for the Armaduras tab of the Treinador."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.armor_proficiency import ArmorTrainerService
from asterion.bot.armor_trainer_ui import (
    REJECTION_TEXT,
    render_armor_class,
    render_armor_trainer,
)
from asterion.bot.creation_handlers import present
from asterion.domain.armor_proficiency import parse_armor_class


def armor_trainer_router(service: ArmorTrainerService, images: dict[str, str]) -> Router:
    router = Router(name="armor_trainer")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data == "apt:root")
    async def armor_root(query: CallbackQuery):
        await query.answer()
        view = await service.view(query.from_user.id)
        if view is None or not isinstance(query.message, Message):
            return
        await present(query.message, render_armor_trainer(view), images, edit=True)

    @router.callback_query(F.data.startswith("apt:c:"))
    async def armor_class_screen(query: CallbackQuery):
        await query.answer()
        view = await service.view(query.from_user.id)
        armor_class = parse_armor_class(query.data.removeprefix("apt:c:"))
        if view is None or not isinstance(query.message, Message):
            return
        if armor_class is None:
            await present(query.message, render_armor_trainer(view), images, edit=True)
            return
        await present(query.message, render_armor_class(view, armor_class), images, edit=True)

    @router.callback_query(F.data.startswith("apt:ok:"))
    async def armor_learn(query: CallbackQuery):
        value = query.data.removeprefix("apt:ok:")
        outcome = await service.learn(query.from_user.id, value)
        if outcome is None or not isinstance(query.message, Message):
            await query.answer()
            return
        armor_class = parse_armor_class(value)
        notice = None
        if outcome.learned or outcome.already_owned:
            await query.answer()
        else:
            notice = REJECTION_TEXT[outcome.reason]
            await query.answer(notice, show_alert=True)
        if armor_class is None:
            await present(query.message, render_armor_trainer(outcome.view), images, edit=True)
            return
        await present(
            query.message, render_armor_class(outcome.view, armor_class, notice), images, edit=True
        )

    return router
