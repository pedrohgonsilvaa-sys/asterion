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
    ALTOS_REGION_ID,
    ALTOS_REGION_LABEL,
    CODEX_CATEGORY_ORDER,
    CODEX_ENTRIES,
    CONFINS_REGION_ID,
    CONFINS_REGION_LABEL,
    CR01_BESTIARY_GROUP,
    CR01_BESTIARY_LABEL,
    CREATURE_PRESENTATION,
    LOCATION_LABELS,
    NARETH_REGION_ID,
    NARETH_REGION_LABEL,
    TDO_REGION_ID,
    TDO_REGION_LABEL,
    VARZEAS_REGION_ID,
    VARZEAS_REGION_LABEL,
    VDE_REGION_ID,
    VDE_REGION_LABEL,
    VEU_BESTIARY_GROUP,
    VEU_BESTIARY_LABEL,
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


def _entry_keys() -> dict[str, str]:
    """Short callback keys: the last id segment, or the last two when that one repeats."""
    last = [entry.entry_id.rsplit(".", 1)[-1] for entry in CODEX_ENTRIES]
    keys = {}
    for entry, tail in zip(CODEX_ENTRIES, last, strict=True):
        if last.count(tail) > 1:
            tail = "_".join(entry.entry_id.rsplit(".", 2)[-2:])
        keys[entry.entry_id] = _slug(tail)
    return keys


CODEX_ENTRY_KEYS = _entry_keys()
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
    ]
    if view.selected_title:
        lines.extend(["", f"🎖️ {view.selected_title}"])
    lines.extend(["", "📖 História", ""])
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
    rows = [[_button(button, f"profile:edit:{_base36(view.revision)}")]]
    if view.history:
        rows.append([_button("Compartilhar História", "so:share")])
        rows.append([_button("Remover História", f"profile:rm:{_base36(view.revision)}")])
    rows.append([_button("← Personagem", "character:root")])
    keyboard = _keyboard(rows)
    return Screen("\n".join(lines), "character", keyboard, parse_mode="HTML")


# Contrato Mestre de Telas UI v1.0.0 §20: Códice de Asterion.
CODEX_TEXT = (
    "O conhecimento que o personagem conquista durante sua jornada permanece registrado "
    "aqui. Cada descoberta amplia sua compreensão sobre o mundo, suas histórias e os "
    "acontecimentos que encontrou pelo caminho."
)
# category_id → (botão, título, descrição)
CODEX_CATEGORY_SCREENS = {
    "world": (
        "🌌 Mundo",
        "🌌 Mundo e Cosmologia",
        "Registros sobre Asterion, o Véu, sua cosmologia e os princípios que moldam a "
        "realidade conhecida.",
    ),
    "regions": (
        "🗺️ Locais",
        "🗺️ Regiões e Locais",
        "Conhecimentos adquiridos sobre as terras percorridas, os lugares descobertos e "
        "aquilo que o personagem aprendeu sobre cada região.",
    ),
    "peoples": (
        "👥 Povos",
        "👥 Povos e Facções",
        "Registros sobre povos, culturas, facções e instituições que o personagem conheceu "
        "ou sobre os quais adquiriu conhecimento.",
    ),
    "figures": (
        "👤 Figuras",
        "👤 Figuras",
        "Registros sobre pessoas cuja história, importância ou participação nos "
        "acontecimentos foi conhecida durante a jornada.",
    ),
    "history": (
        "📜 História",
        "📜 História e Acontecimentos",
        "Conhecimentos sobre acontecimentos do passado e do presente, preservados conforme "
        "o personagem descobre suas causas, consequências e contexto.",
    ),
    "mysteries": (
        "🌀 Mistérios",
        "🌀 Mistérios e Fenômenos",
        "Registros sobre fenômenos, mistérios e verdades ocultas que foram legitimamente "
        "descobertos pelo personagem.",
    ),
    "chronicles": (
        "📖 Crônicas",
        "📖 Crônicas",
        "Conhecimentos preservados das Crônicas vividas pelo personagem, registrando "
        "acontecimentos e descobertas que passam a fazer parte de sua história.",
    ),
}
CODEX_BACK = "↩️ Voltar"
CODEX_BESTIARY = "🐾 Bestiário"


def _codex_screen(title: str, description: str | None, rows) -> Screen:
    from html import escape

    parts = [f"<b>{escape(title)}</b>"]
    if description:
        parts.append(f"<i>{escape(description)}</i>")
    return Screen("\n\n".join(parts), "codex", _keyboard(rows), parse_mode="HTML")


