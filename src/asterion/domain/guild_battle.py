"""Batalha de Guildas pure rules (GDD v1.6.0 §15, §49.14).

Author decisions for gaps the GDD leaves open (2026-11-09):

- only the Leader registers the Guild (§55.5);
- pairing runs when registration closes (20:30) and Entry Confirmation runs from
  then until 20:50, America/Sao_Paulo, the Arena time zone;
- registered Guilds are sorted by technical rating and neighbours are paired;
- an odd count gives the bye to the Guild with fewest byes, then the lowest
  rating, then the lowest id;
- the technical rating uses the Arena Elo, ``round(K x (S - E))``, with S 1/0.5/0
  and no floor;
- both Fronts start at 21:00; the Champion fights after both have ended;
- a side with an unconfirmed combatant loses that Front; both sides absent score
  0/0 on it;
- an AFK combatant is withdrawn as defeated and the team fights on;
- there is no surrender;
- a reserve may replace an unconfirmed combatant until 20:50 and must confirm;
- final rewards are not delivered yet, only standings and eligibility;
- standings tie-break by technical rating, then by Guild id.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo

from asterion.domain.arena import _rating_delta

GUILD_BATTLE_TIMEZONE = ZoneInfo("America/Sao_Paulo")
# Wednesday and Sunday, 21:00 (§49.14). Python weekday(): Monday is 0.
BATTLE_WEEKDAYS = frozenset({2, 6})
BATTLE_START_TIME = time(21, 0)
REGISTRATION_OPENS_BEFORE = timedelta(hours=24)
REGISTRATION_CLOSES_BEFORE = timedelta(minutes=30)  # 20:30
CONFIRMATION_CLOSES_BEFORE = timedelta(minutes=10)  # 20:50

GUILD_BATTLE_MIN_LEVEL = 30
TURN_TTL = timedelta(seconds=60)
COMBATANTS = 5
MAX_RESERVES = 2

INITIAL_RATING = 1500
RATING_K_EARLY = 48
RATING_K_LATE = 32
RATING_EARLY_BATTLES = 5

WIN_POINTS = 3
DRAW_POINTS = 1
LOSS_POINTS = 0
BYE_POINTS = 0
MIN_REAL_BATTLES_FOR_REWARD = 10
MIN_INDIVIDUAL_PARTICIPATIONS = 4

HALF = Decimal("0.5")


class FightKind(StrEnum):
    FRONT_I = "front_1"
    FRONT_II = "front_2"
    CHAMPION = "champion"


FRONT_SIZES: dict[FightKind, int] = {FightKind.FRONT_I: 2, FightKind.FRONT_II: 3}
FRONTS: tuple[FightKind, ...] = (FightKind.FRONT_I, FightKind.FRONT_II)


@dataclass(frozen=True, slots=True)
class BattleSchedule:
    starts_at: datetime
    registration_opens_at: datetime
    registration_closes_at: datetime
    confirmation_closes_at: datetime


def schedule_for(starts_at: datetime) -> BattleSchedule:
    return BattleSchedule(
        starts_at,
        starts_at - REGISTRATION_OPENS_BEFORE,
        starts_at - REGISTRATION_CLOSES_BEFORE,
        starts_at - CONFIRMATION_CLOSES_BEFORE,
    )


def next_battle_start(now: datetime) -> datetime:
    """The first Batalha de Guildas that starts strictly after ``now``."""
    local = now.astimezone(GUILD_BATTLE_TIMEZONE)
    for offset in range(8):
        day = (local + timedelta(days=offset)).date()
        if day.weekday() not in BATTLE_WEEKDAYS:
            continue
        start = datetime.combine(day, BATTLE_START_TIME, GUILD_BATTLE_TIMEZONE)
        if start > now:
            return start.astimezone(now.tzinfo)
    raise AssertionError("A battle day exists in every week.")


def open_registration(now: datetime) -> BattleSchedule | None:
    """The battle whose registration window holds ``now``, if any."""
    schedule = schedule_for(next_battle_start(now))
    if schedule.registration_opens_at <= now < schedule.registration_closes_at:
        return schedule
    return None


def rating_k(real_battles: int) -> int:
    return RATING_K_EARLY if real_battles < RATING_EARLY_BATTLES else RATING_K_LATE


def rating_after_battle(rating: int, opponent: int, score: Decimal, real_battles: int) -> int:
    """Technical Guild rating after one real battle; ``real_battles`` is before it."""
    return rating + _rating_delta(rating_k(real_battles), rating, opponent, score)


def classification_points(score: Decimal) -> int:
    if score == 1:
        return WIN_POINTS
    if score == HALF:
        return DRAW_POINTS
    return LOSS_POINTS


@dataclass(frozen=True, slots=True)
class PairingCandidate:
    guild_id: UUID
    rating: int
    byes: int


@dataclass(frozen=True, slots=True)
class Pairing:
    pairs: tuple[tuple[UUID, UUID], ...]
    bye: UUID | None


def pair_guilds(candidates: Sequence[PairingCandidate]) -> Pairing:
    """Pair neighbours by rating; an odd count rotates the bye."""
    pool = list(candidates)
    bye = None
    if len(pool) % 2:
        chosen = min(pool, key=lambda item: (item.byes, item.rating, item.guild_id))
        pool.remove(chosen)
        bye = chosen.guild_id
    ordered = sorted(pool, key=lambda item: (-item.rating, item.guild_id))
    pairs = tuple(
        (ordered[index].guild_id, ordered[index + 1].guild_id)
        for index in range(0, len(ordered), 2)
    )
    return Pairing(pairs, bye)


def front_points(winner_side: str | None, *, absent_a: bool, absent_b: bool) -> tuple[Decimal, ...]:
    """Points of one finished Front for sides a and b."""
    if absent_a and absent_b:
        return (Decimal(0), Decimal(0))
    if winner_side == "a":
        return (Decimal(1), Decimal(0))
    if winner_side == "b":
        return (Decimal(0), Decimal(1))
    return (HALF, HALF)


def no_show_winner(absent_a: bool, absent_b: bool) -> str | None:
    """Winner of a fight decided before it starts; ``None`` when both are absent."""
    if absent_a and not absent_b:
        return "b"
    if absent_b and not absent_a:
        return "a"
    return None


def battle_score(winner_side: str | None) -> tuple[Decimal, Decimal]:
    if winner_side == "a":
        return (Decimal(1), Decimal(0))
    if winner_side == "b":
        return (Decimal(0), Decimal(1))
    return (HALF, HALF)


@dataclass(frozen=True, slots=True)
class StandingCandidate:
    guild_id: UUID
    points: int
    rating: int


def order_standings(rows: Sequence[StandingCandidate]) -> list[StandingCandidate]:
    return sorted(rows, key=lambda row: (-row.points, -row.rating, row.guild_id))


def reward_eligible(real_battles: int) -> bool:
    return real_battles >= MIN_REAL_BATTLES_FOR_REWARD


def individual_reward_eligible(participations: int) -> bool:
    return participations >= MIN_INDIVIDUAL_PARTICIPATIONS
