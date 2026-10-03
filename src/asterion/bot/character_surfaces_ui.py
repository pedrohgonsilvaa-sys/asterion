"""Telegram presentation for character status and acquired knowledge."""

from __future__ import annotations

from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.character_surfaces import (
    AttributesView,
    BestiaryRecordView,
    CodexEntryView,
    KnowledgeView,
    ProfileView,
)
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_CATEGORIES,
    CODEX_CATEGORY_ORDER,
    CODEX_ENTRIES,
    CREATURE_PRESENTATION,
    TDO_LOCATIONS,
    TDO_REGION_ID,
    TDO_REGION_LABEL,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.paths import PATH_DEFINITIONS

CLASS_NAMES = {
    "sentinela": "Sentinela",
    "errante": "Errante",
    "vigia": "Vigia",
    "tecelao": "Tecelão",
    "oraculo": "Oráculo",
    "luminar": "Luminar",
}
PATH_LABELS = {path_id: definition.name for path_id, definition in PATH_DEFINITIONS.items()}
CODEX_CATEGORY_KEYS = {
    "world": "w",
    "regions": "r",
    "peoples": "p",
    "figures": "f",
    "history": "h",
    "mysteries": "m",
    "chronicles": "c",
}
CODEX_CATEGORY_BY_KEY = {value: key for key, value in CODEX_CATEGORY_KEYS.items()}


def _slug(value: str) -> str:
    return value.replace("-", "_")


CODEX_ENTRY_KEYS = {
    entry.entry_id: _slug(entry.entry_id.rsplit(".", 1)[-1]) for entry in CODEX_ENTRIES
}
CODEX_ENTRY_BY_KEY = {value: key for key, value in CODEX_ENTRY_KEYS.items()}
ACHIEVEMENT_CATEGORY_KEYS = {
    key: str(index) for index, (key, _) in enumerate(ACHIEVEMENT_CATEGORIES)
}
ACHIEVEMENT_CATEGORY_BY_KEY = {value: key for key, value in ACHIEVEMENT_CATEGORY_KEYS.items()}


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_number(value: int | Decimal) -> str:
    number = Decimal(value)
    if number == number.to_integral_value():
        return f"{int(number):,}".replace(",", ".")
    rendered = format(number.normalize(), "f")
    whole, dot, fractional = rendered.partition(".")
    whole = f"{int(whole):,}".replace(",", ".")
    return f"{whole},{fractional}" if dot else whole


def _identity(name: str, level: int, character_class: str, selected_path: str | None) -> list[str]:
    class_name = CLASS_NAMES.get(character_class, character_class)
    path_name = PATH_LABELS.get(selected_path or "")
    class_line = class_name + (f" · {path_name}" if path_name else "")
    return [f"{name} · Nv. {level}", class_line]


def render_attributes(view: AttributesView) -> Screen:
    lines = [
        "📈 Atributos",
        "",
        "Força, resistência e instinto são moldados por tudo aquilo que seu personagem aprende, "
        "veste e aperfeiçoa.",
        "",
        *_identity(view.name, view.level, view.character_class, view.selected_path),
        "",
        f"❤️ HP · {_format_number(view.hp)} / {_format_number(view.max_hp)}",
        f"⚡ Vigor · {view.vigor} / {view.max_vigor}",
        "",
        f"⚔️ ATQ · {_format_number(view.attack)}",
        f"🛡️ DEF · {_format_number(view.defense)}",
        f"💨 AGI · {_format_number(view.agility)}",
        f"🗡️ PER · {_format_number(view.perception)}",
        "",
        f"💥 Crítico · {_format_number(view.critical)}%",
        f"💨 Esquiva · {_format_number(view.evasion)}%",
        f"🛡️ Bloqueio · {_format_number(view.block)}%",
    ]
    keyboard = _keyboard([[_button("← Personagem", "character:root")]])
    return Screen("\n".join(lines), "character", keyboard, parse_mode="HTML")


def render_profile(view: ProfileView) -> Screen:
    lines = [
        "📇 Perfil",
        "",
        *_identity(view.name, view.level, view.character_class, view.selected_path),
        "",
        "📖 História",
        "",
    ]
    if view.history:
        from html import escape

        lines.append(escape(view.history))
        button = "Editar História"
    else:
        lines.append(
            "Conte quem seu personagem era, o que encontrou pelo caminho "
            "e o que ainda busca em Asterion."
        )
        button = "Escrever História"
    keyboard = _keyboard(
        [
            [_button(button, f"profile:edit:{_base36(view.revision)}")],
            [_button("← Personagem", "character:root")],
        ]
    )
    return Screen("\n".join(lines), "character", keyboard, parse_mode="HTML")


