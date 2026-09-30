"""Pure Baseline v1.0 arithmetic. No economy/XP conversion is defined here."""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, localcontext
from hashlib import sha256
from uuid import UUID

from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.paths import PATH_DEFINITIONS

D = Decimal
ZERO = D(0)
PRECISION = 50
STAT_NAMES = ("hp", "attack", "defense", "agility")
COMBAT_STAT_NAMES = STAT_NAMES + ("per", "crit", "evasion", "block")
CLASS_60 = {
    "sentinela": (2808, 368, 324, 276),
    "errante": (2470, 424, 282, 330),
    "vigia": (2522, 420, 288, 321),
    "tecelao": (2418, 436, 273, 300),
    "oraculo": (2574, 400, 291, 309),
    "luminar": (2678, 384, 309, 288),
}


@dataclass(frozen=True)
class CombatStats:
    hp: Decimal
    attack: Decimal
    defense: Decimal
    agility: Decimal
    # Secondary combat attributes are percentage points, not fractions.
    per: Decimal = ZERO
    crit: Decimal = D(5)
    evasion: Decimal = ZERO
    block: Decimal = ZERO

    def values(self) -> tuple[Decimal, ...]:
        return self.hp, self.attack, self.defense, self.agility

    def combat_values(self) -> tuple[Decimal, ...]:
        return self.values() + (self.per, self.crit, self.evasion, self.block)


@dataclass(frozen=True)
class StatMultipliers:
    """Multiplicative enemy vectors; neutral factors are 1, unlike CombatStats."""

    hp: Decimal
    attack: Decimal
    defense: Decimal
    agility: Decimal

    def values(self) -> tuple[Decimal, ...]:
        return self.hp, self.attack, self.defense, self.agility


# Kept as a source-compatible domain name for existing callers and snapshots.
Stats = CombatStats


LEGACY_COMBAT_RULESET = "gdd-1.4.3-baseline-1.0"
CURRENT_COMBAT_RULESET = "gdd-1.4.6-baseline-1.0"
SUPPORTED_LEGACY_COMBAT_RULESETS = frozenset(
    {LEGACY_COMBAT_RULESET, "gdd-1.4.2-baseline-1.0"}
)


def growth(level: int) -> Decimal:
    if not 1 <= level <= 60:
        raise ValueError("The class curve is specified for levels 1 through 60")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return D(4) ** (D(level - 60) / D(59))


def class_stats(character_class: str, level: int) -> CombatStats:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return CombatStats(
            *(
                D(value * growth(level)).quantize(D(1), rounding=ROUND_HALF_UP)
                for value in CLASS_60[character_class]
            )
        )


def racial_stats(stats: CombatStats, race: str) -> CombatStats:
    # No new global racial rounding rule: composition retains fractional values.
    with localcontext() as ctx:
        ctx.prec = PRECISION
        if race == "remanescente":
            return CombatStats(
                *(value * D("1.015") for value in stats.values()),
                stats.per,
                stats.crit,
                stats.evasion,
                stats.block,
            )
        if race == "alvorano":
            return CombatStats(
                stats.hp,
                stats.attack,
                stats.defense,
                stats.agility * D("1.05"),
                stats.per,
                stats.crit,
                stats.evasion,
                stats.block,
            )
        return stats


def resolve_combat_stats(
    character_class: str,
    level: int,
    race: str,
    equipment: EquipmentStatContribution | None = None,
    selected_path: str | None = None,
) -> CombatStats:
    """Resolve class, materialized equipment bonuses, then final static race modifiers."""
    base = class_stats(character_class, level)
    path = PATH_DEFINITIONS.get(selected_path or "")
    if path is not None:
        if path.character_class != character_class:
            raise ValueError("Selected Path does not belong to the character Class.")
        # Inherent Path percentages affect the class portion only and do not add
        # a new intermediate rounding step before flat equipment is composed.
        base = CombatStats(
            base.hp * (D(1) + path.hp),
            base.attack * (D(1) + path.attack),
            base.defense * (D(1) + path.defense),
            base.agility * (D(1) + path.agility),
            base.per,
            base.crit,
            base.evasion,
            base.block,
        )
    equipment = equipment or EquipmentStatContribution()
    with localcontext() as ctx:
        ctx.prec = PRECISION
        composed = CombatStats(
            *(
                left + right
                for left, right in zip(
                    base.combat_values(), equipment.values(), strict=True
                )
            )
        )
    return racial_stats(composed, race)


