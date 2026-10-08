"""Shared rules for campaign boss encounters."""

from decimal import ROUND_HALF_UP, Decimal, localcontext

from asterion.domain.combat_math import PRECISION, CombatStats

D = Decimal

CAMPAIGN_BOSS_HP_SCALE = (D("1.00"), D("1.55"), D("2.10"), D("2.65"))
CAMPAIGN_BOSS_ATTACK_SCALE = (D("1.00"), D("1.04"), D("1.08"), D("1.12"))


def campaign_boss_scaling(group_size: int) -> tuple[Decimal, Decimal]:
    """Return the frozen HP and ATQ factors for a one-to-four person roster."""
    if not 1 <= group_size <= 4:
        raise ValueError("Campaign boss rosters contain one to four characters.")
    return CAMPAIGN_BOSS_HP_SCALE[group_size - 1], CAMPAIGN_BOSS_ATTACK_SCALE[group_size - 1]


def scale_campaign_boss_stats(stats: CombatStats, group_size: int) -> CombatStats:
    """Scale canonical Solo HP/ATQ and close both with global half-up rounding.

    DEF, AGI and percentage-point statistics retain the canonical Solo values.
    A Solo encounter returns the materialized canonical stats byte-for-byte.
    """
    hp_factor, attack_factor = campaign_boss_scaling(group_size)
    if group_size == 1:
        return stats
    with localcontext() as context:
        context.prec = PRECISION
        return CombatStats(
            (stats.hp * hp_factor).quantize(D(1), rounding=ROUND_HALF_UP),
            (stats.attack * attack_factor).quantize(D(1), rounding=ROUND_HALF_UP),
            stats.defense,
            stats.agility,
            stats.per,
            stats.crit,
            stats.evasion,
            stats.block,
        )
