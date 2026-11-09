"""Expedição assíncrona (GDD v1.6.0 §22.2, §49.15).

Windows, the score scale and the rewards come from §49.15. The author decided on
2026-11-09 what the source leaves open:

- the Leader or an Officer picks the roster, up to Monday 18:00;
- each stage offers three options, whose text hints at the best one;
- a stage's score is the roster average; a missing answer uses the default.

``EXPEDITION_ROUTE_CATALOG`` is empty on purpose: the source names no Route yet.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import Bundle

D = Decimal

EXPEDITION_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RULESET = "expedition_v1"

# Monday is 0.
START_WEEKDAY = 0
START_TIME = time(18, 0)
DURATION = timedelta(hours=72)
STAGE_DURATION = timedelta(hours=24)
STAGE_COUNT = 3
ROSTER_MIN = 3
ROSTER_MAX = 6
MIN_ACTIVE_STAGES = 2
DEFAULT_POINTS = 20


class OptionQuality(StrEnum):
    FAVORABLE = "favorable"
    NEUTRAL = "neutral"
    POOR = "poor"


QUALITY_POINTS = {
    OptionQuality.FAVORABLE: 100,
    OptionQuality.NEUTRAL: 50,
    OptionQuality.POOR: 25,
}


class ExpeditionResult(StrEnum):
    FAILED = "failed"
    COMPLETED = "completed"
    DEEP = "deep"
    EXCEPTIONAL = "exceptional"


RESULT_LABELS = {
    ExpeditionResult.FAILED: "Fracassada",
    ExpeditionResult.COMPLETED: "Concluída",
    ExpeditionResult.DEEP: "Profunda",
    ExpeditionResult.EXCEPTIONAL: "Excepcional",
}
TREASURY_BY_RESULT = {
    ExpeditionResult.FAILED: 0,
    ExpeditionResult.COMPLETED: 1_500,
    ExpeditionResult.DEEP: 3_000,
    ExpeditionResult.EXCEPTIONAL: 5_000,
}
_REWARDS = {
    ExpeditionResult.COMPLETED: (D("0.50"), 3, 0),
    ExpeditionResult.DEEP: (D("0.80"), 5, 1),
    ExpeditionResult.EXCEPTIONAL: (D("1.25"), 8, 3),
}


@dataclass(frozen=True, slots=True)
class ExpeditionOption:
    option_id: str
    label: str
    quality: OptionQuality


@dataclass(frozen=True, slots=True)
class ExpeditionStage:
    flavor: str
    options: tuple[ExpeditionOption, ...]

    def __post_init__(self) -> None:
        if sorted(option.quality for option in self.options) != sorted(OptionQuality):
            raise ValueError("A stage has one favorable, one neutral and one poor option.")
        if len({option.option_id for option in self.options}) != len(self.options):
            raise ValueError("Option ids must be unique within a stage.")

    def option(self, option_id: str) -> ExpeditionOption | None:
        return next((row for row in self.options if row.option_id == option_id), None)


@dataclass(frozen=True, slots=True)
class ExpeditionRoute:
    route_id: str
    name: str
    stages: tuple[ExpeditionStage, ...]
    return_flavor: str

    def __post_init__(self) -> None:
        if len(self.stages) != STAGE_COUNT:
            raise ValueError("A Route has exactly three stages.")

    def stage(self, number: int) -> ExpeditionStage:
        return self.stages[number - 1]


EXPEDITION_ROUTE_CATALOG: tuple[ExpeditionRoute, ...] = ()


def next_start(now: datetime) -> datetime:
    """The first Monday 18:00 strictly after ``now``."""
    local = now.astimezone(EXPEDITION_TIMEZONE)
    for days_ahead in range(0, 9):
        day = (local + timedelta(days=days_ahead)).date()
        if day.weekday() != START_WEEKDAY:
            continue
        slot = datetime.combine(day, START_TIME, EXPEDITION_TIMEZONE)
        if slot > local:
            return slot
    raise RuntimeError("The weekly schedule always has a next start.")


def week_key(start: datetime) -> str:
    return start.astimezone(EXPEDITION_TIMEZONE).strftime("%Y%m%d")


def route_for_start(
    catalog: tuple[ExpeditionRoute, ...], start: datetime
) -> ExpeditionRoute | None:
    """Deterministic rotation, so every process picks the same Route."""
    if not catalog:
        return None
    week = start.astimezone(EXPEDITION_TIMEZONE).date().toordinal() // 7
    return catalog[week % len(catalog)]


def stage_at(starts_at: datetime, now: datetime) -> int:
    """The stage open at ``now``; 0 before the start, 4 after the end."""
    if now < starts_at:
        return 0
    return min(STAGE_COUNT + 1, int((now - starts_at) / STAGE_DURATION) + 1)


def stage_ends_at(starts_at: datetime, stage: int) -> datetime:
    return starts_at + STAGE_DURATION * stage


def final_score(points_by_stage: Iterable[Iterable[int]]) -> int:
    """Sum of each stage's roster average, rounded down once at the end."""
    total = sum((D(sum(points)) / D(len(points)) for points in map(tuple, points_by_stage)), D(0))
    return int(total)


def result_for(score: int) -> ExpeditionResult:
    if score >= 240:
        return ExpeditionResult.EXCEPTIONAL
    if score >= 180:
        return ExpeditionResult.DEEP
    if score >= 100:
        return ExpeditionResult.COMPLETED
    return ExpeditionResult.FAILED


def treasury_reward(result: ExpeditionResult) -> int:
    return TREASURY_BY_RESULT[result]


def is_eligible(active_stages: int) -> bool:
    return active_stages >= MIN_ACTIVE_STAGES


def reward_bundle(level: int, result: ExpeditionResult) -> Bundle | None:
    reward = _REWARDS.get(result)
    if reward is None:
        return None
    multiplier, basics, fragments = reward
    return Bundle(
        crowns=round_10(multiplier * crowns_per_level(level)),
        basics=basics,
        fragments=fragments,
    )
