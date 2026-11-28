"""Telas de Doutrinas (especificação consolidada 2026-11-26, Parte II).

Doutrinas são builds salvas: Equipamentos, Artes Ativas e Talentos. Caminho não faz
parte da interface nesta versão (§10) e o termo "Slot" não aparece (§4). Tudo o que
é exibido vem dos dados salvos da Doutrina; nada aqui é exemplo fixo.
"""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.bot.character_progression_ui import _art_emoji
from asterion.bot.creation_ui import Screen
from asterion.bot.item_lines import rarity_emoji, stat_line
from asterion.bot.ui_format import (
    BACK_LABEL,
    blocks,
    first_word,
    keycap,
    mono,
    narrative,
    page_bounds,
    page_nav,
    pairs,
)
from asterion.bot.ui_format import (
    title as bold,
)
from asterion.domain.arts import ACTIVE_ART_IDS_BY_CLASS, active_art_definition
from asterion.domain.class_trials import class_player_actions
from asterion.domain.equipment import assignment_for_item_slot
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TALENTS_BY_CLASS,
    talent_points_at_level,
)

REASON_LABELS = {
    "wrong_path": "Configuração incompatível",
    "trial_required": "Requer Provação concluída",
    "invalid_equipment": "Equipamentos incompatíveis",
    "item_unavailable": "Item indisponível",
    "invalid_art": "Arte incompatível",
    "weapon_requirement": "Arma incompatível com uma Arte da Doutrina",
    "duplicate_art": "Arte repetida",
    "talent_points": "Pontos de Talento insuficientes",
    "invalid_talents": "Talentos incompatíveis",
    "foreground": "Configuração bloqueada durante atividade",
    "safe_location_required": "Requer Refúgio do Ocaso",
    "insufficient_crowns": "Coroas insuficientes",
    "path_cannot_be_cleared": "Configuração incompatível",
    "weapon_unmapped": "Arma sem identidade registrada",
    "weapon_not_trained": "Requer Proficiência de uma arma",
    "weapon_class_forbidden": "Arma não permitida para a Classe",
}

ROOT_TITLE = "🗂️ Doutrinas"
ROOT_TEXT = (
    "Crie e mantenha diferentes configurações para usar em diferentes situações. Cada "
    "Doutrina reúne seus Equipamentos, Artes e Talentos em uma única build."
)
DETAIL_TEXT = (
    "Esta Doutrina reúne uma configuração independente para seu personagem. Edite os "
    "componentes da build e ative-a quando quiser utilizá-la."
)
ACTIVE_MARK, INACTIVE_MARK = "✅", "⛔️"
MIN_TALENT_LINES = 3
EDIT_TITLE = "✏️ Editar Doutrina"
EDIT_TEXT = (
    "Escolha qual parte da configuração deseja editar. As alterações serão salvas nesta Doutrina."
)
ARTS_TITLE = "🧿 Artes da Doutrina"
ARTS_TEXT = "Escolha quais Artes Ativas farão parte desta build."
TALENTS_TITLE = "🌿 Talentos da Doutrina"
TALENTS_TEXT = "Escolha como os Pontos de Talento serão distribuídos nesta build."
TALENT_LEVELS = (5, 15, 25, 35, 45, 55)
TALENT_LEVELS_PER_PAGE = 3
TALENT_LOCKED, TALENT_AVAILABLE, TALENT_ACQUIRED = "🔒", "✨", "✅"
EQUIPMENT_SLOTS = (
    ("Principal", "✋"),
    ("Secundária", "🤚"),
    ("Cabeça", "🪖"),
    ("Torso", "🥋"),
    ("Mãos", "🧤"),
    ("Pés", "🥾"),
    ("Acessório", "💍"),
    ("Artefato", "🔮"),
)
EQUIPMENT_SLOT_LABELS = tuple(label for label, _ in EQUIPMENT_SLOTS)
ART_CHOICES_PER_PAGE = 4
EMPTY = "Vazio"


def b36(value: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, digit = divmod(value, 36)
        result = chars[digit] + result
    return result


def _btn(text: str, callback: str) -> InlineKeyboardButton:
    if len(callback.encode("utf-8")) > 64:
        raise ValueError("Telegram callback exceeds 64 bytes")
    return InlineKeyboardButton(text=text, callback_data=callback)


def _markup(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row])


def _screen(*parts: str | None, rows) -> Screen:
    return Screen(blocks(*parts), "character", _markup(*rows), parse_mode="HTML")


