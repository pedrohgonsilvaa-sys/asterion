"""Telegram callbacks for cosmetic collection and selection."""

from dataclasses import replace

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.cosmetic_catalog import COSMETICS
from asterion.application.cosmetics import CosmeticMutationRejected, CosmeticService
from asterion.bot.cosmetics_ui import (
    DEFAULT_CODES,
    TYPE_BY_CODE,
    TYPE_CODES,
    render_cosmetic_category,
    render_cosmetic_detail,
    render_cosmetic_initial,
    render_cosmetics_root,
)
from asterion.bot.creation_handlers import present
from asterion.bot.media import visual_image_key


def _expected(token: str) -> str | None:
    if token == "0":
        return None
    index = int(token) - 1
    if not 0 <= index < len(COSMETICS):
        raise ValueError
    return COSMETICS[index].cosmetic_id


def cosmetics_router(service: CosmeticService, images: dict[str, str]) -> Router:
    router = Router(name="character_cosmetics")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, screen: str, key: str = "", page: int = 0) -> None:
        if not isinstance(query.message, Message):
            return
        view = await service.view(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if screen == "category" and key in TYPE_BY_CODE:
            category = next(
                item for item in view.categories if item.cosmetic_type == TYPE_BY_CODE[key]
            )
            rendered = render_cosmetic_category(category, view, page)
        elif screen == "detail" and key in DEFAULT_CODES:
            rendered = render_cosmetic_initial(view, key)
        elif screen == "detail":
            index = int(key) if key.isdecimal() else -1
            rendered = render_cosmetic_detail(view, index)
            if 0 <= index < len(COSMETICS):
                cosmetic_id = COSMETICS[index].cosmetic_id
                owned = any(
                    item.cosmetic_id == cosmetic_id
                    for category in view.categories
                    for item in (*category.items, *(filter(None, [category.selected])))
                )
                image = visual_image_key(images, cosmetic_id=cosmetic_id) if owned else None
                if image:
                    rendered = replace(rendered, image_key=image)
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
        action = parts[1] if len(parts) > 1 else ""
        if parts == ["cos", "r"]:
            await query.answer()
            await show(query, "root")
            return
        if action == "c" and len(parts) in {3, 4} and parts[2] in TYPE_BY_CODE:
            page = int(parts[3]) if len(parts) == 4 and parts[3].isdecimal() else 0
            await query.answer()
            await show(query, "category", parts[2], page)
            return
        if action == "d" and len(parts) == 3:
            key = parts[2]
            if key not in DEFAULT_CODES and not (
                key.isdecimal() and 0 <= int(key) < len(COSMETICS)
            ):
                await query.answer("A coleção foi atualizada.", show_alert=True)
                await show(query, "root")
                return
            await query.answer()
            await show(query, "detail", key)
            return
        if action == "u" and len(parts) == 4:
            key = parts[2]
            try:
                expected_id = _expected(parts[3])
                if key in DEFAULT_CODES:
                    kind = DEFAULT_CODES[key]
                    result = await service.select_default(query.from_user.id, kind, expected_id)
                else:
                    index = int(key)
                    if not 0 <= index < len(COSMETICS):
                        raise ValueError
                    kind = COSMETICS[index].cosmetic_type
                    result = await service.select(
                        query.from_user.id, COSMETICS[index].cosmetic_id, expected_id
                    )
            except (ValueError, IndexError, CosmeticMutationRejected):
                await query.answer("A seleção foi atualizada.", show_alert=True)
                await show(query, "root")
                return
            await query.answer("Em uso." if result is not None and not result.changed else None)
            await show(query, "category", TYPE_CODES[kind])
            return
        await query.answer("A tela foi atualizada.", show_alert=True)
        await show(query, "root")

    return router
