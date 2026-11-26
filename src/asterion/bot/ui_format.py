"""Padrão visual global do Bloco UI 1 (v1.1.0 §1), em HTML do Telegram.

Títulos em negrito, narrativas em itálico, valores numéricos em monoespaçado,
barras de 10 segmentos, bloco de Recompensas sem linha vazia e retorno
``↩️ Voltar``. Só formatação: nenhum número de jogo nasce aqui.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.domain.creation import STARTING_CHARACTER_TITLE

BACK_LABEL = "↩️ Voltar"
BAR_SEGMENTS = 10
HP_FILL, VIGOR_FILL, XP_FILL = "🟥", "🟨", "🟦"
REWARDS_HEADING = "🎁 <b>Recompensas:</b>"


def number(value: int) -> str:
    """``1250`` → ``1.250`` (separador de milhar brasileiro)."""
    return f"{int(value):,}".replace(",", ".")


def title(text: str) -> str:
    return f"<b>{escape(text)}</b>"


def narrative(text: str) -> str:
    return f"<i>{escape(text)}</i>"


def mono(text: str) -> str:
    return f"<code>{escape(text)}</code>"


def bar(current, maximum, fill: str) -> str:
    """Barra de 10 segmentos; qualquer valor positivo mostra ao menos um."""
    segments = BAR_SEGMENTS
    filled = min(segments, max(0, int(current * segments / maximum))) if maximum else 0
    if current > 0 and maximum:
        filled = max(1, filled)
    return fill * filled + "⬜" * (segments - filled)


def field(emoji: str, label: str, value: str) -> str:
    """``⭐ **Nível** · `10` ``."""
    return f"{emoji} <b>{escape(label)}</b> · {mono(value)}"


def reward_line(emoji: str, value: str) -> str:
    """Item de recompensa: valor em monoespaçado, sem ``+`` nem ``x3``."""
    return f"{emoji} {mono(value)}"


_LEGACY_TOTAL = re.compile(r"^(\S+) (XP|Coroas) · ([\d.]+)$")
_LEGACY_ITEM = re.compile(r"^📦 (.+) · (\d+)$")


def reward_html(line: str) -> str:
    """Converte uma linha de recompensa de texto ``✨ XP · 120`` para ``✨ `120 XP` ``.

    Linhas sem quantidade (Equipamento, Runa, Receita) só são escapadas.
    """
    total = _LEGACY_TOTAL.match(line)
    if total:
        emoji, label, value = total.groups()
        emoji = "🪙" if label == "Coroas" else emoji
        return f"{emoji} {mono(f'{value} {label}')}"
    item = _LEGACY_ITEM.match(line)
    if item:
        name, quantity = item.groups()
        return f"📦 {mono(f'{quantity} {name}')}"
    return escape(line)


def rewards(lines: Iterable[str]) -> str:
    """``🎁 Recompensas:`` com os itens logo abaixo, sem linha em branco."""
    items = [line for line in lines if line]
    return "\n".join([REWARDS_HEADING, *items]) if items else ""


def button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def back(callback: str) -> list[InlineKeyboardButton]:
    return [button(BACK_LABEL, callback)]


def column(*buttons: InlineKeyboardButton) -> list[list[InlineKeyboardButton]]:
    return [[item] for item in buttons]


def pairs(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    return [buttons[index : index + 2] for index in range(0, len(buttons), 2)]


def keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row])


def blocks(*parts: str | None) -> str:
    """Blocos separados por uma linha; blocos vazios não deixam espaço sobrando."""
    return "\n\n".join(part for part in parts if part)


# Identidade padrão do personagem. Sem Título escolhido nem persistido, vale o Título
# inicial persistido (decisão do autor, HUD do Refúgio).
DEFAULT_TITLE = STARTING_CHARACTER_TITLE
_ROMAN = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))


def roman(value: int) -> str:
    result = ""
    for size, symbol in _ROMAN:
        while value >= size:
            result += symbol
            value -= size
    return result


def identity(
    *,
    emoji: str,
    name: str,
    level: int,
    legacy_level: int = 0,
    guild_tag: str | None = None,
    title: str | None = None,
) -> str:
    """``🗡️ **[RSN] Oheen** · `Nv. 1 · Legado I` `` e ``🎖️ `Caminhante das Cinzas` ``.

    TAG da Guilda e nome em negrito; sem Guilda, a TAG some; sem Legado, ``· Legado I``
    some; o Título fica em monoespaçado e, sem Título, vale o Título inicial persistido.
    """
    tag = f"[{guild_tag}] " if guild_tag else ""
    level_text = f"Nv. {level}"
    if legacy_level > 0:
        level_text += f" · Legado {roman(legacy_level)}"
    return "\n".join(
        (
            f"{emoji} <b>{escape(tag + name)}</b> · {mono(level_text)}",
            f"🎖️ {mono(title or DEFAULT_TITLE)}",
        )
    )
