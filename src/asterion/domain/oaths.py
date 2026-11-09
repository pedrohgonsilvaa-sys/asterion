"""Juramento da Guilda (GDD v1.6.0 §22.1, §49.15).

Windows, limits, thresholds and rewards come from §49.15. The source does not say
what a Provação contains; the author decided on 2026-11-09:

- a Provação is three combats in a row (Elite, Elite, Chefe), using the Masmorra
  group scaling, with HP carried between them;
- C, básicos and Fragmentos use each character's own level, snapshotted when the
  character binds to the cycle; enemies use the group's average level.

``OATH_TRIAL_CATALOG`` is empty on purpose: the source names no Provação yet. With
an empty catalog no cycle is ever created.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from asterion.domain.combat_math import CombatStats, StatMultipliers, enemy_stats
from asterion.domain.dungeons import catalyst_material_id, rune_grade
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import REGION_SUPPLY, Bundle
from asterion.domain.road import ARCHETYPE, CATEGORY, Creature

D = Decimal

OATH_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RULESET = "oath_v1"

# Monday is 0: sexta-feira.
OPENING_WEEKDAY = 4
OPENING_TIME = time(18, 0)
WINDOW = timedelta(hours=48)
GRACE = timedelta(minutes=30)
# Implementation choice, same limit as the Road's group combat: a roster that
# stops playing must not hold its members' Foreground until the grace period.
ATTEMPT_INACTIVITY = timedelta(minutes=30)

PROVACOES_PER_CYCLE = 3
MAX_GROUP_SIZE = 4
STAGE_COUNT = 3
STAGE_POINTS = (10, 15, 20)
CONCLUSION_POINTS = 15
MAX_INDIVIDUAL_CONTRIBUTION = 180
MIN_INDIVIDUAL_CONTRIBUTION = 60
TIER_THRESHOLDS = (120, 300, 540, 780)
TREASURY_BY_TIER = (2_000, 4_000, 7_000, 10_000)

# §49.6, Masmorra group scaling.
GROUP_HP_STEP = D("0.78")
GROUP_ATTACK_STEP = D("0.07")
BOSS_BASE = StatMultipliers(D("3.00"), D("1.10"), D("1.10"), D("1.00"))
ELITE_BASE = CATEGORY["elite"]
_BOSS_CATEGORY_HP = CATEGORY["boss"].hp


@dataclass(frozen=True, slots=True)
class IndividualReward:
    crown_multiplier: Decimal
    basics: int
    fragments: int
    catalysts: int


REWARD_BY_TIER = (
    IndividualReward(D("0.50"), 4, 0, 0),
    IndividualReward(D("0.75"), 6, 1, 0),
    IndividualReward(D("1.00"), 8, 2, 1),
    IndividualReward(D("1.25"), 10, 3, 1),
)


@dataclass(frozen=True, slots=True)
class OathEncounter:
    creature: Creature
    flavor: str


@dataclass(frozen=True, slots=True)
class OathTrialDefinition:
    trial_id: str
    name: str
    encounters: tuple[OathEncounter, ...]
    conclusion_flavor: str

    def __post_init__(self) -> None:
        if len(self.encounters) != STAGE_COUNT:
            raise ValueError("A Provação has exactly three combats.")
        categories = tuple(encounter.creature.category for encounter in self.encounters)
        if categories != ("elite", "elite", "boss"):
            raise ValueError("A Provação is Elite, Elite and Chefe.")

    def encounter(self, stage: int) -> OathEncounter:
        return self.encounters[stage - 1]


OATH_TRIAL_CATALOG: tuple[OathTrialDefinition, ...] = ()


def latest_opening(now: datetime) -> datetime:
    """The most recent Friday 18:00 at or before ``now``."""
    local = now.astimezone(OATH_TIMEZONE)
    for days_back in range(0, 8):
        day = (local - timedelta(days=days_back)).date()
        if day.weekday() != OPENING_WEEKDAY:
            continue
        slot = datetime.combine(day, OPENING_TIME, OATH_TIMEZONE)
        if slot <= local:
            return slot
    raise RuntimeError("The weekly schedule always has a previous opening.")


def next_opening(now: datetime) -> datetime:
    """The first Friday 18:00 strictly after ``now``."""
    local = now.astimezone(OATH_TIMEZONE)
    for days_ahead in range(0, 9):
        day = (local + timedelta(days=days_ahead)).date()
        if day.weekday() != OPENING_WEEKDAY:
            continue
        slot = datetime.combine(day, OPENING_TIME, OATH_TIMEZONE)
        if slot > local:
            return slot
    raise RuntimeError("The weekly schedule always has a next opening.")


def cycle_key(opening: datetime) -> str:
    """Stable per opening: a restart or deploy resolves to the same cycle."""
    return opening.astimezone(OATH_TIMEZONE).strftime("%Y%m%d")


def definition_for_opening(
    catalog: tuple[OathTrialDefinition, ...], opening: datetime
) -> OathTrialDefinition | None:
    """Deterministic rotation, so every process picks the same Provação."""
    if not catalog:
        return None
    week = opening.astimezone(OATH_TIMEZONE).date().toordinal() // 7
    return catalog[week % len(catalog)]


def group_scale(roster_size: int) -> StatMultipliers:
    if not 1 <= roster_size <= MAX_GROUP_SIZE:
        raise ValueError("A Provação has one to four participants.")
    extra = roster_size - 1
    return StatMultipliers(
        D(1) + GROUP_HP_STEP * extra, D(1) + GROUP_ATTACK_STEP * extra, D(1), D(1)
    )


def enemy_level(levels: tuple[int, ...]) -> int:
    """The group's average level."""
    if not levels:
        raise ValueError("A Provação needs at least one participant.")
    average = D(sum(levels)) / D(len(levels))
    return int(average.to_integral_value(rounding=ROUND_HALF_UP))


