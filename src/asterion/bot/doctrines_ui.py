"""Telegram screens for saved character configurations."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.bot.creation_ui import Screen
from asterion.domain.arts import ACTIVE_ART_IDS_BY_CLASS, active_art_definition
from asterion.domain.class_trials import class_player_actions
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TALENTS_BY_CLASS,
    talent_points_at_level,
)

REASON_LABELS = {
    "wrong_path": "Caminho incompatível",
    "trial_required": "Requer Provação concluída",
    "invalid_equipment": "Equipamentos incompatíveis",
    "item_unavailable": "Item indisponível",
    "invalid_art": "Arte incompatível",
    "weapon_requirement": "Arma incompatível com uma Arte equipada",
    "duplicate_art": "Arte repetida",
    "talent_points": "Pontos de Talento insuficientes",
    "invalid_talents": "Talentos incompatíveis",
    "foreground": "Configuração bloqueada durante atividade",
    "safe_location_required": "Requer Refúgio do Ocaso",
    "insufficient_crowns": "Coroas insuficientes",
    "path_cannot_be_cleared": "Caminho não pode ser removido",
}


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


def _markup(rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _art_label(view, art_id: str, selected_path: str | None) -> str:
    try:
        action = class_player_actions(
            view.character_class, (art_id,), selected_path
        ).get(art_id)
    except ValueError:
        action = None
    if action is not None:
        return action.name
    return art_id.rsplit(".", 1)[-1].replace("_", " ").title()


def render_doctrine_root(view: DoctrineCollectionView) -> Screen:
    lines = ["🧩 Doutrinas", ""]
    rows = []
    current = next((item for item in view.doctrines if item.is_current), None)
    if current:
        path = PATH_DEFINITIONS.get(current.configuration.get("path"))
        lines.extend(
            [current.name, f"{path.name if path else 'Sem Caminho'} · Configuração Atual", ""]
        )
        rows.append(
            [_btn("Configuração Atual", f"doc:d:{current.doctrine_id.hex}:{b36(current.revision)}")]
        )
    others = [item for item in view.doctrines if not item.is_current]
    if others:
        lines.append("📚 Outras Doutrinas")
        for index, item in enumerate(others, 1):
            lines.append(f"{index} {item.name}")
            rows.append([_btn(str(index), f"doc:d:{item.doctrine_id.hex}:{b36(item.revision)}")])
    elif not current:
        lines.append("Nenhuma Doutrina foi salva.")
    if len(view.doctrines) < view.limit and not view.foreground:
        rows.append([_btn("Nova Doutrina", f"doc:n:{b36(view.configuration_version)}")])
    elif len(view.doctrines) >= view.limit:
        lines.extend(["", f"🔒 Limite de Doutrinas · {view.limit}/{view.limit}"])
    if view.foreground:
        lines.extend(["", "🔒 Configuração · Bloqueada durante atividade"])
    rows.append([_btn("← Personagem", "character:root")])
    return Screen("\n".join(lines), "character", _markup(rows))


def render_doctrine_detail(view: DoctrineCollectionView, doctrine: DoctrineView) -> Screen:
    config = doctrine.configuration
    path = PATH_DEFINITIONS.get(config.get("path"))
    lines = ["🧩 Doutrina", "", doctrine.name, f"Caminho · {path.name if path else 'Nenhum'}", ""]
    lines.append("🛡️ Equipamentos")
    names = dict(doctrine.equipment_names)
    if config["equipment"]:
        for slot, _item_id in config["equipment"].items():
            lines.append(f"• {slot} · {names.get(slot) or '⚠️ Item Indisponível'}")
    else:
        lines.append("• Nenhum")
    lines.extend(["", "🎴 Artes"])
    if config["arts"]:
        lines.extend(
            f"• Slot {slot} · {_art_label(view, art_id, config.get('path'))}"
            for slot, art_id in sorted(config["arts"].items())
        )
    else:
        lines.append("• Nenhuma")
    lines.extend(["", "🌿 Talentos"])
    if config["talents"]:
        for item in config["talents"]:
            definition = TALENT_DEFINITIONS.get(item["talent_id"])
            talent_name = definition.name if definition else "Indisponível"
            lines.append(f"• Ponto {item['point_slot']} · {talent_name}")
    else:
        lines.append("• Nenhum")
    if doctrine.incomplete_reason:
        lines.extend(
            [
                "",
                "⚠️ Doutrina Incompleta · "
                f"{REASON_LABELS.get(doctrine.incomplete_reason, 'Configuração incompatível')}",
            ]
        )
    elif doctrine.is_current:
        lines.extend(["", "Configuração Atual"])
    if view.foreground:
        lines.extend(["", "🔒 Configuração bloqueada durante atividade"])
    rev = b36(doctrine.revision)
    did = doctrine.doctrine_id.hex
    rows = []
    if doctrine.can_apply:
        rows.append(
            [_btn("Aplicar Doutrina", f"doc:ap:{did}:{rev}:{b36(view.configuration_version)}")]
        )
    if not view.foreground:
        rows.append(
            [
                _btn("Editar Doutrina", f"doc:ed:{did}:{rev}:{b36(view.configuration_version)}"),
                _btn(
                    "Usar Configuração Atual",
                    f"doc:ow:{did}:{rev}:{b36(view.configuration_version)}",
                ),
            ]
        )
        rows.append([_btn("Excluir Doutrina", f"doc:del:{did}:{rev}")])
    rows.append([_btn("← Doutrinas", "doc:r")])
    return Screen("\n".join(lines), "character", _markup(rows))


def render_apply_preview(view: DoctrineCollectionView, doctrine: DoctrineView, cost: int) -> Screen:
    lines = ["🧩 Aplicar Doutrina", "", doctrine.name, ""]
    if cost:
        lines.append(f"🪙 Custo · {cost:,} Coroas".replace(",", "."))
    else:
        lines.append("🪙 Custo · 0 Coroas")
    lines.extend(
        [
            "📍 Alterações de Caminho/Talentos seguem as regras normais.",
            "A configuração só será aplicada se continuar válida.",
        ]
    )
    callback = (
        f"doc:ok:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:"
        f"{b36(view.configuration_version)}"
    )
    return Screen(
        "\n".join(lines),
        "character",
        _markup(
            [
                [_btn("Confirmar Aplicação", callback)],
                [_btn("← Doutrina", f"doc:d:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}")],
            ]
        ),
    )


def render_overwrite_preview(doctrine: DoctrineView, config_version: int) -> Screen:
    return Screen(
        f"✏️ Usar Configuração Atual\n\nA configuração salva em “{doctrine.name}” será substituída.",
        "character",
        _markup(
            [
                [
                    _btn(
                        "Confirmar Atualização",
                        f"doc:owok:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(config_version)}",
                    )
                ],
                [_btn("← Doutrina", f"doc:d:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}")],
            ]
        ),
    )


def render_delete_confirmation(doctrine: DoctrineView) -> Screen:
    return Screen(
        f"🗑️ Excluir Doutrina\n\n{doctrine.name}\n\nEsta ação não pode ser desfeita.",
        "character",
        _markup(
            [
                [
                    _btn(
                        "Confirmar Exclusão",
                        f"doc:x:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}",
                    )
                ],
                [_btn("← Doutrina", f"doc:d:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}")],
            ]
        ),
    )


def render_editor(view: DoctrineCollectionView, doctrine: DoctrineView) -> Screen:
    did, rev, cfg = (
        doctrine.doctrine_id.hex,
        b36(doctrine.revision),
        b36(view.configuration_version),
    )
    return Screen(
        f"✏️ Editar Doutrina\n\n{doctrine.name}",
        "character",
        _markup(
            [
                [_btn("1 · Nome", f"doc:nm:{did}:{rev}:{cfg}")],
                [_btn("2 · Caminho", f"doc:ep:{did}:{rev}:{cfg}")],
                [_btn("3 · Equipamentos", f"doc:es:{did}:{rev}:{cfg}")],
                [_btn("4 · Artes", f"doc:as:{did}:{rev}:{cfg}")],
                [_btn("5 · Talentos", f"doc:ts:{did}:{rev}:{cfg}")],
                [_btn("← Doutrina", f"doc:d:{did}:{rev}")],
            ]
        ),
    )


def render_paths(view, doctrine, path_ids) -> Screen:
    rows = []
    labels = ["Sem Caminho"] + [PATH_DEFINITIONS[path_id].name for path_id in path_ids]
    for index, label in enumerate(labels):
        rows.append(
            [
                _btn(
                    str(index + 1) + " " + label,
                    f"doc:p:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}:{index}",
                )
            ]
        )
    rows.append(
        [
            _btn(
                "← Editar",
                f"doc:ed:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}",
            )
        ]
    )
    return Screen("🧭 Caminho da Doutrina", "character", _markup(rows))


def render_equipment_slots(view, doctrine) -> Screen:
    labels = ("Principal", "Secundária", "Cabeça", "Torso", "Mãos", "Pés", "Acessório", "Artefato")
    rows = [
        [
            _btn(
                str(index + 1) + " " + label,
                f"doc:eq:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}:{index}",
            )
        ]
        for index, label in enumerate(labels)
    ]
    rows.append(
        [
            _btn(
                "← Editar",
                f"doc:ed:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}",
            )
        ]
    )
    return Screen("🛡️ Equipamentos da Doutrina\n\nEscolha um slot.", "character", _markup(rows))


def render_equipment_choices(view, doctrine, slot_index: int, candidates) -> Screen:
    labels = ("Principal", "Secundária", "Cabeça", "Torso", "Mãos", "Pés", "Acessório", "Artefato")
    slot = labels[slot_index]
    lines = [f"🛡️ {slot}", ""]
    rows = []
    compatible = []
    for item_id, name, item_slot, level in candidates:
        from asterion.domain.equipment import assignment_for_item_slot

        assignment = assignment_for_item_slot(item_slot)
        if assignment and assignment.slot.value == slot:
            compatible.append((item_id, name, level))
    for index, (_, name, level) in enumerate(compatible):
        lines.append(f"{index + 1} {name} · Nv.{level}")
        rows.append(
            [
                _btn(
                    str(index + 1),
                    f"doc:ei:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}:{slot_index}:{index}",
                )
            ]
        )
    rows.append(
        [
            _btn(
                "Remover deste slot",
                f"doc:ei:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}:{slot_index}:x",
            )
        ]
    )
    rows.append(
        [
            _btn(
                "← Slots",
                f"doc:es:{doctrine.doctrine_id.hex}:{b36(doctrine.revision)}:{b36(view.configuration_version)}",
            )
        ]
    )
    return Screen("\n".join(lines), "character", _markup(rows))


def render_art_slots(view, doctrine) -> Screen:
    did, rev, cfg = (
        doctrine.doctrine_id.hex,
        b36(doctrine.revision),
        b36(view.configuration_version),
    )
    return Screen(
        "🎴 Artes da Doutrina\n\nEscolha um slot para editar.",
        "character",
        _markup(
            [[_btn(f"Slot {slot}", f"doc:al:{did}:{rev}:{cfg}:{slot}")] for slot in (1, 2, 3)]
            + [[_btn("← Editar", f"doc:ed:{did}:{rev}:{cfg}")]]
        ),
    )


def render_art_choices(view, doctrine, slot: int) -> Screen:
    arts = doctrine_art_ids(view, doctrine)
    did, rev, cfg = (
        doctrine.doctrine_id.hex,
        b36(doctrine.revision),
        b36(view.configuration_version),
    )
    rows = [
        [
            _btn(
                f"{index + 1} {_art_label(view, art_id, doctrine.configuration.get('path'))}",
                f"doc:ai:{did}:{rev}:{cfg}:{slot}:{index}",
            )
        ]
        for index, art_id in enumerate(arts)
        if (definition := active_art_definition(art_id))
        and view.level >= definition.min_level
    ]
    rows.append([_btn("Remover deste slot", f"doc:ai:{did}:{rev}:{cfg}:{slot}:x")])
    rows.append([_btn("← Slots", f"doc:as:{did}:{rev}:{cfg}")])
    return Screen("🎴 Escolha uma Arte disponível.", "character", _markup(rows))


def doctrine_art_ids(view, doctrine) -> tuple[str, ...]:
    """Return implemented Arts eligible for the Path saved in this draft."""
    selected_path = doctrine.configuration.get("path")
    return tuple(
        art_id
        for art_id in ACTIVE_ART_IDS_BY_CLASS[view.character_class]
        if (definition := active_art_definition(art_id)) is not None
        and view.level >= definition.min_level
        and (
            definition.path_id is None
            or definition.path_id == selected_path
        )
    )


def render_talent_slots(view, doctrine) -> Screen:
    did, rev, cfg = (
        doctrine.doctrine_id.hex,
        b36(doctrine.revision),
        b36(view.configuration_version),
    )
    points = talent_points_at_level(view.level)
    lines = ["🌿 Talentos da Doutrina", ""]
    rows = []
    for slot in range(1, points + 1):
        lines.append(f"{slot} · Escolher Talento")
        rows.append([_btn(str(slot), f"doc:tl:{did}:{rev}:{cfg}:{slot}")])
    rows.append([_btn("← Editar", f"doc:ed:{did}:{rev}:{cfg}")])
    return Screen("\n".join(lines), "character", _markup(rows))


def render_talent_choices(view, doctrine, point_slot: int) -> Screen:
    did, rev, cfg = (
        doctrine.doctrine_id.hex,
        b36(doctrine.revision),
        b36(view.configuration_version),
    )
    rows = []
    points = talent_points_at_level(view.level)
    if not 1 <= point_slot <= points:
        return Screen(
            "🔒 Este Ponto de Talento ainda não está disponível.",
            "character",
            _markup([[_btn("← Pontos", f"doc:ts:{did}:{rev}:{cfg}")]]),
        )
    selected_elsewhere = {
        item.get("talent_id")
        for item in doctrine.configuration.get("talents", ())
        if isinstance(item, dict) and item.get("point_slot") != point_slot
    }
    for index, talent in enumerate(TALENTS_BY_CLASS[view.character_class]):
        if talent.level not in IMPLEMENTED_TALENT_LEVELS or talent.level > view.level:
            continue
        if talent.talent_id in selected_elsewhere:
            continue
        rows.append(
            [_btn(f"{index + 1} {talent.name}", f"doc:ti:{did}:{rev}:{cfg}:{point_slot}:{index}")]
        )
    rows.append([_btn("Remover deste ponto", f"doc:ti:{did}:{rev}:{cfg}:{point_slot}:x")])
    rows.append([_btn("← Pontos", f"doc:ts:{did}:{rev}:{cfg}")])
    return Screen("🌿 Escolha um Talento.", "character", _markup(rows))
