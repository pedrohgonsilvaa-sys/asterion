"""Telegram presentation for the Expedição (GDD §22.2, UI §48.5)."""

from __future__ import annotations

from datetime import datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.expeditions import (
    ExpeditionHubView,
    ExpeditionResultView,
    ExpeditionStageNotice,
    ExpeditionView,
)
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import pack
from asterion.domain.expeditions import (
    EXPEDITION_TIMEZONE,
    RESULT_LABELS,
    ROSTER_MAX,
    ROSTER_MIN,
    STAGE_COUNT,
)

_IMAGE = "links"
_WEEKDAYS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
_BACK_TO_GUILD = [InlineKeyboardButton(text="← Guilda", callback_data="guild:root")]
_BACK_TO_EXPEDITION = [InlineKeyboardButton(text="← Expedição", callback_data="exp:hub")]

_ERRORS = {
    "no_character": "Crie um personagem antes de abrir a Expedição.",
    "no_guild": "Você precisa estar em uma Guilda.",
    "catalog_empty": "Nenhuma Expedição está disponível.",
    "not_manager": "Só o Líder ou um Oficial pode montar a Expedição.",
    "guild_dissolving": "A Guilda está em dissolução.",
    "not_member": "Esse personagem não é membro da Guilda.",
    "already_active": "A Guilda já tem uma Expedição em andamento.",
    "roster_full": f"A Expedição aceita até {ROSTER_MAX} participantes.",
    "not_found": "Esta Expedição não está mais disponível.",
    "not_in_roster": "Você não faz parte desta Expedição.",
    "stage_closed": "Este estágio já foi encerrado.",
    "already_chosen": "Você já fez sua escolha neste estágio.",
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Não foi possível concluir essa ação.")


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _when(moment: datetime) -> str:
    local = moment.astimezone(EXPEDITION_TIMEZONE)
    return f"{_WEEKDAYS[local.weekday()]} às {local:%H:%M}"


def _crowns(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _screen(lines: list[str], rows: list[list[InlineKeyboardButton]]) -> Screen:
    return Screen("\n".join(lines), _IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")


def _render_hub(view: ExpeditionHubView) -> Screen:
    lines = ["🚩 Expedição"]
    if view.guild_name:
        lines.append(escape(view.guild_name))
    lines.append("")
    if view.notice:
        lines.extend([escape(view.notice), ""])
    rows: list[list[InlineKeyboardButton]] = []
    if view.catalog_empty:
        lines.append("Nenhuma Expedição programada.")
    elif view.status == "forming":
        _forming(view, lines, rows)
    elif view.status == "active":
        _active(view, lines, rows)
    else:
        lines.append("Entre em uma Guilda para participar de Expedições.")
    if view.has_last_result:
        rows.append([_button("Último Resultado", "exp:last")])
    rows.append(_BACK_TO_GUILD)
    return _screen(lines, rows)


def _forming(view, lines, rows) -> None:
    if view.route_name:
        lines.append(escape(view.route_name))
    lines.extend(
        [
            f"Partida · {_when(view.starts_at)}",
            f"👥 Grupo · {view.roster_count}/{ROSTER_MAX} (mínimo {ROSTER_MIN})",
            "",
        ]
    )
    selected = [entry for entry in view.roster if entry.selected]
    lines.extend(f"· {escape(entry.name)} · Nv. {entry.level}" for entry in selected)
    if not selected:
        lines.append("Ninguém escolhido ainda.")
    if view.can_manage:
        for entry in view.roster:
            mark = "✅" if entry.selected else "➕"
            rows.append([_button(f"{mark} {entry.name}", f"exp:t:{pack(entry.character_id)}")])
    rows.append([_button("Atualizar", "exp:hub")])


def _active(view, lines, rows) -> None:
    if view.route_name:
        lines.append(escape(view.route_name))
    lines.extend([f"Estágio · {view.stage}/{STAGE_COUNT}", f"Até · {_when(view.stage_ends)}", ""])
    if view.stage_flavor:
        lines.extend([escape(view.stage_flavor), ""])
    if not view.in_roster:
        lines.append("Você não faz parte desta Expedição.")
    elif view.answered:
        chosen = next((option for option in view.options if option.chosen), None)
        lines.append(f"Sua escolha · {escape(chosen.label)}" if chosen else "Escolha registrada.")
        if chosen and chosen.description:
            lines.extend(["", escape(chosen.description)])
    else:
        lines.append("Escolha o que fazer. Sem resposta, vale a opção padrão.")
        token = pack(view.expedition_id)
        rows.extend(
            [_button(option.label, f"exp:c:{token}:{view.stage}:{option.index}")]
            for option in view.options
        )
    rows.append([_button("Atualizar", "exp:hub")])


def _render_result(view: ExpeditionResultView) -> Screen:
    # UI §48.5: Treasury and individual reward are distinct blocks.
    lines = [
        f"🚩 Expedição · {RESULT_LABELS[view.result]}",
        escape(view.route_name),
        "",
        f"📊 Pontuação · {view.score}/300",
    ]
    if view.flavor:
        lines.extend(["", escape(view.flavor)])
    if view.treasury:
        lines.extend(["", f"🏛️ Tesouraria · +{_crowns(view.treasury)} Coroas"])
    if view.eligible:
        lines.extend(["", "🎁 Recompensas", f"+{_crowns(view.crowns)} Coroas"])
        lines.extend(f"{item.quantity}x {escape(item.name)}" for item in view.items)
    return _screen(lines, [_BACK_TO_EXPEDITION])


def render_stage_notice(view: ExpeditionStageNotice) -> Screen:
    return _screen(
        [
            f"🚩 {escape(view.route_name)}",
            "",
            f"O estágio {view.stage}/{STAGE_COUNT} foi aberto. Faça sua escolha.",
        ],
        [[_button("Abrir Expedição", "exp:hub")]],
    )


def render_expedition(view: ExpeditionView | ExpeditionStageNotice) -> Screen:
    if isinstance(view, ExpeditionResultView):
        return _render_result(view)
    if isinstance(view, ExpeditionStageNotice):
        return render_stage_notice(view)
    return _render_hub(view)
