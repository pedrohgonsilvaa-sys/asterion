"""Pure rules of Duelo and Arena da Vigília.

Sources: GDD Estrutural v1.6.0 §13, §14 and §49.14.

Author delegation of 2026-11-08, for points the GDD leaves open:
- a Duelo invite lives for ``DUEL_INVITE_TTL``, the same 45s of the Arena;
- Duelo follows the Arena's clean start, turn timer, AFK and Surrender rules;
- "recent rematch" means ``RECENT_REMATCH`` (borrowed from PvPvE §52): the pair
  repeats only when no other compatible opponent is waiting;
- a placed player facing someone in Placement uses that opponent's table value;
- a single turn timeout only loses that turn.

``round(x)`` in §49.14 has no tie rule of its own, so it follows the §49.0 rule
for quantities with an explicit step: ties-to-even.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from zoneinfo import ZoneInfo

ARENA_TIMEZONE = ZoneInfo("America/Sao_Paulo")

DUEL_MIN_LEVEL = 10
ARENA_MIN_LEVEL = 30
ARENA_WINDOWS: tuple[tuple[time, time], ...] = (
    (time(12, 0), time(13, 0)),
    (time(19, 0), time(20, 0)),
)

CONFIRMATION_TTL = timedelta(seconds=45)
DUEL_INVITE_TTL = timedelta(seconds=45)
TURN_TTL = timedelta(seconds=90)
AFK_CONSECUTIVE_TIMEOUTS = 2
AFK_TOTAL_TIMEOUTS = 3
SURRENDER_MIN_ROUND = 5
RECENT_REMATCH = timedelta(minutes=10)

PLACEMENT_MATCHES = 5
PLACEMENT_RENOME: tuple[int, ...] = (400, 600, 800, 1000, 1200, 1400)
RENOME_K = 40
INITIAL_MMR = 1500
MMR_K_EARLY = 48
MMR_K_LATE = 32
MMR_EARLY_MATCHES = 20

DODGE_WINDOW = timedelta(minutes=60)
DODGE_COOLDOWNS: tuple[timedelta, ...] = (
    timedelta(0),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=30),
)

# (upper bound of the wait in seconds, MMR range, level range); None = no bound.
PAIRING_BANDS: tuple[tuple[int | None, int, int], ...] = (
    (45, 100, 3),
    (90, 175, 5),
    (150, 275, 8),
    (240, 400, 12),
    (None, 500, 15),
)
PAIRING_HARD_LEVEL_CAP = 15

DECAY_MIN_RENOME = 2400
DECAY_FLOOR = 2399
DECAY_AMOUNT = 50
DECAY_INACTIVITY = timedelta(days=7)

ELO_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (3000, "Regente"),
    (2800, "Arauto I"),
    (2600, "Arauto II"),
    (2400, "Arauto III"),
    (2200, "Ascendente I"),
    (2000, "Ascendente II"),
    (1800, "Ascendente III"),
    (1600, "Forjado I"),
    (1400, "Forjado II"),
    (1200, "Forjado III"),
    (1000, "Chama I"),
    (800, "Chama II"),
    (600, "Chama III"),
    (400, "Brasa I"),
    (200, "Brasa II"),
    (0, "Brasa III"),
)


def elo_for(renome: int) -> str:
    for floor, name in ELO_THRESHOLDS:
        if renome >= floor:
            return name
    return ELO_THRESHOLDS[-1][1]


def is_arena_window_open(now: datetime) -> bool:
    """The closing minute already belongs to the closed side of the window."""
    local = now.astimezone(ARENA_TIMEZONE).time()
    return any(start <= local < end for start, end in ARENA_WINDOWS)


def expected_score(rating: int, opponent: int) -> Decimal:
    exponent = Decimal(opponent - rating) / Decimal(400)
    return Decimal(1) / (Decimal(1) + Decimal(10) ** exponent)


def _rating_delta(k: int, rating: int, opponent: int, score: Decimal) -> int:
    change = Decimal(k) * (score - expected_score(rating, opponent))
    return int(change.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def renome_after_match(renome: int, opponent_renome: int, score: Decimal) -> int:
    return max(0, renome + _rating_delta(RENOME_K, renome, opponent_renome, score))


def mmr_k(career_matches: int) -> int:
    return MMR_K_EARLY if career_matches < MMR_EARLY_MATCHES else MMR_K_LATE


def mmr_after_match(mmr: int, opponent_mmr: int, score: Decimal, career_matches: int) -> int:
    return mmr + _rating_delta(mmr_k(career_matches), mmr, opponent_mmr, score)


def placement_renome(wins: int) -> int:
    return PLACEMENT_RENOME[min(max(0, wins), PLACEMENT_MATCHES)]


def dodge_cooldown(dodges_in_window: int) -> timedelta:
    """Recharge for the N-th dodge or no-show inside the 60-minute window."""
    index = min(max(1, dodges_in_window), len(DODGE_COOLDOWNS)) - 1
    return DODGE_COOLDOWNS[index]


@dataclass(frozen=True, slots=True)
class PairingBand:
    mmr: int
    levels: int


def pairing_band(waited_seconds: float) -> PairingBand:
    for upper, mmr, levels in PAIRING_BANDS:
        if upper is None or waited_seconds < upper:
            return PairingBand(mmr, levels)
    raise AssertionError("the last pairing band has no upper bound")


def is_pairing_compatible(
    *,
    waited_seconds: float,
    first_mmr: int,
    first_level: int,
    second_mmr: int,
    second_level: int,
) -> bool:
    """Use the band of whoever has waited longest, so it keeps widening."""
    band = pairing_band(waited_seconds)
    level_gap = abs(first_level - second_level)
    return (
        abs(first_mmr - second_mmr) <= band.mmr
        and level_gap <= band.levels
        and level_gap <= PAIRING_HARD_LEVEL_CAP
    )


def latest_decay_boundary(now: datetime) -> datetime:
    """The most recent Monday 06:00 in the Arena timezone."""
    local = now.astimezone(ARENA_TIMEZONE)
    monday = (local - timedelta(days=local.weekday())).date()
    boundary = datetime.combine(monday, time(6, 0), ARENA_TIMEZONE)
    if local < boundary:
        boundary = datetime.combine(monday - timedelta(days=7), time(6, 0), ARENA_TIMEZONE)
    return boundary


def decayed_renome(renome: int) -> int:
    return max(DECAY_FLOOR, renome - DECAY_AMOUNT)


def soft_reset_renome(renome: int) -> int:
    """§49.14 Crônica reset. Kept unwired until the Crônica system exists."""
    value = Decimal(1000) + Decimal("0.5") * (renome - 1000)
    rounded = int(value.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
    return min(2400, max(400, rounded))