def neutral_stats(level: int) -> CombatStats:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        # Exact rational representations of the repeating decimals in the source.
        return CombatStats(
            *(
                value * growth(level)
                for value in (
                    D(7735) / D(3),
                    D(1216) / D(3),
                    D("294.5"),
                    D(304),
                )
            )
        )


def enemy_stats(level: int, *multipliers: StatMultipliers) -> CombatStats:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        values = list(neutral_stats(level).values())
        for multiplier in multipliers:
            values = [
                value * factor
                for value, factor in zip(
                    values,
                    multiplier.values(),
                    strict=True,
                )
            ]
        return CombatStats(*(value.quantize(D(1), rounding=ROUND_HALF_UP) for value in values))


def effective_defense(defense: Decimal, per: Decimal = ZERO) -> Decimal:
    """Apply attacker PER in percentage points before natural DEF mitigation."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        penetration = min(D(30), max(ZERO, per))
        return max(ZERO, defense) * (D(1) - penetration / D(100))


def combine_active_mitigation(*reductions: Decimal) -> Decimal:
    """Combine active reductions multiplicatively, capped separately from DEF."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        remaining = D(1)
        for reduction in reductions:
            remaining *= D(1) - min(D(1), max(ZERO, reduction))
        return min(D("0.65"), max(ZERO, D(1) - remaining))


def chance_from_percentage_points(value: Decimal) -> Decimal:
    """Convert a percentage-point chance to a probability in [0, 1]."""
    return min(D(100), max(ZERO, value)) / D(100)


def defense_reduction(defense: Decimal, attacker_level: int) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return defense / (defense + D(100 + 5 * attacker_level))


def direct_damage(
    attack: Decimal,
    coefficient: Decimal,
    defense: Decimal,
    attacker_level: int,
    *,
    critical: bool = False,
    mitigation: Decimal = ZERO,
    penetration: Decimal = ZERO,
    explicitly_zero: bool = False,
) -> int:
    if explicitly_zero:
        return 0
    with localcontext() as ctx:
        ctx.prec = PRECISION
        raw = attack * coefficient
        if critical:
            raw *= D("1.5")
        effective = effective_defense(defense, penetration)
        active_mitigation = min(D("0.65"), max(ZERO, mitigation))
        value = (
            raw
            * (D(1) - defense_reduction(effective, attacker_level))
            * (D(1) - active_mitigation)
        )
        return max(1, int(value.to_integral_value(rounding=ROUND_FLOOR)))


def dot_damage(
    snapshots: list[Decimal] | tuple[Decimal, ...],
    coefficient: Decimal,
    defense: Decimal,
    attacker_level: int,
    *,
    penetration: Decimal = ZERO,
) -> int:
    """Official DoT tick: ATQ snapshot(s), no crit, using 50% effective normal DEF."""
    if not snapshots:
        return 0
    with localcontext() as ctx:
        ctx.prec = PRECISION
        raw = sum((snapshot * coefficient for snapshot in snapshots), ZERO)
        effective = effective_defense(defense, penetration)
        value = raw * (D(1) - defense_reduction(effective * D("0.50"), attacker_level))
        return max(1, int(value.to_integral_value(rounding=ROUND_FLOOR)))


def stable_priority(combat_id: UUID, fighter_id: str) -> int:
    return int.from_bytes(sha256(f"{combat_id}:initiative:{fighter_id}".encode()).digest())


@dataclass
class CombatRng:
    combat_id: UUID
    cursor: int = 0

    def chance(self, probability: Decimal, purpose: str) -> bool:
        """Counter-based SHA-256 draws, with rejection to avoid modulo bias."""
        if not D(0) <= probability <= D(1):
            raise ValueError("Invalid probability")
        numerator, denominator = probability.as_integer_ratio()
        limit = (2**256 // denominator) * denominator
        attempt = 0
        while True:
            seed = f"{self.combat_id}:{self.cursor}:{purpose}:{attempt}"
            value = int.from_bytes(sha256(seed.encode()).digest())
            if value < limit:
                self.cursor += 1
                return value % denominator < numerator
            attempt += 1
