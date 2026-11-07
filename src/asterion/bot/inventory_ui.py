"""Telegram rendering for Inventory and Pending read models."""

from html import escape
from uuid import UUID

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
RARITY_LABEL = {
    "comum": "Comum",
    "common": "Comum",
    "raro": "Raro",
    "rare": "Raro",
    "épico": "Épico",
    "epic": "Épico",
    "lendário": "Lendário",
    "legendary": "Lendário",
    "mítico": "Mítico",
    "mythic": "Mítico",
}

SLOT_ICON = {
    "main_hand": "🗡️",
    "2H": "🗡️",
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
SLOT_LABEL = {
    "main_hand": "Arma Principal",
    "2H": "Arma Principal",
    "off_hand": "Arma Secundária",
    "head": "Cabeça",
    "torso": "Torso",
    "hands": "Mãos",
    "feet": "Pés",
    "accessory": "Acessório",
    "artifact": "Artefato",
    "Principal": "Arma Principal",
    "Arma Principal": "Arma Principal",
    "Secundária": "Arma Secundária",
    "Arma Secundária": "Arma Secundária",
    "Cabeça": "Cabeça",
    "Torso": "Torso",
    "Mãos": "Mãos",
    "Pés": "Pés",
    "Acessório": "Acessório",
    "Artefato": "Artefato",
}

MATERIAL_META = {
    "material.confins.ferro_baliza": ("⛏️", "Metal · Grau VI"),
    "material.confins.couro_marcha": ("🐾", "Couro · Grau VI"),
    "material.confins.musgo_limiar": ("🌿", "Reagente · Grau VI"),
    "material.confins.po_referencia": ("✨", "Essência · Grau VI"),
    "material.tdo.catalisador_elite_vi": ("⚗️", "Recurso Especial · Grau VI"),
    "material.tdo.fragmento_aprimoramento_vi": ("🪨", "Recurso Especial · Grau VI"),
    "material.tdo.ferro_de_fuligem": ("⛏️", "Metal · Grau I"),
    "material.tdo.couro_escoriado": ("🐾", "Couro · Grau I"),
    "material.tdo.erva_cinzenta": ("🌿", "Reagente · Grau I"),
    "material.tdo.residuo_ocaso": ("💧", "Essência · Grau I"),
    "material.tdo.catalisador_elite_i": ("⚗️", "Recurso Especial · Grau I"),
    "material.tdo.fragmento_aprimoramento_i": ("🪨", "Recurso Especial · Grau I"),
    "material.tdo.nucleo_vigia_partido": ("💠", "Núcleo de Chefe"),
}

CONSUMABLE_FAMILY_LABELS = {
    "healing": "Cura",
    "purification": "Purificação",
    "antidote": "Antídoto",
    "vigor": "Vigor",
    "protection": "Proteção",
    "dispeller": "Dissipador",
    "warding": "Resguardo",
}

CONSUMABLE_DETAILS = {
    "healing": (
        "❤️ Cura · 22% HP Máximo",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "purification": (
        "✨ Purificação · 1 Efeito Negativo",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "antidote": (
        "☣️ Antídoto · 1 DoT",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "vigor": (
        "⚡ Vigor · +20",
        "🎯 Alvo · Próprio",
        "🌙 Uso · Fora de Combate",
    ),
    "protection": (
        "🔰 Barreira · 12% do HP Máximo",
        "⏳ Duração · 2T",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "dispeller": (
        "✨ Dissipação · 1 Efeito Positivo Removível",
        "🎯 Alvo · 1 Inimigo",
        (
            "ℹ️ Efeitos acumuláveis perdem 1 Acúmulo. "
            "Efeitos protegidos ou não removíveis não são opções válidas."
        ),
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "warding": (
        "🛡️ Resguardo · 2T · 1 Carga",
        "Bloqueia a primeira aplicação elegível de Efeito Negativo removível.",
        (
            "ℹ️ O Dano Direto associado continua normalmente. Não bloqueia Controle Rígido, fases, "
            "mecânicas fixas ou efeitos protegidos."
        ),
        "⚔️ Uso · Somente em Combate PvE",
    ),
}


def _rarity(entry: InventoryEntry) -> str:
    if not entry.rarity:
        return ""
    label = RARITY_LABEL.get(entry.rarity.casefold())
    if label is None:
        return "⚪ Equipamento"
    return f"{RARITY_ICON[label]} {label}"


def _entry_lines(index: int, entry: InventoryEntry) -> list[str]:
    if entry.kind == "equipment":
        enhancement = int((entry.payload or {}).get("enhancement", 0))
        icon = SLOT_ICON.get(entry.slot or "", "🛡️")
        lines = [f"{index} {icon} {escape(entry.title)} · +{enhancement}"]
        meta = " · ".join(
            part
            for part in (
                _rarity(entry),
                escape(SLOT_LABEL.get(entry.slot or "", entry.slot or "")),
                f"Nv.{entry.item_level}" if entry.item_level is not None else "",
            )
            if part
        )
        if meta:
            lines.append(meta)
        if entry.bound:
            lines.append("🔗 Vinculado")
        if (entry.payload or {}).get("favorite"):
            lines.append("⭐ Favorito")
        if (entry.payload or {}).get("locked"):
            lines.append("🔒 Protegido")
        runes = (entry.payload or {}).get("runes")
        if isinstance(runes, (list, tuple)) and runes:
            lines.append(f"🔷 Runas · {len(runes)}")
        if entry.equipped:
            lines.append("✅ Equipado")
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

    if entry.kind == "blocked_delivery":
        payload = entry.payload or {}
        item_kind = payload.get("delivery_kind")
        if item_kind == "equipment":
            enhancement = int(payload.get("enhancement", 0))
            lines = [f"{index} ⚠️ {escape(entry.title)} · +{enhancement}"]
            details = " · ".join(
                part
                for part in (
                    _rarity(entry),
                    escape(SLOT_LABEL.get(entry.slot or "", entry.slot or "")),
                    f"Nv.{entry.item_level}" if entry.item_level is not None else "",
                )
                if part
            )
            if details:
                lines.append(details)
            if entry.bound:
                lines.append("🔗 Vinculado")
            if payload.get("favorite"):
                lines.append("⭐ Favorito")
            if payload.get("locked"):
                lines.append("🔒 Protegido")
            return lines
        if item_kind == "material":
            lines = [f"{index} ⚠️ {escape(entry.title)} · {entry.quantity}"]
            if entry.bound:
                lines.append("🔗 Vinculado")
            return lines
        if item_kind == "rune":
            lines = [f"{index} ⚠️ 🔷 {escape(entry.title)} · {entry.quantity}"]
            if entry.rarity or entry.grade is not None:
                details = " · ".join(
                    part
                    for part in (
                        _rarity(entry),
                        f"Grau {entry.grade}" if entry.grade is not None else "",
                    )
                    if part
                )
                lines.append(details)
            if entry.bound:
                lines.append("🔗 Vinculado")
            return lines
        if item_kind == "consumable":
            return [f"{index} ⚠️ {escape(entry.title)} · {entry.quantity}"]

    return [f"{index} 📦 {escape(entry.title)} · {entry.quantity}"]


def render_inventory(view: InventoryView) -> Screen:
    if view.kind == "inventory_root":
        text = (
            "🎒 Inventário\n\n"
            f"📦 Espaço · {view.used_slots}/{view.capacity}\n\n"
            f"1 🛡️ Equipamentos · {view.equipment_slots}\n"
            f"2 🧪 Consumíveis · {view.consumable_slots}\n"
            f"3 🧱 Materiais · {view.material_slots}\n"
            f"4 🔷 Runas · {view.rune_slots}\n"
            f"📦 Pendentes · {view.pending_count}/{view.pending_capacity}"
            + (
                f" · {view.blocked_delivery_count} aguardando espaço"
                if view.blocked_delivery_count
                else ""
            )
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="1", callback_data="inventory:category:equipment"),
                    InlineKeyboardButton(text="2", callback_data="inventory:category:consumables"),
                    InlineKeyboardButton(text="3", callback_data="inventory:category:materials"),
                    InlineKeyboardButton(text="4", callback_data="inventory:category:runes"),
                ],
                [
                    InlineKeyboardButton(text="Armazém", callback_data="warehouse:root"),
                    InlineKeyboardButton(text="Pendentes", callback_data="pending:root"),
                ],
                [InlineKeyboardButton(text="← Personagem", callback_data="character:root")],
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
        equipment_buttons = []
        warehouse_equipment_buttons = []
        if view.category == "equipment":
            for index, entry in enumerate(view.entries, start=1):
                if entry.kind != "equipment":
                    continue
                try:
                    item_id = UUID(entry.key)
                except (ValueError, TypeError, AttributeError):
                    continue
                equipment_buttons.append(
                    InlineKeyboardButton(
                        text=str(index), callback_data=f"eq:v:{item_id.hex}"
                    )
                )
                if not entry.equipped and not bool((entry.payload or {}).get("locked")):
                    warehouse_equipment_buttons.append(
                        InlineKeyboardButton(
                            text=f"Guardar {index}",
                            callback_data=f"warehouse:deposit:equipment:{item_id.hex}",
                        )
                    )
        consumable_buttons = [
            InlineKeyboardButton(
                text=str(index),
                callback_data=f"inventory:consumable:{entry.key}",
            )
            for index, entry in enumerate(view.entries, start=1)
            if entry.kind == "consumable" and entry.payload is not None
        ]
        rows = [
            equipment_buttons[offset : offset + 5]
            for offset in range(0, len(equipment_buttons), 5)
        ]
        rows.extend(
            warehouse_equipment_buttons[offset : offset + 2]
            for offset in range(0, len(warehouse_equipment_buttons), 2)
        )
        if view.category == "materials":
            material_buttons = [
                InlineKeyboardButton(
                    text=f"Guardar {index}",
                    callback_data=(
                        "warehouse:deposit:material:"
                        f"{entry.payload['warehouse_source_id'].replace('-', '')}"
                    ),
                )
                for index, entry in enumerate(view.entries, start=1)
                if entry.kind == "material"
                and entry.payload
                and entry.payload.get("warehouse_source_id")
            ]
            rows.extend(
                material_buttons[offset : offset + 2]
                for offset in range(0, len(material_buttons), 2)
            )
        rows.extend(
            consumable_buttons[index : index + 5]
            for index in range(0, len(consumable_buttons), 5)
        )
        rows.append([InlineKeyboardButton(text="← Inventário", callback_data="inventory:root")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
        return Screen("\n".join(lines), "inventory", keyboard, parse_mode="HTML")

    if view.kind == "inventory_consumable_detail" and view.entries:
        entry = view.entries[0]
        family = (entry.payload or {}).get("family", "")
        label = CONSUMABLE_FAMILY_LABELS.get(family, "Consumível")
        grade = grade_label(entry.grade) if entry.grade is not None else "?"
        lines = [
            f"🧪 {escape(entry.title)} · Grau {grade}",
            f"Consumível · {escape(label)}",
            "",
            f"🎒 Quantidade · {entry.quantity}",
            "",
            *CONSUMABLE_DETAILS.get(family, ()),
        ]
        rows = []
        if family == "vigor" and view.vigor_usable and entry.quantity > 0:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Usar",
                        callback_data=f"consumable:vigor:{entry.key}",
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="← Consumíveis",
                    callback_data="inventory:category:consumables",
                )
            ]
        )
        return Screen("\n".join(lines), "inventory", InlineKeyboardMarkup(inline_keyboard=rows))

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
            if entry.payload and entry.payload.get("origin"):
                lines.append(f"Origem · {escape(str(entry.payload['origin']))}")
    claim_buttons = [
        InlineKeyboardButton(
            text=f"Resgatar {index}",
            callback_data=f"pending:claim:{entry.key.replace('-', '')}",
        )
        for index, entry in enumerate(view.entries, start=1)
        if entry.kind in {"equipment", "material", "rune", "consumable"}
    ]
    rows = [claim_buttons[offset : offset + 3] for offset in range(0, len(claim_buttons), 3)]
    if view.blocked_delivery_count:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Tentar entregas bloqueadas", callback_data="pending:retry"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="← Inventário", callback_data="inventory:root")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return Screen("\n".join(lines), "pending", keyboard, parse_mode="HTML")
