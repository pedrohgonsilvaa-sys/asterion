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
from asterion.bot.ui_format import roman
from asterion.domain.equipment import EquipmentSlot
from asterion.domain.equipment_modifications import equipment_grade

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


# Especificação consolidada 2026-11-26, Parte I §1–§2.
ROOT_TITLE = "🛡️ Equipamentos"
ROOT_TEXT = (
    "Os equipamentos usados pelo personagem ocupam posições específicas e podem ser "
    "substituídos conforme a jornada avança."
)
# (posição, rótulo na tela, emoji)
ROOT_SLOTS = (
    (EquipmentSlot.PRINCIPAL, "Principal", "⚔️"),
    (EquipmentSlot.SECUNDARIA, "Secundária", "⚔️"),
    (EquipmentSlot.CABECA, "Cabeça", "🪖"),
    (EquipmentSlot.TORSO, "Torso", "🥋"),
    (EquipmentSlot.MAOS, "Mãos", "🧤"),
    (EquipmentSlot.PES, "Pés", "🥾"),
    (EquipmentSlot.ACESSORIO, "Acessório", "💍"),
    (EquipmentSlot.ARTEFATO, "Artefato", "🔮"),
)
ROOT_SLOT_EMOJI = {slot: emoji for slot, _, emoji in ROOT_SLOTS}
HANDS_LABELS = {"1 mão": "1 Mão", "2 mãos": "2 Mãos"}


def _field(emoji: str, label: str, value: str) -> str:
    return f"{emoji} <b>{escape(label)}</b> · <code>{escape(value)}</code>"


def _item_name(item: EquipmentItemView) -> str:
    return item.name + (f" +{item.enhancement}" if item.enhancement else "")


