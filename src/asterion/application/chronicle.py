"""Crônica I, its Trilha and its vote (GDD v1.6.0 §5, §5.1–5.4, §49.14, §49.16).

Scopes:
- narrative state (objectives, chapter conclusions) belongs to the character;
- Trilha points, claims, the Passe, the vote and vote eligibility belong to
  ``conta + servidor + Crônica``; eligibility reads the account's point ledger, which
  survives a character deletion. Recreating a character replays the story, never
  the points: every grant is keyed by ``source_key`` per account, so callbacks,
  retries and jobs never pay twice.

Sources call ``record_objective`` and ``record_repeatable`` inside their own
transaction, after their own settlement. Both return quietly when the Crônica is
not accepting progress, so a source never fails because of it.

Lock order: ChronicleCycle (maintenance only) -> Character -> ChronicleAccount.
Finalization also takes the Arena and Batalha de Guildas advisory locks first.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.competitive_cycle import advisory_key, current_cycle_started_at
from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.application.engagement import EngagementError, Granted, GrantedItem, grant_bundle
from asterion.domain.arena import elo_for, soft_reset_renome
from asterion.domain.chronicle import (
    CHAPTER_COMPLETION_POINTS,
    CHAPTER_CONCLUSION_IDS,
    CHAPTERS,
    CHAPTERS_BY_NUMBER,
    CHRONICLE_COSMETICS_BY_ID,
    CHRONICLE_ID,
    ENTRY_GATE_QUEST,
    FINAL_PHASE_OBJECTIVES,
    LAYER_QUESTS,
    OBJECTIVES_BY_ID,
    PREMIUM_TRACK,
    REPEATABLE_POINTS,
    REPEATABLE_SOURCES,
    VOTE_OPTIONS,
    Calendar,
    Layer,
    Objective,
    Outcome,
    Phase,
    RepeatableSource,
    TrackReward,
    calendar_for,
    can_conclude,
    claimable,
    daily_cycle,
    elo_reward_tier,
    layers_for,
    milestones_reached,
    objectives_of,
    repeatable_cap,
    resolve_main,
    resolve_runoff,
    reward_for,
    shuffled_options,
    vote_eligible,
)
from asterion.domain.engagement import Bundle
from asterion.domain.guild_battle import (
    REWARD_COSMETICS,
    StandingCandidate,
    guild_reward_tier,
    individual_reward_eligible,
    order_standings,
    reward_eligible,
)
from asterion.infrastructure.db.models import (
    Achievement,
    ArenaProfile,
    Character,
    CharacterCosmetic,
    ChronicleAccount,
    ChronicleClaim,
    ChronicleCompletion,
    ChronicleCycle,
    ChronicleCycleLog,
    ChronicleElector,
    ChroniclePointGrant,
    ChronicleVote,
    Guild,
    GuildBattle,
    GuildBattleFight,
    GuildBattleFightMember,
    GuildBattleProfile,
    Quest,
    VigilHallEntry,
)

COSMETIC_SOURCE = "trilha_cr01"
ANSWER_FEAT = "feito_cr01_respondeu_ao_eco"  # pr_cr01_feito_resposta (§4.5).


class ChronicleError(EngagementError):
    """A Crônica action is invalid for the current, revalidated state."""


def _utcnow(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def calendar_of(cycle: ChronicleCycle) -> Calendar:
    return calendar_for(cycle.day1, cycle.end_at)


async def load_cycle(
    session: AsyncSession,
    server_id: str,
    *,
    chronicle_id: str = CHRONICLE_ID,
    lock: bool = False,
) -> ChronicleCycle | None:
    statement = select(ChronicleCycle).where(
        ChronicleCycle.server_id == server_id, ChronicleCycle.chronicle_id == chronicle_id
    )
    return await session.scalar(statement.with_for_update() if lock else statement)


async def completed_quests(session: AsyncSession, character_id: UUID) -> set[str]:
    return set(
        (
            await session.scalars(
                select(Quest.quest_id).where(
                    Quest.character_id == character_id,
                    Quest.status == "completed",
                    Quest.quest_id.in_([ENTRY_GATE_QUEST, *LAYER_QUESTS.values()]),
                )
            )
        ).all()
    )


async def pass_open(session: AsyncSession, server_id: str, now: datetime) -> bool:
    """The Passe can be bought only while the Crônica runs, before T (§5.2)."""
    cycle = await load_cycle(session, server_id)
    return cycle is not None and now < cycle.end_at


async def pass_active(session: AsyncSession, server_id: str, account_id: int) -> bool:
    row = await session.get(ChronicleAccount, (account_id, server_id, CHRONICLE_ID))
    return row is not None and row.premium_at is not None


async def grant_pass_in(
    session: AsyncSession, server_id: str, account_id: int, source: str, now: datetime
) -> tuple[datetime, bool]:
    """Activate the Passe inside the caller's transaction.

    Returns ``(premium_at, activated)``; ``activated`` is False when the Passe was
    already active, so the caller knows this grant changed nothing.
    """
    if not await pass_open(session, server_id, now):
        raise ChronicleError("chronicle_pass_closed")
    row = await _account_row(session, account_id, server_id, now)
    if row.premium_at is not None:
        return row.premium_at, False
    row.premium_at = now
    row.premium_source = source[:32]
    return row.premium_at, True


async def revoke_pass_in(
    session: AsyncSession, server_id: str, account_id: int, source: str
) -> tuple[int, ...] | None:
    """Undo a Passe granted by ``source`` (§35.1): the Premium layer, its claims and
    the Premium cosmetics they gave. Free-track rewards stay. Returns the revoked
    Premium milestones, or None when this source did not grant the active Passe."""
    row = await session.get(
        ChronicleAccount, (account_id, server_id, CHRONICLE_ID), with_for_update=True
    )
    if row is None or row.premium_at is None or row.premium_source != source[:32]:
        return None
    row.premium_at = None
    row.premium_source = None
    milestones = tuple(
        (
            await session.scalars(
                delete(ChronicleClaim)
                .where(
                    ChronicleClaim.account_id == account_id,
                    ChronicleClaim.server_id == server_id,
                    ChronicleClaim.chronicle_id == CHRONICLE_ID,
                    ChronicleClaim.track == "premium",
                )
                .returning(ChronicleClaim.milestone)
            )
        ).all()
    )
    premium_cosmetics = [
        reward.cosmetic_id for reward in PREMIUM_TRACK.values() if reward.cosmetic_id
    ]
    characters = select(Character.id).where(
        Character.telegram_id == account_id, Character.server_id == server_id
    )
    await session.execute(
        delete(CharacterCosmetic).where(
            CharacterCosmetic.character_id.in_(characters),
            CharacterCosmetic.source_achievement_id == COSMETIC_SOURCE,
            CharacterCosmetic.cosmetic_id.in_(premium_cosmetics),
        )
    )
    return tuple(sorted(milestones))


async def _account_row(
    session: AsyncSession, account_id: int, server_id: str, now: datetime
) -> ChronicleAccount:
    await session.execute(
        insert(ChronicleAccount)
        .values(
            account_id=account_id,
            server_id=server_id,
            chronicle_id=CHRONICLE_ID,
            points=0,
            repeatable_points=0,
            created_at=now,
        )
        .on_conflict_do_nothing()
    )
    row = await session.scalar(
        select(ChronicleAccount)
        .where(
            ChronicleAccount.account_id == account_id,
            ChronicleAccount.server_id == server_id,
            ChronicleAccount.chronicle_id == CHRONICLE_ID,
        )
        .with_for_update()
    )
    assert row is not None
    return row


async def _grant(
    session: AsyncSession,
    row: ChronicleAccount,
    *,
    source_key: str,
    source_id: str,
    points: int,
    repeatable: bool,
    character_id: UUID | None,
    now: datetime,
) -> int:
    inserted = await session.scalar(
        insert(ChroniclePointGrant)
        .values(
            account_id=row.account_id,
            server_id=row.server_id,
            chronicle_id=row.chronicle_id,
            source_key=source_key,
            source_id=source_id,
            repeatable=repeatable,
            points=points,
            character_id=character_id,
            cycle_date=daily_cycle(now),
            granted_at=now,
        )
        .on_conflict_do_nothing()
        .returning(ChroniclePointGrant.source_key)
    )
    if inserted is None:
        return 0
    row.points += points
    if repeatable:
        row.repeatable_points += points
    return points


def _objective_points(objective_id: str) -> tuple[int, int]:
    """(chapter, points) of an objective or a chapter conclusion."""
    if objective_id in CHAPTER_CONCLUSION_IDS:
        return CHAPTER_CONCLUSION_IDS[objective_id], CHAPTER_COMPLETION_POINTS
    objective = OBJECTIVES_BY_ID[objective_id]
    return objective.chapter, objective.points


async def _participates(session, character: Character, calendar: Calendar, now, started_at):
    if not calendar.playable(now, started_at):
        return False
    return ENTRY_GATE_QUEST in await completed_quests(session, character.id)


async def record_objective(
    session: AsyncSession,
    server_id: str,
    character: Character,
    objective_id: str,
    *,
    now: datetime,
    started_at: datetime | None = None,
) -> bool:
    """Register a unique objective (or a chapter conclusion) for one character.

    The caller holds the Character lock. Points go to the account only once,
    whichever of its characters completes it first.
    """
    if objective_id not in OBJECTIVES_BY_ID and objective_id not in CHAPTER_CONCLUSION_IDS:
        raise ValueError(f"unknown Crônica objective {objective_id}")
    cycle = await load_cycle(session, server_id)
    if cycle is None:
        return False
    calendar = calendar_of(cycle)
    chapter, points = _objective_points(objective_id)
    if calendar.chapter_opens_at(chapter) > (started_at or now):
        return False
    objective = OBJECTIVES_BY_ID.get(objective_id)
    if objective is not None and character.level < objective.min_level:
        return False
    if not await _participates(session, character, calendar, now, started_at):
        return False
    inserted = await session.scalar(
        insert(ChronicleCompletion)
        .values(
            character_id=character.id,
            chronicle_id=CHRONICLE_ID,
            objective_id=objective_id,
            account_id=character.telegram_id,
            server_id=server_id,
            completed_at=now,
        )
        .on_conflict_do_nothing()
        .returning(ChronicleCompletion.objective_id)
    )
    if inserted is None:
        return False
    if calendar.archived(now):
        # Crônica Arquivada: the story is recorded, never the points (§9).
        return True
    row = await _account_row(session, character.telegram_id, server_id, now)
    await _grant(
        session,
        row,
        source_key=objective_id,
        source_id=objective_id,
        points=points,
        repeatable=False,
        character_id=character.id,
        now=now,
    )
    return True


async def _repeatable_open(
    session: AsyncSession,
    server_id: str,
    account_id: int,
    repeatable_points: int,
    source: RepeatableSource,
    calendar: Calendar,
    now: datetime,
    started_at: datetime | None = None,
) -> bool:
    """Whether one more completion still fits the weekly cap and the daily limit."""
    cap = repeatable_cap(calendar.chapters_open(started_at or now))
    if repeatable_points + REPEATABLE_POINTS > cap:
        return False
    if source.daily_limit is None:
        return True
    today = await session.scalar(
        select(func.count())
        .select_from(ChroniclePointGrant)
        .where(
            ChroniclePointGrant.account_id == account_id,
            ChroniclePointGrant.server_id == server_id,
            ChroniclePointGrant.chronicle_id == CHRONICLE_ID,
            ChroniclePointGrant.source_id == source.source_id,
            ChroniclePointGrant.cycle_date == daily_cycle(now),
        )
    )
    return int(today or 0) < source.daily_limit


async def repeatable_available(
    session: AsyncSession,
    character: Character,
    source_id: str,
    calendar: Calendar,
    now: datetime,
) -> bool:
    """Read-only check, so a source can leave its result out once it would pay nothing."""
    if not calendar.accepts_progress(now):
        return False  # the ``rep_cr01_*`` sources end at the cutoff (§9)
    row = await session.get(
        ChronicleAccount, (character.telegram_id, character.server_id, CHRONICLE_ID)
    )
    return await _repeatable_open(
        session,
        character.server_id,
        character.telegram_id,
        0 if row is None else row.repeatable_points,
        REPEATABLE_SOURCES[source_id],
        calendar,
        now,
    )


async def record_repeatable(
    session: AsyncSession,
    server_id: str,
    character: Character,
    source_id: str,
    key: str,
    *,
    now: datetime,
    started_at: datetime | None = None,
) -> int:
    """25 points for one repeatable completion, within the daily and weekly limits.

    ``key`` identifies the run, occurrence, attempt or encounter instance, so the
    same completion never pays twice. The caller holds the Character lock and
    decides who "met the requirements" (an Ajudante never counts).
    """
    source = REPEATABLE_SOURCES[source_id]
    cycle = await load_cycle(session, server_id)
    if cycle is None:
        return 0
    calendar = calendar_of(cycle)
    if not await _participates(session, character, calendar, now, started_at):
        return 0
    row = await _account_row(session, character.telegram_id, server_id, now)
    if not await _repeatable_open(
        session, server_id, row.account_id, row.repeatable_points, source, calendar, now, started_at
    ):
        return 0
    return await _grant(
        session,
        row,
        source_key=f"{source_id}:{key}",
        source_id=source_id,
        points=REPEATABLE_POINTS,
        repeatable=True,
        character_id=character.id,
        now=now,
    )


# ---------------------------------------------------------------------- views


@dataclass(frozen=True, slots=True)
class ObjectiveView:
    objective: Objective
    done: bool
    level_locked: bool


@dataclass(frozen=True, slots=True)
class ChapterView:
    number: int
    title: str
    summary: str
    conclusion: str
    objectives: tuple[ObjectiveView, ...]
    concluded: bool
    can_conclude: bool


@dataclass(frozen=True, slots=True)
class VoteView:
    round: str | None
    eligible: bool
    chapters_concluded: int
    final_objectives: int
    choice: Outcome | None
    options: tuple[Outcome, ...]
    closes_at: datetime | None
    in_electorate: bool


@dataclass(frozen=True, slots=True)
class ChronicleView:
    phase: Phase
    calendar: Calendar | None
    chapters_open: int
    gate_ok: bool
    chapters: tuple[ChapterView, ...]
    points: int
    milestones: int
    claimable: int
    vote: VoteView | None
    outcome: Outcome | None
    layers: frozenset[Layer]


@dataclass(frozen=True, slots=True)
class TrackView:
    phase: Phase
    points: int
    milestones: int
    premium: bool
    claimed: frozenset[tuple[str, int]]
    claimable: tuple[tuple[str, int], ...]
    repeatable_points: int
    repeatable_cap: int
    can_claim: bool


@dataclass(frozen=True, slots=True)
class ClaimResult:
    milestones: tuple[tuple[str, int], ...]
    granted: Granted
    cosmetics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HallRow:
    position: int
    name: str
    rating: int
    elo: str | None
    matches: int
    points: int
    reward_eligible: bool
    reward_tier: str | None


@dataclass(frozen=True, slots=True)
class HallView:
    chronicle_id: str | None
    arena: tuple[HallRow, ...]
    guilds: tuple[HallRow, ...]
    own_arena: HallRow | None


@dataclass(frozen=True, slots=True)
class ChronicleHistory:
    """Profile line: what one account did in each finished Crônica (§26)."""

    chronicle_id: str
    chapters_concluded: int
    points: int
    voted: bool
    arena_elo: str | None


def _phase(cycle: ChronicleCycle | None, now: datetime) -> Phase:
    return Phase.UNSCHEDULED if cycle is None else calendar_of(cycle).phase(now)


class ChronicleService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    # ------------------------------------------------------------- player

    async def view(self, actor: int, *, now: datetime | None = None) -> ChronicleView:
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return await self._view(session, character, now)

    async def conclude_chapter(
        self, actor: int, chapter: int, *, now: datetime | None = None
    ) -> ChronicleView:
        """The short final scene: needs every mandatory objective of the chapter."""
        now = _utcnow(now)
        if chapter not in CHAPTERS_BY_NUMBER:
            raise ChronicleError("chronicle_unknown")
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            cycle = await load_cycle(session, self.server_id)
            if cycle is None or not calendar_of(cycle).playable(now):
                raise ChronicleError("chronicle_closed")
            if now < calendar_of(cycle).chapter_opens_at(chapter):
                raise ChronicleError("chronicle_chapter_locked")
            done = await self._completed(session, character.id)
            if CHAPTERS_BY_NUMBER[chapter].conclusion_id in done:
                raise ChronicleError("chronicle_already_concluded")
            if not can_conclude(chapter, done):
                raise ChronicleError("chronicle_objectives_missing")
            recorded = await record_objective(
                session,
                self.server_id,
                character,
                CHAPTERS_BY_NUMBER[chapter].conclusion_id,
                now=now,
            )
            if not recorded:
                raise ChronicleError("chronicle_gate")
            from asterion.application.chronicle_codex import sync_chronicle_codex

            await sync_chronicle_codex(session, character, now)
            return await self._view(session, character, now)

    async def track(self, actor: int, *, now: datetime | None = None) -> TrackView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            cycle = await load_cycle(session, self.server_id)
            await self._sync_cosmetics(session, character, now)
            return await self._track(session, cycle, character.telegram_id, now)

    async def claim(self, actor: int, *, now: datetime | None = None) -> ClaimResult:
        """Resgatar Disponíveis: every unlocked reward not delivered yet (§5.4)."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            cycle = await load_cycle(session, self.server_id)
            phase = _phase(cycle, now)
            if (
                cycle is None
                or cycle.liquidated_at is not None
                or phase
                not in (
                    Phase.ACTIVE,
                    Phase.CLOSING,
                    Phase.RESCUE,
                )
            ):
                raise ChronicleError("chronicle_claim_closed")
            row = await _account_row(session, character.telegram_id, self.server_id, now)
            result = await self._deliver(session, row, character, "claim", now)
            if not result.milestones:
                raise ChronicleError("nothing_to_claim")
            return result

    async def vote(self, actor: int, option: str, *, now: datetime | None = None) -> ChronicleView:
        now = _utcnow(now)
        try:
            choice = Outcome(option)
        except ValueError as exc:
            raise ChronicleError("chronicle_vote_invalid") from exc
        if choice not in VOTE_OPTIONS:
            raise ChronicleError("chronicle_vote_invalid")
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            cycle = await load_cycle(session, self.server_id)
            if cycle is None:
                raise ChronicleError("chronicle_vote_closed")
            round_ = calendar_of(cycle).vote_round(now)
            if round_ is None:
                raise ChronicleError("chronicle_vote_closed")
            if round_ == "main":
                chapters, finals = await self._account_progress(session, character.telegram_id)
                if not vote_eligible(chapters, finals):
                    raise ChronicleError("chronicle_vote_ineligible")
            else:
                if cycle.vote_closed_at is None:
                    raise ChronicleError("chronicle_vote_counting")
                options = tuple(Outcome(item) for item in (cycle.runoff_options or ()))
                if not options or cycle.runoff_closed_at is not None:
                    raise ChronicleError("chronicle_vote_closed")
                if choice not in options:
                    raise ChronicleError("chronicle_vote_invalid")
                if not await self._in_electorate(session, character.telegram_id):
                    raise ChronicleError("chronicle_vote_ineligible")
            statement = insert(ChronicleVote).values(
                account_id=character.telegram_id,
                server_id=self.server_id,
                chronicle_id=CHRONICLE_ID,
                round=round_,
                option=choice.value,
                character_id=character.id,
                updated_at=now,
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[
                        ChronicleVote.account_id,
                        ChronicleVote.server_id,
                        ChronicleVote.chronicle_id,
                        ChronicleVote.round,
                    ],
                    set_={
                        "option": statement.excluded.option,
                        "character_id": statement.excluded.character_id,
                        "updated_at": statement.excluded.updated_at,
                    },
                )
            )
            return await self._view(session, character, now)

    async def hall(self, actor: int) -> HallView:
        """Salão da Vigília: the snapshot of the last finalized Crônica."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            chronicle_id = await session.scalar(
                select(ChronicleCycle.chronicle_id)
                .where(
                    ChronicleCycle.server_id == self.server_id,
                    ChronicleCycle.finalized_at.is_not(None),
                )
                .order_by(ChronicleCycle.finalized_at.desc())
                .limit(1)
            )
            if chronicle_id is None:
                return HallView(None, (), (), None)
            rows = (
                await session.scalars(
                    select(VigilHallEntry)
                    .where(
                        VigilHallEntry.server_id == self.server_id,
                        VigilHallEntry.chronicle_id == chronicle_id,
                        VigilHallEntry.kind.in_(("arena", "guild_battle")),
                    )
                    .order_by(VigilHallEntry.kind, VigilHallEntry.position)
                )
            ).all()
            own = await session.scalar(
                select(VigilHallEntry).where(
                    VigilHallEntry.server_id == self.server_id,
                    VigilHallEntry.chronicle_id == chronicle_id,
                    VigilHallEntry.kind == "arena",
                    VigilHallEntry.subject_id == character.id,
                )
            )

            def view(row: VigilHallEntry) -> HallRow:
                return HallRow(
                    row.position,
                    row.name,
                    row.rating,
                    row.elo,
                    row.matches,
                    row.points,
                    row.reward_eligible,
                    row.reward_tier,
                )

            return HallView(
                chronicle_id,
                tuple(view(row) for row in rows if row.kind == "arena" and row.position <= 10),
                tuple(
                    view(row) for row in rows if row.kind == "guild_battle" and row.position <= 10
                ),
                None if own is None else view(own),
            )

    async def history(self, actor: int) -> tuple[ChronicleHistory, ...]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            cycles = (
                await session.scalars(
                    select(ChronicleCycle)
                    .where(
                        ChronicleCycle.server_id == self.server_id,
                        ChronicleCycle.finalized_at.is_not(None),
                    )
                    .order_by(ChronicleCycle.day1)
                )
            ).all()
            result = []
            for cycle in cycles:
                account = await session.get(
                    ChronicleAccount, (character.telegram_id, self.server_id, cycle.chronicle_id)
                )
                chapters = await session.scalar(
                    select(func.count()).where(
                        ChroniclePointGrant.account_id == character.telegram_id,
                        ChroniclePointGrant.server_id == self.server_id,
                        ChroniclePointGrant.chronicle_id == cycle.chronicle_id,
                        ChroniclePointGrant.source_id.in_(list(CHAPTER_CONCLUSION_IDS)),
                    )
                )
                voted = await session.scalar(
                    select(ChronicleVote.option)
                    .where(
                        ChronicleVote.account_id == character.telegram_id,
                        ChronicleVote.server_id == self.server_id,
                        ChronicleVote.chronicle_id == cycle.chronicle_id,
                    )
                    .limit(1)
                )
                elo = await session.scalar(
                    select(VigilHallEntry.elo)
                    .where(
                        VigilHallEntry.server_id == self.server_id,
                        VigilHallEntry.chronicle_id == cycle.chronicle_id,
                        VigilHallEntry.kind == "arena",
                        VigilHallEntry.account_id == character.telegram_id,
                    )
                    .limit(1)
                )
                if account is None and not chapters and elo is None:
                    continue
                result.append(
                    ChronicleHistory(
                        cycle.chronicle_id,
                        int(chapters or 0),
                        0 if account is None else account.points,
                        voted is not None,
                        elo,
                    )
                )
            return tuple(result)

    # -------------------------------------------------------- maintenance

    async def run_maintenance(self, *, now: datetime | None = None) -> None:
        """Vote close and snapshot, runoff, finalization at T+2h, liquidation at T+14d.

        Each step is idempotent through its own marker on the cycle row and runs
        in its own transaction, so a late or repeated job never repeats it.
        """
        now = _utcnow(now)
        for step in (self._close_vote, self._close_runoff, self._finalize, self._liquidate):
            async with self.sessions.begin() as session:
                cycle = await load_cycle(session, self.server_id, lock=True)
                if cycle is None:
                    return
                await step(session, cycle, calendar_of(cycle), now)

    async def _close_vote(self, session, cycle, calendar: Calendar, now) -> None:
        if cycle.vote_closed_at is not None or now < calendar.vote_closes_at:
            return
        cutoff = calendar.vote_closes_at
        rows = (
            await session.execute(
                select(ChroniclePointGrant.account_id, ChroniclePointGrant.source_id)
                .where(
                    ChroniclePointGrant.server_id == self.server_id,
                    ChroniclePointGrant.chronicle_id == cycle.chronicle_id,
                    ChroniclePointGrant.repeatable.is_(False),
                    ChroniclePointGrant.granted_at < cutoff,
                )
                .distinct()
            )
        ).all()
        chapters: dict[int, int] = defaultdict(int)
        finals: dict[int, int] = defaultdict(int)
        for account_id, objective_id in rows:
            if objective_id in CHAPTER_CONCLUSION_IDS:
                chapters[account_id] += 1
            elif objective_id in FINAL_PHASE_OBJECTIVES:
                finals[account_id] += 1
        electorate = sorted(
            account for account in chapters if vote_eligible(chapters[account], finals[account])
        )
        for account_id in electorate:
            session.add(
                ChronicleElector(
                    server_id=self.server_id,
                    chronicle_id=cycle.chronicle_id,
                    account_id=account_id,
                    frozen_at=now,
                )
            )
        votes = await self._round_votes(session, cycle, "main", electorate)
        await self._grant_answer_feat(session, cycle, "main", electorate)
        result = resolve_main(votes)
        if result.outcome is not None:
            cycle.outcome = result.outcome.value
        else:
            cycle.runoff_options = [item.value for item in result.runoff]
        cycle.vote_closed_at = now
        cycle.updated_at = now

    async def _close_runoff(self, session, cycle, calendar: Calendar, now) -> None:
        if (
            not cycle.runoff_options
            or cycle.runoff_closed_at is not None
            or now < calendar.runoff_closes_at
        ):
            return
        electorate = (
            await session.scalars(
                select(ChronicleElector.account_id).where(
                    ChronicleElector.server_id == self.server_id,
                    ChronicleElector.chronicle_id == cycle.chronicle_id,
                )
            )
        ).all()
        votes = await self._round_votes(session, cycle, "runoff", list(electorate))
        await self._grant_answer_feat(session, cycle, "runoff", list(electorate))
        options = tuple(Outcome(item) for item in cycle.runoff_options)
        cycle.outcome = resolve_runoff(votes, options).value
        cycle.runoff_closed_at = now
        cycle.updated_at = now

    async def _grant_answer_feat(self, session, cycle, round_: str, electorate) -> None:
        """pr_cr01_feito_resposta: the same Feito for every valid vote, whatever the option.

        A valid vote is one cast by an account in the frozen electorate. The Feito goes to
        the account's character on this server; idempotent per character.
        """
        if not electorate:
            return
        voters = (
            await session.scalars(
                select(ChronicleVote.account_id).where(
                    ChronicleVote.server_id == self.server_id,
                    ChronicleVote.chronicle_id == cycle.chronicle_id,
                    ChronicleVote.round == round_,
                    ChronicleVote.account_id.in_(list(electorate)),
                )
            )
        ).all()
        if not voters:
            return
        characters = (
            await session.scalars(
                select(Character.id).where(
                    Character.server_id == self.server_id,
                    Character.telegram_id.in_(sorted(set(voters))),
                )
            )
        ).all()
        for character_id in characters:
            await session.execute(
                insert(Achievement)
                .values(id=uuid4(), character_id=character_id, achievement_id=ANSWER_FEAT)
                .on_conflict_do_nothing()
            )

    async def _round_votes(self, session, cycle, round_: str, electorate) -> list[Outcome]:
        if not electorate:
            return []
        return [
            Outcome(option)
            for option in (
                await session.scalars(
                    select(ChronicleVote.option).where(
                        ChronicleVote.server_id == self.server_id,
                        ChronicleVote.chronicle_id == cycle.chronicle_id,
                        ChronicleVote.round == round_,
                        ChronicleVote.account_id.in_(list(electorate)),
                    )
                )
            ).all()
        ]

    async def _finalize(self, session, cycle, calendar: Calendar, now) -> None:
        """§5.3 real finalization: freeze the Classificação, archive it, soft reset."""
        if cycle.finalized_at is not None or now < calendar.finalization_at:
            return
        for name in (f"arena:{self.server_id}", f"guild_battle:{self.server_id}"):
            await session.execute(select(func.pg_advisory_xact_lock(advisory_key(name))))
        since = await current_cycle_started_at(session, self.server_id)
        await self._finalize_arena(session, cycle, now)
        await self._finalize_guild_battle(session, cycle, since, now)
        cycle.finalized_at = now
        cycle.updated_at = now

    async def _finalize_arena(self, session, cycle, now) -> None:
        profiles = (
            await session.execute(
                select(ArenaProfile, Character.name, Character.telegram_id)
                .join(Character, Character.id == ArenaProfile.character_id)
                .where(ArenaProfile.server_id == self.server_id)
                .order_by(ArenaProfile.character_id)
                .with_for_update(of=ArenaProfile)
            )
        ).all()
        ranked = sorted(
            (row for row in profiles if row[0].cycle_matches > 0 and row[0].placement_played >= 5),
            key=lambda row: (-row[0].renome, str(row[0].character_id)),
        )
        for position, (profile, name, account_id) in enumerate(ranked, start=1):
            tier = elo_reward_tier(profile.renome, profile.cycle_matches)
            session.add(
                VigilHallEntry(
                    server_id=self.server_id,
                    chronicle_id=cycle.chronicle_id,
                    kind="arena",
                    subject_id=profile.character_id,
                    account_id=account_id,
                    name=name,
                    position=position,
                    rating=profile.renome,
                    elo=elo_for(profile.renome),
                    matches=profile.cycle_matches,
                    reward_eligible=tier is not None,
                    reward_tier=tier,
                    created_at=now,
                )
            )
        for profile, _name, _account in profiles:
            # MMR is never reset; Renome only once placement gave it a value.
            if profile.placement_played >= 5:
                profile.renome = soft_reset_renome(profile.renome)
            profile.cycle_matches = 0

    async def _finalize_guild_battle(self, session, cycle, since, now) -> None:
        profiles = (
            await session.execute(
                select(GuildBattleProfile, Guild.name)
                .join(Guild, Guild.id == GuildBattleProfile.guild_id)
                .where(GuildBattleProfile.server_id == self.server_id)
                .order_by(GuildBattleProfile.guild_id)
                .with_for_update(of=GuildBattleProfile)
            )
        ).all()
        by_id = {profile.guild_id: (profile, name) for profile, name in profiles}
        ordered = order_standings(
            [
                StandingCandidate(profile.guild_id, profile.points, profile.rating)
                for profile, _ in profiles
                if profile.real_battles > 0 or profile.byes > 0
            ]
        )
        tiers: dict = {}
        for position, item in enumerate(ordered, start=1):
            profile, name = by_id[item.guild_id]
            eligible = reward_eligible(profile.real_battles)
            if eligible:
                tiers[profile.guild_id] = guild_reward_tier(len(tiers) + 1)
            session.add(
                VigilHallEntry(
                    server_id=self.server_id,
                    chronicle_id=cycle.chronicle_id,
                    kind="guild_battle",
                    subject_id=profile.guild_id,
                    name=name,
                    position=position,
                    rating=profile.rating,
                    matches=profile.real_battles,
                    points=profile.points,
                    reward_eligible=eligible,
                    reward_tier=tiers.get(profile.guild_id),
                    created_at=now,
                )
            )
        await self._grant_guild_battle_rewards(session, cycle, since, tiers, now)
        participations = (
            select(
                GuildBattleFightMember.character_id,
                GuildBattleFightMember.account_id,
                func.count(func.distinct(GuildBattleFight.battle_id)).label("battles"),
            )
            .join(GuildBattleFight, GuildBattleFight.id == GuildBattleFightMember.fight_id)
            .join(GuildBattle, GuildBattle.id == GuildBattleFight.battle_id)
            .where(GuildBattle.server_id == self.server_id, GuildBattle.status == "finished")
        )
        if since is not None:
            participations = participations.where(GuildBattle.finished_at > since)
        members = (
            await session.execute(
                participations.group_by(
                    GuildBattleFightMember.character_id, GuildBattleFightMember.account_id
                ).order_by(GuildBattleFightMember.character_id)
            )
        ).all()
        names = (
            {
                row.id: row.name
                for row in (
                    await session.scalars(
                        select(Character).where(Character.id.in_([m[0] for m in members]))
                    )
                ).all()
            }
            if members
            else {}
        )
        for position, (character_id, account_id, battles) in enumerate(members, start=1):
            session.add(
                VigilHallEntry(
                    server_id=self.server_id,
                    chronicle_id=cycle.chronicle_id,
                    kind="guild_battle_member",
                    subject_id=character_id,
                    account_id=account_id,
                    name=names.get(character_id, "—"),
                    position=position,
                    rating=0,
                    matches=int(battles),
                    reward_eligible=individual_reward_eligible(int(battles)),
                    created_at=now,
                )
            )
        for profile, _name in profiles:
            profile.real_battles = 0
            profile.wins = profile.draws = profile.losses = profile.byes = 0
            profile.points = 0

    async def _grant_guild_battle_rewards(self, session, cycle, since, tiers, now) -> None:
        """Cosmetics of each eligible Guild's tier to the characters with the
        individual minimum of battles fought for that Guild in this cycle."""
        if not tiers:
            return
        guild_id = case(
            (GuildBattleFightMember.side == "a", GuildBattle.guild_a_id),
            else_=GuildBattle.guild_b_id,
        )
        query = (
            select(
                GuildBattleFightMember.character_id,
                guild_id.label("guild_id"),
                func.count(func.distinct(GuildBattleFight.battle_id)).label("battles"),
            )
            .join(GuildBattleFight, GuildBattleFight.id == GuildBattleFightMember.fight_id)
            .join(GuildBattle, GuildBattle.id == GuildBattleFight.battle_id)
            .where(GuildBattle.server_id == self.server_id, GuildBattle.status == "finished")
        )
        if since is not None:
            query = query.where(GuildBattle.finished_at > since)
        rows = (
            await session.execute(
                query.group_by(GuildBattleFightMember.character_id, guild_id).order_by(
                    GuildBattleFightMember.character_id
                )
            )
        ).all()
        source = f"guild_battle:{cycle.chronicle_id}"
        for character_id, member_guild, battles in rows:
            tier = tiers.get(member_guild)
            if tier is None or not individual_reward_eligible(int(battles)):
                continue
            for cosmetic_id in REWARD_COSMETICS[tier]:
                definition = COSMETICS_BY_ID[cosmetic_id]
                await session.execute(
                    insert(CharacterCosmetic)
                    .values(
                        character_id=character_id,
                        cosmetic_id=cosmetic_id,
                        cosmetic_type=definition.cosmetic_type,
                        source_achievement_id=source,
                        acquired_at=now,
                    )
                    .on_conflict_do_nothing()
                )

    async def _liquidate(self, session, cycle, calendar: Calendar, now) -> None:
        """§5.2: after the rescue period, deliver every pending right exactly once."""
        if cycle.liquidated_at is not None or now < calendar.rescue_ends_at:
            return
        accounts = (
            await session.scalars(
                select(ChronicleAccount.account_id)
                .where(
                    ChronicleAccount.server_id == self.server_id,
                    ChronicleAccount.chronicle_id == cycle.chronicle_id,
                )
                .order_by(ChronicleAccount.account_id)
            )
        ).all()
        for account_id in accounts:
            character = await session.scalar(
                select(Character)
                .where(Character.telegram_id == account_id, Character.server_id == self.server_id)
                .with_for_update()
            )
            row = await _account_row(session, account_id, self.server_id, now)
            await self._deliver(session, row, character, "liquidation", now)
        cycle.liquidated_at = now
        cycle.updated_at = now

    # ------------------------------------------------------------ helpers

    async def _deliver(
        self, session, row: ChronicleAccount, character: Character | None, via: str, now
    ) -> ClaimResult:
        claimed = await self._claimed(session, row.account_id)
        due = claimable(row.points, row.premium_at is not None, claimed)
        crowns = 0
        items: dict[str, int] = defaultdict(int)
        cosmetics: list[str] = []
        delivered: list[tuple[str, int]] = []
        for track, milestone in due:
            inserted = await session.scalar(
                insert(ChronicleClaim)
                .values(
                    account_id=row.account_id,
                    server_id=self.server_id,
                    chronicle_id=CHRONICLE_ID,
                    track=track,
                    milestone=milestone,
                    character_id=None if character is None else character.id,
                    via=via,
                    claimed_at=now,
                )
                .on_conflict_do_nothing()
                .returning(ChronicleClaim.milestone)
            )
            if inserted is None:
                continue
            delivered.append((track, milestone))
            if character is None:
                continue  # no character on this server: the right lapses as delivered
            reward: TrackReward = reward_for(track, milestone)
            if reward.crowns or reward.basics or reward.fragments:
                granted = await grant_bundle(
                    session,
                    character,
                    Bundle(reward.crowns, reward.basics, reward.fragments),
                    f"chronicle:{CHRONICLE_ID}:{track}:{milestone}",
                )
                crowns += granted.crowns
                for item in granted.items:
                    items[item.name] += item.quantity
            if reward.cosmetic_id is not None:
                await self._give_cosmetic(session, character, reward.cosmetic_id, now)
                cosmetics.append(CHRONICLE_COSMETICS_BY_ID[reward.cosmetic_id].name)
        return ClaimResult(
            tuple(delivered),
            Granted(crowns, tuple(GrantedItem(name, qty) for name, qty in sorted(items.items()))),
            tuple(cosmetics),
        )

    @staticmethod
    async def _give_cosmetic(session, character: Character, cosmetic_id: str, now) -> None:
        definition = CHRONICLE_COSMETICS_BY_ID[cosmetic_id]
        await session.execute(
            insert(CharacterCosmetic)
            .values(
                character_id=character.id,
                cosmetic_id=definition.cosmetic_id,
                cosmetic_type=definition.cosmetic_type,
                source_achievement_id=COSMETIC_SOURCE,
                acquired_at=now,
            )
            .on_conflict_do_nothing()
        )

    async def _sync_cosmetics(self, session, character: Character, now) -> None:
        """Cosmetics are account entitlements: a recreated character gets them back."""
        for track, milestone in await self._claimed(session, character.telegram_id):
            cosmetic_id = reward_for(track, milestone).cosmetic_id
            if cosmetic_id is not None:
                await self._give_cosmetic(session, character, cosmetic_id, now)

    async def _claimed(self, session, account_id: int) -> frozenset[tuple[str, int]]:
        rows = (
            await session.execute(
                select(ChronicleClaim.track, ChronicleClaim.milestone).where(
                    ChronicleClaim.account_id == account_id,
                    ChronicleClaim.server_id == self.server_id,
                    ChronicleClaim.chronicle_id == CHRONICLE_ID,
                )
            )
        ).all()
        return frozenset((track, milestone) for track, milestone in rows)

    async def _track(self, session, cycle, account_id: int, now) -> TrackView:
        row = await session.get(ChronicleAccount, (account_id, self.server_id, CHRONICLE_ID))
        points = 0 if row is None else row.points
        premium = row is not None and row.premium_at is not None
        claimed = await self._claimed(session, account_id)
        phase = _phase(cycle, now)
        weeks = 0 if cycle is None else calendar_of(cycle).chapters_open(now)
        return TrackView(
            phase,
            points,
            milestones_reached(points),
            premium,
            claimed,
            claimable(points, premium, claimed),
            0 if row is None else row.repeatable_points,
            repeatable_cap(weeks),
            cycle is not None
            and cycle.liquidated_at is None
            and phase in (Phase.ACTIVE, Phase.CLOSING, Phase.RESCUE),
        )

    async def _completed(self, session, character_id: UUID) -> set[str]:
        return set(
            (
                await session.scalars(
                    select(ChronicleCompletion.objective_id).where(
                        ChronicleCompletion.character_id == character_id,
                        ChronicleCompletion.chronicle_id == CHRONICLE_ID,
                    )
                )
            ).all()
        )

    async def _account_progress(self, session, account_id: int) -> tuple[int, int]:
        rows = (
            await session.scalars(
                select(ChroniclePointGrant.source_id)
                .where(
                    ChroniclePointGrant.account_id == account_id,
                    ChroniclePointGrant.server_id == self.server_id,
                    ChroniclePointGrant.chronicle_id == CHRONICLE_ID,
                    ChroniclePointGrant.repeatable.is_(False),
                )
                .distinct()
            )
        ).all()
        return (
            sum(item in CHAPTER_CONCLUSION_IDS for item in rows),
            sum(item in FINAL_PHASE_OBJECTIVES for item in rows),
        )

    async def _in_electorate(self, session, account_id: int) -> bool:
        return (
            await session.get(ChronicleElector, (self.server_id, CHRONICLE_ID, account_id))
            is not None
        )

    async def _view(self, session, character: Character, now: datetime) -> ChronicleView:
        cycle = await load_cycle(session, self.server_id)
        phase = _phase(cycle, now)
        quests = await completed_quests(session, character.id)
        layers = layers_for(quests)
        row = await session.get(
            ChronicleAccount, (character.telegram_id, self.server_id, CHRONICLE_ID)
        )
        points = 0 if row is None else row.points
        premium = row is not None and row.premium_at is not None
        if cycle is None:
            return ChronicleView(phase, None, 0, False, (), points, 0, 0, None, None, layers)
        calendar = calendar_of(cycle)
        opened = calendar.chapters_open(now)
        done = await self._completed(session, character.id)
        chapters = []
        for chapter in CHAPTERS[:opened]:
            objectives = tuple(
                ObjectiveView(item, item.objective_id in done, character.level < item.min_level)
                for item in objectives_of(chapter.number)
            )
            concluded = chapter.conclusion_id in done
            chapters.append(
                ChapterView(
                    chapter.number,
                    chapter.title,
                    chapter.summary,
                    chapter.conclusion,
                    objectives,
                    concluded,
                    not concluded
                    and calendar.playable(now)
                    and can_conclude(chapter.number, done),
                )
            )
        vote = await self._vote_view(session, cycle, calendar, character, now)
        outcome = (
            Outcome(cycle.outcome) if cycle.outcome is not None and now >= cycle.end_at else None
        )
        return ChronicleView(
            phase,
            calendar,
            opened,
            ENTRY_GATE_QUEST in quests,
            tuple(chapters),
            points,
            milestones_reached(points),
            len(claimable(points, premium, await self._claimed(session, character.telegram_id))),
            vote,
            outcome,
            layers,
        )

    async def _vote_view(self, session, cycle, calendar, character, now) -> VoteView | None:
        round_ = calendar.vote_round(now)
        if round_ is None and now < calendar.vote_opens_at:
            return None
        chapters, finals = await self._account_progress(session, character.telegram_id)
        in_electorate = await self._in_electorate(session, character.telegram_id)
        options = VOTE_OPTIONS
        closes_at = calendar.vote_closes_at
        if round_ == "runoff":
            options = tuple(Outcome(item) for item in (cycle.runoff_options or ()))
            closes_at = calendar.runoff_closes_at
            if not options or cycle.runoff_closed_at is not None:
                round_ = None
        choice = await session.scalar(
            select(ChronicleVote.option).where(
                ChronicleVote.account_id == character.telegram_id,
                ChronicleVote.server_id == self.server_id,
                ChronicleVote.chronicle_id == CHRONICLE_ID,
                ChronicleVote.round == (round_ or "main"),
            )
        )
        eligible = in_electorate if round_ == "runoff" else vote_eligible(chapters, finals)
        return VoteView(
            round_,
            eligible,
            chapters,
            finals,
            None if choice is None else Outcome(choice),
            shuffled_options(character.telegram_id, CHRONICLE_ID, options),
            closes_at if round_ else None,
            in_electorate,
        )

    async def _character(self, session, actor: int, *, lock: bool = False) -> Character:
        statement = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        character = await session.scalar(statement.with_for_update() if lock else statement)
        if character is None:
            raise ChronicleError("no_character")
        return character


# ------------------------------------------------------------------- operator


@dataclass(frozen=True, slots=True)
class CycleStatus:
    calendar: Calendar
    phase: Phase
    outcome: str | None
    vote_closed_at: datetime | None
    runoff_options: tuple[str, ...]
    finalized_at: datetime | None
    liquidated_at: datetime | None


class ChronicleAdmin:
    """Operator actions; never reachable from Telegram."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id

    async def set_day1(self, day1: date, note: str, *, now: datetime | None = None) -> Calendar:
        """Day 1 may change freely until the Crônica starts; after that, only ``extend``."""
        now = _utcnow(now)
        if not note.strip():
            raise ChronicleError("chronicle_note_required")
        calendar = calendar_for(day1)
        if calendar.starts_at <= now:
            raise ChronicleError("chronicle_day1_past")
        async with self.sessions.begin() as session:
            cycle = await load_cycle(session, self.server_id, lock=True)
            before = None
            if cycle is not None:
                if calendar_of(cycle).starts_at <= now:
                    raise ChronicleError("chronicle_started")
                before = {"day1": cycle.day1.isoformat(), "end_at": cycle.end_at.isoformat()}
                cycle.day1, cycle.end_at = day1, calendar.end_at
                cycle.revision += 1
                cycle.updated_at = now
            else:
                session.add(
                    ChronicleCycle(
                        server_id=self.server_id,
                        chronicle_id=CHRONICLE_ID,
                        day1=day1,
                        end_at=calendar.end_at,
                        revision=0,
                        created_at=now,
                        updated_at=now,
                    )
                )
            self._log(session, "set_day1", before, calendar, note, now)
            return calendar

    async def extend(self, end_at: datetime, note: str, *, now: datetime | None = None) -> Calendar:
        """§5.3 exceptional extension: explicit new T, logged, before the closing starts."""
        now = _utcnow(now)
        if not note.strip():
            raise ChronicleError("chronicle_note_required")
        async with self.sessions.begin() as session:
            cycle = await load_cycle(session, self.server_id, lock=True)
            if cycle is None:
                raise ChronicleError("chronicle_unscheduled")
            current = calendar_of(cycle)
            if now < current.starts_at:
                raise ChronicleError("chronicle_not_started")
            if now >= current.vote_closes_at or cycle.vote_closed_at is not None:
                raise ChronicleError("chronicle_closing_started")
            if end_at <= cycle.end_at:
                raise ChronicleError("chronicle_extension_earlier")
            calendar = calendar_for(cycle.day1, end_at)
            before = {"day1": cycle.day1.isoformat(), "end_at": cycle.end_at.isoformat()}
            cycle.end_at = end_at
            cycle.revision += 1
            cycle.updated_at = now
            self._log(session, "extend", before, calendar, note, now)
            return calendar

    async def grant_pass(self, account_id: int, source: str, *, now: datetime | None = None):
        """Activate the Passe da Crônica; buying it after T is blocked (§5.2)."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            premium_at, _ = await grant_pass_in(session, self.server_id, account_id, source, now)
            return premium_at

    async def status(self, *, now: datetime | None = None) -> CycleStatus | None:
        now = _utcnow(now)
        async with self.sessions() as session:
            cycle = await load_cycle(session, self.server_id)
            if cycle is None:
                return None
            calendar = calendar_of(cycle)
            return CycleStatus(
                calendar,
                calendar.phase(now),
                cycle.outcome,
                cycle.vote_closed_at,
                tuple(cycle.runoff_options or ()),
                cycle.finalized_at,
                cycle.liquidated_at,
            )

    def _log(self, session, action, before, calendar: Calendar, note, now) -> None:
        session.add(
            ChronicleCycleLog(
                server_id=self.server_id,
                chronicle_id=CHRONICLE_ID,
                action=action,
                before=before,
                after={"day1": calendar.day1.isoformat(), "end_at": calendar.end_at.isoformat()},
                note=note.strip()[:500],
                created_at=now,
            )
        )
