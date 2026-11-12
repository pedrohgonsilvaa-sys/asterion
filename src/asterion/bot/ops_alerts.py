"""Operator alerts on Telegram (B6): failing jobs, Outbox backlog, database down.

The `ops-alerts` scheduler job checks the health once a minute and sends a
direct message to `ASTERION_ALERT_CHAT_ID`. It never uses the Outbox, because the
Outbox (or the database behind it) may be what is broken.

Each problem has a key. A new problem is sent at once; while it lasts it is sent
again only after the cooldown; when it goes away a "resolvido" message follows.
New `dead` Outbox rows are a one-off notice (also limited by the cooldown).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from asterion.application.outbox import DEAD, PENDING, PROCESSING, outbox_stats
from asterion.infrastructure.metrics import JOB_HEALTH, JobHealth, database_up

logger = logging.getLogger(__name__)

Send = Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class AlertThresholds:
    job_failures: int = 3
    outbox_backlog: int = 500
    outbox_age_seconds: float = 1800.0
    cooldown_seconds: float = 1800.0


@dataclass
class OpsAlerter:
    """Remembers open problems between checks so it does not repeat itself."""

    send: Send
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    clock: Callable[[], float] = time.monotonic
    _open: dict[str, float] = field(default_factory=dict)
    _last_dead: int | None = None
    _last_dead_notice: float | None = None

    async def publish(self, problems: Mapping[str, str]) -> list[str]:
        """Send new or overdue problems and the ones that cleared. Returns the texts sent."""
        now = self.clock()
        sent: list[str] = []
        for key, text in problems.items():
            last = self._open.get(key)
            if last is None or now - last >= self.thresholds.cooldown_seconds:
                # Not delivered: it stays due and is tried again on the next check.
                if await self._send(f"⚠️ Asterion: {text}"):
                    sent.append(text)
                    self._open[key] = now
        for key in [k for k in self._open if k not in problems]:
            if await self._send(f"✅ Asterion: resolvido — {key}"):
                sent.append(f"resolvido — {key}")
                del self._open[key]
        return sent

    async def dead_notice(self, dead: int) -> str | None:
        """One-off notice when the `dead` count grew since the previous check."""
        previous, self._last_dead = self._last_dead, dead
        if previous is None or dead <= previous:
            return None
        now = self.clock()
        if (
            self._last_dead_notice is not None
            and now - self._last_dead_notice < self.thresholds.cooldown_seconds
        ):
            return None
        text = (
            f"{dead - previous} aviso(s) novo(s) da Outbox foram para dead ({dead} no total). "
            "Veja com: python -m asterion.outbox_cli"
        )
        if await self._send(f"⚠️ Asterion: {text}"):
            self._last_dead_notice = now
            return text
        return None

    async def _send(self, text: str) -> bool:
        try:
            await self.send(text)
        except Exception:
            logger.exception("Operator alert could not be sent")
            return False
        return True


def job_problems(health: Mapping[str, JobHealth], threshold: int) -> dict[str, str]:
    return {
        f"job {job_id}": (
            f"o job {job_id} falhou {state.consecutive_failures} vezes seguidas. "
            f"Último erro: {state.last_error}"
        )
        for job_id, state in sorted(health.items())
        if state.consecutive_failures >= threshold
    }


def outbox_problems(
    counts: Mapping[str, int], oldest_age: float | None, thresholds: AlertThresholds
) -> dict[str, str]:
    waiting = counts.get(PENDING, 0) + counts.get(PROCESSING, 0)
    problems: dict[str, str] = {}
    if waiting >= thresholds.outbox_backlog:
        problems["fila da Outbox"] = f"a Outbox tem {waiting} avisos esperando entrega."
    if oldest_age is not None and oldest_age >= thresholds.outbox_age_seconds:
        problems["atraso da Outbox"] = (
            f"o aviso mais antigo da Outbox espera há {int(oldest_age // 60)} min."
        )
    return problems


async def check_and_alert(alerter: OpsAlerter, engine: Any, sessions: Any) -> list[str]:
    """One check: database, jobs and Outbox. Returns the texts sent."""
    problems = job_problems(JOB_HEALTH, alerter.thresholds.job_failures)
    sent: list[str] = []
    if not await database_up(engine):
        problems["banco de dados"] = "o banco de dados não responde."
    else:
        try:
            stats = await outbox_stats(sessions)
        except Exception:
            logger.exception("Outbox stats failed during the alert check")
        else:
            problems.update(
                outbox_problems(stats.counts, stats.oldest_open_age_seconds, alerter.thresholds)
            )
            notice = await alerter.dead_notice(stats.counts.get(DEAD, 0))
            if notice:
                sent.append(notice)
    sent.extend(await alerter.publish(problems))
    return sent
