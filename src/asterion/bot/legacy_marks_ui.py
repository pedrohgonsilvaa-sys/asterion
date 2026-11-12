"""Telas das Marcas de Legado (UI DECISOES §33.3)."""

from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.legacy_marks import (
    LegacyMarkEntry,
    LegacyMarkRejected,
    LegacyMarksView,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.legacy_marks import MAX_ACTIVE_MARKS, RESPEC_COST_CROWNS

REJECTION_TEXT = {
    LegacyMarkRejected.UNKNOWN: "Essa Marca não existe.",
    LegacyMarkRejected.UNAVAILABLE: "Essa Marca ainda não está disponível.",
    LegacyMarkRejected.ALREADY_ACTIVE: "Essa Marca já está ativa.",
    LegacyMarkRejected.NOT_ACTIVE: "Essa Marca não está ativa.",
    LegacyMarkRejected.NO_FREE_SLOT: "Não há vaga livre. Cada Ascensão concede uma vaga.",
    LegacyMarkRejected.SAFE_LOCATION_REQUIRED: "Redistribua junto a um Braseiro permanente.",
    LegacyMarkRejected.ACTIVITY_LOCKED: "Encerre a atividade atual antes de redistribuir.",
    LegacyMarkRejected.RESPEC_COOLDOWN: "A Recarga de Redistribuição ainda não terminou.",
    LegacyMarkRejected.NOT_ENOUGH_CROWNS: "Coroas insuficientes para redistribuir.",
    LegacyMarkRejected.INVENTORY_IN_USE: "Libere espaço no Inventário antes de remover.",
    LegacyMarkRejected.WAREHOUSE_IN_USE: "Libere espaço no Armazém antes de remover.",
    LegacyMarkRejected.PENDING_IN_USE: "Retire Entregas Pendentes antes de remover.",
    LegacyMarkRejected.LISTINGS_IN_USE: "Encerre ofertas do Mercado antes de remover.",
    LegacyMarkRejected.DOCTRINES_IN_USE: "Exclua uma Doutrina antes de remover.",
}


def _number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _when(moment: datetime) -> str:
    return moment.strftime("%d/%m %H:%M UTC")


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _entry(view: LegacyMarksView, mark_id: str) -> LegacyMarkEntry | None:
    return next((row for row in view.entries if row.mark.id.value == mark_id), None)


def render_legacy_marks(view: LegacyMarksView, notice: str | None = None) -> Screen:
    full = view.active_count >= MAX_ACTIVE_MARKS
    header = (
        f"🔒 Marcas Ativas · {view.active_count}/{MAX_ACTIVE_MARKS}"
        if full
        else f"Marcas Ativas · {view.active_count}/{MAX_ACTIVE_MARKS}"
    )
    lines = ["🎗️ Marcas de Legado", "", header, f"Vagas livres · {view.free_slots}"]
    if view.slots == 0:
        lines += ["", "Cada Ascensão de Legado concede uma vaga de Marca."]
    if notice:
        lines = [notice, "", *lines]
    rows = []
    for entry in view.entries:
        mark = entry.mark
        prefix = "✅ " if entry.active else ""
        suffix = "" if mark.available or entry.active else " · Em breve"
        rows.append(
            [_button(f"{prefix}{mark.name} · {mark.descriptor}{suffix}", f"lmk:d:{mark.id}")]
        )
    rows.append([_button("← Legado", "legacy:root")])
    return Screen("\n".join(lines), "menu", InlineKeyboardMarkup(inline_keyboard=rows))


def render_legacy_mark_detail(
    view: LegacyMarksView, mark_id: str, notice: str | None = None
) -> Screen:
    entry = _entry(view, mark_id)
    if entry is None:
        return render_legacy_marks(view, REJECTION_TEXT[LegacyMarkRejected.UNKNOWN])
    mark = entry.mark
    state = "✅ Marca Ativa" if entry.active else "🚫 Marca Inativa"
    lines = [f"🎗️ {mark.name} · {mark.descriptor}", "", mark.effect, "", state]
    rows = []
    if entry.active:
        lines += [
            "",
            "Redistribuição",
            f"Custo · {_number(RESPEC_COST_CROWNS)} Coroas",
            "Local · Braseiro permanente",
            "Recarga · 7 dias",
        ]
        if view.respec_available_at is not None:
            lines.append(f"Disponível em · {_when(view.respec_available_at)}")
        rows.append([_button("Remover Marca", f"lmk:off:{mark.id}")])
    elif not mark.available:
        lines += ["", "Em breve."]
    elif view.active_count >= MAX_ACTIVE_MARKS:
        lines += ["", f"🔒 Marcas Ativas · {MAX_ACTIVE_MARKS}/{MAX_ACTIVE_MARKS}"]
    elif view.free_slots > 0:
        rows.append([_button("Ativar Marca", f"lmk:on:{mark.id}")])
    else:
        lines += ["", "Sem vaga livre. Cada Ascensão concede uma vaga."]
    if notice:
        lines = [notice, "", *lines]
    rows.append([_button("← Marcas de Legado", "lmk:root")])
    return Screen("\n".join(lines), "menu", InlineKeyboardMarkup(inline_keyboard=rows))


def render_legacy_mark_removal(view: LegacyMarksView, mark_id: str) -> Screen:
    entry = _entry(view, mark_id)
    if entry is None:
        return render_legacy_marks(view, REJECTION_TEXT[LegacyMarkRejected.UNKNOWN])
    mark = entry.mark
    lines = [
        f"🎗️ Remover {mark.name}?",
        "",
        f"Custo · {_number(RESPEC_COST_CROWNS)} Coroas (você tem {_number(view.crowns)})",
        f"Local · {view.location}",
        "Recarga · 7 dias até a próxima Redistribuição",
        "",
        "A vaga fica livre para ativar outra Marca sem custo.",
    ]
    rows = [
        [_button("Confirmar Remoção", f"lmk:offok:{mark.id}")],
        [_button("Cancelar", f"lmk:d:{mark.id}")],
    ]
    return Screen("\n".join(lines), "menu", InlineKeyboardMarkup(inline_keyboard=rows))
