"""Telegram callbacks for cosmetic collection and selection."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.cosmetic_catalog import COSMETIC_TYPES, COSMETICS
from asterion.application.cosmetics import CosmeticMutationRejected, CosmeticService
from asterion.bot.cosmetics_ui import (
    TYPE_BY_CODE,
    render_cosmetic_category,
    render_cosmetic_detail,
    render_cosmetics_root,
)
from asterion.bot.creation_handlers import present


def cosmetics_router(service: CosmeticService, images: dict[str, str]) -> Router:
    router = Router(name="character_cosmetics")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, screen: str, key: str | None = None) -> None:
        if not isinstance(query.message, Message):
            return
        view = await service.view(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if screen == "category":
            kind = TYPE_BY_CODE.get(key or "")
            category = next((item for item in view.categories if item.cosmetic_type == kind), None)
            rendered = (
                render_cosmetic_category(category) if category else render_cosmetics_root(view)
            )
        elif screen == "detail":
            try:
                index = int(key or "")
            except ValueError:
                index = -1
            rendered = render_cosmetic_detail(view, index)
        else:
            rendered = render_cosmetics_root(view)
        await present(query.message, rendered, images, edit=True)

    @router.callback_query(F.data == "character:cosmetics")
    async def open_root(query: CallbackQuery) -> None:
        await query.answer()
        await show(query, "root")

    @router.callback_query(F.data.startswith("cos:"))
    async def navigate(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) == 2 and parts[1] == "r":
            await query.answer()
            await show(query, "root")
            return
        if len(parts) == 3 and parts[1] == "c" and parts[2] in TYPE_BY_CODE:
            await query.answer()
            await show(query, "category", parts[2])
            return
        if len(parts) == 3 and parts[1] == "d":
            try:
                index = int(parts[2])
                if not 0 <= index < len(COSMETICS):
                    raise ValueError
            except ValueError:
                await query.answer("A coleção foi atualizada.", show_alert=True)
                await show(query, "root")
                return
            await query.answer()
            await show(query, "detail", parts[2])
            return
        if len(parts) == 4 and parts[1] == "u":
            try:
                index, expected_token = int(parts[2]), parts[3]
                if not 0 <= index < len(COSMETICS):
                    raise ValueError
                expected_id = (
                    None
                    if expected_token == "0"
                    else COSMETICS[int(expected_token) - 1].cosmetic_id
                )
                if expected_token != "0" and not 0 < int(expected_token) <= len(COSMETICS):
                    raise ValueError
                result = await service.select(
                    query.from_user.id, COSMETICS[index].cosmetic_id, expected_id
                )
            except (ValueError, IndexError, CosmeticMutationRejected):
                await query.answer("A seleção foi atualizada.", show_alert=True)
                await show(query, "root")
                return
            await query.answer(
                "Cosmético selecionado." if result and result.changed else "Já selecionado."
            )
            await show(query, "category", str(COSMETIC_TYPES.index(COSMETICS[index].cosmetic_type)))
            return
        await query.answer("A tela foi atualizada.", show_alert=True)
        await show(query, "root")

    return router
