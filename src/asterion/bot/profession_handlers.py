"""Telegram callbacks for Profession slots and previewed C1 Crafting."""

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.crafting import CraftingRejected, CraftingService
from asterion.application.professions import (
    ProfessionMutationRejected,
    ProfessionService,
)
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.professions_ui import (
    render_change_preview,
    render_change_root,
    render_craft_preview,
    render_craft_result,
    render_profession_detail,
    render_profession_home,
    render_profession_initial_primary,
    render_profession_initial_secondary,
    render_recipe_detail,
    render_recipe_list,
    render_replace_profession,
)
from asterion.domain.professions import (
    PROFESSION_BY_ID,
    PROFESSION_IDS,
    RECIPE_DEFINITIONS,
    ProfessionSlot,
)


def profession_router(
    professions: ProfessionService,
    crafting: CraftingService,
    images: dict[str, str],
) -> Router:
    router = Router(name="professions_crafting")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show_home(query: CallbackQuery):
        if not isinstance(query.message, Message):
            return
        view = await professions.view(query.from_user.id)
        if view is not None:
            await present(query.message, render_profession_home(view), images, edit=True)

    async def show_detail(query: CallbackQuery, profession_index: int):
        if not isinstance(query.message, Message) or not 0 <= profession_index < len(
            PROFESSION_IDS
        ):
            return
        home = await professions.view(query.from_user.id)
        if home is None:
            return
        profession_id = PROFESSION_IDS[profession_index]
        progress = next(
            (
                item
                for item in (home.primary, home.secondary)
                if item is not None and item.profession_id == profession_id
            ),
            None,
        )
        can_create = (
            progress is not None and not home.foreground and home.location == "Refúgio do Ocaso"
        )
        screen = render_profession_detail(
            profession_id,
            progress.level if progress else None,
            progress.pxp if progress else 0,
            progress.next_level_pxp if progress else None,
            progress is not None,
            home.foreground,
            can_create=can_create,
        )
        await present(query.message, screen, images, edit=True)

    async def show_recipe_list(query: CallbackQuery, profession_index: int):
        if not isinstance(query.message, Message) or not 0 <= profession_index < len(
            PROFESSION_IDS
        ):
            return
        view = await crafting.recipes(query.from_user.id, PROFESSION_IDS[profession_index])
        if view is not None:
            await present(query.message, render_recipe_list(view), images, edit=True)

    async def show_recipe(query: CallbackQuery, recipe_index: int):
        if not isinstance(query.message, Message) or not 0 <= recipe_index < len(
            RECIPE_DEFINITIONS
        ):
            return
        view = await crafting.recipe(query.from_user.id, RECIPE_DEFINITIONS[recipe_index].recipe_id)
        if view is None:
            await query.answer("Receita indisponível.")
            await show_home(query)
            return
        await present(query.message, render_recipe_detail(view), images, edit=True)

    async def show_craft_root(query: CallbackQuery):
        if not isinstance(query.message, Message):
            return
        home = await professions.view(query.from_user.id)
        if home is None:
            return
        lines = ["🛠️ Criação", ""]
        rows = []
        if home.primary is not None:
            item = home.primary
            lines.append(
                f"1 {PROFESSION_BY_ID[item.profession_id].name} · Principal · Nv.{item.level}"
            )
            rows.append(
                [
                    InlineKeyboardButton(
                        text="1",
                        callback_data=f"craft:recipes:{PROFESSION_IDS.index(item.profession_id)}",
                    )
                ]
            )
        if home.secondary is not None:
            item = home.secondary
            lines.append(
                f"2 {PROFESSION_BY_ID[item.profession_id].name} · Secundário · Nv.{item.level}"
            )
            rows.append(
                [
                    InlineKeyboardButton(
                        text="2",
                        callback_data=f"craft:recipes:{PROFESSION_IDS.index(item.profession_id)}",
                    )
                ]
            )
        if not rows:
            lines.append("Escolha os Ofícios ativos para consultar Criação.")
        rows.append([InlineKeyboardButton(text="← Ofícios", callback_data="prof:root")])
        await present(
            query.message,
            Screen("\n".join(lines), "crafting", InlineKeyboardMarkup(inline_keyboard=rows)),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "character:professions")
    async def open_professions(query: CallbackQuery):
        await query.answer()
        await show_home(query)

    @router.callback_query(F.data == "prof:root")
    async def profession_root(query: CallbackQuery):
        await query.answer()
        await show_home(query)

    @router.callback_query(F.data == "prof:init")
    async def initial_primary(query: CallbackQuery):
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_profession_initial_primary(), images, edit=True)

    @router.callback_query(F.data.startswith("prof:ip:"))
    async def choose_initial_primary(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            index = int(parts[2])
            if len(parts) != 3 or not 0 <= index < len(PROFESSION_IDS):
                raise ValueError
        except ValueError:
            await query.answer("A escolha foi atualizada.")
            await show_home(query)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(
                query.message,
                render_profession_initial_secondary(index),
                images,
                edit=True,
            )

    @router.callback_query(F.data.startswith("prof:is:"))
    async def choose_initial_secondary(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            primary_index, secondary_index = int(parts[2]), int(parts[3])
            primary_id, secondary_id = (
                PROFESSION_IDS[primary_index],
                PROFESSION_IDS[secondary_index],
            )
            if len(parts) != 4 or primary_index == secondary_index:
                raise ValueError
            await professions.initial_selection(query.from_user.id, primary_id, secondary_id)
        except (ValueError, IndexError, ProfessionMutationRejected):
            await query.answer("A escolha de Ofícios não pôde ser aplicada; revise o estado atual.")
            await show_home(query)
            return
        await query.answer()
        await show_home(query)

    @router.callback_query(F.data.startswith("prof:d:"))
    async def profession_detail(query: CallbackQuery):
        try:
            index = int((query.data or "").split(":")[2])
        except (IndexError, ValueError):
            await query.answer("A tela foi atualizada.")
            await show_home(query)
            return
        await query.answer()
        await show_detail(query, index)

    @router.callback_query(F.data == "prof:change")
    async def profession_change_root(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        view = await professions.view(query.from_user.id)
        if view is not None:
            await query.answer()
            await present(query.message, render_change_root(view), images, edit=True)

    @router.callback_query(F.data == "prof:swap")
    async def profession_swap_preview(query: CallbackQuery):
        try:
            preview = await professions.change_preview(query.from_user.id, "swap")
        except ProfessionMutationRejected:
            await query.answer("A tela foi atualizada.")
            await show_home(query)
            return
        await query.answer()
        if preview is not None and isinstance(query.message, Message):
            await present(query.message, render_change_preview(preview), images, edit=True)

    @router.callback_query(F.data.startswith("prof:slot:"))
    async def replace_slot(query: CallbackQuery):
        slot_code = (query.data or "").split(":")[-1]
        slot = (
            ProfessionSlot.PRIMARY.value
            if slot_code == "p"
            else ProfessionSlot.SECONDARY.value
            if slot_code == "s"
            else None
        )
        view = await professions.view(query.from_user.id)
        if view is None or slot is None:
            await query.answer("A tela foi atualizada.")
            await show_home(query)
            return
        current = view.primary if slot == ProfessionSlot.PRIMARY.value else view.secondary
        if current is None:
            await query.answer("A tela foi atualizada.")
            await show_home(query)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(
                query.message,
                render_replace_profession(slot, current.profession_id, view.others),
                images,
                edit=True,
            )

    @router.callback_query(F.data.startswith("prof:replace:"))
    async def profession_replace_preview(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            slot = (
                ProfessionSlot.PRIMARY.value
                if parts[2] == "p"
                else ProfessionSlot.SECONDARY.value
                if parts[2] == "s"
                else None
            )
            profession_id = PROFESSION_IDS[int(parts[3])]
            if len(parts) != 4 or slot is None:
                raise ValueError
            preview = await professions.change_preview(
                query.from_user.id,
                "replace",
                slot=slot,
                profession_id=profession_id,
            )
        except (IndexError, ValueError, ProfessionMutationRejected):
            await query.answer("A tela foi atualizada.")
            await show_home(query)
            return
        await query.answer()
        if preview is not None and isinstance(query.message, Message):
            await present(query.message, render_change_preview(preview), images, edit=True)

    @router.callback_query(F.data.startswith("prof:ok:"))
    async def profession_change_commit(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            if parts[2] == "s" and len(parts) == 4:
                await professions.confirm_change(query.from_user.id, parts[3], "swap")
            elif parts[2] == "r" and len(parts) == 6:
                slot = (
                    ProfessionSlot.PRIMARY.value
                    if parts[3] == "p"
                    else ProfessionSlot.SECONDARY.value
                    if parts[3] == "s"
                    else None
                )
                profession_id = PROFESSION_IDS[int(parts[4])]
                if slot is None:
                    raise ValueError
                await professions.confirm_change(
                    query.from_user.id,
                    parts[5],
                    "replace",
                    slot=slot,
                    profession_id=profession_id,
                )
            else:
                raise ValueError
        except (IndexError, ValueError, ProfessionMutationRejected):
            await query.answer("A confirmação ficou desatualizada; revise a configuração.")
            await show_home(query)
            return
        await query.answer()
        await show_home(query)

    @router.callback_query(F.data == "craft:root")
    async def crafting_root(query: CallbackQuery):
        await query.answer()
        await show_craft_root(query)

    @router.callback_query(F.data.startswith("craft:recipes:"))
    async def crafting_recipes(query: CallbackQuery):
        try:
            index = int((query.data or "").split(":")[-1])
            if not 0 <= index < len(PROFESSION_IDS):
                raise ValueError
        except ValueError:
            await query.answer("A tela foi atualizada.")
            await show_craft_root(query)
            return
        await query.answer()
        await show_recipe_list(query, index)

    @router.callback_query(F.data.startswith("craft:r:"))
    async def recipe_detail(query: CallbackQuery):
        try:
            index = int((query.data or "").split(":")[-1])
            if not 0 <= index < len(RECIPE_DEFINITIONS):
                raise ValueError
        except ValueError:
            await query.answer("A tela foi atualizada.")
            await show_craft_root(query)
            return
        await query.answer()
        await show_recipe(query, index)

    @router.callback_query(F.data.startswith("craft:pv:"))
    async def create_preview(query: CallbackQuery):
        try:
            index = int((query.data or "").split(":")[-1])
            definition = RECIPE_DEFINITIONS[index]
            preview = await crafting.preview(query.from_user.id, definition.recipe_id)
        except (IndexError, ValueError, CraftingRejected):
            await query.answer("A Receita ou o Preview foi atualizado.")
            try:
                await show_recipe(query, int((query.data or "").split(":")[-1]))
            except (ValueError, IndexError):
                await show_craft_root(query)
            return
        await query.answer()
        if preview is not None and isinstance(query.message, Message):
            await present(query.message, render_craft_preview(preview), images, edit=True)

    @router.callback_query(F.data.startswith("craft:cf:"))
    async def commit_craft(query: CallbackQuery):
        try:
            receipt_id = UUID(hex=(query.data or "").split(":")[-1])
            result = await crafting.commit(query.from_user.id, receipt_id)
        except (ValueError, CraftingRejected):
            await query.answer("O Preview expirou ou ficou desatualizado; revise a Receita.")
            await show_craft_root(query)
            return
        await query.answer()
        if result is not None and isinstance(query.message, Message):
            await present(query.message, render_craft_result(result), images, edit=True)

    return router
