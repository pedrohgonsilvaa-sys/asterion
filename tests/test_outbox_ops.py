"""Outbox stats/requeue/CLI and the cluster-wide job lock (GDD §43.5, §43.6)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from asterion.application.admin import AdminService
from asterion.application.outbox import outbox_stats, requeue_dead
from asterion.infrastructure.db.job_lock import run_exclusive
from asterion.infrastructure.db.models import OutboxMessage
from asterion.outbox_cli import run as cli_run


async def _add(sessions, status):
    async with sessions.begin() as s:
        msg = OutboxMessage(
            topic="t", dedup_key=uuid4().hex, payload={}, status=status, attempt_count=5
        )
        s.add(msg)
    return msg.id


async def test_stats_and_requeue(database, capsys):
    sessions = database[1]
    empty = await outbox_stats(sessions)
    assert empty.oldest_open_age_seconds is None
    dead_a = await _add(sessions, "dead")
    await _add(sessions, "dead")
    await _add(sessions, "pending")
    await _add(sessions, "delivered")
    stats = await outbox_stats(sessions)
    assert stats.counts == {"pending": 1, "processing": 0, "delivered": 1, "dead": 2}
    assert stats.oldest_open_age_seconds is not None
    assert await requeue_dead(sessions, [dead_a]) == 1
    assert (await outbox_stats(sessions)).counts["dead"] == 1
    await AdminService(sessions).bootstrap_owner(1, "teste")
    assert await cli_run(["--as", "1", "requeue", "--reason", "falha"], sessions) == 0
    assert "1 mensagem" in capsys.readouterr().out
    assert (await outbox_stats(sessions)).counts == {
        "pending": 3,
        "processing": 0,
        "delivered": 1,
        "dead": 0,
    }
    assert await cli_run(["--as", "1", "stats"], sessions) == 0
    assert "pending" in capsys.readouterr().out


async def test_job_lock_runs_one_instance_at_a_time(database):
    engine_a = database[0]
    engine_b = create_async_engine(engine_a.url, connect_args={"server_settings": {}})
    runs = []
    gate = asyncio.Event()

    async def slow():
        runs.append("a")
        await gate.wait()

    async def other():
        runs.append("b")

    try:
        first = asyncio.create_task(run_exclusive(engine_a, "job-x", slow))
        await asyncio.sleep(0.3)
        # Same job on another instance is skipped; a different job still runs.
        assert await run_exclusive(engine_b, "job-x", other) is None
        await run_exclusive(engine_b, "job-y", other)
        gate.set()
        await first
        await run_exclusive(engine_b, "job-x", other)
    finally:
        await engine_b.dispose()
    assert runs == ["a", "b", "b"]


def test_scheduler_wraps_every_job_but_outbox():
    from asterion.bot.round_scheduler import build_round_scheduler

    jobs = {j.id: j for j in build_round_scheduler().get_jobs()}
    assert "outbox-dispatch" in jobs and "hunt-round-advance" in jobs
    assert jobs["hunt-round-advance"].func.__name__ == "run"
    # Metrics wrap every job (B6); only the lock is left out of the Outbox.
    assert jobs["outbox-dispatch"].func.__name__ == "instrumented"
    # The locks use their own pool, one connection per locked job.
    from asterion.infrastructure.db import session

    cells = [c.cell_contents for c in jobs["hunt-round-advance"].func.__closure__]
    lock_engine = next(c for c in cells if isinstance(c, AsyncEngine))
    assert lock_engine is not session.engine
    assert lock_engine.pool.size() == len(jobs) - 1
    assert all(
        lock_engine in [c.cell_contents for c in job.func.__closure__]
        for job_id, job in jobs.items()
        if job_id != "outbox-dispatch"
    )
