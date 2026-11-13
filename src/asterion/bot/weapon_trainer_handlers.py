"""Telegram routes for the Treinador de Armas."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.weapon_proficiency import WeaponTrainerService
from asterion.bot.creation_handlers import present
from asterion.bot.weapon_trainer_ui import (
    REJECTION_TEXT,
    render_weapon_trainer,
    render_weapon_trainer_confirm,
)
from asterion.domain.weapon_proficiency import FAMILY_LABELS, parse_family


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

    @router.callback_query(F.data.startswith("wpt:c:"))
    async def trainer_confirm(query: CallbackQuery):
        await query.answer()
        view = await service.view(query.from_user.id)
        family = parse_family(query.data.removeprefix("wpt:c:"))
        if view is None or not isinstance(query.message, Message):
            return
        if family is None or family not in {entry.family for entry in view.entries}:
            await present(query.message, render_weapon_trainer(view), images, edit=True)
            return
        await present(
            query.message, render_weapon_trainer_confirm(view, family), images, edit=True
        )

    @router.callback_query(F.data.startswith("wpt:ok:"))
    async def trainer_learn(query: CallbackQuery):
        outcome = await service.learn(query.from_user.id, query.data.removeprefix("wpt:ok:"))
        if outcome is None or not isinstance(query.message, Message):
            await query.answer()
            return
        family = parse_family(query.data.removeprefix("wpt:ok:"))
        if outcome.learned and family is not None:
            notice = f"Proficiência aprendida: {FAMILY_LABELS[family]}."
            await query.answer(notice)
        elif outcome.already_owned:
            notice = "Você já possui essa Proficiência."
            await query.answer(notice)
        else:
            notice = REJECTION_TEXT[outcome.reason]
            await query.answer(notice, show_alert=True)
        await present(
            query.message, render_weapon_trainer(outcome.view, notice), images, edit=True
        )

    return router
