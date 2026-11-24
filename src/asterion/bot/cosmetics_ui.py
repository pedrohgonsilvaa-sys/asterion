"""Telegram screens for the character's acquired cosmetics."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.cosmetic_catalog import (
    COSMETIC_TYPE_LABELS,
    COSMETIC_TYPES,
    COSMETIC_USE_BUTTONS,
    COSMETICS_BY_ID,
    DEFAULT_APPEARANCE_NAME,
)
from asterion.application.cosmetics import CosmeticCategoryView, CosmeticsView
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID, ACHIEVEMENT_CATEGORIES
from asterion.bot.creation_ui import Screen

TYPE_CODES = {kind: str(index) for index, kind in enumerate(COSMETIC_TYPES)}
TYPE_BY_CODE = {value: key for key, value in TYPE_CODES.items()}
DEFAULT_CODE = "x"
ROOT_INTRO = (
    "Escolha como seu personagem se apresenta em Asterion e quais marcas de sua jornada "
    "deseja carregar consigo."
)
CATEGORY_EMOJI = {"appearance": "🧍", "title": "🎖️", "frame": "🖼️"}
# (header, intro, others header, back button)
CATEGORY_HEADERS = {
    "appearance": (
        "🧍 Aparência",
        "As marcas de uma jornada também vivem na forma como ela é lembrada. Escolha o "
        "visual que acompanhará seu personagem pelos caminhos de Asterion.",
        "🗂️ Outras Aparências",
        "← Aparências",
    ),
    "title": (
        "🎖️ Títulos",
        "Alguns nomes são recebidos ao nascer. Outros precisam ser conquistados. Escolha "
        "qual marca de sua jornada acompanhará seu nome por Asterion.",
        "📜 Outros Títulos",
        "← Títulos",
    ),
    # The Source defines no intro text for Frames: none is invented.
    "frame": ("🖼️ Molduras", None, "🪟 Outras Molduras", "← Molduras"),
}
_CATEGORY_NAMES = {key: label.split(" ", 1)[1] for key, label in ACHIEVEMENT_CATEGORIES}
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


def _origin(cosmetic_id: str) -> str | None:
    """Short origin shown to the player; None when the Source defines none."""
    definition = COSMETICS_BY_ID[cosmetic_id]
    if definition.origin_label:
        return definition.origin_label
    achievement = ACHIEVEMENT_BY_ID.get(definition.achievement_id)
    return _CATEGORY_NAMES.get(achievement.category) if achievement else None


def _entry(name: str, origin: str | None) -> str:
    return f"{name} · {origin}" if origin else name


def render_cosmetics_root(view: CosmeticsView) -> Screen:
    rows = [[_button(str(index + 1), f"cos:c:{index}")] for index in range(len(COSMETIC_TYPES))]
    rows.append([_button("← Personagem", "character:root")])
    entries = "\n".join(
        f"{index + 1} {COSMETIC_TYPE_LABELS[kind]}" for index, kind in enumerate(COSMETIC_TYPES)
    )
    return Screen(f"🎨 Cosméticos\n\n{ROOT_INTRO}\n\n{entries}", "character", _markup(rows))


def render_cosmetic_category(category: CosmeticCategoryView) -> Screen:
    kind = category.cosmetic_type
    header, intro, others, _ = CATEGORY_HEADERS[kind]
    emoji = CATEGORY_EMOJI[kind]
    lines = [header, ""]
    if intro:
        lines.extend([intro, ""])
    rows = []
    entries: list[tuple[str, str]] = []  # (text, callback)
    if kind == "appearance":
        if category.uses_initial_appearance:
            lines.extend([DEFAULT_APPEARANCE_NAME, ""])
        else:
            entries.append((DEFAULT_APPEARANCE_NAME, f"cos:d:{DEFAULT_CODE}"))
    if category.selected is not None:
        lines.extend([_entry(category.selected.name, _origin(category.selected.cosmetic_id)), ""])
    for item in category.items:
        entries.append(
            (
                _entry(item.name, _origin(item.cosmetic_id)),
                f"cos:d:{COSMETIC_INDEX[item.cosmetic_id]}",
            )
        )
    if entries:
        lines.append(others)
        lines.append("")
        for index, (text, callback) in enumerate(entries, 1):
            lines.append(f"{index} {emoji} {text}")
            rows.append([_button(str(index), callback)])
    elif category.selected is None and kind != "appearance":
        lines.append("Nenhum item desta categoria foi adquirido.")
    rows.append([_button("← Cosméticos", "cos:r")])
    return Screen("\n".join(lines).rstrip(), "character", _markup(rows))


def render_cosmetic_default_appearance(view: CosmeticsView) -> Screen:
    category = next(item for item in view.categories if item.cosmetic_type == "appearance")
    rows = []
    if category.selected is not None:
        token = _selected_token(category.selected.cosmetic_id)
        rows.append([_button(COSMETIC_USE_BUTTONS["appearance"], f"cos:u:{DEFAULT_CODE}:{token}")])
    rows.append([_button(CATEGORY_HEADERS["appearance"][3], "cos:c:0")])
    return Screen(f"🧍 {DEFAULT_APPEARANCE_NAME}", "character", _markup(rows))


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
    kind = definition.cosmetic_type
    text = f"{CATEGORY_EMOJI[kind]} {_entry(definition.name, _origin(definition.cosmetic_id))}"
    selected_id = category.selected.cosmetic_id if category.selected else None
    rows = []
    if selected_id != definition.cosmetic_id:
        rows.append(
            [
                _button(
                    COSMETIC_USE_BUTTONS[kind],
                    f"cos:u:{item_index}:{_selected_token(selected_id)}",
                )
            ]
        )
    rows.append([_button(CATEGORY_HEADERS[kind][3], f"cos:c:{TYPE_CODES[kind]}")])
    return Screen(text, "character", _markup(rows))


def _selected_token(cosmetic_id: str | None) -> str:
    return "0" if cosmetic_id is None else str(COSMETIC_INDEX[cosmetic_id] + 1)
