"""Telegram adapters for Apoiar Asterion (GDD §35): shop, terms, checkout, orders."""

from __future__ import annotations

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.payments import PaymentError, PaymentService
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.shop_ui import (
    error_text,
    render_checkout,
    render_orders,
    render_shop,
    render_terms,
)
from asterion.domain.payments import PRODUCTS


def shop_router(payments: PaymentService, images: dict[str, str]) -> Router:
    router = Router(name="shop")

    async def show(query: CallbackQuery, screen: Screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def dispatch(query: CallbackQuery, actor: int) -> None:
        data = query.data or ""
        parts = data.split(":")
        if data == "pay:root":
            await show(query, render_shop(await payments.shop(actor)))
        elif data == "pay:orders":
            await show(query, render_orders(await payments.orders(actor), datetime.now(UTC)))
        elif len(parts) == 3 and parts[1] == "t" and parts[2] in PRODUCTS:
            price = payments.config.price(parts[2])
            if price is None or payments.provider is None:
                raise PaymentError("payments_disabled")
            await show(query, render_terms(parts[2], price, payments.config.link_minutes))
        elif len(parts) == 4 and parts[1] == "b":
            # The accepted terms version travels in the button: old buttons fail.
            order = await payments.create_order(actor, parts[2], parts[3])
            await show(query, render_checkout(order))
        else:
            raise PaymentError("unknown")

    @router.callback_query(F.data.startswith("pay:"))
    async def callback(query: CallbackQuery) -> None:
        try:
            await dispatch(query, query.from_user.id)
        except PaymentError as exc:
            await query.answer(error_text(exc.code), show_alert=True)
            return
        await query.answer()

    return router
