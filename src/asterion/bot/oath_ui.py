"""Telegram presentation for the Juramento (GDD §22.1, UI §48.6)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.oaths import (
    OathAttemptResultView,
    OathCycleResultView,
    OathHubView,
    OathTurnNotice,
    OathView,
)
from asterion.application.prologue import CombatView
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.domain.combat import active_player_key
from asterion.domain.oaths import (
    MAX_INDIVIDUAL_CONTRIBUTION,
    MIN_INDIVIDUAL_CONTRIBUTION,
    OATH_TIMEZONE,
    PROVACOES_PER_CYCLE,
)

_IMAGE = "links"
_WEEKDAYS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
_TIERS = ("", "I", "II", "III", "IV")
_BACK_TO_GUILD = [InlineKeyboardButton(text="← Guilda", callback_data="guild:root")]
_BACK_TO_OATH = [InlineKeyboardButton(text="← Juramento", callback_data="oath:hub")]

_ERRORS = {
    "no_character": "Crie um personagem antes de abrir o Juramento.",
    "no_guild": "Você precisa estar em uma Guilda para realizar Provações.",
    "closed": "O Juramento não está aberto para novas Provações.",
    "bound_elsewhere": "Neste ciclo você já está vinculado ao Juramento de outra Guilda.",
    "no_provacoes": "Você já usou todas as Provações deste ciclo.",
    "busy": "Conclua sua atividade atual antes de iniciar uma Provação.",
    "no_active": "Você não está em uma Provação.",
    "not_opener": "Só quem abriu a Provação pode abandoná-la.",
}
_OUTCOME_TITLES = {
    "completed": "Concluída",
    "failed": "Derrota",
    "abandoned": "Abandonada",
    "expired": "Encerrada",
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Não foi possível concluir essa ação.")


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _when(moment: datetime) -> str:
    local = moment.astimezone(OATH_TIMEZONE)
    return f"{_WEEKDAYS[local.weekday()]} às {local:%H:%M}"


def _crowns(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _render_hub(view: OathHubView) -> Screen:
    lines = ["⚜️ Juramento"]
    if view.guild_name:
        lines.append(escape(view.guild_name))
    lines.append("")
    if view.notice:
        lines.extend([escape(view.notice), ""])
    rows: list[list[InlineKeyboardButton]] = []
    if view.catalog_empty:
        lines.append("Nenhum Juramento programado.")
    elif view.deadline is None:
        if view.guild_name is None:
            lines.append("Entre em uma Guilda para participar do Juramento.")
        if view.next_opening is not None:
            lines.append(f"Próximo Juramento · {_when(view.next_opening)}")
    else:
        _active_lines(view, lines)
        _active_rows(view, rows)
    if view.has_last_result:
        rows.append([_button("Último Resultado", "oath:last")])
    rows.append(_BACK_TO_GUILD)
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows), "HTML")


def _active_lines(view: OathHubView, lines: list[str]) -> None:
    if view.trial_name:
        lines.append(escape(view.trial_name))
    if view.window == "open":
        lines.append(f"Aberto até · {_when(view.deadline)}")
    else:
        lines.append("Janela encerrada · Provações em andamento podem terminar.")
    lines.extend(
        [
            "",
            f"⚔️ Provações · {view.provacoes_left}/{PROVACOES_PER_CYCLE}",
            f"📈 Contribuição · {view.individual}/{MAX_INDIVIDUAL_CONTRIBUTION}",
        ]
    )
    if view.bound and view.individual < MIN_INDIVIDUAL_CONTRIBUTION:
        lines.append(f"Elegibilidade · {MIN_INDIVIDUAL_CONTRIBUTION} pontos")
    lines.append("")
    tier = f" · Faixa {_TIERS[view.tier]}" if view.tier else ""
    lines.append(f"🏛️ Guilda · {view.collective} pontos{tier}")
    if view.next_threshold is not None:
        lines.append(f"Próxima Faixa · {view.next_threshold} pontos")
    if view.bound_elsewhere:
        lines.extend(
            [
                "",
                "Sua participação neste ciclo continua vinculada à Guilda anterior. "
                "Você volta a participar no próximo ciclo.",
            ]
        )


def _active_rows(view: OathHubView, rows: list[list[InlineKeyboardButton]]) -> None:
    if view.active_attempt_id is not None:
        rows.append([_button("Voltar à Provação", "oath:go")])
        if view.can_abandon:
            rows.append([_button("Abandonar Provação", "oath:out")])
    elif view.can_start:
        rows.append([_button("Iniciar sozinho", "oath:solo")])
        if view.has_group:
            rows.append([_button("Iniciar com o Grupo", "group:oath:p")])
    rows.append([_button("Atualizar", "oath:hub")])


def render_abandon_confirm() -> Screen:
    return Screen(
        "⚠️ Abandonar Provação\n\n"
        "A Provação termina para todo o grupo e continua consumida. "
        "Os objetivos já concluídos permanecem válidos.",
        _IMAGE,
        _keyboard([[_button("Abandonar", "oath:outy")], [_button("Voltar", "oath:hub")]]),
        "HTML",
    )


def _render_attempt_result(view: OathAttemptResultView) -> Screen:
    title = _OUTCOME_TITLES.get(view.outcome, "Encerrada")
    lines = [f"⚜️ Provação · {title}", f"Juramento · {escape(view.guild_name)}", ""]
    if view.flavor:
        lines.extend([escape(view.flavor), ""])
    lines.extend(
        [
            f"📈 Contribuição · +{view.points}",
            f"⚜️ Ciclo · {view.cycle_total}/{MAX_INDIVIDUAL_CONTRIBUTION}",
        ]
    )
    return Screen("\n".join(lines), _IMAGE, _keyboard([_BACK_TO_OATH]), "HTML")


def _cycle_flavor(view: OathCycleResultView) -> str:
    if not view.tier:
        return "A Guilda não alcançou a primeira Faixa neste ciclo."
    if view.eligible:
        return "O Juramento foi cumprido, e sua parte nele foi reconhecida."
    if view.participated:
        return (
            "Você participou deste ciclo, mas não alcançou a contribuição "
            "necessária para a recompensa individual."
        )
    return "Sua Guilda cumpriu o Juramento sem a sua participação neste ciclo."


def _render_cycle_result(view: OathCycleResultView) -> Screen:
    title = f"Faixa {_TIERS[view.tier]}" if view.tier else "Sem Faixa"
    lines = [
        f"⚜️ Juramento · {title}",
        escape(view.guild_name),
        "",
        f"📈 Contribuição · {view.contribution}/{MAX_INDIVIDUAL_CONTRIBUTION}",
        "",
        _cycle_flavor(view),
    ]
    if view.treasury:
        lines.extend(["", f"🏛️ Tesouraria · +{_crowns(view.treasury)} Coroas"])
    # UI §48.6: no Recompensas block at all without individual eligibility.
    if view.eligible:
        lines.extend(["", "🎁 Recompensas", f"+{_crowns(view.crowns)} Coroas"])
        lines.extend(f"{item.quantity}x {escape(item.name)}" for item in view.items)
    return Screen("\n".join(lines), _IMAGE, _keyboard([_BACK_TO_OATH]), "HTML")


def render_turn_notice(view: OathTurnNotice) -> Screen:
    text = "A Provação começou." if view.started else "É a sua vez na Provação."
    return Screen(
        f"⚜️ {escape(view.title)}\n\n{text}",
        _IMAGE,
        _keyboard([[_button("Abrir Provação", "oath:go")]]),
        "HTML",
    )


def _render_combat(view: CombatView) -> Screen:
    screen = render_combat(view)
    text = f"⚜️ {escape(view.stage)}\n\n{screen.text}"
    # Teammates play in turns, so a waiting member needs a way to reload.
    if active_player_key(view.combat) == view.combat_actor_key:
        return replace(screen, text=text)
    rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
    rows.append([_button("Atualizar", "oath:go")])
    return replace(screen, text=text, keyboard=_keyboard(rows))


def render_oath(view: OathView | OathTurnNotice) -> Screen:
    if isinstance(view, CombatView):
        return _render_combat(view)
    if isinstance(view, OathAttemptResultView):
        return _render_attempt_result(view)
    if isinstance(view, OathCycleResultView):
        return _render_cycle_result(view)
    if isinstance(view, OathTurnNotice):
        return render_turn_notice(view)
    return _render_hub(view)