def render_equipment_root(view: EquipmentRootView) -> Screen:
    lines = []
    buttons = []
    for index, slot_view in enumerate(view.slots):
        slot, label, emoji = ROOT_SLOTS[index]
        code = SLOT_CODES[slot]
        if slot_view.blocked_by_two_handed:
            value = "Bloqueada"
        elif slot_view.item is None:
            value = "Vazio"
        else:
            value = _item_name(slot_view.item)
        lines.append(_field(emoji, label, value))
        if slot_view.blocked_by_two_handed:
            continue
        buttons.append(
            InlineKeyboardButton(
                text=f"{emoji} {label}",
                callback_data=f"eq:s:{code}:{view.combat_configuration_version}",
            )
        )
    rows = [buttons[offset : offset + 2] for offset in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="character:root")])
    return Screen(
        "\n\n".join(
            (f"<b>{escape(ROOT_TITLE)}</b>", f"<i>{escape(ROOT_TEXT)}</i>", "\n".join(lines))
        ),
        "equipment",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _proficiency(item: EquipmentItemView) -> str | None:
    if item.weapon_proficiency_label:
        return item.weapon_proficiency_label.split(" · ")[-1]
    return item.armor_class_label


def render_equipment_detail(view: EquipmentDetailView, *, context: str) -> Screen:
    """Detalhe do Equipamento (§2): sem Posição, Forma, Nível do Item nem
    Compatibilidade de Artes."""
    item = view.item
    icon = ROOT_SLOT_EMOJI[item.slot]
    rarity = _rarity_label(item.rarity)
    parts = [f"{icon} <b>{escape(_item_name(item))}</b>"]
    if item.lore:
        parts.append(f"<i>{escape(item.lore)}</i>")
    attributes = _attribute_lines(item)
    if attributes:
        parts.append("\n".join(attributes))
    parts.append(
        "\n".join(
            (
                _field("✨", "Grau", roman(equipment_grade(item.item_level))),
                _field(RARITY_ICON.get(rarity, "⚪"), "Raridade", rarity),
            )
        )
    )
    details = []
    if item.weapon_handedness_label:
        hands = HANDS_LABELS.get(item.weapon_handedness_label, item.weapon_handedness_label)
        details.append(_field("👐", "Mãos", hands))
    if proficiency := _proficiency(item):
        details.append(_field("🛡️", "Proficiência", proficiency))
    if item.bound:
        details.append(_field("🔗", "Vínculo", "Vinculado"))
    if details:
        parts.append("\n".join(details))

    version = view.combat_configuration_version
    token = item.item_instance_id.hex
    slot_code = SLOT_CODES[item.slot]
    rows: list[list[InlineKeyboardButton]] = []
    if context == "s":
        rows.append(
            [
                InlineKeyboardButton(text="🔄 Trocar", callback_data=f"eq:c:{slot_code}:{version}"),
                InlineKeyboardButton(
                    text="❌ Desequipar", callback_data=f"eq:u:{slot_code}:{version}:s"
                ),
            ]
        )
    elif item.equipped:
        rows.append(
            [
                InlineKeyboardButton(
                    text="❌ Desequipar", callback_data=f"eq:u:{slot_code}:{version}:i"
                )
            ]
        )
    elif item.eligible:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Equipar", callback_data=f"eq:e:{token}:{version}:i"
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text="🔮 Runas", callback_data=f"em:r:{token}"),
            InlineKeyboardButton(text="✨ Encantamento", callback_data=f"em:e:{token}"),
        ]
    )
    upkeep = []
    if item.enhancement < 10:
        upkeep.append(InlineKeyboardButton(text="🔨 Aprimorar", callback_data=f"em:h:{token}"))
    if not item.favorite and not item.locked and not item.runes:
        upkeep.append(InlineKeyboardButton(text="🔧 Desmontar", callback_data=f"em:d:{token}"))
    if upkeep:
        rows.append(upkeep)
    rows.append(
        [
            InlineKeyboardButton(
                text="🚫 Desbloquear" if item.locked else "🚫 Bloquear",
                callback_data=f"em:k:{token}:{item.item_version}:{version}",
            ),
            InlineKeyboardButton(
                text="⭐ Desfavoritar" if item.favorite else "⭐ Favoritar",
                callback_data=f"em:f:{token}:{item.item_version}:{version}",
            ),
        ]
    )
    if item.reroll_available:
        rows.append([InlineKeyboardButton(text="🎲 Reroll", callback_data=f"em:l:{token}")])
    back = "eq:r" if context == "s" else "inventory:category:equipment"
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data=back)])
    return Screen(
        "\n\n".join(parts),
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
            lines.append(f"{escape(item.name)} · +{item.enhancement}")
            lines.append(
                f"{RARITY_ICON.get(_rarity_label(item.rarity), '⚪')} "
                f"{escape(_rarity_label(item.rarity))} · {SLOT_LABELS[item.slot]}"
            )
            lines.extend(_origin_lines(item))
            lines.append(f"📈 Nível do Item · {item.item_level}")
            lines.extend(_attribute_lines(item))
    buttons = [
        InlineKeyboardButton(
            text=f"{item.name} +{item.enhancement}",
            callback_data=(
                f"eq:e:{item.item_instance_id.hex}:{view.combat_configuration_version}:s"
            ),
        )
        for index, item in enumerate(view.candidates, start=1)
    ]
    rows = [[button] for button in buttons]
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="eq:r")])
    return Screen(
        "\n".join(lines),
        "equipment",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _origin_lines(item: EquipmentItemView) -> list[str]:
    lines = []
    if item.armor_class_label is not None:
        lines.append(f"🛡️ Classe de Armadura · {escape(item.armor_class_label)}")
    if item.region_label is not None:
        lines.append(f"🗺️ Região · {escape(item.region_label)}")
    return lines


def _attribute_lines(item: EquipmentItemView) -> list[str]:
    lines = []
    for attribute, icon, label, percentage in ATTRIBUTE_PRESENTATION:
        value = getattr(item.contribution, attribute)
        if value == 0:
            continue
        formatted = _decimal_text(value)
        suffix = "%" if percentage else ""
        lines.append(_field(icon, label, f"+{formatted}{suffix}"))
    return lines


def _decimal_text(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _rarity_label(value: str) -> str:
    return RARITY_LABEL.get(value.casefold(), "Raridade desconhecida")