def render_codex_root(view: KnowledgeView) -> Screen:
    """Raiz do Códice: as sete categorias, sem contador nem indicação de conteúdo oculto."""
    buttons = [
        _button(CODEX_CATEGORY_SCREENS[category_id][0], f"kb:c:{CODEX_CATEGORY_KEYS[category_id]}")
        for category_id, _label in CODEX_CATEGORY_ORDER
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    # Bestiário é sistema próprio, não categoria do Códice: entrada em linha separada.
    rows.append([_button(CODEX_BESTIARY, "kb:b")])
    rows.append([_button(CODEX_BACK, "menu:back")])
    return _codex_screen("📖 Códice de Asterion", CODEX_TEXT, rows)


def render_codex_category(view: KnowledgeView, category: str) -> Screen:
    """Categoria: descrição e só o que foi descoberto; vazia, só descrição e Voltar."""
    if category not in CODEX_CATEGORY_SCREENS:
        return render_codex_root(view)
    _button_label, title, description = CODEX_CATEGORY_SCREENS[category]
    rows: list[list[InlineKeyboardButton]] = []
    regions = _known_codex_regions(view) if category == "regions" else []
    # Entries without a Local (the Crônica's) are listed after the Regions.
    entries = [
        entry
        for entry in view.codex_entries
        if entry.category == category and entry.location_id is None
    ]
    for region_id, region_label in regions:
        rows.append([_button(region_label, f"kb:r:{region_id}")])
    for entry in entries:
        rows.append([_button(entry.title, f"kb:e:{CODEX_ENTRY_KEYS[entry.entry_id]}")])
    rows.append([_button(CODEX_BACK, "kb:cd")])
    return _codex_screen(title, description, rows)


def render_codex_region(view: KnowledgeView, region_id: str) -> Screen:
    region_labels = _region_labels()
    if region_id not in region_labels:
        return render_codex_category(view, "regions")
    locations = _locations_in_region(view, region_id)
    if not locations:
        return render_codex_category(view, "regions")
    rows = [
        [_button(entry.title, f"kb:l:{CODEX_ENTRY_KEYS[entry.entry_id]}")]
        for entry in locations
    ]
    rows.append([_button(CODEX_BACK, "kb:c:r")])
    return _codex_screen(f"🗺️ {region_labels[region_id]}", None, rows)


def render_codex_detail(view: KnowledgeView, entry: CodexEntryView) -> Screen:
    from html import escape

    if entry not in view.codex_entries:
        return render_codex_root(view)
    parts = [f"📖 <b>{escape(entry.title)}</b>"]
    if entry.location_id and LOCATION_LABELS.get(entry.location_id):
        parts.append(f"<i>{escape(LOCATION_LABELS[entry.location_id])}</i>")
    for fragment in entry.fragments:
        parts.append(f"📜 <b>{escape(fragment.title)}</b>\n{escape(fragment.text)}")
    region_id = _codex_region_id(entry.location_id) if entry.location_id else None
    parent = (
        f"kb:r:{region_id}"
        if region_id in _region_labels()
        else f"kb:c:{CODEX_CATEGORY_KEYS[entry.category]}"
    )
    rows = [[_button(CODEX_BACK, parent)]]
    return Screen("\n\n".join(parts), "codex", _keyboard(rows), parse_mode="HTML")


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
        for region_id, label, count in regions:
            lines.extend([label, f"{count} Criaturas Conhecidas", ""])
            rows.append([_button(label, f"kb:br:{region_id}")])
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines).rstrip(), "bestiary", _keyboard(rows))


def render_bestiary_region(view: KnowledgeView, region_id: str) -> Screen:
    region_labels = _bestiary_labels()
    if region_id not in region_labels:
        return render_bestiary_root(view)
    records = _bestiary_in_region(view, region_id)
    if not records:
        return render_bestiary_root(view)
    lines = ["🐾 Bestiário", "", region_labels[region_id], ""]
    rows = []
    for record in records:
        lines.append(f"{record.name} · {record.stage_label}")
        rows.append([_button(record.name, f"kb:be:{_slug(record.creature_id)}")])
    rows.append([_button("← Bestiário", "kb:b")])
    rows.extend(_knowledge_navigation("kb"))
    return Screen("\n".join(lines), "bestiary", _keyboard(rows))


