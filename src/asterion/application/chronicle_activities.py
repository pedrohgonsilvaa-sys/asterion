"""Playable activities of Crônica I: Falar com NPC, Leituras and Desbravar (§0.3, §2, §8).

The Região de Ressonância (RR) is the most advanced Region where the character already
has Desbravar released; its most advanced such Local is the Local de Ressonância (LR).
A chapter runs in focus when the character can already Desbravar in the focus Region,
and in mirror otherwise. Leituras and talks cost nothing and create no economy.

Which Locals are released comes from ``latest_local``, injected by the Road service so
this module never imports it (the Road imports this module for the Desbravar hook).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.chronicle import (
    ChronicleError,
    calendar_of,
    completed_quests,
    load_cycle,
    record_objective,
    record_repeatable,
    repeatable_available,
)
from asterion.domain.chronicle import (
    CHRONICLE_ID,
    ENTRY_GATE_QUEST,
    OBJECTIVES_BY_ID,
    REPEATABLE_POINTS,
    Calendar,
    Layer,
    Objective,
    ObjectiveKind,
    layers_for,
    objectives_of,
)
from asterion.domain.chronicle_content import (
    CHAPTER_FOCUS,
    CHAPTER_RESULT_WEIGHT,
    DESBRAVAR_GUARANTEE_ATTEMPT,
    DESBRAVAR_OBJECTIVES,
    DESBRAVAR_STEPS,
    NPC_STEPS,
    READING_STEPS,
    REGIONS,
    REGIONS_BY_NAME,
    VESTIGIO_RESULT,
    VESTIGIO_SOURCE,
    VESTIGIO_TEXT,
    VESTIGIO_WEIGHT,
    RegionInfo,
    with_complement,
)
from asterion.domain.road import (
    ExplorationLocationProfile,
    ExplorationResultDefinition,
    hunt_profile_for_local_id,
)
from asterion.infrastructure.db.models import (
    Character,
    ChronicleCompletion,
    ExplorationAttempt,
    WorldState,
)

LatestLocal = Callable[[AsyncSession, Character, str], Awaitable[str | None]]

_ACTION_KINDS = (ObjectiveKind.NPC, ObjectiveKind.EVIDENCE, ObjectiveKind.DESBRAVAR)


@dataclass(frozen=True, slots=True)
class Route:
    region: RegionInfo
    local_id: str
    focus: bool

    @property
    def local_label(self) -> str:
        return hunt_profile_for_local_id(self.local_id).label


class _Resolver:
    """Per-request cache of the Region lookups, which cost several queries each."""

    def __init__(self, session: AsyncSession, character: Character, latest: LatestLocal):
        self.session, self.character, self.latest = session, character, latest
        self._locals: dict[str, str | None] = {}

    async def local_in(self, region: RegionInfo) -> str | None:
        if self.character.level < region.min_level:
            return None
        if region.name not in self._locals:
            self._locals[region.name] = await self.latest(
                self.session, self.character, region.name
            )
        return self._locals[region.name]

    async def route(self, chapter: int) -> Route | None:
        focus = CHAPTER_FOCUS.get(chapter)
        if focus is not None:
            region = REGIONS_BY_NAME[focus]
            local_id = await self.local_in(region)
            if local_id is not None:
                return Route(region, local_id, True)
        resonance = await self.resonance()
        # A chapter without focus has only one version of its text.
        return None if resonance is None else replace(resonance, focus=focus is None)

    async def resonance(self) -> Route | None:
        """The Região and Local de Ressonância, where every Encontro is fought (§0.3.7)."""
        for region in reversed(REGIONS):
            local_id = await self.local_in(region)
            if local_id is not None:
                return Route(region, local_id, True)
        return None


def _npc_of(region: RegionInfo, role: str) -> str:
    return region.coordinator if role == "coordinator" else region.registrar


@dataclass(frozen=True, slots=True)
class ActionView:
    objective: Objective
    location: str
    here: bool
    npc: str | None = None
    points_done: int = 0
    points_total: int = 0


@dataclass(frozen=True, slots=True)
class TalkView:
    objective: Objective
    npc: str
    text: str
    completed_now: bool


@dataclass(frozen=True, slots=True)
class ReadingView:
    point_id: str
    label: str
    done: bool


@dataclass(frozen=True, slots=True)
class ReadingsView:
    objective: Objective
    location: str
    points: tuple[ReadingView, ...]
    last_text: str | None = None
    completed_now: bool = False


class ChronicleActivityService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        latest_local: LatestLocal,
    ):
        self.sessions, self.server_id, self.latest_local = sessions, server_id, latest_local

    async def actions(self, actor: int, *, now: datetime | None = None) -> tuple[ActionView, ...]:
        """Pending Falar, Leituras and Desbravar of every open chapter (empty if closed)."""
        moment = now or datetime.now(UTC)
        async with self.sessions() as session:
            character = await session.scalar(self._character_query(actor))
            if character is None:
                return ()
            cycle = await load_cycle(session, self.server_id)
            if cycle is None:
                return ()
            calendar = calendar_of(cycle)
            if not calendar.accepts_progress(moment):
                return ()
            if ENTRY_GATE_QUEST not in await completed_quests(session, character.id):
                return ()
            world = await session.get(WorldState, character.id)
            done = await _flags(session, character)
            resolver = _Resolver(session, character, self.latest_local)
            result = []
            for chapter in range(1, calendar.chapters_open(moment) + 1):
                route = await resolver.route(chapter)
                if route is None:
                    continue
                for objective in objectives_of(chapter):
                    if objective.kind not in _ACTION_KINDS or objective.objective_id in done:
                        continue
                    result.append(_action(objective, route, world, done))
            return tuple(result)

    async def here(self, actor: int, *, now: datetime | None = None) -> tuple[ActionView, ...]:
        """Actions started from the current Local (Desbravar has its own button there)."""
        return tuple(
            item
            for item in await self.actions(actor, now=now)
            if item.here and item.objective.kind is not ObjectiveKind.DESBRAVAR
        )

    async def talk(
        self, actor: int, chapter: int, slot: int, *, now: datetime | None = None
    ) -> TalkView:
        moment = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            context = await self._context(session, actor, chapter, slot, ObjectiveKind.NPC, moment)
            step = NPC_STEPS[context.objective.objective_id]
            region = context.route.region
            if context.world is None or context.world.location != region.hub:
                raise ChronicleError("chronicle_not_here")
            npc = _npc_of(region, step.role)
            template = step.text if context.route.focus or step.mirror is None else step.mirror
            completed = await record_objective(
                session,
                self.server_id,
                context.character,
                context.objective.objective_id,
                now=moment,
            )
            return TalkView(
                context.objective,
                npc,
                with_complement(template.format(npc=npc), step.complement, context.layers),
                completed,
            )

    async def readings(
        self, actor: int, chapter: int, slot: int, *, now: datetime | None = None
    ) -> ReadingsView:
        moment = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            context = await self._context(
                session, actor, chapter, slot, ObjectiveKind.EVIDENCE, moment
            )
            done = await _flags(session, context.character)
            return _readings_view(context, done)

    async def examine(
        self, actor: int, chapter: int, slot: int, point_id: str, *, now: datetime | None = None
    ) -> ReadingsView:
        moment = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            context = await self._context(
                session, actor, chapter, slot, ObjectiveKind.EVIDENCE, moment
            )
            if context.world is None or context.world.location != context.route.local_label:
                raise ChronicleError("chronicle_not_here")
            points = READING_STEPS[context.objective.objective_id]
            point = next((item for item in points if item.point_id == point_id), None)
            if point is None:
                raise ChronicleError("chronicle_unknown")
            await session.execute(
                insert(ChronicleCompletion)
                .values(
                    character_id=context.character.id,
                    chronicle_id=CHRONICLE_ID,
                    objective_id=point_id,
                    account_id=context.character.telegram_id,
                    server_id=self.server_id,
                    completed_at=moment,
                )
                .on_conflict_do_nothing()
            )
            done = await _flags(session, context.character)
            completed = {item.point_id for item in points} <= done and await record_objective(
                session,
                self.server_id,
                context.character,
                context.objective.objective_id,
                now=moment,
            )
            mirrored = not context.route.focus and point.mirror_text is not None
            return replace(
                _readings_view(context, done),
                last_text=point.mirror_text if mirrored else point.text,
                completed_now=bool(completed),
            )

    def _character_query(self, actor: int):
        return select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )

    async def _context(
        self,
        session: AsyncSession,
        actor: int,
        chapter: int,
        slot: int,
        kind: ObjectiveKind,
        now: datetime,
    ) -> _Context:
        objective = OBJECTIVES_BY_ID.get(f"cap_{chapter:02d}_obj_{slot:02d}")
        if objective is None or objective.kind is not kind:
            raise ChronicleError("chronicle_unknown")
        character = await session.scalar(self._character_query(actor).with_for_update())
        if character is None:
            raise ChronicleError("no_character")
        cycle = await load_cycle(session, self.server_id)
        if cycle is None:
            raise ChronicleError("chronicle_closed")
        calendar: Calendar = calendar_of(cycle)
        if not calendar.accepts_progress(now):
            raise ChronicleError("chronicle_closed")
        if calendar.chapter_opens_at(chapter) > now:
            raise ChronicleError("chronicle_chapter_locked")
        quests = await completed_quests(session, character.id)
        if ENTRY_GATE_QUEST not in quests:
            raise ChronicleError("chronicle_gate")
        route = await _Resolver(session, character, self.latest_local).route(chapter)
        if route is None:
            raise ChronicleError("chronicle_not_here")
        world = await session.get(WorldState, character.id)
        return _Context(character, objective, route, world, layers_for(quests))


@dataclass(frozen=True, slots=True)
class _Context:
    character: Character
    objective: Objective
    route: Route
    world: WorldState | None
    layers: frozenset[Layer]


def _readings_view(context: _Context, done: set[str]) -> ReadingsView:
    points = []
    for point in READING_STEPS[context.objective.objective_id]:
        mirrored = not context.route.focus and point.mirror_label is not None
        points.append(
            ReadingView(
                point.point_id,
                point.mirror_label if mirrored else point.label,
                point.point_id in done,
            )
        )
    return ReadingsView(context.objective, context.route.local_label, tuple(points))


def _action(objective: Objective, route: Route, world: WorldState | None, done: set[str]):
    location = world.location if world is not None else None
    if objective.kind is ObjectiveKind.NPC:
        npc = _npc_of(route.region, NPC_STEPS[objective.objective_id].role)
        return ActionView(objective, route.region.hub, location == route.region.hub, npc)
    label = route.local_label
    if objective.kind is ObjectiveKind.EVIDENCE:
        points = READING_STEPS[objective.objective_id]
        count = sum(item.point_id in done for item in points)
        return ActionView(objective, label, location == label, None, count, len(points))
    return ActionView(objective, label, location == label)


async def _flags(session: AsyncSession, character: Character) -> set[str]:
    return set(
        (
            await session.scalars(
                select(ChronicleCompletion.objective_id).where(
                    ChronicleCompletion.character_id == character.id,
                    ChronicleCompletion.chronicle_id == CHRONICLE_ID,
                )
            )
        ).all()
    )


# ------------------------------------------------------------- Desbravar hook


@dataclass(frozen=True, slots=True)
class DesbravarOffer:
    profile: ExplorationLocationProfile
    forced: ExplorationResultDefinition | None = None


async def desbravar_offer(
    session: AsyncSession,
    character: Character,
    profile: ExplorationLocationProfile,
    attempt_local_id: str,
    latest_local: LatestLocal,
    now: datetime,
) -> DesbravarOffer:
    """The Local's pool for this attempt. The caller holds the Character lock."""
    unchanged = DesbravarOffer(profile)
    cycle = await load_cycle(session, character.server_id)
    if cycle is None:
        return unchanged
    calendar = calendar_of(cycle)
    if not calendar.accepts_progress(now):
        return unchanged
    quests = await completed_quests(session, character.id)
    if ENTRY_GATE_QUEST not in quests:
        return unchanged
    done = await _flags(session, character)
    resolver = _Resolver(session, character, latest_local)
    for chapter in range(1, calendar.chapters_open(now) + 1):
        for objective in objectives_of(chapter):
            if objective.kind is not ObjectiveKind.DESBRAVAR or objective.objective_id in done:
                continue
            route = await resolver.route(chapter)
            if route is None or route.local_id != profile.local_id:
                continue
            definition = _chapter_result(objective, route, layers_for(quests))
            attempts = await session.scalar(
                select(func.count(ExplorationAttempt.id)).where(
                    ExplorationAttempt.character_id == character.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                    ExplorationAttempt.created_at >= calendar.chapter_opens_at(chapter),
                )
            )
            if (attempts or 0) >= DESBRAVAR_GUARANTEE_ATTEMPT - 1:
                return DesbravarOffer(profile, definition)
            others = tuple(item for item in profile.results if item.category != "narrative")
            return DesbravarOffer(replace(profile, results=(*others, definition)))
    if await repeatable_available(session, character, VESTIGIO_SOURCE, calendar, now):
        vestigio = ExplorationResultDefinition(
            VESTIGIO_RESULT, "narrative", VESTIGIO_RESULT, VESTIGIO_WEIGHT, VESTIGIO_TEXT
        )
        return DesbravarOffer(replace(profile, results=(*profile.results, vestigio)))
    return unchanged


