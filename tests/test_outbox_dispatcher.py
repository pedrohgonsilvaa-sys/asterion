"""GDD §43.5: Outbox dispatcher (claim, retry, dead, order, multi-instance)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update

from asterion.application import outbox
from asterion.application.outbox import MAX_ATTEMPTS, OutboxDispatcher
from asterion.infrastructure.db.models import OutboxMessage


async def _add(sessions, topic="t", aggregate=None, created_offset=0, **extra):
    msg = OutboxMessage(
        topic=topic,
        dedup_key=uuid4().hex,
        aggregate_key=aggregate,
        payload={"n": created_offset},
        created_at=datetime.now(UTC) + timedelta(seconds=created_offset),
        **extra,
    )
    async with sessions.begin() as s:
        s.add(msg)
    return msg.id


async def _get(sessions, id_):
    async with sessions() as s:
        return await s.get(OutboxMessage, id_)


async def _make_due(sessions, id_):
    async with sessions.begin() as s:
        await s.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id == id_)
            .values(available_at=datetime.now(UTC) - timedelta(seconds=1))
        )


async def test_delivers_pending_once(database):
    sessions = database[1]
    seen = []

    async def handler(payload):
        seen.append(payload)

    id_ = await _add(sessions)
    dispatcher = OutboxDispatcher(sessions, {"t": handler})
    report = await dispatcher.run_maintenance()
    again = await dispatcher.run_maintenance()
    row = await _get(sessions, id_)
    assert (report.delivered, again.delivered) == (1, 0)
    assert len(seen) == 1
    assert row.status == "delivered" and row.delivered_at is not None
    assert row.attempt_count == 1


async def test_failure_backs_off_then_dies(database):
    sessions = database[1]

    async def handler(_payload):
        raise RuntimeError("telegram down")

    id_ = await _add(sessions)
    dispatcher = OutboxDispatcher(sessions, {"t": handler})
    for attempt in range(1, MAX_ATTEMPTS + 1):
        report = await dispatcher.run_maintenance()
        row = await _get(sessions, id_)
        assert row.attempt_count == attempt
        assert "telegram down" in row.last_error
        if attempt < MAX_ATTEMPTS:
            assert (report.retried, row.status) == (1, "pending")
            assert row.available_at > datetime.now(UTC)
            # Not due yet: nothing is claimed.
            assert (await dispatcher.run_maintenance()) == outbox.OutboxReport()
            await _make_due(sessions, id_)
    assert (report.dead, row.status) == (1, "dead")
    await _make_due(sessions, id_)
    assert (await dispatcher.run_maintenance()) == outbox.OutboxReport()


async def test_unknown_topic_is_a_failure_not_a_loss(database):
    sessions = database[1]
    id_ = await _add(sessions, topic="nobody")
    report = await OutboxDispatcher(sessions, {}).run_maintenance()
    row = await _get(sessions, id_)
    assert report.retried == 1 and row.status == "pending"
    assert "no handler" in row.last_error


async def test_expired_lease_is_reclaimed(database):
    sessions = database[1]
    seen = []

    async def handler(payload):
        seen.append(payload)

    id_ = await _add(sessions, status="processing", attempt_count=1)
    dispatcher = OutboxDispatcher(sessions, {"t": handler})
    # Lease still running (available_at defaults to now, so push it ahead).
    async with sessions.begin() as s:
        await s.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id == id_)
            .values(available_at=datetime.now(UTC) + timedelta(minutes=1))
        )
    assert (await dispatcher.run_maintenance()).delivered == 0
    await _make_due(sessions, id_)
    assert (await dispatcher.run_maintenance()).delivered == 1
    assert len(seen) == 1


async def test_same_aggregate_keeps_order(database):
    sessions = database[1]
    order = []
    fail_first = {"on": True}

    async def handler(payload):
        if payload["n"] == -2 and fail_first["on"]:
            fail_first["on"] = False
            raise RuntimeError("once")
        order.append(payload["n"])

    first = await _add(sessions, aggregate="a", created_offset=-2)
    await _add(sessions, aggregate="a", created_offset=-1)
    await _add(sessions, aggregate="b", created_offset=0)
    dispatcher = OutboxDispatcher(sessions, {"t": handler})
    # First fails: its follower must wait, the other aggregate goes through.
    await dispatcher.run_maintenance()
    assert order == [0]
    await _make_due(sessions, first)
    await dispatcher.run_maintenance()
    assert order == [0, -2]
    await dispatcher.run_maintenance()
    assert order == [0, -2, -1]


async def test_two_instances_never_send_twice(database):
    sessions = database[1]
    seen = []

    async def handler(payload):
        await asyncio.sleep(0.05)
        seen.append(payload["n"])

    for i in range(10):
        await _add(sessions, created_offset=-i - 1)
    a = OutboxDispatcher(sessions, {"t": handler}, batch_size=6)
    b = OutboxDispatcher(sessions, {"t": handler}, batch_size=6)
    await asyncio.gather(a.run_maintenance(), b.run_maintenance())
    await asyncio.gather(a.run_maintenance(), b.run_maintenance())
    assert sorted(seen) == sorted(set(seen)) and len(seen) == 10
    async with sessions() as s:
        statuses = set((await s.scalars(select(OutboxMessage.status))).all())
    assert statuses == {"delivered"}
