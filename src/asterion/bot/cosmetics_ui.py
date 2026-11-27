"""Telas de Cosméticos (especificação consolidada 2026-11-26, Parte IV §2–§5).

Aparência, Títulos e Molduras. Cada item abre primeiro a tela de detalhes, com
``✨ Raridade`` e ``🌐 Origem`` quando a Fonte os define, e a ação ``✅ Usar``.
O personagem começa sem Moldura: não existe Moldura Padrão.
"""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.cosmetic_catalog import (
    COSMETIC_TYPES,
    COSMETIC_USE_BUTTONS,
    COSMETICS_BY_ID,
    INITIAL_APPEARANCE,
    INITIAL_TITLE,
    InitialCosmetic,
)
from asterion.application.cosmetics import CosmeticCategoryView, CosmeticsView
from asterion.application.knowledge_catalog import ACHIEVEMENT_BY_ID, ACHIEVEMENT_CATEGORIES
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import BACK_LABEL, first_word, page_bounds, page_nav, pairs

TYPE_CODES = {kind: str(index) for index, kind in enumerate(COSMETIC_TYPES)}
TYPE_BY_CODE = {value: key for key, value in TYPE_CODES.items()}
# Aparência inicial e Título inicial: valem quando nada está selecionado.
DEFAULT_CODE = "x"
INITIAL_TITLE_CODE = "t"
DEFAULT_CODES = {DEFAULT_CODE: "appearance", INITIAL_TITLE_CODE: "title"}
ITEMS_PER_PAGE = 4
ROOT_TITLE = "🎨 Cosméticos"
ROOT_INTRO = (
    "Escolha como o personagem se apresenta em Asterion e quais marcas da jornada deseja "
    "carregar consigo."
)
INITIAL_APPEARANCE_EMOJI = "🌒"
CATEGORY_EMOJI = {"appearance": "👘", "title": "🎖️", "frame": "🖼️"}
# (título, texto da tela)
CATEGORY_HEADERS = {
    "appearance": (
        "👘 Aparência",
        "As marcas de uma jornada também vivem na forma como ela é lembrada. Escolha o "
        "visual que acompanhará o personagem pelos caminhos de Asterion.",
    ),
    "title": (
        "🎖️ Títulos",
        "Alguns nomes são recebidos ao nascer. Outros precisam ser conquistados. Escolha "
        "qual marca de sua jornada acompanhará seu nome por Asterion.",
    ),
    "frame": (
        "🖼️ Molduras",
        "Uma moldura acompanha seu perfil e dá forma à maneira como outros aventureiros "
        "enxergam sua jornada.",
    ),
}
FRAMES_EMPTY = "Você ainda não possui nenhuma moldura."
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


