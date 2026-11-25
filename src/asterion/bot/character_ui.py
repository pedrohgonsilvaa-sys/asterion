"""Menu de Personagem (Contrato Mestre de Telas UI v1.0.0 §6).

Personagem é só menu: identidade padrão e as entradas do personagem. Ofícios e
Caminho ficam no Refúgio do Ocaso; Legado só aparece quando aplicável.
"""

from __future__ import annotations

from asterion.application.character_surfaces import IdentityView
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import back, blocks, button, identity, keyboard, pairs
from asterion.bot.world_ui import CLASS_EMOJI

# Legado I exige somente Nv.60 (SOURCE_AUTHORITY, override de 2026-11-20).
LEGACY_LEVEL = 60
CHARACTER_BUTTONS = (
    ("⚔️ Equipamentos", "eq:r"),
    ("🎒 Inventário", "inventory:root"),
    ("📊 Atributos", "character:attributes"),
    ("✨ Artes", "character:arts"),
    ("🌿 Talentos", "character:talents"),
    ("🪪 Perfil", "character:profile"),
    ("🧩 Doutrinas", "character:doctrines"),
    ("🎨 Cosméticos", "character:cosmetics"),
    ("🏆 Feitos", "kb:a"),
)
LEGACY_BUTTON = ("🏛️ Legado", "legacy:root")


def legacy_applies(view: IdentityView | None) -> bool:
    return view is not None and (view.legacy_level > 0 or view.level >= LEGACY_LEVEL)


def render_character(view: IdentityView | None = None) -> Screen:
    header = "👤 <b>Personagem</b>"
    text = (
        blocks(
            header,
            identity(
                emoji=CLASS_EMOJI.get(view.character_class, "👤"),
                name=view.name,
                level=view.level,
                legacy_level=view.legacy_level,
                guild_tag=view.guild_tag,
                title=view.selected_title,
            ),
        )
        if view is not None
        else header
    )
    rows = pairs([button(label, callback) for label, callback in CHARACTER_BUTTONS])
    legacy = [button(*LEGACY_BUTTON)] if legacy_applies(view) else []
    return Screen(text, "character", keyboard(*rows, legacy, back("menu:back")), "HTML")
