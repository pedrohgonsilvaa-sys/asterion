"""Telegram routes for the Treinador de Armas."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.weapon_proficiency import WeaponTrainerService
from asterion.bot.creation_handlers import present
from asterion.bot.weapon_trainer_ui import (
    REJECTION_TEXT,
    render_weapon_family,
    render_weapon_trainer,
)
from asterion.domain.weapon_proficiency import ProficiencyFamily, parse_family


def weapon_trainer_router(service: WeaponTrainerService, images: dict[str, str]) -> Router:
    router = Router(name="weapon_trainer")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data == "wpt:root")
    async def trainer_root(query: CallbackQuery):
        await query.answer()
        view = await service.view(query.from_user.id)
        if view is None or not isinstance(query.message, Message):
            return
        await present(query.message, render_weapon_trainer(view), images, edit=True)

    async def family_screen(query: CallbackQuery, family, notice: str | None = None):
        view = await service.view(query.from_user.id)
        if view is None or not isinstance(query.message, Message):
            return
        if family is None or family not in {entry.family for entry in view.entries}:
            await present(query.message, render_weapon_trainer(view), images, edit=True)
            return
        await present(
            query.message, render_weapon_family(view, family, notice), images, edit=True
        )

    @router.callback_query(F.data.startswith("wpt:c:"))
    async def trainer_family(query: CallbackQuery):
        await query.answer()
        await family_screen(query, parse_family(query.data.removeprefix("wpt:c:")))

    @router.callback_query(F.data == "wpt:shield")
    async def trainer_shield(query: CallbackQuery):
        await query.answer()
        await family_screen(query, ProficiencyFamily.SHIELD)

    @router.callback_query(F.data.startswith("wpt:ok:"))
    async def trainer_learn(query: CallbackQuery):
        outcome = await service.learn(query.from_user.id, query.data.removeprefix("wpt:ok:"))
        if outcome is None or not isinstance(query.message, Message):
            await query.answer()
            return
        family = parse_family(query.data.removeprefix("wpt:ok:"))
        notice = None
        if outcome.learned or outcome.already_owned:
            await query.answer()
        else:
            notice = REJECTION_TEXT[outcome.reason]
            await query.answer(notice, show_alert=True)
        if family is None:
            await present(query.message, render_weapon_trainer(outcome.view), images, edit=True)
            return
        await present(
            query.message, render_weapon_family(outcome.view, family, notice), images, edit=True
        )

    return router
