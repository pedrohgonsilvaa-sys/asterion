"""Intent-only Telegram callbacks for S2 — Os Nomes Esquecidos."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.s2 import S2Service
from asterion.bot.creation_handlers import present
from asterion.bot.s2_ui import render_s2

_VESTIGES = {
    "1": "s2.vestige.1",
    "2": "s2.vestige.2",
    "3": "s2.vestige.3",
}


def s2_router(service: S2Service, images: dict[str, str]) -> Router:
    router = Router(name="s2")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, view) -> None:
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_s2(view), images, edit=True)

    @router.callback_query(F.data == "s2:oren")
    async def oren(query: CallbackQuery):
        await query.answer()
        await show(query, await service.oren(query.from_user.id))

    @router.callback_query(F.data == "s2:offer")
    async def offer(query: CallbackQuery):
        await query.answer()
        await show(query, await service.offer(query.from_user.id))

    @router.callback_query(F.data == "s2:detail")
    async def detail(query: CallbackQuery):
        await query.answer()
        await show(query, await service.resume(query.from_user.id))

    @router.callback_query(F.data == "s2:objective")
    async def objective(query: CallbackQuery):
        await query.answer()
        await show(query, await service.objective(query.from_user.id))

    @router.callback_query(F.data.startswith("s2:") & F.data.endswith(":accept"))
    async def accept(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _ = (query.data or "").split(":")
            version = int(raw_version)
        except (TypeError, ValueError):
            return
        await show(query, await service.accept(query.from_user.id, version))

    @router.callback_query(F.data.startswith("s2:") & F.data.endswith(":reaccept"))
    async def reaccept(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _ = (query.data or "").split(":")
            version = int(raw_version)
        except (TypeError, ValueError):
            return
        await show(
            query,
            await service.accept(query.from_user.id, version, reaccept=True),
        )

    @router.callback_query(F.data.startswith("s2:") & F.data.endswith(":camp"))
    async def camp(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _ = (query.data or "").split(":")
            version = int(raw_version)
        except (TypeError, ValueError):
            return
        await show(query, await service.find_camp(query.from_user.id, version))

    @router.callback_query(F.data.startswith("s2:") & F.data.contains(":vestige:"))
    async def vestige(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _, raw_point = (query.data or "").split(":")
            version = int(raw_version)
            vestige_id = _VESTIGES[raw_point]
        except (TypeError, ValueError, KeyError):
            return
        await show(
            query,
            await service.examine_vestige(query.from_user.id, vestige_id, version),
        )

    @router.callback_query(F.data.startswith("s2:") & F.data.endswith(":group"))
    async def group_combat(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _ = (query.data or "").split(":")
            version = int(raw_version)
        except (TypeError, ValueError):
            return
        try:
            view = await service.propose_group_combat(query.from_user.id, version)
        except GroupError:
            await query.answer("Não foi possível preparar o Grupo.", show_alert=True)
            return
        await show(query, view)

    @router.callback_query(F.data.startswith("s2:") & F.data.endswith(":solo"))
    async def solo_combat(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _ = (query.data or "").split(":")
            version = int(raw_version)
        except (TypeError, ValueError):
            return
        await show(query, await service.start_solo_combat(query.from_user.id, version))

    for action, method in (
        ("retry", "retry"),
        ("fragment", "recover_fragment"),
        ("complete", "complete_with_oren"),
        ("track", "toggle_tracking"),
        ("abandon", "abandon_confirmation"),
    ):
        async def callback(query: CallbackQuery, *, method=method, action=action):
            await query.answer()
            if method == "abandon_confirmation":
                view = await service.abandon_confirmation(query.from_user.id)
            else:
                try:
                    _, raw_version, _ = (query.data or "").split(":")
                    version = int(raw_version)
                except (TypeError, ValueError):
                    return
                view = await getattr(service, method)(query.from_user.id, version)
            await show(query, view)

        router.callback_query.register(
            callback,
            F.data == "s2:abandon"
            if action == "abandon"
            else F.data.startswith("s2:") & F.data.endswith(f":{action}"),
        )

    @router.callback_query(
        F.data.startswith("s2:") & F.data.endswith(":abandon:confirm")
    )
    async def confirm_abandon(query: CallbackQuery):
        await query.answer()
        try:
            _, raw_version, _, _ = (query.data or "").split(":")
            version = int(raw_version)
        except (TypeError, ValueError):
            return
        await show(query, await service.abandon(query.from_user.id, version))

    return router
