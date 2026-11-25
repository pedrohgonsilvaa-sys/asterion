"""O Despertar dos Flagelos: orquestração (barras, Flagelo global, combate, liquidação).

Exceção autoral ao GDD §21/§49.15 (``SOURCE_AUTHORITY.md``): o Flagelo não expira, escala por
abandono, custa 0 Vigor, paga ``0,50×C + 3 básicos + 1 Fragmento do Flagelo`` e exige 3
Participation Points. O Evento Mundial genérico e A Ruptura do Véu não mudam.

Infraestrutura reaproveitada, sem sistema paralelo:

- combate: motor existente via simulador do Véu (``flagelo_combat``) e lote simultâneo
  ``veu_combat.resolve_batch`` (rodada de 10 s, Barreira, Defender, efeitos);
- recompensa: ``grant_bundle``/``return_to_owner`` (Coroas, materiais, Pending);
- XP: ``level_xp`` + ``consolidate_character_level``;
- receitas: ``Unlock`` (o mesmo vínculo das Receitas especiais do Crafting);
- Bestiário/Códice: ``BestiaryRecorder`` e ``CodexEntry``;
- notificações: Transactional Outbox (``OutboxMessage``) gravada na mesma transação.

Ordem de travas (todas as escritas a seguem; impede deadlock):
``flagelo_region_progress`` (ordem de ``region_id``) → ``flagelo_events`` → ``flagelo_rounds``
→ ``characters`` → ``flagelo_participants``. A liquidação paga um personagem por transação e
não trava progresso nem rodada.

Lock da Configuração de Combate (espec. final §3): ``in_combat`` é o lock. Ele é lido pelo
guarda global ``combat_configuration_guard`` e só termina pela resolução válida do encontro
(derrota, saída registrada, inatividade do GDD §49 ou morte do Flagelo).

Idempotência: contribuição por ``activity_id + character_id``; um único ``active`` por
servidor (índice único parcial); morte registrada uma vez (``status``); rodada resolvida uma
vez (OPEN → RESOLVING → RESOLVED); cada recompensa com ``settlement_key`` única; notificações
com ``dedup_key`` única no Outbox.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BestiaryRecorder
from asterion.application.combat_configuration_guard import (
    FLAGELO_ACTIVITY_CONTENT,
    find_combat_configuration_blocker,
)
from asterion.application.engagement import grant_bundle
from asterion.application.equipment import equipment_instance_payload
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.flagelo_combat import (
    BossEffects,
    FlageloRoundSimulator,
    next_boss_state,
)
from asterion.application.item_escrow import return_to_owner
from asterion.application.progression import consolidate_character_level, level_xp
from asterion.application.world_event_veu import RoundInputs
from asterion.domain import flagelo_catalog as catalog
from asterion.domain import flagelo_lore
from asterion.domain import flagelos as fl
from asterion.domain import veu_combat as vc
from asterion.domain.combat_math import CombatStats
from asterion.domain.engagement import Bundle
from asterion.domain.road import RULESET as COMBAT_RULESET
from asterion.domain.road import materialize_equipment
from asterion.domain.veu_bestiary import ActionKind
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Character,
    CodexEntry,
    CodexFragment,
    FlageloAction,
    FlageloContribution,
    FlageloEvent,
    FlageloParticipant,
    FlageloRegionProgress,
    FlageloRewardSettlement,
    FlageloRound,
    GameActivity,
    OutboxMessage,
    Unlock,
    WorldState,
)

# Exclusividade de atividade: o combate no Flagelo mantém uma ``GameActivity`` ativa, como o
# Evento Mundial genérico. É a "linha de primeiro plano" única (``uq_active_foreground``) que
# Caçada, Desbravar, Masmorra, PvP, Missões e Ofícios já consultam: nenhuma trava paralela.
ACTIVITY_CONTENT = FLAGELO_ACTIVITY_CONTENT
ACTION_TYPES = ("attack", "defend", "art")
NOTICE_TOPIC = "flagelo.community_notice"
OPEN, RESOLVING, RESOLVED = "OPEN", "RESOLVING", "RESOLVED"


class FlageloError(ValueError):
    def __init__(self, code: str, seconds: int = 0):
        self.code = code
        self.seconds = seconds
        super().__init__(code)


class RoundSimulator(Protocol):
    async def prepare(self, session, participants, actions, enemies, combat_key) -> RoundInputs: ...


SimulatorFactory = Callable[[int, BossEffects], RoundSimulator]


def _engine_simulator(level: int, boss: BossEffects) -> FlageloRoundSimulator:
    return FlageloRoundSimulator(level, boss)


def _utc(now: datetime | None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return current.astimezone(UTC)


def _seconds(deadline: datetime | None, now: datetime) -> int:
    return 0 if deadline is None else max(0, int((deadline - now).total_seconds()))


def _metrics(row: FlageloParticipant) -> fl.ParticipationMetrics:
    return fl.ParticipationMetrics(
        int(row.effective_damage),
        int(row.effective_healing),
        int(row.barrier_absorbed),
        int(row.defender_prevented_damage),
        int(row.meaningful_effects),
    )


async def _configuration_snapshot(session, character: Character) -> dict:
    """A Configuração de Combate efetiva na entrada (equipamento, Caminho, Talentos, Artes)."""
    equipment = await load_equipment_configuration(session, character)
    arts = await load_active_art_configuration(session, character)
    return {
        "combat_configuration_version": int(character.combat_configuration_version),
        "equipment": equipment.to_data(COMBAT_RULESET),
        "active_arts": arts.to_data(),
    }


def _boss_snapshot(event: FlageloEvent) -> dict:
    return {
        "max_hp": event.max_hp,
        "attack": event.attack,
        "defense": event.base_def,
        "agility": event.base_agi,
        "steps": event.abandonment_steps,
    }


# ---------------------------------------------------------------------- views


@dataclass(frozen=True, slots=True)
class RegionBar:
    region_id: str
    emoji: str
    label: str
    points: int
    threshold: int
    percent: int
    active: bool


@dataclass(frozen=True, slots=True)
class ActiveFlagelo:
    event_id: UUID
    region_id: str
    region: str
    name: str
    hp: int
    max_hp: int
    active_seconds: int
    combatants: int
    capacity: int
    scaling_steps: int
    scaling_paused: bool


@dataclass(frozen=True, slots=True)
class SelfState:
    joined: bool
    in_combat: bool
    reentry_seconds: int
    participation_points: int
    eligible: bool
    metrics: fl.ParticipationMetrics | None = None


@dataclass(frozen=True, slots=True)
class RankingLine:
    category: str
    position: int
    name: str
    value: int


@dataclass(frozen=True, slots=True)
class RegionStatus:
    """Barra da Região atual do personagem e se há um Flagelo desperto (HUD da Região)."""

    bar: RegionBar
    flagelo_awake: bool


@dataclass(frozen=True, slots=True)
class HubView:
    bars: tuple[RegionBar, ...]
    active: ActiveFlagelo | None
    me: SelfState | None
    last_rankings: tuple[RankingLine, ...] = ()
    last_name: str | None = None
    # Recompensa do personagem no último Flagelo morto (quando já liquidada).
    last_reward: dict | None = None


@dataclass(frozen=True, slots=True)
class CombatScreen:
    event_id: UUID
    name: str
    round_number: int
    seconds_left: int
    boss_hp: int
    boss_max_hp: int
    self_name: str
    self_hp: int
    self_max_hp: int
    art_slots: tuple[int, ...]
    acted: bool
    waiting: bool
    telegraph: str | None
    history: tuple[dict, ...]
    participation_points: int
    # Escala atual (passos de 15 min sem combatente) e métricas do próprio personagem.
    scaling_steps: int = 0
    metrics: fl.ParticipationMetrics | None = None


@dataclass(frozen=True, slots=True)
class UpkeepReport:
    applied: int
    spawned: tuple[UUID, ...]
    rounds_resolved: int
    rounds_opened: int
    scaled: int
    defeated: tuple[UUID, ...]
    settled: int


# ---------------------------------------------------------------------- service


class FlageloService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        simulator: SimulatorFactory | None = _engine_simulator,
    ):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id
        self.simulator = simulator

    # ------------------------------------------------------------ progresso

    async def _ensure_progress(self, session: AsyncSession) -> None:
        await session.execute(
            insert(FlageloRegionProgress)
            .values(
                [
                    {
                        "server_id": self.server_id,
                        "region_id": region.region_id,
                        "current_points": 0,
                        "threshold": fl.THRESHOLD,
                        "cycle": 1,
                        "version": 0,
                    }
                    for region in fl.REGIONS
                ]
            )
            .on_conflict_do_nothing(index_elements=["server_id", "region_id"])
        )

    async def _lock_progress(self, session, region_ids: Sequence[str] | None = None):
        query = (
            select(FlageloRegionProgress)
            .where(FlageloRegionProgress.server_id == self.server_id)
            .order_by(FlageloRegionProgress.region_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if region_ids is not None:
            query = query.where(FlageloRegionProgress.region_id.in_(sorted(region_ids)))
        return {row.region_id: row for row in (await session.scalars(query)).all()}

    async def apply_contributions(
        self, *, now: datetime | None = None, limit: int = 1000
    ) -> tuple[int, tuple[UUID, ...]]:
        """Aplicador serializado: soma as contribuições pendentes em ordem e faz o spawn.

        Contribuição de região congelada (Flagelo vivo, ou criada antes da morte que zerou a
        barra) fica registrada com ``counted_points = 0``.
        """
        now = _utc(now)
        async with self.sessions.begin() as session:
            await self._ensure_progress(session)
            progress = await self._lock_progress(session)
            rows = (
                await session.scalars(
                    select(FlageloContribution)
                    .where(
                        FlageloContribution.server_id == self.server_id,
                        FlageloContribution.applied_at.is_(None),
                    )
                    .order_by(FlageloContribution.seq)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for row in rows:
                bar = progress.get(row.region_id)
                if bar is None:
                    row.applied_at, row.counted_points = now, 0
                    continue
                frozen = bar.active_flagelo_id is not None or (
                    bar.last_defeated_at is not None and row.created_at < bar.last_defeated_at
                )
                new, added = fl.apply_points(bar.current_points, row.points, frozen=frozen)
                if added:
                    bar.current_points = new
                    bar.version += 1
                    bar.updated_at = now
                    if new >= bar.threshold and bar.threshold_reached_at is None:
                        bar.threshold_reached_at = now
                row.applied_at, row.counted_points, row.cycle = now, added, bar.cycle
            spawned = await self._spawn_if_due(session, progress, now)
            return len(rows), spawned

    async def _spawn_if_due(self, session, progress, now: datetime) -> tuple[UUID, ...]:
        """Zero ou um Flagelo ativo: a região que chegou a 500 primeiro desperta o seu.

        Duas regiões no limite ao mesmo tempo não criam dois Flagelos: o índice único parcial
        recusa o segundo, e a outra barra fica em 500/500 até o Flagelo atual morrer.
        """
        active = await session.scalar(
            select(FlageloEvent.id).where(
                FlageloEvent.server_id == self.server_id, FlageloEvent.status == "active"
            )
        )
        if active is not None:
            return ()
        waiting = sorted(
            (
                bar
                for bar in progress.values()
                if bar.active_flagelo_id is None
                and bar.threshold_reached_at is not None
                and bar.current_points >= bar.threshold
            ),
            key=lambda bar: (
                bar.threshold_reached_at,
                [r.region_id for r in fl.REGIONS].index(bar.region_id),
            ),
        )
        if not waiting:
            return ()
        bar = waiting[0]
        definition = fl.region(bar.region_id).flagelo
        event_id = uuid4()
        inserted = await session.execute(
            insert(FlageloEvent)
            .values(
                id=event_id,
                server_id=self.server_id,
                region_id=bar.region_id,
                flagelo_id=definition.flagelo_id,
                cycle=bar.cycle,
                status="active",
                spawned_at=now,
                base_hp=definition.hp,
                base_atq=definition.attack,
                base_def=definition.defense,
                base_agi=definition.agility,
                max_hp=definition.hp,
                attack=definition.attack,
                hp_current=definition.hp,
                abandonment_steps=0,
                hp_scaling_bonus=Decimal(0),
                atq_scaling_bonus=Decimal(0),
                last_zero_combat_at=now,
                enemy_state={},
                round_number=0,
                rankings={},
                version=0,
            )
            .on_conflict_do_nothing()
            .returning(FlageloEvent.id)
        )
        if inserted.first() is None:
            return ()
        bar.active_flagelo_id = event_id
        bar.version += 1
        bar.updated_at = now
        self._notice(session, "spawn", event_id, bar.region_id)
        return (event_id,)

    def _notice(self, session, kind: str, event_id: UUID, region_id: str) -> None:
        """Notificação única por ocorrência, na mesma transação do fato (Outbox)."""
        session.add(
            OutboxMessage(
                topic=NOTICE_TOPIC,
                dedup_key=f"flagelo:{kind}:{event_id}",
                aggregate_key=f"flagelo:{self.server_id}",
                payload={"kind": kind, "event_id": str(event_id), "region_id": region_id},
            )
        )

    # ------------------------------------------------------------ leitura

    async def active_event(self, session, *, lock: bool = False) -> FlageloEvent | None:
        query = select(FlageloEvent).where(
            FlageloEvent.server_id == self.server_id, FlageloEvent.status == "active"
        )
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return await session.scalar(query)

    async def _character(self, session, actor: int, *, lock: bool = False) -> Character:
        query = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        character = await session.scalar(query.with_for_update() if lock else query)
        if character is None:
            raise FlageloError("no_character")
        return character

    async def _combatants(self, session, event_id: UUID) -> int:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(FlageloParticipant)
                .where(
                    FlageloParticipant.flagelo_id == event_id,
                    FlageloParticipant.in_combat.is_(True),
                )
            )
            or 0
        )

    async def hub(self, actor: int, *, now: datetime | None = None) -> HubView:
        now = _utc(now)
        async with self.sessions.begin() as session:
            await self._ensure_progress(session)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            rows = (
                await session.scalars(
                    select(FlageloRegionProgress).where(
                        FlageloRegionProgress.server_id == self.server_id
                    )
                )
            ).all()
            by_id = {row.region_id: row for row in rows}
            bars = tuple(
                RegionBar(
                    region.region_id,
                    region.emoji,
                    region.short_label,
                    by_id[region.region_id].current_points,
                    by_id[region.region_id].threshold,
                    fl.percent(by_id[region.region_id].current_points),
                    by_id[region.region_id].active_flagelo_id is not None,
                )
                for region in fl.REGIONS
            )
            event = await self.active_event(session)
            active = me = None
            if event is not None:
                count = await self._combatants(session, event.id)
                region = fl.region(event.region_id)
                active = ActiveFlagelo(
                    event.id,
                    event.region_id,
                    region.region,
                    region.flagelo.name,
                    event.hp_current,
                    event.max_hp,
                    max(0, int((now - event.spawned_at).total_seconds())),
                    count,
                    fl.PARTICIPANT_CAP,
                    event.abandonment_steps,
                    count > 0,
                )
                participant = await session.get(FlageloParticipant, (event.id, character.id))
                if participant is not None:
                    me = SelfState(
                        True,
                        participant.in_combat,
                        _seconds(participant.reentry_available_at, now),
                        participant.participation_points,
                        fl.is_eligible(_metrics(participant)),
                        _metrics(participant),
                    )
            last_rankings, last_name, last_reward = await self._last_rankings(
                session, character.id
            )
            return HubView(bars, active, me, last_rankings, last_name, last_reward)

    async def region_status(self, actor: int) -> RegionStatus | None:
        """Barra da Região onde o personagem está (``WorldState.region``). Só leitura."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            place = await session.scalar(
                select(WorldState.region).where(WorldState.character_id == character.id)
            )
            region = fl.REGIONS_BY_NAME.get(place or "")
            if region is None:
                return None
            row = await session.get(FlageloRegionProgress, (self.server_id, region.region_id))
            points = row.current_points if row is not None else 0
            awake = await self.active_event(session) is not None
            return RegionStatus(
                RegionBar(
                    region.region_id,
                    region.emoji,
                    region.short_label,
                    points,
                    fl.THRESHOLD,
                    fl.percent(points),
                    row is not None and row.active_flagelo_id is not None,
                ),
                awake,
            )

    async def _last_rankings(self, session, character_id: UUID | None = None):
        event = await session.scalar(
            select(FlageloEvent)
            .where(
                FlageloEvent.server_id == self.server_id,
                FlageloEvent.status.in_(("defeated", "settled")),
            )
            .order_by(FlageloEvent.defeated_at.desc())
            .limit(1)
        )
        if event is None:
            return (), None, None
        reward = None
        if character_id is not None:
            mine = await session.get(FlageloParticipant, (event.id, character_id))
            if mine is not None and mine.settled_at is not None and mine.eligible:
                reward = dict(mine.reward or {})
        lines = []
        for category in fl.RANKING_CATEGORIES:
            for entry in event.rankings.get(category, ()):
                lines.append(
                    RankingLine(category, int(entry["position"]), entry["name"], entry["value"])
                )
        return tuple(lines), fl.region(event.region_id).flagelo.name, reward

    # ------------------------------------------------------------ entrada e saída

    async def enter(self, actor: int, *, now: datetime | None = None) -> UUID:
        """Entra (ou reentra) no combate do Flagelo ativo. 0 Vigor; capacidade 200."""
        now = _utc(now)
        async with self.sessions.begin() as session:
            event = await self.active_event(session, lock=True)
            if event is None:
                raise FlageloError("no_flagelo")
            # Trava do personagem primeiro: é a mesma trava das mutações de Configuração
            # (``combat_configuration_guard``), então entrada e troca de equipamento se
            # serializam e nenhuma escapa do lock.
            character = await self._character(session, actor, lock=True)
            participant = await session.scalar(
                select(FlageloParticipant)
                .where(
                    FlageloParticipant.flagelo_id == event.id,
                    FlageloParticipant.character_id == character.id,
                )
                .with_for_update()
            )
            if participant is not None and participant.in_combat:
                return event.id
            blocker = await find_combat_configuration_blocker(session, character.id)
            if blocker is not None:
                # Outra atividade autoritativa já detém a Configuração (Caçada, Masmorra...).
                raise FlageloError("busy")
            if (
                participant is not None
                and participant.reentry_available_at is not None
                and now < participant.reentry_available_at
            ):
                raise FlageloError("reentry_wait", _seconds(participant.reentry_available_at, now))
            if await self._combatants(session, event.id) >= fl.PARTICIPANT_CAP:
                raise FlageloError("full")
            if participant is None:
                participant = FlageloParticipant(
                    flagelo_id=event.id,
                    character_id=character.id,
                    joined_at=now,
                    effective_damage=0,
                    effective_healing=0,
                    barrier_absorbed=0,
                    defender_prevented_damage=0,
                    meaningful_effects=0,
                    participation_points=0,
                    first_metric_timestamps={},
                    combat_state={},
                    reward={},
                )
                session.add(participant)
            elif participant.hp is not None and participant.hp <= 0:
                # Reentrada depois de derrota volta com a vida cheia (regra do Evento
                # existente); a vida do Flagelo e o escalonamento não mudam.
                participant.hp = None
                participant.combat_state = {}
            participant.in_combat = True
            participant.combat_entered_at = now
            participant.acts_from_round = event.round_number + 1
            participant.idle_rounds = 0
            participant.left_at = None
            # Snapshot autoritativo da entrada: atributos do Flagelo e a Configuração de
            # Combate travada. Reentrada grava um novo.
            participant.entry_snapshot = {
                **_boss_snapshot(event),
                "configuration": await _configuration_snapshot(session, character),
            }
            event.last_zero_combat_at = None
            event.version += 1
            session.add(
                GameActivity(
                    character_id=character.id,
                    content_id=ACTIVITY_CONTENT,
                    status="active",
                    state_version=0,
                    ruleset_version=fl.RULESET,
                    last_valid_action_at=now,
                )
            )
            await session.flush()
            return event.id

    @staticmethod
    async def _release_activities(session, character_ids: Sequence[UUID] | None = None) -> None:
        """Encerra a ``GameActivity`` do combate no Flagelo (saída, derrota, inatividade ou
        morte do Flagelo). Idempotente: sem linha ativa não faz nada."""
        statement = (
            update(GameActivity)
            .where(GameActivity.content_id == ACTIVITY_CONTENT, GameActivity.status == "active")
            .values(status="completed")
        )
        if character_ids is not None:
            if not character_ids:
                return
            statement = statement.where(GameActivity.character_id.in_(list(character_ids)))
        await session.execute(statement)

    async def _release_orphans(self, session) -> int:
        """Rede de segurança do restart: nenhuma linha ativa sem ``in_combat`` correspondente."""
        in_combat = (
            select(FlageloParticipant.character_id)
            .where(FlageloParticipant.in_combat.is_(True))
            .scalar_subquery()
        )
        result = await session.execute(
            update(GameActivity)
            .where(
                GameActivity.content_id == ACTIVITY_CONTENT,
                GameActivity.status == "active",
                GameActivity.character_id.not_in(in_combat),
            )
            .values(status="completed")
        )
        return int(result.rowcount or 0)

    async def leave(self, actor: int, *, now: datetime | None = None) -> None:
        now = _utc(now)
        async with self.sessions.begin() as session:
            event = await self.active_event(session, lock=True)
            if event is None:
                raise FlageloError("no_flagelo")
            character = await self._character(session, actor)
            participant = await session.get(
                FlageloParticipant, (event.id, character.id), with_for_update=True
            )
            if participant is None or not participant.in_combat:
                return
            self._exit(participant, now)
            await self._release_activities(session, [character.id])
            await session.flush()
            await self._mark_idle_if_empty(session, event, now)

    @staticmethod
    def _exit(participant: FlageloParticipant, now: datetime, *, defeated: bool = False):
        participant.in_combat = False
        participant.idle_rounds = 0
        participant.reentry_available_at = now + fl.REENTRY_DELAY
        if defeated:
            participant.defeated_at = now
            participant.hp = Decimal(0)
        else:
            participant.left_at = now

    async def _mark_idle_if_empty(self, session, event: FlageloEvent, now: datetime) -> None:
        if event.status == "active" and await self._combatants(session, event.id) == 0:
            if event.last_zero_combat_at is None:
                event.last_zero_combat_at = now
                event.version += 1

    # ------------------------------------------------------------ ações

    async def register_action(
        self,
        actor: int,
        round_number: int,
        action_type: str,
        *,
        art_slot: int | None = None,
        target_ref: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Registra a ação da oportunidade. Repetir a mesma ação é idempotente (``False``)."""
        now = _utc(now)
        if action_type not in ACTION_TYPES:
            raise FlageloError("invalid_action")
        if (action_type == "art") != (art_slot is not None) or (
            art_slot is not None and not 1 <= art_slot <= 3
        ):
            raise FlageloError("invalid_action")
        if target_ref is not None and len(target_ref) > 64:
            raise FlageloError("invalid_action")
        async with self.sessions.begin() as session:
            event = await self.active_event(session, lock=True)
            if event is None:
                raise FlageloError("no_flagelo")
            round_ = await session.scalar(
                select(FlageloRound)
                .where(
                    FlageloRound.flagelo_id == event.id,
                    FlageloRound.round_number == round_number,
                )
                .with_for_update()
            )
            if round_ is None or round_.state != OPEN or now > round_.decision_deadline:
                raise FlageloError("window_closed")
            character = await self._character(session, actor)
            participant = await session.get(
                FlageloParticipant, (event.id, character.id), with_for_update=True
            )
            if participant is None or not participant.in_combat:
                raise FlageloError("not_in_combat")
            if round_number < participant.acts_from_round:
                raise FlageloError("waiting_next_round")
            action_id = uuid5(NAMESPACE_URL, f"flagelo:{round_.id}:{character.id}")
            existing = await session.get(FlageloAction, action_id)
            if existing is not None:
                if (existing.action_type, existing.art_slot, existing.target_ref) != (
                    action_type,
                    art_slot,
                    target_ref,
                ):
                    raise FlageloError("already_registered")
                return False
            session.add(
                FlageloAction(
                    id=action_id,
                    round_id=round_.id,
                    character_id=character.id,
                    action_type=action_type,
                    art_slot=art_slot,
                    target_ref=target_ref,
                    registered_at=now,
                )
            )
            await session.flush()
            return True

    # ------------------------------------------------------------ rodadas

    async def open_round(self, *, now: datetime | None = None) -> FlageloRound | None:
        """Abre a próxima oportunidade se há combatentes e nenhuma rodada aberta.

        A IA escolhe a ação do Flagelo na abertura (a Preparada é anunciada durante a janela,
        como no Véu/motor: uma janela de resposta antes do golpe).
        """
        now = _utc(now)
        async with self.sessions.begin() as session:
            event = await self.active_event(session, lock=True)
            if event is None:
                return None
            unresolved = await session.scalar(
                select(FlageloRound).where(
                    FlageloRound.flagelo_id == event.id, FlageloRound.state != RESOLVED
                )
            )
            if unresolved is not None:
                return None
            present = list(
                (
                    await session.scalars(
                        select(FlageloParticipant.character_id).where(
                            FlageloParticipant.flagelo_id == event.id,
                            FlageloParticipant.in_combat.is_(True),
                        )
                    )
                ).all()
            )
            if not present:
                return None
            number = event.round_number + 1
            state = event.enemy_state or {}
            chosen = fl.choose_action(
                event.flagelo_id,
                cooldowns={k: int(v) for k, v in state.get("cooldowns", {}).items()},
                uses={k: int(v) for k, v in state.get("uses", {}).items()},
                hp=Decimal(event.hp_current),
                max_hp=Decimal(event.max_hp),
            )
            seed = fl.seed_for(str(event.id), number)
            targets = fl.choose_targets(chosen, present, seed)
            round_ = FlageloRound(
                flagelo_id=event.id,
                round_number=number,
                state=OPEN,
                opened_at=now,
                decision_deadline=now + fl.DECISION_WINDOW,
                boss_snapshot=_boss_snapshot(event),
                decision={
                    "action_key": chosen.key,
                    "targets": [str(target) for target in targets],
                    "telegraph": chosen.prepared,
                    "seed": seed,
                },
                result={},
            )
            session.add(round_)
            event.round_number = number
            event.version += 1
            await session.flush()
            return round_

    async def due_rounds(self, now: datetime) -> list[UUID]:
        async with self.sessions() as session:
            rows = await session.scalars(
                select(FlageloRound.id)
                .join(FlageloEvent, FlageloEvent.id == FlageloRound.flagelo_id)
                .where(
                    FlageloEvent.server_id == self.server_id,
                    FlageloRound.state != RESOLVED,
                    FlageloRound.decision_deadline <= now,
                )
                .order_by(FlageloRound.round_number)
            )
            return list(rows.all())

    async def resolve_round(self, round_id: UUID, *, now: datetime | None = None) -> bool:
        """Resolve a oportunidade uma única vez. ``True`` se resolveu agora."""
        now = _utc(now)
        async with self.sessions.begin() as session:
            probe = await session.get(FlageloRound, round_id)
            if probe is None:
                return False
            event_probe = await session.get(FlageloEvent, probe.flagelo_id)
            if event_probe is None or event_probe.server_id != self.server_id:
                return False
            progress = await self._lock_progress(session, [event_probe.region_id])
            event = await session.scalar(
                select(FlageloEvent)
                .where(FlageloEvent.id == probe.flagelo_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            round_ = await session.scalar(
                select(FlageloRound)
                .where(FlageloRound.id == round_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if round_.state == RESOLVED:
                return False
            if round_.state == OPEN and now < round_.decision_deadline:
                raise FlageloError("window_open")
            round_.state = RESOLVING
            if event.status != "active":
                # Morte já registrada (callback antigo): fecha sem combate.
                round_.state, round_.resolved_at = RESOLVED, now
                return True
            history = await self._resolve_combat(session, event, round_, now)
            round_.result = {"history": history}
            round_.state, round_.resolved_at = RESOLVED, now
            if event.hp_current <= 0:
                await self._defeat(session, event, progress[event.region_id], now)
            else:
                await session.flush()
                await self._mark_idle_if_empty(session, event, now)
            return True

    async def _resolve_combat(self, session, event, round_, now: datetime) -> list[dict]:
        definition = fl.FLAGELOS_BY_ID[event.flagelo_id].flagelo
        snapshot = round_.boss_snapshot
        stats = CombatStats(
            Decimal(snapshot["max_hp"]),
            Decimal(snapshot["attack"]),
            Decimal(snapshot["defense"]),
            Decimal(snapshot["agility"]),
        )
        state = dict(event.enemy_state or {})
        boss = BossEffects.from_data(state.get("player_effects"))
        code = event.flagelo_id
        unit = vc.EnemyUnit.from_data(
            code,
            {
                **state.get("unit", {}),
                "hp": str(event.hp_current),
                "max_hp": str(snapshot["max_hp"]),
                # ATQ/DEF com os efeitos que jogadores aplicaram (``Fighter.stat`` do motor).
                "attack": str(boss.stat(stats, "attack")),
                "defense": str(snapshot["defense"]),
                "agility": str(snapshot["agility"]),
            },
        )
        participants = list(
            (
                await session.scalars(
                    select(FlageloParticipant)
                    .where(
                        FlageloParticipant.flagelo_id == event.id,
                        FlageloParticipant.in_combat.is_(True),
                    )
                    .order_by(FlageloParticipant.character_id)
                    .with_for_update()
                )
            ).all()
        )
        acting = [p for p in participants if round_.round_number >= p.acts_from_round]
        actions = list(
            (
                await session.scalars(
                    select(FlageloAction).where(FlageloAction.round_id == round_.id)
                )
            ).all()
        )
        acting_ids = {p.character_id for p in acting}
        actions = [action for action in actions if action.character_id in acting_ids]
        await self._record_observations(session, definition, {a.character_id for a in actions})
        decisions = self._decisions(event, round_, unit, participants)
        enemies = {code: unit}
        players: dict[UUID, vc.PlayerUnit] = {}
        intents: list[vc.PlayerIntent] = []
        simulator = None
        if self.simulator is not None and participants:
            simulator = self.simulator(definition.level, boss)
            inputs = await simulator.prepare(
                session, participants, actions, enemies, f"{event.id}|{round_.round_number}"
            )
            players, intents = inputs.players, inputs.intents
        outcome = vc.resolve_batch(
            enemies,
            players,
            intents,
            decisions,
            kit=fl.kit,
            level=definition.level,
            # Esquiva global (espec. final §3): semente da ocorrência e da rodada.
            evasion_seed=f"{event.id}|{round_.round_number}",
        )
        # Efeitos de jogadores no Flagelo: ticks dos DoTs carregados, envelhecimento e os novos.
        merged = simulator.merged() if isinstance(simulator, FlageloRoundSimulator) else boss
        next_boss, ticks = next_boss_state(boss, merged, boss.stat(stats, "defense"))
        dot_credit: dict[UUID, int] = {}
        for source, damage in ticks:
            effective = int(min(Decimal(damage), max(unit.hp, Decimal(0))))
            if effective <= 0:
                continue
            unit.hp -= effective
            try:
                credited = UUID(source)
            except ValueError:
                continue
            dot_credit[credited] = dot_credit.get(credited, 0) + effective
            outcome.history.append({"kind": "boss_dot", "amount": effective})
        event.hp_current = max(0, int(unit.hp))
        state["unit"] = {
            key: value
            for key, value in unit.to_data().items()
            if key not in {"hp", "max_hp", "attack", "defense", "agility"}
        }
        state["cooldowns"] = dict(unit.cooldowns)
        state["uses"] = dict(unit.uses)
        state["player_effects"] = next_boss.to_data()
        event.enemy_state = state
        event.version += 1
        self._credit(participants, actions, outcome, intents, dot_credit, now)
        released: list[UUID] = []
        for participant in participants:
            player = players.get(participant.character_id)
            if player is not None:
                participant.hp = player.hp
                participant.combat_state = player.state_data()
            if participant.character_id in outcome.defeated_players or (
                player is not None and player.hp <= 0
            ):
                self._exit(participant, now, defeated=True)
                released.append(participant.character_id)
                continue
            if participant in acting:
                if any(a.character_id == participant.character_id for a in actions):
                    participant.idle_rounds = 0
                else:
                    participant.idle_rounds += 1
                    if participant.idle_rounds >= fl.INACTIVE_ROUNDS:
                        self._exit(participant, now)
                        released.append(participant.character_id)
        await self._release_activities(session, released)
        return outcome.history

    @staticmethod
    def _decisions(event, round_, unit, participants) -> list[vc.EnemyDecisionData]:
        """A ação comprometida na abertura; recalcula alvo/ação se o estado mudou."""
        decision = round_.decision or {}
        key = decision.get("action_key")
        if not key:
            return []
        present = sorted(p.character_id for p in participants)
        chosen = fl.action(event.flagelo_id, key)
        skipped: list[str] = []
        while True:
            executable = not (chosen.kind is ActionKind.HEAL and unit.hp >= unit.max_hp)
            if executable:
                break
            skipped.append(chosen.key)
            chosen = fl.choose_action(
                event.flagelo_id,
                cooldowns=unit.cooldowns,
                uses=unit.uses,
                hp=unit.hp,
                max_hp=unit.max_hp,
                skip=skipped,
            )
        targets = [UUID(value) for value in decision.get("targets", ()) if UUID(value) in present]
        if chosen.key != key or (
            not targets
            and chosen.kind
            not in (
                ActionKind.SELF_BUFF,
                ActionKind.HEAL,
                ActionKind.BARRIER,
            )
        ):
            targets = list(fl.choose_targets(chosen, present, int(decision.get("seed", 0))))
        return [vc.EnemyDecisionData(event.flagelo_id, chosen.key, tuple(targets), chosen.prepared)]

    @staticmethod
    def _credit(participants, actions, outcome, intents, dot_credit, now: datetime) -> None:
        """Métricas reais do motor/lote: dano efetivo, cura efetiva, Barreira absorvida, dano
        prevenido pelo Defender e aplicação significativa de efeito (§12, §13)."""
        by_id = {p.character_id: p for p in participants}
        effects: dict[UUID, int] = {}
        for intent in intents:
            if intent.effect_applied:
                effects[intent.character_id] = effects.get(intent.character_id, 0) + 1
            if any(result.kind == "protection" for result in intent.support):
                effects[intent.character_id] = effects.get(intent.character_id, 0) + 1
        stamp = now.isoformat()
        for character_id, participant in by_id.items():
            before = {
                category: fl.ranking_metric(category, _metrics(participant))
                for category in fl.RANKING_CATEGORIES
            }
            participant.effective_damage += outcome.damage_by_character.get(
                character_id, 0
            ) + dot_credit.get(character_id, 0)
            participant.effective_healing += outcome.heal_by_character.get(character_id, 0)
            participant.barrier_absorbed += outcome.barrier_absorbed_for.get(character_id, 0)
            participant.defender_prevented_damage += outcome.prevented_by_character.get(
                character_id, 0
            )
            participant.meaningful_effects += effects.get(character_id, 0)
            metrics = _metrics(participant)
            participant.participation_points = fl.participation_points(metrics)
            stamps = dict(participant.first_metric_timestamps or {})
            for category in fl.RANKING_CATEGORIES:
                if fl.ranking_metric(category, metrics) > before[category]:
                    stamps[category] = stamp
            participant.first_metric_timestamps = stamps
        # Dano de DoT de quem já saiu do combate também é efetivo.
        missing = set(dot_credit) - set(by_id)
        if missing:
            outcome.history.append({"kind": "dot_credit_pending", "count": len(missing)})

    async def _record_observations(self, session, definition, character_ids: set[UUID]):
        """Primeira observação no Bestiário quando o personagem age validamente (como o Véu)."""
        if not character_ids:
            return
        known = set(
            (
                await session.scalars(
                    select(BestiaryEntry.character_id).where(
                        BestiaryEntry.character_id.in_(character_ids),
                        BestiaryEntry.creature_id == definition.bestiary_key,
                    )
                )
            ).all()
        )
        recorder = BestiaryRecorder()
        for character_id in sorted(character_ids - known, key=str):
            await recorder.record(session, character_id, definition.bestiary_key)

    # ------------------------------------------------------------ morte

    async def _defeat(self, session, event, bar, now: datetime) -> None:
        """Morte registrada uma vez: congela o resultado, calcula ranking e o sorteio do
        equipamento, zera a barra da região e abre o novo ciclo, na mesma transação."""
        if event.status != "active":
            return
        participants = list(
            (
                await session.scalars(
                    select(FlageloParticipant)
                    .where(FlageloParticipant.flagelo_id == event.id)
                    .order_by(FlageloParticipant.character_id)
                    .with_for_update()
                )
            ).all()
        )
        for participant in participants:
            if participant.in_combat:
                participant.in_combat = False
        await self._release_activities(session, [p.character_id for p in participants])
        eligible = [p for p in participants if fl.is_eligible(_metrics(p))]
        names = {
            row.id: row.name
            for row in (
                await session.scalars(
                    select(Character).where(
                        Character.id.in_([p.character_id for p in participants])
                    )
                )
            ).all()
        }
        rankings = {}
        entries = [
            fl.RankingEntry(
                p.character_id,
                _metrics(p),
                None,
            )
            for p in participants
        ]
        stamps = {p.character_id: p.first_metric_timestamps or {} for p in participants}
        for category in fl.RANKING_CATEGORIES:
            dated = [
                fl.RankingEntry(
                    entry.character_id,
                    entry.metrics,
                    datetime.fromisoformat(stamps[entry.character_id][category])
                    if category in stamps[entry.character_id]
                    else None,
                )
                for entry in entries
            ]
            rankings[category] = [
                {
                    "position": index,
                    "character_id": str(entry.character_id),
                    "name": names.get(entry.character_id, ""),
                    "value": fl.ranking_metric(category, entry.metrics),
                }
                for index, entry in enumerate(fl.rank(category, dated), start=1)
            ]
        winner = fl.equipment_winner(str(event.id), [p.character_id for p in eligible])
        event.status = "defeated"
        event.hp_current = 0
        event.defeated_at = now
        event.lifetime_seconds = max(0, int((now - event.spawned_at).total_seconds()))
        event.rankings = rankings
        event.equipment_winner_id = winner
        event.equipment_status = None if winner is None else "rolled"
        event.last_zero_combat_at = None
        event.version += 1
        bar.current_points = 0
        bar.active_flagelo_id = None
        bar.threshold_reached_at = None
        bar.last_defeated_at = now
        bar.cycle += 1
        bar.version += 1
        bar.updated_at = now
        self._notice(session, "defeat", event.id, event.region_id)

    # ------------------------------------------------------------ liquidação

    async def settle(self, event_id: UUID, *, now: datetime | None = None) -> int:
        """Paga cada participante uma única vez; restart retoma de onde parou."""
        now = _utc(now)
        async with self.sessions() as session:
            event = await session.get(FlageloEvent, event_id)
            if event is None or event.status != "defeated":
                return 0
            ids = list(
                (
                    await session.scalars(
                        select(FlageloParticipant.character_id)
                        .where(
                            FlageloParticipant.flagelo_id == event_id,
                            FlageloParticipant.settled_at.is_(None),
                        )
                        .order_by(FlageloParticipant.character_id)
                    )
                ).all()
            )
        paid = 0
        for character_id in ids:
            paid += await self._settle_one(event_id, character_id, now)
        async with self.sessions.begin() as session:
            event = await session.scalar(
                select(FlageloEvent).where(FlageloEvent.id == event_id).with_for_update()
            )
            pending = await session.scalar(
                select(func.count())
                .select_from(FlageloParticipant)
                .where(
                    FlageloParticipant.flagelo_id == event_id,
                    FlageloParticipant.settled_at.is_(None),
                )
            )
            if event.status == "defeated" and not pending:
                event.status = "settled"
                event.settled_at = now
                event.version += 1
        return paid

    async def _grant_once(
        self, session, event, character, reward_type: str, status: str, payload: dict
    ) -> bool:
        result = await session.execute(
            insert(FlageloRewardSettlement)
            .values(
                flagelo_id=event.id,
                character_id=character.id,
                reward_type=reward_type,
                settlement_key=f"flagelo:{event.id.hex}:{character.id.hex}:{reward_type}",
                status=status,
                payload=payload,
            )
            .on_conflict_do_nothing()
            .returning(FlageloRewardSettlement.reward_type)
        )
        return result.first() is not None

    async def _settle_one(self, event_id: UUID, character_id: UUID, now: datetime) -> int:
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
            participant = await session.scalar(
                select(FlageloParticipant)
                .where(
                    FlageloParticipant.flagelo_id == event_id,
                    FlageloParticipant.character_id == character_id,
                )
                .with_for_update()
            )
            if character is None or participant is None or participant.settled_at is not None:
                return 0
            event = await session.get(FlageloEvent, event_id)
            region = fl.region(event.region_id)
            definition = region.flagelo
            eligible = fl.is_eligible(_metrics(participant))
            reward: dict = {"items": []}
            paid = False
            if eligible:
                key = f"flagelo:{event.id.hex}:{character.id.hex}"
                if await self._grant_once(session, event, character, "base", "granted", {}):
                    paid = True
                    granted = await grant_bundle(
                        session,
                        character,
                        fl.reward_bundle(region.reference_level),
                        f"{key}:base",
                        region=region.region,
                    )
                    xp = fl.reward_xp(level_xp(region.reference_level))
                    character.xp += xp
                    await self._fragment(
                        session, character, definition, fl.REWARD_FLAGELO_FRAGMENTS, f"{key}:base"
                    )
                    reward["crowns"] = granted.crowns
                    reward["xp"] = xp
                    reward["items"].extend(
                        {"name": item.name, "quantity": item.quantity} for item in granted.items
                    )
                    reward["items"].append(
                        {"name": definition.fragment_name, "quantity": fl.REWARD_FLAGELO_FRAGMENTS}
                    )
                for category in fl.RANKING_CATEGORIES:
                    for entry in event.rankings.get(category, ()):
                        if entry["character_id"] != str(character.id):
                            continue
                        fragments, basics = fl.RANKING_REWARDS[int(entry["position"])]
                        reward_type = f"ranking:{category}"
                        if not await self._grant_once(
                            session,
                            event,
                            character,
                            reward_type,
                            "granted",
                            {"position": int(entry["position"])},
                        ):
                            continue
                        granted = await grant_bundle(
                            session,
                            character,
                            Bundle(basics=basics),
                            f"{key}:{reward_type}",
                            region=region.region,
                        )
                        await self._fragment(
                            session, character, definition, fragments, f"{key}:{reward_type}"
                        )
                        reward["items"].extend(
                            {"name": item.name, "quantity": item.quantity} for item in granted.items
                        )
                        reward["items"].append(
                            {"name": definition.fragment_name, "quantity": fragments}
                        )
                        reward.setdefault("rankings", []).append(
                            {"category": category, "position": int(entry["position"])}
                        )
                if event.equipment_winner_id == character.id:
                    reward["equipment"] = await self._equipment(
                        session, event, character, region, definition
                    )
                await self._recipe(session, event, character, definition, reward)
                await consolidate_character_level(session, character)
                await self._knowledge(session, character, definition)
            participant.eligible = eligible
            if paid or not eligible:
                participant.reward = reward if eligible else {}
            participant.settled_at = now
            return 1 if paid else 0

    async def _equipment(self, session, event, character, region, definition) -> dict | None:
        """O único equipamento da morte (espec. final §6/§11): template 1/9, +0, materializado
        pelo materializador global (núcleo, secundários e metadata de arma), no nível de
        referência do Flagelo. Entrega pelo caminho comum (Inventário → Pendentes → retenção).
        """
        template_id = fl.equipment_template(str(event.id), definition.flagelo_id)
        template = catalog.TEMPLATES_BY_ID[template_id]
        source_key = f"flagelo:{event.id.hex}:equipment"
        if not await self._grant_once(
            session, event, character, "equipment", "granted", {"template_id": template_id}
        ):
            return None
        payload = materialize_equipment(
            source_key,
            template.rarity,
            region.reference_level,
            forced_name=template.name,
            forced_slot=template.slot,
            bound=True,
            weapon_type_id=template.weapon_type_id,
        )
        payload["template_id"] = template_id
        payload["catalog_item_id"] = template_id
        instance_id, instance = equipment_instance_payload(
            payload, instance_id=uuid5(NAMESPACE_URL, source_key)
        )
        await return_to_owner(
            session,
            character,
            "equipment",
            {
                "id": str(instance_id),
                "source_key": source_key,
                "item_name": instance["item_name"],
                "rarity": instance["rarity"],
                "slot": instance["slot"],
                "item_level": instance["item_level"],
                "bound": True,
                "payload": instance,
            },
            1,
            source_key,
        )
        return {
            "template_id": template_id,
            "name": template.name,
            "rarity": template.rarity,
            "slot": template.slot,
            "item_id": str(instance_id),
        }

    async def _fragment(self, session, character, definition, quantity: int, key: str) -> None:
        if quantity <= 0:
            return
        await return_to_owner(
            session,
            character,
            "material",
            {"material_id": definition.fragment_material_id, "bound": True},
            quantity,
            f"{key}:{definition.fragment_material_id}",
        )

    async def _recipe(self, session, event, character, definition, reward: dict) -> None:
        """Espec. final §12: enquanto houver Receita desconhecida daquele Flagelo, 25% por
        morte; uma desconhecida, uniforme; no máximo uma por morte; sem pity; com as 9
        conhecidas não há sorteio. As Receitas são conhecimento do personagem (``Unlock``,
        o mesmo vínculo das Receitas especiais do Crafting), então o sorteio é por elegível.
        """
        recipes = definition.recipe_unlock_ids()
        known = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(
                        Unlock.character_id == character.id, Unlock.unlock_id.in_(recipes)
                    )
                )
            ).all()
        )
        unknown = [recipe for recipe in recipes if recipe not in known]
        found = fl.recipe_roll(str(event.id), character.id, unknown)
        status = "granted" if found else "skipped"
        payload = {"recipe": found} if found else ({} if unknown else {"reason": "all_known"})
        if not await self._grant_once(session, event, character, "recipe", status, payload):
            return
        if found:
            session.add(Unlock(character_id=character.id, unlock_id=found))
            reward["recipe"] = found
            reward["recipe_name"] = catalog.TEMPLATES_BY_RECIPE[found].name

    async def _knowledge(self, session, character, definition) -> None:
        """Bestiário: derrota + material associado; Códice: a entrada geral do evento e a do
        Flagelo, com o texto aprovado (espec. final §16) como fragmento da entrada."""
        await BestiaryRecorder().record(
            session,
            character.id,
            definition.bestiary_key,
            victory=True,
            evidence_id=f"material:{definition.fragment_material_id}",
            evidence_category="material",
        )
        for text in (flagelo_lore.GENERAL_CODEX, flagelo_lore.FLAGELO_CODEX[definition.flagelo_id]):
            await session.execute(
                insert(CodexEntry)
                .values(id=uuid4(), character_id=character.id, entry_id=text.entry_id)
                .on_conflict_do_nothing(constraint="uq_character_codex")
            )
            await session.execute(
                insert(CodexFragment)
                .values(
                    id=uuid4(),
                    character_id=character.id,
                    entry_id=text.entry_id,
                    fragment_id=text.fragment_id,
                )
                .on_conflict_do_nothing(constraint="uq_character_fragment")
            )

    # ------------------------------------------------------------ escalonamento

    async def apply_scaling(self, *, now: datetime | None = None) -> int:
        """§8: +8% HP Máximo e +3% ATQ a cada 15 min completos sem ninguém em combate.

        Não cura (o HP atual não muda), DEF e AGI não mudam, para no teto (+80% / +30%) e só
        volta a zero com um novo Flagelo. Idempotente: o tempo já usado avança ``idle_since``.
        """
        now = _utc(now)
        async with self.sessions.begin() as session:
            event = await self.active_event(session, lock=True)
            if event is None:
                return 0
            count = await self._combatants(session, event.id)
            if count > 0:
                if event.last_zero_combat_at is not None:
                    event.last_zero_combat_at = None
                return 0
            if event.last_zero_combat_at is None:
                event.last_zero_combat_at = now
                return 0
            steps = fl.due_steps(event.abandonment_steps, event.last_zero_combat_at, now, count)
            if steps <= 0:
                return 0
            event.abandonment_steps += steps
            scaling = fl.scaling_for_steps(event.abandonment_steps)
            event.hp_scaling_bonus = scaling.hp_bonus
            event.atq_scaling_bonus = scaling.atq_bonus
            event.max_hp = fl.effective_max_hp(event.base_hp, scaling.hp_bonus)
            event.attack = fl.effective_attack(event.base_atq, scaling.atq_bonus)
            event.last_zero_combat_at = event.last_zero_combat_at + fl.SCALING_INTERVAL * steps
            event.version += 1
            return steps

    # ------------------------------------------------------------ telas

    async def combat_screen(self, actor: int, *, now: datetime | None = None) -> CombatScreen:
        now = _utc(now)
        async with self.sessions() as session:
            event = await self.active_event(session)
            if event is None:
                raise FlageloError("no_flagelo")
            character = await self._character(session, actor)
            participant = await session.get(FlageloParticipant, (event.id, character.id))
            if participant is None or not participant.in_combat:
                raise FlageloError("not_in_combat")
            open_round = await session.scalar(
                select(FlageloRound).where(
                    FlageloRound.flagelo_id == event.id, FlageloRound.state != RESOLVED
                )
            )
            last = await session.scalar(
                select(FlageloRound)
                .where(FlageloRound.flagelo_id == event.id, FlageloRound.state == RESOLVED)
                .order_by(FlageloRound.round_number.desc())
                .limit(1)
            )
            acted = False
            if open_round is not None:
                acted = (
                    await session.scalar(
                        select(FlageloAction.id).where(
                            FlageloAction.round_id == open_round.id,
                            FlageloAction.character_id == character.id,
                        )
                    )
                    is not None
                )
            telegraph = None
            if open_round is not None and (open_round.decision or {}).get("telegraph"):
                telegraph = fl.action(event.flagelo_id, open_round.decision["action_key"]).label
            arts = await load_active_art_configuration(session, character, lock_rows=False)
            slots = tuple(
                int(entry["slot"])
                for entry in arts.to_data().get("active_arts", ())
                if isinstance(entry, dict) and entry.get("slot")
            )
            number = open_round.round_number if open_round else event.round_number
            hp = participant.hp if participant.hp is not None else character.max_hp
            return CombatScreen(
                event.id,
                fl.region(event.region_id).flagelo.name,
                number,
                _seconds(open_round.decision_deadline, now) if open_round else 0,
                event.hp_current,
                event.max_hp,
                character.name,
                int(hp),
                int(character.max_hp),
                slots,
                acted,
                number < participant.acts_from_round,
                telegraph,
                tuple(last.result.get("history", ())) if last is not None else (),
                participant.participation_points,
                event.abandonment_steps,
                _metrics(participant),
            )

    async def art_target_mode(self, actor: int, slot: int) -> str | None:
        """Modo de alvo da Arte no slot, pelo catálogo do motor (o mesmo usado pelo Véu)."""
        from asterion.application.equipment_configuration import load_equipment_configuration
        from asterion.domain.class_trials import class_player_actions

        async with self.sessions() as session:
            character = await self._character(session, actor)
            arts = await load_active_art_configuration(session, character, lock_rows=False)
            ids = list(arts.art_ids)
            if not 0 < slot <= len(ids):
                return None
            equipment = await load_equipment_configuration(session, character)
            actions = class_player_actions(
                character.character_class, tuple(ids), selected_path=equipment.selected_path
            )
            action = actions.get(ids[slot - 1])
            return action.target_mode if action is not None else None

    async def allies(self, actor: int, limit: int = 8) -> list[tuple[UUID, str]]:
        """Outros combatentes presentes (alvo de Arte aliada), por nome."""
        async with self.sessions() as session:
            event = await self.active_event(session)
            if event is None:
                return []
            me = await self._character(session, actor)
            rows = await session.execute(
                select(Character.id, Character.name)
                .join(FlageloParticipant, FlageloParticipant.character_id == Character.id)
                .where(
                    FlageloParticipant.flagelo_id == event.id,
                    FlageloParticipant.in_combat.is_(True),
                    Character.id != me.id,
                )
                .order_by(Character.name)
                .limit(limit)
            )
            return [(row[0], row[1]) for row in rows.all()]

    async def names(self, character_ids: Sequence[str]) -> dict[str, str]:
        ids = []
        for value in character_ids:
            try:
                ids.append(UUID(value))
            except (TypeError, ValueError):
                continue
        if not ids:
            return {}
        async with self.sessions() as session:
            rows = await session.execute(
                select(Character.id, Character.name).where(Character.id.in_(ids))
            )
            return {str(row[0]): row[1] for row in rows.all()}

    # ------------------------------------------------------------ upkeep

    async def unsettled(self) -> list[UUID]:
        async with self.sessions() as session:
            rows = await session.scalars(
                select(FlageloEvent.id)
                .where(FlageloEvent.server_id == self.server_id, FlageloEvent.status == "defeated")
                .order_by(FlageloEvent.defeated_at)
            )
            return list(rows.all())

    async def tick(self, *, now: datetime | None = None) -> UpkeepReport:
        """Ciclo do job: contribuições/spawn, rodadas vencidas, morte, escalonamento, nova
        rodada e liquidação. Cada passo é idempotente; um restart retoma do estado salvo."""
        now = _utc(now)
        applied, spawned = await self.apply_contributions(now=now)
        async with self.sessions.begin() as session:
            await self._release_orphans(session)  # nenhum lock fantasma depois de um restart
        resolved = 0
        defeated: list[UUID] = []
        for round_id in await self.due_rounds(now):
            if await self.resolve_round(round_id, now=now):
                resolved += 1
        async with self.sessions() as session:
            just_defeated = list(
                (
                    await session.scalars(
                        select(FlageloEvent.id).where(
                            FlageloEvent.server_id == self.server_id,
                            FlageloEvent.status == "defeated",
                        )
                    )
                ).all()
            )
        defeated.extend(just_defeated)
        if just_defeated:
            # Novo ciclo imediato: outra região já em 500/500 desperta agora.
            more_applied, more = await self.apply_contributions(now=now)
            applied += more_applied
            spawned = (*spawned, *more)
        scaled = await self.apply_scaling(now=now)
        opened = 1 if await self.open_round(now=now) is not None else 0
        settled = 0
        for event_id in await self.unsettled():
            settled += await self.settle(event_id, now=now)
        return UpkeepReport(
            applied, tuple(spawned), resolved, opened, scaled, tuple(defeated), settled
        )

    async def notice_payload(self, event_id: UUID) -> tuple[str, str, str] | None:
        """(nome completo, nome curto, Região) para o texto da notificação."""
        async with self.sessions() as session:
            event = await session.get(FlageloEvent, event_id)
            if event is None:
                return None
            region = fl.region(event.region_id)
            return region.flagelo.name, region.flagelo.short_name, region.region
