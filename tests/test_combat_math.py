from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from asterion.domain.combat_math import (
    CombatRng,
    CombatStats,
    StatMultipliers,
    class_stats,
    combine_active_mitigation,
    defense_reduction,
    direct_damage,
    dot_damage,
    effective_defense,
    enemy_stats,
    finalize_primary_stats,
    growth,
    neutral_stats,
    racial_stats,
    resolve_combat_stats,
    stable_priority,
)
from asterion.domain.equipment_stats import EquipmentStatContribution

D = Decimal
COMBAT_ID = UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5")


def test_growth_curve_endpoints_and_midpoint():
    assert growth(1) == D("0.25")
    assert growth(60) == 1
    assert growth(30) < D("0.5") < growth(31)
    with localcontext() as ctx:
        ctx.prec = 50
        assert abs(growth(30) * growth(31) - D("0.25")) < D("1e-48")


@pytest.mark.parametrize("level", [0, 61])
def test_curve_rejects_unspecified_levels(level):
    with pytest.raises(ValueError):
        growth(level)


@pytest.mark.parametrize(
    "cls, expected",
    [
        ("sentinela", (702, 92, 81, 69)),
        ("errante", (618, 106, 71, 83)),
        ("vigia", (631, 105, 72, 80)),
        ("tecelao", (605, 109, 68, 75)),
        ("oraculo", (644, 100, 73, 77)),
        ("luminar", (670, 96, 77, 72)),
    ],
)
def test_official_class_level_one_vectors(cls, expected):
    assert class_stats(cls, 1).values() == expected


def test_k_level_and_enemy_composition_have_no_intermediate_rounding():
    k = neutral_stats(1)
    assert k.defense == D("73.625") and k.agility == 76
    with localcontext() as ctx:
        ctx.prec = 50
        assert abs(k.hp - D(7735) / 12) < D("1e-46")
    # Synthetic multiplier proves K is composed before the one final rounding.
    result = enemy_stats(1, StatMultipliers(D(1), D(1), D("0.5"), D(1)))
    assert result.defense == 37


def test_dog_vector_includes_common_category_without_intermediate_rounding():
    from asterion.domain.prologue import CATEGORY_COMMON, PREDATOR, PROFILE, PROLOGUE_MULTIPLIERS

    assert CATEGORY_COMMON.values() == (D("0.70"), D("0.82"), D("0.90"), D("0.95"))
    assert enemy_stats(1, CATEGORY_COMMON, PREDATOR, PROLOGUE_MULTIPLIERS).values() == (
        244,
        50,
        45,
        56,
    )
    assert PROFILE.enemy.values() == (244, 50, 45, 56)
    assert PROFILE.art_blocked_opportunities == 1


def test_racial_stats_preserve_fractional_composition_before_finalization():
    stats = racial_stats(class_stats("sentinela", 1), "remanescente")
    assert stats.values() == (D("712.530"), D("93.380"), D("82.215"), D("70.035"))
    assert racial_stats(class_stats("errante", 1), "alvorano").agility == D("87.15")


def test_finalizer_rounds_only_primary_stats_half_up_and_applies_floors():
    stats = CombatStats(
        D("10.49"),
        D("20.50"),
        D("30.51"),
        D("40.50"),
        D("1.25"),
        D("5.50"),
        D("0.25"),
        D("0.75"),
    )
    finalized = finalize_primary_stats(stats)
    assert finalized.values() == (D(10), D(21), D(31), D(41))
    assert (finalized.per, finalized.crit, finalized.evasion, finalized.block) == (
        D("1.25"),
        D("5.50"),
        D("0.25"),
        D("0.75"),
    )
    floored = finalize_primary_stats(CombatStats(D("0.49"), D("-0.6"), D("-1"), D("-2")))
    assert floored.values() == (D(1), D(0), D(0), D(0))


@pytest.mark.parametrize(
    "cls", ["sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar"]
)
def test_central_resolver_preserves_level_one_and_level_sixty_class_curves(cls):
    level_one = resolve_combat_stats(cls, 1, "velado")
    level_sixty = resolve_combat_stats(cls, 60, "velado")
    assert level_one.values() == class_stats(cls, 1).values()
    assert level_sixty.values() == class_stats(cls, 60).values()
    assert (level_one.per, level_one.crit, level_one.evasion, level_one.block) == (
        D(0), D(5), D(0), D(0)
    )


