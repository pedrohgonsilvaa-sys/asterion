"""Canonical Legacy progression constants and XP multiplier."""

from decimal import Decimal

LEGACY_XP_FACTORS: dict[int, Decimal] = {
    0: Decimal("1.00"),
    1: Decimal("1.75"),
    2: Decimal("2.00"),
    3: Decimal("2.25"),
    4: Decimal("2.50"),
    5: Decimal("2.75"),
}


def legacy_xp_factor(legacy_level: int) -> Decimal:
    """Return the canonical XP factor for a persisted Legacy rank (0 through 5)."""
    if isinstance(legacy_level, bool) or not isinstance(legacy_level, int):
        raise ValueError("Legacy level must be an integer from 0 through 5.")
    try:
        return LEGACY_XP_FACTORS[legacy_level]
    except KeyError as error:
        raise ValueError("Legacy level must be an integer from 0 through 5.") from error
