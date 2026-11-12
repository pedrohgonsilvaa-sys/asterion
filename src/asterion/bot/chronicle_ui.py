"""Telegram screens for the Crônica, its vote, the Trilha and the Salão da Vigília."""

from __future__ import annotations

from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.chronicle import (
    ChapterView,
    ChronicleView,
    ClaimResult,
    HallRow,
    HallView,
    TrackView,
)
from asterion.application.chronicle_activities import ActionView, ReadingsView, TalkView
from asterion.application.chronicle_encounters import EncounterActionView, EncounterResultView
from asterion.application.prologue import CombatView
from asterion.bot.benefits_ui import granted_lines
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.domain.calendar_cycles import next_daily_reset, next_new_vigil
from asterion.domain.chronicle import (
    CHAPTER_COUNT,
    CHRONICLE_COSMETICS_BY_ID,
    CHRONICLE_NAME,
    EPILOGUES,
    FREE_TRACK,
    KIND_LABELS,
    MAX_POINTS,
    MILESTONE_COUNT,
    MILESTONE_STEP,
    OPENING_TEXT,
    PREMIUM_TRACK,
    TIMEZONE,
    VOTE_FOOTER,
    VOTE_TEXTS,
    Layer,
    ObjectiveKind,
    Outcome,
    Phase,
    TrackReward,
)
from asterion.domain.world_events import ENTRY_WINDOW, EVENT_TIMEZONE

_IMAGE = "menu"

