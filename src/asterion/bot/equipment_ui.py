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
from asterion.bot.item_lines import (
    component_stat,
    equipment_name,
    rarity_emoji,
    stat_line,
    stat_parts,
)
from asterion.bot.ui_format import (
    CHARACTER_SKIN,
    keycap,
    numeric_rows,
    page_bounds,
    page_nav,
    pairs,
    roman,
)
from asterion.domain.equipment import EquipmentSlot
from asterion.domain.equipment_modifications import (
    ENCHANTMENT_FAMILIES,
    RUNE_FAMILIES,
    equipment_grade,
)
from asterion.domain.item_descriptions import (
    EQUIPMENT_SLOT_DESCRIPTIONS,
    WEAPON_FORM_DESCRIPTIONS,
)

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


# UI aprovada: Personagem → Equipamentos (2 páginas de 4), Detalhe e Seleção.
ROOT_TITLE = "🛡️ Equipamentos"
ROOT_TEXT = (
    "Aqui ficam os equipamentos que acompanham seu personagem. Cada peça ocupa uma "
    "posição específica e contribui com seus próprios atributos para a jornada."
)
# (posição, rótulo na tela, emoji)
ROOT_SLOTS = (
    (EquipmentSlot.PRINCIPAL, "Principal", "✋"),
    (EquipmentSlot.SECUNDARIA, "Secundária", "🤚"),
    (EquipmentSlot.CABECA, "Cabeça", "🪖"),
    (EquipmentSlot.TORSO, "Torso", "🥋"),
    (EquipmentSlot.MAOS, "Mãos", "🧤"),
    (EquipmentSlot.PES, "Pés", "🥾"),
    (EquipmentSlot.ACESSORIO, "Acessório", "💍"),
    (EquipmentSlot.ARTEFATO, "Artefato", "🔮"),
)
ROOT_SLOT_EMOJI = {slot: emoji for slot, _, emoji in ROOT_SLOTS}


CANDIDATES_PER_PAGE = 6
HANDS_LABELS = {"1 mão": "1 Mão", "2 mãos": "2 Mãos"}
EMPTY_CANDIDATES_TEXT = (
    "Nenhum equipamento compatível está disponível para esta posição. Obtenha um "
    "equipamento compatível para poder equipá-lo."
)
CANDIDATES_TEXT = "Neste espaço, escolha entre os equipamentos compatíveis disponíveis para equipar."  # noqa: E501


def _field(emoji: str, label: str, value: str) -> str:
    return f"{emoji} <b>{escape(label)}</b> · <code>{escape(value)}</code>"


def _item_name(item: EquipmentItemView) -> str:
    return equipment_name(item.name, item.enhancement)


