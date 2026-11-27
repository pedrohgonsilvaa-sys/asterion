"""Telas de Doutrinas (especificação consolidada 2026-11-26, Parte II).

Doutrinas são builds salvas: Equipamentos, Artes Ativas e Talentos. Caminho não faz
parte da interface nesta versão (§10) e o termo "Slot" não aparece (§4). Tudo o que
é exibido vem dos dados salvos da Doutrina; nada aqui é exemplo fixo.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.bot.creation_ui import Screen
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
    "Crie e salve diferentes configurações para usar em diferentes situações. Cada "
    "Doutrina reúne seus Equipamentos, Artes e Talentos em uma única build."
)
ROOT_NOTICE = (
    "⚠️ Pode criar diferentes Doutrinas para adaptar a cada desafio. Apenas uma "
    "Doutrina pode estar em uso por vez."
)
IN_USE, OTHER = "🟢", "🔴"
CONFIG_TITLE = "⚙️ Configuração"
CONFIG_TEXT = (
    "Esta Doutrina reúne a configuração que será usada pelo personagem. Edite "
    "Equipamentos, Artes e Talentos para montar esta build."
)
EDIT_TITLE = "✏️ Editar Doutrina"
EDIT_TEXT = (
    "Edite os elementos que fazem parte desta build. Você pode alterar o nome, definir "
    "os Equipamentos, selecionar as Artes e ajustar os Talentos."
)
NAME_TITLE = "✏️ Nome da Doutrina"
NAME_TEXT = (
    "O nome identifica esta build entre suas Doutrinas salvas. Escolha um nome que "
    "ajude a reconhecer rapidamente o estilo de configuração."
)
NAME_PROMPT = "✏️ Envie o novo nome da Doutrina."
ARTS_TITLE = "🧿 Artes da Doutrina"
ARTS_TEXT = "Escolha quais Artes Ativas farão parte desta build."
TALENTS_TITLE = "🌿 Talentos da Doutrina"
TALENTS_TEXT = "Escolha como os Pontos de Talento serão distribuídos nesta build."
TALENT_LEVELS = (5, 15, 25, 35, 45, 55)
TALENT_LEVELS_PER_PAGE = 3
TALENT_LOCKED, TALENT_AVAILABLE, TALENT_ACQUIRED = "🔒", "✨", "✅"
EQUIPMENT_SLOTS = (
    ("Principal", "⚔️"),
    ("Secundária", "⚔️"),
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
    return (
        f"{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:"
        f"{b36(view.configuration_version)}"
    )


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
    """A Doutrina em uso: a primeira cuja build salva é a configuração atual.

    Apenas uma Doutrina pode estar em uso por vez (§1), mesmo se duas guardarem a
    mesma build.
    """
    return next((item for item in view.doctrines if item.is_current), None)


def render_doctrine_root(view: DoctrineCollectionView) -> Screen:
    current = in_use_doctrine(view)
    cells = [
        (IN_USE if current is not None and item.doctrine_id == current.doctrine_id else OTHER, item)
        for item in view.doctrines
    ]
    listing = None
    if cells:
        # Duas colunas de largura fixa e igual: o nome da coluna esquerda ocupa sempre a
        # largura do maior nome da lista, em monoespaçado (§2, layout simétrico).
        width = max(len(item.name) for _, item in cells)
        lines = []
        for offset in range(0, len(cells), 2):
            left_mark, left = cells[offset]
            line = f"{left_mark} {mono(left.name.ljust(width))}"
            if offset + 1 < len(cells):
                right_mark, right = cells[offset + 1]
                line += f"  {right_mark} {mono(right.name.ljust(width))}"
            lines.append(line)
        listing = "\n".join(lines)
    buttons = [
        _btn(f"{mark} {item.name}", f"doc:d:{item.doctrine_id.hex}:{b36(item.revision)}")
        for mark, item in cells
    ]
    create = (
        [_btn("➕ Criar", f"doc:n:{b36(view.configuration_version)}")]
        if len(view.doctrines) < view.limit
        else []
    )
    return _screen(
        bold(ROOT_TITLE),
        narrative(ROOT_TEXT),
        listing,
        ROOT_NOTICE,
        rows=[*pairs(buttons), create, [_btn(BACK_LABEL, "character:root")]],
    )


def _equipment_lines(doctrine: DoctrineView) -> str:
    saved = doctrine.configuration["equipment"]
    names = dict(doctrine.equipment_names)
    lines = []
    for label, emoji in EQUIPMENT_SLOTS:
        if label in saved:
            value = names.get(label) or "Indisponível"
        else:
            value = EMPTY
        lines.append(f"{emoji} {bold(label)} · {mono(value)}")
    return "\n".join(lines)


def _art_lines(view: DoctrineCollectionView, doctrine: DoctrineView) -> str:
    arts = doctrine.configuration["arts"]
    return "\n".join(
        f"{keycap(slot)} {mono(art_name(view, arts[str(slot)]) if str(slot) in arts else EMPTY)}"
        for slot in (1, 2, 3)
    )


def _talent_lines(doctrine: DoctrineView) -> str:
    """Só os Talentos distribuídos nesta Doutrina, todos na própria tela (§3)."""
    talents = sorted(doctrine.configuration["talents"], key=lambda item: item["point_slot"])
    if not talents:
        return mono(EMPTY)
    lines = []
    for position, item in enumerate(talents, start=1):
        definition = TALENT_DEFINITIONS.get(item["talent_id"])
        name = definition.name if definition else "Indisponível"
        lines.append(f"{keycap(position)} {mono(name)}")
    return "\n".join(lines)


def render_doctrine_detail(view: DoctrineCollectionView, doctrine: DoctrineView) -> Screen:
    """Configuração da Doutrina, aberta direto ao selecioná-la (§3 e §9)."""
    keys = _keys(view, doctrine)
    return _screen(
        bold(CONFIG_TITLE),
        narrative(CONFIG_TEXT),
        f"🛡️ {bold('Equipamentos')}\n\n{_equipment_lines(doctrine)}",
        f"🧿 {bold('Artes')}\n\n{_art_lines(view, doctrine)}",
        f"🌿 {bold('Talentos')}\n\n{_talent_lines(doctrine)}",
        rows=[
            [_btn("✅ Usar", f"doc:u:{keys}"), _btn("✏️ Editar", f"doc:ed:{keys}")],
            [_btn("🗑️ Excluir", f"doc:x:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}")],
            [_btn(BACK_LABEL, "doc:r")],
        ],
    )


def render_apply_preview(view: DoctrineCollectionView, doctrine: DoctrineView, cost: int) -> Screen:
    """Confirmação só quando usar a Doutrina custa Coroas (decisão do autor 2026-11-27)."""
    keys = _keys(view, doctrine)
    return _screen(
        bold("✅ Usar Doutrina"),
        f"🗂️ {bold('Doutrina')} · {mono(doctrine.name)}\n"
        f"🪙 {bold('Custo')} · {mono(f'{cost:,} Coroas'.replace(',', '.'))}",
        rows=[
            [_btn("✅ Confirmar", f"doc:ok:{keys}")],
            [_btn(BACK_LABEL, f"doc:d:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}")],
        ],
    )


def render_editor(view: DoctrineCollectionView, doctrine: DoctrineView) -> Screen:
    keys = _keys(view, doctrine)
    return _screen(
        bold(EDIT_TITLE),
        narrative(EDIT_TEXT),
        rows=[
            [_btn("✏️ Nome", f"doc:nm:{keys}"), _btn("🛡️ Equipamentos", f"doc:es:{keys}")],
            [_btn("🧿 Artes", f"doc:as:{keys}"), _btn("🌿 Talentos", f"doc:ts:{keys}:0")],
            [_btn(BACK_LABEL, f"doc:d:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}")],
        ],
    )


def render_name_prompt(back_callback: str, notice: str | None = None) -> Screen:
    """Pedido de nome na própria tela (§7): sem confirmação adicional."""
    return _screen(
        bold(NAME_TITLE),
        narrative(NAME_TEXT),
        notice,
        NAME_PROMPT,
        rows=[[_btn(BACK_LABEL, back_callback)]],
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
