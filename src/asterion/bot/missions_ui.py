"""Quadro de Missões do Bloco UI 1 v1.1.0 §6: entrada, Principais e Secundárias.

O handler de Missões continua calculando o estado de cada Missão nos serviços. Este
módulo só reparte o resultado em telas: a entrada com as três categorias, a lista de
Missões Principais e a lista de Missões Secundárias. Objetivos, progresso,
acompanhamento e reaceite ficam nas telas próprias de cada Missão.
"""

from __future__ import annotations

import re
from html import escape

from aiogram.types import InlineKeyboardButton

from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import back, blocks, button, keyboard, narrative

ENTRY = "world:missions"
MAIN = "world:missions:main"
SIDE = "world:missions:side"
SECTIONS = frozenset({ENTRY, MAIN, SIDE})
CONTRACTS = "ctr:root"
# Contrato Mestre de Telas UI v1.0.0 §19: Missões entram pelo Mural do Refúgio.
BACK = "refuge:local"
SIDE_MARKER = "\n\n📖 Missões Secundárias\n\n"

ENTRY_TEXT = (
    "As missões registram os acontecimentos, objetivos e tarefas encontrados ao longo da "
    "jornada. Algumas fazem parte da Campanha, enquanto outras surgem de pessoas, "
    "acontecimentos e oportunidades espalhadas pelas Terras do Ocaso."
)
EMPTY_TEXT = (
    "Ainda não há novas missões disponíveis. Novos acontecimentos, descobertas e avanços "
    "da jornada podem revelar outras oportunidades."
)
MAIN_TEXT = (
    "As missões principais conduzem a Campanha e revelam gradualmente os acontecimentos "
    "ligados às Cinzas da Ruptura. Seu progresso acompanha a jornada do personagem e não "
    "pode ser abandonado."
)
SIDE_TEXT = (
    "Além da Campanha, diferentes acontecimentos podem levar a tarefas e histórias "
    "paralelas. Essas missões podem ser acompanhadas ou abandonadas conforme suas próprias "
    "regras."
)
# "🔥 Missão Principal\n\n📜 Vozes na Estrada · Em Andamento" ou
# "🔥 Missão Principal · Entre Galhos Suspensos · Disponível".
_PRINCIPAL = re.compile(
    r"🔥 Missão Principal(?:\n\n| · )(?:\S+ )?(?P<title>[^·\n]+?) · "
    r"(?P<state>Em Andamento|Disponível)"
)
_ENTRY_LINE = re.compile(r"^(?:\d+ )?(?P<icon>\S+) (?P<title>[^·]+?) · (?P<state>.+)$")
_GROUPS = (
    ("Ativas", ("Em Andamento",)),
    ("Disponíveis", ("Disponível",)),
    ("Concluídas", ("Concluída",)),
)


def split_board(
    text: str,
    rows: list[list[InlineKeyboardButton]],
    secondary_rows: list[list[InlineKeyboardButton]],
) -> tuple[str, list[list[InlineKeyboardButton]]]:
    """Texto e botões das Principais: o quadro sem o bloco das Secundárias."""
    principal = text
    if SIDE_MARKER in text:
        before, after = text.split(SIDE_MARKER, 1)
        principal = before + ("\n\n" + after.split("\n\n", 1)[1] if "\n\n" in after else "")
    side_ids = {id(row) for row in secondary_rows}
    return principal, [row for row in rows if id(row) not in side_ids]


def _principal_title_rows(text: str, rows):
    """Troca o rótulo genérico ``Principal`` pelo título da Missão (``📖 Vozes na Estrada``)."""
    titles = [match.group("title").strip() for match in _PRINCIPAL.finditer(text)]
    relabeled = []
    for row in rows:
        new_row = []
        for item in row:
            label = item.text
            if label in {"Principal", "Iniciar Missão"} and titles:
                label = f"📖 {titles.pop(0)}"
            elif not label.startswith(("📖", "📜", "🔥", "✅")):
                label = f"📖 {label}"
            new_row.append(InlineKeyboardButton(text=label, callback_data=item.callback_data))
        relabeled.append(new_row)
    return relabeled