def _screen(*parts: str | None, rows) -> Screen:
    return Screen(
        "\n\n".join(part for part in parts if part),
        "character",
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def _bold(text: str) -> str:
    return f"<b>{escape(text)}</b>"


def _italic(text: str) -> str:
    return f"<i>{escape(text)}</i>"


def _origin(cosmetic_id: str) -> str | None:
    """Origem curta mostrada ao jogador; ``None`` quando a Fonte não define nenhuma."""
    definition = COSMETICS_BY_ID[cosmetic_id]
    if definition.origin_label:
        return definition.origin_label
    achievement = ACHIEVEMENT_BY_ID.get(definition.achievement_id)
    return _CATEGORY_NAMES.get(achievement.category) if achievement else None


def _category(view: CosmeticsView, kind: str) -> CosmeticCategoryView:
    return next(item for item in view.categories if item.cosmetic_type == kind)


def _owned(category: CosmeticCategoryView) -> list:
    """Itens adquiridos na ordem do catálogo, o selecionado incluído."""
    items = [*category.items, *([category.selected] if category.selected else [])]
    return sorted(items, key=lambda item: COSMETIC_INDEX[item.cosmetic_id])


def _initial_title(view: CosmeticsView) -> str:
    return view.initial_title or INITIAL_TITLE.name


def _entries(view: CosmeticsView, kind: str) -> list[tuple[str, str, str]]:
    """(emoji, nome, código do detalhe) de cada item da categoria."""
    entries = []
    if kind == "appearance":
        entries.append((INITIAL_APPEARANCE_EMOJI, INITIAL_APPEARANCE.name, DEFAULT_CODE))
    elif kind == "title":
        entries.append((CATEGORY_EMOJI["title"], _initial_title(view), INITIAL_TITLE_CODE))
    entries.extend(
        (CATEGORY_EMOJI[kind], item.name, str(COSMETIC_INDEX[item.cosmetic_id]))
        for item in _owned(_category(view, kind))
    )
    return entries


def render_cosmetics_root(view: CosmeticsView) -> Screen:
    return _screen(
        _bold(ROOT_TITLE),
        _italic(ROOT_INTRO),
        rows=[
            [_button("👘 Aparência", "cos:c:0"), _button("🎖️ Títulos", "cos:c:1")],
            [_button("🖼️ Molduras", "cos:c:2")],
            [_button(BACK_LABEL, "character:root")],
        ],
    )


def render_cosmetic_category(
    category: CosmeticCategoryView, view: CosmeticsView | None = None, page: int = 0
) -> Screen:
    kind = category.cosmetic_type
    if view is None:
        view = CosmeticsView("", (category,))
    title, intro = CATEGORY_HEADERS[kind]
    entries = _entries(view, kind)
    page, pages, start = page_bounds(len(entries), page, ITEMS_PER_PAGE)
    shown = entries[start : start + ITEMS_PER_PAGE]
    if shown:
        listing = "\n".join(f"{emoji} <code>{escape(name)}</code>" for emoji, name, _ in shown)
    else:
        # Sem Moldura conquistada: só o estado vazio, sem botão de seleção (§5).
        listing = _italic(FRAMES_EMPTY) if kind == "frame" else None
    buttons = [
        _button(f"{emoji} {first_word(name)}", f"cos:d:{code}") for emoji, name, code in shown
    ]
    code = TYPE_CODES[kind]
    return _screen(
        _bold(title),
        _italic(intro),
        listing,
        rows=[
            *pairs(buttons),
            page_nav(page, pages, lambda target: f"cos:c:{code}:{target}"),
            [_button(BACK_LABEL, "cos:r")],
        ],
    )


def _page_of(view: CosmeticsView, kind: str, code: str) -> int:
    codes = [entry[2] for entry in _entries(view, kind)]
    return codes.index(code) // ITEMS_PER_PAGE if code in codes else 0


def _detail(
    view: CosmeticsView,
    kind: str,
    code: str,
    name: str,
    *,
    description: str | None,
    rarity: str | None,
    origin: str | None,
    closing: str | None = None,
    use_callback: str,
) -> Screen:
    fields = []
    if rarity:
        fields.append(f"✨ <b>Raridade</b> · <code>{escape(rarity)}</code>")
    if origin:
        fields.append(f"🌐 <b>Origem</b> · <code>{escape(origin)}</code>")
    page = _page_of(view, kind, code)
    back = f"cos:c:{TYPE_CODES[kind]}" + (f":{page}" if page else "")
    return _screen(
        f"{CATEGORY_EMOJI[kind]} {_bold(name)}",
        _italic(description) if description else None,
        "\n".join(fields) if fields else None,
        _italic(closing) if closing else None,
        rows=[[_button(COSMETIC_USE_BUTTONS[kind], use_callback)], [_button(BACK_LABEL, back)]],
    )


def _initial_detail(view: CosmeticsView, code: str) -> Screen:
    kind = DEFAULT_CODES[code]
    initial: InitialCosmetic = INITIAL_APPEARANCE if kind == "appearance" else INITIAL_TITLE
    name = initial.name if kind == "appearance" else _initial_title(view)
    known = name == initial.name
    selected = _category(view, kind).selected
    return _detail(
        view,
        kind,
        code,
        name,
        description=initial.description if known else None,
        rarity=initial.rarity if known else None,
        origin=initial.origin if known else None,
        closing=initial.closing if known else None,
        use_callback=f"cos:u:{code}:{_selected_token(selected.cosmetic_id if selected else None)}",
    )


def render_cosmetic_default_appearance(view: CosmeticsView) -> Screen:
    return _initial_detail(view, DEFAULT_CODE)


def render_cosmetic_initial(view: CosmeticsView, code: str) -> Screen:
    return _initial_detail(view, code)


def render_cosmetic_detail(view: CosmeticsView, item_index: int) -> Screen:
    from asterion.application.cosmetic_catalog import COSMETICS

    if not 0 <= item_index < len(COSMETICS):
        return render_cosmetics_root(view)
    definition = COSMETICS[item_index]
    kind = definition.cosmetic_type
    category = _category(view, kind)
    if definition.cosmetic_id not in {item.cosmetic_id for item in _owned(category)}:
        return render_cosmetic_category(category, view)
    selected_id = category.selected.cosmetic_id if category.selected else None
    return _detail(
        view,
        kind,
        str(item_index),
        definition.name,
        description=definition.description,
        rarity=definition.rarity,
        origin=_origin(definition.cosmetic_id),
        use_callback=f"cos:u:{item_index}:{_selected_token(selected_id)}",
    )


def _selected_token(cosmetic_id: str | None) -> str:
    return "0" if cosmetic_id is None else str(COSMETIC_INDEX[cosmetic_id] + 1)
