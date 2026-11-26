"""Prompts de entrada temporários (decisão do autor 2026-11-26 §2 e §26.3).

A tela atual vira o pedido de texto, como na criação de personagem: não se envia uma
mensagem nova com quote/ForceReply. Quando o jogador responde, a mensagem dele é
apagada e a mesma tela é editada com o resultado. Qualquer botão pressionado depois
cancela o pedido (``PromptResetMiddleware``), então nada fica pendurado no chat.

O estado é só de interface e fica em memória: se o processo reiniciar, a tela continua
com ``↩️ Retornar`` e o jogador abre o pedido de novo. Nenhuma regra de jogo depende dele.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from asterion.bot.creation_ui import Screen

PROMPT_TTL_SECONDS = 15 * 60


@dataclass(slots=True)
class PendingPrompt:
    kind: str
    chat_id: int
    message_id: int
    data: dict[str, Any] = field(default_factory=dict)
    expires_at: float = 0.0


class PromptStore:
    def __init__(self) -> None:
        self._items: dict[int, PendingPrompt] = {}

    def open(
        self, actor: int, kind: str, message: Message, data: dict[str, Any] | None = None
    ) -> None:
        self._items[actor] = PendingPrompt(
            kind,
            message.chat.id,
            message.message_id,
            dict(data or {}),
            time.monotonic() + PROMPT_TTL_SECONDS,
        )

    def follow(
        self,
        actor: int,
        prompt: PendingPrompt,
        *,
        kind: str | None = None,
        message_id: int | None = None,
    ) -> None:
        """Mantém (ou avança) o pedido na mesma tela depois de uma resposta."""
        self._items[actor] = PendingPrompt(
            kind or prompt.kind,
            prompt.chat_id,
            message_id or prompt.message_id,
            dict(prompt.data),
            time.monotonic() + PROMPT_TTL_SECONDS,
        )

    def get(self, actor: int, prefix: str = "") -> PendingPrompt | None:
        item = self._items.get(actor)
        if item is None:
            return None
        if item.expires_at < time.monotonic():
            self._items.pop(actor, None)
            return None
        return item if item.kind.startswith(prefix) else None

    def close(self, actor: int) -> PendingPrompt | None:
        return self._items.pop(actor, None)


PROMPTS = PromptStore()


class HasPrompt(Filter):
    """Mensagem de texto de quem tem um pedido aberto com esse prefixo de tipo."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    async def __call__(self, message: Message) -> bool | dict[str, Any]:
        if message.from_user is None or not message.text or message.text.startswith("/"):
            return False
        pending = PROMPTS.get(message.from_user.id, self.prefix)
        return {"prompt": pending} if pending is not None else False


class PromptResetMiddleware(BaseMiddleware):
    """Qualquer botão encerra o pedido aberto; o handler pode abrir outro em seguida."""

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is not None:
            PROMPTS.close(event.from_user.id)
        return await handler(event, data)


async def consume_reply(message: Message) -> None:
    """Apaga a resposta do jogador para que o texto digitado não fique no chat."""
    try:
        await message.delete()
    except TelegramAPIError:
        pass


async def show_on_prompt(
    message: Message, prompt: PendingPrompt, screen: Screen, images: dict[str, str]
) -> int | None:
    """Edita a tela que fez o pedido; se ela sumiu, envia a tela como mensagem nova."""
    from asterion.bot.creation_handlers import edit_screen, present

    if await edit_screen(message, prompt.message_id, screen, images):
        return prompt.message_id
    return await present(message, screen, images)