def _principal_lines(text: str) -> list[str]:
    """Linhas de estado (concluídas/bloqueadas) que não viram botão."""
    lines = []
    for chunk in text.split("\n\n")[1:]:
        chunk = chunk.strip()
        if not chunk or chunk.startswith(("🔥 Missão Principal", "Acompanhe")):
            continue
        if _PRINCIPAL.search(f"🔥 Missão Principal\n\n{chunk}") and " · Em Andamento" in chunk:
            continue
        if chunk.startswith(("✅", "🔒")):
            lines.append(escape(chunk.split("\n", 1)[0]))
    return lines


def has_missions(principal_rows, secondary_entries) -> bool:
    return bool(principal_rows) or bool(secondary_entries)


def render_entry(*, any_mission: bool) -> Screen:
    if not any_mission:
        return Screen(
            blocks("📜 <b>Missões</b>", narrative(EMPTY_TEXT)),
            "missions",
            keyboard(
                [button("📜 Contratos", CONTRACTS)],
                back(BACK),
            ),
            "HTML",
        )
    return Screen(
        blocks("📜 <b>Missões</b>", narrative(ENTRY_TEXT)),
        "missions",
        keyboard(
            [button("📖 Missões Principais", MAIN)],
            [button("🗺️ Missões Secundárias", SIDE)],
            [button("📜 Contratos", CONTRACTS)],
            back(BACK),
        ),
        "HTML",
    )


def render_main(text: str, rows) -> Screen:
    active_rows = _principal_title_rows(text, rows)
    other = _principal_lines(text)
    parts = ["📖 <b>Missões Principais</b>", narrative(MAIN_TEXT)]
    if active_rows:
        parts.append("<b>Em andamento</b>")
    if other:
        parts.append("\n".join(other))
    if not active_rows and not other:
        parts.append(narrative(EMPTY_TEXT))
    return Screen(blocks(*parts), "missions", keyboard(*active_rows, back(ENTRY)), "HTML")


def render_side(entries: list[tuple[str, str | None]]) -> Screen:
    """Secundárias agrupadas por estado; cada botão abre a tela própria da Missão."""
    grouped: dict[str, list[InlineKeyboardButton]] = {label: [] for label, _ in _GROUPS}
    locked: list[str] = []
    reaccept: list[InlineKeyboardButton] = []
    for line, callback in entries:
        match = _ENTRY_LINE.match(line.strip())
        if match is None:
            continue
        title, state = match.group("title").strip(), match.group("state").strip()
        if callback is None:
            locked.append(f"🔒 {escape(title)} · {escape(state)}")
            continue
        if state.startswith("Disponível para reaceite"):
            reaccept.append(button(f"▶️ {title}", callback))
            continue
        for label, states in _GROUPS:
            if any(state.startswith(prefix) for prefix in states):
                grouped[label].append(button(f"📜 {title}", callback))
                break
    parts = ["🗺️ <b>Missões Secundárias</b>", narrative(SIDE_TEXT)]
    icons = {"Ativas": "📜", "Disponíveis": "📜", "Concluídas": "✅"}
    rows: list[list[InlineKeyboardButton]] = []
    for label, _ in _GROUPS:
        rows.extend(
            [InlineKeyboardButton(text=f"{icons[label]} {item.text.split(' ', 1)[1]}",
                                  callback_data=item.callback_data)]
            for item in grouped[label]
        )
    rows.extend([item] for item in reaccept)
    if grouped["Ativas"]:
        parts.append("<b>Ativas</b>")
    if locked:
        parts.append("\n".join(locked))
    if not rows and not locked:
        parts.append(narrative(EMPTY_TEXT))
    return Screen(blocks(*parts), "missions", keyboard(*rows, back(ENTRY)), "HTML")
