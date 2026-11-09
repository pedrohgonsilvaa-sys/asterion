"""Telegram adapters for the Crônica, the Trilha and the Salão da Vigília."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.chronicle import ChronicleError, ChronicleService
from asterion.bot.chronicle_ui import (
    error_text,
    render_chapter,
    render_chronicle,
    render_hall,
    render_trail,
    render_vote,
    vote_notice,
)
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.domain.chronicle import Outcome


def chronicle_router(service: ChronicleService, images: dict[str, str]) -> Router:
    router = Router(name="chronicle")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def chapter_screen(actor: int, number: int) -> Screen:
        view = await service.view(actor)
        chapter = next((item for item in view.chapters if item.number == number), None)
        if chapter is None:
            raise ChronicleError("chronicle_chapter_locked")
        return render_chapter(view, chapter)

    async def dispatch(query: CallbackQuery, actor: int) -> None:
        parts = (query.data or "").split(":")
        match parts:
            case ["cr", "root"]:
                await show(query, render_chronicle(await service.view(actor)))
            case ["cr", "ch", number] if number.isdigit():
                await show(query, await chapter_screen(actor, int(number)))
            case ["cr", "conclude", number] if number.isdigit():
                view = await service.conclude_chapter(actor, int(number))
                chapter = next(item for item in view.chapters if item.number == int(number))
                await show(query, render_chapter(view, chapter))
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

    @router.callback_query(F.data.startswith("cr:"))
    async def callback(query: CallbackQuery) -> None:
        try:
            await dispatch(query, query.from_user.id)
        except ChronicleError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        await query.answer()

    return router
