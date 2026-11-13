"""Adaptador Telegram dos Contratos Regionais (Documento B)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.contracts import ContractError, ContractService
from asterion.bot.contracts_ui import (
    error_text,
    render_abandon,
    render_board,
    render_contract,
    render_detail,
    render_mine,
)
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import unpack


def contracts_router(service: ContractService, images: dict[str, str]) -> Router:
    router = Router(name="contracts")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def handle(query: CallbackQuery, actor: int, parts: list[str]) -> None:
        action = parts[1]
        if action in {"root", "b"}:
            await show(query, render_board(await service.board(actor)))
            return
        if action == "m":
            await show(query, render_mine(await service.mine(actor)))
            return
        instance_id, version = unpack(parts[2]), int(parts[3])
        if action == "d":
            view = await service.get(actor, instance_id)
            if view.version != version:
                raise ContractError("stale")
            await show(query, render_detail(view))
        elif action == "a":
            view = await service.accept(actor, instance_id, version)
            await show(query, render_contract(view))
        elif action == "o":
            await show(query, render_contract(await service.get(actor, instance_id)))
        elif action == "g":
            view = await service.get(actor, instance_id)
            if view.version != version:
                raise ContractError("stale")
            if view.definition.contract_type in {"ENTREGA", "INVESTIGACAO"}:
                try:
                    view = await service.act(actor, instance_id, version)
                except ContractError as exc:
                    if exc.code != "wrong_place":
                        raise
                    await show(
                        query,
                        render_contract(view, f"Vá até {view.place} para cumprir o objetivo."),
                    )
                    return
            else:
                await show(
                    query,
                    render_contract(view, "Cumpra o objetivo na região; o progresso é automático."),
                )
                return
            await show(query, render_contract(view))
        elif action == "x":
            view = await service.get(actor, instance_id)
            if view.version != version:
                raise ContractError("stale")
            await show(query, render_abandon(view))
        elif action == "z":
            await service.abandon(actor, instance_id, version)
            await show(query, render_board(await service.board(actor), "Contrato abandonado."))
        elif action == "r":
            await service.claim(actor, instance_id, version)
            await show(query, render_board(await service.board(actor), "Recompensa resgatada."))
        else:
            raise ValueError(action)

    @router.callback_query(F.data.startswith("ctr:"))
    async def contracts(query: CallbackQuery):
        try:
            await handle(query, query.from_user.id, (query.data or "").split(":"))
        except ContractError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        except (IndexError, KeyError, ValueError):
            await query.answer(error_text("stale"), show_alert=True)
            return
        await query.answer()

    return router
