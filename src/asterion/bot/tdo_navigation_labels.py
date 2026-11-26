"""Rótulo de retorno nas Terras do Ocaso (UI v1.6.2, seção 66.1 item 6).

Nas Terras do Ocaso o Refúgio do Ocaso substitui o Menu Principal. Toda navegação
de retorno antes rotulada ``← Menu``, ``← Campanha`` ou ``← Aventura`` usa o rótulo
``↩️ Retornar`` (decisão do autor 2026-11-26 §2). O destino não muda: ``← Menu`` e
``← Campanha`` abrem o Refúgio na Região; ``← Aventura`` abre o submenu Aventura.
Fora das Terras do Ocaso nada é alterado.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.methods import TelegramMethod
from aiogram.methods.base import Response, TelegramType
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

TDO_REGION = "Terras do Ocaso"
BACK_TO_REFUGE_LABEL = "↩️ Retornar"

# (rótulo antigo, callback) -> mesmo callback com o rótulo do Refúgio.
_LEGACY_RETURNS = frozenset(
    {
        ("← Menu", "menu:back"),
        ("← Campanha", "world:adventure"),
        ("← Aventura", "adv:hub"),
    }
)

RegionLookup = Callable[[int], Awaitable[str | None]]


def has_legacy_return(markup: InlineKeyboardMarkup) -> bool:
    return any(
        (button.text, button.callback_data) in _LEGACY_RETURNS
        for row in markup.inline_keyboard
        for button in row
    )


def relabel_returns_to_refuge(markup: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Cópia do teclado com os retornos antigos rotulados ``↩️ Retornar``."""
    rows = [
        [
            InlineKeyboardButton(text=BACK_TO_REFUGE_LABEL, callback_data=button.callback_data)
            if (button.text, button.callback_data) in _LEGACY_RETURNS
            else button
            for button in row
        ]
        for row in markup.inline_keyboard
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


class TdoReturnLabelMiddleware(BaseRequestMiddleware):
    """Reescreve o rótulo de retorno dos teclados enviados a quem está nas Terras do Ocaso."""

    def __init__(self, region_of: RegionLookup) -> None:
        self._region_of = region_of

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        markup = getattr(method, "reply_markup", None)
        chat_id = getattr(method, "chat_id", None)
        if (
            isinstance(markup, InlineKeyboardMarkup)
            and isinstance(chat_id, int)
            and chat_id > 0
            and has_legacy_return(markup)
        ):
            try:
                region = await self._region_of(chat_id)
            except Exception:  # noqa: BLE001 - o rótulo nunca pode bloquear a resposta
                region = None
            if region == TDO_REGION:
                _set_markup(method, relabel_returns_to_refuge(markup))
        return await make_request(bot, method)


def _set_markup(method: Any, markup: InlineKeyboardMarkup) -> None:
    method.reply_markup = markup
