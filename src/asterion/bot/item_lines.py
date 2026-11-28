"""Linhas de item compartilhadas por Inventário, Entregas Pendentes, Armazém e Seleção.

Só apresentação: nenhum número de jogo nasce aqui. Os atributos vêm da contribuição de
domínio já existente (``equipment_stat_contribution``) e as quantidades dos catálogos.
"""

from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Any

from asterion.bot.ui_format import mono, roman
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.equipment import assignment_for_item_slot
from asterion.domain.equipment_stats import (
    EquipmentStatContribution,
    equipment_stat_contribution,
    item_snapshot_from_persisted,
)

RARITY_EMOJI = {"Comum": "⚪️", "Raro": "🔵", "Épico": "🟣", "Lendário": "🟠", "Mítico": "🔴"}
RARITY_NAMES = {
    "comum": "Comum",
    "common": "Comum",
    "raro": "Raro",
    "rare": "Raro",
    "rara": "Raro",
    "épico": "Épico",
    "epic": "Épico",
    "épica": "Épico",
    "lendário": "Lendário",
    "legendary": "Lendário",
    "lendária": "Lendário",
    "mítico": "Mítico",
    "mythic": "Mítico",
    "mítica": "Mítico",
}
# (campo da contribuição, emoji, rótulo, é percentual)
STAT_ROWS = (
    ("hp", "❤️", "HP", False),
    ("attack", "⚔️", "ATQ", False),
    ("defense", "🛡️", "DEF", False),
    ("agility", "💨", "AGI", False),
    ("per", "🎯", "Precisão", True),
    ("crit", "💥", "Crítico", True),
    ("evasion", "⚡️", "Esquiva", True),
    ("block", "💢", "Bloqueio", True),
)
# Atributo de runa/encantamento → (emoji, rótulo).
COMPONENT_STATS = {
    "HP": ("❤️", "HP"),
    "ATQ": ("⚔️", "ATQ"),
    "DEF": ("🛡️", "DEF"),
    "AGI": ("💨", "AGI"),
    "PER": ("🎯", "Precisão"),
    "CRIT": ("💥", "Crítico"),
    "Esquiva": ("⚡️", "Esquiva"),
    "Bloqueio": ("💢", "Bloqueio"),
}
# Resumo de uma linha dos Consumíveis (valores já definidos em CONSUMABLE_DETAILS).
CONSUMABLE_SUMMARY = {
    "healing": ("❤️", "Cura 22% HP"),
    "purification": ("✨", "Purifica 1 Efeito Negativo"),
    "antidote": ("☣️", "Remove 1 DoT"),
    "vigor": ("⚡", "Vigor +20"),
    "protection": ("🔰", "Barreira 12% HP"),
    "dispeller": ("✨", "Dissipa 1 Efeito Positivo"),
    "warding": ("🛡️", "Resguardo 2T"),
}
MATERIAL_ICONS = {
    "Metal": "⛏️",
    "Couro": "🐾",
    "Reagente": "🌿",
    "Essência": "💧",
}
KIND_ICON = {"consumable": "🧪", "material": "🧱", "rune": "🔷"}


def rarity_name(value: str | None) -> str | None:
    return RARITY_NAMES.get(value.casefold()) if value else None


def rarity_emoji(value: str | None) -> str:
    return RARITY_EMOJI.get(rarity_name(value) or "", "⚪️")


