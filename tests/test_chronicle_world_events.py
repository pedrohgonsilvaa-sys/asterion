"""O Compasso during the Crônica: versions, eligibility and Trilha (§0.3.8, §8, §11.5)."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select, update

from asterion.application.chronicle_activities import ChronicleActivityService
from asterion.application.prologue import CombatView
from asterion.application.world_events import WorldEventError, WorldEventService
from asterion.domain.chronicle_content import OCASO, VALES
from asterion.domain.road import ROAD_LOCATION, VDE_GARGANTA_LOCATION
from asterion.domain.world_events import EVENT_TIMEZONE
from asterion.infrastructure.db.models import (
    Character,
    GameActivity,
    WorldEventOccurrence,
    WorldEventParticipation,
)
from tests.test_chronicle_activities import (
    ANA,
    CAL,
    SERVER,
    _done,
    _make,
    _points,
    _resolver,
    _schedule,
)

D = Decimal
_BOTH = {OCASO: ROAD_LOCATION, VALES: VDE_GARGANTA_LOCATION}


def _slot(day: int, hour: int = 12) -> datetime:
    local = datetime.combine(CAL.day1 + timedelta(days=day - 1), datetime.min.time())
    return local.replace(hour=hour, tzinfo=EVENT_TIMEZONE)


def _service(database, **by_region) -> WorldEventService:
    latest = _resolver(**by_region) if by_region else None
    return WorldEventService(database[1], SERVER, (), latest_local=latest)


async def _ready(database, actor=ANA, level=10) -> None:
    await _make(database, actor, level=level)
    async with database[1].begin() as session:
        await session.execute(
            update(Character).where(Character.telegram_id == actor).values(vigor=100, max_vigor=100)
        )


async def _occurrences(database) -> dict[str, WorldEventOccurrence]:
    async with database[1]() as session:
        rows = (await session.scalars(select(WorldEventOccurrence))).all()
    return {row.occurrence_key: row for row in rows}


async def _version(database, slot: datetime, region: str) -> WorldEventOccurrence:
    async with database[1]() as session:
        rows = (
            await session.scalars(
                select(WorldEventOccurrence).where(
                    WorldEventOccurrence.opened_at == slot.astimezone(EVENT_TIMEZONE)
                )
            )
        ).all()
    service = WorldEventService(lambda: None, SERVER, ())
    return next(row for row in rows if service._definition(row).region == region)


async def _code(awaitable) -> str:
    try:
        await awaitable
    except WorldEventError as error:
        return error.code
    raise AssertionError("expected a WorldEventError")


async def _eligible_and_completed(database, occurrence_id, actor=ANA, phases=(1, 2)) -> None:
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await session.execute(
            update(WorldEventParticipation)
            .where(
                WorldEventParticipation.occurrence_id == occurrence_id,
                WorldEventParticipation.character_id == character.id,
            )
            .values(phases=list(phases), significant_actions=8)
        )
        await session.execute(
            update(WorldEventOccurrence)
            .where(WorldEventOccurrence.id == occurrence_id)
            .values(status="completed", phase=3)
        )


async def _join_and_settle(database, slot, *, phases=(1, 2)) -> None:
    service = _service(database, **{OCASO: ROAD_LOCATION})
    now = slot + timedelta(minutes=1)
    await service.run_maintenance(now=now)
    occurrence = await _version(database, slot, OCASO)
    await service.enter(ANA, occurrence.id, now=now)
    await _eligible_and_completed(database, occurrence.id, phases=phases)
    await service.run_maintenance(now=slot + timedelta(minutes=30))


async def test_each_slot_opens_one_occurrence_per_region_version(database):
    await _ready(database)
    await _schedule(database)
    service = _service(database, **{OCASO: ROAD_LOCATION})
    for _ in range(2):  # a restart lands on the same rows
        await service.run_maintenance(now=_slot(1) + timedelta(minutes=1))
    rows = await _occurrences(database)
    assert len(rows) == 6
    assert {row.event_id for row in rows.values()} == {
        f"evt_cr01_ressonancia.{index}" for index in range(1, 7)
    }
    # Only the reached Regions are offered; the character picks one.
    view = await service.hub(ANA, now=_slot(1) + timedelta(minutes=1))
    assert view.status is None
    assert [(item.region, item.level) for item in view.versions] == [(OCASO, 10)]
    assert view.next_opening is not None


async def test_plena_replaces_the_ressonancia_from_chapter_seven(database):
    await _ready(database)
    await _schedule(database)
    await _service(database).run_maintenance(now=_slot(43) + timedelta(minutes=1))
    assert {row.event_id.split(".")[0] for row in (await _occurrences(database)).values()} == {
        "evt_cr01_ressonancia_plena"
    }


async def test_no_occurrence_outside_the_crônica(database):
    await _ready(database)
    await _schedule(database)
    await _service(database).run_maintenance(now=_slot(1) - timedelta(days=7))
    assert await _occurrences(database) == {}


async def test_one_version_per_slot_and_only_reached_regions(database):
    await _ready(database, level=15)
    await _schedule(database)
    now = _slot(1) + timedelta(minutes=1)
    service = _service(database, **_BOTH)
    await service.run_maintenance(now=now)
    ocaso = await _version(database, _slot(1), OCASO)
    vales = await _version(database, _slot(1), VALES)
    confins = await _version(database, _slot(1), "Confins do Véu")
    assert await _code(service.enter(ANA, confins.id, now=now)) == "region_locked"
    # Without the Local lookup no Crônica version can be joined.
    assert await _code(_service(database).enter(ANA, ocaso.id, now=now)) == "region_locked"
    view = await service.enter(ANA, ocaso.id, now=now)
    assert view.status is not None and view.status.region == OCASO
    assert await _code(service.enter(ANA, vales.id, now=now)) == "other_version"
    hub = await service.hub(ANA, now=now)
    assert hub.status is not None and hub.status.occurrence_id == ocaso.id


async def test_eligible_participation_counts_for_objective_and_trilha_once(database):
    await _ready(database)
    await _schedule(database)
    await _join_and_settle(database, _slot(22))
    assert "cap_04_obj_03" in await _done(database)
    assert await _points(database) == 25 + 60
    await _service(database).run_maintenance(now=_slot(22) + timedelta(minutes=40))
    assert await _points(database) == 25 + 60


async def test_before_the_chapter_only_the_repeatable_counts(database):
    await _ready(database)
    await _schedule(database)
    await _join_and_settle(database, _slot(1))
    assert "cap_04_obj_03" not in await _done(database)
    assert await _points(database) == 25


async def test_ineligible_participation_counts_for_nothing(database):
    await _ready(database)
    await _schedule(database)
    await _join_and_settle(database, _slot(22), phases=(1,))
    assert await _points(database) == 0


async def test_chapter_eight_needs_another_plena_occurrence(database):
    await _ready(database)
    await _schedule(database)
    await _join_and_settle(database, _slot(50))
    done = await _done(database)
    assert "cap_07_obj_04" in done and "cap_08_obj_03" not in done
    await _join_and_settle(database, _slot(50, 20))
    assert "cap_08_obj_03" in await _done(database)
    assert await _points(database) == 25 + 60 + 25 + 50


async def _phase_three(database, occurrence_id) -> None:
    async with database[1].begin() as session:
        await session.execute(
            update(WorldEventOccurrence)
            .where(WorldEventOccurrence.id == occurrence_id)
            .values(
                status="active",
                phase=3,
                participants_snapshot=1,
                boss_hp=D("1000"),
                boss_max_hp=D("1000"),
                phase_started_at=_slot(1) + timedelta(minutes=10),
            )
        )


def _resonance_gate(view: CombatView) -> tuple[str, ...]:
    return next(
        action.phase_ids
        for key, action in view.combat.enemy_actions.items()
        if key.endswith("ressonancia")
    )


async def test_ressonancia_only_in_the_first_phase_three_instance(database):
    await _ready(database)
    await _schedule(database)
    now = _slot(1) + timedelta(minutes=1)
    service = _service(database, **{OCASO: ROAD_LOCATION})
    await service.run_maintenance(now=now)
    occurrence = await _version(database, _slot(1), OCASO)
    await service.enter(ANA, occurrence.id, now=now)
    await _phase_three(database, occurrence.id)
    fight_at = _slot(1) + timedelta(minutes=11)
    first = await service.fight(ANA, occurrence.id, now=fight_at)
    assert isinstance(first, CombatView)
    assert first.combat.phase_id == "phase_iii"
    assert _resonance_gate(first) == ("phase_iii",)
    # The participant falls; the reentry opens a new instance of the same phase.
    async with database[1].begin() as session:
        await session.execute(
            update(GameActivity).where(GameActivity.id == first.activity_id).values(status="failed")
        )
        await session.execute(
            update(WorldEventParticipation)
            .where(WorldEventParticipation.occurrence_id == occurrence.id)
            .values(activity_id=None, combat_phase=None, reentry_at=None)
        )
    second = await service.fight(ANA, occurrence.id, now=fight_at + timedelta(minutes=3))
    assert isinstance(second, CombatView)
    assert _resonance_gate(second) == ("cr01.compasso.spent",)
    async with database[1]() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(GameActivity)
                .where(GameActivity.content_id == f"world_event:{occurrence.id.hex}:3")
            )
            == 2
        )


async def test_chapter_shows_when_and_where_the_next_occurrence_happens(database):
    await _ready(database)
    await _schedule(database)
    activities = ChronicleActivityService(database[1], SERVER, _resolver(**{OCASO: ROAD_LOCATION}))
    morning = CAL.chapter_opens_at(4) + timedelta(hours=1)
    items = {
        item.objective.objective_id: item for item in await activities.actions(ANA, now=morning)
    }
    event = items["cap_04_obj_03"]
    assert (event.event_at, event.event_live, event.location) == (_slot(22), False, OCASO)
    assert not event.here
    live = {
        item.objective.objective_id: item
        for item in await activities.actions(ANA, now=_slot(22) + timedelta(minutes=5))
    }
    assert live["cap_04_obj_03"].event_live
    # No Ressonância left after D43: the optional objective leaves the list.
    late = CAL.chapter_opens_at(7) + timedelta(hours=1)
    assert "cap_04_obj_03" not in {
        item.objective.objective_id for item in await activities.actions(ANA, now=late)
    }
