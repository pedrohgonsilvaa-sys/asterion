"""Telegram presentation for Eventos Mundiais (GDD §21, UI §48.4)."""

from __future__ import annotations

from dataclasses import replace
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.prologue import CombatView
from asterion.application.world_events import (
    WorldEventHubView,
    WorldEventResultView,
    WorldEventStatus,
    WorldEventView,
)
from asterion.bot.combat_ui import hp_bar, number, render_combat
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import pack
from asterion.domain.world_events import (
    ELIGIBILITY_MIN_ACTIONS,
    ELIGIBILITY_MIN_PHASES,
    EVENT_TIMEZONE,
    PHASE_COUNT,
    VIGOR_COST,
)

_WEEKDAYS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
_BACK_TO_EVENTS = [InlineKeyboardButton(text="← Eventos", callback_data="wev:hub")]
_BACK_TO_ADVENTURE = [InlineKeyboardButton(text="← Aventura", callback_data="adv:hub")]

_ERRORS = {
    "no_character": "Crie um personagem antes de entrar em um Evento.",
    "not_found": "Este Evento não está mais disponível.",
    "entry_closed": "A entrada neste Evento já foi encerrada.",
    "withdrawn": "Você encerrou sua participação neste Evento.",
    "busy": "Conclua sua atividade atual antes de entrar no Evento.",
    "no_hp": "Recupere sua vida antes de entrar no Evento.",
    "vigor": f"Você precisa de {VIGOR_COST} Vigor para entrar no Evento.",
    "not_joined": "Você não está participando deste Evento.",
    "gathering": "O Evento ainda está reunindo participantes.",
    "reentry_wait": "Sua reentrada ainda não abriu.",
    "other_version": "Você já entrou em outra versão deste Evento neste horário.",
    "region_locked": "Esta versão é de uma Região que você ainda não alcançou.",
}


def error_text(code: str, seconds: int = 0) -> str:
    text = _ERRORS.get(code, "Não foi possível concluir essa ação.")
    return f"{text} Faltam {seconds}s." if seconds else text


def _button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback)


def _render_empty(view: WorldEventHubView) -> Screen:
    lines = ["🌍 Eventos Mundiais", ""]
    if view.notice:
        lines.extend([escape(view.notice), ""])
    if view.next_opening is None:
        lines.append("Nenhum Evento Mundial programado.")
    else:
        local = view.next_opening.astimezone(EVENT_TIMEZONE)
        lines.append(f"Próximo Evento · {_WEEKDAYS[local.weekday()]} às {local:%H:%M}")
    rows = []
    if view.has_last_result:
        rows.append([_button("Último Resultado", "wev:last")])
    rows.append(_BACK_TO_ADVENTURE)
    return Screen(
        "\n".join(lines), "world_events", InlineKeyboardMarkup(inline_keyboard=rows), "HTML"
    )


def _render_versions(view: WorldEventHubView) -> Screen:
    """Crônica: one version per Region in the same slot; the character picks one."""
    first = view.versions[0]
    lines = [f"🌍 Evento Mundial · {escape(first.name)}", ""]
    if view.notice:
        lines.extend([escape(view.notice), ""])
    if view.seconds_to_start:
        lines.extend([f"⏳ Reunindo participantes · {view.seconds_to_start}s", ""])
    lines.append("Escolha a versão. Você participa de uma só neste horário.")
    lines.append("Nas versões abaixo do seu nível, vale a Sintonização do Véu.")
    lines.append("")
    lines.extend(
        f"• {escape(item.region)} · Nv. {item.level} · 👥 {item.participants}"
        for item in view.versions
    )
    rows = [
        [
            _button(
                f"Entrar · {item.region} · {VIGOR_COST} Vigor",
                f"wev:in:{pack(item.occurrence_id)}",
            )
        ]
        for item in view.versions
    ]
    rows.append([_button("Atualizar", "wev:hub")])
    if view.has_last_result:
        rows.append([_button("Último Resultado", "wev:last")])
    rows.append(_BACK_TO_ADVENTURE)
    return Screen(
        "\n".join(lines), "world_events", InlineKeyboardMarkup(inline_keyboard=rows), "HTML"
    )


