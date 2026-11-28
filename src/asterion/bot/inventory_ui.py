"""Telegram rendering for Inventory and Pending read models."""

from html import escape
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.inventory import InventoryEntry, InventoryView
from asterion.bot.creation_ui import Screen
from asterion.bot.item_lines import list_item
from asterion.bot.ui_format import keycap, numeric_rows, page_nav
from asterion.domain.consumables import grade_label

# UI aprovada: até 6 itens por página, cada um com seu botão numérico.
PAGE_SIZE = 6

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


def page_slice(entries: tuple, page: int) -> tuple[int, int, int, tuple]:
    """Clamp the page so a stale button still lands on a page that exists."""

    pages = max(1, -(-len(entries) // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    start = page * PAGE_SIZE
    return page, pages, start, entries[start : start + PAGE_SIZE]


def page_line(page: int, pages: int) -> list[str]:
    return [_field("📄", "Página", f"{page + 1}/{pages}")]


def page_buttons(page: int, pages: int, prefix: str) -> list[list[InlineKeyboardButton]]:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="← Anterior", callback_data=f"{prefix}:{page - 1}"))
    if page < pages - 1:
        row.append(InlineKeyboardButton(text="Próxima →", callback_data=f"{prefix}:{page + 1}"))
    return [row] if row else []

# UI aprovada (Inventário, Entregas Pendentes e Armazém).
INVENTORY_TITLE = "💼 Inventário"
INVENTORY_TEXT = (
    "Cada item encontrado permanece registrado no inventário enquanto estiver sob posse "
    "do aventureiro."
)
PENDING_TITLE = "📦 Entregas Pendentes"
PENDING_TEXT = (
    "Itens recebidos durante a jornada permanecem aqui quando não podem ser enviados "
    "diretamente para o inventário."
)
FILTER_LABELS = {
    "all": "Todos",
    "equipment": "Equipamentos",
    "consumables": "Consumíveis",
    "materials": "Materiais",
    "runes": "Runas",
}
FILTER_BUTTONS = (
    (("📋 Todos", "inventory:category:all"),),
    (
        ("🛡️ Equipamentos", "inventory:category:equipment"),
        ("🧪 Consumíveis", "inventory:category:consumables"),
    ),
    (("🧱 Materiais", "inventory:category:materials"), ("🔷 Runas", "inventory:category:runes")),
    (("📦 Entregas", "pending:root"), ("🗄️ Armazém", "warehouse:root")),
)
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


def _hex(value: str) -> str:
    return str(value).replace("-", "")


def select_callback(entry: InventoryEntry, page: int = 0) -> str | None:
    """Ação do botão numérico de um item do Inventário (detalhe do próprio item)."""
    if entry.kind == "equipment":
        try:
            return f"eq:v:{UUID(entry.key).hex}"
        except (ValueError, TypeError, AttributeError):
            return None
    if entry.kind == "consumable" and entry.payload is not None:
        return f"inventory:consumable:{entry.key}"
    if entry.kind == "material" and (source := material_source(entry)):
        return f"inventory:material:{source}:{page}"
    if entry.kind == "rune" and (source := material_source(entry)):
        return f"inventory:rune:{source}"
    return None


def numbered_buttons(callbacks: list[str | None]) -> list[InlineKeyboardButton]:
    """Um botão ``1️⃣``, ``2️⃣``… por item da página, na mesma ordem da lista."""
    return [
        InlineKeyboardButton(text=keycap(position), callback_data=callback or "noop")
        for position, callback in enumerate(callbacks, start=1)
    ]


