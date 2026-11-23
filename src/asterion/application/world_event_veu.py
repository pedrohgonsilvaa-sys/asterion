"""A Ruptura do Véu: orquestração (camada Application, Etapa 4).

Liga o domínio (``domain/world_event_veu.py``, ``domain/veu_bestiary.py``) às tabelas
``veu_event_*``. Não toca o modelo regional antigo (``application/world_events.py``), a
Crônica, o motor de combate, o scheduler, a UI nem os handlers.

O que este módulo NÃO decide (``BLOCKED_RULES`` do domínio e lacunas da fonte):

- O que torna um Núcleo RESOLVIDA (objetivo/combate) e a aresta de estado de Núcleo que
  isso exige. Aqui só se *lê* RESOLVIDA (``reevaluate_progress``); quem escreve é a
  integração de combate. ``nucleus_state_transitions``.
- Destino dos Núcleos remanescentes ao trocar de fase: ficam como estão.
- Troca de Núcleo (``switch_blocked_round_instant``): só a primeira entrada é aceita.
- Barreira (``barrier_duration``): decisão de inimigo com Barreira é recusada.
- Escolha da ação do inimigo: o chamador informa; o serviço valida contra o kit e grava
  junto da semente determinística.
- O que é ação "significativa"/"contribuição maior": nada é marcado, e elegibilidade e
  recompensa não são calculadas aqui.
- Custo de Vigor e reentrada após derrota: fora desta etapa.
"""

from __future__ import annotations

import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.engagement import grant_bundle
from asterion.application.progression import consolidate_character_level, level_xp
from asterion.application.vigor import reconcile_character_vigor
from asterion.domain import veu_combat as vc
from asterion.domain import world_event_veu as ev
from asterion.domain.combat_math import CombatStats
from asterion.domain.veu_bestiary import ActionKind, creature, creature_stats
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    VeuEventAction,
    VeuEventEnemyDecision,
    VeuEventNucleus,
    VeuEventOccurrence,
    VeuEventParticipant,
    VeuEventPhaseSnapshot,
    VeuEventRound,
)

ACTION_TYPES = ("attack", "defend", "art")


