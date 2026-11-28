"""Telegram screens for public Warehouse transfers."""

from dataclasses import replace
from html import escape
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.inventory import origin_label
from asterion.application.warehouse import WarehouseView
from asterion.bot.creation_ui import Screen
from asterion.bot.inventory_ui import (
    FROM_ITEM_DETAIL,
    _field,
    numbered_buttons,
    page_line,
    page_slice,
)
from asterion.bot.item_lines import list_item
from asterion.bot.ui_format import CHARACTER_SKIN, numeric_rows, page_nav

QUANTITY_STEPS = (100, 10, 1)
# Short codes keep quantity callbacks inside Telegram's 64-byte limit.
DIRECTION_CODE = {"deposit": "d", "withdraw": "w"}
KIND_CODE = {"material": "m", "consumable": "c", "rune": "r"}

WAREHOUSE_TITLE = "🗄️ Armazém"
WAREHOUSE_TEXT = (
    "Itens armazenados permanecem guardados separadamente do inventário e podem ser "
    "retirados quando necessário."
)
WAREHOUSE_EMPTY_TEXT = (
    "O Armazém ainda não possui itens armazenados. Os itens depositados aqui ficarão "
    "disponíveis para retirada quando necessário."
)
STORE_TITLE = "🗄️ Confirmar Armazenamento"
STORE_TEXT = (
    "O item será retirado do inventário e transferido para o Armazém, onde permanecerá "
    "guardado separadamente até que você decida retirá-lo novamente."
)
# Armazém aberto pelo Mercado fica sem a skin; aberto pelo Personagem, com a skin
# (decisão do autor 2026-11-28).
MARKET_IMAGE = "warehouse"
UNAVAILABLE_REASON = {"EQUIPPED": "Equipado"}
SOURCE_TITLE = {
    "equipment": "Equipamentos disponíveis para guardar",
    "material": "Materiais disponíveis para guardar",
    "consumable": "Consumíveis disponíveis para guardar",
    "rune": "Runas disponíveis para guardar",
}


def _image(back_to_refuge: bool) -> str:
    return MARKET_IMAGE if back_to_refuge else CHARACTER_SKIN


def render_warehouse(
    view: WarehouseView,
    page: int = 0,
    *,
    back_to_refuge: bool = False,
    from_item: bool = False,
) -> Screen:
    """``back_to_refuge``: o Armazém foi aberto pelo Mercado, e Voltar retorna a ele.

    ``from_item``: o depósito começou no 📥 Guardar do detalhe do item.
    """
    if view.kind == "warehouse_operation":
        screen = _render_operation(view, from_item=from_item)
    elif view.kind == "warehouse_inventory_sources":
        screen = _render_sources(view, page)
    else:
        screen = _render_root(view, page, back_to_refuge)
    return replace(screen, image_key=_image(back_to_refuge))


def render_warehouse_quantity(
    view: WarehouseView, selected: int, *, back_to_refuge: bool = False, from_item: bool = False
) -> Screen:
    """Let the player pick an exact amount; the amount only lives in the buttons."""

    available = view.quantity
    selected = min(max(selected, 1), available)
    origin = f":{FROM_ITEM_DETAIL}" if from_item else ""
    token = (
        f"{DIRECTION_CODE[view.direction or '']}:{KIND_CODE[view.item_kind or '']}:"
        f"{view.source_id.hex if view.source_id else ''}"
    )

    def goes_to(text: str, amount: int) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=text, callback_data=f"warehouse:qty:{token}:{amount}{origin}"
        )

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
                text="Continuar", callback_data=f"warehouse:go:{token}:{selected}{origin}"
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
        _image(back_to_refuge),
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def parse_quantity_callback(data: str) -> tuple[str, str, UUID, int]:
    """Decode `warehouse:<qty|go>:<direction>:<kind>:<source>:<amount>`."""

    parts = data.split(":")
    if len(parts) == 7 and parts[6] == FROM_ITEM_DETAIL:
        parts = parts[:6]
    if len(parts) != 6:
        raise ValueError("Malformed Warehouse quantity callback")
    directions = {code: name for name, code in DIRECTION_CODE.items()}
    kinds = {code: name for name, code in KIND_CODE.items()}
    if parts[2] not in directions or parts[3] not in kinds:
        raise ValueError("Unknown Warehouse quantity callback")
    return directions[parts[2]], kinds[parts[3]], UUID(hex=parts[4]), int(parts[5])


