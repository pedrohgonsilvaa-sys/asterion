from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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


def render_adventure(location: str | None = None) -> Screen:
    current = f"📍 Local Atual · {escape(location)}\n\n" if location else ""
    text = (
        "🗺️ Aventura\n\n"
        f"{current}"
        "Escolha para onde deseja seguir."
    )
    keyboard = [
        [InlineKeyboardButton(text="Local Atual", callback_data="world:local")],
        [
            InlineKeyboardButton(text="Mapa", callback_data="world:map"),
            InlineKeyboardButton(text="Missões", callback_data="world:missions"),
        ],
        [InlineKeyboardButton(text="Masmorras", callback_data="dungeon:known")],
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
        ("Configurações", "settings:root"),
    ]
    rows = [
        [InlineKeyboardButton(text=a, callback_data=b) for a, b in labels[i : i + 2]]
        for i in range(0, len(labels), 2)
    ]
    return Screen(text, "menu", InlineKeyboardMarkup(inline_keyboard=rows))