class VeuEventError(ValueError):
    """Ação inválida para o estado revalidado."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class BlockedRuleError(VeuEventError):
    """A fonte não define a regra que esta operação exigiria (ver ``BLOCKED_RULES``)."""


@dataclass(frozen=True, slots=True)
class OccurrenceView:
    id: UUID
    server_id: str
    occurrence_key: str
    state: str
    phase: int
    state_version: int
    nuclei: dict[str, str]  # chave -> estado
    snapshots: dict[int, int]  # fase -> N congelado
    scheduled_at: datetime | None = None
    deadline_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ParticipantView:
    character_id: UUID
    current_nucleus: str | None
    afk_streak: int
    afk_label: str | None
    nucleus_removed: bool
    voluntary_exit: bool
    phases: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class RoundView:
    id: UUID
    nucleus_key: str
    round_number: int
    state: str
    opened_at: datetime
    decision_deadline: datetime
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class ActionView:
    id: UUID
    round_id: UUID
    character_id: UUID
    action_type: str
    art_slot: int | None
    target_ref: str | None
    valid: bool | None
    created: bool


@dataclass(frozen=True, slots=True)
class DecisionView:
    round_id: UUID
    enemy_key: str
    action_key: str
    target_ids: tuple[str, ...]
    telegraph_key: str | None
    seed: int
    created: bool


@dataclass(frozen=True, slots=True)
class SettlementView:
    occurrence_id: UUID
    state: str
    participants: int
    rewarded: int


@dataclass(frozen=True, slots=True)
class ResolutionView:
    round_id: UUID
    resolved_now: bool  # False: já estava resolvida; nada foi refeito
    afk_streaks: dict[UUID, int]
    removed: tuple[UUID, ...]


def _utc(now: datetime | None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return current.astimezone(UTC)


def _event_move(current: str, target: ev.EventState) -> str:
    try:
        return ev.transition_event(ev.EventState(current), target).value
    except ev.InvalidTransition as error:
        raise VeuEventError("invalid_transition") from error


@dataclass(frozen=True, slots=True)
class RoundInputs:
    """O que o motor mediu sobre o estado inicial da rodada."""

    intents: list[vc.PlayerIntent]
    players: dict[UUID, vc.PlayerUnit]


class RoundSimulator(Protocol):
    async def prepare(
        self,
        session: AsyncSession,
        participants: Sequence[VeuEventParticipant],
        actions: Sequence[VeuEventAction],
        enemies: dict[str, vc.EnemyUnit],
        combat_key: str,
    ) -> RoundInputs: ...


class VeuEventService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        simulator: RoundSimulator | None = None,
    ):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id
        # Sem simulador só o AFK é aplicado; com ele a rodada vira combate de verdade.
        self.simulator = simulator

    # ------------------------------------------------------------------ ocorrência

    async def get_or_create_occurrence(self, slot: datetime) -> OccurrenceView:
        """Uma ocorrência global por horário da agenda; chamadas repetidas devolvem a mesma."""
        if slot.tzinfo is None:
            raise ValueError("slot must be timezone-aware")
        if not ev.is_scheduled_slot(slot):
            raise VeuEventError("not_a_scheduled_slot")
        slot = slot.astimezone(UTC)
        async with self.sessions.begin() as session:
            await session.execute(
                insert(VeuEventOccurrence)
                .values(
                    id=uuid4(),
                    server_id=self.server_id,
                    event_id=ev.EVENT_ID,
                    occurrence_key=ev.occurrence_key(slot),
                    state=ev.EventState.AGENDADO.value,
                    phase=1,
                    scheduled_at=slot,
                    entry_closes_at=slot + ev.ENTRY_WINDOW,
                    deadline_at=slot + ev.DEADLINE,
                    state_version=0,
                    ruleset_version=ev.RULESET,
                )
                .on_conflict_do_nothing(constraint="uq_veu_occurrence")
            )
            occurrence = await session.scalar(
                select(VeuEventOccurrence).where(
                    VeuEventOccurrence.server_id == self.server_id,
                    VeuEventOccurrence.occurrence_key == ev.occurrence_key(slot),
                )
            )
            return await self._occurrence_view(session, occurrence)

    async def get_occurrence(self, occurrence_id: UUID) -> OccurrenceView:
        async with self.sessions() as session:
            occurrence = await self._load_occurrence(session, occurrence_id, lock=False)
            return await self._occurrence_view(session, occurrence)

    async def open_occurrence(
        self, occurrence_id: UUID, *, now: datetime | None = None
    ) -> OccurrenceView:
        """AGENDADO -> ABERTO a partir do horário agendado. Idempotente em ABERTO."""
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            if occurrence.state != ev.EventState.ABERTO.value:
                if now < occurrence.scheduled_at:
                    raise VeuEventError("before_scheduled_time")
                occurrence.state = _event_move(occurrence.state, ev.EventState.ABERTO)
                occurrence.opened_at = now
                occurrence.state_version += 1
            return await self._occurrence_view(session, occurrence)

    async def start_occurrence(
        self, occurrence_id: UUID, *, now: datetime | None = None
    ) -> OccurrenceView:
        """ABERTO -> EM_ANDAMENTO: congela o N da Fase I e cria os Núcleos A, B e C.

        A fonte não define o gatilho do início; quem chama decide quando.
        """
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            if occurrence.state != ev.EventState.EM_ANDAMENTO.value:
                occurrence.state = _event_move(occurrence.state, ev.EventState.EM_ANDAMENTO)
                occurrence.started_at = now
                occurrence.phase = 1
                occurrence.state_version += 1
                await self._begin_phase(session, occurrence, 1, now)
            return await self._occurrence_view(session, occurrence)

    async def reevaluate_progress(
        self, occurrence_id: UUID, *, now: datetime | None = None
    ) -> OccurrenceView:
        """Lê os Núcleos RESOLVIDA e aplica o domínio.

        Núcleo I resolvido conclui a ocorrência; senão, 2 de 3 Núcleos da fase avançam a
        fase (novo snapshot e novos 3 Núcleos). Quem sai de um Núcleo RESOLVIDA, sem punição.
        """
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            if occurrence.state != ev.EventState.EM_ANDAMENTO.value:
                return await self._occurrence_view(session, occurrence)
            nuclei = await self._nuclei(session, occurrence.id)
            for nucleus in nuclei.values():
                if ev.nucleus_removes_participants(ev.NucleusState(nucleus.state)):
                    await self._remove_from_nucleus(session, occurrence.id, nucleus.id)
            resolved = {
                key for key, row in nuclei.items() if row.state == ev.NucleusState.RESOLVIDA.value
            }
            if ev.event_completed(resolved):
                occurrence.state = _event_move(occurrence.state, ev.EventState.CONCLUIDO)
                occurrence.state_version += 1
            elif ev.phase_should_advance(occurrence.phase, resolved):
                occurrence.phase += 1
                occurrence.phase_started_at = now
                occurrence.state_version += 1
                await self._begin_phase(session, occurrence, occurrence.phase, now)
            return await self._occurrence_view(session, occurrence)

    # --------------------------------------------------------------- participantes

    async def join(
        self, occurrence_id: UUID, character_id: UUID, *, now: datetime | None = None
    ) -> ParticipantView:
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            character = await session.get(Character, character_id)
            if character is None or character.server_id != self.server_id:
                raise VeuEventError("character_not_found")
            participant = await session.get(VeuEventParticipant, (occurrence.id, character_id))
            if participant is not None:
                if participant.voluntary_exit:
                    raise VeuEventError("participant_left")
                return await self._participant_view(session, participant)
            if occurrence.state not in (
                ev.EventState.ABERTO.value,
                ev.EventState.EM_ANDAMENTO.value,
            ):
                raise VeuEventError("event_not_open")
            if now > occurrence.entry_closes_at:
                raise VeuEventError("entry_window_closed")
            participant = VeuEventParticipant(
                occurrence_id=occurrence.id,
                character_id=character_id,
                joined_at=now,
                voluntary_exit=False,
                afk_streak=0,
                significant_actions=0,
                major_contributions=0,
                phases=[occurrence.phase],
            )
            session.add(participant)
            await session.flush()
            return await self._participant_view(session, participant)

    async def leave_event(
        self, occurrence_id: UUID, character_id: UUID, *, now: datetime | None = None
    ) -> ParticipantView:
        """Saída voluntária do Evento (diferente de sair de um Núcleo). Idempotente."""
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            participant = await self._participant(session, occurrence.id, character_id)
            if not participant.voluntary_exit:
                participant.voluntary_exit = True
                participant.left_at = now
                participant.current_nucleus_id = None
            return await self._participant_view(session, participant)

    async def list_participants(self, occurrence_id: UUID) -> list[ParticipantView]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(VeuEventParticipant)
                    .where(VeuEventParticipant.occurrence_id == occurrence_id)
                    .order_by(VeuEventParticipant.joined_at, VeuEventParticipant.character_id)
                )
            ).all()
            return [await self._participant_view(session, row) for row in rows]

    async def enter_nucleus(
        self,
        occurrence_id: UUID,
        character_id: UUID,
        nucleus_key: str,
        *,
        now: datetime | None = None,
    ) -> ParticipantView:
        """Entra ou troca de Núcleo ATIVA (§14.1, §14.2). Idempotente no mesmo Núcleo."""
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            if occurrence.state != ev.EventState.EM_ANDAMENTO.value:
                raise VeuEventError("event_not_running")
            nucleus = (await self._nuclei(session, occurrence.id)).get(nucleus_key)
            if nucleus is None:
                raise VeuEventError("nucleus_not_available")
            if not ev.nucleus_accepts_players(ev.NucleusState(nucleus.state)):
                raise VeuEventError("nucleus_not_active")
            participant = await self._participant(session, occurrence.id, character_id)
            if participant.voluntary_exit:
                raise VeuEventError("participant_left")
            if participant.current_nucleus_id == nucleus.id:
                return await self._participant_view(session, participant)
            if (
                participant.reentry_available_at is not None
                and participant.reentry_available_at > now
            ):
                raise VeuEventError("reentry_pending")
            switching = participant.current_nucleus_id is not None
            unresolved = await session.scalar(
                select(VeuEventRound.round_number).where(
                    VeuEventRound.nucleus_id == nucleus.id,
                    VeuEventRound.state != ev.RoundState.RESOLVED.value,
                )
            )
            last = await session.scalar(
                select(func.max(VeuEventRound.round_number)).where(
                    VeuEventRound.nucleus_id == nucleus.id
                )
            )
            participant.acts_from_round = ev.first_action_round(
                unresolved, (last or 0) + 1, switching=switching
            )
            participant.current_nucleus_id = nucleus.id
            participant.nucleus_entered_at = now
            participant.nucleus_removed_at = None
            participant.afk_streak = 0
            await session.flush()
            return await self._participant_view(session, participant)

    async def leave_nucleus(
        self, occurrence_id: UUID, character_id: UUID, *, now: datetime | None = None
    ) -> ParticipantView:
        """Volta ao painel de Núcleos sem punição e sem sair do Evento (§14.6)."""
        _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            participant = await self._participant(session, occurrence.id, character_id)
            participant.current_nucleus_id = None
            participant.afk_streak = 0
            return await self._participant_view(session, participant)

    # --------------------------------------------------------------------- rodadas

    async def open_round(
        self, occurrence_id: UUID, nucleus_key: str, *, now: datetime | None = None
    ) -> RoundView:
        """Abre a próxima rodada do Núcleo; se já há uma aberta, devolve essa."""
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            if occurrence.state != ev.EventState.EM_ANDAMENTO.value:
                raise VeuEventError("event_not_running")
            nucleus = (await self._nuclei(session, occurrence.id)).get(nucleus_key)
            if nucleus is None:
                raise VeuEventError("nucleus_not_available")
            if not ev.nucleus_accepts_rounds(ev.NucleusState(nucleus.state)):
                raise VeuEventError("nucleus_not_active")
            unresolved = await session.scalar(
                select(VeuEventRound).where(
                    VeuEventRound.nucleus_id == nucleus.id,
                    VeuEventRound.state != ev.RoundState.RESOLVED.value,
                )
            )
            if unresolved is not None:
                return self._round_view(unresolved, nucleus_key)
            last = await session.scalar(
                select(func.max(VeuEventRound.round_number)).where(
                    VeuEventRound.nucleus_id == nucleus.id
                )
            )
            round_ = VeuEventRound(
                occurrence_id=occurrence.id,
                nucleus_id=nucleus.id,
                round_number=(last or 0) + 1,
                state=ev.RoundState.OPEN.value,
                opened_at=now,
                decision_deadline=ev.decision_deadline(now),
            )
            session.add(round_)
            await session.flush()
            return self._round_view(round_, nucleus_key)

    async def get_round(self, round_id: UUID) -> RoundView:
        async with self.sessions() as session:
            round_ = await session.get(VeuEventRound, round_id)
            if round_ is None:
                raise VeuEventError("round_not_found")
            nucleus = await session.get(VeuEventNucleus, round_.nucleus_id)
            return self._round_view(round_, nucleus.nucleus_key)

    async def register_action(
        self,
        round_id: UUID,
        character_id: UUID,
        action_type: str,
        *,
        art_slot: int | None = None,
        target_ref: str | None = None,
        now: datetime | None = None,
    ) -> ActionView:
        """Registra a ação do participante. Mesma rodada + mesmo personagem = mesmo ID."""
        now = _utc(now)
        if action_type not in ACTION_TYPES:
            raise VeuEventError("invalid_action_type")
        if (action_type == "art") != (art_slot is not None) or (
            art_slot is not None and not 1 <= art_slot <= 3
        ):
            raise VeuEventError("invalid_art_slot")
        if target_ref is not None and len(target_ref) > 64:
            raise VeuEventError("invalid_target_ref")
        async with self.sessions.begin() as session:
            occurrence, round_, nucleus = await self._lock_round(session, round_id)
            if occurrence.state != ev.EventState.EM_ANDAMENTO.value:
                raise VeuEventError("event_not_running")
            if round_.state != ev.RoundState.OPEN.value or now > round_.decision_deadline:
                raise VeuEventError("decision_window_closed")
            participant = await self._participant(session, occurrence.id, character_id)
            if participant.voluntary_exit or participant.current_nucleus_id != nucleus.id:
                raise VeuEventError("not_in_nucleus")
            if round_.round_number < participant.acts_from_round:
                raise VeuEventError("waiting_next_round")
            action_id = ev.action_id(
                occurrence.occurrence_key, nucleus.nucleus_key, round_.round_number, character_id
            )
            existing = await session.get(VeuEventAction, action_id)
            if existing is not None:
                if (existing.action_type, existing.art_slot, existing.target_ref) != (
                    action_type,
                    art_slot,
                    target_ref,
                ):
                    raise VeuEventError("action_already_registered")
                return self._action_view(existing, created=False)
            action = VeuEventAction(
                id=action_id,
                occurrence_id=occurrence.id,
                round_id=round_.id,
                character_id=character_id,
                action_type=action_type,
                art_slot=art_slot,
                target_ref=target_ref,
                registered_at=now,
                significant=False,
                major_contribution=False,
            )
            session.add(action)
            participant.phases = sorted({*participant.phases, nucleus.phase})
            await session.flush()
            return self._action_view(action, created=True)

    async def register_enemy_decision(
        self,
        round_id: UUID,
        enemy_key: str,
        action_key: str,
        *,
        target_ids: Sequence[UUID] = (),
        telegraph_key: str | None = None,
        now: datetime | None = None,
    ) -> DecisionView:
        """Grava a decisão do inimigo com a semente determinística da rodada (§17.2).

        O serviço não escolhe a ação: valida contra o kit do bestiário. Barreira é recusada
        (``barrier_duration``).
        """
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence, round_, nucleus = await self._lock_round(session, round_id)
            if round_.state != ev.RoundState.OPEN.value:
                raise VeuEventError("round_not_open")
            definition = ev.NUCLEI_BY_KEY[nucleus.nucleus_key]
            if enemy_key not in definition.creature_codes:
                raise VeuEventError("enemy_not_in_nucleus")
            action = next((a for a in creature(enemy_key).actions if a.key == action_key), None)
            if action is None:
                raise VeuEventError("enemy_action_unknown")
            if (action.prepared or action.always_telegraphed) and not telegraph_key:
                raise VeuEventError("telegraph_required")
            if action.kind is ActionKind.MULTI_TARGET and len(target_ids) > (action.targets or 1):
                raise VeuEventError("too_many_targets")
            present = set(
                (
                    await session.scalars(
                        select(VeuEventParticipant.character_id).where(
                            VeuEventParticipant.occurrence_id == occurrence.id,
                            VeuEventParticipant.current_nucleus_id == nucleus.id,
                        )
                    )
                ).all()
            )
            if any(target not in present for target in target_ids):
                raise VeuEventError("target_not_in_nucleus")
            if action.not_consecutive and round_.round_number > 1:
                previous = await session.scalar(
                    select(VeuEventEnemyDecision.action_key)
                    .join(VeuEventRound, VeuEventRound.id == VeuEventEnemyDecision.round_id)
                    .where(
                        VeuEventRound.nucleus_id == nucleus.id,
                        VeuEventRound.round_number == round_.round_number - 1,
                        VeuEventEnemyDecision.enemy_key == enemy_key,
                    )
                )
                if previous == action_key:
                    raise VeuEventError("action_not_consecutive")
            targets = tuple(sorted(str(target) for target in target_ids))
            existing = await session.get(VeuEventEnemyDecision, (round_.id, enemy_key))
            if existing is not None:
                if (existing.action_key, tuple(existing.target_ids), existing.telegraph_key) != (
                    action_key,
                    targets,
                    telegraph_key,
                ):
                    raise VeuEventError("decision_already_committed")
                return self._decision_view(existing, created=False)
            decision = VeuEventEnemyDecision(
                round_id=round_.id,
                enemy_key=enemy_key,
                action_key=action_key,
                target_ids=list(targets),
                telegraph_key=telegraph_key,
                seed=ev.enemy_seed(
                    occurrence.occurrence_key, nucleus.nucleus_key, round_.round_number
                ),
                committed_at=now,
            )
            session.add(decision)
            await session.flush()
            return self._decision_view(decision, created=True)

    async def resolve_round(
        self, round_id: UUID, *, now: datetime | None = None
    ) -> ResolutionView:
        """OPEN -> RESOLVING -> RESOLVED uma única vez, depois dos 10 s de decisão.

        Aplica o AFK (1/3, 2/3, remoção do Núcleo na 3ª) e, com simulador, o combate em lote.
        Idempotente: a segunda chamada só devolve ``resolved_now=False``.
        """
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence, round_, nucleus = await self._lock_round(session, round_id)
            if round_.state == ev.RoundState.OPEN.value and now < round_.decision_deadline:
                raise VeuEventError("decision_window_open")
            state, first = ev.begin_round_resolution(ev.RoundState(round_.state))
            if not first:
                return ResolutionView(round_.id, False, {}, ())
            round_.state = state.value
            round_.resolution_started_at = now
            nucleus_state = ev.NucleusState(nucleus.state)
            if nucleus_state is ev.NucleusState.ATIVA:
                nucleus.state = ev.transition_nucleus(
                    nucleus_state, ev.NucleusState.RESOLVENDO
                ).value
            actions = (
                await session.scalars(
                    select(VeuEventAction).where(VeuEventAction.round_id == round_.id)
                )
            ).all()
            for action in actions:
                action.valid = True
                action.validated_at = now
            acted = {action.character_id for action in actions}
            present = (
                await session.scalars(
                    select(VeuEventParticipant)
                    .where(
                        VeuEventParticipant.occurrence_id == occurrence.id,
                        VeuEventParticipant.current_nucleus_id == nucleus.id,
                        VeuEventParticipant.voluntary_exit.is_(False),
                    )
                    .order_by(VeuEventParticipant.character_id)
                )
            ).all()
            streaks: dict[UUID, int] = {}
            removed: list[UUID] = []
            for participant in present:
                # Quem ainda espera o próximo ciclo (entrada/troca) não estava lá para agir.
                if round_.round_number < participant.acts_from_round:
                    continue
                afk = ev.afk_after_round(
                    participant.afk_streak, participant.character_id in acted
                )
                participant.afk_streak = afk.streak
                streaks[participant.character_id] = afk.streak
                if afk.removed:
                    removed.append(participant.character_id)
            history: list[dict] = []
            if self.simulator is not None:
                history = await self._resolve_combat(
                    session, occurrence, round_, nucleus, list(present), list(actions), now
                )
            # A remoção por AFK vale depois do lote: o jogador ainda estava no Núcleo.
            for participant in present:
                if participant.character_id in removed and participant.current_nucleus_id:
                    participant.current_nucleus_id = None
                    participant.nucleus_removed_at = now
            round_.result = {"history": history}
            if nucleus.state == ev.NucleusState.RESOLVENDO.value:
                resolved = ev.nucleus_resolved(
                    nucleus.nucleus_key,
                    [
                        code
                        for code, data in nucleus.enemy_state.items()
                        if Decimal(data["hp"]) <= 0
                    ],
                )
                nucleus.state = ev.transition_nucleus(
                    ev.NucleusState.RESOLVENDO,
                    ev.NucleusState.RESOLVIDA if resolved else ev.NucleusState.ATIVA,
                ).value
                nucleus.state_version += 1
                if resolved:
                    nucleus.resolved_at = now
            round_.state = ev.transition_round(state, ev.RoundState.RESOLVED).value
            round_.resolved_at = now
            await session.flush()
            return ResolutionView(round_.id, True, streaks, tuple(removed))

    async def _resolve_combat(
        self,
        session: AsyncSession,
        occurrence: VeuEventOccurrence,
        round_: VeuEventRound,
        nucleus: VeuEventNucleus,
        present: list[VeuEventParticipant],
        actions: list[VeuEventAction],
        now: datetime,
    ) -> list[dict]:
        enemies = {
            code: vc.EnemyUnit.from_data(code, data) for code, data in nucleus.enemy_state.items()
        }
        inputs = await self.simulator.prepare(
            session,
            present,
            [action for action in actions if action.valid],
            enemies,
            f"{occurrence.occurrence_key}|{nucleus.nucleus_key}|{round_.round_number}",
        )
        rows = (
            await session.scalars(
                select(VeuEventEnemyDecision).where(VeuEventEnemyDecision.round_id == round_.id)
            )
        ).all()
        decisions = [
            vc.EnemyDecisionData(
                row.enemy_key,
                row.action_key,
                tuple(UUID(value) for value in row.target_ids),
                row.telegraph_key is not None,
            )
            for row in sorted(rows, key=lambda row: row.enemy_key)
        ]
        outcome = vc.resolve_batch(enemies, inputs.players, inputs.intents, decisions)
        nucleus.enemy_state = {code: unit.to_data() for code, unit in enemies.items()}
        by_id = {participant.character_id: participant for participant in present}
        for action in actions:
            participant = by_id.get(action.character_id)
            damage = outcome.damage_by_character.get(action.character_id, 0)
            absorbed = outcome.absorbed_by_character.get(action.character_id, 0)
            objective = bool(outcome.kills_by_character.get(action.character_id))
            action.significant = ev.significant_action(
                effective_damage=damage, absorbed=absorbed, objective=objective
            )
            action.major_contribution = objective
            if participant is not None and action.significant:
                participant.significant_actions += 1
                if action.major_contribution:
                    participant.major_contributions += 1
        for character_id, unit in inputs.players.items():
            participant = by_id.get(character_id)
            if participant is None:
                continue
            participant.hp = unit.hp
            if unit.hp <= 0:
                participant.defeated_at = now
                participant.reentry_available_at = now + ev.REENTRY_DELAY
                participant.current_nucleus_id = None
                participant.afk_streak = 0
        return outcome.history

    async def commit_enemy_decisions(
        self, round_id: UUID, *, now: datetime | None = None
    ) -> list[DecisionView]:
        """IA determinística: escolhe e grava ação/alvo de cada inimigo ao abrir a rodada (§17)."""
        now = _utc(now)
        async with self.sessions() as session:
            round_ = await session.get(VeuEventRound, round_id)
            if round_ is None:
                raise VeuEventError("round_not_found")
            nucleus = await session.get(VeuEventNucleus, round_.nucleus_id)
            occurrence = await session.get(VeuEventOccurrence, round_.occurrence_id)
            present = list(
                (
                    await session.scalars(
                        select(VeuEventParticipant.character_id).where(
                            VeuEventParticipant.occurrence_id == occurrence.id,
                            VeuEventParticipant.current_nucleus_id == nucleus.id,
                            VeuEventParticipant.voluntary_exit.is_(False),
                        )
                    )
                ).all()
            )
            enemies = {
                code: vc.EnemyUnit.from_data(code, data)
                for code, data in nucleus.enemy_state.items()
            }
            base = ev.enemy_seed(
                occurrence.occurrence_key, nucleus.nucleus_key, round_.round_number
            )
            number = round_.round_number
        views: list[DecisionView] = []
        for code in sorted(enemies):
            decision = vc.decide_enemy(
                enemies[code], present, number, base ^ zlib.crc32(code.encode())
            )
            if decision is None:
                continue
            views.append(
                await self.register_enemy_decision(
                    round_id,
                    code,
                    decision.action_key,
                    target_ids=decision.target_ids,
                    telegraph_key=(
                        f"telegraph.{decision.action_key}" if decision.telegraph else None
                    ),
                    now=now,
                )
            )
        return views

    async def settle_occurrence(
        self, occurrence_id: UUID, *, now: datetime | None = None
    ) -> SettlementView:
        """CONCLUIDO/FRACASSADO -> ENCERRADO, pagando cada participante uma única vez (§24).

        Elegível: ocorrência concluída + 2 fases + 8 pontos de contribuição. O Vigor (10) é
        cobrado só aqui, até o que o personagem tiver. Derrota global não paga conclusão.
        """
        now = _utc(now)
        async with self.sessions() as session:
            occurrence = await self._load_occurrence(session, occurrence_id, lock=False)
            if occurrence.state == ev.EventState.ENCERRADO.value:
                return SettlementView(occurrence.id, occurrence.state, 0, 0)
            if occurrence.state not in (
                ev.EventState.CONCLUIDO.value,
                ev.EventState.FRACASSADO.value,
            ):
                raise VeuEventError("occurrence_not_final")
            ids = list(
                (
                    await session.scalars(
                        select(VeuEventParticipant.character_id).where(
                            VeuEventParticipant.occurrence_id == occurrence_id,
                            VeuEventParticipant.settled_at.is_(None),
                        )
                    )
                ).all()
            )
        paid = 0
        for character_id in sorted(ids, key=str):
            paid += await self._settle_participant(occurrence_id, character_id, now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            if occurrence.state != ev.EventState.ENCERRADO.value:
                occurrence.state = _event_move(occurrence.state, ev.EventState.ENCERRADO)
                occurrence.closed_at = now
                occurrence.settled_at = now
                occurrence.state_version += 1
            return SettlementView(occurrence.id, occurrence.state, len(ids), paid)

    async def _settle_participant(
        self, occurrence_id: UUID, character_id: UUID, now: datetime
    ) -> int:
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            participant = await session.scalar(
                select(VeuEventParticipant)
                .where(
                    VeuEventParticipant.occurrence_id == occurrence_id,
                    VeuEventParticipant.character_id == character_id,
                )
                .with_for_update()
            )
            if participant is None or participant.settled_at is not None:
                return 0
            character = await session.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
            eligible = (
                occurrence.state == ev.EventState.CONCLUIDO.value
                and character is not None
                and ev.is_eligible(
                    len(participant.phases),
                    participant.significant_actions,
                    participant.major_contributions,
                )
            )
            reward: dict = {}
            if eligible:
                granted = await grant_bundle(
                    session,
                    character,
                    ev.reward_bundle(ev.EVENT_REFERENCE_LEVEL),
                    f"veu_event:{occurrence.id.hex}:{character.id.hex}",
                )
                xp = ev.reward_xp(level_xp(ev.EVENT_REFERENCE_LEVEL))
                character.xp += xp
                await consolidate_character_level(session, character)
                await reconcile_character_vigor(session, character, now=now)
                spent = min(character.vigor, ev.VIGOR_COST)
                character.vigor -= spent
                # §24.3/§25.1: a primeira conclusão só abre a entrada do Códice, sem bônus.
                known = await session.scalar(
                    select(CodexEntry.id).where(
                        CodexEntry.character_id == character.id,
                        CodexEntry.entry_id == ev.CODEX_KEY,
                    )
                )
                if known is None:
                    session.add(CodexEntry(character_id=character.id, entry_id=ev.CODEX_KEY))
                reward = {
                    "crowns": granted.crowns,
                    "xp": xp,
                    "vigor": spent,
                    "items": [
                        {"name": item.name, "quantity": item.quantity} for item in granted.items
                    ],
                }
            participant.eligible = eligible
            participant.reward = reward
            participant.settled_at = now
            return 1 if eligible else 0

    async def fail_at_deadline(self, occurrence_id: UUID, *, now: datetime | None = None) -> bool:
        """EM_ANDAMENTO -> FRACASSADO quando o prazo (``DEADLINE``) esgota. Idempotente."""
        now = _utc(now)
        async with self.sessions.begin() as session:
            occurrence = await self._load_occurrence(session, occurrence_id)
            if occurrence.state != ev.EventState.EM_ANDAMENTO.value or now < occurrence.deadline_at:
                return False
            occurrence.state = _event_move(occurrence.state, ev.EventState.FRACASSADO)
            occurrence.state_version += 1
            return True

    async def unfinished_occurrences(self, now: datetime) -> list[OccurrenceView]:
        """EM_ANDAMENTO (qualquer idade) e AGENDADO/ABERTO ainda dentro do prazo."""
        now = _utc(now)
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(VeuEventOccurrence)
                    .where(
                        VeuEventOccurrence.server_id == self.server_id,
                        (VeuEventOccurrence.state == ev.EventState.EM_ANDAMENTO.value)
                        | (
                            VeuEventOccurrence.state.in_(
                                (ev.EventState.AGENDADO.value, ev.EventState.ABERTO.value)
                            )
                            & (VeuEventOccurrence.deadline_at > now)
                        ),
                    )
                    .order_by(VeuEventOccurrence.scheduled_at)
                )
            ).all()
            return [await self._occurrence_view(session, row) for row in rows]

    async def nucleus_enemy_state(self, occurrence_id: UUID, nucleus_key: str) -> dict:
        async with self.sessions() as session:
            nucleus = (await self._nuclei(session, occurrence_id)).get(nucleus_key)
            if nucleus is None:
                raise VeuEventError("nucleus_not_available")
            return dict(nucleus.enemy_state)

    async def unsettled_final_occurrences(self) -> list[UUID]:
        async with self.sessions() as session:
            rows = await session.scalars(
                select(VeuEventOccurrence.id).where(
                    VeuEventOccurrence.server_id == self.server_id,
                    VeuEventOccurrence.state.in_(
                        (ev.EventState.CONCLUIDO.value, ev.EventState.FRACASSADO.value)
                    ),
                )
            )
            return list(rows.all())

    async def enemy_stats(self, occurrence_id: UUID, nucleus_key: str) -> dict[str, CombatStats]:
        """Atributos das criaturas do Núcleo com o N congelado da fase (§8.1–§8.4).

        Criatura sem perfil de motor na fonte levanta ``UnresolvedArchetypeError``
        (``archetype_engine_profile``); nenhum perfil é inventado.
        """
        definition = ev.NUCLEI_BY_KEY.get(nucleus_key)
        if definition is None:
            raise VeuEventError("nucleus_not_available")
        async with self.sessions() as session:
            snapshot = await session.get(VeuEventPhaseSnapshot, (occurrence_id, definition.phase))
        if snapshot is None:
            raise VeuEventError("phase_not_started")
        return {
            code: creature_stats(creature(code), snapshot.n)
            for code in definition.creature_codes
        }

    async def due_round_ids(self, occurrence_id: UUID, now: datetime) -> list[UUID]:
        """Rodadas abertas cujos 10 s de decisão já passaram."""
        async with self.sessions() as session:
            rows = await session.scalars(
                select(VeuEventRound.id).where(
                    VeuEventRound.occurrence_id == occurrence_id,
                    VeuEventRound.state == ev.RoundState.OPEN.value,
                    VeuEventRound.decision_deadline <= now,
                )
            )
            return list(rows.all())

    async def nuclei_with_players(self, occurrence_id: UUID) -> list[str]:
        """Núcleos ATIVA com ao menos um participante presente."""
        async with self.sessions() as session:
            rows = await session.scalars(
                select(VeuEventNucleus.nucleus_key)
                .join(
                    VeuEventParticipant,
                    VeuEventParticipant.current_nucleus_id == VeuEventNucleus.id,
                )
                .where(
                    VeuEventNucleus.occurrence_id == occurrence_id,
                    VeuEventNucleus.state == ev.NucleusState.ATIVA.value,
                )
                .distinct()
                .order_by(VeuEventNucleus.nucleus_key)
            )
            return list(rows.all())

    # ------------------------------------------------------------------ internals

    async def _load_occurrence(
        self, session: AsyncSession, occurrence_id: UUID, *, lock: bool = True
    ) -> VeuEventOccurrence:
        query = select(VeuEventOccurrence).where(VeuEventOccurrence.id == occurrence_id)
        occurrence = await session.scalar(query.with_for_update() if lock else query)
        if occurrence is None or occurrence.server_id != self.server_id:
            raise VeuEventError("occurrence_not_found")
        return occurrence

    async def _lock_round(
        self, session: AsyncSession, round_id: UUID
    ) -> tuple[VeuEventOccurrence, VeuEventRound, VeuEventNucleus]:
        # Mesma ordem de trava em tudo: ocorrência primeiro, depois a rodada.
        probe = await session.get(VeuEventRound, round_id)
        if probe is None:
            raise VeuEventError("round_not_found")
        occurrence = await self._load_occurrence(session, probe.occurrence_id)
        round_ = await session.scalar(
            select(VeuEventRound)
            .where(VeuEventRound.id == round_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        nucleus = await session.get(VeuEventNucleus, round_.nucleus_id)
        return occurrence, round_, nucleus

    async def _nuclei(self, session: AsyncSession, occurrence_id: UUID):
        rows = (
            await session.scalars(
                select(VeuEventNucleus).where(VeuEventNucleus.occurrence_id == occurrence_id)
            )
        ).all()
        return {row.nucleus_key: row for row in rows}

    async def _participant(
        self, session: AsyncSession, occurrence_id: UUID, character_id: UUID
    ) -> VeuEventParticipant:
        participant = await session.get(VeuEventParticipant, (occurrence_id, character_id))
        if participant is None:
            raise VeuEventError("not_a_participant")
        return participant

    async def _begin_phase(
        self, session: AsyncSession, occurrence: VeuEventOccurrence, phase: int, now: datetime
    ) -> None:
        records = [
            ev.ParticipantRecord(row.character_id, row.voluntary_exit, row.reentry_available_at)
            for row in (
                await session.scalars(
                    select(VeuEventParticipant).where(
                        VeuEventParticipant.occurrence_id == occurrence.id
                    )
                )
            ).all()
        ]
        snapshot = ev.freeze_phase_snapshot(phase, records, now)
        session.add(
            VeuEventPhaseSnapshot(
                occurrence_id=occurrence.id, phase=phase, n=snapshot.n, frozen_at=now
            )
        )
        for definition in ev.nuclei_of_phase(phase):
            enemy_state = {}
            for code in definition.creature_codes:
                stats = creature_stats(creature(code), max(1, snapshot.n))
                hp = stats.hp.to_integral_value()
                enemy_state[code] = vc.EnemyUnit(
                    code, hp, hp, stats.attack, stats.defense, agility=stats.agility
                ).to_data()
            session.add(
                VeuEventNucleus(
                    occurrence_id=occurrence.id,
                    nucleus_key=definition.key,
                    phase=phase,
                    state=ev.NucleusState.ATIVA.value,
                    enemy_state=enemy_state,
                    state_version=0,
                )
            )
        await session.flush()

    async def _remove_from_nucleus(
        self, session: AsyncSession, occurrence_id: UUID, nucleus_id: UUID
    ) -> None:
        """§14.6: sem punição; não marca remoção nem mexe no AFK."""
        rows = (
            await session.scalars(
                select(VeuEventParticipant).where(
                    VeuEventParticipant.occurrence_id == occurrence_id,
                    VeuEventParticipant.current_nucleus_id == nucleus_id,
                )
            )
        ).all()
        for row in rows:
            row.current_nucleus_id = None

    async def _occurrence_view(
        self, session: AsyncSession, occurrence: VeuEventOccurrence
    ) -> OccurrenceView:
        nuclei = await self._nuclei(session, occurrence.id)
        snapshots = (
            await session.scalars(
                select(VeuEventPhaseSnapshot).where(
                    VeuEventPhaseSnapshot.occurrence_id == occurrence.id
                )
            )
        ).all()
        return OccurrenceView(
            id=occurrence.id,
            server_id=occurrence.server_id,
            occurrence_key=occurrence.occurrence_key,
            state=occurrence.state,
            phase=occurrence.phase,
            state_version=occurrence.state_version,
            nuclei={key: row.state for key, row in sorted(nuclei.items())},
            snapshots={row.phase: row.n for row in snapshots},
            scheduled_at=occurrence.scheduled_at,
            deadline_at=occurrence.deadline_at,
        )

    async def _participant_view(
        self, session: AsyncSession, participant: VeuEventParticipant
    ) -> ParticipantView:
        key = None
        if participant.current_nucleus_id is not None:
            nucleus = await session.get(VeuEventNucleus, participant.current_nucleus_id)
            key = nucleus.nucleus_key
        label = ev.AfkState(participant.afk_streak, False).label
        return ParticipantView(
            character_id=participant.character_id,
            current_nucleus=key,
            afk_streak=participant.afk_streak,
            afk_label=label,
            nucleus_removed=participant.nucleus_removed_at is not None,
            voluntary_exit=participant.voluntary_exit,
            phases=tuple(participant.phases),
        )

    @staticmethod
    def _round_view(round_: VeuEventRound, nucleus_key: str) -> RoundView:
        return RoundView(
            id=round_.id,
            nucleus_key=nucleus_key,
            round_number=round_.round_number,
            state=round_.state,
            opened_at=round_.opened_at,
            decision_deadline=round_.decision_deadline,
            resolved_at=round_.resolved_at,
        )

    @staticmethod
    def _action_view(action: VeuEventAction, *, created: bool) -> ActionView:
        return ActionView(
            id=action.id,
            round_id=action.round_id,
            character_id=action.character_id,
            action_type=action.action_type,
            art_slot=action.art_slot,
            target_ref=action.target_ref,
            valid=action.valid,
            created=created,
        )

    @staticmethod
    def _decision_view(decision: VeuEventEnemyDecision, *, created: bool) -> DecisionView:
        return DecisionView(
            round_id=decision.round_id,
            enemy_key=decision.enemy_key,
            action_key=decision.action_key,
            target_ids=tuple(decision.target_ids),
            telegraph_key=decision.telegraph_key,
            seed=int(decision.seed),
            created=created,
        )


@dataclass(frozen=True, slots=True)
class VeuNotice:
    """Aviso estruturado. O texto não existe no repositório (``notice_texts``)."""

    kind: str  # "opens_in"
    occurrence_id: UUID
    minutes: int


@dataclass(frozen=True, slots=True)
class UpkeepReport:
    opened: tuple[UUID, ...]
    failed: tuple[UUID, ...]
    rounds_resolved: int
    rounds_opened: int
    notices: tuple[VeuNotice, ...]


class VeuEventUpkeep:
    """Ciclo automático: ocorrências, abertura, rodadas e prazo.

    Início: o evento começa no horário da agenda (§3.3: os 15 min iniciais não são lobby), isto
    é, ``start_after`` = 0 depois da abertura. Fim: ao ficar CONCLUIDO/FRACASSADO a ocorrência
    é acertada e vira ENCERRADO.
    """

    def __init__(
        self,
        service: VeuEventService,
        *,
        start_after: timedelta | None = timedelta(0),
        horizon: timedelta = timedelta(minutes=10),
    ):
        self.service = service
        self.start_after = start_after
        self.horizon = horizon

    async def tick(
        self, now: datetime | None = None, *, previous: datetime | None = None
    ) -> UpkeepReport:
        """``previous`` = instante da última verificação; sem ele não há avisos (evita repetir)."""
        now = _utc(now)
        previous = _utc(previous) if previous is not None else None
        service = self.service
        notices: list[VeuNotice] = []
        slots = ev.slots_in_range(now - ev.DEADLINE, now + self.horizon)
        views = {}
        for slot in slots:
            view = await service.get_or_create_occurrence(slot)
            views[view.id] = view
        # EM_ANDAMENTO velho (queda do scheduler) ainda precisa do prazo.
        for view in await service.unfinished_occurrences(now):
            views.setdefault(view.id, view)
        opened: list[UUID] = []
        failed: list[UUID] = []
        resolved = opened_rounds = 0
        for view in sorted(views.values(), key=lambda item: item.scheduled_at):
            slot = view.scheduled_at
            if previous is not None:
                for mark in ev.due_notice_marks(slot, previous, now):
                    notices.append(
                        VeuNotice("opens_in", view.id, int(mark.total_seconds() // 60))
                    )
            state = view.state
            if state == ev.EventState.AGENDADO.value and now >= slot:
                state = (await service.open_occurrence(view.id, now=now)).state
                opened.append(view.id)
            if (
                state == ev.EventState.ABERTO.value
                and self.start_after is not None
                and now >= slot + self.start_after
            ):
                state = (await service.start_occurrence(view.id, now=now)).state
            if state != ev.EventState.EM_ANDAMENTO.value:
                continue
            resolved += await self._resolve_due_rounds(view.id, now)
            current = await service.reevaluate_progress(view.id, now=now)
            if current.state != ev.EventState.EM_ANDAMENTO.value:
                continue
            if now >= view.deadline_at:
                if await service.fail_at_deadline(view.id, now=now):
                    failed.append(view.id)
                continue
            opened_rounds += await self._open_rounds(current, now)
        for occurrence_id in await service.unsettled_final_occurrences():
            await service.settle_occurrence(occurrence_id, now=now)
        return UpkeepReport(
            tuple(opened), tuple(failed), resolved, opened_rounds, tuple(notices)
        )

    async def _resolve_due_rounds(self, occurrence_id: UUID, now: datetime) -> int:
        count = 0
        for round_id in await self.service.due_round_ids(occurrence_id, now):
            if (await self.service.resolve_round(round_id, now=now)).resolved_now:
                count += 1
        return count

    async def _open_rounds(self, occurrence: OccurrenceView, now: datetime) -> int:
        count = 0
        for key in await self.service.nuclei_with_players(occurrence.id):
            opened = await self.service.open_round(occurrence.id, key, now=now)
            if opened.opened_at == now:
                await self.service.commit_enemy_decisions(opened.id, now=now)
                count += 1
        return count
