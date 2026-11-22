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


MAX_LEGACY_LEVEL = 5
LEGACY_ASCENSION_LEVEL = 60

# Coroas paid to ascend INTO each Legado rank (author decision, Legado I–V).
LEGACY_ASCENSION_COSTS: dict[int, int] = {
    1: 0,
    2: 10_000,
    3: 20_000,
    4: 40_000,
    5: 80_000,
}


def legacy_ascension_cost(current_legacy_level: int) -> int:
    """Coroas to ascend from ``current_legacy_level`` to the next rank.

    Ranks above the maximum have no next step, so they cost nothing here; the
    caller must reject them on the rank check.
    """
    return LEGACY_ASCENSION_COSTS.get(current_legacy_level + 1, 0)


def legacy_xp_factor(legacy_level: int) -> Decimal:
    """Return the canonical XP factor for a persisted Legacy rank (0 through 5)."""
    if isinstance(legacy_level, bool) or not isinstance(legacy_level, int):
        raise ValueError("Legacy level must be an integer from 0 through 5.")
    try:
        return LEGACY_XP_FACTORS[legacy_level]
    except KeyError as error:
        raise ValueError("Legacy level must be an integer from 0 through 5.") from error