def encounter_stats(creature: Creature, level: int, roster_size: int) -> CombatStats:
    """One single rounding on the final attribute (§49.6)."""
    base = BOSS_BASE if creature.category == "boss" else ELITE_BASE
    return enemy_stats(level, base, ARCHETYPE[creature.archetype], group_scale(roster_size))


def engine_multipliers(creature: Creature, roster_size: int) -> StatMultipliers:
    """Factors over the engine's creature category, for the opening turn."""
    scale = group_scale(roster_size)
    if creature.category != "boss":
        return scale
    return StatMultipliers(BOSS_BASE.hp / _BOSS_CATEGORY_HP * scale.hp, scale.attack, D(1), D(1))


def stage_milestones(stage: int) -> tuple[tuple[str, int], ...]:
    """Milestones earned by winning ``stage``; the last one also concludes the Provação."""
    milestones = [(f"stage_{stage}", STAGE_POINTS[stage - 1])]
    if stage == STAGE_COUNT:
        milestones.append(("conclusion", CONCLUSION_POINTS))
    return tuple(milestones)


def tier_for(contribution: int) -> int:
    """The highest tier reached; 0 means no minimum tier was reached."""
    return sum(1 for threshold in TIER_THRESHOLDS if contribution >= threshold)


def next_threshold(contribution: int) -> int | None:
    return next((value for value in TIER_THRESHOLDS if contribution < value), None)


def treasury_reward(tier: int) -> int:
    return TREASURY_BY_TIER[tier - 1] if tier else 0


def is_eligible(contribution: int) -> bool:
    return contribution >= MIN_INDIVIDUAL_CONTRIBUTION


def region_for_level(level: int) -> str:
    """Fragment grades and Regions advance together, every ten levels."""
    return tuple(REGION_SUPPLY)[rune_grade(level) - 1]


def reward_bundle(level: int, tier: int) -> Bundle:
    reward = REWARD_BY_TIER[tier - 1]
    return Bundle(
        crowns=round_10(reward.crown_multiplier * crowns_per_level(level)),
        basics=reward.basics,
        fragments=reward.fragments,
    )


def reward_catalysts(tier: int) -> int:
    return REWARD_BY_TIER[tier - 1].catalysts


def reward_catalyst_id(level: int) -> str:
    return catalyst_material_id(level)
