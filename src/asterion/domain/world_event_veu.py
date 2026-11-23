"""A Ruptura do Véu: estrutura do Evento Mundial (domínio puro, sem banco).

Arquitetura da fonte: ``EVENTO MUNDIAL → FASE → NÚCLEO → objetivo/combate → estado global``.
Este módulo não toca o motor de combate, a Crônica nem o catálogo antigo de
``domain/world_events.py``; reaproveita dele só as constantes e funções que a fonte repete
(agenda, janelas, scaling, elegibilidade, recompensa).

Regras que a fonte NÃO define ficam em ``BLOCKED_RULES`` e não têm comportamento aqui.
"""

from __future__ import annotations

import hashlib
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from asterion.domain.veu_bestiary import EVENT_REFERENCE_LEVEL, VEU_CREATURES  # noqa: F401
from asterion.domain.world_events import (  # noqa: F401  (re-exportados de propósito)
    DEADLINE,
    ENTRY_WINDOW,
    EVENT_TIMEZONE,
    PARTICIPANT_CAP,
    REENTRY_DELAY,
    SCHEDULE_TIMES,
    SCHEDULE_WEEKDAYS,
    VIGOR_COST,
    contribution_points,
    is_eligible,
    next_slot,
    occurrence_key,
    phase_scale,
    reward_bundle,
    reward_xp,
)

EVENT_ID = "a_ruptura_do_veu"
EVENT_NAME = "A Ruptura do Véu"
SCENARIO_NAME = "Margem da Ruptura"  # nome provisório na fonte (§2.2)
CODEX_KEY = "codex.world_event.a_ruptura_do_veu"
RULESET = "world_event_veu_v1"

# Override exclusivo do Evento Mundial. Não altera PvE (180s), PvP (90s) nem Guilda (60s).
DECISION_WINDOW = timedelta(seconds=10)

PHASE_COUNT = 3
NUCLEI_PER_PHASE = 3
PHASE_ADVANCE_RESOLVED = 2  # Fase I→II e II→III: 2 de 3 Núcleos resolvidos
AFK_LIMIT = 3


# --------------------------------------------------------------------- estados


class EventState(StrEnum):
    """Estados globais (§3.4)."""

    AGENDADO = "AGENDADO"
    ABERTO = "ABERTO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    FRACASSADO = "FRACASSADO"
    ENCERRADO = "ENCERRADO"


EVENT_TRANSITIONS: dict[EventState, frozenset[EventState]] = {
    EventState.AGENDADO: frozenset({EventState.ABERTO}),
    EventState.ABERTO: frozenset({EventState.EM_ANDAMENTO}),
    EventState.EM_ANDAMENTO: frozenset(
        {EventState.CONCLUIDO, EventState.FRACASSADO, EventState.ENCERRADO}
    ),
    EventState.CONCLUIDO: frozenset({EventState.ENCERRADO}),
    EventState.FRACASSADO: frozenset({EventState.ENCERRADO}),
    EventState.ENCERRADO: frozenset(),
}


class NucleusState(StrEnum):
    """Estados de Núcleo (§15)."""

    ATIVA = "ATIVA"
    RESOLVENDO = "RESOLVENDO"
    RESOLVIDA = "RESOLVIDA"
    COLAPSADA = "COLAPSADA"
    SUBSTITUIDA = "SUBSTITUIDA"


# §61: COLAPSADA existe na arquitetura, mas a primeira ocorrência não a usa.
# A fonte não define as transições entre estados de Núcleo: ver ``BLOCKED_RULES``.
UNUSED_IN_FIRST_OCCURRENCE = frozenset({NucleusState.COLAPSADA})


def nucleus_state_used_in_first_occurrence(state: NucleusState) -> bool:
    return state not in UNUSED_IN_FIRST_OCCURRENCE


class RoundState(StrEnum):
    """Rodada: OPEN → RESOLVING → RESOLVED, uma única vez (§30.3)."""

    OPEN = "OPEN"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"


ROUND_TRANSITIONS: dict[RoundState, frozenset[RoundState]] = {
    RoundState.OPEN: frozenset({RoundState.RESOLVING}),
    RoundState.RESOLVING: frozenset({RoundState.RESOLVED}),
    RoundState.RESOLVED: frozenset(),
}


class InvalidTransition(ValueError):
    pass


def _move(table, current, target, label: str):
    if target not in table[current]:
        raise InvalidTransition(f"{label}: {current} -> {target}")
    return target


def transition_event(current: EventState, target: EventState) -> EventState:
    return _move(EVENT_TRANSITIONS, current, target, "event")


def transition_round(current: RoundState, target: RoundState) -> RoundState:
    return _move(ROUND_TRANSITIONS, current, target, "round")


