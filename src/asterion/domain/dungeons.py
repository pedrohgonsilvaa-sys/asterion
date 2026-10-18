"""Shared deterministic rules for persistent dungeon runs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256

D = Decimal
CRYPT_FAMILY_ID = "dungeon.tdo.cripta_ocaso"
CRYPT_CONTENT_VERSION = "tdo-1.0.11"
CRYPT_RULESET_VERSION = "dungeon-1.0"
CRYPT_RECIPE_UNLOCK = "recipe.tdo.cripta.relicario_sem_nome"
CRYPT_CORE_ID = "material.tdo.nucleo_cripta_ocaso"
CRYPT_BRAZIER_LABEL = "Braseiro do Silêncio"
BASIC_MATERIALS = (
    "material.tdo.ferro_de_fuligem",
    "material.tdo.couro_escoriado",
    "material.tdo.erva_cinzenta",
    "material.tdo.residuo_ocaso",
)


@dataclass(frozen=True, slots=True)
class DungeonDifficulty:
    key: str
    label: str
    vigor: int
    consumable_limit: int
    brazier_percent: int
    reference_level: int
    duration_minutes: Decimal
    efficiency: Decimal
    crowns_factor: Decimal
    basic_materials: int
    catalysts: int
    cores: int
    fragments: int
    pity_points: int
    equipment_bands: tuple[tuple[int, str], ...]
    rune_chance: int
    rune_rarity_bands: tuple[tuple[int, str], ...]
    recipe_chance: int
    pressure_start: int
    boss_hp_multiplier: Decimal
    boss_attack_multiplier: Decimal


DIFFICULTIES = {
    "stable": DungeonDifficulty(
        "stable",
        "Estável",
        25,
        6,
        70,
        6,
        D(30),
        D(1),
        D("0.80"),
        8,
        2,
        1,
        2,
        1,
        ((2500, "Comum"), (5000, "Raro"), (2200, "Épico"), (280, "Lendário"), (20, "Mítico")),
        20,
        ((7000, "Rara"), (2800, "Épica"), (200, "Lendária")),
        8,
        12,
        D(1),
        D(1),
    ),
    "fractured": DungeonDifficulty(
        "fractured",
        "Fraturada",
        35,
        5,
        40,
        6,
        D(35),
        D("1.05"),
        D("1.20"),
        11,
        3,
        2,
        4,
        2,
        ((1000, "Comum"), (4500, "Raro"), (3800, "Épico"), (650, "Lendário"), (50, "Mítico")),
        35,
        ((5500, "Rara"), (4000, "Épica"), (500, "Lendária")),
        15,
        10,
        D("1.15"),
        D("1.08"),
    ),
    "rupture": DungeonDifficulty(
        "rupture",
        "Ruptura",
        50,
        4,
        20,
        60,
        D("42.5"),
        D("1.10"),
        D("1.80"),
        14,
        4,
        4,
        7,
        4,
        ((0, "Comum"), (2000, "Raro"), (6000, "Épico"), (1900, "Lendário"), (100, "Mítico")),
        50,
        ((3500, "Rara"), (5500, "Épica"), (1000, "Lendária")),
        25,
        8,
        D("1.30"),
        D("1.15"),
    ),
}


def stable_draw(seed: str, purpose: str, modulo: int) -> int:
    if modulo < 1:
        raise ValueError("A deterministic draw requires a positive range.")
    return int.from_bytes(sha256(f"{seed}:{purpose}".encode()).digest()[:8], "big") % modulo


def stable_percent(seed: str, purpose: str) -> bool:
    return stable_draw(seed, purpose, 10_000) < 100


def difficulty_gate(
    *,
    level: int,
    discovered: bool,
    stable_first_clear: bool,
    fractured_first_clear: bool,
    minimum_level: int = 4,
) -> dict[str, str]:
    """Return player-facing eligibility without exposing undiscovered content."""
    if not discovered:
        return {}
    return {
        "stable": "available" if level >= minimum_level else "level",
        "fractured": (
            "level"
            if level < minimum_level
            else "available"
            if stable_first_clear
            else "first_stable"
        ),
        "rupture": (
            "available"
            if level >= 60 and fractured_first_clear
            else "level"
            if level < 60
            else "first_fractured"
        ),
    }


def dungeon_completion_xp(
    reference_level: int, difficulty: str, *, first_clear: bool = False
) -> int:
    profile = DIFFICULTIES[difficulty]
    h = D("0.905903") + D("0.094097") * reference_level
    xp_requirement = D(4000 + 750 * reference_level + 43 * reference_level**2)
    xp_requirement = (xp_requirement / D(100)).quantize(D(1), rounding=ROUND_HALF_EVEN) * D(100)
    xp_per_hour = xp_requirement / h
    raw = xp_per_hour * profile.duration_minutes / D(60) * profile.efficiency
    if first_clear:
        raw *= D("1.60")
    return int((raw / D(10)).quantize(D(1), rounding=ROUND_HALF_EVEN) * 10)


def dungeon_crowns(reference_level: int, difficulty: str) -> int:
    profile = DIFFICULTIES[difficulty]
    base = int(
        ((D(100) + D(15) * reference_level) / D(10)).quantize(D(1), rounding=ROUND_HALF_EVEN) * 10
    )
    return int(
        ((D(base) * profile.crowns_factor) / D(10)).quantize(D(1), rounding=ROUND_HALF_EVEN) * 10
    )


def roll_weighted(seed: str, purpose: str, bands: tuple[tuple[int, str], ...]) -> str:
    draw = stable_draw(seed, purpose, 10_000)
    cursor = 0
    for weight, value in bands:
        cursor += weight
        if draw < cursor:
            return value
    if cursor != 10_000:
        raise ValueError("Dungeon reward weights must total 10000 basis points.")
    return bands[-1][1]


def roll_brazier(seed: str, difficulty: str) -> bool:
    return (
        stable_draw(seed, "brazier.exists", 10_000) < DIFFICULTIES[difficulty].brazier_percent * 100
    )


def rarity_with_pity(
    seed: str,
    difficulty: str,
    legendary_plus_points: int,
    mythic_points: int,
) -> tuple[str, int, int]:
    """Roll one guaranteed reward and settle independent global Dungeon pity."""
    profile = DIFFICULTIES[difficulty]
    rarity = roll_weighted(seed, "equipment.rarity", profile.equipment_bands)
    legendary_progress = legendary_plus_points + profile.pity_points
    mythic_progress = mythic_points + profile.pity_points
    if mythic_progress >= 200:
        return "Mítico", 0, 0
    if rarity == "Mítico":
        return rarity, 0, 0
    if rarity == "Lendário":
        return rarity, 0, mythic_progress
    if legendary_progress >= 24:
        return "Lendário", 0, mythic_progress
    return rarity, legendary_progress, mythic_progress


def material_for_ordinal(
    seed: str, ordinal: int, pool: tuple[str, ...] = BASIC_MATERIALS
) -> str:
    if not pool:
        raise ValueError("Dungeon basic-material pools cannot be empty.")
    return pool[stable_draw(seed, f"material.basic.{ordinal}", len(pool))]


def weighted_material_for_ordinal(
    seed: str,
    ordinal: int,
    pool: tuple[tuple[str, int], ...],
) -> str:
    """Draw one basic material deterministically from a basis-point pool."""
    if not pool or any(weight < 0 for _material_id, weight in pool):
        raise ValueError("Dungeon weighted material pools must be non-empty and non-negative.")
    if sum(weight for _material_id, weight in pool) != 10_000:
        raise ValueError("Dungeon weighted material weights must total 10000 basis points.")
    draw = stable_draw(seed, f"material.basic.{ordinal}", 10_000)
    cursor = 0
    for material_id, weight in pool:
        cursor += weight
        if draw < cursor:
            return material_id
    raise AssertionError("A validated weighted material pool must resolve a draw.")


def rune_grade(reference_level: int) -> int:
    return min(6, max(1, (reference_level - 1) // 10 + 1))


def fragment_material_id(reference_level: int) -> str:
    grade = rune_grade(reference_level)
    roman = ("i", "ii", "iii", "iv", "v", "vi")[grade - 1]
    return f"material.tdo.fragmento_aprimoramento_{roman}"


def catalyst_material_id(reference_level: int) -> str:
    grade = rune_grade(reference_level)
    roman = ("i", "ii", "iii", "iv", "v", "vi")[grade - 1]
    return f"material.tdo.catalisador_elite_{roman}"
