"""Telegram presentation of authoritative equipment modification previews."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from hashlib import sha256
from html import escape
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.bot.creation_ui import Screen


def _value(entry: Any, key: str, default: Any = None) -> Any:
    if isinstance(entry, Mapping):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _label(entry: Any) -> str:
    return escape(
        str(
            _value(
                entry,
                "name",
                _value(entry, "family", _value(entry, "attribute", "Componente")),
            )
        )
    )


def _amount(value: Any) -> str:
    if isinstance(value, Decimal):
        value = format(value, "f")
    return escape(str(value))


def _component_line(number: int, entry: Any, *, icon: str) -> str:
    rarity = escape(str(_value(entry, "rarity", "")))
    grade = escape(str(_value(entry, "grade", "I")))
    potency = _amount(_value(entry, "potency", ""))
    return f"{number} {icon} {_label(entry)} · {rarity} · Grau {grade} · {potency}"


def _item_header(preview: Any, title: str) -> list[str]:
    item = preview.item
    return [
        title,
        "",
        f"{escape(item.name)} · +{item.enhancement}",
        f"{escape(item.rarity)} · {escape(item.item_slot)} · Nv.{item.item_level}",
    ]


def _button(label: str, callback: str) -> InlineKeyboardButton:
    if len(callback.encode("utf-8")) > 64:
        raise ValueError("Equipment callback exceeds Telegram's 64-byte limit")
    return InlineKeyboardButton(text=label, callback_data=callback)


def _back(item_id: str) -> list[InlineKeyboardButton]:
    return [_button("← Equipamento", f"eq:v:{item_id}")]


def _base36(value: int) -> str:
    if value < 0:
        raise ValueError("Versions cannot be negative")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = alphabet[remainder] + result
    return result


def _rune_stack_token(stack_id: Any) -> str:
    return sha256(str(stack_id).encode()).hexdigest()[:8]


def _screen(lines: list[str], rows: list[list[InlineKeyboardButton]]) -> Screen:
    return Screen(
        "\n".join(lines),
        "equipment_item",
        InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


def _reason(preview: Any) -> str:
    reason = _value(preview, "reason")
    if reason is None:
        return "Operação indisponível."
    labels = {
        "INVENTORY_FULL": "🔒 Inventário · Sem espaço",
        "CROWNS": "🔒 Coroas · Insuficientes",
        "MATERIALS": "🔒 Materiais · Insuficientes",
        "FRAGMENTS": "🔒 Fragmentos · Insuficientes",
        "FOREGROUND": "🔒 Configuração · Atividade em andamento",
        "LOCATION": "🔒 Local · Local Inapropriado",
        "FAVORITE": "🔒 Item Favorito",
        "LOCKED": "🔒 Item Bloqueado",
        "EXTRACT_RUNES": "🔒 Extraia as Runas antes da Desmontagem",
        "PROFESSION": "🔒 Ofício · Requisito inválido",
    }
    return labels.get(str(reason), f"🔒 {escape(str(reason).replace('_', ' ').capitalize())}")


def render_enhancement(preview: Any) -> Screen:
    item_id = preview.item.item_instance_id.hex
    details = preview.details
    lines = _item_header(preview, "🔼 Aprimoramento")
    target = _value(details, "target_enhancement", preview.item.enhancement + 1)
    lines.extend(("", f"📈 Aprimoramento · +{target}"))
    current = _value(details, "current_contribution")
    updated = _value(details, "next_contribution")
    attributes = (
        ("hp", "❤️ HP"),
        ("attack", "⚔️ ATQ"),
        ("defense", "🛡️ DEF"),
        ("agility", "💨 AGI"),
        ("per", "🗡️ PER"),
        ("crit", "💥 CRIT"),
        ("evasion", "💨 Esquiva"),
        ("block", "🛡️ Bloqueio"),
    )
    if current is not None and updated is not None:
        for key, label in attributes:
            before = _value(current, key, Decimal(0))
            after = _value(updated, key, Decimal(0))
            if before != after:
                lines.append(
                    f"{label} · {_amount(before)} → {_amount(after)} (+{_amount(after - before)})"
                )
    fragment_name = _value(
        details,
        "fragment_name",
        _value(details, "fragment_id", "Fragmento de Aprimoramento"),
    )
    fragment_owned = _amount(_value(details, "fragment_owned", 0))
    fragment_required = _amount(_value(details, "fragment_required", 0))
    lines.extend(
        (
            "",
            f"🪨 {escape(str(fragment_name))} · {fragment_owned} / {fragment_required}",
            f"🪙 Coroas · {_amount(_value(details, 'crown_cost', 0))}",
        )
    )
    rows = []
    if preview.available:
        rows.append(
            [
                _button(
                    "Aprimorar",
                    f"em:hc:{item_id}:{preview.item_version}:{preview.combat_configuration_version}",
                )
            ]
        )
    else:
        lines.extend(("", _reason(preview)))
    rows.append(_back(item_id))
    return _screen(lines, rows)


def render_runes(preview: Any, *, affinity: str) -> Screen:
    item_id = preview.item.item_instance_id.hex
    details = preview.details
    lines = _item_header(preview, "🔷 Runas")
    if preview.item.two_handed:
        lines.append(
            f"Afinidade {escape(affinity)} · {'Principal' if affinity == 'A' else 'Secundária'}"
        )
    current = _value(details, "current")
    if current:
        grade = escape(str(_value(current, "grade", "I")))
        potency = _amount(_value(current, "potency", ""))
        lines.append(f"Atual · {_label(current)} · Grau {grade} · {potency}")
    else:
        lines.append("Atual · Vazio")
    candidates = tuple(_value(details, "candidates", ()))
    lines.extend(("", "🎒 Runas Compatíveis"))
    rows: list[list[InlineKeyboardButton]] = []
    for index, candidate in enumerate(candidates):
        lines.append(_component_line(index + 1, candidate, icon="🔷"))
        token = _rune_stack_token(_value(candidate, "stack_id"))
        rows.append(
            [
                _button(
                    str(index + 1),
                    f"em:rp:{item_id}:{affinity}:{token}:"
                    f"{_base36(preview.item_version)}:"
                    f"{_base36(preview.combat_configuration_version)}",
                )
            ]
        )
    if not candidates:
        lines.append("Nenhuma Runa compatível disponível.")
    if not preview.available:
        lines.extend(("", _reason(preview)))
    if current and _value(details, "can_remove", False):
        rows.append(
            [
                _button(
                    "Remover Runa",
                    f"em:rr:{item_id}:{affinity}:{preview.item_version}:{preview.combat_configuration_version}",
                )
            ]
        )
    if preview.item.two_handed:
        other = "B" if affinity == "A" else "A"
        rows.append([_button(f"Afinidade {other}", f"em:r:{item_id}:{other}")])
    rows.append(_back(item_id))
    return _screen(lines, rows)


def render_rune_preview(preview: Any, *, affinity: str) -> Screen:
    item_id = preview.item.item_instance_id.hex
    details = preview.details
    candidate = _value(details, "candidate")
    current = _value(details, "current")
    lines = _item_header(preview, "🔷 Instalar Runa")
    lines.extend(
        (
            "",
            f"🔷 {_label(candidate)} · Grau {_value(candidate, 'grade', 'I')}",
            f"{_amount(_value(candidate, 'potency', ''))}",
        )
    )
    if current:
        lines.extend(
            ("", "♻️ Substituição", f"Atual · {_label(current)}", f"Nova · {_label(candidate)}")
        )
    rows = []
    if preview.available:
        action = "Substituir Runa" if current else "Instalar Runa"
        rows.append(
            [
                _button(
                    action,
                    f"em:ri:{item_id}:{affinity}:"
                    f"{_rune_stack_token(_value(candidate, 'stack_id'))}:"
                    f"{_base36(preview.item_version)}:"
                    f"{_base36(preview.combat_configuration_version)}",
                )
            ]
        )
    else:
        lines.extend(("", _reason(preview)))
    rows.append([_button("← Runas", f"em:r:{item_id}:{affinity}")])
    return _screen(lines, rows)


def render_enchantments(preview: Any) -> Screen:
    item_id = preview.item.item_instance_id.hex
    details = preview.details
    lines = _item_header(preview, "💫 Encantamento")
    current = _value(details, "current")
    lines.append(
        f"Atual · {_label(current)} · {_amount(_value(current, 'potency', ''))}"
        if current
        else "Atual · Nenhum"
    )
    lines.extend(("", "🪄 Receitas Disponíveis"))
    rows = []
    candidates = tuple(_value(details, "candidates", ()))
    for index, candidate in enumerate(candidates):
        lines.append(_component_line(index + 1, candidate, icon="💫"))
        rows.append(
            [
                _button(
                    str(index + 1),
                    f"em:ep:{item_id}:{index}:{preview.item_version}:{preview.combat_configuration_version}",
                )
            ]
        )
    if not candidates:
        lines.append("Nenhuma Receita de Encantamento disponível.")
    if not preview.available:
        lines.extend(("", _reason(preview)))
    rows.append(_back(item_id))
    return _screen(lines, rows)


def render_enchantment_preview(preview: Any, *, candidate_index: int) -> Screen:
    item_id = preview.item.item_instance_id.hex
    details = preview.details
    candidate = _value(details, "candidate")
    current = _value(details, "current")
    lines = _item_header(preview, "💫 Encantamento · Preview")
    lines.extend(("", f"💫 {_label(candidate)}", f"{_amount(_value(candidate, 'potency', ''))}"))
    if current:
        lines.extend(
            (
                "",
                "♻️ Substituição",
                f"Atual · {_label(current)}",
                f"Novo · {_label(candidate)}",
                "⚠️ O Encantamento atual será destruído.",
            )
        )
    lines.extend(("", "🧱 Materiais"))
    for material in _value(details, "materials", ()):
        owned = _amount(_value(material, "owned", 0))
        required = _amount(_value(material, "required", 0))
        lines.append(
            f"{_label(material)} · {owned} / {required}"
        )
        selected = tuple(_value(material, "stacks", ()))
        if selected:
            consumption = [
                f"{quantity} {'Vinculado' if bound else 'Negociável'}"
                for _, quantity, bound in selected
            ]
            lines.append("  Consumir · " + ", ".join(consumption))
    lines.append(f"🪙 Coroas · {_amount(_value(details, 'crown_cost', 0))}")
    lines.append(
        "🔗 Vinculado" if _value(details, "result_bound", False) else "🔓 Negociável"
    )
    rows = []
    if preview.available:
        token = str(_value(details, "token", ""))
        if len(token) != 8 or any(char not in "0123456789abcdef" for char in token):
            raise ValueError("Missing enchantment preview token")
        rows.append(
            [
                _button(
                    "Aplicar Encantamento",
                    f"em:ec:{item_id}:{candidate_index}:{preview.item_version}:{preview.combat_configuration_version}:{token}",
                )
            ]
        )
    else:
        lines.extend(("", _reason(preview)))
    rows.append([_button("← Encantamentos", f"em:e:{item_id}")])
    return _screen(lines, rows)


def render_reroll_choices(item: Any, combat_configuration_version: int) -> Screen:
    item_id = item.item_instance_id.hex
    lines = ["🎲 Reroll de Secundário", "", escape(item.name), "", "Escolha um secundário:"]
    rows = []
    for index, (name, value) in enumerate(item.secondaries):
        lines.append(f"{index + 1} {escape(name)} +{escape(value)}")
        rows.append(
            [
                _button(
                    str(index + 1),
                    f"em:lp:{item_id}:{index}:{item.item_version}:{combat_configuration_version}",
                )
            ]
        )
    rows.append(_back(item_id))
    return _screen(lines, rows)


def render_reroll_preview(preview: Any, *, index: int) -> Screen:
    item_id = preview.item.item_instance_id.hex
    details = preview.details
    lines = _item_header(preview, "🎲 Reroll · Preview")
    lines.extend(
        (
            "",
            f"Secundário selecionado · {_label(_value(details, 'current'))}",
            "A identidade será substituída por outra compatível.",
            f"🪙 Coroas · {_amount(_value(details, 'crown_cost', 0))}",
        )
    )
    rows = []
    if preview.available:
        rows.append(
            [
                _button(
                    "Confirmar Reroll",
                    f"em:lc:{item_id}:{index}:{preview.item_version}:{preview.combat_configuration_version}",
                )
            ]
        )
    else:
        lines.extend(("", _reason(preview)))
    rows.append([_button("← Secundários", f"em:l:{item_id}")])
    return _screen(lines, rows)


def render_dismantle_preview(preview: Any, *, reinforced: bool = False) -> Screen:
    item_id = preview.item.item_instance_id.hex
    lines = _item_header(preview, "♻️ Desmontagem")
    lines.extend(("", "🎁 Materiais Recuperados"))
    for material in _value(preview.details, "materials", ()):
        lines.append(
            f"{_label(material)} · {_amount(_value(material, 'quantity', 0))}"
            + (" · Vinculado" if _value(material, "bound", False) else "")
        )
    lines.extend(("", "⚠️ O equipamento será destruído permanentemente."))
    needs_mythic = bool(_value(preview.details, "needs_mythic_confirmation", False))
    if needs_mythic:
        lines.append("⚠️ Equipamento Mítico · Confirmação reforçada")
    rows = []
    if preview.available:
        if needs_mythic and not reinforced:
            rows.append(
                [
                    _button(
                        "Prosseguir com Mítico",
                        f"em:dm:{item_id}:{preview.item_version}:{preview.combat_configuration_version}",
                    )
                ]
            )
        else:
            rows.append(
                [
                    _button(
                        "Desmontar",
                        f"em:dc:{item_id}:{preview.item_version}:{preview.combat_configuration_version}:{int(needs_mythic)}",
                    )
                ]
            )
    else:
        lines.extend(("", _reason(preview)))
    rows.append(_back(item_id))
    return _screen(lines, rows)
