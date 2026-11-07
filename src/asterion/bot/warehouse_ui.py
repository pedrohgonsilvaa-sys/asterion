"""Telegram screens for public Warehouse transfers."""

from html import escape
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.inventory import origin_label
from asterion.application.inventory_capacity import INVENTORY_CAPACITY, WAREHOUSE_CAPACITY
from asterion.application.warehouse import WarehouseEntry, WarehouseView
from asterion.bot.creation_ui import Screen
from asterion.bot.inventory_ui import (
    SLOT_LABEL,
    page_buttons,
    page_line,
    page_slice,
    rarity_label,
)
from asterion.domain.consumables import grade_label

QUANTITY_STEPS = (100, 10, 1)
# Short codes keep quantity callbacks inside Telegram's 64-byte limit.
DIRECTION_CODE = {"deposit": "d", "withdraw": "w"}
KIND_CODE = {"material": "m", "consumable": "c", "rune": "r"}

UNAVAILABLE_REASON = {"EQUIPPED": "Equipado"}
SOURCE_TITLE = {
    "equipment": "Equipamentos disponíveis para guardar",
    "material": "Materiais disponíveis para guardar",
    "consumable": "Consumíveis disponíveis para guardar",
    "rune": "Runas disponíveis para guardar",
}


def render_warehouse(view: WarehouseView, page: int = 0) -> Screen:
    if view.kind == "warehouse_operation":
        return _render_operation(view)
    if view.kind == "warehouse_inventory_sources":
        return _render_sources(view, page)
    return _render_root(view, page)


