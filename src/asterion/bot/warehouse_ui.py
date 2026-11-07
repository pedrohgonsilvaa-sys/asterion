"""Telegram screens for public Warehouse transfers."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.warehouse import WarehouseEntry, WarehouseView
from asterion.bot.creation_ui import Screen


def render_warehouse(view: WarehouseView) -> Screen:
    if view.kind == "warehouse_operation":
        direction = {
            "deposit": "Depositar no Armazém",
            "withdraw": "Retirar do Armazém",
            "claim_pending": "Resgatar Entrega Pendente",
        }.get(view.direction or "", "Transferência")
        status = view.status or "preview"
        rows = []
        if status == "preview" and view.operation_id is not None:
            token = view.operation_id.hex
            rows.extend(
                [
                    [
                        InlineKeyboardButton(
                            text="Confirmar", callback_data=f"warehouse:confirm:{token}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Cancelar", callback_data=f"warehouse:cancel:{token}"
                        )
                    ],
                ]
            )
        rows.append([InlineKeyboardButton(text="Armazém", callback_data="warehouse:root")])
        lines = [
            "📦 Confirmar transferência",
            "",
            escape(direction),
            f"Item · {escape(view.title or view.item_kind or 'Item')}",
            f"Quantidade · {view.quantity}",
        ]
        if view.origin:
            lines.append(f"Origem · {escape(view.origin)}")
        lines.extend(
            [
                f"Inventário · {view.inventory_used}/60",
                f"Armazém · {view.warehouse_used}/100",
                f"Estado · {escape(status)}",
            ]
        )
        return Screen(
            "\n".join(lines),
            "warehouse",
            InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="HTML",
        )

    if view.kind == "warehouse_inventory_sources":
        title = (
            "Equipamentos disponíveis para guardar"
            if view.entries and view.entries[0].kind == "equipment"
            else "Materiais disponíveis para guardar"
        )
        lines = [
            f"📦 {title}",
            "",
            f"Inventário · {view.inventory_used}/60",
            f"Armazém · {view.warehouse_used}/100",
            "",
        ]
        buttons = []
        for index, entry in enumerate(view.entries, start=1):
            lines.append(_entry_line(index, entry))
            if not entry.eligible:
                lines.append(f"Indisponível · {escape(entry.reason or 'verificação necessária')}")
            elif entry.id:
                buttons.append(
                    InlineKeyboardButton(
                        text=f"Guardar {index}",
                        callback_data=f"warehouse:deposit:{entry.kind}:{entry.id.replace('-', '')}",
                    )
                )
        rows = [buttons[offset : offset + 2] for offset in range(0, len(buttons), 2)]
        rows.append([InlineKeyboardButton(text="← Armazém", callback_data="warehouse:root")])
        return Screen(
            "\n".join(lines),
            "warehouse",
            InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="HTML",
        )

    lines = [
        "📦 Armazém",
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
    lines.extend(
        [
            f"Inventário · {view.inventory_used}/60",
            f"Armazém · {view.warehouse_used}/100",
            "",
        ]
    )
    if view.entries:
        for index, entry in enumerate(view.entries, start=1):
            lines.append(_entry_line(index, entry))
    else:
        lines.append("O Armazém está vazio.")
    buttons = []
    for index, entry in enumerate(view.entries, start=1):
        buttons.append(
            InlineKeyboardButton(
                text=f"Retirar {index}",
                callback_data=f"warehouse:withdraw:{entry.kind}:{entry.id.replace('-', '')}",
            )
        )
    rows = [buttons[offset : offset + 2] for offset in range(0, len(buttons), 2)]
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="Guardar equipamento",
                    callback_data="warehouse:inventory:equipment",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Guardar materiais",
                    callback_data="warehouse:inventory:material",
                )
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


def _entry_line(index: int, entry: WarehouseEntry) -> str:
    details = []
    if entry.rarity:
        details.append(entry.rarity)
    if entry.slot:
        details.append(entry.slot)
    if entry.item_level is not None:
        details.append(f"Nv.{entry.item_level}")
    if entry.bound:
        details.append("vinculado")
    if entry.kind == "equipment":
        payload = entry.payload or {}
        details.append(f"+{int(payload.get('enhancement', 0))}")
        if payload.get("favorite"):
            details.append("Favorito")
        if payload.get("locked"):
            details.append("Protegido")
        runes = payload.get("runes")
        if isinstance(runes, (list, tuple)) and runes:
            details.append(f"Runas {len(runes)}")
    suffix = f" · {' · '.join(details)}" if details else ""
    quantity = f" · {entry.quantity}" if entry.kind == "material" else ""
    return f"{index}. {escape(entry.title)}{quantity}{suffix}"
