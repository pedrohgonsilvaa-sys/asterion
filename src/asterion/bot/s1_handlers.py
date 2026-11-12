"""Telegram callbacks for S1 — Luzes sob as Cinzas."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.s1 import S1Service
from asterion.bot.creation_handlers import present
from asterion.bot.s1_ui import render_missions_after_s1_abandon, render_s1


def s1_router(service: S1Service, images: dict[str, str]) -> Router:
    router = Router(name="s1")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s1(view), images, edit=True)

    @router.callback_query(F.data == "s1:oren")
    async def oren(query: CallbackQuery):
        await query.answer()
        await show(query, await service.oren(query.from_user.id))

    @router.callback_query(F.data == "s1:offer")
    async def offer(query: CallbackQuery):
        await query.answer()
        await show(query, await service.offer(query.from_user.id))

    @router.callback_query(F.data == "s1:accept")
    async def accept(query: CallbackQuery):
        await query.answer()
        await show(query, await service.accept(query.from_user.id))

    @router.callback_query(F.data == "s1:reaccept")
    async def reaccept(query: CallbackQuery):
        await query.answer()
        await show(query, await service.accept(query.from_user.id, reaccept=True))

    @router.callback_query(F.data == "s1:detail")
    async def detail(query: CallbackQuery):
        await query.answer()
        view = await service.resume(query.from_user.id)
        if view is not None:
            await show(query, view)

    @router.callback_query(F.data == "s1:objective")
    async def objective(query: CallbackQuery):
        await query.answer()
        await show(query, await service.objective(query.from_user.id))

    @router.callback_query(F.data == "s1:abandon")
    async def abandon_confirmation(query: CallbackQuery):
        await query.answer()
        await show(query, await service.abandon_confirmation(query.from_user.id))

    @router.callback_query(F.data.startswith("s1:") & F.data.endswith(":track"))
    async def track(query: CallbackQuery):
        await query.answer()
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            return
        await show(query, await service.toggle_tracking(query.from_user.id, version))

    @router.callback_query(F.data.startswith("s1:") & F.data.contains(":point:"))
    async def point(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _, raw_point = (query.data or "").split(":")
            version, point_id = int(raw_version), int(raw_point)
        except (TypeError, ValueError):
            return
        await show(
            query,
            await service.investigate_point(query.from_user.id, point_id, version),
        )

    @router.callback_query(F.data.startswith("s1:") & F.data.endswith(":ashes"))
    async def ashes(query: CallbackQuery):
        await query.answer()
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            return
        await show(query, await service.examine_ashes(query.from_user.id, version))

    @router.callback_query(F.data.startswith("s1:") & F.data.endswith(":light"))
    async def light(query: CallbackQuery):
        await query.answer()
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            return
        await show(query, await service.observe_light(query.from_user.id, version))

    @router.callback_query(F.data.startswith("s1:") & F.data.contains(":nc:"))
    async def narrative_choice(query: CallbackQuery):
        await query.answer()
        parts = (query.data or "").split(":")
        try:
            version = int(parts[1])
        except (TypeError, ValueError, IndexError):
            return
        kind = "oren" if parts[2] == "o" else "objective"
        await show(
            query,
            await service.choose_response(query.from_user.id, version, parts[-1], kind),
        )

    @router.callback_query(F.data.startswith("s1:") & F.data.endswith(":complete"))
    async def complete(query: CallbackQuery):
        await query.answer()
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            return
        await show(query, await service.complete_with_oren(query.from_user.id, version))

    @router.callback_query(F.data.startswith("s1:") & F.data.endswith(":abandon:confirm"))
    async def confirm_abandon(query: CallbackQuery):
        await query.answer()
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            return
        view = await service.abandon(query.from_user.id, version)
        if view is not None and isinstance(query.message, Message):
            if view.status == "abandoned":
                await present(
                    query.message,
                    render_missions_after_s1_abandon(),
                    images,
                    edit=True,
                )
            else:
                await present(query.message, render_s1(view), images, edit=True)

    return router