def decimal_text(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def equipment_name(name: str, enhancement: int) -> str:
    """``+0`` nunca aparece; só aprimoramento real."""
    return f"{name} +{enhancement}" if enhancement > 0 else name


def stat_parts(
    contribution: EquipmentStatContribution, *, attack_icon: str = "⚔️"
) -> list[tuple[str, str, str]]:
    """(emoji, rótulo, valor) de cada atributo não nulo, ex. ``("🎯", "Precisão", "+2%")``."""
    parts = []
    for attribute, icon, label, percentage in STAT_ROWS:
        value = getattr(contribution, attribute)
        if value == 0:
            continue
        parts.append(
            (attack_icon if attribute == "attack" else icon, label,
             f"+{decimal_text(value)}{'%' if percentage else ''}")
        )  # fmt: skip
    return parts


def stat_line(contribution: EquipmentStatContribution | None, *, attack_icon: str = "⚔️") -> str:
    """``🗡️ `+9 ATQ` · 💨 `+2 AGI` `` — valor e rótulo juntos em monoespaçado."""
    if contribution is None:
        return ""
    return " · ".join(
        f"{icon} {mono(f'{value} {label}')}"
        for icon, label, value in stat_parts(contribution, attack_icon=attack_icon)
    )


def contribution_from_payload(
    *, item_id: str, slot: str | None, item_level: int | None, rarity: str | None,
    payload: dict[str, Any] | None,
) -> EquipmentStatContribution | None:  # fmt: skip
    """Contribuição de um equipamento persistido; ``None`` se o registro não for legível."""
    payload = payload or {}
    label = rarity_name(rarity)
    assignment = assignment_for_item_slot(slot or "")
    if label is None or assignment is None or item_level is None:
        return None
    try:
        snapshot = item_snapshot_from_persisted(
            item_instance_id=str(payload.get("item_instance_id") or item_id),
            equipped_slot=assignment.slot.value,
            item_slot=slot or "",
            item_level=item_level,
            rarity=label,
            payload=payload,
        )
        return equipment_stat_contribution(snapshot)
    except Exception:  # noqa: BLE001 - registro ilegível só perde a linha de atributos
        return None


def component_stat(attribute: str, potency: str) -> str:
    """``("PER", "2.00 p.p.")`` → ``🎯 `+2% Precisão` ``."""
    icon, label = COMPONENT_STATS.get(attribute, ("✨", attribute))
    amount = potency.replace("p.p.", "").replace("%", "").strip()
    try:
        amount = decimal_text(Decimal(amount))
    except ArithmeticError:
        return ""
    return f"{icon} {mono(f'+{amount}% {label}')}"


def _consumable_line(entry: Any) -> str:
    payload = entry.payload or {}
    definition = consumable_definition(payload.get("consumable_id") or getattr(entry, "key", ""))
    if definition is None:
        return ""
    emoji, text = CONSUMABLE_SUMMARY.get(definition.family.value, ("🧪", "Consumível"))
    return f"{emoji} {mono(text)}"


def _material_line(entry: Any) -> str:
    from asterion.bot.inventory_ui import MATERIAL_META

    payload = entry.payload or {}
    _, meta = MATERIAL_META.get(payload.get("material_id") or getattr(entry, "key", ""), ("🧱", "Material"))  # noqa: E501
    if "Grau " in meta:
        return f"✨ {mono('Grau ' + meta.split('Grau ', 1)[1])}"
    return f"🧱 {mono(meta)}"


def item_icon(entry: Any) -> str:
    """Materiais usam sempre 🧱 nas listas aprovadas."""
    return KIND_ICON.get(entry.kind, "📦")


def list_item(position: int, entry: Any, item_id: str, *, blocked: bool = False) -> str:
    """Bloco aprovado de um item de lista:

    ``#2 🧪 **Poção de Vida** · `×4` `` + linha de atributos/efeito.
    ``entry`` é um ``InventoryEntry`` ou ``WarehouseEntry``; ``blocked`` marca ⚠️.
    """
    kind = (entry.payload or {}).get("delivery_kind") if entry.kind == "blocked_delivery" else entry.kind  # noqa: E501
    kind = kind or entry.kind
    warning = "⚠️ " if blocked else ""
    quantity = f" · {mono(f'×{entry.quantity}')}"
    if kind == "equipment":
        payload = entry.payload or {}
        name = escape(equipment_name(entry.title, int(payload.get("enhancement", 0) or 0)))
        lines = [f"#{position} {warning}{rarity_emoji(entry.rarity)} <b>{name}</b>{quantity}"]
        attributes = stat_line(
            contribution_from_payload(
                item_id=item_id, slot=entry.slot, item_level=entry.item_level,
                rarity=entry.rarity, payload=payload,
            ),
            attack_icon="🗡️",
        )  # fmt: skip
        if attributes:
            lines.append(attributes)
        return "\n".join(lines)
    if kind == "consumable":
        lines = [f"#{position} {warning}🧪 <b>{escape(entry.title)}</b>{quantity}"]
        if line := _consumable_line(entry):
            lines.append(line)
        return "\n".join(lines)
    if kind == "material":
        lines = [f"#{position} {warning}{item_icon(entry)} <b>{escape(entry.title)}</b>{quantity}"]
        lines.append(_material_line(entry))
        return "\n".join(lines)
    if kind == "rune":
        lines = [f"#{position} {warning}🔷 <b>{escape(entry.title)}</b>{quantity}"]
        grade = f"Grau {roman(int(entry.grade))}" if entry.grade else ""
        lines.append(f"{rarity_emoji(entry.rarity)} {mono(grade)}" if grade else rarity_emoji(entry.rarity))  # noqa: E501
        return "\n".join(lines)
    return f"#{position} {warning}📦 <b>{escape(entry.title)}</b>{quantity}"
