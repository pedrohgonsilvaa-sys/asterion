"""Pure rules of Duelo, Arena da Vigilia and PvP Exhaustion (GDD v1.6.0 13, 14, 49.14)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from asterion.domain.arena import (
    decayed_renome,
    dodge_cooldown,
    elo_for,
    expected_score,
    is_arena_window_open,
    is_pairing_compatible,
    latest_decay_boundary,
    mmr_after_match,
    mmr_k,
    pairing_band,
    placement_renome,
    renome_after_match,
    soft_reset_renome,
)
from asterion.domain.combat import (
    _deal_combat_damage,
    _pvp_adjusted_healing,
    pvp_exhaustion_multiplier,
)
from tests.test_barrier_sources import _combat, _grant


@pytest.mark.parametrize(
    ("renome", "elo"),
    [
        (0, "Brasa III"),
        (199, "Brasa III"),
        (200, "Brasa II"),
        (599, "Brasa I"),
        (600, "Chama III"),
        (1199, "Chama I"),
        (1200, "Forjado III"),
        (1799, "Forjado I"),
        (1800, "Ascendente III"),
        (2399, "Ascendente I"),
        (2400, "Arauto III"),
        (2999, "Arauto I"),
        (3000, "Regente"),
        (4200, "Regente"),
    ],
)
def test_elo_thresholds_follow_section_49_14(renome, elo):
    assert elo_for(renome) == elo


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (14, 59, False),
        (15, 0, True),
        (15, 59, True),
        (16, 0, False),
        (22, 0, True),
        (22, 59, True),
        (23, 0, False),
    ],
)
def test_windows_use_sao_paulo_time(hour, minute, expected):
    assert is_arena_window_open(datetime(2026, 11, 9, hour, minute, tzinfo=UTC)) is expected


def test_renome_uses_elo_formula_and_floor_zero():
    assert expected_score(1000, 1000) == D("0.5")
    assert renome_after_match(1000, 1000, D(1)) == 1020
    assert renome_after_match(1000, 1000, D(0)) == 980
    assert renome_after_match(1000, 1000, D("0.5")) == 1000
    assert renome_after_match(10, 10, D(0)) == 0
    assert renome_after_match(0, 0, D(0)) == 0


def test_mmr_k_changes_after_twenty_career_matches():
    assert mmr_k(19) == 48
    assert mmr_k(20) == 32
    assert mmr_after_match(1500, 1500, D(1), 0) == 1524
    assert mmr_after_match(1500, 1500, D(1), 20) == 1516


def test_placement_table():
    assert [placement_renome(wins) for wins in range(6)] == [400, 600, 800, 1000, 1200, 1400]


def test_dodge_recharge_sequence():
    assert [dodge_cooldown(count) for count in (1, 2, 3, 4, 9)] == [
        timedelta(0),
        timedelta(minutes=5),
        timedelta(minutes=15),
        timedelta(minutes=30),
        timedelta(minutes=30),
    ]


@pytest.mark.parametrize(
    ("waited", "mmr", "levels"),
    [
        (0, 100, 3),
        (44.9, 100, 3),
        (45, 175, 5),
        (90, 275, 8),
        (150, 400, 12),
        (240, 500, 15),
        (9000, 500, 15),
    ],
)
def test_pairing_bands(waited, mmr, levels):
    band = pairing_band(waited)
    assert (band.mmr, band.levels) == (mmr, levels)


def test_pairing_is_widened_by_time_and_capped_at_fifteen_levels():
    pair = {"first_mmr": 1500, "first_level": 30, "second_mmr": 1650, "second_level": 34}
    assert not is_pairing_compatible(waited_seconds=0, **pair)
    assert is_pairing_compatible(waited_seconds=45, **pair)
    far = {"first_mmr": 1500, "first_level": 30, "second_mmr": 1500, "second_level": 46}
    assert not is_pairing_compatible(waited_seconds=9000, **far)


def test_decay_boundary_is_monday_six_in_sao_paulo():
    monday_before = datetime(2026, 11, 9, 8, 59, tzinfo=UTC)
    monday_after = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
    assert latest_decay_boundary(monday_after) == monday_after
    assert latest_decay_boundary(monday_before) == monday_after - timedelta(days=7)


def test_decay_floor_and_soft_reset():
    assert decayed_renome(2600) == 2550
    assert decayed_renome(2420) == 2399
    assert soft_reset_renome(1000) == 1000
    assert soft_reset_renome(3000) == 2000
    assert soft_reset_renome(0) == 500
    assert soft_reset_renome(9000) == 2400


@pytest.mark.parametrize(
    ("round_number", "expected"),
    [
        (1, "1"),
        (19, "1"),
        (20, "0.90"),
        (21, "0.80"),
        (22, "0.70"),
        (23, "0.60"),
        (24, "0.50"),
        (25, "0.35"),
        (40, "0.35"),
    ],
)
def test_exhaustion_table(round_number, expected):
    assert pvp_exhaustion_multiplier(round_number) == D(expected)


def test_round_25_barrier_keeps_35_percent():
    state = _combat(hp=10_000, pvp=True)
    state.round = 25
    assert _grant(state, applier="a", effect="x", value=1000) == D(350)


def test_pvp_healing_is_90_percent_before_exhaustion():
    state = _combat(hp=1000, pvp=True)
    assert _pvp_adjusted_healing(state, D(100)) == D(90)
    state.round = 20
    assert _pvp_adjusted_healing(state, D(100)) == D(81)
    state.round = 25
    assert _pvp_adjusted_healing(state, D(100)) == D(31)


def test_pve_healing_is_untouched():
    state = _combat(hp=1000, pvp=False)
    state.round = 30
    assert _pvp_adjusted_healing(state, D(100)) == D(100)


@pytest.mark.parametrize(("round_number", "expected"), [(25, 900), (26, 890), (28, 870)])
def test_final_damage_grows_from_round_26(round_number, expected):
    state = _combat(hp=1000, pvp=True)
    state.round = round_number
    _deal_combat_damage(state, "player", D(100))
    assert state.fighters["player"].hp == D(expected)


def test_pve_final_damage_never_grows():
    state = _combat(hp=1000, pvp=False)
    state.round = 40
    _deal_combat_damage(state, "player", D(100))
    assert state.fighters["player"].hp == D(900)