def _keys(view: DoctrineCollectionView, doctrine: DoctrineView) -> str:
    """``<id>:<revisão>:<versão da configuração>`` usado pelos callbacks de edição."""
    return f"{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}"


def art_name(view: DoctrineCollectionView, art_id: str) -> str:
    definition = active_art_definition(art_id)
    selected_path = definition.path_id if definition is not None else view.selected_path
    try:
        action = class_player_actions(view.character_class, (art_id,), selected_path).get(art_id)
    except ValueError:
        action = None
    if action is not None:
        return action.name
    return art_id.rsplit(".", 1)[-1].replace("_", " ").title()


def in_use_doctrine(view: DoctrineCollectionView) -> DoctrineView | None:
    """A Doutrina Ativada: a registrada no banco (no máximo uma por personagem)."""
    return next((item for item in view.doctrines if item.is_active), None)


def render_doctrine_root(view: DoctrineCollectionView) -> Screen:
    lines = []
    buttons = []
    for position, item in enumerate(view.doctrines, start=1):
        mark = ACTIVE_MARK if item.is_active else INACTIVE_MARK
        suffix = f" · {mono('Ativada')}" if item.is_active else ""
        lines.append(f"#{position} {mark} {bold(item.name)}{suffix}")
        buttons.append(_btn(keycap(position), f"doc:d:{item.doctrine_id.hex}:{b36(item.revision)}"))
    return _screen(
        bold(ROOT_TITLE),
        narrative(ROOT_TEXT),
        f"{bold('📜 Lista de Doutrinas')}\n\n" + "\n".join(lines) if lines else None,
        rows=[buttons, [_btn(BACK_LABEL, "character:root")]],
    )


def _equipment_lines(doctrine: DoctrineView) -> str:
    """Mesmo molde da tela de Equipamentos: peça com raridade e atributos, ou ``Vazio``."""
    saved = doctrine.configuration["equipment"]
    details = {line.slot: line for line in doctrine.equipment_lines}
    blocks_ = []
    for label, emoji in EQUIPMENT_SLOTS:
        head = f"{emoji} {bold(label)} · "
        if label not in saved:
            blocks_.append(head + EMPTY)
            continue
        line = details.get(label)
        if line is None or not line.name:
            blocks_.append(head + "Indisponível")
            continue
        text = [f"{head}{rarity_emoji(line.rarity)} {escape(line.name)}"]
        if attributes := stat_line(line.contribution):
            text.append(attributes)
        blocks_.append("\n".join(text))
    return "\n\n".join(blocks_)


def art_label(view: DoctrineCollectionView, art_id: str) -> str:
    """``🗡️ Golpe de Guarda``: emoji próprio da Arte e o nome."""
    definition = active_art_definition(art_id)
    selected_path = definition.path_id if definition is not None else view.selected_path
    try:
        action = class_player_actions(view.character_class, (art_id,), selected_path).get(art_id)
    except ValueError:
        action = None
    emoji = _art_emoji(action) if action is not None else "⚔️"
    return f"{emoji} {escape(art_name(view, art_id))}"


def _art_lines(view: DoctrineCollectionView, doctrine: DoctrineView) -> str:
    arts = doctrine.configuration["arts"]
    return "\n".join(
        art_label(view, arts[str(slot)]) if str(slot) in arts else f"⛔️ {EMPTY}"
        for slot in (1, 2, 3)
    )


def _talent_lines(doctrine: DoctrineView) -> str:
    """Distribuição completa salva (até 12 no Nv.60); com menos de 3, completa com Vazio."""
    talents = sorted(doctrine.configuration["talents"], key=lambda item: item["point_slot"])
    lines = []
    for item in talents:
        definition = TALENT_DEFINITIONS.get(item["talent_id"])
        lines.append(f"🌿 {escape(definition.name if definition else 'Indisponível')}")
    lines.extend(f"⛔️ {EMPTY}" for _ in range(max(0, MIN_TALENT_LINES - len(lines))))
    return "\n".join(lines)


def _doctrine_page(
    view: DoctrineCollectionView, doctrine: DoctrineView, page: int, *, editing: bool
) -> list[str]:
    status = (
        f"{ACTIVE_MARK} {bold('Status')} · {mono('Ativada')}"
        if doctrine.is_active
        else f"{INACTIVE_MARK} {bold('Status')} · {mono('Inativa')}"
    )
    header = [f"📄 {bold('Página')} · {mono(f'{page}/2')}"]
    if not editing:
        header.insert(0, status)
    if page == 1:
        body = [
            f"🛡️ {bold('Equipamentos')}\n\n{_equipment_lines(doctrine)}",
            f"🧿 {bold('Artes')}\n\n{_art_lines(view, doctrine)}",
        ]
    else:
        body = [f"🌳 {bold('Talentos')}\n\n{_talent_lines(doctrine)}"]
    return ["\n".join(header), *body]