def render_item_list(
    entries: tuple, *, ids: list[str], blocked: list[bool] | None = None
) -> str:
    """Itens numerados ``#1``… da página, separados por uma linha em branco."""
    return "\n\n".join(
        list_item(position, entry, ids[position - 1], blocked=bool(blocked and blocked[position - 1]))  # noqa: E501
        for position, entry in enumerate(entries, start=1)
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
        rows.append([discard_button("material", source)])
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
    if view.kind == "inventory_category":
        return _render_listing(view, page)
    if view.kind == "inventory_consumable_detail" and view.entries:
        return _render_consumable_detail(view)
    return render_pending(view, page)


def _render_listing(view: InventoryView, page: int) -> Screen:
    category = view.category if view.category in FILTER_LABELS else "all"
    page, pages, start, entries = page_slice(view.entries, page)
    listing = (
        render_item_list(entries, ids=[entry.key for entry in entries])
        if entries
        else "Nenhum item neste filtro."
    )
    header = "\n".join(
        (
            _field("🔎", "Filtro", FILTER_LABELS[category]),
            _field("🗳️", "Espaço", f"{view.used_slots}/{view.capacity}"),
            *page_line(page, pages),
        )
    )
    rows = numeric_rows(numbered_buttons([select_callback(entry) for entry in entries]))
    rows.extend(
        [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
        for row in FILTER_BUTTONS
    )
    rows.append(page_nav(page, pages, lambda target: f"inventory:category:{category}:{target}"))
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="character:root")])
    return Screen(
        _blocks(
            f"<b>{INVENTORY_TITLE}</b>", f"<i>{escape(INVENTORY_TEXT)}</i>", header, listing
        ),
        "inventory",
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def render_pending(view: InventoryView, page: int = 0) -> Screen:
    """Entregas Pendentes: mesma convenção do Inventário, sem filtros."""
    page, pages, start, entries = page_slice(view.entries, page)
    blocked = [entry.kind == "blocked_delivery" for entry in entries]
    listing = (
        render_item_list(entries, ids=[entry.key for entry in entries], blocked=blocked)
        if entries
        else "Nenhuma Entrega Pendente."
    )
    header = "\n".join(
        (_field("🗳️", "Espaço", f"{view.pending_count}/{view.pending_capacity}"), *page_line(page, pages))  # noqa: E501
    )
    callbacks = [
        "pending:retry" if entry.kind == "blocked_delivery" else f"pending:claim:{_hex(entry.key)}"
        for entry in entries
    ]
    rows = numeric_rows(numbered_buttons(callbacks))
    rows.append(page_nav(page, pages, lambda target: f"pending:root:{target}"))
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="inventory:root")])
    waiting = (
        f"⚠️ <b>Entregas aguardando espaço</b> · <code>{view.blocked_delivery_count}</code>"
        if view.blocked_delivery_count
        else None
    )
    return Screen(
        _blocks(
            f"<b>{PENDING_TITLE}</b>", f"<i>{escape(PENDING_TEXT)}</i>", header, waiting, listing
        ),
        "pending",
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def render_rune_detail(entry: InventoryEntry) -> Screen:
    """Detalhe mínimo da Runa (sem ação de Forja): nome, raridade, Grau e quantidade."""
    from asterion.bot.item_lines import rarity_emoji, rarity_name
    from asterion.bot.ui_format import roman

    fields = [
        *([_field("✨", "Grau", roman(int(entry.grade)))] if entry.grade else []),
        _field(rarity_emoji(entry.rarity), "Raridade", rarity_name(entry.rarity) or "Comum"),
        _field("📦", "Quantidade", entry.quantity),
        *([_field("🔗", "Vínculo", "Vinculado")] if entry.bound else []),
    ]
    rows = [[InlineKeyboardButton(text="↩️ Retornar", callback_data="inventory:category:runes")]]
    return Screen(
        _blocks(f"🔷 <b>{escape(entry.title)}</b>", "\n".join(fields)),
        "inventory",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _render_consumable_detail(view: InventoryView) -> Screen:
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
    if stack_id := material_source(entry):
        rows.append([discard_button("consumable", stack_id)])
    rows.append(
        [
            InlineKeyboardButton(
                text="← Consumíveis",
                callback_data="inventory:category:consumables",
            )
        ]
    )
    return Screen("\n".join(lines), "inventory", InlineKeyboardMarkup(inline_keyboard=rows))


def discard_button(kind: str, item_hex: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🗑️ Descartar", callback_data=f"discard:ask:{kind}:{item_hex}")


def _item_detail_callback(kind: str, item_hex: str) -> str:
    if kind == "material":
        return f"inventory:material:{item_hex}"
    return "inventory:category:consumables"


def render_discard_confirm(view) -> Screen:
    """Confirmação de descarte, no mesmo padrão das telas de confirmação do Inventário."""
    item_hex = view.item_id.hex
    fields = [
        _field("🎒", "Item", view.title),
        _field("📦", "Quantidade", view.quantity),
        _field("💼", "Inventário", f"{view.inventory_used}/{view.inventory_capacity}"),
        _field("🗄️", "Armazém", f"{view.warehouse_used}/{view.warehouse_capacity}"),
    ]
    if getattr(view, "equipped", False):
        fields.append("🔓 <b>Desequipar</b> · será retirado de Equipamentos antes do descarte")
    back = _item_detail_callback(view.kind, item_hex)
    rows = [
        [
            InlineKeyboardButton(
                text="✅ Confirmar",
                callback_data=f"discard:ok:{view.kind}:{item_hex}:{view.quantity}",
            ),
            InlineKeyboardButton(text="❌ Cancelar", callback_data=back),
        ],
        [InlineKeyboardButton(text="↩️ Retornar", callback_data=back)],
    ]
    return Screen(
        _blocks(
            "🗑️ <b>Confirmar Descarte</b>",
            "<i>O item será removido do inventário e não poderá ser recuperado. "
            "Ele não vai para o Armazém.</i>",
            "\n".join(fields),
        ),
        "inventory",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
