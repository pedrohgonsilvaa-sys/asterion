"""Player-facing Character hub."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.bot.creation_ui import Screen

CHARACTER_COPY = (
    "🪪 Personagem\n\n"
    "Cada batalha, escolha e descoberta deixa marcas em quem você se torna. "
    "Aqui estão os caminhos, conquistas e escolhas que dão forma à sua jornada por Asterion.\n\n"
    "🎒 Inventário · Itens\n"
    "🛡️ Equipamentos · Arsenal\n"
    "🎴 Artes · Combate\n"
    "🧩 Doutrinas · Configuração\n"
    "🌿 Talentos · Evolução\n"
    "📈 Atributos · Status\n"
    "⚒️ Ofícios · Criação\n"
    "🎨 Cosméticos · Aparência\n"
    "📇 Perfil · Identidade\n"
    "🎭 Caminho · Especialização\n"
    "🏛️ Legado · Ascensão"
)


def render_character() -> Screen:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Inventário", callback_data="inventory:root"),
                InlineKeyboardButton(text="Equipamentos", callback_data="eq:r"),
            ],
            [InlineKeyboardButton(text="← Menu", callback_data="menu:back")],
        ]
    )
    return Screen(CHARACTER_COPY, "character", keyboard)
