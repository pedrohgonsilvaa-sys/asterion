"""Player-facing Character hub."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.bot.creation_ui import Screen

CHARACTER_COPY = (
    "🪪 Personagem\n\n"
    "Consulte os atributos, escolhas e recursos que já fazem parte da "
    "jornada do seu personagem.\n\n"
    "🎒 Inventário · Itens\n"
    "🛡️ Equipamentos · Arsenal\n"
    "🎴 Artes · Combate\n"
    "🌿 Talentos · Evolução\n"
    "📈 Atributos · Status\n"
    "⚒️ Ofícios · Criação\n"
    "📇 Perfil · Identidade\n"
    "🎭 Caminho · Especialização\n"
    "🧩 Doutrinas · Configurações salvas\n"
    "🎨 Cosméticos · Apresentação\n"
    "🔱 Legado · Ascensão"
)


def render_character() -> Screen:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Inventário", callback_data="inventory:root"),
                InlineKeyboardButton(text="Equipamentos", callback_data="eq:r"),
            ],
            [
                InlineKeyboardButton(text="Artes", callback_data="character:arts"),
                InlineKeyboardButton(text="Talentos", callback_data="character:talents"),
            ],
            [
                InlineKeyboardButton(text="Atributos", callback_data="character:attributes"),
                InlineKeyboardButton(text="Ofícios", callback_data="character:professions"),
            ],
            [
                InlineKeyboardButton(text="Perfil", callback_data="character:profile"),
                InlineKeyboardButton(text="Caminho", callback_data="character:path"),
            ],
            [
                InlineKeyboardButton(text="Doutrinas", callback_data="character:doctrines"),
                InlineKeyboardButton(text="Cosméticos", callback_data="character:cosmetics"),
            ],
            [InlineKeyboardButton(text="Legado", callback_data="legacy:root")],
            [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
        ]
    )
    return Screen(CHARACTER_COPY, "character", keyboard)
