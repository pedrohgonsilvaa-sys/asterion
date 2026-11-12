from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.legacy import LegacyView
from asterion.application.world import WorldView
from asterion.bot.creation_ui import Screen

LORE = (
    "Sob céus cobertos de fuligem, as estradas de Asterion seguem marcadas por ruínas, "
    "brasas antigas e promessas que nunca repousam por completo. Mesmo nos caminhos "
    "mais silenciosos, cada passo ainda parece ecoar a memória de algo que o mundo "
    "não conseguiu esquecer."
)


def bar(current, maximum, fill: str) -> str:
    n = min(10, max(0, int(current * 10 / maximum))) if maximum else 0
    return fill * n + "⬜" * (10 - n)


def number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def render_adventure(
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
        "🗺️ Aventura\n\n"
        f"{current}"
        f"{principal_quest}"
        "Escolha uma atividade ou abra o Mapa."
    )
    keyboard = [
        [
            InlineKeyboardButton(text="Local Atual", callback_data="world:local"),
            InlineKeyboardButton(text="Mapa", callback_data="world:map"),
        ],
        [
            InlineKeyboardButton(text="Missões", callback_data="world:missions"),
            InlineKeyboardButton(text="Masmorras", callback_data="dungeon:known"),
        ],
        [
            InlineKeyboardButton(text="Eventos", callback_data="wev:hub"),
            InlineKeyboardButton(text="PvP", callback_data="pvp:hub"),
        ],
        [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
    ]
    return Screen(text, "adventure", InlineKeyboardMarkup(inline_keyboard=keyboard))


def render_world(view: WorldView) -> Screen:
    if view.kind == "brazier":
        text = (
            "🔥 Braseiro\nEstrada das Cinzas · Terras do Ocaso\n\n"
            "Entre pedras escurecidas pela fuligem, uma chama permanece acesa onde tudo ao redor "
            "parece ter sido abandonado. Seu calor atravessa o silêncio da estrada e oferece, "
            "pela primeira vez, um lugar seguro para recuperar as forças.\n\n"
            "🔥 Braseiro · Descoberto\n❤️ Descansar · Restaura HP\n\n"
            "ℹ️ Braseiros permanentes podem servir para descanso e, quando outros forem "
            "descobertos, "
            "conectar diferentes pontos de Asterion através da Travessia dos Braseiros."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Descansar", callback_data="world:rest")]]
        )
        return Screen(text, "brazier_estrada", kb)
    emoji = {
        "sentinela": "🛡️",
        "errante": "🗡️",
        "vigia": "🏹",
        "tecelao": "🪄",
        "oraculo": "🔮",
        "luminar": "☀️",
    }[view.character_class]
    title = {
        "sentinela": "Sentinela",
        "errante": "Errante",
        "vigia": "Vigia",
        "tecelao": "Tecelão",
        "oraculo": "Oráculo",
        "luminar": "Luminar",
    }[view.character_class]
    quest_lines = []
    if view.quest_title:
        quest_lines.append(f"📜 Missão Principal · {escape(view.quest_title)}")
    if view.tracked_secondary_quest_title:
        quest_lines.append(
            f"📖 Missão Secundária · {escape(view.tracked_secondary_quest_title)}"
        )
    quest_line = "\n".join(quest_lines)
    text = (
        f"🌑 Asterion\n{view.region} · {view.location}\n\n{LORE}\n\n"
        f"{emoji} {escape(view.name)} · Nv. {view.level}\n{title}\n\n"
        f"❤️ HP · {view.hp} / {view.max_hp}\n{bar(view.hp, view.max_hp, '🟩')}\n\n"
        f"⚡ Vigor · {view.vigor} / {view.max_vigor}\n{bar(view.vigor, view.max_vigor, '🟨')}\n\n"
        f"✨ XP · {number(view.xp)} / {number(view.xp_required)}\n"
        f"{bar(view.xp, view.xp_required, '🟦')}\n\n"
        f"{quest_line}"
    )
    labels = [
        ("Aventura", "world:adventure"),
        ("Personagem", "character:root"),
        ("Códice", "knowledge:codex"),
        ("Calendário", "calendar:root"),
        ("Vínculos", "links:root"),
        ("Mercado", "mkt:root"),
        ("Classificação da Vigília", "pvp:rank"),
        ("Benefícios", "bn:root"),
        ("Comunidade", "community:open"),
        ("Configurações", "settings:root"),
    ]
    rows = [
        [InlineKeyboardButton(text=a, callback_data=b) for a, b in labels[i : i + 2]]
        for i in range(0, len(labels), 2)
    ]
    return Screen(text, "menu", InlineKeyboardMarkup(inline_keyboard=rows))


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
    reasons = {
        "level_required": "Alcance o Nv.60.",
        "campaign_required": "Conclua a campanha principal.",
        "safe_location_required": "Venha ao Refúgio do Ocaso.",
        "activity_locked": "Encerre atividades e vínculos incompatíveis antes de ascender.",
        "legacy_transition_undefined": "A próxima transição ainda não está disponível.",
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
            "\nConfirme a Ascensão para Legado I. O personagem voltará ao Nv.1 e perderá "
            "qualquer XP restante no Nv.60. A campanha e os itens serão preservados; itens "
            "incompatíveis serão desequipados. Esta ação não pode ser desfeita."
        )
    elif view.can_ascend:
        text += "\nVocê atende aos requisitos da primeira Ascensão em um local seguro."
    else:
        text += "\nPara a primeira Ascensão:"
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
    return Screen(text, "menu", keyboard)
