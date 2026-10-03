"""Telegram screens for the character's acquired cosmetics."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.cosmetic_catalog import (
    COSMETIC_TYPE_LABELS,
    COSMETIC_TYPE_NOUNS,
    COSMETIC_TYPES,
    COSMETIC_USE_BUTTONS,
)
from asterion.application.cosmetics import CosmeticCategoryView, CosmeticsView
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID
from asterion.bot.creation_ui import Screen

TYPE_CODES = {kind: str(index) for index, kind in enumerate(COSMETIC_TYPES)}
TYPE_BY_CODE = {value: key for key, value in TYPE_CODES.items()}
COSMETIC_INDEX = {}
COSMETIC_BY_INDEX = {}


def _initialize_catalog():
    from asterion.application.cosmetic_catalog import COSMETICS

    global COSMETIC_INDEX, COSMETIC_BY_INDEX
    COSMETIC_INDEX = {item.cosmetic_id: index for index, item in enumerate(COSMETICS)}
    COSMETIC_BY_INDEX = {index: item.cosmetic_id for index, item in enumerate(COSMETICS)}


_initialize_catalog()


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _markup(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def render_cosmetics_root(view: CosmeticsView) -> Screen:
    labels = (
        "🧍 Aparência · Visual",
        "🎖️ Título · Identidade",
        "🔰 Emblema · Distinção",
        "🖼️ Moldura · Perfil",
        "🏳️ Banner · Exibição",
    )
    rows = [[_button(str(index + 1), f"cos:c:{index}")] for index in range(len(COSMETIC_TYPES))]
    rows.append([_button("← Personagem", "character:root")])
    return Screen(
        "🎨 Cosméticos\n\n"
        + "\n".join(f"{index + 1} {label}" for index, label in enumerate(labels)),
        "character",
        _markup(rows),
    )


def render_cosmetic_category(category: CosmeticCategoryView) -> Screen:
    kind = category.cosmetic_type
    lines = [f"🎨 {COSMETIC_TYPE_LABELS[kind]}", ""]
    rows = []
    if category.selected is not None:
        lines.extend([category.selected.name, "Selecionado", ""])
    if not category.items:
        if category.selected is None:
            lines.append("Nenhum cosmético desta categoria foi adquirido.")
        else:
            lines.append("Nenhum outro cosmético desta categoria foi adquirido.")
    else:
        for index, item in enumerate(category.items, 1):
            lines.append(f"{index} {item.name}")
            source = ACHIEVEMENT_BY_ID.get(item.source_achievement_id)
            lines.append(f"Origem · Feito {source.name if source else 'TDO'}")
            rows.append([_button(str(index), f"cos:d:{COSMETIC_INDEX[item.cosmetic_id]}")])
    rows.append([_button("← Cosméticos", "cos:r")])
    return Screen("\n".join(lines), "character", _markup(rows))


def render_cosmetic_detail(view: CosmeticsView, item_index: int) -> Screen:
    from asterion.application.cosmetic_catalog import COSMETICS

    if not 0 <= item_index < len(COSMETICS):
        return render_cosmetics_root(view)
    definition = COSMETICS[item_index]
    category = next(
        item for item in view.categories if item.cosmetic_type == definition.cosmetic_type
    )
    owned_ids = {item.cosmetic_id for item in category.items}
    if category.selected:
        owned_ids.add(category.selected.cosmetic_id)
    if definition.cosmetic_id not in owned_ids:
        return render_cosmetic_category(category)
    source = ACHIEVEMENT_BY_ID.get(definition.achievement_id)
    text = (
        f"🎨 {definition.name}\n{COSMETIC_TYPE_NOUNS[definition.cosmetic_type]}"
        f"\n\nOrigem · Feito {source.name if source else 'TDO'}"
    )
    selected_id = category.selected.cosmetic_id if category.selected else None
    rows = []
    if selected_id != definition.cosmetic_id:
        rows.append(
            [
                _button(
                    COSMETIC_USE_BUTTONS[definition.cosmetic_type],
                    f"cos:u:{item_index}:{_selected_token(selected_id)}",
                )
            ]
        )
    rows.append([_button("← Coleção", f"cos:c:{TYPE_CODES[definition.cosmetic_type]}")])
    return Screen(text, "character", _markup(rows))


def _selected_token(cosmetic_id: str | None) -> str:
    return "0" if cosmetic_id is None else str(COSMETIC_INDEX[cosmetic_id] + 1)
