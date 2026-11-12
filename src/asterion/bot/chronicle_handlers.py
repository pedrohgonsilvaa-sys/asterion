"""Telegram adapters for the Crônica, the Trilha and the Salão da Vigília."""

from __future__ import annotations

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from asterion.application.chronicle import ChronicleError, ChronicleService
from asterion.application.chronicle_activities import ChronicleActivityService
from asterion.application.chronicle_encounters import ChronicleEncounterService
from asterion.application.groups import ActivityProposalView
from asterion.bot.chronicle_ui import (
    error_text,
    render_calendar,
    render_chapter,
    render_chronicle,
    render_encounter,
    render_group_proposal,
    render_hall,
    render_here,
    render_readings,
    render_talk,
    render_trail,
    render_vote,
    vote_notice,
)
from asterion.bot.combat_ui import ChronicleCombatCallback, ChronicleIntentCallback
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.domain.chronicle import Outcome


def chronicle_router(
    service: ChronicleService,
    images: dict[str, str],
    activities: ChronicleActivityService | None = None,
    encounters: ChronicleEncounterService | None = None,
) -> Router:
    router = Router(name="chronicle")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def chapter_screen(actor: int, number: int) -> Screen:
        view = await service.view(actor)
        chapter = next((item for item in view.chapters if item.number == number), None)
        if chapter is None:
            raise ChronicleError("chronicle_chapter_locked")
        actions = () if activities is None else await activities.actions(actor)
        fights = () if encounters is None else await encounters.encounters(actor)
        return render_chapter(
            view,
            chapter,
            tuple(a for a in actions if a.objective.chapter == number),
            tuple(f for f in fights if f.objective.chapter == number),
        )

    def active() -> ChronicleActivityService:
        if activities is None:
            raise ChronicleError("unknown")
        return activities

    async def dispatch(query: CallbackQuery, actor: int) -> None:
        parts = (query.data or "").split(":")
        match parts:
            case ["cr", "root"]:
                await show(query, render_chronicle(await service.view(actor)))
            case ["cr", "ch", number] if number.isdigit():
                await show(query, await chapter_screen(actor, int(number)))
            case ["cr", "conclude", number] if number.isdigit():
                await service.conclude_chapter(actor, int(number))
                await show(query, await chapter_screen(actor, int(number)))
            case ["cr", "here"]:
                actions = () if activities is None else await activities.here(actor)
                fights = () if encounters is None else await encounters.here(actor)
                await show(query, render_here(actions, fights))
            case ["cr", "fight", number, slot] if number.isdigit() and slot.isdigit():
                if encounters is None:
                    raise ChronicleError("unknown")
                fight_view = await encounters.start(actor, int(number), int(slot))
                await show(query, render_encounter(fight_view))
            case ["cr", "gfight", number, slot] if number.isdigit() and slot.isdigit():
                if encounters is None:
                    raise ChronicleError("unknown")
                proposed = await encounters.propose_group(actor, int(number), int(slot))
                if isinstance(proposed, ActivityProposalView):
                    await show(query, render_group_proposal(int(number)))
                else:
                    await show(query, render_encounter(proposed))
            case ["cr", "talk", number, slot] if number.isdigit() and slot.isdigit():
                await show(query, render_talk(await active().talk(actor, int(number), int(slot))))
            case ["cr", "read", number, slot] if number.isdigit() and slot.isdigit():
                view = await active().readings(actor, int(number), int(slot))
                await show(query, render_readings(view))
            case ["cr", "read", number, slot, point] if number.isdigit() and slot.isdigit():
                view = await active().examine(actor, int(number), int(slot), point)
                await show(query, render_readings(view))
            case ["cr", "vote"]:
                await show(query, render_vote(await service.view(actor)))
            case ["cr", "vote", option]:
                view = await service.vote(actor, option)
                await show(query, render_vote(view, vote_notice(Outcome(option))))
            case ["cr", "trail"]:
                await show(query, render_trail(await service.track(actor)))
            case ["cr", "trail", "claim"]:
                result = await service.claim(actor)
                await show(query, render_trail(await service.track(actor), result))
            case ["cr", "hall"]:
                await show(query, render_hall(await service.hall(actor)))
            case _:
                raise ChronicleError("unknown")

    @router.message(CommandStart(), F.chat.type == "private")
    @router.message(Command("menu"), F.chat.type == "private")
    async def resume_fight(message: Message) -> None:
        if encounters is None or message.from_user is None:
            raise SkipHandler
        view = await encounters.foreground(message.from_user.id)
        if view is None:
            raise SkipHandler
        await present(message, render_encounter(view), images)

    @router.callback_query(ChronicleCombatCallback.filter())
    async def fight(query: CallbackQuery, callback_data: ChronicleCombatCallback) -> None:
        view = None
        if encounters is not None:
            view = await encounters.action(
                query.from_user.id,
                callback_data.activity_id,
                callback_data.version,
                callback_data.action,
            )
        if view is None:
            await query.answer(error_text("chronicle_fight_over"), show_alert=True)
            return
        await query.answer()
        await show(query, render_encounter(view))

    @router.callback_query(ChronicleIntentCallback.filter())
    async def fight_intent(query: CallbackQuery, callback_data: ChronicleIntentCallback) -> None:
        view = None
        if encounters is not None:
            view = await encounters.intent(
                query.from_user.id,
                callback_data.activity_id,
                callback_data.combat_version,
                callback_data.action_index,
                callback_data.target,
            )
        if view is None:
            await query.answer(error_text("chronicle_fight_over"), show_alert=True)
            return
        await query.answer()
        await show(query, render_encounter(view))

    @router.callback_query(F.data == "calendar:root")
    async def calendar(query: CallbackQuery) -> None:
        view = await service.view(query.from_user.id)
        await show(query, render_calendar(view, datetime.now(UTC)))
        await query.answer()

    @router.callback_query(F.data.startswith("cr:"))
    async def callback(query: CallbackQuery) -> None:
        try:
            await dispatch(query, query.from_user.id)
        except ChronicleError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        await query.answer()

    return router
