"""Pure Telegram rendering for the Character Equipment and item-detail flows."""

from decimal import Decimal
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.equipment_view import (
    EquipmentCandidatesView,
    EquipmentDetailView,
    EquipmentItemView,
    EquipmentRootView,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.equipment import EquipmentSlot

SLOT_PRESENTATION = (
    (EquipmentSlot.PRINCIPAL, "Arma Principal", "🗡️", "p"),
    (EquipmentSlot.SECUNDARIA, "Arma Secundária", "⚔️", "s"),
    (EquipmentSlot.CABECA, "Cabeça", "🪖", "h"),
    (EquipmentSlot.TORSO, "Torso", "🥋", "t"),
    (EquipmentSlot.MAOS, "Mãos", "🧤", "m"),
    (EquipmentSlot.PES, "Pés", "🥾", "f"),
    (EquipmentSlot.ACESSORIO, "Acessório", "💍", "a"),
    (EquipmentSlot.ARTEFATO, "Artefato", "🧿", "r"),
)
SLOT_LABELS = {slot: label for slot, label, _, _ in SLOT_PRESENTATION}
SLOT_CODES = {slot: code for slot, _, _, code in SLOT_PRESENTATION}
CODE_SLOTS = {code: slot for slot, _, _, code in SLOT_PRESENTATION}
RARITY_ICON = {
    "Comum": "⚪",
    "Raro": "🔵",
    "Épico": "🟣",
    "Lendário": "🟠",
    "Mítico": "🔴",
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
ATTRIBUTE_PRESENTATION = (
    ("hp", "❤️", "HP", False),
    ("attack", "⚔️", "ATQ", False),
    ("defense", "🛡️", "DEF", False),
    ("agility", "💨", "AGI", False),
    ("per", "🗡️", "PER", True),
    ("crit", "💥", "CRIT", True),
    ("evasion", "💨", "Esquiva", True),
    ("block", "🛡️", "Bloqueio", True),
)


def render_equipment_root(view: EquipmentRootView) -> Screen:
    lines = ["🛡️ Equipamentos", ""]
    buttons = []
    for index, slot_view in enumerate(view.slots, start=1):
        slot, label, icon, code = SLOT_PRESENTATION[index - 1]
        if slot_view.blocked_by_two_handed:
            lines.append(f"{index} {icon} {label} · Bloqueada")
            lines.append("🔒 Arma de 2 mãos equipada")
            continue
        item = slot_view.item
        if item is None:
            lines.append(f"{index} {icon} {label} · Vazio")
        else:
            lines.append(
                f"{index} {icon} {label} · {escape(item.name)} · +{item.enhancement}"
            )
        buttons.append(
            InlineKeyboardButton(
                text=str(index),
                callback_data=f"eq:s:{code}:{view.combat_configuration_version}",
            )
        )
    rows = [buttons[offset : offset + 4] for offset in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton(text="← Personagem", callback_data="character:root")])
    return Screen(
        "\n".join(lines),
        "equipment",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def render_equipment_detail(view: EquipmentDetailView, *, context: str) -> Screen:
    item = view.item
    icon = next(icon for slot, _, icon, _ in SLOT_PRESENTATION if slot == item.slot)
    label = SLOT_LABELS[item.slot]
    rarity = _rarity_label(item.rarity)
    rarity_icon = RARITY_ICON.get(rarity, "⚪")
    lines = [
        f"{icon} {escape(item.name)} · +{item.enhancement}",
        f"{rarity_icon} {escape(rarity)} · {label}",
    ]
    if context == "i" and item.equipped:
        lines.append("✅ Equipado")
    if item.bound:
        lines.append("🔗 Vinculado")
    lines.append(f"📈 Nível do Item · {item.item_level}")
    if not item.eligible:
        lines.append(f"⏳ Requer Nv. {item.item_level}")
    attributes = _attribute_lines(item)
    if attributes:
        lines.extend(("", *attributes))
    if item.lore:
        lines.extend(("", escape(item.lore)))

    rows: list[list[InlineKeyboardButton]] = []
    version = view.combat_configuration_version
    if context == "s":
        slot_code = SLOT_CODES[item.slot]
        rows.append(
            [
                InlineKeyboardButton(
                    text="Trocar", callback_data=f"eq:c:{slot_code}:{version}"
                ),
                InlineKeyboardButton(
                    text="Desequipar", callback_data=f"eq:u:{slot_code}:{version}:s"
                ),
            ]
        )
        rows.append([InlineKeyboardButton(text="← Equipamentos", callback_data="eq:r")])
    else:
        slot_code = SLOT_CODES[item.slot]
        if item.equipped:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Desequipar", callback_data=f"eq:u:{slot_code}:{version}:i"
                    )
                ]
            )
        elif item.eligible:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Equipar",
                        callback_data=f"eq:e:{item.item_instance_id.hex}:{version}:i",
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="← Equipamentos", callback_data="inventory:category:equipment"
                )
            ]
        )
    return Screen(
        "\n".join(lines),
        "equipment_item",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def render_equipment_candidates(view: EquipmentCandidatesView) -> Screen:
    label = SLOT_LABELS[view.slot]
    lines = [f"🛡️ Equipamentos · {label}", ""]
    if view.blocked_by_two_handed:
        lines.extend(("🔒 Arma de 2 mãos equipada", "", "Este slot está bloqueado."))
    elif not view.candidates:
        lines.append("Nenhum Equipamento compatível disponível.")
    else:
        for index, item in enumerate(view.candidates, start=1):
            if index > 1:
                lines.append("")
            lines.append(
                f"{index} {escape(item.name)} · +{item.enhancement}"
            )
            lines.append(
                f"{RARITY_ICON.get(_rarity_label(item.rarity), '⚪')} "
                f"{escape(_rarity_label(item.rarity))} · {SLOT_LABELS[item.slot]}"
            )
            lines.append(f"📈 Nível do Item · {item.item_level}")
            lines.extend(_attribute_lines(item))
    buttons = [
        InlineKeyboardButton(
            text=str(index),
            callback_data=(
                f"eq:e:{item.item_instance_id.hex}:"
                f"{view.combat_configuration_version}:s"
            ),
        )
        for index, item in enumerate(view.candidates, start=1)
    ]
    rows = [buttons[offset : offset + 5] for offset in range(0, len(buttons), 5)]
    rows.append([InlineKeyboardButton(text="← Equipamentos", callback_data="eq:r")])
    return Screen(
        "\n".join(lines),
        "equipment",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _attribute_lines(item: EquipmentItemView) -> list[str]:
    lines = []
    for attribute, icon, label, percentage in ATTRIBUTE_PRESENTATION:
        value = getattr(item.contribution, attribute)
        if value == 0:
            continue
        formatted = _decimal_text(value)
        suffix = "%" if percentage else ""
        lines.append(f"{icon} {label} +{formatted}{suffix}")
    return lines


def _decimal_text(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _rarity_label(value: str) -> str:
    return RARITY_LABEL.get(value.casefold(), "Raridade desconhecida")
