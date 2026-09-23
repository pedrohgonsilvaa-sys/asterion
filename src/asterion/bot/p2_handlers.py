"""Telegram callbacks for P2 — Fuligem sem Fogo."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.p2 import P2Service
from asterion.bot.combat_ui import P2CombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.p2_ui import render_p2


def p2_router(service: P2Service, images: dict[str, str]) -> Router:
    router = Router(name="p2")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p2(view), images, edit=True)

    @router.callback_query(F.data.startswith("p2fight:"))
    async def fight(query: CallbackQuery):
        try:
            cb = P2CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        await show(
            query,
            await service.action(
                query.from_user.id,
                cb.activity_id,
                cb.version,
                cb.action,
            ),
        )

    @router.callback_query(F.data == "p2:alda")
    async def alda(query: CallbackQuery):
        await show(query, await service.alda(query.from_user.id))

    @router.callback_query(F.data == "p2:offer")
    async def offer(query: CallbackQuery):
        await show(query, await service.offer(query.from_user.id))

    @router.callback_query(F.data == "p2:accept")
    async def accept(query: CallbackQuery):
        await show(query, await service.accept(query.from_user.id))

    @router.callback_query(F.data == "p2:detail")
    async def detail(query: CallbackQuery):
        await show(query, await service.resume(query.from_user.id))

    @router.callback_query(F.data == "p2:objective")
    async def objective(query: CallbackQuery):
        await show(query, await service.objective(query.from_user.id))

    @router.callback_query(F.data.startswith("p2:") & F.data.contains(":point:"))
    async def point(query: CallbackQuery):
        try:
            _, raw_version, _, raw_point = (query.data or "").split(":")
            version, point_id = int(raw_version), int(raw_point)
        except (TypeError, ValueError):
            await query.answer()
            return
        await show(
            query,
            await service.investigate_point(query.from_user.id, point_id, version),
        )

    @router.callback_query(F.data.startswith("p2:") & F.data.endswith(":stone"))
    async def stone(query: CallbackQuery):
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            await query.answer()
            return
        await show(query, await service.examine_stone(query.from_user.id, version))

    @router.callback_query(F.data == "p2:oren")
    async def oren(query: CallbackQuery):
        await show(query, await service.oren(query.from_user.id))

    @router.callback_query(F.data.startswith("p2:") & F.data.endswith(":oren:deliver"))
    async def deliver(query: CallbackQuery):
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            await query.answer()
            return
        await show(query, await service.deliver_record(query.from_user.id, version))

    @router.callback_query(F.data.startswith("p2:") & F.data.endswith(":complete"))
    async def complete(query: CallbackQuery):
        try:
            version = int((query.data or "").split(":")[1])
        except (TypeError, ValueError, IndexError):
            await query.answer()
            return
        await show(query, await service.complete_with_alda(query.from_user.id, version))

    @router.callback_query(F.data.startswith("world:walk:"))
    async def walk(query: CallbackQuery):
        destination = {
            "charneca": "Charneca da Fuligem",
            "refuge": "Refúgio do Ocaso",
            "road": "Estrada das Cinzas",
        }.get((query.data or "").rsplit(":", 1)[-1])
        if destination is None:
            await query.answer()
            return
        await show(query, await service.travel_normal(query.from_user.id, destination))

    return router