def render_doctrine_detail(
    view: DoctrineCollectionView, doctrine: DoctrineView, page: int = 1
) -> Screen:
    """Doutrina em duas páginas: Equipamentos e Artes; depois Talentos."""
    keys = _keys(view, doctrine)
    identity = f"{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}"
    page = 2 if page == 2 else 1
    edit = _btn("✏️ Editar", f"doc:ed:{keys}")
    activate = [] if doctrine.is_active else [_btn("✅ Ativar", f"doc:u:{keys}")]
    if page == 1:
        nav = _btn("▶️ Próxima", f"doc:dq:{identity}")
    else:
        nav = _btn("◀️ Anterior", f"doc:d:{identity}")
    first = [*activate, edit]
    rows = [first, [nav]] if not doctrine.is_active else [[edit, nav]]
    return _screen(
        bold(f"🗂️ {doctrine.name}"),
        narrative(DETAIL_TEXT),
        *_doctrine_page(view, doctrine, page, editing=False),
        rows=[*rows, [_btn(BACK_LABEL, "doc:r")]],
    )


def render_editor(view: DoctrineCollectionView, doctrine: DoctrineView, page: int = 1) -> Screen:
    keys = _keys(view, doctrine)
    page = 2 if page == 2 else 1
    nav = _btn("▶️ Próxima", f"doc:e2:{keys}") if page == 1 else _btn("◀️ Anterior", f"doc:ed:{keys}")
    return _screen(
        bold(f"✏️ Editar {doctrine.name}"),
        narrative(EDIT_TEXT),
        *_doctrine_page(view, doctrine, page, editing=True),
        rows=[
            [_btn("🛡️ Equipamentos", f"doc:es:{keys}"), _btn("🧿 Artes", f"doc:as:{keys}")],
            [_btn("🌳 Talentos", f"doc:ts:{keys}:0"), nav],
            [_btn(BACK_LABEL, f"doc:d:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}")],
        ],
    )


def render_equipment_slots(view: DoctrineCollectionView, doctrine: DoctrineView) -> Screen:
    keys = _keys(view, doctrine)
    buttons = [
        _btn(f"{emoji} {label}", f"doc:eq:{keys}:{index}")
        for index, (label, emoji) in enumerate(EQUIPMENT_SLOTS)
    ]
    return _screen(
        bold("🛡️ Equipamentos da Doutrina"),
        _equipment_lines(doctrine),
        rows=[*pairs(buttons), [_btn(BACK_LABEL, f"doc:ed:{keys}")]],
    )


def equipment_candidates(candidates, slot_index: int) -> list[tuple]:
    """Equipamentos do personagem que cabem na posição escolhida, na ordem do serviço."""
    slot = EQUIPMENT_SLOT_LABELS[slot_index]
    result = []
    for item in candidates:
        assignment = assignment_for_item_slot(item[2])
        if assignment and assignment.slot.value == slot:
            result.append(item)
    return result


def render_equipment_choices(view, doctrine, slot_index: int, candidates) -> Screen:
    keys = _keys(view, doctrine)
    label, emoji = EQUIPMENT_SLOTS[slot_index]
    compatible = equipment_candidates(candidates, slot_index)
    lines = [f"{emoji} {mono(name)}" for _, name, _, _ in compatible]
    buttons = [
        _btn(f"{emoji} {first_word(name)}", f"doc:ei:{keys}:{slot_index}:{b36(index)}")
        for index, (_, name, _, _) in enumerate(compatible)
    ]
    current = label in doctrine.configuration["equipment"]
    return _screen(
        f"{emoji} {bold(label)}",
        "\n".join(lines) if lines else None,
        rows=[
            *pairs(buttons),
            [_btn("❌ Desequipar", f"doc:ei:{keys}:{slot_index}:x")] if current else [],
            [_btn(BACK_LABEL, f"doc:es:{keys}")],
        ],
    )