def render_equipment_root(view: EquipmentRootView, page: int = 0) -> Screen:
    """As 8 posições numa única página, com os atributos de cada peça.

    ``page`` fica só para callbacks antigos (``eq:r:1``) e não muda a tela.
    """
    blocks = []
    buttons = []
    for index in range(len(view.slots)):
        slot_view = view.slots[index]
        slot, label, emoji = ROOT_SLOTS[index]
        head = f"{emoji} <b>{escape(label)}</b> · "
        if slot_view.blocked_by_two_handed:
            blocks.append(head + "Bloqueada")
            continue
        item = slot_view.item
        if item is None:
            blocks.append(head + "Vazio")
        else:
            favorite = "⭐" if item.favorite else ""
            lines = [f"{head}{favorite}{rarity_emoji(item.rarity)} {escape(_item_name(item))}"]
            if attributes := stat_line(item.contribution):
                lines.append(attributes)
            blocks.append("\n".join(lines))
        buttons.append(
            InlineKeyboardButton(
                text=f"{emoji} {label}",
                callback_data=f"eq:s:{SLOT_CODES[slot]}:{view.combat_configuration_version}",
            )
        )
    rows = pairs(buttons)
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="character:root")])
    return Screen(
        "\n\n".join(
            (f"<b>{escape(ROOT_TITLE)}</b>", f"<i>{escape(ROOT_TEXT)}</i>", "\n\n".join(blocks))
        ),
        CHARACTER_SKIN,
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def _proficiency(item: EquipmentItemView) -> str | None:
    if item.weapon_proficiency_label:
        return item.weapon_proficiency_label.split(" · ")[-1]
    return item.armor_class_label


def _component_lines(
    emoji: str, label: str, name: str, attribute: str | None, potency: str | None
) -> str:
    lines = [_field(emoji, label, name)]
    if attribute and potency and (effect := component_stat(attribute, potency)):
        lines.append(effect)
    return "\n".join(lines)


def _default_description(item) -> str | None:
    """Descrição por tipo quando o item não traz texto próprio (``lore``)."""
    if item.slot in {EquipmentSlot.PRINCIPAL, EquipmentSlot.SECUNDARIA}:
        return WEAPON_FORM_DESCRIPTIONS.get(item.weapon_form_label or "")
    return EQUIPMENT_SLOT_DESCRIPTIONS.get(item.slot.value)


def render_equipment_detail(view: EquipmentDetailView, *, context: str) -> Screen:
    """Detalhe aprovado: ações somente Trocar, Desequipar, Favoritar e Retornar.

    Runas, Encantamento, Aprimoramento e Desmontagem pertencem ao fluxo da Forja e
    não são ações desta tela; Runa e Encantamento aparecem apenas como estado.
    """
    item = view.item
    icon = "🗡️" if item.slot in {EquipmentSlot.PRINCIPAL, EquipmentSlot.SECUNDARIA} else (
        ROOT_SLOT_EMOJI[item.slot]
    )
    rarity = _rarity_label(item.rarity)
    parts = [f"<b>{icon} {escape(_item_name(item))}</b>"]
    if description := item.lore or _default_description(item):
        parts.append(f"<i>{escape(description)}</i>")
    # Especificação visual 2026-11-28: atributos | Grau, Raridade, Quantidade |
    # Empunhadura, Proficiência, Vínculo, em três blocos.
    stats = [
        _field(attr_icon, label, value)
        for attr_icon, label, value in stat_parts(item.contribution, attack_icon="🗡️")
    ]
    if stats:
        parts.append("\n".join(stats))
    parts.append(
        "\n".join(
            (
                _field("✨", "Grau", roman(equipment_grade(item.item_level))),
                _field(RARITY_ICON.get(rarity, "⚪"), "Raridade", rarity),
                # Cada equipamento é uma instância única: a quantidade é sempre 1.
                _field("📦", "Quantidade", "1"),
            )
        )
    )
    facts = []
    if item.weapon_handedness_label:
        hands = HANDS_LABELS.get(item.weapon_handedness_label, item.weapon_handedness_label)
        facts.append(_field("✋", "Empunhadura", hands))
    if proficiency := _proficiency(item):
        facts.append(_field("🎓", "Proficiência", proficiency))
    if item.bound:
        facts.append(_field("🔗", "Vínculo", "Vinculado"))
    if facts:
        parts.append("\n".join(facts))
    for rune in item.runes:
        family = str(rune.get("family") or "")
        attribute = RUNE_FAMILIES.get(family, (None, None))[0]
        name = str(rune.get("name") or RUNE_FAMILIES.get(family, (None, family or "Runa"))[1])
        parts.append(_component_lines("🔷", "Runa", name, attribute, rune.get("potency")))
    if item.enchantment:
        enchantment = item.enchantment
        family = str(enchantment.get("family") or "")
        name = str(enchantment.get("name") or family or "Encantamento")
        parts.append(
            _component_lines(
                "💫", "Encantamento", name, ENCHANTMENT_FAMILIES.get(family),
                enchantment.get("potency"),
            )  # fmt: skip
        )
    for ability in item.special_abilities:
        heading = f"🌟 <b>{escape(str(ability.get('name', '')))}</b>"
        if ability.get("type"):
            heading += f" · <code>{escape(str(ability['type']))}</code>"
        text = [heading]
        if ability.get("description"):
            text.append(f"\n<i>{escape(str(ability['description']))}</i>")
        parts.append("\n".join(text))

    version = view.combat_configuration_version
    token = item.item_instance_id.hex
    slot_code = SLOT_CODES[item.slot]
    swap = InlineKeyboardButton(text="🔄 Trocar", callback_data=f"eq:c:{slot_code}:{version}")
    rows: list[list[InlineKeyboardButton]] = []
    if item.equipped:
        rows.append(
            [
                swap,
                InlineKeyboardButton(
                    text="❌ Desequipar", callback_data=f"eq:u:{slot_code}:{version}:{context}"
                ),
            ]
        )
    else:
        rows.append([swap])
    rows.append(
        [
            InlineKeyboardButton(
                text="⭐ Desfavoritar" if item.favorite else "⭐ Favoritar",
                callback_data=f"em:f:{token}:{item.item_version}:{version}",
            )
        ]
    )
    back = "eq:r" if context == "s" else "inventory:category:equipment"
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data=back)])
    return Screen(
        "\n\n".join(parts),
        CHARACTER_SKIN,
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def render_equipment_candidates(view: EquipmentCandidatesView, page: int = 0) -> Screen:
    """Seleção: até 6 equipamentos compatíveis por página; o botão numérico equipa direto."""
    back = [InlineKeyboardButton(text="↩️ Retornar", callback_data="eq:r")]
    title = f"<b>{escape(ROOT_TITLE)}</b>"
    if view.blocked_by_two_handed or not view.candidates:
        text = (
            "Esta posição está bloqueada por uma arma de 2 mãos."
            if view.blocked_by_two_handed
            else EMPTY_CANDIDATES_TEXT
        )
        return Screen(
            f"{title}\n\n<i>{escape(text)}</i>",
            CHARACTER_SKIN,
            InlineKeyboardMarkup(inline_keyboard=[back]),
            parse_mode="HTML",
        )
    page, pages, start = page_bounds(len(view.candidates), page, CANDIDATES_PER_PAGE)
    shown = view.candidates[start : start + CANDIDATES_PER_PAGE]
    blocks = []
    for position, item in enumerate(shown, start=1):
        lines = [f"#{position} {rarity_emoji(item.rarity)} <b>{escape(_item_name(item))}</b>"]
        if attributes := stat_line(item.contribution, attack_icon="🗡️"):
            lines.append(attributes)
        blocks.append("\n".join(lines))
    version = view.combat_configuration_version
    buttons = [
        InlineKeyboardButton(
            text=keycap(position),
            callback_data=f"eq:e:{item.item_instance_id.hex}:{version}:s",
        )
        for position, item in enumerate(shown, start=1)
    ]
    code = SLOT_CODES[view.slot]
    rows = numeric_rows(buttons)
    rows.append(page_nav(page, pages, lambda target: f"eq:c:{code}:{version}:{target}"))
    rows.append(back)
    return Screen(
        "\n\n".join((title, f"<i>{escape(CANDIDATES_TEXT)}</i>", "\n\n".join(blocks))),
        CHARACTER_SKIN,
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
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
