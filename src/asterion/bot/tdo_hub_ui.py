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


EXPLORE_TEXT = (
    "Além das cinzas do Refúgio, caminhos pouco conhecidos se espalham pela região. A "
    "cada avanço, novos lugares, acontecimentos e oportunidades podem surgir."
)
# Bloco UI 1 §3: três caminhos. Todos acionam o mesmo Explorar canônico (TDO v1.0.18
# §33.2): nenhuma fonte define resultados diferentes por caminho.
EXPLORE_PATHS = (
    "👣 Seguir pela estrada",
    "🌲 Seguir pela trilha",
    "🪨 Explorar os arredores",
)
EXPLORE_GO = "tdo:explore:go"
EXPLORE_ENTRY = "tdo:explore"
# Primeiro parágrafo da descoberta. Charneca: Bloco UI 1; Câmara: Fonte Regional §3.6.
_DISCOVERY_TEXT = {
    "Charneca da Fuligem": (
        "Depois de atravessar a trilha, uma extensa região coberta por cinzas surge além "
        "das árvores. O terreno é silencioso, mas há sinais de que outros caminhos ainda "
        "podem ser encontrados por ali."
    ),
    CAMARA_LABEL: TEXTO_CAMARA_DESCOBERTA,
}
_OF = {
    "Charneca da Fuligem": "da",
    "Bosque Calcinado": "do",
    "Ruínas do Vigia": "das",
    CAMARA_LABEL: "da",
    "Estrada das Cinzas": "da",
}


def _explore_status(view) -> str:
    """Status de Explorar: sem nome nem Classe (Bloco UI 1 §3)."""
    from asterion.bot.ui_format import HP_FILL, VIGOR_FILL, XP_FILL, bar, mono, number

    return "\n".join(
        (
            f"❤️ {mono(f'{number(int(view.hp))} / {number(int(view.max_hp))}')}",
            bar(view.hp, view.max_hp, HP_FILL),
            f"⚡ {mono(f'{view.vigor} / {view.max_vigor}')}",
            bar(view.vigor, view.max_vigor, VIGOR_FILL),
            f"✨ {mono(f'{number(view.xp)} / {number(view.xp_required)}')}",
            bar(view.xp, view.xp_required, XP_FILL),
        )
    )


def render_explore_entry(view, *, remaining: int | None) -> Screen:
    """Entrada de Explorar. Explorar custa 0 Vigor (TDO v1.0.18 §33.2): sem custo exibido."""
    from asterion.bot.ui_format import back, blocks, button, column, keyboard, narrative

    parts = ["🧭 <b>Explorar</b>", narrative(EXPLORE_TEXT), _explore_status(view)]
    rows: list[list[InlineKeyboardButton]] = []
    if remaining == 0:
        parts.append(TEXT_NOTHING_TO_EXPLORE)
    else:
        rows = column(*(button(label, EXPLORE_GO) for label in EXPLORE_PATHS))
    return Screen(
        blocks(*parts), location_key(REFUGE_LABEL), keyboard(*rows, back("menu:back")), "HTML"
    )


def render_explore_result(result: ExploreResult) -> Screen:
    """Descoberta de Local (Bloco UI 1 §3): acontecimento → narrativa → Recompensas."""
    from asterion.bot.ui_format import (
        back,
        blocks,
        button,
        keyboard,
        narrative,
        reward_line,
        rewards,
    )
    from asterion.bot.ui_format import number as fmt

    if result.status == "discovered":
        label = result.label or ""
        known = (
            f"A rota até {label} agora é conhecida, permitindo que o local seja acessado "
            "novamente a partir dos caminhos já explorados."
        )
        items = [f"🗺️ <b>Descoberta {_OF.get(label, 'de')} {escape(label)}</b>"]
        if result.camara_codex:
            items.append("📖 <b>Entrada do Códice</b>")
        if result.xp:
            items.append(reward_line("✨", f"{fmt(result.xp)} XP"))
        text = blocks(
            f"{hub_icon(label)} <b>{escape(label)}</b>",
            narrative(_DISCOVERY_TEXT[label]) if label in _DISCOVERY_TEXT else None,
            narrative(known),
            rewards(items),
        )
        rows = keyboard(
            [button("🧭 Continuar explorando", EXPLORE_ENTRY)],
            [button("↩️ Voltar ao Refúgio", "menu:back")],
        )
        return Screen(text, location_key(label), rows, "HTML")
    text = {
        "unavailable": TEXT_NOTHING_TO_EXPLORE,
        "cooldown": TEXT_WAIT,
        "busy": TEXT_WAIT,
        "not_in_refuge": "Explorar só está disponível no Refúgio do Ocaso.",
        "foreground": "Termine o que está fazendo antes de explorar.",
    }.get(result.status, TEXT_WAIT)
    return Screen(
        blocks("🧭 <b>Explorar</b>", escape(text)),
        location_key(REFUGE_LABEL),
        keyboard(back(EXPLORE_ENTRY if result.status != "unavailable" else "menu:back")),
        "HTML",
    )