def begin_round_resolution(state: RoundState) -> tuple[RoundState, bool]:
    """Idempotente: só a primeira chamada ganha o direito de resolver a rodada."""
    if state is RoundState.OPEN:
        return RoundState.RESOLVING, True
    return state, False


def nucleus_accepts_players(state: NucleusState) -> bool:
    return state is NucleusState.ATIVA


def nucleus_accepts_rounds(state: NucleusState) -> bool:
    return state is NucleusState.ATIVA


def nucleus_removes_participants(state: NucleusState) -> bool:
    """§14.6: fora de ATIVA (e de RESOLVENDO, estado curto) os participantes saem sem punição."""
    return state in {
        NucleusState.RESOLVIDA,
        NucleusState.COLAPSADA,
        NucleusState.SUBSTITUIDA,
    }


# ------------------------------------------------------------ fases e Núcleos


@dataclass(frozen=True, slots=True)
class NucleusDefinition:
    key: str  # A..I
    phase: int
    name: str
    objective: str  # texto da fonte (§9–§11)
    creature_codes: tuple[str, ...]
    principal: str | None = None  # só onde a fonte diz "criatura principal"
    support: tuple[str, ...] = ()  # só onde a fonte diz "apoio"
    independent_targets: bool = False  # Núcleo F: dois alvos independentes


NUCLEI: tuple[NucleusDefinition, ...] = (
    NucleusDefinition(
        "A", 1, "O Primeiro Rasgo", "estabilizar uma fissura menor",
        ("VEU-01", "VEU-02", "VEU-03"),
    ),
    NucleusDefinition(
        "B", 1, "A Margem Viva", "impedir que a matéria deformada avance",
        ("VEU-04", "VEU-05", "VEU-06"),
    ),
    NucleusDefinition(
        "C", 1, "A Boca Aberta", "conter uma abertura maior", ("VEU-07", "VEU-08")
    ),
    NucleusDefinition(
        "D", 2, "A Coluna", "derrubar uma manifestação vertical", ("VEU-09", "VEU-13"),
        principal="VEU-09", support=("VEU-13",),
    ),
    NucleusDefinition(
        "E", 2, "O Interior", "romper a casca de uma manifestação", ("VEU-10", "VEU-11"),
        principal="VEU-10", support=("VEU-11",),
    ),
    NucleusDefinition(
        "F", 2, "O Amontoado", "impedir que a massa alcance o centro da ruptura",
        ("VEU-12", "VEU-14"), independent_targets=True,
    ),
    NucleusDefinition(
        "G", 3, "O Portador", "impedir que a criatura alcance a borda central", ("VEU-15",)
    ),
    NucleusDefinition(
        "H", 3, "A Ausência", "interromper a manifestação antes que ela se torne estável",
        ("VEU-16", "VEU-17"),
    ),
    NucleusDefinition("I", 3, "O Centro da Ruptura", "derrotar o Chefe", ("VEU-18",)),
)

NUCLEI_BY_KEY = {nucleus.key: nucleus for nucleus in NUCLEI}
FINAL_NUCLEUS_KEY = "I"


def nuclei_of_phase(phase: int) -> tuple[NucleusDefinition, ...]:
    if not 1 <= phase <= PHASE_COUNT:
        raise ValueError("phase must be between 1 and 3")
    return tuple(nucleus for nucleus in NUCLEI if nucleus.phase == phase)


def phase_should_advance(phase: int, resolved_keys: Collection[str]) -> bool:
    """§12 e checklist: Fase I→II e II→III com 2 de 3 Núcleos da fase resolvidos.

    Sem tempo mínimo. A Fase III não avança: a vitória é o Núcleo I (``event_completed``).
    O destino dos Núcleos remanescentes ao avançar NÃO é definido pela fonte (ver
    ``BLOCKED_RULES``) e não é tratado aqui.
    """
    if phase >= PHASE_COUNT:
        return False
    keys = {nucleus.key for nucleus in nuclei_of_phase(phase)}
    return len(keys & set(resolved_keys)) >= PHASE_ADVANCE_RESOLVED


def event_completed(resolved_keys: Collection[str]) -> bool:
    """§11/checklist: a vitória depende do Núcleo I, não da resolução dos 9 Núcleos."""
    return FINAL_NUCLEUS_KEY in set(resolved_keys)


# ----------------------------------------------------------- N global por fase


@dataclass(frozen=True, slots=True)
class ParticipantRecord:
    """O mínimo que o N válido precisa saber de um participante (§12.2)."""

    character_id: UUID
    voluntary_exit: bool = False
    reentry_available_at: datetime | None = None  # derrota/cooldown em curso


@dataclass(frozen=True, slots=True)
class PhaseSnapshot:
    """Único N da fase, compartilhado por todos os Núcleos (§8.4); congelado."""

    phase: int
    n: int  # válidos, limitado a PARTICIPANT_CAP


