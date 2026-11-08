"""Telegram screens for Vínculos (GDD v1.6.0 §31). Player text is sent without parse mode."""

from __future__ import annotations

import re
from datetime import datetime
from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.social import (
    CardPage,
    PlayerCard,
    PublicProfile,
    RelatoView,
    RequestsView,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.social import MAX_BLOCKED, MAX_FRIENDS, PAGE_SIZE

_IMAGE = "links"
_REF = re.compile(r"\nRef: (so:[\w:-]+)$")

SEARCH_PROMPT = "Envie o nome, ou o começo do nome, do personagem.\n\nRef: so:search"

_ERRORS = {
    "no_character": "Crie um personagem para usar Vínculos.",
    "not_found": "Este personagem não está disponível.",
    "self": "Essa ação não vale para o seu próprio personagem.",
    "unavailable": "Essa ação não está disponível para este personagem.",
    "already_friends": "Vocês já são Amigos.",
    "incoming_pending": "Este personagem já enviou um pedido para você. Veja em Pedidos.",
    "friends_full": f"Sua lista já tem o máximo de {MAX_FRIENDS} Amigos.",
    "target_full": "Este personagem não pode receber pedidos agora.",
    "sent_full": "Você atingiu o limite de pedidos enviados.",
    "blocked_full": f"Sua lista já tem o máximo de {MAX_BLOCKED} Bloqueados.",
    "request_gone": "Este pedido não existe mais.",
    "query_invalid": "Envie de 2 a 16 caracteres.",
    "search_rate_limited": "Muitas buscas em pouco tempo. Tente de novo em um minuto.",
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


def parse_ref(text: str | None) -> str | None:
    match = _REF.search(text or "")
    return None if match is None else match.group(1)


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


_BACK = [_button("← Vínculos", "links:root")]


def _card_label(card: PlayerCard) -> str:
    return f"{card.name} · Nv.{card.level} · {card.character_class}"


def _paged(view: CardPage, title: str, empty: str, section: str) -> Screen:
    pages = max(1, ceil(view.total / PAGE_SIZE))
    text = f"{title} · {view.total}\n\n{empty}" if not view.cards else f"{title} · {view.total}"
    rows = [[_button(_card_label(card), f"so:p:{card.character_id.hex}")] for card in view.cards]
    navigation = []
    if view.page > 0:
        navigation.append(_button("←", f"so:{section}:{view.page - 1}"))
    if view.page + 1 < pages:
        navigation.append(_button("→", f"so:{section}:{view.page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append(_BACK)
    return Screen(text, _IMAGE, _keyboard(rows))


def render_friends(view: CardPage) -> Screen:
    return _paged(view, "🤝 Amigos", "Você ainda não tem Amigos. Use Buscar Jogador.", "friends")


def render_recents(view: CardPage) -> Screen:
    return _paged(
        view,
        "🕯️ Recentes",
        "Quem jogar com você em Grupo, Masmorra, Arena, Duelo ou Troca aparece aqui por 14 dias.",
        "recents",
    )


def render_blocked(view: CardPage) -> Screen:
    return _paged(view, "🚫 Bloqueados", "Nenhum personagem bloqueado.", "blocked")


def render_search_results(cards: tuple[PlayerCard, ...]) -> Screen:
    text = "🔎 Resultado da busca" if cards else "🔎 Nenhum personagem encontrado."
    rows = [[_button(_card_label(card), f"so:p:{card.character_id.hex}")] for card in cards]
    rows.append([_button("Buscar novamente", "so:search")])
    rows.append(_BACK)
    return Screen(text, _IMAGE, _keyboard(rows))


def render_requests(view: RequestsView) -> Screen:
    lines = [f"📩 Pedidos · {len(view.incoming)} recebidos · {len(view.outgoing)} enviados"]
    rows: list[list[InlineKeyboardButton]] = []
    # Telegram rejects a keyboard above 100 buttons; 30 + 20 requests would exceed it.
    for item in view.incoming[:PAGE_SIZE]:
        rows.append([_button(_card_label(item.card), f"so:p:{item.card.character_id.hex}")])
        rows.append(
            [
                _button("Aceitar", f"so:acc:{item.request_id.hex}"),
                _button("Recusar", f"so:dec:{item.request_id.hex}"),
            ]
        )
    for item in view.outgoing[:PAGE_SIZE]:
        rows.append(
            [
                _button(f"Enviado · {item.card.name}", f"so:p:{item.card.character_id.hex}"),
                _button("Cancelar", f"so:can:{item.request_id.hex}"),
            ]
        )
    if not rows:
        lines.extend(["", "Nenhum pedido pendente."])
    rows.append(_BACK)
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


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
    if view.blocked_by_me:
        rows.append([_button("Desbloquear", f"so:unb:{key}")])
    else:
        if view.incoming_request_id is not None:
            request = view.incoming_request_id.hex
            rows.append(
                [_button("Aceitar", f"so:acc:{request}"), _button("Recusar", f"so:dec:{request}")]
            )
        elif view.outgoing_request_id is not None:
            rows.append([_button("Cancelar Pedido", f"so:can:{view.outgoing_request_id.hex}")])
        elif view.is_friend:
            rows.append([_button("Remover Amigo", f"so:rm:{key}")])
        elif not view.blocked_me:
            rows.append([_button("Adicionar Amigo", f"so:add:{key}")])
        rows.append([_button("Bloquear", f"so:blk:{key}")])
    if view.history:
        rows.append([_button("Denunciar História", f"so:rep:{key}")])
    rows.append(_BACK)
    return rows


def render_confirm_block(view: PublicProfile) -> Screen:
    key = view.character_id.hex
    return Screen(
        f"🚫 Bloquear {view.name}?\n\n"
        "Vocês deixam de ser Amigos e os pedidos entre vocês são apagados. "
        "Depois disso não há convite direto de Grupo, Guilda, Troca ou Duelo entre vocês.",
        _IMAGE,
        _keyboard(
            [
                [_button("Confirmar Bloqueio", f"so:bly:{key}")],
                [_button("← Perfil", f"so:p:{key}")],
            ]
        ),
    )


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
