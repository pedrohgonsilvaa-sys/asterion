"""PowerlevelFactor, XP de inimigo e Legado conforme GDD v1.7.1 (§41, §49.7, §16)."""

from decimal import Decimal as D

import pytest

from asterion.domain.dungeons import dungeon_completion_xp
from asterion.domain.legacy import LEGACY_XP_FACTORS, legacy_xp_factor
from asterion.domain.road import enemy_xp, powerlevel_factor


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        (-3, "1.00"),
        (0, "1.00"),
        (10, "1.00"),
        (11, "0.70"),
        (15, "0.70"),
        (16, "0.45"),
        (20, "0.45"),
        (21, "0.20"),
        (30, "0.20"),
        (31, "0.05"),
        (59, "0.05"),
    ],
)
def test_powerlevel_factor_brackets(gap, expected):
    assert powerlevel_factor(gap) == D(expected)


def test_enemy_xp_category_multipliers_round_10_once():
    assert [enemy_xp(30, c) for c in ("common", "uncommon", "elite", "boss")] == [
        870,
        1180,
        2400,
        5250,
    ]


def test_powerlevel_applies_after_level_factor_and_composes_before_single_round():
    assert enemy_xp(30, "elite", powerlevel_factor=powerlevel_factor(12)) == 1680
    assert enemy_xp(30, "elite", powerlevel_factor=powerlevel_factor(35)) == 120
    assert enemy_xp(
        30, "elite", powerlevel_factor=powerlevel_factor(12), legacy_factor=legacy_xp_factor(2)
    ) == 3370
    # 25% de Masmorra x PowerlevelFactor num único round_10 (sem arredondar intermediário).
    assert enemy_xp(30, "common", powerlevel_factor=D("0.25") * powerlevel_factor(12)) == 150
    assert enemy_xp(30, "common", powerlevel_factor=D("0.25")) == 220


def test_legacy_factors_only_xp_and_vigor_25_percent_is_separate():
    assert [legacy_xp_factor(n) for n in range(6)] == [
        D("1.00"),
        D("1.75"),
        D("2.00"),
        D("2.25"),
        D("2.50"),
        D("2.75"),
    ]
    assert set(LEGACY_XP_FACTORS) == {0, 1, 2, 3, 4, 5}
    with pytest.raises(ValueError):
        legacy_xp_factor(6)
    assert enemy_xp(30, "common", D("0.25"), legacy_factor=legacy_xp_factor(5)) == 600


def test_dungeon_completion_xp_time_normalised_first_clear_plus_60_percent():
    assert dungeon_completion_xp(6, "stable") == 3400
    assert dungeon_completion_xp(6, "stable", first_clear=True) == 5440
    # Ruptura usa referência Nv.60 (sem Nv.61) e eficiência 1,10 x 42,5m.
    rupture = dungeon_completion_xp(60, "rupture")
    assert rupture > dungeon_completion_xp(60, "fractured") > dungeon_completion_xp(60, "stable")
    assert dungeon_completion_xp(60, "rupture", first_clear=True) == pytest.approx(
        rupture * 1.6, abs=10
    )