def render_bestiary_detail(view: KnowledgeView, record: BestiaryRecordView) -> Screen:
    if record not in view.bestiary:
        return render_bestiary_root(view)
    presentation = CREATURE_PRESENTATION.get(record.creature_id)
    region_labels = _bestiary_labels()
    region_id = presentation.region_id if presentation else TDO_REGION_ID
    lines = [
        f"🐾 {record.name}",
        record.stage_label,
        "",
        region_labels.get(region_id, TDO_REGION_LABEL),
    ]
    if record.note:
        lines.extend(["", record.note])
    if record.habitats:
        lines.append("Habitat conhecido")
        lines.extend(
            f"• {LOCATION_LABELS[location_id]}"
            for location_id in record.habitats
            if location_id in LOCATION_LABELS
        )
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
    rows = [[_button("← Bestiário", f"kb:br:{region_id}")]]
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
            lines.append(label)
            rows.append([_button(label, f"kb:ac:{ACHIEVEMENT_CATEGORY_KEYS[category]}")])
    # Feitos fica no Personagem (Contrato Mestre de Telas UI v1.0.0 §6).
    rows.append([_button("↩️ Voltar", "character:root")])
    return Screen("\n".join(lines), "achievements", _keyboard(rows))


def render_achievement_category(view: KnowledgeView, category: str) -> Screen:
    label = dict(ACHIEVEMENT_CATEGORIES).get(category)
    if label is None:
        return render_achievement_root(view)
    entries = [entry for entry in view.achievements if entry.category == category]
    if not entries:
        return render_achievement_root(view)
    lines = ["🏆 Feitos", "", label, ""]
    for entry in entries:
        lines.append(f"✅ {entry.name}")
        lines.append(entry.description)
        if entry.reward:
            lines.append(f"🎁 {entry.reward}")
        lines.append("")
    lines.pop()
    rows = [[_button("↩️ Voltar", "kb:a")]]
    return Screen("\n".join(lines), "achievements", _keyboard(rows))


def _known_codex_categories(view: KnowledgeView) -> set[str]:
    return {entry.category for entry in view.codex_entries}


def _locations_in_region(view: KnowledgeView, region_id: str) -> list[CodexEntryView]:
    return sorted(
        (
            entry
            for entry in view.codex_entries
            if entry.location_id is not None
            and _codex_region_id(entry.location_id) == region_id
        ),
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
    # Short names ("🌑 Terras do Ocaso"), in Region order, the Crônica last.
    labels = {
        region_id: label.split(" · ", 1)[0] for region_id, label in _region_labels().items()
    }
    labels[CR01_BESTIARY_GROUP] = CR01_BESTIARY_LABEL
    labels[VEU_BESTIARY_GROUP] = VEU_BESTIARY_LABEL
    return [
        (region_id, label, counts[region_id])
        for region_id, label in labels.items()
        if counts.get(region_id)
    ]


def _bestiary_labels() -> dict[str, str]:
    return _region_labels() | {
        CR01_BESTIARY_GROUP: CR01_BESTIARY_LABEL,
        VEU_BESTIARY_GROUP: VEU_BESTIARY_LABEL,
    }


def _region_labels() -> dict[str, str]:
    """The six Regions, in progression order."""
    return {
        TDO_REGION_ID: TDO_REGION_LABEL,
        VDE_REGION_ID: VDE_REGION_LABEL,
        NARETH_REGION_ID: NARETH_REGION_LABEL,
        VARZEAS_REGION_ID: VARZEAS_REGION_LABEL,
        ALTOS_REGION_ID: ALTOS_REGION_LABEL,
        CONFINS_REGION_ID: CONFINS_REGION_LABEL,
    }


def _known_codex_regions(view: KnowledgeView) -> list[tuple[str, str]]:
    region_ids = {
        _codex_region_id(entry.location_id)
        for entry in view.codex_entries
        if entry.location_id is not None
    }
    labels = _region_labels()
    return [
        (region_id, labels[region_id])
        for region_id in labels
        if region_id in region_ids and _locations_in_region(view, region_id)
    ]


def _codex_region_id(location_id: str) -> str:
    if location_id.startswith("location.altos."):
        return ALTOS_REGION_ID
    if location_id.startswith("location.confins."):
        return CONFINS_REGION_ID
    return location_id.split(".", 1)[0]


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
