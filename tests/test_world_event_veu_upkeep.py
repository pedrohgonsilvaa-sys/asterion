"""Ciclo automático de A Ruptura do Véu: ocorrências, abertura, rodadas e prazo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from asterion.application.world_event_veu import VeuEventService, VeuEventUpkeep
from asterion.domain import world_event_veu as ev
from asterion.infrastructure.db.models import VeuEventOccurrence
from tests.test_world_event_veu_application import SERVER, SLOT, _characters

NAIVE_OK = SLOT - timedelta(minutes=30)


# ------------------------------------------------------------------ domínio puro


def test_slots_in_range_follow_the_schedule():
    found = ev.slots_in_range(SLOT - timedelta(hours=1), SLOT + timedelta(hours=1))
    assert found == [SLOT]
    assert ev.slots_in_range(SLOT + timedelta(minutes=1), SLOT + timedelta(hours=1)) == []


def test_due_notice_marks_fire_once_at_10_and_5_minutes():
    ten = SLOT - timedelta(minutes=10)
    five = SLOT - timedelta(minutes=5)
    assert ev.due_notice_marks(SLOT, ten - timedelta(seconds=1), ten) == (
        timedelta(minutes=10),
    )
    assert ev.due_notice_marks(SLOT, ten, ten + timedelta(seconds=1)) == ()
    assert ev.due_notice_marks(SLOT, five - timedelta(seconds=1), five) == (
        timedelta(minutes=5),
    )
    assert len(ev.due_notice_marks(SLOT, ten - timedelta(seconds=1), five)) == 2


# ------------------------------------------------------------------------ banco


@pytest.fixture
def svc(database) -> VeuEventService:
    return VeuEventService(database[1], SERVER)


@pytest.mark.asyncio
async def test_tick_creates_occurrence_and_emits_notices(svc):
    upkeep = VeuEventUpkeep(svc)
    ten = SLOT - timedelta(minutes=10)
    report = await upkeep.tick(ten, previous=ten - timedelta(seconds=5))
    assert [n.minutes for n in report.notices] == [10]
    again = await upkeep.tick(ten + timedelta(seconds=5), previous=ten)
    assert again.notices == ()
    five = SLOT - timedelta(minutes=5)
    report = await upkeep.tick(five, previous=five - timedelta(seconds=5))
    assert [n.minutes for n in report.notices] == [5]


@pytest.mark.asyncio
async def test_tick_opens_at_the_slot_and_is_idempotent(svc, database):
    upkeep = VeuEventUpkeep(svc)
    await upkeep.tick(SLOT - timedelta(minutes=1))
    report = await upkeep.tick(SLOT)
    assert len(report.opened) == 1
    assert (await upkeep.tick(SLOT + timedelta(seconds=1))).opened == ()
    async with database[1]() as session:
        rows = (await session.scalars(select(VeuEventOccurrence))).all()
    assert [row.state for row in rows] == ["ABERTO"]


@pytest.mark.asyncio
async def test_without_start_rule_the_event_never_starts(svc, database):
    upkeep = VeuEventUpkeep(svc)
    await upkeep.tick(SLOT)
    await upkeep.tick(SLOT + timedelta(minutes=30))
    async with database[1]() as session:
        row = await session.scalar(select(VeuEventOccurrence))
    assert row.state == "ABERTO"


@pytest.mark.asyncio
async def test_rounds_open_resolve_and_afk_runs_through_upkeep(svc, database):
    (character,) = await _characters(database, 1, base=771000)
    upkeep = VeuEventUpkeep(svc, start_after=timedelta(minutes=1))
    await upkeep.tick(SLOT)
    occurrence = (await svc.get_or_create_occurrence(SLOT)).id
    await svc.join(occurrence, character, now=SLOT)
    start = SLOT + timedelta(minutes=1)
    await upkeep.tick(start)
    await svc.enter_nucleus(occurrence, character, "A", now=start)
    report = await upkeep.tick(start + timedelta(seconds=1))
    assert report.rounds_opened == 1
    # Dentro dos 10 s nada resolve.
    assert (await upkeep.tick(start + timedelta(seconds=5))).rounds_resolved == 0
    report = await upkeep.tick(start + timedelta(seconds=12))
    assert report.rounds_resolved == 1
    assert report.rounds_opened == 1  # a seguinte abre na hora
    (view,) = await svc.list_participants(occurrence)
    assert view.afk_streak == 1


@pytest.mark.asyncio
async def test_three_idle_rounds_remove_player_and_stop_rounds(svc, database):
    (character,) = await _characters(database, 1, base=772000)
    upkeep = VeuEventUpkeep(svc, start_after=timedelta(minutes=1))
    await upkeep.tick(SLOT)
    occurrence = (await svc.get_or_create_occurrence(SLOT)).id
    await svc.join(occurrence, character, now=SLOT)
    now = SLOT + timedelta(minutes=1)
    await upkeep.tick(now)
    await svc.enter_nucleus(occurrence, character, "A", now=now)
    for step in range(1, 5):
        await upkeep.tick(now + timedelta(seconds=step * 11))
    (view,) = await svc.list_participants(occurrence)
    assert view.nucleus_removed and view.current_nucleus is None
    report = await upkeep.tick(now + timedelta(seconds=60))
    assert report.rounds_opened == 0


@pytest.mark.asyncio
async def test_deadline_fails_the_running_event_once(svc, database):
    upkeep = VeuEventUpkeep(svc, start_after=timedelta(minutes=1))
    await upkeep.tick(SLOT)
    await upkeep.tick(SLOT + timedelta(minutes=1))
    report = await upkeep.tick(SLOT + ev.DEADLINE)
    assert len(report.failed) == 1
    assert (await upkeep.tick(SLOT + ev.DEADLINE + timedelta(seconds=1))).failed == ()
    async with database[1]() as session:
        row = await session.scalar(select(VeuEventOccurrence))
    assert row.state == "FRACASSADO"
    assert row.deadline_at == SLOT.astimezone(UTC) + ev.DEADLINE
    assert isinstance(NAIVE_OK, datetime)