def valid_participant_count(records: Iterable[ParticipantRecord], now: datetime) -> int:
    """§12.2: sai quem encerrou a participação; fica de fora quem está em derrota/cooldown.

    Ser removido de um Núcleo por AFK não é sair do Evento: não há campo para isso aqui.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return sum(
        1
        for record in records
        if not record.voluntary_exit
        and (record.reentry_available_at is None or record.reentry_available_at <= now)
    )


def freeze_phase_snapshot(
    phase: int, records: Iterable[ParticipantRecord], now: datetime
) -> PhaseSnapshot:
    if not 1 <= phase <= PHASE_COUNT:
        raise ValueError("phase must be between 1 and 3")
    count = valid_participant_count(records, now)
    return PhaseSnapshot(phase, min(count, PARTICIPANT_CAP))


# ------------------------------------------------------------------------- AFK


@dataclass(frozen=True, slots=True)
class AfkState:
    streak: int
    removed: bool

    @property
    def label(self) -> str | None:
        return f"AFK {self.streak}/{AFK_LIMIT}" if self.streak else None


def afk_after_round(streak: int, acted: bool) -> AfkState:
    """1 rodada sem ação = 1/3; 2 seguidas = 2/3; 3 seguidas = remoção do Núcleo.

    Ação válida zera o contador. A remoção não expulsa o jogador do Evento (§14.5).
    """
    if streak < 0:
        raise ValueError("streak cannot be negative")
    if acted:
        return AfkState(0, False)
    streak += 1
    return AfkState(min(streak, AFK_LIMIT), streak >= AFK_LIMIT)


# ----------------------------------------------------------- troca de Núcleo

# §14.2: depois de trocar, o jogador fica 1 rodada sem poder agir na nova Núcleo. A fonte
# não diz se essa rodada é a aberta no destino ou a próxima: ver ``BLOCKED_RULES``.
SWITCH_BLOCKED_ROUNDS = 1
SWITCH_ALLOWS_IMMEDIATE_ACTION = False


# ------------------------------------------------------ determinismo / idempotência


def action_id(
    occurrence_key_: str, nucleus_key: str, round_number: int, character_id: UUID
) -> UUID:
    """Mesma ação da mesma rodada, mesmo ID: reenvio e reconnect não duplicam (§30.2)."""
    name = f"{EVENT_ID}|{occurrence_key_}|{nucleus_key}|{round_number}|{character_id}"
    return uuid5(NAMESPACE_URL, name)


def enemy_seed(occurrence_key_: str, nucleus_key: str, round_number: int) -> int:
    """Semente do desempate da IA: igual em qualquer processo (§17.2)."""
    name = f"{EVENT_ID}|{occurrence_key_}|{nucleus_key}|{round_number}"
    return int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "big")


def decision_deadline(opened_at: datetime) -> datetime:
    return opened_at + DECISION_WINDOW


def is_scheduled_slot(slot: datetime) -> bool:
    local = slot.astimezone(EVENT_TIMEZONE)
    return (
        local.weekday() in SCHEDULE_WEEKDAYS
        and local.timetz().replace(tzinfo=None) in SCHEDULE_TIMES
    )


# ------------------------------------------------------------------- bloqueios

BLOCKED_RULES: dict[str, str] = {
    "contextual_actions": "Estabilizar/Romper/Interromper: a fonte só dá exemplos (§16.3).",
    "nucleus_a_objective": "Núcleo A: 'manter a manifestação abaixo do limite' sem regra.",
    "nucleus_b_structural_objective": "Núcleo B: objetivo estrutural opcional sem regra.",
    "recent_contribution_priority": "Tecelão de Ossos: 'maior contribuição recente' indefinida.",
    "barrier_duration": "Barreiras dos kits não têm duração; sem duração o motor não concede.",
    "remaining_nucleus_on_phase_change": "Destino do Núcleo não resolvido na troca de fase.",
    "archetype_engine_profile": "Resistente, Técnico, Suporte e Eq./Controlador sem perfil.",
    "nucleus_state_transitions": (
        "Arestas entre ATIVA/RESOLVENDO/RESOLVIDA/SUBSTITUIDA não definidas pela fonte; "
        "inclui se RESOLVENDO volta a ATIVA e se RESOLVENDO já remove participantes (§14.6)."
    ),
    "boss_form_70_boundary": (
        "VEU-18: a fonte dá '100%→70%' e '70%→35%' sem dizer a que forma pertence 70%."
    ),
    "switch_blocked_round_instant": (
        "Troca de Núcleo: não definido se a rodada sem agir é a aberta no destino ou a próxima."
    ),
}


def _check_catalog() -> None:
    codes = {creature.code for creature in VEU_CREATURES}
    used = [code for nucleus in NUCLEI for code in nucleus.creature_codes]
    if set(used) != codes or len(used) != len(codes):
        raise ValueError("every VEU creature belongs to exactly one Núcleo")


_check_catalog()
