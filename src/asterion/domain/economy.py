"""Shared economic units used by character services."""

from decimal import ROUND_HALF_EVEN, Decimal

D = Decimal


def round_10(value: Decimal | int) -> int:
    return int((D(value) / D(10)).quantize(D(1), rounding=ROUND_HALF_EVEN) * 10)


def crowns_per_level(level: int) -> int:
    if not 1 <= level <= 60:
        raise ValueError("Character level must be between 1 and 60.")
    return round_10(D(100) + D(15) * level)


def path_switch_cost(level: int) -> int:
    return round_10(D(crowns_per_level(level)) * D("1.5"))
