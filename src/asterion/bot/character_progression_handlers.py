"""Telegram callbacks for persistent Talent and Active Art configuration."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.active_arts import ActiveArtMutationRejected, ActiveArtService
from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.talents import (
    TalentMutationRejected,
    TalentService,
)
from asterion.bot.character_progression_ui import (
    render_art_detail,
    render_art_root,
    render_art_slot_choice,
    render_talent_detail,
    render_talent_list,
    render_talent_respec,
    render_talent_root,
)
from asterion.bot.creation_handlers import present
from asterion.domain.arts import ART_IDS_BY_CLASS
from asterion.domain.talents import TALENTS_BY_CLASS


def _from_base36(value: str) -> int:
    return int(value, 36)


def _talent_by_index(view, index: int):
    return TALENTS_BY_CLASS[view.character_class][index]


def _art_by_index(view, index: int) -> str:
    return ART_IDS_BY_CLASS[view.character_class][index]


def character_progression_router(
    talents: TalentService,
    active_arts: ActiveArtService,
    images: dict[str, str],
) -> Router:
    router = Router(name="character_progression")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show_talents(query: CallbackQuery, *, screen: str = "root", index: int = 0):
        if not isinstance(query.message, Message):
            return
        view = await talents.view(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if screen == "list":
            rendered = render_talent_list(view)
        elif screen == "detail":
            try:
                rendered = render_talent_detail(view, _talent_by_index(view, index))
            except IndexError:
                rendered = render_talent_list(view)
        elif screen == "respec":
            rendered = render_talent_respec(view)
        else:
            rendered = render_talent_root(view)
        await present(query.message, rendered, images, edit=True)

    async def show_arts(query: CallbackQuery, *, art_id: str | None = None, choose: bool = False):
        if not isinstance(query.message, Message):
            return
        view = await active_arts.view(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if art_id is None:
            rendered = render_art_root(view)
        elif choose:
            occupied = {entry.slot for entry in view.slots}
            empty = [slot for slot in (1, 2, 3) if slot not in occupied]
            if len(empty) == 1:
                try:
                    await active_arts.equip_art(
                        query.from_user.id,
                        empty[0],
                        art_id,
                        expected_configuration_version=view.combat_configuration_version,
                    )
                except (ActiveArtMutationRejected, CombatConfigurationLocked):
                    await show_arts(query)
                    return
                await show_arts(query)
                return
            rendered = render_art_slot_choice(view, art_id)
        else:
            rendered = render_art_detail(view, art_id)
        await present(query.message, rendered, images, edit=True)

    @router.callback_query(F.data == "character:talents")
    async def open_talents(query: CallbackQuery) -> None:
        await query.answer()
        await show_talents(query)

    @router.callback_query(F.data == "character:arts")
    async def open_arts(query: CallbackQuery) -> None:
        await query.answer()
        await show_arts(query)

    @router.callback_query(F.data.startswith("tal:"))
    async def talent_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        actor = query.from_user.id
        if parts == ["tal", "root"]:
            await query.answer()
            await show_talents(query)
            return
        try:
            action = parts[1]
            if action in {"list", "respec"} and len(parts) == 3:
                expected = _from_base36(parts[2])
                view = await talents.view(actor)
                if view is None or expected != view.combat_configuration_version:
                    await query.answer("A tela foi atualizada.")
                    await show_talents(query, screen="list" if action == "list" else "root")
                    return
                if action == "list":
                    await query.answer()
                    await show_talents(query, screen="list")
                else:
                    await query.answer()
                    await show_talents(query, screen="respec")
                return
            if action in {"d", "a"} and len(parts) == 4:
                index, expected = _from_base36(parts[2]), _from_base36(parts[3])
                view = await talents.view(actor)
                if view is None or expected != view.combat_configuration_version:
                    await query.answer("A tela foi atualizada.")
                    await show_talents(query, screen="list")
                    return
                definition = _talent_by_index(view, index)
                if action == "d":
                    await query.answer()
                    await show_talents(query, screen="detail", index=index)
                    return
                await talents.acquire(
                    actor,
                    definition.talent_id,
                    expected_configuration_version=expected,
                )
                await query.answer()
                await show_talents(query, screen="list")
                return
            if action == "rc" and len(parts) == 3:
                expected = _from_base36(parts[2])
                await talents.respec(actor, expected_configuration_version=expected)
                await query.answer()
                await show_talents(query)
                return
        except (IndexError, KeyError, TypeError, ValueError, TalentMutationRejected) as exc:
            message = (
                "A tela foi atualizada."
                if isinstance(exc, ValueError)
                else "A configuração não pôde ser alterada."
            )
            await query.answer(message)
            await show_talents(query, screen="list")
            return
        await query.answer("A tela foi atualizada.")
        await show_talents(query)

    @router.callback_query(F.data.startswith("art:"))
    async def art_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        actor = query.from_user.id
        if parts == ["art", "r"]:
            await query.answer()
            await show_arts(query)
            return
        try:
            action = parts[1]
            if action == "d" and len(parts) == 4:
                index, expected = _from_base36(parts[2]), _from_base36(parts[3])
                view = await active_arts.view(actor)
                art_id = _art_by_index(view, index) if view is not None else None
                if (
                    view is None
                    or expected != view.combat_configuration_version
                    or art_id not in view.available_art_ids
                ):
                    await query.answer("A tela foi atualizada.")
                    await show_arts(query)
                    return
                await query.answer()
                await show_arts(query, art_id=art_id)
                return
            if action == "e" and len(parts) == 4:
                index, expected = _from_base36(parts[2]), _from_base36(parts[3])
                view = await active_arts.view(actor)
                art_id = _art_by_index(view, index) if view is not None else None
                if (
                    view is None
                    or expected != view.combat_configuration_version
                    or art_id not in view.available_art_ids
                    or any(entry.art_id == art_id for entry in view.slots)
                ):
                    await query.answer("A tela foi atualizada.")
                    await show_arts(query)
                    return
                await query.answer()
                await show_arts(query, art_id=art_id, choose=True)
                return
            if action == "s" and len(parts) == 5:
                index, slot, expected = (
                    _from_base36(parts[2]),
                    _from_base36(parts[3]),
                    _from_base36(parts[4]),
                )
                view = await active_arts.view(actor)
                art_id = _art_by_index(view, index) if view is not None else None
                if (
                    view is None
                    or expected != view.combat_configuration_version
                    or art_id not in view.available_art_ids
                ):
                    await query.answer("A tela foi atualizada.")
                    await show_arts(query)
                    return
                await active_arts.equip_art(
                    actor,
                    slot,
                    art_id,
                    expected_configuration_version=expected,
                )
                await query.answer()
                await show_arts(query)
                return
        except (
            IndexError,
            KeyError,
            TypeError,
            ValueError,
            ActiveArtMutationRejected,
            CombatConfigurationLocked,
        ):
            await query.answer("A tela foi atualizada.")
            await show_arts(query)
            return
        await query.answer("A tela foi atualizada.")
        await show_arts(query)

    return router
