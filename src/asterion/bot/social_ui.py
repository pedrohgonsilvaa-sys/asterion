"""Telegram screens for the public Profile and Relatos. Player text is sent without parse mode.

Vínculos (Amigos, Pedidos, Recentes, Bloqueados e Buscar Jogador) saiu do produto por
decisão do autor; o Grupo segue independente.
"""

from __future__ import annotations

from datetime import datetime
from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.social import PublicProfile, RelatoView
from asterion.bot.creation_ui import Screen

_IMAGE = "links"
_ERRORS = {
    "no_character": "Crie um personagem primeiro.",
    "not_found": "Este personagem não está disponível.",
    "self": "Essa ação não vale para o seu próprio personagem.",
    "unavailable": "Essa ação não está disponível para este personagem.",
    "no_story": "Escreva uma História no Perfil antes de compartilhar.",
    "story_too_long": "Encurte a História para compartilhar.",
    "story_forbidden": "Remova links e menções da História para compartilhar.",
    "community_unavailable": "O tópico Relatos ainda não foi configurado.",
    "post_failed": "Não consegui publicar o Relato. A Recarga não foi usada.",
}


def error_text(code: str, available_at: datetime | None = None, now: datetime | None = None) -> str:
    if code == "share_cooldown" and available_at is not None and now is not None:
        minutes = max(1, ceil((available_at - now).total_seconds() / 60))
        return f"Compartilhar História estará disponível em {minutes} min."
    return _ERRORS.get(code, "Esta ação não está mais disponível.")


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


_BACK = [_button("← Menu", "menu:back")]


def render_public_profile(view: PublicProfile, notice: str | None = None) -> Screen:
    lines = [f"📇 {view.name}", ""]
    if notice:
        lines[:0] = [notice, ""]
    lines.append(f"Nv.{view.level} · Legado {view.legacy_level}")
    path = f" · {view.selected_path}" if view.selected_path else ""
    lines.append(f"{view.race} · {view.character_class}{path}")
    if view.guild:
        lines.append(f"🏰 Guilda · {view.guild}")
    if view.title:
        lines.append(f"🎖️ {view.title}")
    if view.elo:
        lines.append(f"⚔️ Elo · {view.elo}")
    lines.append(f"🏅 Feitos · {view.feats}")
    if view.history:
        lines.extend(["", "📖 História", "", view.history])
    return Screen("\n".join(lines), _IMAGE, _keyboard(_profile_rows(view)))


def _profile_rows(view: PublicProfile) -> list[list[InlineKeyboardButton]]:
    key = view.character_id.hex
    rows: list[list[InlineKeyboardButton]] = []
    if view.is_self:
        return [_BACK]
    if view.history:
        rows.append([_button("Denunciar História", f"so:rep:{key}")])
    rows.append(_BACK)
    return rows


def render_relato(view: RelatoView, notice: str | None = None) -> Screen:
    lines = [f"📖 Relato de {view.author_name}", "", view.body]
    if notice:
        lines[:0] = [notice, ""]
    return Screen(
        "\n".join(lines),
        _IMAGE,
        _keyboard(
            [
                [_button("Abrir Perfil", f"so:p:{view.character_id.hex}")],
                [_button("Denunciar Relato", f"so:repr:{view.relato_id.hex}")],
                _BACK,
            ]
        ),
    )


def relato_message(view: RelatoView) -> str:
    return (
        f"📖 Relato de {view.author_name}\n\n{view.body}\n\n"
        "História escrita pelo jogador. Não é lore oficial de Asterion."
    )


def relato_keyboard(link: str | None) -> InlineKeyboardMarkup | None:
    if link is None:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Abrir no Bot", url=link)]]
    )
