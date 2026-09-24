"""Telegram rendering for Inventory and Pending read models."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.inventory import InventoryEntry, InventoryView
from asterion.bot.creation_ui import Screen
from asterion.domain.consumables import grade_label

RARITY_ICON = {
    "Comum": "⚪",
    "Raro": "🔵",
    "Épico": "🟣",
    "Lendário": "🟠",
    "Mítico": "🔴",
    "common": "⚪",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠",
    "mythic": "🔴",
}

SLOT_ICON = {
    "main_hand": "🗡️",
    "off_hand": "⚔️",
    "head": "🪖",
    "torso": "🥋",
    "hands": "🧤",
    "feet": "🥾",
    "accessory": "💍",
    "artifact": "🧿",
    "Arma Principal": "🗡️",
    "Arma Secundária": "⚔️",
    "Cabeça": "🪖",
    "Torso": "🥋",
    "Mãos": "🧤",
    "Pés": "🥾",
    "Acessório": "💍",
    "Artefato": "🧿",
}

MATERIAL_META = {
    "material.tdo.ferro_de_fuligem": ("⛏️", "Metal · Grau I"),
    "material.tdo.couro_escoriado": ("🐾", "Couro · Grau I"),
    "material.tdo.erva_cinzenta": ("🌿", "Reagente · Grau I"),
    "material.tdo.residuo_ocaso": ("💧", "Essência · Grau I"),
    "material.tdo.catalisador_elite_i": ("⚗️", "Recurso Especial · Grau I"),
    "material.tdo.fragmento_aprimoramento_i": ("🪨", "Recurso Especial · Grau I"),
}


def _rarity(entry: InventoryEntry) -> str:
    if not entry.rarity:
        return ""
    return f"{RARITY_ICON.get(entry.rarity, '⚪')} {escape(entry.rarity)}"


def _entry_lines(index: int, entry: InventoryEntry) -> list[str]:
    if entry.kind == "equipment":
        enhancement = int((entry.payload or {}).get("enhancement", 0))
        icon = SLOT_ICON.get(entry.slot or "", "🛡️")
        lines = [f"{index} {icon} {escape(entry.title)} · +{enhancement}"]
        meta = " · ".join(part for part in (_rarity(entry), escape(entry.slot or "")) if part)
        if meta:
            lines.append(meta)
        if entry.bound:
            lines.append("🔗 Vinculado")
        return lines

    if entry.kind == "consumable":
        grade = f"Grau {grade_label(entry.grade)}" if entry.grade is not None else None
        metadata = f"Consumível · {grade}" if grade else "Consumível"
        return [f"{index} 🧪 {escape(entry.title)} · {entry.quantity}", escape(metadata)]

    if entry.kind == "material":
        icon, meta = MATERIAL_META.get(entry.key, ("🧱", "Material"))
        lines = [f"{index} {icon} {escape(entry.title)} · {entry.quantity}", meta]
        if entry.bound:
            lines.append("🔗 Vinculado")
        return lines

    if entry.kind == "rune":
        lines = [f"{index} 🔷 {escape(entry.title)} · {entry.quantity}"]
        meta = " · ".join(
            part
            for part in (
                _rarity(entry),
                f"Grau {entry.grade}" if entry.grade is not None else "",
            )
            if part
        )
        if meta:
            lines.append(meta)
        if entry.bound:
            lines.append("🔗 Vinculado")
        return lines

    return [f"{index} 📦 {escape(entry.title)} · {entry.quantity}"]


def render_inventory(view: InventoryView) -> Screen:
    if view.kind == "inventory_root":
        text = (
            "🎒 Inventário\n\n"
            f"📦 Espaço · {view.used_slots}/{view.capacity}\n\n"
            f"1 🛡️ Equipamentos · {view.equipment_slots}\n"
            f"2 🧪 Consumíveis · {view.consumable_slots}\n"
            f"3 🧱 Materiais · {view.material_slots}\n"
            f"4 🔷 Runas · {view.rune_slots}"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="1", callback_data="inventory:category:equipment"),
                    InlineKeyboardButton(text="2", callback_data="inventory:category:consumables"),
                    InlineKeyboardButton(text="3", callback_data="inventory:category:materials"),
                    InlineKeyboardButton(text="4", callback_data="inventory:category:runes"),
                ],
                [InlineKeyboardButton(text="← Voltar", callback_data="menu:back")],
            ]
        )
        return Screen(text, "inventory", keyboard)

    if view.kind == "inventory_category":
        headings = {
            "equipment": "🛡️ Equipamentos",
            "consumables": "🧪 Consumíveis",
            "materials": "🧱 Materiais",
            "runes": "🔷 Runas",
        }
        lines = [
            headings.get(view.category or "", "🎒 Inventário"),
            "",
            f"🎒 Inventário · {view.used_slots}/{view.capacity}",
            "",
        ]
        if not view.entries:
            lines.append("Nenhum item nesta categoria.")
        else:
            for index, entry in enumerate(view.entries, start=1):
                if index > 1:
                    lines.append("")
                lines.extend(_entry_lines(index, entry))
        rows = []
        rows.extend(
            [
                InlineKeyboardButton(
                    text=f"Usar · {entry.title}",
                    callback_data=f"consumable:vigor:{entry.key}",
                )
            ]
            for entry in view.entries
            if entry.kind == "consumable"
            and entry.quantity > 0
            and (entry.payload or {}).get("family") == "vigor"
        )
        rows.append([InlineKeyboardButton(text="← Inventário", callback_data="inventory:root")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
        return Screen("\n".join(lines), "inventory", keyboard, parse_mode="HTML")

    lines = [
        "📦 Entregas Pendentes",
        "",
        f"📦 Espaço · {view.pending_count}/{view.pending_capacity}",
    ]
    if view.blocked_delivery_count:
        lines.extend(
            [
                "",
                f"⚠️ Entregas aguardando espaço · {view.blocked_delivery_count}",
            ]
        )
    lines.append("")
    if not view.entries:
        lines.append("Nenhuma Entrega Pendente.")
    else:
        for index, entry in enumerate(view.entries, start=1):
            if index > 1:
                lines.append("")
            lines.extend(_entry_lines(index, entry))
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Inventário", callback_data="inventory:root")],
            [InlineKeyboardButton(text="← Voltar", callback_data="menu:back")],
        ]
    )
    return Screen("\n".join(lines), "pending", keyboard, parse_mode="HTML")
