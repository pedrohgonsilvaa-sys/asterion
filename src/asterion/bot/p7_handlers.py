"""Telegram intent adapter for P7: A Estrada Estrangulada."""
# ruff: noqa: B904,E501

from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.p7 import P7Service
from asterion.bot.combat_ui import (
    CampaignCombatCallback,
    CombatCallback,
    CombatConsumableCallback,
    CombatConsumableFlowCallback,
)
from asterion.bot.creation_handlers import present
from asterion.bot.groups_ui import render_group
from asterion.bot.p7_ui import render_p7


def _parse_revision(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid revision")
    return int(value, 36)


def p7_router(service: P7Service, images: dict[str, str]) -> Router:
    router = Router(name="p7")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p7(view), images, edit=True)

    async def show_group(query: CallbackQuery) -> None:
        if service.groups is None:
            return
        group = await service.groups.group(query.from_user.id)
        proposals = await service.groups.activity_proposals(query.from_user.id)
        if isinstance(query.message, Message):
            await present(query.message, render_group(group, proposals), images, edit=True)

    async def active_view(actor: int):
        view = await service.resume(actor)
        if view is None or view.status != "active":
            return None
        return view

    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def resume_from_command(message: Message) -> None:
        if message.from_user is None:
            raise SkipHandler()
        view = await active_view(message.from_user.id)
        if view is None:
            raise SkipHandler()
        await present(message, render_p7(view), images, edit=False)

    @router.callback_query(F.data.in_({"world:missions", "world:principal"}))
    async def mission_shortcut(query: CallbackQuery) -> None:
        view = await service.resume(query.from_user.id)
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data == "p7:enter")
    async def enter(query: CallbackQuery) -> None:
        await show(query, await service.enter_vales(query.from_user.id))

    @router.callback_query(F.data == "p7:resume")
    async def resume(query: CallbackQuery) -> None:
        await show(query, await service.resume(query.from_user.id))

    @router.callback_query(F.data.startswith("p7:"))
    async def mutate(query: CallbackQuery) -> None:
        parts = (query.data or "").split(":")
        if len(parts) < 3:
            raise SkipHandler()
        try:
            version = int(parts[1])
        except ValueError:
            await query.answer()
            return
        action = parts[2]
        actor = query.from_user.id
        if action == "road" and len(parts) == 4:
            view = await service.examine_road_point(actor, version, parts[3])
        elif action == "passage":
            view = await service.inspect_recent_passage(actor, version)
        elif action == "solo":
            view = await service.start_solo_combat(actor, version)
        elif action == "group":
            try:
                view = await service.propose_group_combat(actor, version)
            except GroupError:
                await query.answer("Não foi possível preparar o Grupo. Atualize a tela.", show_alert=True)
                return
            await query.answer("Confirmação enviada ao Grupo.")
            await show_group(query)
            return
        elif action == "retry":
            view = await service.retry(actor, version)
        elif action == "stone":
            view = await service.inspect_worked_stone(actor, version)
        elif action == "vigilia":
            view = await service.proceed_to_vigilia(actor, version)
        elif action == "brazier":
            view = await service.activate_brazier(actor, version)
        elif action == "report":
            view = await service.report_dara(actor, version)
        else:
            view = await service.resume(actor)
        await show(query, view)

    @router.callback_query(F.data.startswith("fight:"))
    async def solo_fight(query: CallbackQuery) -> None:
        try:
            cb = CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler()
        view = await service.action_combat(
            query.from_user.id, cb.activity_id, cb.version, cb.action
        )
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("cc:"))
    async def group_fight(query: CallbackQuery) -> None:
        try:
            cb = CampaignCombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler()
        view = await service.campaign_action(
            query.from_user.id,
            cb.activity_id,
            cb.combat_version,
            cb.action_index,
            cb.target,
        )
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("cu:"))
    async def consumable(query: CallbackQuery) -> None:
        try:
            cb = CombatConsumableCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler()
        view = await service.action_combat(
            query.from_user.id,
            cb.activity_id,
            cb.state_version,
            consumable_id=cb.item_id,
            target_id=cb.target_id,
            effect_id=cb.effect_id,
        )
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("cf:"))
    async def consumable_flow(query: CallbackQuery) -> None:
        try:
            cb = CombatConsumableFlowCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            raise SkipHandler()
        current = await service.resume(query.from_user.id)
        if current is None or current.activity_id != cb.activity_id:
            raise SkipHandler()
        if cb.step == "o":
            view = await service.consumable_selection(
                query.from_user.id, cb.activity_id, cb.state_version, screen="items"
            )
        elif cb.step == "i" and cb.item_id is not None:
            view = await service.consumable_selection(
                query.from_user.id,
                cb.activity_id,
                cb.state_version,
                screen="choose_item",
                item_id=cb.item_id,
            )
            option = getattr(view, "ready_consumable_option", None)
            if option is not None:
                view = await service.action_combat(
                    query.from_user.id,
                    cb.activity_id,
                    cb.state_version,
                    consumable_id=option.item_id,
                    target_id=option.target_id,
                    effect_id=option.effect_id,
                )
        elif cb.step == "t" and cb.item_id is not None and cb.target_id is not None:
            view = await service.consumable_selection(
                query.from_user.id,
                cb.activity_id,
                cb.state_version,
                screen="choose_target",
                item_id=cb.item_id,
                target_id=cb.target_id,
            )
            option = getattr(view, "ready_consumable_option", None)
            if option is not None:
                view = await service.action_combat(
                    query.from_user.id,
                    cb.activity_id,
                    cb.state_version,
                    consumable_id=option.item_id,
                    target_id=option.target_id,
                    effect_id=option.effect_id,
                )
        elif cb.step == "e" and cb.item_id is not None and cb.target_id is not None and cb.effect_id:
            view = await service.action_combat(
                query.from_user.id,
                cb.activity_id,
                cb.state_version,
                consumable_id=cb.item_id,
                target_id=cb.target_id,
                effect_id=cb.effect_id,
            )
        elif cb.step == "b":
            view = await service.consumable_selection(
                query.from_user.id,
                cb.activity_id,
                cb.state_version,
                screen=cb.parent_screen or "combat",
                item_id=cb.item_id,
                target_id=cb.target_id,
            )
        else:
            view = current
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
            revision = _parse_revision(parts[4])
            proposal = await service.groups.activity_proposal(query.from_user.id, proposal_id)
        except (ValueError, GroupError):
            raise SkipHandler()
        if proposal.activity_type != "campaign_p7":
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
            await query.answer(
                "A confirmação expirou ou o roster mudou." if exc.code in {"stale", "proposal_expired", "eligibility_changed"} else "Não foi possível iniciar a Jornada.",
                show_alert=True,
            )
            await show_group(query)
            return
        await query.answer("Confronto da Jornada iniciado.")
        if isinstance(query.message, Message):
            view = await service.resume(query.from_user.id)
            if view is not None:
                await present(query.message, render_p7(view), images, edit=True)

    return router
