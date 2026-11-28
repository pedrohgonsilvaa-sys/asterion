"""Forja de Equipamento (Mercado): Runas, Encantamento, Aprimoramento e Desmontagem.

Só apresentação. As operações são as de ``equipment_modification_handlers`` (``em:*``).
"""

from html import escape
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.equipment_view import EquipmentDetailView
from asterion.application.inventory import InventoryEntry
from asterion.bot.creation_ui import Screen
from asterion.bot.equipment_ui import _item_name
from asterion.bot.inventory_ui import PAGE_SIZE, numbered_buttons, page_line, page_slice
from asterion.bot.item_lines import list_item, rarity_emoji, stat_line
from asterion.bot.ui_format import numeric_rows, page_nav

FORGE_TITLE = "🔨 Forja"
FORGE_TEXT = (
    "Escolha um equipamento para instalar Runas, aplicar Encantamento, aprimorar ou desmontar."
)
EMPTY_TEXT = "Nenhum equipamento disponível para a Forja."
BACK_TO_MARKET = "mkt:root"


def render_forge_list(entries: tuple[InventoryEntry, ...], page: int = 0) -> Screen:
    equipment = tuple(entry for entry in entries if entry.kind == "equipment")
    page, pages, _, shown = page_slice(equipment, page)
    listing = (
        "\n\n".join(
            list_item(position, entry, entry.key) for position, entry in enumerate(shown, start=1)
        )
        if shown
        else EMPTY_TEXT
    )
    callbacks = []
    for entry in shown:
        try:
            callbacks.append(f"forge:i:{UUID(entry.key).hex}")
        except (ValueError, TypeError):
            callbacks.append("forge:root")
    rows = numeric_rows(numbered_buttons(callbacks))
    rows.append(page_nav(page, pages, lambda target: f"forge:root:{target}"))
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data=BACK_TO_MARKET)])
    parts = [f"<b>{FORGE_TITLE}</b>", f"<i>{escape(FORGE_TEXT)}</i>"]
    if shown:
        parts.append("\n".join(page_line(page, pages)))
    parts.append(listing)
    return Screen(
        "\n\n".join(parts),
        "market",
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def render_forge_item(view: EquipmentDetailView) -> Screen:
    item = view.item
    token = item.item_instance_id.hex
    head = f"{rarity_emoji(item.rarity)} <b>{escape(_item_name(item))}</b>"
    if attributes := stat_line(item.contribution, attack_icon="🗡️"):
        head += f"\n{attributes}"
    rows = [
        [
            InlineKeyboardButton(text="🔮 Runas", callback_data=f"em:r:{token}"),
            InlineKeyboardButton(text="✨ Encantamento", callback_data=f"em:e:{token}"),
        ]
    ]
    upkeep = []
    if item.enhancement < 10:
        upkeep.append(InlineKeyboardButton(text="🔨 Aprimorar", callback_data=f"em:h:{token}"))
    if not item.favorite and not item.locked and not item.runes:
        upkeep.append(InlineKeyboardButton(text="🔧 Desmontar", callback_data=f"em:d:{token}"))
    if upkeep:
        rows.append(upkeep)
    if item.reroll_available:
        rows.append([InlineKeyboardButton(text="🎲 Reroll", callback_data=f"em:l:{token}")])
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="forge:root")])
    return Screen(
        f"<b>{FORGE_TITLE}</b>\n\n{head}",
        "market",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


__all__ = ["PAGE_SIZE", "render_forge_item", "render_forge_list"]