_ERRORS = {
    "no_character": "Crie um personagem para acompanhar a Crônica.",
    "nothing_to_claim": "Ainda não há Marco para resgatar.",
    "chronicle_closed": "A Crônica não está aceitando progresso agora.",
    "chronicle_chapter_locked": "Este capítulo ainda não foi liberado.",
    "chronicle_already_concluded": "Você já concluiu este capítulo.",
    "chronicle_objectives_missing": "Ainda faltam objetivos obrigatórios deste capítulo.",
    "chronicle_gate": "Conclua P1 · Vozes na Estrada para participar da Crônica.",
    "chronicle_claim_closed": "O período de resgate da Trilha está encerrado.",
    "chronicle_vote_closed": "A votação não está aberta agora.",
    "chronicle_vote_counting": "A votação principal está sendo apurada. Tente em instantes.",
    "chronicle_vote_ineligible": "Você ainda não pode votar.",
    "chronicle_vote_invalid": "Esta opção não está disponível.",
    "chronicle_unknown": "Este capítulo não existe.",
    "chronicle_not_here": "Vá ao Local indicado na Crônica para fazer isso.",
    "chronicle_level": "Seu nível ainda não permite este Encontro.",
    "chronicle_busy": "Termine a atividade em andamento antes de enfrentar o Eco.",
    "chronicle_repeat_limit": "O Eco não rende mais pontos de Trilha hoje. Volte amanhã.",
    "chronicle_fight_over": "Este combate já terminou.",
    "group_participant_busy": "Alguém do Grupo já está em outra atividade.",
    "group_not_in_group": "Você precisa estar num Grupo para enfrentar em Grupo.",
    "group_proposer_ineligible": "Você não pode propor este Encontro agora.",
    "group_empty_eligible_roster": "Ninguém do Grupo pode entrar neste Encontro agora.",
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Esta ação não está mais disponível.")


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _when(moment: datetime) -> str:
    return moment.astimezone(TIMEZONE).strftime("%d/%m às %H:%M")


_BACK = [_button("← Crônica", "cr:root")]


def reward_text(reward: TrackReward) -> str:
    parts = []
    if reward.crowns:
        parts.append(f"{reward.crowns} Coroas")
    if reward.basics:
        parts.append(f"{reward.basics} Materiais Básicos")
    if reward.fragments:
        parts.append(f"{reward.fragments} Fragmentos")
    if reward.cosmetic_id:
        cosmetic = CHRONICLE_COSMETICS_BY_ID[reward.cosmetic_id]
        noun = {"title": "Título", "frame": "Moldura", "appearance": "Aparência"}
        parts.append(f"{noun[cosmetic.cosmetic_type]} {cosmetic.name}")
    return " + ".join(parts)


# ------------------------------------------------------------------- Crônica


# Draft text (HANDOFF.md): the proposal §9 gives the rule, not the line.
ARCHIVED_TEXT = (
    "📦 Crônica Arquivada. A Crônica terminou, mas a história continua aqui: os capítulos "
    "podem ser jogados sozinho, sem pontos, voto ou recompensa, para recuperar a história "
    "e o Códice."
)


def render_calendar(view: ChronicleView, now: datetime) -> Screen:
    """Menu → Calendário: cycles, times, Nova Vigília and the Crônica (GDD §34, §37.2)."""
    lines = [
        "🗓️ Calendário",
        "",
        f"🌅 Reset diário · {_when(next_daily_reset(now))}",
        f"🛡️ Nova Vigília · {_when(next_new_vigil(now))}",
        "",
        f"🌌 Crônica I · {CHRONICLE_NAME}",
    ]
    if view.phase is Phase.UNSCHEDULED or view.calendar is None:
        lines.append("Sem data ainda. Ela abre quando o Dia 1 for anunciado.")
    elif view.phase is Phase.SCHEDULED:
        lines.append(f"Começa em {_when(view.calendar.starts_at)}.")
    elif view.phase is Phase.ACTIVE:
        lines.append(f"Em andamento · termina em {_when(view.calendar.end_at)}.")
    elif view.phase in (Phase.CLOSING, Phase.RESCUE):
        lines.append(f"Encerrada · resgate da Trilha até {_when(view.calendar.rescue_ends_at)}.")
    else:
        lines.append("Arquivada.")
    lines.extend(["", "Horários de Brasília (America/Sao_Paulo)."])
    rows = [[_button("Crônica", "cr:root")], [_button("← Menu", "menu:back")]]
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def render_chronicle(view: ChronicleView) -> Screen:
    lines = [f"🌌 Crônica I · {CHRONICLE_NAME}", ""]
    rows: list[list[InlineKeyboardButton]] = []
    if view.phase is Phase.UNSCHEDULED or view.calendar is None:
        lines.append("A Crônica ainda não tem data. Ela abre quando o Dia 1 for anunciado.")
    elif view.phase is Phase.SCHEDULED:
        lines.append(f"Começa em {_when(view.calendar.starts_at)}.")
    else:
        lines.extend([OPENING_TEXT, ""])
        if view.phase is Phase.ACTIVE:
            lines.append(
                f"Capítulos liberados · {view.chapters_open}/{CHAPTER_COUNT} · "
                f"termina em {_when(view.calendar.end_at)}"
            )
        elif view.phase in (Phase.CLOSING, Phase.RESCUE):
            lines.append(
                f"A Crônica terminou. Resgate da Trilha até {_when(view.calendar.rescue_ends_at)}."
            )
        else:
            lines.append(ARCHIVED_TEXT)
        if not view.gate_ok and view.phase is Phase.ACTIVE:
            lines.extend(["", "Conclua P1 · Vozes na Estrada para participar."])
        for chapter in view.chapters:
            mark = "✅" if chapter.concluded else "▫️"
            label = f"{mark} {chapter.number} · {chapter.title}"
            rows.append([_button(label, f"cr:ch:{chapter.number}")])
        if view.outcome is not None:
            lines.extend(["", "📜 O Que Foi Respondido", EPILOGUES[view.outcome]])
        if view.vote is not None and view.vote.round is not None:
            rows.append([_button("🗳️ Votação final", "cr:vote")])
    lines.extend(
        [
            "",
            f"🧭 Trilha · {view.points} pontos · Marco {view.milestones}/{MILESTONE_COUNT}",
        ]
    )
    if view.claimable:
        lines.append(f"🎁 {view.claimable} recompensa(s) para resgatar")
    rows.append([_button("Trilha da Crônica", "cr:trail")])
    rows.append([_button("← Benefícios", "bn:root")])
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def _objective_line(item, archived: bool = False) -> str:
    objective = item.objective
    if item.done:
        mark = "✅"
    elif item.level_locked:
        mark = f"⏳ Requer Nv. {objective.min_level} ·"
    else:
        mark = "▫️"
    optional = "" if objective.required else " · opcional"
    points = "" if archived else f" · {objective.points} pts"
    return f"{mark} {objective.title} · {KIND_LABELS[objective.kind]}{optional}{points}"



# Started elsewhere: Desbravar has its own button in the Local, a Masmorra its own menu.
_NO_BUTTON = (ObjectiveKind.DESBRAVAR, ObjectiveKind.DUNGEON, ObjectiveKind.EVENT)


def _action_data(action: ActionView) -> str:
    objective = action.objective
    verb = "talk" if objective.kind is ObjectiveKind.NPC else "read"
    return f"cr:{verb}:{objective.chapter}:{objective.objective_id[-2:].lstrip('0')}"


def _action_button(action: ActionView) -> list[InlineKeyboardButton]:
    if action.objective.kind is ObjectiveKind.NPC:
        return [_button(f"💬 Falar com {action.npc}", _action_data(action))]
    return [_button(f"🔎 {action.objective.title}", _action_data(action))]


_WEEKDAYS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")


def _event_when(action: ActionView) -> str:
    local = action.event_at.astimezone(EVENT_TIMEZONE)
    if action.event_live:
        closes = (action.event_at + ENTRY_WINDOW).astimezone(EVENT_TIMEZONE)
        return f"acontecendo agora, entrada até {closes:%H:%M}"
    return f"{_WEEKDAYS[local.weekday()]} {local:%d/%m} às {local:%H:%M}"


def _action_line(action: ActionView) -> str:
    title = action.objective.title
    if action.objective.kind is ObjectiveKind.EVENT:
        return f"📍 {title} · {_event_when(action)} · Eventos Mundiais, versão {action.location}"
    if action.objective.kind is ObjectiveKind.NPC:
        return f"📍 {title} · {action.npc} · {action.location}"
    if action.objective.kind is ObjectiveKind.EVIDENCE:
        return f"📍 {title} · {action.points_done}/{action.points_total} · {action.location}"
    if action.objective.kind is ObjectiveKind.DUNGEON:
        if not action.dungeons:
            return f"📍 {title} · sem Masmorra liberada: Desbravar em {action.location}"
        if not action.focus:
            return f"📍 {title} · qualquer Masmorra com Estável liberada"
        return f"📍 {title} · Masmorra: {' ou '.join(action.dungeons)}"
    return f"📍 {title} · Desbravar em {action.location}"


def _fight_listed(item: EncounterActionView) -> bool:
    """Pending Encontros, and won ones while the Eco still pays Trilha today."""
    return not item.level_locked and (not item.won or item.repeat_open)


def _encounter_line(item: EncounterActionView) -> str:
    name = item.encounter.creature.name
    if item.won:
        return f"🔁 {name} · Enfrentar o Eco de novo em {item.location}"
    return f"📍 {item.objective.title} · {name} · {item.location}"


def _encounter_button(item: EncounterActionView) -> list[InlineKeyboardButton]:
    objective = item.objective
    data = f"cr:fight:{objective.chapter}:{objective.objective_id[-2:].lstrip('0')}"
    name = item.encounter.creature.name
    row = (
        [_button(f"🔁 Enfrentar o Eco de novo · {name}", data)]
        if item.won
        else [_button(f"⚔️ Enfrentar · {name}", data)]
    )
    if item.in_group:
        row.append(_button("👥 Em Grupo", data.replace("cr:fight:", "cr:gfight:", 1)))
    return row


def render_chapter(
    view: ChronicleView,
    chapter: ChapterView,
    actions: tuple[ActionView, ...] = (),
    encounters: tuple[EncounterActionView, ...] = (),
) -> Screen:
    lines = [f"🌌 Capítulo {chapter.number} · {chapter.title}", "", chapter.summary, ""]
    archived = view.phase is Phase.ARCHIVED
    lines.extend(_objective_line(item, archived) for item in chapter.objectives)
    points = "" if archived else " · 250 pts"
    lines.append(f"{'✅' if chapter.concluded else '▫️'} Conclusão do capítulo{points}")
    fights = tuple(item for item in encounters if _fight_listed(item))
    if actions or fights:
        lines.append("")
        lines.extend(_action_line(item) for item in actions)
        lines.extend(_encounter_line(item) for item in fights)
    if chapter.concluded:
        lines.extend(["", chapter.conclusion])
    rows = [
        _action_button(item)
        for item in actions
        if item.here and item.objective.kind not in _NO_BUTTON
    ]
    rows.extend(_encounter_button(item) for item in fights if item.here)
    if chapter.can_conclude:
        rows.append([_button("Concluir capítulo", f"cr:conclude:{chapter.number}")])
    rows.append(_BACK)
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def _back_to_chapter(chapter: int) -> list[InlineKeyboardButton]:
    return [_button(f"← Capítulo {chapter}", f"cr:ch:{chapter}")]


def render_here(
    actions: tuple[ActionView, ...], encounters: tuple[EncounterActionView, ...] = ()
) -> Screen:
    lines = ["🌌 Crônica · Neste Local", ""]
    if not actions and not encounters:
        lines.append("Nada da Crônica para fazer aqui agora.")
    lines.extend(_action_line(item) for item in actions)
    lines.extend(_encounter_line(item) for item in encounters)
    rows = [_action_button(item) for item in actions]
    rows.extend(_encounter_button(item) for item in encounters)
    rows.append([_button("🌌 Crônica", "cr:root")])
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def render_talk(view: TalkView) -> Screen:
    lines = [f"💬 {view.objective.title}", "", view.text]
    if view.completed_now:
        lines.extend(["", f"✅ {view.objective.title} concluído"])
    rows = [_back_to_chapter(view.objective.chapter)]
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def render_readings(view: ReadingsView) -> Screen:
    done = sum(item.done for item in view.points)
    lines = [f"🔎 {view.objective.title} · {done}/{len(view.points)}", f"📍 {view.location}", ""]
    if view.last_text:
        lines.extend([view.last_text, ""])
    if view.completed_now:
        lines.extend([f"✅ {view.objective.title} concluído", ""])
    lines.extend(f"{'✅' if item.done else '⚪'} {item.label}" for item in view.points)
    objective = view.objective
    slot = objective.objective_id[-2:].lstrip("0")
    rows = [
        [_button(f"Examinar · {item.label}", f"cr:read:{objective.chapter}:{slot}:{item.point_id}")]
        for item in view.points
        if not item.done
    ]
    rows.append(_back_to_chapter(objective.chapter))
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


# ------------------------------------------------------------------ Encontros


def render_encounter(view: CombatView | EncounterResultView) -> Screen:
    """The fight itself, or its result: only XP, Trilha, Bestiário and Feito."""
    if isinstance(view, CombatView):
        return render_combat(view)
    name = view.encounter.creature.name
    back = _keyboard([_back_to_chapter(view.objective.chapter)])
    if view.helper:
        outcome = "Vitória" if view.victory else "Derrota"
        lines = [
            f"{'🏆' if view.victory else '💀'} {name} · Nv.{view.enemy_level} · {outcome}",
            "",
            "Você lutou como Ajudante: este Encontro não conta para a sua Crônica.",
        ]
        if view.recovery_location:
            lines.append(f"🔥 Você desperta em {view.recovery_location}.")
        return Screen("\n".join(lines), _IMAGE, back)
    if not view.victory:
        lines = [
            f"💀 {name} · Nv.{view.enemy_level}",
            "",
            "O Eco continua onde estava. Você não perdeu nada.",
        ]
        if view.recovery_location:
            lines.append(f"🔥 Você desperta em {view.recovery_location}.")
        lines.append("Enfrente-o de novo quando quiser.")
        return Screen("\n".join(lines), _IMAGE, back)
    lines = [f"🏆 {name} · Nv.{view.enemy_level} · Vitória", ""]
    if view.repeat:
        if view.trail_points:
            lines.append(f"🧭 Trilha da Crônica · +{view.trail_points} pontos")
        else:
            lines.append("🧭 Trilha da Crônica · limite de repetíveis já atingido")
    else:
        if view.objective_completed:
            lines.append(f"✅ {view.objective.title} concluído · {view.objective.points} pts")
        if view.xp:
            lines.append(f"✨ +{view.xp} XP")
        if view.feat:
            lines.append(f"🎖️ Feito · {view.feat}")
    if view.bestiary_stage:
        lines.append(f"🐾 Bestiário · {name} · {view.bestiary_stage}")
    return Screen("\n".join(lines), _IMAGE, back)


# ----------------------------------------------------------------------- vote


def render_vote(view: ChronicleView, notice: str | None = None) -> Screen:
    vote = view.vote
    lines = ["🗳️ A Resposta · Votação final", ""]
    if notice:
        lines.extend([notice, ""])
    rows: list[list[InlineKeyboardButton]] = []
    if vote is None or vote.round is None:
        lines.append("A votação não está aberta agora.")
        rows.append(_BACK)
        return Screen("\n".join(lines), _IMAGE, _keyboard(rows))
    if vote.round == "runoff":
        lines.extend(["Desempate de 24h entre as opções empatadas.", ""])
    if vote.closes_at is not None:
        lines.append(f"Fecha em {_when(vote.closes_at)}.")
    if not vote.eligible:
        lines.append(
            f"Para votar: 4 de 8 capítulos concluídos ({vote.chapters_concluded}/4) e "
            f"1 objetivo da fase final ({min(vote.final_objectives, 1)}/1)."
        )
    lines.append("")
    for option in vote.options:
        texts = VOTE_TEXTS[option]
        chosen = " · seu voto" if vote.choice is option else ""
        lines.append(f"{'☑️' if chosen else '▫️'} {texts.label}{chosen}")
        lines.append(texts.text)
        if Layer.C3 in view.layers:
            lines.append(texts.c3)
        lines.append("")
        if vote.eligible:
            rows.append([_button(f"Votar · {texts.label}", f"cr:vote:{option.value}")])
    lines.append(VOTE_FOOTER)
    rows.append(_BACK)
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


def vote_notice(option: Outcome) -> str:
    return f"Voto registrado: {VOTE_TEXTS[option].label}. Você pode mudar até o fechamento."


# --------------------------------------------------------------------- Trilha


def render_trail(view: TrackView, result: ClaimResult | None = None) -> Screen:
    lines = ["🧭 Trilha da Crônica", ""]
    if result is not None:
        lines.append(f"Resgatado: {len(result.milestones)} recompensa(s).")
        lines.extend(granted_lines(result.granted))
        lines.extend(f"🎖️ {name}" for name in result.cosmetics)
        lines.append("")
    lines.append(f"Pontos · {view.points}/{MAX_POINTS} · Marco {view.milestones}/{MILESTONE_COUNT}")
    lines.append(f"Repetíveis · {view.repeatable_points}/{view.repeatable_cap}")
    lines.append(f"Passe da Crônica · {'ativo' if view.premium else 'inativo'}")
    upcoming = [m for m in sorted(FREE_TRACK) if m > view.milestones][:3]
    if upcoming:
        lines.extend(["", "Próximos Marcos Livres"])
        lines.extend(
            f"▫️ Marco {m} · {m * MILESTONE_STEP} pts · {reward_text(FREE_TRACK[m])}"
            for m in upcoming
        )
    premium = [m for m in sorted(PREMIUM_TRACK) if m > view.milestones][:2]
    if premium:
        lines.extend(["", "Próximos Marcos Premium"])
        lines.extend(f"▫️ Marco {m} · {reward_text(PREMIUM_TRACK[m])}" for m in premium)
    if view.claimable:
        lines.extend(["", f"🎁 Disponíveis para resgate: {len(view.claimable)}"])
    rows = []
    if view.claimable and view.can_claim:
        rows.append([_button("Resgatar Disponíveis", "cr:trail:claim")])
    rows.append([_button("🌌 Crônica", "cr:root")])
    rows.append([_button("← Benefícios", "bn:root")])
    return Screen("\n".join(lines), _IMAGE, _keyboard(rows))


# ------------------------------------------------------------ Salão da Vigília


def _hall_line(row: HallRow, *, arena: bool) -> str:
    if arena:
        reward = f" · 🎁 {row.reward_tier}" if row.reward_tier else ""
        return f"{row.position}. {row.name} · {row.elo} · {row.rating} Renome{reward}"
    tier = _GUILD_REWARD_LABELS.get(row.reward_tier or "")
    reward = f" · 🎁 {tier}" if tier else " · 🎁 Elegível" if row.reward_eligible else ""
    return f"{row.position}. {row.name} · {row.points} pts · {row.matches} batalhas{reward}"


# Batalha de Guildas reward tiers (domain/guild_battle.py) and what each grants.
_GUILD_REWARD_LABELS = {
    "champion": "Campeã: Campeão da Vigília, Estandarte Invicto",
    "podium": "Pódio: Linha que Não Cedeu",
    "top10": "Top 10: Frente Firme",
    "veteran": "Veterano das Frentes",
}


def render_hall(view: HallView) -> Screen:
    lines = ["🏛️ Salão da Vigília", ""]
    if view.chronicle_id is None:
        lines.append("Nenhuma Crônica foi encerrada ainda.")
    else:
        lines.extend([f"Crônica I · {CHRONICLE_NAME}", "", "⚔️ Arena da Vigília"])
        lines.extend(_hall_line(row, arena=True) for row in view.arena)
        if not view.arena:
            lines.append("Ninguém completou a Colocação neste ciclo.")
        if view.own_arena is not None:
            lines.extend(["", "Sua posição", _hall_line(view.own_arena, arena=True)])
        lines.extend(["", "🛡️ Batalha de Guildas"])
        lines.extend(_hall_line(row, arena=False) for row in view.guilds)
        if not view.guilds:
            lines.append("Nenhuma Guilda batalhou neste ciclo.")
    return Screen(
        "\n".join(lines),
        _IMAGE,
        _keyboard([[_button("← Classificação da Vigília", "pvp:rank")]]),
    )


def render_group_proposal(chapter: int) -> Screen:
    """The Confirmação de Entrada went to the Group (GDD §51.2)."""
    lines = [
        "👥 Confirmação de Entrada enviada ao Grupo.",
        "",
        "Cada membro confirma em 👥 Grupo em até 60 segundos. Depois, inicie o Encontro "
        "por lá. Quem não estiver no mesmo Local fica de fora; quem já venceu ou não "
        "tem este objetivo entra como Ajudante e não conta.",
    ]
    return Screen("\n".join(lines), _IMAGE, _keyboard([_back_to_chapter(chapter)]))
