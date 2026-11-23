from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.contracts import is_enabled as contracts_enabled
from asterion.application.legacy import LegacyView
from asterion.application.world import WorldView
from asterion.bot.creation_ui import Screen
from asterion.bot.flavor_ui import with_flavor
from asterion.bot.tdo_hub_ui import refuge_global_rows, refuge_hub_rows
from asterion.domain.paths import PATH_DEFINITIONS

LORE = (
    "Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, "
    "brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos "
    "mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo "
    "não conseguiu esquecer."
)


def bar(current, maximum, fill: str) -> str:
    segments = 9
    n = min(segments, max(0, int(current * segments / maximum))) if maximum else 0
    if current > 0 and maximum:
        n = max(1, n)
    return fill * n + "⬜" * (segments - n)


def number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


CLASS_LABELS = {
    "sentinela": "Sentinela",
    "errante": "Errante",
    "vigia": "Vigia",
    "tecelao": "Tecelão",
    "oraculo": "Oráculo",
    "luminar": "Luminar",
}
PATH_LABELS = {path_id: definition.name for path_id, definition in PATH_DEFINITIONS.items()}
LEGACY_LABELS = {
    0: "Legado",
    1: "Legado I",
    2: "Legado II",
    3: "Legado III",
    4: "Legado IV",
    5: "Legado V",
}


