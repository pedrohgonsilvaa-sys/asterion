"""Playable activities of Crônica I: Falar com NPC, Leituras and Desbravar (§0.3, §2, §8).

The Região de Ressonância (RR) is the most advanced Region where the character already
has Desbravar released; its most advanced such Local is the Local de Ressonância (LR).
A chapter runs in focus when the character can already Desbravar in the focus Region,
and in mirror otherwise. Leituras and talks cost nothing and create no economy.

Masmorra objectives (§0.3.4) are completed at the end of a valid run; while no accepted
Masmorra has Estável released, ``dsc_cr01_vestigio_profundo`` in the LR replaces them.
Evento Mundial objectives (§0.3.8) are completed when an O Compasso occurrence settles
with the participant eligible (``record_world_event``).

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
    DEEP_VESTIGIO_RESULT,
    DEEP_VESTIGIO_TEXT,
    DESBRAVAR_GUARANTEE_ATTEMPT,
    DESBRAVAR_OBJECTIVES,
    DESBRAVAR_STEPS,
    DUNGEON_FOCUS,
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
from asterion.domain.chronicle_events import EVENT_SOURCE, OBJECTIVE_FAMILY, next_occurrence
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

_ACTION_KINDS = (
    ObjectiveKind.NPC,
    ObjectiveKind.EVIDENCE,
    ObjectiveKind.DESBRAVAR,
    ObjectiveKind.DUNGEON,
    ObjectiveKind.EVENT,
)
# Started elsewhere: Desbravar has its own button in the Local, a Masmorra its own menu,
# the Evento Mundial the Eventos menu.
_NO_BUTTON = (ObjectiveKind.DESBRAVAR, ObjectiveKind.DUNGEON, ObjectiveKind.EVENT)


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
        self._released: dict[str, bool] = {}

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

    async def dungeons(self, objective: Objective, route: Route) -> tuple[str, ...]:
        """Accepted Masmorras with Estável released: the focus pair, or any in mirror."""
        from asterion.application.dungeons import DUNGEON_FAMILIES, stable_released

        accepted = DUNGEON_FOCUS[objective.objective_id] if route.focus else DUNGEON_FAMILIES
        result = []
        for family_id in accepted:
            if family_id not in self._released:
                self._released[family_id] = await stable_released(
                    self.session, self.character, family_id
                )
            if self._released[family_id]:
                result.append(family_id)
        return tuple(result)

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
    dungeons: tuple[str, ...] = ()  # Masmorra names; empty means the Desbravar alternative
    focus: bool = True
    event_at: datetime | None = None  # Evento Mundial: the open or next occurrence
    event_live: bool = False


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
            if not calendar.playable(moment):
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
                    if objective.kind is ObjectiveKind.DUNGEON:
                        result.append(await _dungeon_action(objective, route, world, resolver))
                        continue
                    if objective.kind is ObjectiveKind.EVENT:
                        event = await _event_action(objective, calendar, moment, resolver)
                        if event is not None:
                            result.append(event)
                        continue
                    result.append(_action(objective, route, world, done))
            return tuple(result)

    async def here(self, actor: int, *, now: datetime | None = None) -> tuple[ActionView, ...]:
        """Actions started from the current Local (Desbravar has its own button there)."""
        return tuple(
            item
            for item in await self.actions(actor, now=now)
            if item.here and item.objective.kind not in _NO_BUTTON
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
        if not calendar.playable(now):
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


async def _dungeon_action(
    objective: Objective, route: Route, world: WorldState | None, resolver: _Resolver
) -> ActionView:
    from asterion.application.dungeons import DUNGEON_FAMILIES

    location = world.location if world is not None else None
    names = tuple(
        DUNGEON_FAMILIES[family_id].name
        for family_id in await resolver.dungeons(objective, route)
    )
    label = route.local_label
    return ActionView(objective, label, location == label, dungeons=names, focus=route.focus)


async def region_accessible(
    session: AsyncSession, character: Character, region_name: str, latest_local: LatestLocal
) -> bool:
    """A Region counts as reached once it has a Local with Desbravar released (§0.3)."""
    return await _Resolver(session, character, latest_local).local_in(
        REGIONS_BY_NAME[region_name]
    ) is not None


async def _event_action(
    objective: Objective, calendar: Calendar, now: datetime, resolver: _Resolver
) -> ActionView | None:
    """When and where: the open or next occurrence, in the version of the RR (§11.5)."""
    upcoming = next_occurrence(calendar, OBJECTIVE_FAMILY[objective.objective_id], now)
    resonance = await resolver.resonance()
    if upcoming is None or resonance is None:
        return None
    return ActionView(
        objective,
        resonance.region.name,
        False,
        event_at=upcoming.at,
        event_live=upcoming.live,
    )


async def record_world_event(
    session: AsyncSession,
    character: Character,
    family: str,
    occurrence_id: str,
    *,
    now: datetime,
    started_at: datetime,
) -> str | None:
    """An eligible participant of an O Compasso occurrence (§0.3.8, §8).

    The Event calls it at settlement, holding the Character lock. The same occurrence
    pays ``rep_cr01_evento`` once and completes at most one Evento Mundial objective,
    the oldest pending one that accepts ``family``; so ``cap_08_obj_03`` always comes
    from an occurrence other than the one of ``cap_07_obj_04``.
    """
    await record_repeatable(
        session,
        character.server_id,
        character,
        EVENT_SOURCE,
        occurrence_id,
        now=now,
        started_at=started_at,
    )
    cycle = await load_cycle(session, character.server_id)
    if cycle is None:
        return None
    calendar = calendar_of(cycle)
    if not calendar.accepts_progress(now, started_at):
        return None
    if ENTRY_GATE_QUEST not in await completed_quests(session, character.id):
        return None
    done = await _flags(session, character)
    for chapter in range(1, calendar.chapters_open(started_at) + 1):
        for objective in objectives_of(chapter):
            if objective.kind is not ObjectiveKind.EVENT or objective.objective_id in done:
                continue
            if OBJECTIVE_FAMILY[objective.objective_id] != family:
                continue
            if await record_objective(
                session,
                character.server_id,
                character,
                objective.objective_id,
                now=now,
                started_at=started_at,
            ):
                return objective.objective_id
    return None


async def record_dungeon_run(
    session: AsyncSession,
    character: Character,
    family_id: str,
    latest_local: LatestLocal,
    *,
    now: datetime,
    started_at: datetime | None = None,
) -> str | None:
    """Complete the oldest pending Masmorra objective this run is accepted for.

    The Masmorra calls it for each participant with participation above 0, holding the
    Character lock. One run completes at most one objective.
    """
    cycle = await load_cycle(session, character.server_id)
    if cycle is None:
        return None
    calendar = calendar_of(cycle)
    if not calendar.playable(now, started_at):
        return None
    if ENTRY_GATE_QUEST not in await completed_quests(session, character.id):
        return None
    done = await _flags(session, character)
    resolver = _Resolver(session, character, latest_local)
    for chapter in range(1, calendar.chapters_open(started_at or now) + 1):
        for objective in objectives_of(chapter):
            if objective.kind is not ObjectiveKind.DUNGEON or objective.objective_id in done:
                continue
            route = await resolver.route(chapter)
            if route is None:
                continue
            if route.focus and family_id not in DUNGEON_FOCUS[objective.objective_id]:
                continue
            if await record_objective(
                session,
                character.server_id,
                character,
                objective.objective_id,
                now=now,
                started_at=started_at,
            ):
                return objective.objective_id
    return None


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
    objective_id: str | None = None  # the Crônica objective of the chapter result offered


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
    if not calendar.playable(now):
        return unchanged
    quests = await completed_quests(session, character.id)
    if ENTRY_GATE_QUEST not in quests:
        return unchanged
    done = await _flags(session, character)
    resolver = _Resolver(session, character, latest_local)
    for chapter in range(1, calendar.chapters_open(now) + 1):
        for objective in objectives_of(chapter):
            if objective.kind not in _NO_BUTTON or objective.objective_id in done:
                continue
            route = await resolver.route(chapter)
            if route is None or route.local_id != profile.local_id:
                continue
            if objective.kind is ObjectiveKind.DUNGEON:
                if await resolver.dungeons(objective, route):
                    continue
                definition = _deep_vestigio()
            else:
                definition = _chapter_result(objective, route, layers_for(quests))
            attempts = await session.scalar(
                select(func.count(ExplorationAttempt.id)).where(
                    ExplorationAttempt.character_id == character.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                    ExplorationAttempt.created_at >= calendar.chapter_opens_at(chapter),
                )
            )
            if (attempts or 0) >= DESBRAVAR_GUARANTEE_ATTEMPT - 1:
                return DesbravarOffer(profile, definition, objective.objective_id)
            others = tuple(item for item in profile.results if item.category != "narrative")
            return DesbravarOffer(
                replace(profile, results=(*others, definition)), None, objective.objective_id
            )
    if await repeatable_available(session, character, VESTIGIO_SOURCE, calendar, now):
        vestigio = ExplorationResultDefinition(
            VESTIGIO_RESULT, "narrative", VESTIGIO_RESULT, VESTIGIO_WEIGHT, VESTIGIO_TEXT
        )
        return DesbravarOffer(replace(profile, results=(*profile.results, vestigio)))
    return unchanged


def _deep_vestigio() -> ExplorationResultDefinition:
    return ExplorationResultDefinition(
        DEEP_VESTIGIO_RESULT,
        "narrative",
        DEEP_VESTIGIO_RESULT,
        CHAPTER_RESULT_WEIGHT,
        DEEP_VESTIGIO_TEXT,
        unique=True,
    )


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
    if attempt.result_id == DEEP_VESTIGIO_RESULT:
        # One result id serves the four Masmorra objectives; the offer names which one.
        objective_id = (attempt.progress or {}).get("chronicle_objective")
    if objective_id is not None:
        if await record_objective(session, character.server_id, character, objective_id, now=now):
            lines.append(f"🌌 Crônica · {OBJECTIVES_BY_ID[objective_id].title} concluído")
    elif attempt.result_id == VESTIGIO_RESULT and (
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