def test_central_resolver_rounds_final_static_race_modifiers_once():
    remanescente = resolve_combat_stats("sentinela", 1, "remanescente")
    alvorano = resolve_combat_stats("errante", 1, "alvorano")
    assert remanescente.values() == (D(713), D(93), D(82), D(70))
    assert (remanescente.per, remanescente.crit, remanescente.evasion, remanescente.block) == (
        D(0), D(5), D(0), D(0)
    )
    assert alvorano.agility == D(87)
    assert (alvorano.per, alvorano.crit, alvorano.evasion, alvorano.block) == (
        D(0), D(5), D(0), D(0)
    )


def test_central_resolver_closes_fractional_equipment_components_and_path_stats():
    zero_stage = (D(0),) * 8
    equipment = EquipmentStatContribution(
        hp=D("3.4"),
        attack=D("2.6"),
        defense=D("1.2"),
        agility=D("4.8"),
        per=D("0.25"),
        crit=D("0.50"),
        rune_percent=(D("0.0055"), D("0.0055"), D("0.01"), D("0.01")) + (D(0),) * 4,
        rune_points=zero_stage,
        enchantment_percent=(D("0.0035"), D("0.0035"), D("0.007"), D("0.007")) + (D(0),) * 4,
        enchantment_points=zero_stage,
    )
    stats = resolve_combat_stats(
        "sentinela",
        10,
        "remanescente",
        equipment,
        selected_path="devastador",
    )
    assert all(value == value.to_integral_value() for value in stats.values())
    assert stats.per == D("0.25")
    assert stats.crit == D("5.50")


def test_per_reduces_defense_before_normal_formula_and_caps_at_thirty_points():
    assert effective_defense(D(100), D(30)) == D(70)
    assert effective_defense(D(100), D(60)) == D(70)
    assert effective_defense(D(-100), D(30)) == D(0)
    assert direct_damage(D(100), D(1), D(100), 1, penetration=D(30)) == 60
    assert direct_damage(D(100), D(1), D(100), 1, penetration=D(50)) == 60


def test_dot_uses_half_of_per_adjusted_effective_defense_once():
    assert dot_damage([D(100)], D("0.50"), D(100), 1, penetration=D(30)) == 37
    assert dot_damage([D(100)], D("0.50"), D(100), 1) == 33


def test_active_mitigation_is_multiplicative_and_has_separate_sixty_five_cap():
    assert combine_active_mitigation(D("0.45"), D("0.35")) == D("0.6425")
    assert combine_active_mitigation(D("0.52"), D("0.35")) == D("0.65")


def test_defense_formula_and_single_final_floor():
    assert defense_reduction(D(105), 1) == D("0.5")
    assert direct_damage(D("99.9"), D("1.15"), D(45), 1) == 80
    assert direct_damage(D("99.9"), D("1.15"), D(45), 1, critical=True) == 120
    assert direct_damage(D("0.1"), D(1), D(10000), 1) == 1
    assert direct_damage(D(100), D(1), D(0), 1, explicitly_zero=True) == 0


def test_defender_reductions():
    assert direct_damage(D(100), D(1), D(0), 1, mitigation=D("0.45")) == 55
    assert direct_damage(D(100), D(1), D(0), 1, mitigation=D("0.52")) == 48


def test_rng_reproducible_counter_and_stable_tie_priority():
    rng = CombatRng(COMBAT_ID)
    first = [rng.chance(D("0.05"), "crit") for _ in range(100)]
    replay = CombatRng(COMBAT_ID)
    assert first == [replay.chance(D("0.05"), "crit") for _ in range(100)]
    assert any(first) and not all(first)
    resumed = CombatRng(COMBAT_ID, 50)
    assert first[50:] == [resumed.chance(D("0.05"), "crit") for _ in range(50)]
    assert stable_priority(COMBAT_ID, "player") == stable_priority(COMBAT_ID, "player")
    assert stable_priority(COMBAT_ID, "player") != stable_priority(COMBAT_ID, "enemy")
