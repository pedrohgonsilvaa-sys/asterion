"""Daily reset and weekly Nova Vigília times (GDD §34). Pure functions.

Reset diário: 06:00 America/Sao_Paulo. Nova Vigília: monday 06:00 America/Sao_Paulo.
Times come from the zone (not a fixed UTC-3) and are computed from the clock, so they
never depend on a scheduler job having run.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

CYCLE_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RESET_TIME = time(6, 0)
NEW_VIGIL_WEEKDAY = 0  # monday (datetime.weekday())


def _local(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(CYCLE_TIMEZONE)


def _at_reset(day: datetime) -> datetime:
    return datetime.combine(day.date(), RESET_TIME, tzinfo=CYCLE_TIMEZONE)


def next_daily_reset(now: datetime) -> datetime:
    """First 06:00 (Sao Paulo) strictly after ``now``."""
    local = _local(now)
    candidate = _at_reset(local)
    if candidate <= local:
        candidate = _at_reset(local + timedelta(days=1))
    return candidate


def next_new_vigil(now: datetime) -> datetime:
    """First monday 06:00 (Sao Paulo) strictly after ``now``."""
    local = _local(now)
    days = (NEW_VIGIL_WEEKDAY - local.weekday()) % 7
    candidate = _at_reset(local + timedelta(days=days))
    if candidate <= local:
        candidate = _at_reset(local + timedelta(days=days + 7))
    return candidate