def render_campaign(
    location: str | None = None, principal_quest_title: str | None = None
) -> Screen:
    location_icon = {
        "Estrada das Cinzas": "🔥",
        "Refúgio do Ocaso": "🏚️",
        "Charneca da Fuligem": "🌑",
        "Bosque Calcinado": "🌲",
        "Ruínas do Vigia": "🪨",
    }.get(location, "📍")
    current = (
        f"📍 Local Atual\n{location_icon} {escape(location)}\nTerras do Ocaso\n\n"
        if location
        else ""
    )
    principal_quest = (
        f"📜 Missão Principal\n{escape(principal_quest_title)} · Em Andamento\n\n"
        if principal_quest_title
        else ""
    )
    text = (
        "📖 Campanha\n\n"
        f"{current}"
        f"{principal_quest}"
        "Siga a história: veja o Local Atual, abra o Mapa ou as Missões."
    )
    keyboard = [
        [
            InlineKeyboardButton(text="Local Atual", callback_data="world:local"),
            InlineKeyboardButton(text="Mapa", callback_data="world:map"),
        ],
        [InlineKeyboardButton(text="Missões", callback_data="world:missions")],
        [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
    ]
    if contracts_enabled():
        keyboard.insert(
            -1, [InlineKeyboardButton(text="Quadro de Contratos", callback_data="ctr:root")]
        )
    return Screen(text, "adventure", InlineKeyboardMarkup(inline_keyboard=keyboard))


def render_adventure() -> Screen:
    """Aventura hub: activities played with or against other players."""
    text = (
        "⚔️ Aventura\n\n"
        "Masmorras, Eventos e confrontos contra outros jogadores. "
        "Para a história e o mapa, use a Campanha."
    )
    keyboard = [
        [
            InlineKeyboardButton(text="Masmorras", callback_data="dungeon:known"),
            InlineKeyboardButton(text="Eventos", callback_data="wev:hub"),
        ],
        [InlineKeyboardButton(text="PvP", callback_data="pvp:hub")],
        [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
    ]
    return Screen(text, "adventure", InlineKeyboardMarkup(inline_keyboard=keyboard))


RACE_LABEL = {
    "remanescente": "Remanescente", "velado": "Velado", "cinereo": "Cinéreo",
    "hemario": "Hemário", "alvorano": "Alvorano",
}
CLASS_LABEL = {
    "sentinela": "Sentinela", "errante": "Errante", "vigia": "Vigia",
    "tecelao": "Tecelão", "oraculo": "Oráculo", "luminar": "Luminar",
}


def render_world(view: WorldView) -> Screen:
    if view.kind == "brazier":
        from asterion.bot.prologue_ui import render_brazier

        return render_brazier(view.name, view.max_hp)
    class_label = CLASS_LABELS.get(view.character_class, view.character_class)
    path_label = PATH_LABELS.get(view.selected_path or "", "Caminho")
    legacy_label = LEGACY_LABELS.get(view.legacy_level, "Legado")
    title_label = view.selected_title or "Título"
    identity = (
        f"👤 {escape(view.name)} · {class_label} · {path_label}\n"
        f"🏛️ Nv. {view.level} · {legacy_label}\n"
        f"🔰 {title_label}"
    )
    stats = "\n".join(
        (
            f"❤️ HP · {view.hp} / {view.max_hp}\n{bar(view.hp, view.max_hp, '🟥')}",
            f"⚡ Vigor · {view.vigor} / {view.max_vigor}\n"
            f"{bar(view.vigor, view.max_vigor, '🟨')}",
            f"✨ XP · {number(view.xp)} / {number(view.xp_required)}\n"
            f"{bar(view.xp, view.xp_required, '🟦')}",
        )
    )
    text = "\n\n".join(
        (
            "🌘 Refúgio do Ocaso",
            identity,
            stats,
            "━━━━━━━━━━━━━━━━━━",
        )
    )
    action_labels = [
        ("🧭 Desbravar", "road:explore:start"),
        ("🗡️ Caçada", "road:hunt"),
        ("🗝️ Masmorra", "dungeon:known"),
        ("🗺️ Mapa", "world:map"),
        ("📜 Missões", "world:missions"),
        ("👤 Personagem", "character:root"),
        ("🏰 Guilda", "guild:root"),
        ("🏟️ Arena", "pvp:hub"),
        ("🏪 Mercado", "mkt:root"),
        ("🤝 Vínculos", "links:root"),
        ("🏆 Classificação", "pvp:rank"),
        ("📖 Códice", "knowledge:codex"),
        ("📅 Calendário", "calendar:root"),
        ("🎁 Benefícios", "bn:root"),
        ("🌐 Comunidade", "community:open"),
        ("⚙️ Configurações", "settings:root"),
    ]
    rows = [[InlineKeyboardButton(text="🎁 Resgatar Recompensa Diária", callback_data="bn:gift")]]
    rows.extend(
        [InlineKeyboardButton(text=a, callback_data=b) for a, b in action_labels[i : i + 2]]
        for i in range(0, len(action_labels), 2)
    )
    return Screen(text, "menu", InlineKeyboardMarkup(inline_keyboard=rows))


def render_refuge_dashboard(
    view: WorldView,
    *,
    route_destinations: tuple[str, ...],
    explore_remaining: int | None,
    can_hunt: bool,
    known_dungeons: bool,
) -> Screen:
    """The Terras do Ocaso main screen: character HUD plus Refúgio actions."""
    dashboard = render_world(view)
    hub_lines, hub_rows = refuge_hub_rows(
        route_destinations,
        explore_remaining=explore_remaining,
        can_hunt=can_hunt,
        known_dungeons=known_dungeons,
    )
    rows = list(hub_rows)
    if "Refúgio do Ocaso" in route_destinations or view.location == "Refúgio do Ocaso":
        rows.extend(
            [
                [InlineKeyboardButton(text="Alda Veyr", callback_data="p2:alda")],
                [InlineKeyboardButton(text="Oren Cal", callback_data="world:oren")],
                [InlineKeyboardButton(text="Treinador de Armas", callback_data="wpt:root")],
            ]
        )
    rows.extend(refuge_global_rows())
    text = dashboard.text
    if hub_lines:
        text = f"{text}\n\n" + "\n".join(hub_lines)
    return Screen(text, "refuge", InlineKeyboardMarkup(inline_keyboard=rows))


def render_legacy(
    view: LegacyView,
    *,
    confirmation_key: str | None = None,
    succeeded: bool = False,
) -> Screen:
    ranks = {
        0: "Sem Legado",
        1: "Legado I",
        2: "Legado II",
        3: "Legado III",
        4: "Legado IV",
        5: "Legado V",
    }
    next_rank = ranks.get(view.legacy_level + 1, "")
    cost_text = (
        "gratuito"
        if view.ascension_cost == 0
        else f"{view.ascension_cost:,} Coroas".replace(",", ".")
    )
    reasons = {
        "level_required": "Alcance o Nv.60.",
        "crowns_required": f"Reúna {cost_text} para este Legado.",
        "safe_location_required": "Descanse num Braseiro permanente.",
        "activity_locked": "Encerre atividades e vínculos incompatíveis antes de ascender.",
        "legacy_max_reached": "Você já alcançou o Legado V, o máximo.",
    }
    text = (
        "🔱 Legado\n\n"
        f"{ranks.get(view.legacy_level, 'Legado desconhecido')} · Nv. {view.level}\n"
        f"Multiplicador de XP elegível: ×{view.xp_factor}\n"
    )
    if succeeded:
        text += (
            "\nAscensão concluída. Sua campanha e conquistas permanecem; sua progressão foi "
            "reiniciada no Nv.1. Equipamentos incompatíveis continuam no Inventário.\n"
            "Uma nova vaga de Marca de Legado foi liberada."
        )
    elif confirmation_key is not None:
        text += (
            f"\nConfirme a Ascensão para {next_rank} ({cost_text}). O personagem voltará ao "
            "Nv.1 e perderá qualquer XP restante no Nv.60. A campanha e os itens serão "
            "preservados; itens incompatíveis serão desequipados. Esta ação não pode ser "
            "desfeita."
        )
    elif view.can_ascend:
        text += (
            f"\nVocê atende aos requisitos para {next_rank} ({cost_text}) em um local seguro."
        )
    else:
        text += f"\nPara {next_rank or 'a próxima Ascensão'}:"
        text += "\n" + "\n".join(
            f"• {reasons.get(reason.value, 'Requisito ainda não atendido.')}"
            for reason in view.reasons
        )

    if confirmation_key is not None:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Confirmar Ascensão",
                        callback_data=f"legacy:confirm:{confirmation_key}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Cancelar", callback_data=f"legacy:cancel:{confirmation_key}"
                    )
                ],
                [InlineKeyboardButton(text="← Personagem", callback_data="character:root")],
            ]
        )
    else:
        rows = []
        if view.can_ascend:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Preparar Ascensão",
                        callback_data=f"legacy:prepare:{view.configuration_version}",
                    )
                ]
            )
        rows.append(
            [InlineKeyboardButton(text="🎗️ Marcas de Legado", callback_data="lmk:root")]
        )
        rows.append(
            [InlineKeyboardButton(text="← Personagem", callback_data="character:root")]
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return with_flavor(Screen(text, "menu", keyboard), "legado")