def _status_lines(status: WorldEventStatus) -> list[str]:
    lines = [f"🌍 Evento Mundial · {escape(status.name)}", escape(status.region), ""]
    if status.status == "gathering":
        lines.append(f"⏳ Reunindo participantes · {status.seconds_to_start}s")
    else:
        lines.extend(
            [
                f"⚔️ Fase {status.phase}/{PHASE_COUNT} · {escape(status.boss_name or '')}",
                f"{hp_bar(status.boss_hp, status.boss_max_hp)} "
                f"{number(status.boss_hp)}/{number(status.boss_max_hp)}",
            ]
        )
        if status.flavor:
            lines.extend(["", escape(status.flavor)])
    lines.extend(["", f"👥 Participantes · {status.participants}"])
    if status.joined or status.withdrawn:
        state = "✅ Elegível" if status.eligible else "⏳ Em andamento"
        lines.extend(
            [
                "",
                f"Participação · {state}",
                f"Fases · {status.phases_done}/{ELIGIBILITY_MIN_PHASES}",
                f"Ações Significativas · {status.significant_actions}/{ELIGIBILITY_MIN_ACTIONS}",
                f"Consumíveis · {status.consumables_left} restantes",
            ]
        )
    if status.reentry_seconds:
        lines.extend(["", f"💀 Reentrada em {status.reentry_seconds}s"])
    if status.withdrawn:
        lines.extend(["", "Você encerrou sua participação nesta ocorrência."])
    return lines


def _render_status(view: WorldEventHubView, status: WorldEventStatus) -> Screen:
    lines = _status_lines(status)
    if view.notice:
        lines = [escape(view.notice), "", *lines]
    token = pack(status.occurrence_id)
    rows: list[list[InlineKeyboardButton]] = []
    if status.can_enter:
        rows.append([_button(f"Entrar · {VIGOR_COST} Vigor", f"wev:in:{token}")])
    if status.joined and status.status == "active" and not status.reentry_seconds:
        label = "Voltar ao Combate" if status.in_combat else "Combater"
        rows.append([_button(label, f"wev:go:{token}")])
    rows.append([_button("Atualizar", "wev:hub")])
    if status.joined:
        rows.append([_button("Encerrar Participação", f"wev:out:{token}")])
    if view.has_last_result:
        rows.append([_button("Último Resultado", "wev:last")])
    rows.append(_BACK_TO_ADVENTURE)
    return Screen(
        "\n".join(lines), "world_events", InlineKeyboardMarkup(inline_keyboard=rows), "HTML"
    )


def render_withdraw_confirm(token: str) -> Screen:
    return Screen(
        "⚠️ Encerrar Participação\n\n"
        "Sua Configuração de Combate será liberada e você perde o direito de "
        "reentrada nesta ocorrência.",
        "world_events",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [_button("Encerrar", f"wev:oy:{token}")],
                [_button("Voltar", "wev:hub")],
            ]
        ),
        "HTML",
    )


def _render_result(view: WorldEventResultView) -> Screen:
    if not view.completed:
        lines = [
            "⏳ Evento Mundial · Encerrado",
            escape(view.name) + (f" · {escape(view.region)}" if view.region else ""),
            "",
            "O tempo acabou antes do fim. Seu Vigor foi devolvido.",
        ]
    else:
        # UI §48.4: no Recompensas block at all without individual eligibility.
        lines = [
            "🏆 Evento Mundial · Concluído",
            f"{escape(view.name)} · {escape(view.region)}",
            "",
            escape(view.flavor),
            "",
            "✅ Participação · Elegível" if view.eligible else "⚠️ Participação · Insuficiente",
        ]
        if view.eligible:
            lines.extend(["", "🎁 Recompensas", f"+{view.crowns} Coroas", f"+{view.xp} XP"])
            lines.extend(f"{item.quantity}x {escape(item.name)}" for item in view.items)
    return Screen(
        "\n".join(lines),
        "world_events",
        InlineKeyboardMarkup(inline_keyboard=[_BACK_TO_EVENTS]),
        "HTML",
    )


def _render_combat(view: CombatView) -> Screen:
    screen = render_combat(view)
    return replace(screen, text=f"🌍 {escape(view.stage)}\n\n{screen.text}")


def render_world_event(view: WorldEventView) -> Screen:
    if isinstance(view, CombatView):
        return _render_combat(view)
    if isinstance(view, WorldEventResultView):
        return _render_result(view)
    if view.status is None:
        return _render_versions(view) if view.versions else _render_empty(view)
    return _render_status(view, view.status)
