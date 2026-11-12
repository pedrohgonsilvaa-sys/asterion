"""B6: operation metrics (/metrics) and operator alerts. Not game rules."""

from __future__ import annotations

from uuid import uuid4

import pytest
from aiogram.types import Update
from fastapi.testclient import TestClient

from asterion.application.outbox import OutboxReport
from asterion.bot.metrics_middleware import MetricsMiddleware
from asterion.bot.ops_alerts import (
    AlertThresholds,
    OpsAlerter,
    check_and_alert,
    job_problems,
    outbox_problems,
)
from asterion.infrastructure import metrics
from asterion.infrastructure.db.models import OutboxMessage
from asterion.infrastructure.metrics import (
    JOB_HEALTH,
    Counter,
    Gauge,
    Histogram,
    JobHealth,
    Registry,
    authorized,
    collect_live_gauges,
    instrument_job,
)


def test_registry_renders_prometheus_text() -> None:
    registry = Registry()
    hits = registry.register(Counter("x_total", "Hits.", ("kind",)))
    level = registry.register(Gauge("x_level", "Level."))
    took = registry.register(Histogram("x_seconds", "Time.", ("kind",), buckets=(0.1, 1.0)))
    hits.inc(kind='a"b')
    hits.inc(2, kind='a"b')
    level.set(1.5)
    took.observe(0.05, kind="a")
    took.observe(0.5, kind="a")
    text = registry.render()
    assert "# TYPE x_total counter" in text
    assert 'x_total{kind="a\\"b"} 3' in text
    assert "x_level 1.5" in text
    assert 'x_seconds_bucket{kind="a",le="0.1"} 1' in text
    assert 'x_seconds_bucket{kind="a",le="1"} 2' in text
    assert 'x_seconds_bucket{kind="a",le="+Inf"} 2' in text
    assert 'x_seconds_count{kind="a"} 2' in text
    assert 'x_seconds_sum{kind="a"} 0.55' in text
    with pytest.raises(ValueError):
        hits.inc(kind="a", extra="b")
    with pytest.raises(ValueError):
        hits.inc(-1, kind="a")


async def test_instrument_job_counts_failures_in_a_row_and_outbox_report() -> None:
    job_id = f"test-job-{uuid4().hex[:8]}"
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RuntimeError("boom")
        return OutboxReport(delivered=3, retried=1, dead=0)

    run = instrument_job(job_id, flaky)
    delivered_before = metrics.OUTBOX_DISPATCH.value(outcome="delivered")
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await run()
    assert JOB_HEALTH[job_id].consecutive_failures == 2
    assert JOB_HEALTH[job_id].last_error == "RuntimeError: boom"
    assert metrics.JOB_RUNS.value(job=job_id, outcome="error") == 2
    assert metrics.JOB_CONSECUTIVE_FAILURES.value(job=job_id) == 2
    await run()
    assert JOB_HEALTH[job_id].consecutive_failures == 0
    assert metrics.JOB_RUNS.value(job=job_id, outcome="ok") == 1
    assert metrics.JOB_CONSECUTIVE_FAILURES.value(job=job_id) == 0
    assert metrics.JOB_LAST_SUCCESS.value(job=job_id) > 0
    assert metrics.JOB_SECONDS.count(job=job_id) == 3
    assert metrics.OUTBOX_DISPATCH.value(outcome="delivered") == delivered_before + 3
    JOB_HEALTH.pop(job_id)


async def test_metrics_middleware_counts_ok_and_error_updates() -> None:
    middleware = MetricsMiddleware()
    update = Update.model_validate(
        {
            "update_id": 1,
            "callback_query": {
                "id": "c",
                "from": {"id": 7, "is_bot": False, "first_name": "A"},
                "chat_instance": "i",
                "data": "x",
            },
        }
    )
    ok_before = metrics.TELEGRAM_UPDATES.value(type="callback_query", outcome="ok")
    error_before = metrics.TELEGRAM_UPDATES.value(type="callback_query", outcome="error")

    async def fine(event, data):
        return "done"

    async def broken(event, data):
        raise ValueError("bad")

    assert await middleware(fine, update, {}) == "done"
    with pytest.raises(ValueError):
        await middleware(broken, update, {})
    assert metrics.TELEGRAM_UPDATES.value(type="callback_query", outcome="ok") == ok_before + 1
    assert (
        metrics.TELEGRAM_UPDATES.value(type="callback_query", outcome="error") == error_before + 1
    )
    assert metrics.TELEGRAM_UPDATE_SECONDS.count(type="callback_query") >= 2


def test_authorized() -> None:
    assert authorized(None, None)
    assert authorized("Bearer s3", "s3")
    assert not authorized(None, "s3")
    assert not authorized("Bearer nope", "s3")


