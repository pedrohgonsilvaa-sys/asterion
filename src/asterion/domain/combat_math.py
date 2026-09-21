"""Pure Baseline v1.0 arithmetic. No economy/XP conversion is defined here."""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, localcontext
from hashlib import sha256
from uuid import UUID

D = Decimal
ZERO = D(0)
PRECISION = 50
STAT_NAMES = ("hp", "attack", "defense", "agility")
CLASS_60 = {
    "sentinela": (2808, 368, 324, 276),
    "errante": (2470, 424, 282, 330),
    "vigia": (2522, 420, 288, 321),
    "tecelao": (2418, 436, 273, 300),
    "oraculo": (2574, 400, 291, 309),
    "luminar": (2678, 384, 309, 288),
}


@dataclass(frozen=True)
class Stats:
    hp: Decimal
    attack: Decimal
    defense: Decimal
    agility: Decimal

    def values(self) -> tuple[Decimal, ...]:
        return self.hp, self.attack, self.defense, self.agility


def growth(level: int) -> Decimal:
    if not 1 <= level <= 60:
        raise ValueError("The class curve is specified for levels 1 through 60")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return D(4) ** (D(level - 60) / D(59))


def class_stats(character_class: str, level: int) -> Stats:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return Stats(
            *(
                D(value * growth(level)).quantize(D(1), rounding=ROUND_HALF_UP)
                for value in CLASS_60[character_class]
            )
        )


def racial_stats(stats: Stats, race: str) -> Stats:
    # No new global racial rounding rule: composition retains fractional values.
    with localcontext() as ctx:
        ctx.prec = PRECISION
        if race == "remanescente":
            return Stats(*(value * D("1.015") for value in stats.values()))
        if race == "alvorano":
            return Stats(stats.hp, stats.attack, stats.defense, stats.agility * D("1.05"))
        return stats


def neutral_stats(level: int) -> Stats:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        # Exact rational representations of the repeating decimals in the source.
        return Stats(
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


def enemy_stats(level: int, *multipliers: Stats) -> Stats:
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
        return Stats(*(value.quantize(D(1), rounding=ROUND_HALF_UP) for value in values))


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
    explicitly_zero: bool = False,
) -> int:
    if explicitly_zero:
        return 0
    with localcontext() as ctx:
        ctx.prec = PRECISION
        raw = attack * coefficient
        if critical:
            raw *= D("1.5")
        value = raw * (D(1) - defense_reduction(defense, attacker_level)) * (D(1) - mitigation)
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
