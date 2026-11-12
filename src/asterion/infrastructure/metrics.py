"""Operation metrics in the Prometheus text format (B6). Not game rules.

A small in-process registry, so no extra dependency: counters, gauges and
histograms with labels. Each process (bot in polling, API in webhook) keeps its
own numbers; `render()` turns them into the text Prometheus reads at `/metrics`.

`collect_live_gauges` refreshes the values read at scrape time (database up,
connection pool, Outbox queue) right before rendering.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

LabelValues = tuple[str, ...]

# Seconds. Handlers and jobs are short; the tail shows what is stuck.
DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_labels(names: Sequence[str], values: Sequence[str]) -> str:
    if not names:
        return ""
    pairs = ",".join(f'{n}="{_escape(v)}"' for n, v in zip(names, values, strict=True))
    return "{" + pairs + "}"


def _format_number(value: float) -> str:
    if value == float("inf"):
        return "+Inf"
    if float(value).is_integer():
        return str(int(value))
    return repr(float(value))


class _Metric:
    kind = ""

    def __init__(self, name: str, documentation: str, labels: Sequence[str] = ()):
        self.name = name
        self.documentation = documentation
        self.label_names = tuple(labels)

    def _key(self, labels: dict[str, str]) -> LabelValues:
        if set(labels) != set(self.label_names):
            raise ValueError(f"{self.name} expects labels {self.label_names}, got {tuple(labels)}")
        return tuple(str(labels[n]) for n in self.label_names)

    def header(self) -> list[str]:
        return [f"# HELP {self.name} {self.documentation}", f"# TYPE {self.name} {self.kind}"]

    def samples(self) -> Iterable[str]:  # pragma: no cover - overridden
        return ()


class Counter(_Metric):
    kind = "counter"

    def __init__(self, name: str, documentation: str, labels: Sequence[str] = ()):
        super().__init__(name, documentation, labels)
        self._values: dict[LabelValues, float] = {}

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        if amount < 0:
            raise ValueError("counters only go up")
        key = self._key(labels)
        self._values[key] = self._values.get(key, 0.0) + amount

    def value(self, **labels: str) -> float:
        return self._values.get(self._key(labels), 0.0)

    def samples(self) -> Iterable[str]:
        for key, value in sorted(self._values.items()):
            labels = _format_labels(self.label_names, key)
            yield f"{self.name}{labels} {_format_number(value)}"


class Gauge(Counter):
    kind = "gauge"

    def set(self, value: float, **labels: str) -> None:
        self._values[self._key(labels)] = float(value)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = self._key(labels)
        self._values[key] = self._values.get(key, 0.0) + amount

    def clear(self) -> None:
        self._values.clear()


@dataclass
class _HistogramState:
    buckets: list[float]
    total: float = 0.0
    count: int = 0


class Histogram(_Metric):
    kind = "histogram"

    def __init__(
        self,
        name: str,
        documentation: str,
        labels: Sequence[str] = (),
        buckets: Sequence[float] = DEFAULT_BUCKETS,
    ):
        super().__init__(name, documentation, labels)
        self.bounds = tuple(sorted(buckets))
        self._states: dict[LabelValues, _HistogramState] = {}

    def observe(self, value: float, **labels: str) -> None:
        key = self._key(labels)
        state = self._states.get(key)
        if state is None:
            state = self._states[key] = _HistogramState([0.0] * len(self.bounds))
        for index, bound in enumerate(self.bounds):
            if value <= bound:
                state.buckets[index] += 1
        state.total += value
        state.count += 1

    def count(self, **labels: str) -> int:
        state = self._states.get(self._key(labels))
        return 0 if state is None else state.count

    def samples(self) -> Iterable[str]:
        for key, state in sorted(self._states.items()):
            for bound, hits in zip(self.bounds, state.buckets, strict=True):
                labels = _format_labels((*self.label_names, "le"), (*key, _format_number(bound)))
                yield f"{self.name}_bucket{labels} {_format_number(hits)}"
            labels = _format_labels((*self.label_names, "le"), (*key, "+Inf"))
            yield f"{self.name}_bucket{labels} {state.count}"
            base = _format_labels(self.label_names, key)
            yield f"{self.name}_sum{base} {_format_number(state.total)}"
            yield f"{self.name}_count{base} {state.count}"


@dataclass
class Registry:
    metrics: list[_Metric] = field(default_factory=list)

    def register[M: _Metric](self, metric: M) -> M:
        self.metrics.append(metric)
        return metric

    def render(self) -> str:
        lines: list[str] = []
        for metric in self.metrics:
            lines.extend(metric.header())
            lines.extend(metric.samples())
        return "\n".join(lines) + "\n"


CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

REGISTRY = Registry()

TELEGRAM_UPDATES = REGISTRY.register(
    Counter(
        "asterion_telegram_updates_total",
        "Telegram updates processed, by update type and outcome (ok or error).",
        ("type", "outcome"),
    )
)
TELEGRAM_UPDATE_SECONDS = REGISTRY.register(
    Histogram(
        "asterion_telegram_update_duration_seconds",
        "Time spent handling one Telegram update.",
        ("type",),
    )
)
JOB_RUNS = REGISTRY.register(
    Counter(
        "asterion_job_runs_total",
        "Scheduler job runs, by job and outcome (ok or error).",
        ("job", "outcome"),
    )
)
JOB_SECONDS = REGISTRY.register(
    Histogram("asterion_job_duration_seconds", "Time spent in one scheduler job run.", ("job",))
)
JOB_CONSECUTIVE_FAILURES = REGISTRY.register(
    Gauge(
        "asterion_job_consecutive_failures",
        "Failed runs in a row of a scheduler job (0 after a success).",
        ("job",),
    )
)
JOB_LAST_SUCCESS = REGISTRY.register(
    Gauge(
        "asterion_job_last_success_timestamp_seconds",
        "Unix time of the last successful run of a scheduler job.",
        ("job",),
    )
)
OUTBOX_DISPATCH = REGISTRY.register(
    Counter(
        "asterion_outbox_dispatch_total",
        "Outbox deliveries made by this process, by outcome (delivered, retried, dead).",
        ("outcome",),
    )
)
OUTBOX_MESSAGES = REGISTRY.register(
    Gauge("asterion_outbox_messages", "Outbox rows per status, read at scrape time.", ("status",))
)
OUTBOX_OLDEST_OPEN_AGE = REGISTRY.register(
    Gauge(
        "asterion_outbox_oldest_open_age_seconds",
        "Age of the oldest Outbox row still pending or processing (0 when empty).",
    )
)
DB_UP = REGISTRY.register(
    Gauge("asterion_db_up", "1 when the database answered SELECT 1 at scrape time, else 0.")
)
DB_POOL_CONNECTIONS = REGISTRY.register(
    Gauge(
        "asterion_db_pool_connections",
        "Game connection pool: checked_out, idle, overflow and size.",
        ("state",),
    )
)


@dataclass
class JobHealth:
    consecutive_failures: int = 0
    last_error: str = ""


# job id -> health in this process; read by the operator alerts.
JOB_HEALTH: dict[str, JobHealth] = {}


def instrument_job(
    job_id: str,
    job: Callable[[], Awaitable[Any]],
    clock: Callable[[], float] = time.perf_counter,
) -> Callable[[], Awaitable[Any]]:
    """Wrap a scheduler job: count runs, time them and track failures in a row."""

    async def run() -> Any:
        started = clock()
        health = JOB_HEALTH.setdefault(job_id, JobHealth())
        try:
            result = await job()
        except Exception as exc:
            health.consecutive_failures += 1
            health.last_error = f"{type(exc).__name__}: {exc}"[:300]
            JOB_RUNS.inc(job=job_id, outcome="error")
            JOB_CONSECUTIVE_FAILURES.set(health.consecutive_failures, job=job_id)
            raise
        else:
            health.consecutive_failures = 0
            health.last_error = ""
            JOB_RUNS.inc(job=job_id, outcome="ok")
            JOB_CONSECUTIVE_FAILURES.set(0, job=job_id)
            JOB_LAST_SUCCESS.set(time.time(), job=job_id)
            record_outbox_report(result)
            return result
        finally:
            JOB_SECONDS.observe(max(clock() - started, 0.0), job=job_id)

    run.__name__ = "instrumented"
    return run


def record_outbox_report(result: object) -> None:
    from asterion.application.outbox import OutboxReport

    if isinstance(result, OutboxReport):
        for outcome in ("delivered", "retried", "dead"):
            amount = getattr(result, outcome)
            if amount:
                OUTBOX_DISPATCH.inc(amount, outcome=outcome)


async def database_up(engine: Any, timeout: float = 5.0) -> bool:
    from sqlalchemy import text

    async def ping() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(ping(), timeout)
    except Exception:
        logger.warning("Database health check failed", exc_info=True)
        return False
    return True


def record_pool(engine: Any) -> None:
    pool = getattr(engine, "pool", None)
    for state, method in (
        ("checked_out", "checkedout"),
        ("idle", "checkedin"),
        ("overflow", "overflow"),
        ("size", "size"),
    ):
        reader = getattr(pool, method, None)
        if callable(reader):
            DB_POOL_CONNECTIONS.set(float(reader()), state=state)


async def collect_live_gauges(engine: Any, sessions: Any, timeout: float = 5.0) -> None:
    """Refresh the scrape-time gauges. A failing database never breaks `/metrics`."""
    from asterion.application.outbox import outbox_stats

    record_pool(engine)
    up = await database_up(engine, timeout)
    DB_UP.set(1.0 if up else 0.0)
    if not up:
        return
    try:
        stats = await asyncio.wait_for(outbox_stats(sessions), timeout)
    except Exception:
        logger.warning("Outbox stats failed", exc_info=True)
        return
    for status, count in stats.counts.items():
        OUTBOX_MESSAGES.set(count, status=status)
    OUTBOX_OLDEST_OPEN_AGE.set(stats.oldest_open_age_seconds or 0.0)


async def render_metrics(engine: Any, sessions: Any) -> str:
    await collect_live_gauges(engine, sessions)
    return REGISTRY.render()


def authorized(header: str | None, token: str | None) -> bool:
    """No token configured means open; otherwise `Authorization: Bearer <token>`."""
    if not token:
        return True
    import hmac

    return header is not None and hmac.compare_digest(header, f"Bearer {token}")
