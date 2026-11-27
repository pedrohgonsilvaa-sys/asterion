"""Menu de Personagem (Contrato Mestre de Telas UI v1.0.0 §6).

Personagem é só menu: identidade padrão e as entradas do personagem. Ofícios e
Caminho ficam no Refúgio do Ocaso; Legado só aparece quando aplicável.
"""

from __future__ import annotations

from decimal import Decimal

from asterion.application.character_surfaces import AttributesView, IdentityView
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import (
    HP_FILL,
    VIGOR_FILL,
    XP_FILL,
    back,
    bar,
    blocks,
    button,
    identity,
    keyboard,
    mono,
    number,
    pairs,
)
from asterion.bot.world_ui import CLASS_EMOJI

# Legado I exige somente Nv.60 (SOURCE_AUTHORITY, override de 2026-11-20).
LEGACY_LEVEL = 60
# Decisão do autor 2026-11-26 §6: atributos aparecem na própria tela; os botões são
# Equipamentos/Inventário, Artes/Talentos, Doutrinas/Perfil e Cosméticos/Feitos.
# Especificação consolidada 2026-11-26, Parte IV §8: não existe mais tela Perfil;
# a entrada abre direto a História.
CHARACTER_BUTTONS = (
    ("⚔️ Equipamentos", "eq:r"),
    ("💼 Inventário", "inventory:root"),
    ("🧿 Artes", "character:arts"),
    ("🌳 Talentos", "character:talents"),
    ("🔱 Doutrinas", "character:doctrines"),
    ("📖 História", "character:profile"),
    ("🎨 Cosméticos", "character:cosmetics"),
    ("🏆 Feitos", "kb:a"),
)
# Espaço ideográfico: separa as duas colunas sem quebrar na largura do celular.
COLUMN_GAP = "\u3000"
LEGACY_BUTTON = ("🏛️ Legado", "legacy:root")


def legacy_applies(view: IdentityView | None) -> bool:
    return view is not None and (view.legacy_level > 0 or view.level >= LEGACY_LEVEL)


def _value(value) -> str:
    return number(int(value))


def _percent(value) -> str:
    text = f"{Decimal(value):f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text.replace('.', ',')}%"


def resource_bars(hp, max_hp, vigor, max_vigor, xp, xp_required, life_label="HP") -> str:
    """HP, Vigor e XP com barras de 10 segmentos (valores reais, sem espaços extras)."""
    return "\n".join(
        (
            f"❤️ <b>{life_label}</b> · {mono(f'{_value(hp)}/{_value(max_hp)}')}",
            bar(hp, max_hp, HP_FILL),
            f"⚡ <b>Vigor</b> · {mono(f'{vigor}/{max_vigor}')}",
            bar(vigor, max_vigor, VIGOR_FILL),
            f"✨ <b>XP</b> · {mono(f'{number(xp)}/{number(xp_required)}')}",
            bar(xp, xp_required, XP_FILL),
        )
    )


def render_character(
    view: IdentityView | None = None, stats: AttributesView | None = None
) -> Screen:
    header = "👤 <b>Personagem</b>"
    parts: list[str | None] = [header]
    if view is not None:
        parts.append(
            identity(
                emoji=CLASS_EMOJI.get(view.character_class, "👤"),
                name=view.name,
                level=view.level,
                legacy_level=view.legacy_level,
                guild_tag=view.guild_tag,
                title=view.selected_title,
            )
        )
    if stats is not None:
        # UI aprovada: Coroas junto da identidade; Vida na barra, HP nos atributos.
        if view is not None:
            parts[-1] += f"\n🪙 <b>Coroas</b> · {mono(number(stats.crowns))}"
        else:
            parts.append(f"🪙 <b>Coroas</b> · {mono(number(stats.crowns))}")
        parts.extend(
            (
                resource_bars(
                    stats.hp, stats.max_hp, stats.vigor, stats.max_vigor,
                    stats.xp, stats.xp_required, life_label="Vida",
                ),
                f"⚔️ <b>ATQ</b> · {mono(_value(stats.attack))}{COLUMN_GAP}"
                f"💨 <b>AGI</b> · {mono(_value(stats.agility))}\n"
                f"🛡️ <b>DEF</b> · {mono(_value(stats.defense))}{COLUMN_GAP}"
                f"❤️ <b>HP</b> · {mono(_value(stats.max_hp))}",
                f"💥 <b>Crítico</b> · {mono(_percent(stats.critical))}{COLUMN_GAP}"
                f"⚡️ <b>Esquiva</b> · {mono(_percent(stats.evasion))}\n"
                f"💢 <b>Bloqueio</b> · {mono(_percent(stats.block))}{COLUMN_GAP}"
                f"🎯 <b>Precisão</b> · {mono(_percent(stats.perception))}",
            )
        )  # fmt: skip
    rows = pairs([button(label, callback) for label, callback in CHARACTER_BUTTONS])
    legacy = [button(*LEGACY_BUTTON)] if legacy_applies(view) else []
    return Screen(blocks(*parts), "character", keyboard(*rows, legacy, back("menu:back")), "HTML")