def render_codex_root(view: KnowledgeView) -> Screen:
    categories = _known_codex_categories(view)
    lines = ["📚 Códice", ""]
    rows: list[list[InlineKeyboardButton]] = []
    for category_id, label in CODEX_CATEGORY_ORDER:
        if category_id not in categories:
            continue
        visible_number = len(rows) + 1
        lines.append(f"{visible_number} {label}")
        key = CODEX_CATEGORY_KEYS[category_id]
        rows.append([_button(str(len(rows) + 1), f"kb:c:{key}")])
    rows.append([_button("Bestiário", "kb:b"), _button("Feitos", "kb:a")])
    rows.append([_button("← Menu", "menu:back")])
    if not categories:
        lines.append("Nenhuma entrada foi registrada ainda.")
    return Screen("\n".join(lines), "codex", _keyboard(rows))


def render_codex_category(view: KnowledgeView, category: str) -> Screen:
    label = dict(CODEX_CATEGORY_ORDER).get(category)
    if label is None:
        return render_codex_root(view)
    rows: list[list[InlineKeyboardButton]] = []
    lines = ["📚 Códice", "", label, ""]
    if category == "regions":
        locations = _locations_in_region(view, TDO_REGION_ID)
        if not locations:
            return render_codex_root(view)
        lines.append(TDO_REGION_LABEL)
        rows.append([_button("1", f"kb:r:{TDO_REGION_ID}")])
    else:
        entries = [
            entry
            for entry in view.codex_entries
            if entry.category == category and entry.location_id is None
        ]
        if not entries:
            return render_codex_root(view)
        for index, entry in enumerate(entries, 1):
            lines.append(f"{index} {entry.title}")
            rows.append([_button(str(index), f"kb:e:{CODEX_ENTRY_KEYS[entry.entry_id]}")])
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "codex", _keyboard(rows))


def render_codex_region(view: KnowledgeView, region_id: str) -> Screen:
    if region_id != TDO_REGION_ID:
        return render_codex_category(view, "regions")
    locations = _locations_in_region(view, region_id)
    if not locations:
        return render_codex_category(view, "regions")
    lines = ["🗺️ Regiões e Locais", "", TDO_REGION_LABEL, ""]
    rows = []
    for index, entry in enumerate(locations, 1):
        lines.append(f"{index} {entry.title}")
        rows.append([_button(str(index), f"kb:l:{CODEX_ENTRY_KEYS[entry.entry_id]}")])
    rows.append([_button("← Regiões e Locais", "kb:c:r")])
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "codex", _keyboard(rows))


def render_codex_detail(view: KnowledgeView, entry: CodexEntryView) -> Screen:
    if entry not in view.codex_entries:
        return render_codex_root(view)
    lines = [f"📖 {entry.title}"]
    if entry.location_id:
        lines.extend(["", TDO_LOCATIONS.get(entry.location_id, "Terras do Ocaso")])
    if entry.fragments:
        lines.append("")
        for fragment in entry.fragments:
            lines.extend([f"📜 {fragment.title}", fragment.text, ""])
        lines.pop()
    parent = "kb:r:tdo" if entry.location_id else f"kb:c:{CODEX_CATEGORY_KEYS[entry.category]}"
    rows = [[_button("← Região" if entry.location_id else "← Categoria", parent)]]
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "codex", _keyboard(rows))


def render_bestiary_root(view: KnowledgeView) -> Screen:
    lines = ["🐾 Bestiário", ""]
    regions = _known_bestiary_regions(view)
    rows = []
    if not regions:
        lines.extend(
            [
                "Nenhuma criatura foi registrada ainda.",
                "Enfrente ou observe criaturas durante sua jornada para ampliar seus registros.",
            ]
        )
    else:
        for index, (region_id, label, count) in enumerate(regions, 1):
            lines.extend([f"{index} {label}", f"{count} Criaturas Conhecidas", ""])
            rows.append([_button(str(index), f"kb:br:{region_id}")])
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines).rstrip(), "bestiary", _keyboard(rows))


def render_bestiary_region(view: KnowledgeView, region_id: str) -> Screen:
    if region_id != TDO_REGION_ID:
        return render_bestiary_root(view)
    records = _bestiary_in_region(view, region_id)
    if not records:
        return render_bestiary_root(view)
    lines = ["🐾 Bestiário", "", "🌑 Terras do Ocaso", ""]
    rows = []
    for index, record in enumerate(records, 1):
        lines.append(f"{index} {record.name} · {record.stage_label}")
        rows.append([_button(str(index), f"kb:be:{_slug(record.creature_id)}")])
    rows.append([_button("← Bestiário", "kb:b")])
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "bestiary", _keyboard(rows))


