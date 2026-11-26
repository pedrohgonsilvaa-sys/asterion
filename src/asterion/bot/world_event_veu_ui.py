"""Telegram: telas de A Ruptura do Véu (textos e leiaute da especificação v1.3.0 §18–§22)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.world_event_veu_views import (
    NucleusScreen,
    PanelView,
    ParticipantsPage,
)
from asterion.bot.character_surfaces_ui import CLASS_NAMES
from asterion.bot.combat_ui import hp_bar
from asterion.bot.creation_ui import Screen
from asterion.domain import world_event_veu as ev

IMAGE = "world_events"
OPENING_TEXT = "Uma ruptura surgiu no Véu.\nAlgo está atravessando."
CHOOSE_TEXT = "Uma ruptura surgiu no Véu.\nEscolha um Núcleo para participar."
SPECIAL_ICONS = {"A": "🌫️", "D": "🦴", "E": "🕳️"}
ACTION_REGISTERED = "✅ Ação registrada."
# Entrada de O Despertar dos Flagelos (evento permanente) na mesma tela de Eventos.
FLAGELO_ENTRY = ("⚔️ O Despertar dos Flagelos", "flg:hub")

_ERRORS = {
    "no_character": "Crie um personagem antes de participar do Evento.",
    "event_not_running": "O Evento não está em andamento.",
    "event_not_open": "O Evento não está aberto.",
    "entry_window_closed": "A entrada neste Evento já foi encerrada.",
    "participant_left": "Você encerrou sua participação neste Evento.",
    "nucleus_not_active": "Este Núcleo não está mais ativo.",
    "nucleus_not_available": "Este Núcleo não está disponível.",
    "reentry_pending": "Sua reentrada ainda não abriu.",
    "decision_window_closed": "A janela desta rodada já fechou.",
    "waiting_next_round": "Você poderá agir na próxima rodada.",
    "not_in_nucleus": "Você não está neste Núcleo.",
    "action_already_registered": "Sua ação desta rodada já foi registrada.",
    "no_ally_target": "Não há aliado disponível para essa Arte.",
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Não foi possível concluir essa ação.")


def _fmt(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _clock(seconds: int) -> str:
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _bar(hp: int, max_hp: int) -> str:
    return hp_bar(Decimal(hp), Decimal(max_hp), color="🟥")


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _class_name(character_class: str) -> str:
    return CLASS_NAMES.get(character_class, character_class)


def _icon(key: str) -> str:
    return SPECIAL_ICONS.get(key, "🌫️")


def render_panel(view: PanelView, *, now: datetime | None = None) -> Screen:
    if view.kind == "scheduled":
        return _render_scheduled(view)
    if view.kind == "final":
        return _render_final(view)
    return _render_active(view)


EVENTS_TEXT = (
    "Eventos especiais acontecem em diferentes momentos de Asterion e podem alterar o "
    "estado das Regiões ou abrir novas oportunidades para os aventureiros."
)
RUPTURE_TEXT = (
    "Em determinados momentos do dia, uma Ruptura manifesta-se em Asterion e altera "
    "temporariamente o comportamento do Véu. Os aventureiros podem acompanhar o horário do "
    "evento e verificar se a última Ruptura foi concluída."
)
RUPTURE_FOOTER = (
    "Quando uma Ruptura acontece, o Véu permanece instável por um período limitado antes "
    "de desaparecer novamente."
)
_BACK_EVENTS = [InlineKeyboardButton(text="↩️ Retornar", callback_data="wev:hub")]


def render_events_menu() -> Screen:
    """Menu de Eventos (decisão do autor 2026-11-26 §33.1)."""
    return Screen(
        f"🌌 <b>Eventos</b>\n\n<i>{escape(EVENTS_TEXT)}</i>",
        IMAGE,
        InlineKeyboardMarkup(
            inline_keyboard=[
                [_button("🔥 Despertar", "flg:hub"), _button("🕳️ Ruptura", "veu:hub")],
                [_button("↩️ Retornar", "menu:back")],
            ]
        ),
        "HTML",
    )


def _render_scheduled(view: PanelView) -> Screen:
    """Ruptura do Véu fora do horário (§33.3): só o horário real da próxima Ruptura."""
    local = view.next_slot.astimezone(ev.EVENT_TIMEZONE) if view.next_slot else None
    parts = ["🕳️ <b>Ruptura do Véu</b>", f"<i>{escape(RUPTURE_TEXT)}</i>"]
    if local is not None:
        parts.append(f"🕐 <b>Próxima Ruptura</b> · <code>{local:%H:%M}</code>")
    parts.append(f"<i>{escape(RUPTURE_FOOTER)}</i>")
    return Screen(
        "\n\n".join(parts), IMAGE, InlineKeyboardMarkup(inline_keyboard=[_BACK_EVENTS]), "HTML"
    )


def _render_active(view: PanelView) -> Screen:
    running = view.state == ev.EventState.EM_ANDAMENTO.value
    lines = [
        "🌫️ <b>A Ruptura do Véu</b>",
        "",
        "⏱️ Evento em andamento" if running else "⏱️ Evento aberto",
        f"⚔️ Fase atual · <code>{view.phase}/{ev.PHASE_COUNT}</code>",
        f"⏳ Tempo restante · <code>{_clock(view.seconds_left)}</code>",
        "",
        *escape(CHOOSE_TEXT if running else OPENING_TEXT).split("\n"),
    ]
    rows: list[list[InlineKeyboardButton]] = []
    if view.nuclei:
        lines.extend(["", "🌫️ Núcleos Ativos"])
        for line in view.nuclei:
            lines.extend(
                [
                    "",
                    f"{_icon(line.key)} {escape(line.name)}",
                    f"👥 {line.participants} participantes",
                    f"🎯 {escape(line.objective.capitalize())}",
                ]
            )
            rows.append([_button(f"{_icon(line.key)} {line.name}", f"veu:n:{line.key}")])
    rows.append(_BACK_EVENTS)
    return Screen("\n".join(lines), IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


def _render_final(view: PanelView) -> Screen:
    victory = view.victory
    lines = ["🌫️ <b>A Ruptura do Véu</b>", ""]
    if victory:
        lines.extend(
            [
                "A abertura começa a se fechar.",
                "",
                "As criaturas que ainda estavam do outro lado desaparecem da margem da ruptura.",
                "",
                "Por alguns instantes, o lugar parece normal.",
                "",
                "Então uma última fissura se fecha como uma ferida.",
                "",
                "<b>O Véu permanece. Por enquanto.</b>",
            ]
        )
    else:
        lines.extend(
            [
                "A ruptura não foi contida a tempo.",
                "",
                "A manifestação desaparece da vista, mas não se fecha completamente.",
                "",
                "<b>O Véu permanece aberto em algum lugar que vocês não conseguem alcançar.</b>",
            ]
        )
    reward = view.reward or {}
    if view.eligible and reward:
        lines.extend(["", f"🪙 Coroas · <code>{_fmt(int(reward.get('crowns', 0)))}</code>"])
        lines.append(f"✨ XP · <code>{_fmt(int(reward.get('xp', 0)))}</code>")
        for item in reward.get("items", ()):
            lines.append(f"📦 {escape(str(item['name']))} × {item['quantity']}")
    rows = [_BACK_EVENTS]
    return Screen("\n".join(lines), IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


def render_nucleus(view: NucleusScreen) -> Screen:
    lines = [
        f"{_icon(view.key)} <b>{escape(view.name)}</b>",
        "",
        f"🌐 <code>Turno {view.round_number}</code> · ⏱️ <code>{_clock(view.seconds_left)}</code>",
    ]
    for enemy in view.enemies:
        lines.extend(
            [
                "",
                f"🕳️ <b>{escape(enemy.name)}</b>",
                f"❤️ <code>{_fmt(enemy.hp)}/{_fmt(enemy.max_hp)}</code>",
                _bar(enemy.hp, enemy.max_hp),
            ]
        )
    lines.extend(
        [
            "",
            f"🧙 <b>{escape(view.self_name)}</b>",
            f"❤️ <code>{_fmt(view.self_hp)}/{_fmt(view.self_max_hp)}</code>",
            _bar(view.self_hp, view.self_max_hp),
        ]
    )
    if view.telegraphs:
        names = ", ".join(escape(_enemy_name(view, code)) for code in view.telegraphs)
        lines.extend(["", f"⚠️ <i>{names} prepara um ataque.</i>"])
    if view.support:
        lines.extend(["", "🤝 <b>Suporte:</b>"])
        for entry in view.support:
            lines.append(_support_line(entry))
    if view.history:
        lines.extend(["", "📜 <b>Histórico:</b>"])
        for entry in view.history:
            lines.append(_history_line(entry))
    rows: list[list[InlineKeyboardButton]] = []
    if view.state == ev.NucleusState.ATIVA.value and not view.removed:
        key = view.key
        rn = view.round_number
        rows.append([_button("⚔️ Atacar", f"veu:a:atk:{key}:{rn}")])
        rows.append([_button("🛡️ Defender", f"veu:a:def:{key}:{rn}")])
        for slot in view.art_slots:
            rows.append([_button(f"Arte {slot}", f"veu:a:art{slot}:{key}:{rn}")])
        rows.append([_button("👥 Participantes", f"veu:p:{key}:0")])
    rows.append([_button("↩️ Núcleos", "veu:back")])
    return Screen("\n".join(lines), IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


_SUPPORT_TEXT = {
    "heal": ("✨", "cura", ""),
    "barrier": ("🕸️", "ergue barreira", "em "),
    "protection": ("🛡️", "protege", ""),
}


def _support_line(entry) -> str:
    """Só o que foi registrado; sem valores (adendo C: o resultado vai ao Histórico)."""
    icon, verb, preposition = _SUPPORT_TEXT[entry.kind]
    target = escape(entry.target) if entry.target else "todos os aliados"
    return f"{icon} {escape(entry.source)} <b>{verb}</b> {preposition}{target}."


def _enemy_name(view: NucleusScreen, code: str) -> str:
    return next((enemy.name for enemy in view.enemies if enemy.code == code), code)


def _history_line(entry) -> str:
    if entry.kind == "barrier_absorbed":
        return f"🛡️ A barreira absorveu <b>{_fmt(entry.amount)} de dano</b>."
    return f"⚔️ {escape(entry.name)} sofreu <b>{_fmt(entry.amount)} de dano</b>."


def render_targets(view: NucleusScreen, action: str) -> Screen:
    """Alvo só quando há dois ou mais válidos (§21)."""
    rows = [
        [_button(f"🕳️ {enemy.name}", f"veu:t:{action}:{view.key}:{view.round_number}:{enemy.code}")]
        for enemy in view.enemies
        if not enemy.defeated
    ]
    rows.append([_button("↩️ Retornar", f"veu:n:{view.key}")])
    return Screen(
        "🎯 <b>Escolha o alvo</b>", IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML"
    )


def render_ally_targets(page: ParticipantsPage, kind: str, round_number: int) -> Screen:
    """Alvo aliado de uma Arte de suporte: participantes do Núcleo, 5 por página (§20, §21)."""
    key = page.key
    rows = [
        [
            _button(
                f"{row.name} · {_fmt(row.hp)}/{_fmt(row.max_hp)}",
                f"veu:t:{kind}:{key}:{round_number}:c{row.character_id.hex}",
            )
        ]
        for row in page.rows
        if row.character_id is not None
    ]
    nav = []
    if page.page > 0:
        nav.append(_button("⬅️ Anterior", f"veu:ta:{kind}:{key}:{round_number}:{page.page - 1}"))
    if page.page < page.pages - 1:
        nav.append(_button("➡️ Próxima", f"veu:ta:{kind}:{key}:{round_number}:{page.page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([_button("↩️ Retornar", f"veu:n:{key}")])
    return Screen(
        "🎯 <b>Escolha o alvo</b>", IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML"
    )


def render_participants(page: ParticipantsPage) -> Screen:
    lines = ["👥 <b>Participantes</b>"]
    for row in page.rows:
        lines.extend(
            [
                "",
                f"🌫️ {escape(row.name)} · {escape(_class_name(row.character_class))}",
                f"❤️ {_fmt(row.hp)}/{_fmt(row.max_hp)}",
                _bar(row.hp, row.max_hp),
            ]
        )
    nav = []
    if page.page > 0:
        nav.append(_button("⬅️ Anterior", f"veu:p:{page.key}:{page.page - 1}"))
    if page.page < page.pages - 1:
        nav.append(_button("➡️ Próxima", f"veu:p:{page.key}:{page.page + 1}"))
    rows = [nav] if nav else []
    rows.append([_button("↩️ Retornar", f"veu:n:{page.key}")])
    return Screen("\n".join(lines), IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


def render_notice(minutes: int) -> Screen:
    """Avisos pré-evento (adendo B): informam, não recomendam."""
    if minutes == 10:
        quote = "Uma ruptura surgiu no Véu. Algo desconhecido está atravessando para este lado."
        button = "🌫️ Ver Evento"
    else:
        quote = "O Véu está cedendo. A manifestação se aproxima."
        button = "🌫️ Entrar no Evento"
    text = (
        "🌫️ <b>A Ruptura do Véu</b>\n\n"
        f"<i>{escape(quote)}</i>\n\n"
        f"⏰ O evento começa em <code>{minutes} minutos</code>."
    )
    return Screen(
        text,
        IMAGE,
        InlineKeyboardMarkup(inline_keyboard=[[_button(button, "veu:hub")]]),
        "HTML",
    )
