"""Telegram rendering for Inventory and Pending read models."""

from html import escape
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.inventory import InventoryEntry, InventoryView, origin_label
from asterion.bot.creation_ui import Screen
from asterion.bot.ui_format import first_word, page_bounds, page_nav, pairs
from asterion.domain.consumables import grade_label

# Keeps a page of the longest possible entries under Telegram's 4096-character limit.
PAGE_SIZE = 15

RARITY_ICON = {
    "Comum": "⚪",
    "Raro": "🔵",
    "Épico": "🟣",
    "Lendário": "🟠",
    "Mítico": "🔴",
    "common": "⚪",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟠",
    "mythic": "🔴",
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

SLOT_ICON = {
    "main_hand": "🗡️",
    "2H": "🗡️",
    "off_hand": "⚔️",
    "head": "🪖",
    "torso": "🥋",
    "hands": "🧤",
    "feet": "🥾",
    "accessory": "💍",
    "artifact": "🧿",
    "Arma Principal": "🗡️",
    "Arma Secundária": "⚔️",
    "Cabeça": "🪖",
    "Torso": "🥋",
    "Mãos": "🧤",
    "Pés": "🥾",
    "Acessório": "💍",
    "Artefato": "🧿",
}
SLOT_LABEL = {
    "main_hand": "Arma Principal",
    "2H": "Arma Principal",
    "off_hand": "Arma Secundária",
    "head": "Cabeça",
    "torso": "Torso",
    "hands": "Mãos",
    "feet": "Pés",
    "accessory": "Acessório",
    "artifact": "Artefato",
    "Principal": "Arma Principal",
    "Arma Principal": "Arma Principal",
    "Secundária": "Arma Secundária",
    "Arma Secundária": "Arma Secundária",
    "Cabeça": "Cabeça",
    "Torso": "Torso",
    "Mãos": "Mãos",
    "Pés": "Pés",
    "Acessório": "Acessório",
    "Artefato": "Artefato",
}

MATERIAL_META = {
    "material.confins.ferro_baliza": ("⛏️", "Metal · Grau VI"),
    "material.confins.couro_marcha": ("🐾", "Couro · Grau VI"),
    "material.confins.musgo_limiar": ("🌿", "Reagente · Grau VI"),
    "material.confins.po_referencia": ("✨", "Essência · Grau VI"),
    "material.tdo.catalisador_elite_vi": ("⚗️", "Recurso Especial · Grau VI"),
    "material.tdo.fragmento_aprimoramento_vi": ("🪨", "Recurso Especial · Grau VI"),
    "material.tdo.ferro_de_fuligem": ("⛏️", "Metal · Grau I"),
    "material.tdo.couro_escoriado": ("🐾", "Couro · Grau I"),
    "material.tdo.erva_cinzenta": ("🌿", "Reagente · Grau I"),
    "material.tdo.residuo_ocaso": ("💧", "Essência · Grau I"),
    "material.tdo.catalisador_elite_i": ("⚗️", "Recurso Especial · Grau I"),
    "material.tdo.fragmento_aprimoramento_i": ("🪨", "Recurso Especial · Grau I"),
    "material.tdo.nucleo_vigia_partido": ("💠", "Núcleo de Chefe"),
}

CONSUMABLE_FAMILY_LABELS = {
    "healing": "Cura",
    "purification": "Purificação",
    "antidote": "Antídoto",
    "vigor": "Vigor",
    "protection": "Proteção",
    "dispeller": "Dissipador",
    "warding": "Resguardo",
}

CONSUMABLE_DETAILS = {
    "healing": (
        "❤️ Cura · 22% HP Máximo",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "purification": (
        "✨ Purificação · 1 Efeito Negativo",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "antidote": (
        "☣️ Antídoto · 1 DoT",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "vigor": (
        "⚡ Vigor · +20",
        "🎯 Alvo · Próprio",
        "🌙 Uso · Fora de Combate",
    ),
    "protection": (
        "🔰 Barreira · 12% do HP Máximo",
        "⏳ Duração · 2T",
        "🎯 Alvo · Próprio",
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "dispeller": (
        "✨ Dissipação · 1 Efeito Positivo Removível",
        "🎯 Alvo · 1 Inimigo",
        (
            "ℹ️ Efeitos acumuláveis perdem 1 Acúmulo. "
            "Efeitos protegidos ou não removíveis não são opções válidas."
        ),
        "⚔️ Uso · Somente em Combate PvE",
    ),
    "warding": (
        "🛡️ Resguardo · 2T · 1 Carga",
        "Bloqueia a primeira aplicação elegível de Efeito Negativo removível.",
        (
            "ℹ️ O Dano Direto associado continua normalmente. Não bloqueia Controle Rígido, fases, "
            "mecânicas fixas ou efeitos protegidos."
        ),
        "⚔️ Uso · Somente em Combate PvE",
    ),
}


def rarity_label(entry: InventoryEntry) -> str:
    if not entry.rarity:
        return ""
    label = RARITY_LABEL.get(entry.rarity.casefold())
    if label is None:
        return "⚪ Equipamento"
    return f"{RARITY_ICON[label]} {label}"


def _entry_lines(index: int, entry: InventoryEntry) -> list[str]:
    if entry.kind == "equipment":
        enhancement = int((entry.payload or {}).get("enhancement", 0))
        icon = SLOT_ICON.get(entry.slot or "", "🛡️")
        lines = [f"{icon} {escape(entry.title)} · +{enhancement}"]
        meta = " · ".join(
            part
            for part in (
                rarity_label(entry),
                escape(SLOT_LABEL.get(entry.slot or "", entry.slot or "")),
                f"Nv.{entry.item_level}" if entry.item_level is not None else "",
            )
            if part
        )
        if meta:
            lines.append(meta)
        if entry.bound:
            lines.append("🔗 Vinculado")
        if (entry.payload or {}).get("favorite"):
            lines.append("⭐ Favorito")
        if (entry.payload or {}).get("locked"):
            lines.append("🔒 Protegido")
        runes = (entry.payload or {}).get("runes")
        if isinstance(runes, (list, tuple)) and runes:
            lines.append(f"🔷 Runas · {len(runes)}")
        if entry.equipped:
            lines.append("✅ Equipado")
        return lines

    if entry.kind == "consumable":
        grade = f"Grau {grade_label(entry.grade)}" if entry.grade is not None else None
        metadata = f"Consumível · {grade}" if grade else "Consumível"
        return [f"🧪 {escape(entry.title)} · {entry.quantity}", escape(metadata)]

    if entry.kind == "material":
        icon, meta = MATERIAL_META.get(entry.key, ("🧱", "Material"))
        lines = [f"{icon} {escape(entry.title)} · {entry.quantity}", meta]
        if entry.bound:
            lines.append("🔗 Vinculado")
        return lines

    if entry.kind == "rune":
        lines = [f"🔷 {escape(entry.title)} · {entry.quantity}"]
        meta = " · ".join(
            part
            for part in (
                rarity_label(entry),
                f"Grau {entry.grade}" if entry.grade is not None else "",
            )
            if part
        )
        if meta:
            lines.append(meta)
        if entry.bound:
            lines.append("🔗 Vinculado")
        return lines

    if entry.kind == "blocked_delivery":
        payload = entry.payload or {}
        item_kind = payload.get("delivery_kind")
        if item_kind == "equipment":
            enhancement = int(payload.get("enhancement", 0))
            lines = [f"⚠️ {escape(entry.title)} · +{enhancement}"]
            details = " · ".join(
                part
                for part in (
                    rarity_label(entry),
                    escape(SLOT_LABEL.get(entry.slot or "", entry.slot or "")),
                    f"Nv.{entry.item_level}" if entry.item_level is not None else "",
                )
                if part
            )
            if details:
                lines.append(details)
            if entry.bound:
                lines.append("🔗 Vinculado")
            if payload.get("favorite"):
                lines.append("⭐ Favorito")
            if payload.get("locked"):
                lines.append("🔒 Protegido")
            return lines
        if item_kind == "material":
            lines = [f"⚠️ {escape(entry.title)} · {entry.quantity}"]
            if entry.bound:
                lines.append("🔗 Vinculado")
            return lines
        if item_kind == "rune":
            lines = [f"⚠️ 🔷 {escape(entry.title)} · {entry.quantity}"]
            if entry.rarity or entry.grade is not None:
                details = " · ".join(
                    part
                    for part in (
                        rarity_label(entry),
                        f"Grau {entry.grade}" if entry.grade is not None else "",
                    )
                    if part
                )
                lines.append(details)
            if entry.bound:
                lines.append("🔗 Vinculado")
            return lines
        if item_kind == "consumable":
            return [f"⚠️ {escape(entry.title)} · {entry.quantity}"]

    return [f"📦 {escape(entry.title)} · {entry.quantity}"]


def page_slice(entries: tuple, page: int) -> tuple[int, int, int, tuple]:
    """Clamp the page so a stale button still lands on a page that exists."""

    pages = max(1, -(-len(entries) // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    start = page * PAGE_SIZE
    return page, pages, start, entries[start : start + PAGE_SIZE]


def page_line(page: int, pages: int) -> list[str]:
    return [f"Página {page + 1}/{pages}"] if pages > 1 else []


def page_buttons(page: int, pages: int, prefix: str) -> list[list[InlineKeyboardButton]]:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="← Anterior", callback_data=f"{prefix}:{page - 1}"))
    if page < pages - 1:
        row.append(InlineKeyboardButton(text="Próxima →", callback_data=f"{prefix}:{page + 1}"))
    return [row] if row else []


# Especificação consolidada 2026-11-26, Parte I §3, §5 e §6.
INVENTORY_TITLE = "🎒 Inventário"
INVENTORY_TEXT = (
    "Cada item encontrado permanece registrado no inventário enquanto estiver sob posse "
    "do aventureiro."
)
MATERIALS_TITLE = "🧱 Materiais"
MATERIALS_TEXT = (
    "Materiais encontrados durante a jornada podem ser armazenados, utilizados em "
    "criações e empregados em diferentes possibilidades de Asterion."
)
MATERIALS_PER_PAGE = 5
# Descrições de Material definidas pela Fonte; sem descrição, a linha não aparece.
MATERIAL_DESCRIPTIONS = {
    "material.tdo.residuo_ocaso": (
        "Um resíduo condensado das forças que atravessam as regiões de Asterion."
    ),
}


def _field(emoji: str, label: str, value) -> str:
    return f"{emoji} <b>{escape(label)}</b> · <code>{escape(str(value))}</code>"


def _blocks(*parts: str | None) -> str:
    return "\n\n".join(part for part in parts if part)


def material_grade(entry: InventoryEntry) -> str | None:
    _, meta = MATERIAL_META.get(entry.key, ("🧱", "Material"))
    marker = "Grau "
    return meta.split(marker, 1)[1] if marker in meta else None


def material_source(entry: InventoryEntry) -> str | None:
    source = (entry.payload or {}).get("warehouse_source_id")
    return str(source).replace("-", "") if source else None


def render_inventory_root(view: InventoryView) -> Screen:
    counts = "\n".join(
        (
            _field("🛡️", "Equipamentos", view.equipment_slots),
            _field("🧪", "Consumíveis", view.consumable_slots),
            _field("🧱", "Materiais", view.material_slots),
            _field("🔷", "Runas", view.rune_slots),
        )
    )
    space = "\n".join(
        (
            _field("🎒", "Espaço Inventário", f"{view.used_slots}/{view.capacity}"),
            _field(
                "📦", "Entregas Pendentes", f"{view.pending_count}/{view.pending_capacity}"
            ),
        )
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛡️ Equipamentos", callback_data="inventory:category:equipment"
                ),
                InlineKeyboardButton(
                    text="🧪 Consumíveis", callback_data="inventory:category:consumables"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧱 Materiais", callback_data="inventory:category:materials"
                ),
                InlineKeyboardButton(text="🔷 Runas", callback_data="inventory:category:runes"),
            ],
            [
                # O Armazém não exige Braseiro permanente descoberto (§4).
                InlineKeyboardButton(text="🗄️ Armazém", callback_data="warehouse:root"),
                InlineKeyboardButton(text="📦 Pendentes", callback_data="pending:root"),
            ],
            [InlineKeyboardButton(text="↩️ Retornar", callback_data="character:root")],
        ]
    )
    return Screen(
        _blocks(f"<b>{INVENTORY_TITLE}</b>", f"<i>{escape(INVENTORY_TEXT)}</i>", counts, space),
        "inventory",
        keyboard,
        parse_mode="HTML",
    )


def render_materials(view: InventoryView, page: int = 0) -> Screen:
    """Até 5 Materiais por página, botões 2×2 com a primeira palavra do nome (§5)."""
    entries = [entry for entry in view.entries if entry.kind == "material"]
    page, pages, start = page_bounds(len(entries), page, MATERIALS_PER_PAGE)
    shown = entries[start : start + MATERIALS_PER_PAGE]
    listing = "\n".join(
        f"{MATERIAL_META.get(entry.key, ('🧱', ''))[0]} <b>{escape(entry.title)}</b> · "
        f"<code>{entry.quantity}</code>"
        for entry in shown
    )
    buttons = [
        InlineKeyboardButton(
            text=f"{MATERIAL_META.get(entry.key, ('🧱', ''))[0]} {first_word(entry.title)}",
            callback_data=f"inventory:material:{source}:{page}",
        )
        for entry in shown
        if (source := material_source(entry))
    ]
    rows = [
        *pairs(buttons),
        page_nav(page, pages, lambda target: f"inventory:category:materials:{target}"),
        [InlineKeyboardButton(text="↩️ Retornar", callback_data="inventory:root")],
    ]
    return Screen(
        _blocks(
            f"<b>{MATERIALS_TITLE}</b>",
            f"<i>{escape(MATERIALS_TEXT)}</i>",
            listing or "<i>Nenhum Material no Inventário.</i>",
        ),
        "inventory",
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def render_material_detail(entry: InventoryEntry, page: int = 0) -> Screen:
    """Detalhe do Material (§6): Grau, Quantidade, Tipo e Vínculo; ação Guardar."""
    icon = MATERIAL_META.get(entry.key, ("🧱", ""))[0]
    description = MATERIAL_DESCRIPTIONS.get(entry.key)
    grade = material_grade(entry)
    fields = [
        *([_field("✨", "Grau", grade)] if grade else []),
        _field("📦", "Quantidade", entry.quantity),
        _field("🧱", "Tipo", "Material"),
        *([_field("🔗", "Vínculo", "Vinculado")] if entry.bound else []),
    ]
    rows = []
    if source := material_source(entry):
        rows.append(
            [
                InlineKeyboardButton(
                    text="📦 Guardar", callback_data=f"warehouse:deposit:material:{source}"
                )
            ]
        )
    back = "inventory:category:materials" + (f":{page}" if page else "")
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data=back)])
    return Screen(
        _blocks(
            f"{icon} <b>{escape(entry.title)}</b>",
            f"<i>{escape(description)}</i>" if description else None,
            "\n".join(fields),
        ),
        "inventory",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def render_inventory(view: InventoryView, page: int = 0) -> Screen:
    if view.kind == "inventory_root":
        return render_inventory_root(view)
    if view.kind == "inventory_category" and view.category == "materials":
        return render_materials(view, page)

    if view.kind == "inventory_category":
        headings = {
            "equipment": "🛡️ Equipamentos",
            "consumables": "🧪 Consumíveis",
            "materials": "🧱 Materiais",
            "runes": "🔷 Runas",
        }
        page, pages, start, entries = page_slice(view.entries, page)
        lines = [
            headings.get(view.category or "", "🎒 Inventário"),
            "",
            f"🎒 Inventário · {view.used_slots}/{view.capacity}",
            *page_line(page, pages),
            "",
        ]
        if not entries:
            lines.append("Nenhum item nesta categoria.")
        else:
            for index, entry in enumerate(entries, start=start + 1):
                if index > start + 1:
                    lines.append("")
                lines.extend(_entry_lines(index, entry))
        equipment_buttons = []
        warehouse_equipment_buttons = []
        if view.category == "equipment":
            for entry in entries:
                if entry.kind != "equipment":
                    continue
                try:
                    item_id = UUID(entry.key)
                except (ValueError, TypeError, AttributeError):
                    continue
                equipment_buttons.append(
                    InlineKeyboardButton(
                        text=f"{entry.title} +{int((entry.payload or {}).get('enhancement', 0))}",
                        callback_data=f"eq:v:{item_id.hex}",
                    )
                )
                if not entry.equipped:
                    warehouse_equipment_buttons.append(
                        InlineKeyboardButton(
                            text=f"Guardar {entry.title}",
                            callback_data=f"warehouse:deposit:equipment:{item_id.hex}",
                        )
                    )
        consumable_buttons = [
            InlineKeyboardButton(
                text=entry.title,
                callback_data=f"inventory:consumable:{entry.key}",
            )
            for index, entry in enumerate(entries, start=start + 1)
            if entry.kind == "consumable" and entry.payload is not None
        ]
        rows = [[button] for button in equipment_buttons]
        rows.extend(
            [button] for button in warehouse_equipment_buttons
        )
        if view.category in {"materials", "consumables", "runes"}:
            stack_buttons = [
                InlineKeyboardButton(
                    text=f"Guardar {entry.title}",
                    callback_data=(
                        f"warehouse:deposit:{entry.kind}:"
                        f"{entry.payload['warehouse_source_id'].replace('-', '')}"
                    ),
                )
                for index, entry in enumerate(entries, start=start + 1)
                if entry.payload and entry.payload.get("warehouse_source_id")
            ]
            rows.extend(
                [button] for button in stack_buttons
            )
        rows.extend(
            [button] for button in consumable_buttons
        )
        rows.extend(page_buttons(page, pages, f"inventory:category:{view.category}"))
        rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="inventory:root")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
        return Screen("\n".join(lines), "inventory", keyboard, parse_mode="HTML")

    if view.kind == "inventory_consumable_detail" and view.entries:
        entry = view.entries[0]
        family = (entry.payload or {}).get("family", "")
        label = CONSUMABLE_FAMILY_LABELS.get(family, "Consumível")
        grade = grade_label(entry.grade) if entry.grade is not None else "?"
        lines = [
            f"🧪 {escape(entry.title)} · Grau {grade}",
            f"Consumível · {escape(label)}",
            "",
            f"🎒 Quantidade · {entry.quantity}",
            "",
            *CONSUMABLE_DETAILS.get(family, ()),
        ]
        rows = []
        if family == "vigor" and view.vigor_usable and entry.quantity > 0:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Usar",
                        callback_data=f"consumable:vigor:{entry.key}",
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="← Consumíveis",
                    callback_data="inventory:category:consumables",
                )
            ]
        )
        return Screen("\n".join(lines), "inventory", InlineKeyboardMarkup(inline_keyboard=rows))

    lines = [
        "📦 Entregas Pendentes",
        "",
        f"📦 Espaço · {view.pending_count}/{view.pending_capacity}",
    ]
    if view.blocked_delivery_count:
        lines.extend(
            [
                "",
                f"⚠️ Entregas aguardando espaço · {view.blocked_delivery_count}",
            ]
        )
    lines.append("")
    if not view.entries:
        lines.append("Nenhuma Entrega Pendente.")
    else:
        for index, entry in enumerate(view.entries, start=1):
            if index > 1:
                lines.append("")
            lines.extend(_entry_lines(index, entry))
            if entry.payload and entry.payload.get("origin"):
                lines.append(f"Origem · {origin_label(str(entry.payload['origin']))}")
    claim_buttons = [
        InlineKeyboardButton(
            text=f"Resgatar {entry.title}",
            callback_data=f"pending:claim:{entry.key.replace('-', '')}",
        )
        for index, entry in enumerate(view.entries, start=1)
        if entry.kind in {"equipment", "material", "rune", "consumable"}
    ]
    rows = [[button] for button in claim_buttons]
    if view.blocked_delivery_count:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Tentar entregas bloqueadas", callback_data="pending:retry"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="inventory:root")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    return Screen("\n".join(lines), "pending", keyboard, parse_mode="HTML")