def _chapter_result(objective, route: Route, layers: frozenset[Layer]):
    step = DESBRAVAR_STEPS[objective.objective_id]
    text = step.text if route.focus or step.mirror is None else step.mirror
    return ExplorationResultDefinition(
        step.result_id,
        "narrative",
        step.result_id,
        CHAPTER_RESULT_WEIGHT,
        with_complement(text, step.complement, layers),
        unique=True,
    )


async def settle_desbravar(
    session: AsyncSession, character: Character, attempt: ExplorationAttempt, now: datetime
) -> None:
    """Register a ``dsc_cr01_*`` result: never Vigor, Coroas, XP or Materiais (§0.3.6)."""
    lines = [(attempt.progress or {}).get("result_text", "")]
    objective_id = DESBRAVAR_OBJECTIVES.get(attempt.result_id)
    if objective_id is not None:
        if await record_objective(session, character.server_id, character, objective_id, now=now):
            lines.append(f"🌌 Crônica · {OBJECTIVES_BY_ID[objective_id].title} concluído")
    elif (
        await record_repeatable(
            session, character.server_id, character, VESTIGIO_SOURCE, attempt.id.hex, now=now
        )
        > 0
    ):
        lines.append(f"🧭 Trilha da Crônica · +{REPEATABLE_POINTS} pontos")
    attempt.progress = {
        **(attempt.progress or {}),
        "receipt_text": "\n\n".join(lines),
        "settled": True,
    }
    attempt.completed_at = attempt.completed_at or now