def render_warehouse_quantity(view: WarehouseView, selected: int) -> Screen:
    """Let the player pick an exact amount; the amount only lives in the buttons."""

    available = view.quantity
    selected = min(max(selected, 1), available)
    token = (
        f"{DIRECTION_CODE[view.direction or '']}:{KIND_CODE[view.item_kind or '']}:"
        f"{view.source_id.hex if view.source_id else ''}"
    )

    def goes_to(text: str, amount: int) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=text, callback_data=f"warehouse:qty:{token}:{amount}")

    steps = [step for step in QUANTITY_STEPS if step == 1 or available > step]
    decrease = [
        goes_to(f"−{step}", max(selected - step, 1)) for step in steps if selected > 1
    ]
    increase = [
        goes_to(f"+{step}", min(selected + step, available))
        for step in reversed(steps)
        if selected < available
    ]
    rows = [row for row in (decrease, increase) if row]
    if selected != available:
        rows.append([goes_to("Tudo", available)])
    rows.append(
        [
            InlineKeyboardButton(
                text="Continuar", callback_data=f"warehouse:go:{token}:{selected}"
            )
        ]
    )
    rows.append([InlineKeyboardButton(text="← Armazém", callback_data="warehouse:root")])
    action = "Depositar no Armazém" if view.direction == "deposit" else "Retirar do Armazém"
    lines = [
        "🗄️ Escolher quantidade",
        "",
        action,
        f"Item · {escape(view.title or 'Item')}",
        f"Disponível · {available}",
        f"Quantidade · {selected}",
        *_capacity_lines(view),
    ]
    return Screen(
        "\n".join(lines),
        "warehouse",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def parse_quantity_callback(data: str) -> tuple[str, str, UUID, int]:
    """Decode `warehouse:<qty|go>:<direction>:<kind>:<source>:<amount>`."""

    parts = data.split(":")
    if len(parts) != 6:
        raise ValueError("Malformed Warehouse quantity callback")
    directions = {code: name for name, code in DIRECTION_CODE.items()}
    kinds = {code: name for name, code in KIND_CODE.items()}
    if parts[2] not in directions or parts[3] not in kinds:
        raise ValueError("Unknown Warehouse quantity callback")
    return directions[parts[2]], kinds[parts[3]], UUID(hex=parts[4]), int(parts[5])


def _render_operation(view: WarehouseView) -> Screen:
    direction = {
        "deposit": "Depositar no Armazém",
        "withdraw": "Retirar do Armazém",
        "claim_pending": "Resgatar Entrega Pendente",
    }.get(view.direction or "", "Transferência")
    rows = []
    if view.status == "preview" and view.operation_id is not None:
        token = view.operation_id.hex
        rows.extend(
            [
                [
                    InlineKeyboardButton(
                        text="Confirmar", callback_data=f"warehouse:confirm:{token}"
                    )
                ],
                [InlineKeyboardButton(text="Cancelar", callback_data=f"warehouse:cancel:{token}")],
            ]
        )
    rows.append([InlineKeyboardButton(text="Armazém", callback_data="warehouse:root")])
    icon = "📦" if view.direction == "claim_pending" else "🗄️"
    lines = [
        f"{icon} Confirmar transferência",
        "",
        escape(direction),
        f"Item · {escape(view.title or view.item_kind or 'Item')}",
        f"Quantidade · {view.quantity}",
    ]
    if view.origin:
        lines.append(f"Origem · {origin_label(view.origin)}")
    lines.extend(_capacity_lines(view))
    return Screen(
        "\n".join(lines),
        "warehouse",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _render_sources(view: WarehouseView, page: int) -> Screen:
    title = SOURCE_TITLE.get(view.item_kind or "", "Itens disponíveis para guardar")
    page, pages, start, entries = page_slice(view.entries, page)
    lines = [f"🗄️ {title}", "", *_capacity_lines(view)]
    lines.extend(page_line(page, pages))
    lines.append("")
    buttons = []
    for index, entry in enumerate(entries, start=start + 1):
        lines.append(_entry_line(index, entry))
        if not entry.eligible:
            reason = UNAVAILABLE_REASON.get(entry.reason or "", "verificação necessária")
            lines.append(f"Indisponível · {reason}")
        elif entry.id:
            buttons.append(
                InlineKeyboardButton(
                    text=f"Guardar {index}",
                    callback_data=f"warehouse:deposit:{entry.kind}:{entry.id.replace('-', '')}",
                )
            )
    rows = [buttons[offset : offset + 2] for offset in range(0, len(buttons), 2)]
    rows.extend(page_buttons(page, pages, f"warehouse:inventory:{view.item_kind}"))
    rows.append([InlineKeyboardButton(text="← Armazém", callback_data="warehouse:root")])
    return Screen(
        "\n".join(lines),
        "warehouse",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _render_root(view: WarehouseView, page: int) -> Screen:
    lines = [
        "🗄️ Armazém",
        "",
        f"Local seguro · {escape(view.location or 'indisponível')}",
    ]
    if not view.accessible:
        lines.append("Acesse um Braseiro permanente descoberto para usar o Armazém.")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="← Inventário", callback_data="inventory:root")]
            ]
        )
        return Screen("\n".join(lines), "warehouse", keyboard)
    page, pages, start, entries = page_slice(view.entries, page)
    lines.extend(_capacity_lines(view))
    lines.extend(page_line(page, pages))
    lines.append("")
    if entries:
        lines.extend(
            _entry_line(index, entry) for index, entry in enumerate(entries, start=start + 1)
        )
    else:
        lines.append("O Armazém está vazio.")
    buttons = [
        InlineKeyboardButton(
            text=f"Retirar {index}",
            callback_data=f"warehouse:withdraw:{entry.kind}:{entry.id.replace('-', '')}",
        )
        for index, entry in enumerate(entries, start=start + 1)
    ]
    rows = [buttons[offset : offset + 2] for offset in range(0, len(buttons), 2)]
    rows.extend(page_buttons(page, pages, "warehouse:page"))
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="Guardar equipamento",
                    callback_data="warehouse:inventory:equipment",
                ),
                InlineKeyboardButton(
                    text="Guardar materiais",
                    callback_data="warehouse:inventory:material",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Guardar consumíveis",
                    callback_data="warehouse:inventory:consumable",
                ),
                InlineKeyboardButton(
                    text="Guardar runas",
                    callback_data="warehouse:inventory:rune",
                ),
            ],
            [InlineKeyboardButton(text="← Inventário", callback_data="inventory:root")],
        ]
    )
    return Screen(
        "\n".join(lines),
        "warehouse",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _capacity_lines(view: WarehouseView) -> list[str]:
    return [
        f"Inventário · {view.inventory_used}/{INVENTORY_CAPACITY}",
        f"Armazém · {view.warehouse_used}/{WAREHOUSE_CAPACITY}",
    ]


def _entry_line(index: int, entry: WarehouseEntry) -> str:
    details = []
    if entry.rarity:
        details.append(rarity_label(entry))
    if entry.slot:
        details.append(escape(SLOT_LABEL.get(entry.slot, entry.slot)))
    if entry.item_level is not None:
        details.append(f"Nv.{entry.item_level}")
    if entry.grade is not None:
        grade = grade_label(entry.grade) if entry.kind == "consumable" else entry.grade
        details.append(f"Grau {grade}")
    if entry.bound:
        details.append("🔗 Vinculado")
    if entry.kind == "equipment":
        payload = entry.payload or {}
        details.append(f"+{int(payload.get('enhancement', 0))}")
        if payload.get("favorite"):
            details.append("⭐ Favorito")
        if payload.get("locked"):
            details.append("🔒 Protegido")
        runes = payload.get("runes")
        if isinstance(runes, (list, tuple)) and runes:
            details.append(f"🔷 Runas {len(runes)}")
    suffix = f" · {' · '.join(details)}" if details else ""
    quantity = "" if entry.kind == "equipment" else f" · {entry.quantity}"
    icon = {"consumable": "🧪 ", "rune": "🔷 "}.get(entry.kind, "")
    return f"{index}. {icon}{escape(entry.title)}{quantity}{suffix}"