def render_bestiary_detail(view: KnowledgeView, record: BestiaryRecordView) -> Screen:
    if record not in view.bestiary:
        return render_bestiary_root(view)
    lines = [
        f"🐾 {record.name}",
        record.stage_label,
        "",
        "🌑 Terras do Ocaso",
    ]
    if record.note:
        lines.extend(["", record.note])
    if record.habitats:
        lines.append("Habitat conhecido")
        lines.extend(f"• {TDO_LOCATIONS[location_id]}" for location_id in record.habitats)
    if record.materials and record.stage in {"known", "studied", "dominated"}:
        lines.extend(["", "🧱 Materiais conhecidos"])
        lines.extend(f"• {material}" for material in record.materials)
    if record.observed_actions and record.stage in {"studied", "dominated"}:
        lines.extend(
            ["", "📓 Notas de Campo" if record.stage == "dominated" else "Artes observadas"]
        )
        lines.extend(f"• {name}" for name in record.observed_actions)
    if record.variants:
        lines.extend(["", "Variantes observadas"])
        lines.extend(f"• {variant}" for variant in record.variants)
    rows = [[_button("← Terras do Ocaso", "kb:br:tdo")]]
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "bestiary", _keyboard(rows))


def render_achievement_root(view: KnowledgeView) -> Screen:
    lines = ["🏆 Feitos", ""]
    present = {entry.category for entry in view.achievements}
    rows = []
    if not view.achievements:
        lines.append("Nenhum Feito foi conquistado ainda.")
    else:
        for category, label in ACHIEVEMENT_CATEGORIES:
            if category not in present:
                continue
            visible_number = len(rows) + 1
            lines.append(f"{visible_number} {label}")
            rows.append(
                [_button(str(visible_number), f"kb:ac:{ACHIEVEMENT_CATEGORY_KEYS[category]}")]
            )
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "achievements", _keyboard(rows))


def render_achievement_category(view: KnowledgeView, category: str) -> Screen:
    label = dict(ACHIEVEMENT_CATEGORIES).get(category)
    if label is None:
        return render_achievement_root(view)
    entries = [entry for entry in view.achievements if entry.category == category]
    if not entries:
        return render_achievement_root(view)
    lines = ["🏆 Feitos", "", label, ""]
    for index, entry in enumerate(entries, 1):
        lines.append(f"{index} ✅ {entry.name}")
        lines.append(entry.description)
        if entry.reward:
            lines.append(f"🎁 {entry.reward}")
        lines.append("")
    lines.pop()
    rows = [[_button("← Feitos", "kb:a")]]
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "achievements", _keyboard(rows))


def _known_codex_categories(view: KnowledgeView) -> set[str]:
    return {entry.category for entry in view.codex_entries}


def _locations_in_region(view: KnowledgeView, region_id: str) -> list[CodexEntryView]:
    if region_id != TDO_REGION_ID:
        return []
    return sorted(
        (entry for entry in view.codex_entries if entry.location_id is not None),
        key=lambda entry: (entry.order, entry.title.casefold()),
    )


def _bestiary_in_region(view: KnowledgeView, region_id: str) -> list[BestiaryRecordView]:
    return [
        record
        for record in view.bestiary
        if CREATURE_PRESENTATION.get(record.creature_id)
        and CREATURE_PRESENTATION[record.creature_id].region_id == region_id
    ]


def _known_bestiary_regions(view: KnowledgeView) -> list[tuple[str, str, int]]:
    counts: dict[str, int] = {}
    for record in view.bestiary:
        presentation = CREATURE_PRESENTATION.get(record.creature_id)
        if presentation:
            counts[presentation.region_id] = counts.get(presentation.region_id, 0) + 1
    labels = {TDO_REGION_ID: "🌑 Terras do Ocaso"}
    return [
        (region_id, labels[region_id], count)
        for region_id, count in sorted(counts.items())
        if count and region_id in labels
    ]


def _knowledge_navigation(prefix: str) -> list[list[InlineKeyboardButton]]:
    return [
        [
            _button("Códice", f"{prefix}:cd"),
            _button("Bestiário", f"{prefix}:b"),
            _button("Feitos", f"{prefix}:a"),
        ]
    ]


def _base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = digits[remainder] + result
    return result