def test_metrics_endpoint_survives_database_down(monkeypatch) -> None:
    from asterion.api import app as api

    async def down(engine, timeout=5.0):
        return False

    monkeypatch.setattr(metrics, "database_up", down)
    client = TestClient(api.app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "asterion_db_up 0" in response.text
    assert "asterion_job_runs_total" in response.text

    monkeypatch.setattr(api.settings, "metrics_token", "s3")
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer s3"}).status_code == 200


async def test_polling_metrics_server(monkeypatch) -> None:
    from aiohttp.test_utils import TestClient as AioClient
    from aiohttp.test_utils import TestServer

    from asterion.bot.metrics_server import build_metrics_app

    async def down(engine, timeout=5.0):
        return False

    monkeypatch.setattr(metrics, "database_up", down)
    async with AioClient(TestServer(build_metrics_app(None, None, "s3"))) as client:
        assert (await client.get("/metrics")).status == 401
        response = await client.get("/metrics", headers={"Authorization": "Bearer s3"})
        assert response.status == 200
        assert "asterion_db_up 0" in await response.text()


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def test_alerter_sends_once_repeats_after_cooldown_and_resolves() -> None:
    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    clock = _Clock()
    alerter = OpsAlerter(send, AlertThresholds(cooldown_seconds=600), clock)
    problem = {"banco de dados": "o banco de dados não responde."}
    await alerter.publish(problem)
    clock.now = 300
    await alerter.publish(problem)
    assert len(sent) == 1 and sent[0].startswith("⚠️")
    clock.now = 601
    await alerter.publish(problem)
    assert len(sent) == 2
    await alerter.publish({})
    assert sent[-1] == "✅ Asterion: resolvido — banco de dados"
    await alerter.publish({})
    assert len(sent) == 3


async def test_alerter_retries_when_telegram_fails() -> None:
    attempts: list[str] = []

    async def send(text: str) -> None:
        attempts.append(text)
        if len(attempts) == 1:
            raise RuntimeError("telegram down")

    alerter = OpsAlerter(send, AlertThresholds(), _Clock())
    problem = {"k": "algo"}
    assert await alerter.publish(problem) == []
    assert await alerter.publish(problem) == ["algo"]


async def test_dead_notice_only_when_dead_grows() -> None:
    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    clock = _Clock()
    alerter = OpsAlerter(send, AlertThresholds(cooldown_seconds=600), clock)
    assert await alerter.dead_notice(4) is None  # first check is the baseline
    assert await alerter.dead_notice(4) is None
    assert "2 aviso(s)" in (await alerter.dead_notice(6) or "")
    clock.now = 100
    assert await alerter.dead_notice(7) is None  # cooldown
    clock.now = 700
    assert await alerter.dead_notice(8) is not None
    assert len(sent) == 2


def test_job_and_outbox_problems() -> None:
    health = {"a": JobHealth(3, "RuntimeError: x"), "b": JobHealth(2, "y")}
    problems = job_problems(health, 3)
    assert list(problems) == ["job a"]
    assert "3 vezes seguidas" in problems["job a"]
    thresholds = AlertThresholds(outbox_backlog=10, outbox_age_seconds=600)
    assert outbox_problems({"pending": 5, "processing": 4}, 599.0, thresholds) == {}
    found = outbox_problems({"pending": 6, "processing": 4}, 600.0, thresholds)
    assert set(found) == {"fila da Outbox", "atraso da Outbox"}
    assert outbox_problems({}, None, thresholds) == {}


async def test_check_and_alert_reports_database_down(monkeypatch) -> None:
    from asterion.bot import ops_alerts

    async def down(engine, timeout=5.0):
        return False

    monkeypatch.setattr(ops_alerts, "database_up", down)
    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    texts = await check_and_alert(OpsAlerter(send), None, None)
    assert texts == ["o banco de dados não responde."]


async def test_live_gauges_and_alerts_with_database(database) -> None:
    engine, sessions = database
    async with sessions.begin() as s:
        for status in ("pending", "pending", "dead"):
            s.add(OutboxMessage(topic="t", dedup_key=uuid4().hex, payload={}, status=status))
    await collect_live_gauges(engine, sessions)
    assert metrics.DB_UP.value() == 1
    assert metrics.OUTBOX_MESSAGES.value(status="pending") == 2
    assert metrics.OUTBOX_MESSAGES.value(status="dead") == 1
    assert metrics.OUTBOX_OLDEST_OPEN_AGE.value() >= 0

    sent: list[str] = []

    async def send(text: str) -> None:
        sent.append(text)

    alerter = OpsAlerter(send, AlertThresholds(outbox_backlog=2))
    texts = await check_and_alert(alerter, engine, sessions)
    assert texts == ["a Outbox tem 2 avisos esperando entrega."]
    async with sessions.begin() as s:
        s.add(OutboxMessage(topic="t", dedup_key=uuid4().hex, payload={}, status="dead"))
    texts = await check_and_alert(alerter, engine, sessions)
    assert len(texts) == 1 and "1 aviso(s) novo(s)" in texts[0]


def test_scheduler_adds_unlocked_alert_job_and_instruments_jobs(monkeypatch) -> None:
    from asterion.bot import round_scheduler
    from asterion.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "alert_chat_id", -100123)
    monkeypatch.setattr(settings, "telegram_bot_enabled", True)
    wrapped: list[str] = []
    real = round_scheduler.instrument_job

    def spy(job_id, job):
        wrapped.append(job_id)
        return real(job_id, job)

    monkeypatch.setattr(round_scheduler, "instrument_job", spy)
    locked: list[str] = []
    monkeypatch.setattr(
        round_scheduler, "_exclusive", lambda engine, job_id, job: locked.append(job_id) or job
    )
    scheduler = round_scheduler.build_round_scheduler()
    ids = {job.id for job in scheduler.get_jobs()}
    assert round_scheduler.OPS_ALERTS_JOB in ids
    assert set(wrapped) == ids
    assert round_scheduler.OPS_ALERTS_JOB not in locked
    assert "outbox-dispatch" not in locked
    assert "hunt-round-advance" in locked


def test_blank_optional_ids_from_env_example_mean_unset(monkeypatch) -> None:
    from asterion.config import Settings

    for name in ("METRICS_PORT", "ALERT_CHAT_ID", "COMMUNITY_CHAT_ID"):
        monkeypatch.setenv(f"ASTERION_{name}", "")
    settings = Settings(_env_file=None)
    assert settings.metrics_port is None
    assert settings.alert_chat_id is None
    assert settings.community_chat_id is None
