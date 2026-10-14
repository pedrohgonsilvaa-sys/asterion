"""Telegram callbacks for the Nareth campaign and its shared encounters."""

from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.nareth_missions import (
    MISSION_TITLES,
    S13_ID,
    NarethMissionService,
)
from asterion.bot.combat_ui import (
    CampaignCombatCallback,
    CombatCallback,
    CombatConsumableCallback,
    CombatConsumableFlowCallback,
)
from asterion.bot.creation_handlers import present
from asterion.bot.groups_ui import render_group
from asterion.bot.nareth_missions_ui import render_nareth_mission


def _base36(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid revision")
    return int(value, 36)


def nareth_missions_router(
    service: NarethMissionService, images: dict[str, str]
) -> Router:
    router = Router(name="nareth_missions")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_nareth_mission(view), images, edit=True)

    async def show_group(query: CallbackQuery) -> None:
        if service.groups is None or not isinstance(query.message, Message):
            return
        group = await service.groups.group(query.from_user.id)
        proposals = await service.groups.activity_proposals(query.from_user.id)
        await present(query.message, render_group(group, proposals), images, edit=True)

    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def resume_from_command(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler()
        view = await service.resume_active(message.from_user.id)
        if view is None:
            raise SkipHandler()
        await present(message, render_nareth_mission(view), images, edit=False)

    @router.callback_query(F.data.startswith("nareth:"))
    async def mission_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) < 3:
            raise SkipHandler()
        action_type = parts[1]
        quest_id = parts[2]
        if quest_id not in MISSION_TITLES:
            raise SkipHandler()
        try:
            if action_type == "mission" and len(parts) == 3:
                view = await service.resume(query.from_user.id, quest_id)
            elif action_type == "start" and len(parts) == 3:
                view = await service.start(query.from_user.id, quest_id)
            elif action_type == "action" and len(parts) == 5:
                view = await service.advance(
                    query.from_user.id, quest_id, int(parts[3]), parts[4]
                )
            elif action_type == "ex" and len(parts) == 5 and quest_id == S13_ID:
                view = await service.examine(
                    query.from_user.id, quest_id, int(parts[3]), parts[4]
                )
            elif action_type == "combat" and len(parts) == 5:
                version = int(parts[3])
                if parts[4] == "solo":
                    view = await service.start_solo_combat(
                        query.from_user.id, quest_id, version
                    )
                elif parts[4] == "group":
                    view = await service.propose_group_combat(
                        query.from_user.id, quest_id, version
                    )
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif action_type == "choice" and len(parts) == 5 and quest_id in {"P15", "P18"}:
                view = await service.choose_midgame_reward(
                    query.from_user.id, int(parts[3]), parts[4], quest_id
                )
            else:
                raise ValueError("invalid Nareth mission callback")
        except (TypeError, ValueError, GroupError):
            await query.answer("A ação expirou ou o estado da missão mudou.", show_alert=True)
            return
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("group:proposal:"))
    async def group_proposal(query: CallbackQuery) -> None:
        if service.groups is None:
            raise SkipHandler()
        parts = (query.data or "").split(":")
        try:
            if len(parts) != 5 or parts[2] not in {"yes", "no", "start"}:
                raise ValueError("invalid proposal callback")
            proposal_id = UUID(hex=parts[3])
            revision = _base36(parts[4])
            proposal = await service.groups.activity_proposal(
                query.from_user.id, proposal_id
            )
        except (ValueError, GroupError):
            raise SkipHandler() from None
        if proposal.activity_type != "campaign_nareth":
            raise SkipHandler()
        try:
            if parts[2] in {"yes", "no"}:
                await service.groups.respond_activity(
                    query.from_user.id,
                    proposal_id,
                    expected_revision=revision,
                    accept=parts[2] == "yes",
                )
                await query.answer(
                    "Atividade confirmada." if parts[2] == "yes" else "Atividade recusada."
                )
                await show_group(query)
                return
            await service.start_group_combat(
                query.from_user.id,
                proposal_id,
                expected_revision=revision,
            )
        except GroupError as exc:
            message = (
                "A confirmação expirou ou a elegibilidade mudou."
                if exc.code in {"stale", "proposal_expired", "eligibility_changed"}
                else "Não foi possível iniciar o encontro compartilhado."
            )
            await query.answer(message, show_alert=True)
            await show_group(query)
            return
        await query.answer("Encontro compartilhado iniciado.")
        view = await service.resume_active(query.from_user.id)
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_nareth_mission(view), images, edit=True)

    @router.callback_query(F.data.startswith("fight:"))
    async def solo_fight(query: CallbackQuery) -> None:
        try:
            callback = CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler() from None
        view = await service.action_combat(
            query.from_user.id,
            callback.activity_id,
            callback.version,
            callback.action,
        )
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("cc:"))
    async def group_fight(query: CallbackQuery) -> None:
        try:
            callback = CampaignCombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler() from None
        view = await service.campaign_action(
            query.from_user.id,
            callback.activity_id,
            callback.combat_version,
            callback.action_index,
            callback.target,
        )
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("cu:"))
    async def consumable(query: CallbackQuery) -> None:
        try:
            callback = CombatConsumableCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler() from None
        view = await service.action_combat(
            query.from_user.id,
            callback.activity_id,
            callback.state_version,
            consumable_id=callback.item_id,
            target_id=callback.target_id,
            effect_id=callback.effect_id,
        )
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("cf:"))
    async def consumable_flow(query: CallbackQuery) -> None:
        try:
            callback = CombatConsumableFlowCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler() from None
        current = await service._combat_view_for_actor(
            query.from_user.id, callback.activity_id
        )
        if current is None or current.activity_id != callback.activity_id:
            raise SkipHandler()
        version = callback.state_version
        if callback.step == "o":
            view = await service.consumable_selection(
                query.from_user.id, callback.activity_id, version, screen="items"
            )
        elif callback.step == "i" and callback.item_id is not None:
            view = await service.consumable_selection(
                query.from_user.id,
                callback.activity_id,
                version,
                screen="choose_item",
                item_id=callback.item_id,
            )
        elif (
            callback.step == "t"
            and callback.item_id is not None
            and callback.target_id is not None
        ):
            view = await service.consumable_selection(
                query.from_user.id,
                callback.activity_id,
                version,
                screen="choose_target",
                item_id=callback.item_id,
                target_id=callback.target_id,
            )
        elif (
            callback.step == "e"
            and callback.item_id is not None
            and callback.target_id is not None
            and callback.effect_id
        ):
            view = await service.action_combat(
                query.from_user.id,
                callback.activity_id,
                version,
                consumable_id=callback.item_id,
                target_id=callback.target_id,
                effect_id=callback.effect_id,
            )
        elif callback.step == "b":
            view = await service.consumable_selection(
                query.from_user.id,
                callback.activity_id,
                version,
                screen=callback.parent_screen or "combat",
                item_id=callback.item_id,
                target_id=callback.target_id,
            )
        else:
            view = current
        if view is None:
            raise SkipHandler()
        option = view.ready_consumable_option
        if option is not None:
            view = await service.action_combat(
                query.from_user.id,
                callback.activity_id,
                version,
                consumable_id=option.item_id,
                target_id=option.target_id,
                effect_id=option.effect_id,
            )
        await show(query, view)

    return router