def _render_store_confirmation(view: WarehouseView, *, from_item: bool) -> Screen:
    """Confirmar Armazenamento (especificação visual 2026-11-28).

    Pelo detalhe do item, Cancelar e Retornar cancelam a prévia e voltam ao detalhe;
    pelo Armazém, Retornar volta ao Armazém sem cancelar, como antes.
    """
    token = view.operation_id.hex if view.operation_id is not None else ""
    cancel = f"warehouse:cancel:{token}"
    back = cancel if from_item else "warehouse:root"
    rows = []
    if view.status == "preview" and view.operation_id is not None:
        rows.append(
            [InlineKeyboardButton(text="✅ Confirmar", callback_data=f"warehouse:confirm:{token}")]
        )
        rows.append([InlineKeyboardButton(text="❌ Cancelar", callback_data=cancel)])
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data=back)])
    item = "\n".join(
        (
            _field("🎒", "Item", view.title or view.item_kind or "Item"),
            _field("📦", "Quantidade", view.quantity),
        )
    )
    capacity = "\n".join(
        (
            _field("💼", "Inventário", f"{view.inventory_used}/{view.inventory_capacity}"),
            _field("🗄️", "Armazém", f"{view.warehouse_used}/{view.warehouse_capacity}"),
        )
    )
    return Screen(
        "\n\n".join(
            (f"<b>{escape(STORE_TITLE)}</b>", f"<i>{escape(STORE_TEXT)}</i>", item, capacity)
        ),
        CHARACTER_SKIN,
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _render_operation(view: WarehouseView, *, from_item: bool = False) -> Screen:
    if view.direction == "deposit":
        return _render_store_confirmation(view, from_item=from_item)
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
    listing = []
    callbacks = []
    for position, entry in enumerate(entries, start=1):
        block = list_item(position, entry, entry.id)
        if not entry.eligible:
            reason = UNAVAILABLE_REASON.get(entry.reason or "", "verificação necessária")
            block += f"\n🚫 <code>{escape(reason)}</code>"
            callbacks.append(f"warehouse:inventory:{view.item_kind}")
        else:
            callbacks.append(f"warehouse:deposit:{entry.kind}:{entry.id.replace('-', '')}")
        listing.append(block)
    header = "\n".join(
        (
            _field("🗳️", "Espaço", f"{view.inventory_used}/{view.inventory_capacity}"),
            *page_line(page, pages),
        )
    )
    rows = numeric_rows(numbered_buttons(callbacks))
    rows.append(page_nav(page, pages, lambda t: f"warehouse:inventory:{view.item_kind}:{t}"))
    rows.append([InlineKeyboardButton(text="↩️ Retornar", callback_data="warehouse:store")])
    return Screen(
        "\n\n".join(
            (
                f"<b>🗄️ {escape(title)}</b>",
                header,
                "\n\n".join(listing) or "<i>Nenhum item disponível.</i>",
            )
        ),
        "warehouse",
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def render_warehouse_store_menu(*, back_to_refuge: bool = False) -> Screen:
    """Escolha do tipo de item a guardar; preserva a operação real de depósito."""
    rows = [
        [
            InlineKeyboardButton(text="🛡️ Equipamentos", callback_data="warehouse:inventory:equipment"),  # noqa: E501
            InlineKeyboardButton(text="🧪 Consumíveis", callback_data="warehouse:inventory:consumable"),  # noqa: E501
        ],
        [
            InlineKeyboardButton(text="🧱 Materiais", callback_data="warehouse:inventory:material"),
            InlineKeyboardButton(text="🔷 Runas", callback_data="warehouse:inventory:rune"),
        ],
        [InlineKeyboardButton(text="↩️ Retornar", callback_data="warehouse:root")],
    ]
    return Screen(
        "<b>🗄️ Armazém</b>\n\n<i>Escolha o que guardar a partir do inventário.</i>",
        _image(back_to_refuge),
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _back_row(back_to_refuge: bool) -> list[InlineKeyboardButton]:
    """Retornar preserva a origem: Mercado (antes, Refúgio do Ocaso) ou Inventário."""
    if back_to_refuge:
        return [InlineKeyboardButton(text="↩️ Retornar", callback_data="mkt:root")]
    return [InlineKeyboardButton(text="↩️ Retornar", callback_data="inventory:root")]


def _render_root(view: WarehouseView, page: int, back_to_refuge: bool) -> Screen:
    # Especificação consolidada 2026-11-26 §4: o Armazém não exige Braseiro permanente.
    page, pages, start, entries = page_slice(view.entries, page)
    listing = (
        "\n\n".join(
            list_item(position, entry, entry.id) for position, entry in enumerate(entries, start=1)
        )
        if entries
        else f"<i>{escape(WAREHOUSE_EMPTY_TEXT)}</i>"
    )
    header = "\n".join(
        (
            _field("🗳️", "Espaço", f"{view.warehouse_used}/{view.warehouse_capacity}"),
            *page_line(page, pages),
        )
    )
    callbacks = [
        f"warehouse:withdraw:{entry.kind}:{entry.id.replace('-', '')}" for entry in entries
    ]
    rows = numeric_rows(numbered_buttons(callbacks))
    rows.append([InlineKeyboardButton(text="📥 Guardar", callback_data="warehouse:store")])
    rows.append(page_nav(page, pages, lambda target: f"warehouse:page:{target}"))
    rows.append(_back_row(back_to_refuge))
    return Screen(
        "\n\n".join(
            (
                f"<b>{WAREHOUSE_TITLE}</b>",
                f"<i>{escape(WAREHOUSE_TEXT)}</i>",
                header,
                listing,
            )
        ),
        "warehouse",
        InlineKeyboardMarkup(inline_keyboard=[row for row in rows if row]),
        parse_mode="HTML",
    )


def _capacity_lines(view: WarehouseView) -> list[str]:
    return [
        f"Inventário · {view.inventory_used}/{view.inventory_capacity}",
        f"Armazém · {view.warehouse_used}/{view.warehouse_capacity}",
    ]
