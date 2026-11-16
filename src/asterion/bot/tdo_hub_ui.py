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
    is_hub_location,
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


_MISSION_TARGET_LABELS = {
    "Charneca da Fuligem": "Seguir para a Charneca",
    "Bosque Calcinado": "Seguir para o Bosque",
    "Ruínas do Vigia": "Seguir para as Ruínas",
    CAMARA_LABEL: "Seguir para a Câmara do Poente",
}


def mission_hub_button(location: str, target: str) -> InlineKeyboardButton | None:
    """Passo de Missão no hub (33.1): do Refúgio ao Local alvo, de outro Local só a volta.

    Nunca há botão Local-Local. No Local alvo não há botão de viagem.
    """
    if location == target:
        return None
    if location == REFUGE_LABEL:
        key = hub_route_key(target)
        if key is None:
            return None
        return InlineKeyboardButton(
            text=_MISSION_TARGET_LABELS.get(target, f"Seguir para {target}"),
            callback_data=f"road:route:{key}",
        )
    if is_hub_location(location):
        return InlineKeyboardButton(text=BACK_TO_REFUGE, callback_data=BACK_TO_REFUGE_CALLBACK)
    return None


def back_to_refuge_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=BACK_TO_REFUGE, callback_data=BACK_TO_REFUGE_CALLBACK)]


def refuge_hub_rows(
    route_destinations: tuple[str, ...],
    *,
    explore_remaining: int | None,
    can_hunt: bool = True,
    known_dungeons: bool = True,
) -> tuple[list[str], list[list[InlineKeyboardButton]]]:
    """Linhas de texto e botões do hub na tela do Refúgio (66.1 item 2)."""
    lines: list[str] = []
    rows: list[list[InlineKeyboardButton]] = []
    first_row: list[InlineKeyboardButton] = []
    if explore_remaining == 0:
        lines.append(f"🧭 Explorar · {TEXT_NOTHING_TO_EXPLORE}")
    else:
        lines.append("🧭 Explorar · Revela um Local")
        first_row.append(InlineKeyboardButton(text="Explorar", callback_data="tdo:explore"))
    first_row.append(InlineKeyboardButton(text="Mapa", callback_data="world:map"))
    rows.append(first_row)
    activities_row: list[InlineKeyboardButton] = []
    if can_hunt and any(label in HUNT_LABELS for label in route_destinations):
        activities_row.append(InlineKeyboardButton(text="Caçar", callback_data="tdo:hunt"))
    if known_dungeons:
        activities_row.append(InlineKeyboardButton(text="Masmorra", callback_data="dungeon:known"))
    if activities_row:
        rows.append(activities_row)
    rows.append([InlineKeyboardButton(text="Missões", callback_data="world:missions")])
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


def refuge_global_rows() -> list[list[InlineKeyboardButton]]:
    """Entradas do Menu Principal mantidas como atalhos no Refúgio."""
    pairs = (
        (("Personagem", "character:root"), ("Guilda", "guild:root")),
        (("Mercado", "mkt:root"), ("Arena", "pvp:hub")),
        (("Códice", "knowledge:codex"), ("Calendário", "calendar:root")),
        (("Vínculos", "links:root"), ("Classificação", "pvp:rank")),
        (("Benefícios", "bn:root"), ("Comunidade", "community:open")),
        (("Configurações", "settings:root"),),
    )
    return [
        [InlineKeyboardButton(text=label, callback_data=callback) for label, callback in pair]
        for pair in pairs
    ]


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
    rows.append([InlineKeyboardButton(text=BACK_TO_REFUGE, callback_data="world:local")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return Screen("\n".join(lines), location_key(REFUGE_LABEL), keyboard)


def render_explore_result(result: ExploreResult) -> Screen:
    """Resultado de Explorar (66.2): Local revelado, XP e aparece no Refúgio; sem Vigor."""
    back_button = InlineKeyboardButton(text=BACK_TO_REFUGE, callback_data="world:local")
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
                [InlineKeyboardButton(text=BACK_TO_REFUGE, callback_data="world:local")],
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
