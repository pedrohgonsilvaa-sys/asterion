"""Telegram callbacks for the Altos Cinéreos opening mission."""

from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.altos_missions import AltosMissionService
from asterion.application.groups import GroupError
from asterion.application.s30 import S30Service, S30View
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.bot.combat_ui import (
    CampaignCombatCallback,
    CombatCallback,
    CombatConsumableCallback,
    CombatConsumableFlowCallback,
)
from asterion.bot.creation_handlers import present
from asterion.bot.groups_ui import render_group
from asterion.bot.s30_ui import render_s30


def _base36(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid revision")
    return int(value, 36)


def altos_missions_router(
    service: AltosMissionService,
    images: dict[str, str],
    *,
    s30: S30Service | None = None,
) -> Router:
    router = Router(name="altos_missions")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            screen = render_altos_mission(view)
            if view.quest_id == "S30" and s30 is not None:
                mission_view = await s30.resume(query.from_user.id)
                if isinstance(mission_view, S30View):
                    screen = render_s30(mission_view)
            await present(query.message, screen, images, edit=True)

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
        await present(message, render_altos_mission(view), images, edit=False)

    @router.callback_query(F.data == "altos:mission")
    async def resume_mission(query: CallbackQuery) -> None:
        view = await service.resume_active(query.from_user.id)
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("altos:"))
    async def mission_action(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        try:
            if len(parts) == 5 and parts[1] == "choice" and parts[2] == "P27":
                view = await service.choose_p27_reward(
                    query.from_user.id, int(parts[3]), parts[4]
                )
            if len(parts) == 4 and parts[1] == "action":
                view = await service.advance(
                    query.from_user.id, int(parts[2]), parts[3]
                )
            elif len(parts) == 4 and parts[1] == "combat":
                version = int(parts[2])
                if parts[3] == "solo":
                    view = await service.start_solo_combat(query.from_user.id, version)
                elif parts[3] == "group":
                    view = await service.propose_group_combat(query.from_user.id, version)
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif len(parts) == 3 and parts[1] == "retry":
                view = await service.retry_combat(query.from_user.id, int(parts[2]))
            elif len(parts) == 5 and parts[1] == "combat" and parts[2] == "P27":
                version = int(parts[3])
                if parts[4] == "solo":
                    view = await service.start_solo_combat(
                        query.from_user.id, version, "P27"
                    )
                elif parts[4] == "group":
                    view = await service.propose_group_combat(
                        query.from_user.id, version, "P27"
                    )
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif len(parts) == 5 and parts[1] == "combat" and parts[2] == "P28":
                version = int(parts[3])
                if parts[4] == "solo":
                    view = await service.start_solo_combat(
                        query.from_user.id, version, "P28"
                    )
                elif parts[4] == "group":
                    view = await service.propose_group_combat(
                        query.from_user.id, version, "P28"
                    )
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif len(parts) == 5 and parts[1] == "combat" and parts[2] == "P29":
                version = int(parts[3])
                if parts[4] == "solo":
                    view = await service.start_solo_combat(
                        query.from_user.id, version, "P29"
                    )
                elif parts[4] == "group":
                    view = await service.propose_group_combat(
                        query.from_user.id, version, "P29"
                    )
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif len(parts) == 5 and parts[1] == "combat" and parts[2] == "P30":
                version = int(parts[3])
                if parts[4] == "solo":
                    view = await service.start_solo_combat(
                        query.from_user.id, version, "P30"
                    )
                elif parts[4] == "group":
                    view = await service.propose_group_combat(
                        query.from_user.id, version, "P30"
                    )
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif len(parts) == 5 and parts[1] == "combat" and parts[2] == "S30":
                version = int(parts[3])
                if parts[4] == "solo":
                    view = await service.start_solo_combat(
                        query.from_user.id, version, "S30"
                    )
                elif parts[4] == "group":
                    view = await service.propose_group_combat(
                        query.from_user.id, version, "S30"
                    )
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif len(parts) == 5 and parts[1] == "combat" and parts[2] == "S26":
                version = int(parts[3])
                if parts[4] == "solo":
                    view = await service.start_solo_combat(
                        query.from_user.id, version, "S26"
                    )
                elif parts[4] == "group":
                    view = await service.propose_group_combat(
                        query.from_user.id, version, "S26"
                    )
                    if view is not None and view.proposal_id is not None:
                        await query.answer("Confirmação enviada ao Grupo.")
                        await show_group(query)
                        return
                else:
                    raise ValueError("invalid combat mode")
            elif len(parts) == 4 and parts[1] == "retry" and parts[2] == "P27":
                view = await service.retry_combat(query.from_user.id, int(parts[3]), "P27")
            elif len(parts) == 4 and parts[1] == "retry" and parts[2] == "P28":
                view = await service.retry_combat(query.from_user.id, int(parts[3]), "P28")
            elif len(parts) == 4 and parts[1] == "retry" and parts[2] == "P29":
                view = await service.retry_combat(query.from_user.id, int(parts[3]), "P29")
            elif len(parts) == 4 and parts[1] == "retry" and parts[2] == "P30":
                view = await service.retry_combat(query.from_user.id, int(parts[3]), "P30")
            elif len(parts) == 4 and parts[1] == "retry" and parts[2] == "S30":
                view = await service.retry_combat(query.from_user.id, int(parts[3]), "S30")
            elif len(parts) == 4 and parts[1] == "retry" and parts[2] == "S26":
                view = await service.retry_combat(query.from_user.id, int(parts[3]), "S26")
            else:
                if not (
                    len(parts) == 5
                    and parts[1] == "choice"
                    and parts[2] == "P27"
                ):
                    raise SkipHandler()
        except (TypeError, ValueError, GroupError):
            await query.answer("A ação expirou ou o estado da missão mudou.", show_alert=True)
            return
        if view is None:
            await query.answer("A missão não está disponível neste estado.", show_alert=True)
            return
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
        if proposal.activity_type != "campaign_altos":
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
            view = await service.start_group_combat(
                query.from_user.id,
                proposal_id,
                expected_revision=revision,
                quest_id=(proposal.context_payload or {}).get("quest_id", "P25"),
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
        if view is not None and isinstance(query.message, Message):
            await show(query, view)

    @router.callback_query(F.data.startswith("fight:"))
    async def solo_fight(query: CallbackQuery) -> None:
        try:
            callback = CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler() from None
        view = await service.action(
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
        view = await service.action(
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
        current = await service.combat_view_for_actor(query.from_user.id, callback.activity_id)
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
            view = await service.action(
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
        await show(query, view)

    return router