def doctrine_art_ids(view, doctrine) -> tuple[str, ...]:
    """Artes implementadas e liberadas pelo nível que esta Doutrina pode usar."""
    selected_path = doctrine.configuration.get("path")
    return tuple(
        art_id
        for art_id in ACTIVE_ART_IDS_BY_CLASS[view.character_class]
        if (definition := active_art_definition(art_id)) is not None
        and view.level >= definition.min_level
        and (definition.path_id is None or definition.path_id == selected_path)
    )


def render_art_slots(view: DoctrineCollectionView, doctrine: DoctrineView) -> Screen:
    keys = _keys(view, doctrine)
    return _screen(
        bold(ARTS_TITLE),
        narrative(ARTS_TEXT),
        f"✨ {bold('Artes Ativas')}\n\n{_art_lines(view, doctrine)}",
        rows=[
            *([_btn(f"⚔️ Arte {slot}", f"doc:al:{keys}:{slot}:0")] for slot in (1, 2, 3)),
            [_btn(BACK_LABEL, f"doc:ed:{keys}")],
        ],
    )


def render_art_choices(view, doctrine, slot: int, page: int = 0) -> Screen:
    keys = _keys(view, doctrine)
    arts = doctrine_art_ids(view, doctrine)
    page, pages, start = page_bounds(len(arts), page, ART_CHOICES_PER_PAGE)
    shown = list(enumerate(arts))[start : start + ART_CHOICES_PER_PAGE]
    lines = [f"⚔️ {mono(art_name(view, art_id))}" for _, art_id in shown]
    buttons = [
        _btn(f"⚔️ {first_word(art_name(view, art_id))}", f"doc:ai:{keys}:{slot}:{b36(index)}")
        for index, art_id in shown
    ]
    current = str(slot) in doctrine.configuration["arts"]
    return _screen(
        bold(f"🧿 Arte {slot}"),
        "\n".join(lines) if lines else None,
        rows=[
            *pairs(buttons),
            page_nav(page, pages, lambda target: f"doc:al:{keys}:{slot}:{target}"),
            [_btn("❌ Remover", f"doc:ai:{keys}:{slot}:x")] if current else [],
            [_btn(BACK_LABEL, f"doc:as:{keys}")],
        ],
    )


def talent_state(view: DoctrineCollectionView, doctrine: DoctrineView, talent) -> str:
    """🔒 requisito não atendido · ✨ disponível para aquisição · ✅ adquirido (§5)."""
    chosen = {item["talent_id"] for item in doctrine.configuration["talents"]}
    if talent.talent_id in chosen:
        return TALENT_ACQUIRED
    if talent.level not in IMPLEMENTED_TALENT_LEVELS or talent.level > view.level:
        return TALENT_LOCKED
    return TALENT_AVAILABLE


def available_talent_points(view: DoctrineCollectionView, doctrine: DoctrineView) -> int:
    return max(0, talent_points_at_level(view.level) - len(doctrine.configuration["talents"]))


def render_talent_page(view: DoctrineCollectionView, doctrine: DoctrineView, page: int) -> Screen:
    keys = _keys(view, doctrine)
    pages = -(-len(TALENT_LEVELS) // TALENT_LEVELS_PER_PAGE)
    page = min(max(page, 0), pages - 1)
    levels = TALENT_LEVELS[page * TALENT_LEVELS_PER_PAGE : (page + 1) * TALENT_LEVELS_PER_PAGE]
    talents = TALENTS_BY_CLASS[view.character_class]
    sections = []
    buttons = []
    for level in levels:
        lines = [f"📜 {bold(f'Requer Nv. {level}')}", ""]
        for index, talent in enumerate(talents):
            if talent.level != level:
                continue
            state = talent_state(view, doctrine, talent)
            lines.append(f"{state} {mono(talent.name)}")
            if state != TALENT_LOCKED:
                buttons.append(
                    _btn(f"{state} {first_word(talent.name)}", f"doc:tt:{keys}:{b36(index)}")
                )
        sections.append("\n".join(lines))
    navigation = []
    if page > 0:
        navigation.append([_btn("◀️ Anterior", f"doc:ts:{keys}:{page - 1}")])
    if page < pages - 1:
        navigation.append([_btn("▶️ Próxima", f"doc:ts:{keys}:{page + 1}")])
    return _screen(
        bold(TALENTS_TITLE),
        narrative(TALENTS_TEXT),
        f"🎋 {bold('Pontos Disponíveis')} · {mono(str(available_talent_points(view, doctrine)))}",
        *sections,
        rows=[*pairs(buttons), *navigation, [_btn(BACK_LABEL, f"doc:ed:{keys}")]],
    )
