"""Telegram routes for character status, profile, Bestiary, Codex, and Feats."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import CallbackQuery, Message

from asterion.application.character_surfaces import (
    MAX_HISTORY_CHARACTERS,
    CharacterSurfacesService,
    HistoryInputResult,
)
from asterion.application.knowledge_catalog import ACHIEVEMENTS
from asterion.bot.character_surfaces_ui import (
    ACHIEVEMENT_CATEGORY_BY_KEY,
    CODEX_CATEGORY_BY_KEY,
    CODEX_ENTRY_BY_KEY,
    render_achievement_category,
    render_achievement_detail,
    render_achievement_root,
    render_attributes,
    render_bestiary_detail,
    render_bestiary_region,
    render_bestiary_root,
    render_codex_category,
    render_codex_detail,
    render_codex_region,
    render_codex_root,
    render_history,
    render_profile,
)
from asterion.bot.character_ui import render_character
from asterion.bot.creation_handlers import present
from asterion.bot.text_prompt import (
    PROMPTS,
    HasPrompt,
    PendingPrompt,
    consume_reply,
    show_on_prompt,
)

HISTORY_PROMPT_KIND = "profile:history"
HISTORY_ERRORS = {
    HistoryInputResult.TOO_LONG: (
        f"⚠️ A História pode ter até {MAX_HISTORY_CHARACTERS} caracteres."
    ),
    HistoryInputResult.FORBIDDEN: "⚠️ A História não pode ter links nem menções.",
    HistoryInputResult.EMPTY: "⚠️ A História está vazia.",
}


def _parse_base36(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid version")
    return int(value, 36)


def character_surfaces_router(service: CharacterSurfacesService, images: dict[str, str]) -> Router:
    router = Router(name="character_surfaces")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show_profile(query: CallbackQuery, *, edit: bool = True) -> None:
        if not isinstance(query.message, Message):
            return
        view = await service.profile(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        await present(query.message, render_profile(view), images, edit=edit)

    async def show_knowledge(
        query: CallbackQuery, screen: str, key: str | None = None, page: int = 0
    ) -> None:
        if not isinstance(query.message, Message):
            return
        view = await service.knowledge(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if screen == "codex":
            rendered = render_codex_root(view)
        elif screen == "category":
            rendered = render_codex_category(view, CODEX_CATEGORY_BY_KEY.get(key or "", ""))
        elif screen == "region":
            rendered = render_codex_region(view, key or "")
        elif screen == "location":
            entry_id = CODEX_ENTRY_BY_KEY.get(key or "")
            entry = next(
                (
                    entry
                    for entry in view.codex_entries
                    if entry.entry_id == entry_id and entry.location_id is not None
                ),
                None,
            )
            rendered = (
                render_codex_detail(view, entry)
                if entry is not None
                else render_codex_category(view, "regions")
            )
        elif screen == "entry":
            entry_id = CODEX_ENTRY_BY_KEY.get(key or "")
            entry = next(
                (entry for entry in view.codex_entries if entry.entry_id == entry_id),
                None,
            )
            rendered = render_codex_detail(view, entry) if entry else render_codex_root(view)
        elif screen == "bestiary":
            rendered = render_bestiary_root(view)
        elif screen == "bestiary_region":
            rendered = render_bestiary_region(view, key or "")
        elif screen == "creature":
            creature_key = key or ""
            record = next(
                (
                    record
                    for record in view.bestiary
                    if record.creature_id.replace("-", "_") == creature_key
                ),
                None,
            )
            rendered = (
                render_bestiary_detail(view, record) if record else render_bestiary_root(view)
            )
        elif screen == "achievements":
            rendered = render_achievement_root(view)
        elif screen == "achievement_category":
            rendered = render_achievement_category(
                view, ACHIEVEMENT_CATEGORY_BY_KEY.get(key or "", ""), page
            )
        elif screen == "achievement":
            try:
                achievement_id = ACHIEVEMENTS[int(key or "", 36)].achievement_id
            except (ValueError, IndexError):
                achievement_id = ""
            rendered = render_achievement_detail(view, achievement_id)
        else:
            rendered = render_codex_root(view)
        await present(query.message, rendered, images, edit=True)

    @router.callback_query(F.data == "character:root")
    async def open_character_root(query: CallbackQuery) -> None:
        await service.cancel_history_input(query.from_user.id)
        await query.answer()
        if isinstance(query.message, Message):
            view = await service.identity(query.from_user.id)
            stats = await service.attributes(query.from_user.id)
            await present(query.message, render_character(view, stats), images, edit=True)

    @router.callback_query(F.data == "character:attributes")
    async def open_attributes(query: CallbackQuery) -> None:
        await service.cancel_history_input(query.from_user.id)
        view = await service.attributes(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_attributes(view), images, edit=True)

    @router.callback_query(F.data == "character:profile")
    async def open_profile(query: CallbackQuery) -> None:
        await service.cancel_history_input(query.from_user.id)
        await query.answer()
        await show_profile(query)

    @router.callback_query(F.data.startswith("profile:edit:"))
    async def edit_history(query: CallbackQuery) -> None:
        """✍️ Escrever: a própria tela entra no estado de entrada de texto (Parte IV §1)."""
        parts = (query.data or "").split(":")
        if len(parts) != 3 or not isinstance(query.message, Message):
            await query.answer("A História foi atualizada.", show_alert=True)
            return
        try:
            expected_revision = _parse_base36(parts[2])
        except ValueError:
            await query.answer("A História foi atualizada.", show_alert=True)
            await show_profile(query)
            return
        current = await service.profile(query.from_user.id)
        if current is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        started = current.revision == expected_revision and await service.begin_history_input(
            query.from_user.id, expected_revision, query.message.message_id
        )
        if not started:
            await query.answer("A História foi atualizada.", show_alert=True)
            await present(query.message, render_history(current), images, edit=True)
            return
        await query.answer()
        await present(query.message, render_history(current, writing=True), images, edit=True)
        PROMPTS.open(query.from_user.id, HISTORY_PROMPT_KIND, query.message)

    @router.message(F.text, HasPrompt(HISTORY_PROMPT_KIND))
    async def history_reply(message: Message, prompt: PendingPrompt) -> None:
        actor = message.from_user.id
        await consume_reply(message)
        result = await service.save_history(actor, prompt.message_id, message.text or "")
        notice = HISTORY_ERRORS.get(result)
        view = await service.profile(actor)
        if view is None:
            PROMPTS.close(actor)
            return
        if notice is not None:
            # Fica no estado de entrada, na mesma tela, com o aviso.
            await show_on_prompt(
                message, prompt, render_history(view, writing=True, notice=notice), images
            )
            PROMPTS.follow(actor, prompt)
            return
        PROMPTS.close(actor)
        await show_on_prompt(message, prompt, render_history(view), images)

    @router.message(F.text.startswith("/"))
    async def pass_commands(message: Message) -> None:
        if message.from_user is not None:
            await service.cancel_history_input(message.from_user.id)
        raise SkipHandler()

    @router.callback_query(F.data == "knowledge:codex")
    async def open_codex(query: CallbackQuery) -> None:
        await service.cancel_history_input(query.from_user.id)
        await query.answer()
        await show_knowledge(query, "codex")

    @router.callback_query(F.data.startswith("kb:"))
    async def knowledge_navigation(query: CallbackQuery) -> None:
        await service.cancel_history_input(query.from_user.id)
        parts = (query.data or "").split(":")
        if len(parts) == 2 and parts[1] == "cd":
            await query.answer()
            await show_knowledge(query, "codex")
            return
        if len(parts) == 2 and parts[1] == "b":
            await query.answer()
            await show_knowledge(query, "bestiary")
            return
        if len(parts) == 2 and parts[1] == "a":
            await query.answer()
            await show_knowledge(query, "achievements")
            return
        if len(parts) == 4 and parts[1] == "ac" and parts[3].isdecimal():
            await query.answer()
            await show_knowledge(query, "achievement_category", parts[2], int(parts[3]))
            return
        if len(parts) != 3:
            await query.answer("A tela foi atualizada.")
            await show_knowledge(query, "codex")
            return
        action, key = parts[1], parts[2]
        route = {
            "c": ("category",),
            "r": ("region",),
            "l": ("location",),
            "e": ("entry",),
            "br": ("bestiary_region",),
            "be": ("creature",),
            "ac": ("achievement_category",),
            "ae": ("achievement",),
        }
        if action not in route:
            await query.answer("A tela foi atualizada.")
            await show_knowledge(query, "codex")
            return
        screen = route[action][0]
        await query.answer()
        await show_knowledge(query, screen, key)

    return router
