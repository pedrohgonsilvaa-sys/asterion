"""Flood guard (token bucket) and operator suspensions with audit trail."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from asterion.admin_cli import run as cli_run
from asterion.application.sanctions import SanctionService
from asterion.bot.guards import FloodGuardMiddleware, SuspensionMiddleware
from asterion.infrastructure.db.models import AccountSanction


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


async def _pass(event, data):
    return "handled"


def test_flood_guard_allows_burst_then_blocks_then_refills():
    clock = Clock()
    guard = FloodGuardMiddleware(burst=3, per_second=1.0, clock=clock)
    assert [guard.allow(1) for _ in range(4)] == [True, True, True, False]
    clock.now += 1.0
    assert guard.allow(1) is True
    assert guard.allow(1) is False


def test_flood_guard_buckets_are_per_player():
    guard = FloodGuardMiddleware(burst=1, per_second=0.1, clock=Clock())
    assert guard.allow(1) is True
    assert guard.allow(1) is False
    assert guard.allow(2) is True


@pytest.mark.asyncio
async def test_flood_guard_middleware_drops_excess_updates():
    guard = FloodGuardMiddleware(burst=1, per_second=0.1, clock=Clock())
    data = {"event_from_user": SimpleNamespace(id=7, is_bot=False)}
    assert await guard(_pass, object(), data) == "handled"
    assert await guard(_pass, object(), data) is None


@pytest.mark.asyncio
async def test_flood_guard_ignores_updates_without_user():
    guard = FloodGuardMiddleware(burst=1, per_second=0.1, clock=Clock())
    for _ in range(5):
        assert await guard(_pass, object(), {}) == "handled"


@pytest.mark.asyncio
async def test_suspension_lifecycle_and_audit(database):
    _engine, sessions = database
    clock = Clock()
    now = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    service = SanctionService(sessions, clock=clock, now=lambda: now)

    assert await service.is_suspended(10) is False
    await service.suspend(10, reason="boosting", by="op", hours=24)
    assert await service.is_suspended(10) is True
    assert [row.telegram_id for row in await service.active()] == [10]

    assert await service.lift(10, by="op") == 1
    assert await service.is_suspended(10) is False
    assert await service.active() == []

    history = await service.history(10)
    assert len(history) == 1
    assert history[0].revoked_at is not None
    async with sessions() as session:
        total = await session.scalar(select(func.count()).select_from(AccountSanction))
    assert total == 1  # lifting never deletes the row


@pytest.mark.asyncio
async def test_suspension_expires(database):
    _engine, sessions = database
    moment = {"now": datetime(2026, 11, 11, 12, 0, tzinfo=UTC)}
    clock = Clock()
    service = SanctionService(sessions, clock=clock, now=lambda: moment["now"])
    await service.suspend(11, reason="teste", by="op", hours=2)
    assert await service.is_suspended(11) is True
    moment["now"] += timedelta(hours=3)
    clock.now += 60  # past the cache window
    assert await service.is_suspended(11) is False


@pytest.mark.asyncio
async def test_suspension_middleware_blocks_and_fails_open(database):
    _engine, sessions = database
    service = SanctionService(sessions)
    await service.suspend(12, reason="teste", by="op")
    middleware = SuspensionMiddleware(service)
    blocked = {"event_from_user": SimpleNamespace(id=12, is_bot=False)}
    free = {"event_from_user": SimpleNamespace(id=13, is_bot=False)}
    assert await middleware(_pass, object(), blocked) is None
    assert await middleware(_pass, object(), free) == "handled"

    class Broken:
        async def is_suspended(self, _telegram_id):
            raise RuntimeError("database down")

    assert await SuspensionMiddleware(Broken())(_pass, object(), blocked) == "handled"


@pytest.mark.asyncio
async def test_admin_cli_roundtrip(database):
    _engine, sessions = database
    assert await cli_run(["bootstrap-owner", "1", "--reason", "início"], sessions) == [
        "1 agora é owner"
    ]
    out = await cli_run(
        ["--as", "1", "suspend", "20", "--reason", "multicontas", "--hours", "5"], sessions
    )
    assert "20" in out[0] and "ativa" in out[0]
    assert "20" in (await cli_run(["--as", "1", "list"], sessions))[0]
    assert await cli_run(["--as", "1", "lift", "20", "--reason", "ok"], sessions) == [
        "1 suspensão(ões) encerrada(s)"
    ]
    assert await cli_run(["--as", "1", "list"], sessions) == ["nenhuma suspensão ativa"]
    assert "encerrada" in (await cli_run(["--as", "1", "history", "20"], sessions))[0]
