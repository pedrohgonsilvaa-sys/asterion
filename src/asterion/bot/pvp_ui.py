"""Telegram presentation for Duelo and Arena da Vigília (UI §34, §38.5, §48)."""

from __future__ import annotations

from datetime import datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.pvp import (
    ConfirmationView,
    DuelInviteView,
    DuelPreviewView,
    PvpCombatView,
    PvpHubView,
    PvpMessageView,
    PvpResultView,
    PvpView,
    QueueView,
    RankingView,
)
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import pack
from asterion.domain.arena import (
    ARENA_MIN_LEVEL,
    ARENA_TIMEZONE,
    DUEL_MIN_LEVEL,
    PLACEMENT_MATCHES,
    elo_for,
)
from asterion.domain.pvp_flavor import pvp_flavor

DUEL_PROMPT_REF = "pvp:duel"
_IMAGE = "pvp"
_OUTCOME = {"win": ("🏆", "Vitória"), "loss": ("💀", "Derrota"), "draw": ("⚖️", "Empate")}
_REASONS = {
    "surrender": "Encerrado por Rendição.",
    "afk": "Encerrado por ausência (AFK).",
}
_CLASS_NAMES = {
    "sentinela": "Sentinela",
    "errante": "Errante",
    "vigia": "Vigia",
    "tecelao": "Tecelão",
    "oraculo": "Oráculo",
    "luminar": "Luminar",
}
_ERRORS = {
    "no_character": "Crie um personagem antes de entrar no PvP.",
    "arena_level": f"A Arena da Vigília abre no Nv. {ARENA_MIN_LEVEL}.",
    "duel_level": f"O Duelo abre no Nv. {DUEL_MIN_LEVEL}.",
    "opponent_level": f"O oponente precisa estar no Nv. {DUEL_MIN_LEVEL} ou acima.",
    "window_closed": "A Arena da Vigília está fechada agora.",
    "cycle_closed": (
        "A Crônica terminou e a Classificação da Vigília está sendo fechada. "
        "A fila volta a abrir depois da finalização."
    ),
    "queue_blocked": "Sua entrada na fila está em Recarga.",
    "busy": "Conclua sua atividade atual antes de entrar no PvP.",
    "opponent_busy": "Esse personagem não pode duelar agora.",
    "invite_open": "Você já tem um convite de Duelo em aberto.",
    "target_not_found": "Personagem não encontrado.",
    "duel_self": "Escolha outro personagem para desafiar.",
    "not_found": "Esta partida não existe mais.",
    "expired": "Este convite ou confirmação já expirou.",
    "surrender_round": "A Rendição fica disponível a partir da Rodada 5.",
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Esta ação não está mais disponível.")


def _button(text: str, data: str) -> InlineKeyboardButton:
    assert len(data.encode("utf-8")) <= 64, data
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


_BACK = [_button("← PvP", "pvp:hub")]


def _clock(moment: datetime) -> str:
    return moment.astimezone(ARENA_TIMEZONE).strftime("%H:%M")


def _class_name(value: str) -> str:
    return _CLASS_NAMES.get(value, value.title())


def _render_hub(view: PvpHubView) -> Screen:
    if view.elo is not None:
        rank = f"🏅 Renome · {view.renome}\n🔥 Elo · {view.elo}"
    else:
        rank = f"🏅 Colocação · {view.placement_played}/{PLACEMENT_MATCHES}"
    lines = [
        "⚔️ PvP · Competição",
        "",
        f"<b>{escape(view.name)}</b> · Nv. {view.level}",
        rank,
        f"📜 {view.wins}V · {view.losses}D · {view.draws}E",
        "",
        "🕛 Arena da Vigília: 12:00–13:00 e 19:00–20:00",
        "🟢 Aberta agora" if view.window_open else "🔴 Fechada agora",
    ]
    if view.blocked_until is not None:
        lines.append(f"⏳ Fila em Recarga até {_clock(view.blocked_until)}")
    rows = []
    if view.invite is not None:
        lines.extend(["", _invite_line(view.invite)])
        rows.extend(_invite_rows(view.invite))
    rows.extend(
        [
            [_button("Arena da Vigília", "pvp:q"), _button("Duelo", "pvp:duel")],
            [_button("Classificação da Vigília", "pvp:rank")],
            [_button("← Aventura", "world:adventure")],
        ]
    )
    return Screen("\n".join(lines), _IMAGE, _keyboard(*rows), "HTML")


def _invite_line(view: DuelInviteView) -> str:
    who = (
        f"<b>{escape(view.opponent_name)}</b> · Nv. {view.opponent_level} · "
        f"{_class_name(view.opponent_class)}"
    )
    if view.incoming:
        return f"⚔️ Desafio de Duelo\n{who}\n⏳ {view.seconds_left}s para responder"
    return f"⚔️ Duelo enviado para\n{who}\n⏳ {view.seconds_left}s para a resposta"


def _invite_rows(view: DuelInviteView) -> list[list[InlineKeyboardButton]]:
    token = pack(view.match_id)
    if view.incoming:
        return [[_button("Aceitar", f"pvp:ok:{token}"), _button("Recusar", f"pvp:no:{token}")]]
    return [[_button("Cancelar Duelo", f"pvp:no:{token}")]]


def _render_invite(view: DuelInviteView) -> Screen:
    return Screen(_invite_line(view), _IMAGE, _keyboard(*_invite_rows(view), _BACK), "HTML")


def _render_preview(view: DuelPreviewView) -> Screen:
    text = (
        "⚔️ Duelo\n\n"
        f"<b>{escape(view.name)}</b> · Nv. {view.level} · {_class_name(view.character_class)}\n\n"
        "O Duelo não usa normalização e não dá recompensa econômica. "
        "Quando os dois aceitarem, as Configurações de Combate ficam travadas até o fim."
    )
    return Screen(
        text,
        _IMAGE,
        _keyboard([_button("Enviar Desafio", f"pvp:dch:{pack(view.character_id)}")], _BACK),
        "HTML",
    )


def _render_queue(view: QueueView) -> Screen:
    text = (
        "⚔️ Arena da Vigília · Fila\n\n"
        f"⏳ Procurando oponente há {view.waited_seconds}s.\n\n"
        "Sua Configuração de Combate fica travada enquanto você estiver na fila."
    )
    return Screen(
        text,
        _IMAGE,
        _keyboard([_button("Atualizar", "pvp:ref")], [_button("Sair da Fila", "pvp:leave")]),
        "HTML",
    )


def _render_confirmation(view: ConfirmationView) -> Screen:
    token = pack(view.match_id)
    if view.accepted:
        text = (
            "⚔️ Arena da Vigília · Confirmação de Entrada\n\n"
            f"✅ Você confirmou. Aguardando o oponente ({view.seconds_left}s)."
        )
        rows = [[_button("Atualizar", "pvp:ref")]]
    else:
        text = (
            "⚔️ Arena da Vigília · Confirmação de Entrada\n\n"
            f"Um oponente foi encontrado. Confirme em {view.seconds_left}s.\n"
            "O oponente é revelado quando os dois aceitarem."
        )
        rows = [[_button("Aceitar", f"pvp:ok:{token}"), _button("Recusar", f"pvp:no:{token}")]]
    return Screen(text, _IMAGE, _keyboard(*rows), "HTML")


def _render_combat(view: PvpCombatView) -> Screen:
    screen = render_combat(view.battle)
    token = pack(view.match_id)
    timer = (
        f"⏳ Seu turno · {view.seconds_left}s"
        if view.my_turn
        else f"⏳ Turno do oponente · {view.seconds_left}s"
    )
    rows = list(screen.keyboard.inline_keyboard) if screen.keyboard is not None else []
    rows.append([_button("Atualizar", "pvp:ref")])
    if view.can_surrender:
        rows.append([_button("Render-se", f"pvp:sur:{token}")])
    return Screen(
        f"{screen.text}\n\n{timer}",
        screen.image_key,
        _keyboard(*rows),
        screen.parse_mode,
    )


def render_surrender_confirm(match_token: str) -> Screen:
    return Screen(
        "⚔️ Render-se conta como derrota normal. Confirmar?",
        _IMAGE,
        _keyboard(
            [_button("Confirmar Rendição", f"pvp:suy:{match_token}")],
            [_button("Voltar", "pvp:ref")],
        ),
        "HTML",
    )


def _render_result(view: PvpResultView) -> Screen:
    icon, label = _OUTCOME[view.outcome]
    title = "Arena da Vigília" if view.kind == "arena" else "Duelo"
    lines = [f"{icon} {title} · {label}", f"{escape(view.name)} vs {escape(view.opponent)}"]
    reason = _REASONS.get(view.reason)
    if reason is not None:
        lines.extend(["", reason])
    if view.kind == "arena":
        lines.extend(["", *_arena_lines(view)])
    seed = f"{view.name}:{view.opponent}:{view.renome_before}:{view.placement_played}"
    lines.extend(["", f"<i>{escape(pvp_flavor(view.kind, view.outcome, seed))}</i>"])
    return Screen("\n".join(lines), _IMAGE, _keyboard(_BACK), "HTML")


def _arena_lines(view: PvpResultView) -> list[str]:
    if view.placed_after is False:
        return [f"🏅 Colocação · {view.placement_played}/{PLACEMENT_MATCHES}"]
    before, after = view.renome_before or 0, view.renome_after or 0
    if view.placed_before is False:
        return [f"🏅 Renome · {after}", f"🔥 Elo · {elo_for(after)}"]
    elo_before, elo_after = elo_for(before), elo_for(after)
    elo = elo_after if elo_before == elo_after else f"{elo_before} → {elo_after}"
    return [f"🏅 Renome · {before} → {after} ({after - before:+d})", f"🔥 Elo · {elo}"]


def _render_message(view: PvpMessageView) -> Screen:
    texts = {
        "dodged": "A Confirmação de Entrada não foi concluída. Você saiu da fila.",
        "requeued": "O oponente não confirmou. Você voltou para a fila, sem penalidade.",
        "queue_released": "A janela da Arena fechou. Você saiu da fila, sem penalidade.",
        "duel_expired": "O convite de Duelo expirou.",
        "duel_declined": f"{escape(view.name or 'O oponente')} encerrou o convite de Duelo.",
    }
    lines = [texts.get(view.code, "Esta ação não está mais disponível.")]
    if view.until is not None:
        lines.append(f"⏳ Fila em Recarga até {_clock(view.until)}.")
    rows = [[_button("Atualizar", "pvp:ref")]] if view.code == "requeued" else [_BACK]
    return Screen("\n".join(lines), _IMAGE, _keyboard(*rows), "HTML")


def render_pvp(view: PvpView) -> Screen:
    if isinstance(view, PvpHubView):
        return _render_hub(view)
    if isinstance(view, DuelPreviewView):
        return _render_preview(view)
    if isinstance(view, DuelInviteView):
        return _render_invite(view)
    if isinstance(view, QueueView):
        return _render_queue(view)
    if isinstance(view, ConfirmationView):
        return _render_confirmation(view)
    if isinstance(view, PvpCombatView):
        return _render_combat(view)
    if isinstance(view, PvpResultView):
        return _render_result(view)
    return _render_message(view)


def render_ranking(view: RankingView) -> Screen:
    lines = ["🏆 Classificação da Vigília", "", "🏅 Posição Atual", ""]
    if view.own is not None:
        lines.extend(
            [
                f"{escape(view.own.name)} · #{view.own.position}",
                f"{view.own.elo} · {view.own.renome} Renome",
            ]
        )
    else:
        lines.append(f"Em Colocação · {view.own_placement_played}/{PLACEMENT_MATCHES}")
    lines.extend(["", "🏆 Destaques da Vigília", ""])
    if view.highlights:
        for row in view.highlights:
            lines.extend([f"{row.position} {escape(row.name)}", f"{row.elo} · {row.renome} Renome"])
    else:
        lines.append("Nenhum nome registrado ainda.")
    rows = [[_button("🏛️ Salão da Vigília", "cr:hall")], _BACK]
    return Screen("\n".join(lines), _IMAGE, InlineKeyboardMarkup(inline_keyboard=rows), "HTML")
