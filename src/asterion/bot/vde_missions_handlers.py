"""Telegram callbacks for S7 and P8 in Vales dos Enforcados."""

from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.vde_missions import (
    MISSION_TITLES,
    P9_ID,
    VDEMissionService,
)
from asterion.bot.combat_ui import (
    CampaignCombatCallback,
    CombatCallback,
    CombatConsumableCallback,
    CombatConsumableFlowCallback,
)
from asterion.bot.creation_handlers import present
from asterion.bot.groups_ui import render_group
from asterion.bot.vde_missions_ui import render_vde_mission


def _base36(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid revision")
    return int(value, 36)


def vde_missions_router(service: VDEMissionService, images: dict[str, str]) -> Router:
    router = Router(name="vde_missions")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_vde_mission(view), images, edit=True)

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
        await present(message, render_vde_mission(view), images, edit=False)

    @router.callback_query(F.data.startswith("vde:"))
    async def mission_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) not in {3, 4, 5} or parts[1] not in MISSION_TITLES:
            raise SkipHandler()
        quest_id = parts[1]
        try:
            if len(parts) == 3:
                action = parts[2]
                if action == "start":
                    view = await service.start(query.from_user.id, quest_id)
                elif action == "resume":
                    view = await service.resume(query.from_user.id, quest_id)
                else:
                    raise ValueError("invalid mission action")
            elif len(parts) == 4:
                version, action = int(parts[2]), parts[3]
                if action == "solo":
                    view = await service.start_solo_combat(query.from_user.id, quest_id, version)
                elif action == "group":
                    view = await service.propose_group_combat(query.from_user.id, quest_id, version)
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                elif action == "enter":
                    view = await service.enter_mata(query.from_user.id, version)
                elif action == "baixios":
                    view = await service.enter_baixios(query.from_user.id, version)
                elif action == "return":
                    view = await service.return_vigilia(query.from_user.id, version)
                elif action in {
                    "rope", "report", "compare", "masonry", "record", "passage",
                    "hardware", "route", "follow", "inscription", "fragment", "locate",
                    "fragments", "sample",
                    "structure", "sanctuary", "zone", "bag", "tracks", "survivor",
                }:
                    view = await service.advance(query.from_user.id, quest_id, version, action)
                else:
                    raise ValueError("invalid mission action")
            else:
                version = int(parts[2])
                if parts[3] == "ex" and parts[4] in {"a", "b", "c"}:
                    view = await service.examine(query.from_user.id, quest_id, version, parts[4])
                elif quest_id == P9_ID and parts[3] == "ch" and parts[4] in {"1", "2", "3"}:
                    view = await service.choose_p9_reward(query.from_user.id, version, parts[4])
                else:
                    raise ValueError("invalid objective callback")
        except (ValueError, GroupError):
            await query.answer("A ação expirou ou o estado do Grupo mudou.", show_alert=True)
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
            proposal = await service.groups.activity_proposal(query.from_user.id, proposal_id)
        except (ValueError, GroupError):
            raise SkipHandler() from None
        if proposal.activity_type != "campaign_vde":
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
            await present(query.message, render_vde_mission(view), images, edit=True)

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
        current = await service.resume_active(query.from_user.id)
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
            callback.step == "t" and callback.item_id is not None and callback.target_id is not None
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
