"""Telas do hub das Terras do Ocaso v1.0.18 (UI v1.6.1, secao 66).

Estrutura de telas, rótulos e textos de interface. Regras e textos canônicos da
Câmara vêm de ``asterion.domain.tdo_hub``; o marcador de referência da Fonte
nunca aparece para o jogador.
"""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.tdo_explore import ExploreResult
from asterion.bot.asset_catalog import location_key
from asterion.bot.creation_ui import Screen
from asterion.domain.tdo_hub import (
    CAMARA_LABEL,
    HUNT_LABELS,
    REFUGE_LABEL,
    TEXTO_CAMARA_DESCOBERTA,
    camara_entry_text,
)

CAMARA_ICON = "🕯"
BACK_TO_REFUGE = "Voltar ao Refúgio"
BACK_TO_REFUGE_CALLBACK = "road:route:refuge"

TEXT_NOTHING_TO_EXPLORE = "Não há mais o que explorar por aqui."
TEXT_WAIT = "Aguarde um instante."
TEXT_EXPLORE_FOR_PLACE = "Explore para encontrar este lugar."

_ICONS = {
    "Estrada das Cinzas": "🔥",
    "Charneca da Fuligem": "🌑",
    "Bosque Calcinado": "🌲",
    "Ruínas do Vigia": "🪨",
    CAMARA_LABEL: CAMARA_ICON,
}
_ROUTE_KEYS = {
    "Estrada das Cinzas": "road",
    "Charneca da Fuligem": "charneca",
    "Bosque Calcinado": "bosque",
    "Ruínas do Vigia": "ruinas",
    CAMARA_LABEL: "camara",
}


def hub_route_key(label: str) -> str | None:
    return _ROUTE_KEYS.get(label)


def hub_icon(label: str) -> str:
    return _ICONS.get(label, "📍")


def back_to_refuge_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=BACK_TO_REFUGE, callback_data=BACK_TO_REFUGE_CALLBACK)]


def refuge_hub_rows(
    route_destinations: tuple[str, ...], *, explore_remaining: int | None
) -> tuple[list[str], list[list[InlineKeyboardButton]]]:
    """Linhas de texto e botões do hub na tela do Refúgio (66.1 item 2)."""
    lines: list[str] = []
    rows: list[list[InlineKeyboardButton]] = []
    if explore_remaining == 0:
        lines.append(f"🧭 Explorar · {TEXT_NOTHING_TO_EXPLORE}")
    else:
        lines.append("🧭 Explorar · Revela um Local")
        rows.append([InlineKeyboardButton(text="Explorar", callback_data="tdo:explore")])
    if any(label in HUNT_LABELS for label in route_destinations):
        rows.append([InlineKeyboardButton(text="Caçar", callback_data="tdo:hunt")])
    rows.append([InlineKeyboardButton(text="Masmorra (Covil)", callback_data="dungeon:known")])
    rows.append([InlineKeyboardButton(text="Personagem", callback_data="character:root")])
    if route_destinations:
        lines.extend(["", "📍 Locais descobertos"])
    for label in route_destinations:
        key = hub_route_key(label)
        if key is None:
            continue
        lines.append(f"{hub_icon(label)} {escape(label)}")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{hub_icon(label)} {label}", callback_data=f"road:route:{key}"
                )
            ]
        )
    return lines, rows


def render_camara(p6_completed: bool) -> Screen:
    """Entrada na Câmara do Poente (66.3): texto pré ou pós P6 de quem vê."""
    text = f"{CAMARA_ICON} {CAMARA_LABEL}\n\n{camara_entry_text(p6_completed)}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[back_to_refuge_row()])
    return Screen(text, location_key(CAMARA_LABEL), keyboard)


def render_hunt_choice(route_destinations: tuple[str, ...]) -> Screen:
    """Caçar no Refúgio: só Locais descobertos com Caçada (66.1 item 2)."""
    choices = [label for label in route_destinations if label in HUNT_LABELS]
    lines = ["🦌 Caçar", "", "Escolha onde caçar."]
    rows: list[list[InlineKeyboardButton]] = []
    for label in choices:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{hub_icon(label)} {label}",
                    callback_data=f"road:route:{hub_route_key(label)}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=f"← {REFUGE_LABEL}", callback_data="world:local")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return Screen("\n".join(lines), location_key(REFUGE_LABEL), keyboard)


def render_explore_result(result: ExploreResult) -> Screen:
    """Resultado de Explorar (66.2): Local revelado, XP e aparece no Refúgio; sem Vigor."""
    back_button = InlineKeyboardButton(text=f"← {REFUGE_LABEL}", callback_data="world:local")
    back = InlineKeyboardMarkup(inline_keyboard=[[back_button]])
    if result.status == "discovered":
        label = result.label or ""
        lines = ["🧭 Explorar", "", f"{hub_icon(label)} {escape(label)}"]
        if label == CAMARA_LABEL:
            lines.extend(["", TEXTO_CAMARA_DESCOBERTA])
        lines.extend(["", f"✨ XP de descoberta · {result.xp}"])
        lines.append(f"{escape(label)} agora aparece no Refúgio.")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Explorar", callback_data="tdo:explore")],
                [InlineKeyboardButton(text=f"← {REFUGE_LABEL}", callback_data="world:local")],
            ]
        )
        return Screen("\n".join(lines), location_key(REFUGE_LABEL), keyboard)
    text = {
        "unavailable": TEXT_NOTHING_TO_EXPLORE,
        "cooldown": TEXT_WAIT,
        "busy": TEXT_WAIT,
        "not_in_refuge": "Explorar só está disponível no Refúgio do Ocaso.",
        "foreground": "Termine o que está fazendo antes de explorar.",
    }.get(result.status, TEXT_WAIT)
    return Screen(f"🧭 Explorar\n\n{text}", location_key(REFUGE_LABEL), back)
