"""Telegram intent callbacks for the automatically unlocked P6 campaign quest."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.p6 import P6_CHOICES, P6Service
from asterion.bot.creation_handlers import present
from asterion.bot.p6_ui import render_p6


def p6_router(service: P6Service, images: dict[str, str]) -> Router:
    router = Router(name="p6")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("p6:"))
    async def callback(query: CallbackQuery):
        raw = query.data or ""
        parts = raw.split(":")
        actor = query.from_user.id
        view = None
        if raw in {"p6:resume", "p6:detail"}:
            view = await service.resume(actor)
        elif len(parts) >= 3:
            try:
                version = int(parts[1])
            except ValueError:
                version = None
            if version is not None:
                operation = parts[2]
                if operation == "choice" and len(parts) == 4 and parts[3] in P6_CHOICES:
                    view = await service.choose_reward(actor, version, parts[3])
                elif len(parts) == 3 and operation in {
                    "cross_door", "inspect_before", "start_boss", "enter_chamber",
                    "retry", "inspect_after", "record_anchor", "return_ruins",
                    "report_alda", "report_oren",
                }:
                    view = await service.action(actor, version, operation)
                elif len(parts) == 3 and operation == "group":
                    try:
                        view = await service.propose_group_combat(actor, version)
                    except GroupError:
                        await query.answer(
                            "Não foi possível preparar o Grupo. Atualize a tela.",
                            show_alert=True,
                        )
                        return
        if view is None:
            view = await service.resume(actor)
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p6(view), images, edit=True)

    return router
