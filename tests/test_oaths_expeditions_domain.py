"""Pure rules of the Juramento and the Expedição (GDD v1.6.0 §22, §49.15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from asterion.domain import expeditions as exp
from asterion.domain import oaths
from asterion.domain.engagement import Bundle
from asterion.domain.road import Creature

D = Decimal
FRIDAY_OPENING = datetime(2026, 11, 13, 21, 0, tzinfo=UTC)
MONDAY_START = datetime(2026, 11, 16, 21, 0, tzinfo=UTC)


def _creature(category: str) -> Creature:
    return Creature(
        f"teste_{category}",
        category,
        category,
        "balanced",
        1,
        60,
        0,
        ("g",),
        (("g", "Golpe", D("1.00"), 0, D(0), 0),),
    )


def test_cycle_opens_on_friday_at_18_in_the_server_timezone():
    assert oaths.latest_opening(FRIDAY_OPENING) == FRIDAY_OPENING
    just_before = FRIDAY_OPENING - timedelta(seconds=1)
    assert oaths.latest_opening(just_before) == FRIDAY_OPENING - timedelta(days=7)
    assert oaths.next_opening(FRIDAY_OPENING) == FRIDAY_OPENING + timedelta(days=7)
    assert oaths.WINDOW == timedelta(hours=48) and oaths.GRACE == timedelta(minutes=30)


@pytest.mark.parametrize(
    ("contribution", "tier"),
    [(0, 0), (119, 0), (120, 1), (299, 1), (300, 2), (540, 3), (779, 3), (780, 4), (9999, 4)],
)
def test_collective_tiers(contribution, tier):
    assert oaths.tier_for(contribution) == tier


def test_treasury_and_milestones_match_section_49_15():
    assert [oaths.treasury_reward(tier) for tier in (0, 1, 2, 3, 4)] == [
        0,
        2_000,
        4_000,
        7_000,
        10_000,
    ]
    assert oaths.stage_milestones(1) == (("stage_1", 10),)
    assert oaths.stage_milestones(3) == (("stage_3", 20), ("conclusion", 15))
    total = sum(points for stage in (1, 2, 3) for _, points in oaths.stage_milestones(stage))
    assert total == 60
    assert not oaths.is_eligible(59) and oaths.is_eligible(60)


@pytest.mark.parametrize(
    ("tier", "bundle", "catalysts"),
    [
        (1, Bundle(crowns=500, basics=4, fragments=0), 0),
        (2, Bundle(crowns=750, basics=6, fragments=1), 0),
        (3, Bundle(crowns=1_000, basics=8, fragments=2), 1),
        (4, Bundle(crowns=1_250, basics=10, fragments=3), 1),
    ],
)
def test_individual_oath_rewards_at_level_60(tier, bundle, catalysts):
    assert oaths.reward_bundle(60, tier) == bundle
    assert oaths.reward_catalysts(tier) == catalysts


def test_group_scale_uses_the_dungeon_formula():
    scales = [oaths.group_scale(size) for size in (1, 2, 3, 4)]
    assert [scale.hp for scale in scales] == [D("1"), D("1.78"), D("2.56"), D("3.34")]
    assert [scale.attack for scale in scales] == [D("1"), D("1.07"), D("1.14"), D("1.21")]
    with pytest.raises(ValueError):
        oaths.group_scale(5)


def test_boss_engine_factor_reaches_the_dungeon_base():
    factors = oaths.engine_multipliers(_creature("boss"), 2)
    assert factors.hp == D("3.00") / D("2.20") * D("1.78")
    assert oaths.engine_multipliers(_creature("elite"), 1).hp == D(1)


def test_enemy_level_is_the_group_average():
    assert oaths.enemy_level((10, 20)) == 15
    assert oaths.enemy_level((10, 11)) == 11
    assert oaths.enemy_level((30,)) == 30


def test_trial_requires_elite_elite_boss():
    elite = oaths.OathEncounter(_creature("elite"), "x")
    boss = oaths.OathEncounter(_creature("boss"), "x")
    oaths.OathTrialDefinition("t", "T", (elite, elite, boss), "fim")
    with pytest.raises(ValueError):
        oaths.OathTrialDefinition("t", "T", (elite, boss, boss), "fim")
    with pytest.raises(ValueError):
        oaths.OathTrialDefinition("t", "T", (elite, boss), "fim")


@pytest.mark.parametrize(
    ("level", "region"),
    [(1, "Terras do Ocaso"), (11, "Vales dos Enforcados"), (60, "Confins do Véu")],
)
def test_material_region_follows_the_character_level(level, region):
    assert oaths.region_for_level(level) == region


def test_catalogs_are_empty_until_the_author_defines_content():
    assert oaths.OATH_TRIAL_CATALOG == ()
    assert exp.EXPEDITION_ROUTE_CATALOG == ()
    assert oaths.definition_for_opening((), FRIDAY_OPENING) is None
    assert exp.route_for_start((), MONDAY_START) is None


def test_expedition_clock():
    assert exp.next_start(MONDAY_START - timedelta(seconds=1)) == MONDAY_START
    assert exp.next_start(MONDAY_START) == MONDAY_START + timedelta(days=7)
    assert exp.stage_at(MONDAY_START - timedelta(seconds=1), MONDAY_START) == 1
    assert exp.stage_at(MONDAY_START, MONDAY_START - timedelta(seconds=1)) == 0
    assert exp.stage_at(MONDAY_START, MONDAY_START) == 1
    assert exp.stage_at(MONDAY_START, MONDAY_START + timedelta(hours=24)) == 2
    assert exp.stage_at(MONDAY_START, MONDAY_START + timedelta(hours=72)) == 4


@pytest.mark.parametrize(
    ("score", "result"),
    [
        (0, exp.ExpeditionResult.FAILED),
        (99, exp.ExpeditionResult.FAILED),
        (100, exp.ExpeditionResult.COMPLETED),
        (179, exp.ExpeditionResult.COMPLETED),
        (180, exp.ExpeditionResult.DEEP),
        (239, exp.ExpeditionResult.DEEP),
        (240, exp.ExpeditionResult.EXCEPTIONAL),
        (300, exp.ExpeditionResult.EXCEPTIONAL),
    ],
)
def test_expedition_score_bands(score, result):
    assert exp.result_for(score) == result


def test_expedition_score_is_the_sum_of_stage_averages():
    assert exp.final_score([[100, 100, 100]] * 3) == 300
    assert exp.final_score([[20, 20, 20]] * 3) == 60
    # 58,33 + 20 + 100 is rounded down once, at the end.
    assert exp.final_score([[100, 50, 25], [20, 20, 20], [100, 100, 100]]) == 178


def test_expedition_rewards_match_section_49_15():
    assert exp.reward_bundle(60, exp.ExpeditionResult.FAILED) is None
    assert exp.reward_bundle(60, exp.ExpeditionResult.COMPLETED) == Bundle(500, 3, 0)
    assert exp.reward_bundle(60, exp.ExpeditionResult.DEEP) == Bundle(800, 5, 1)
    assert exp.reward_bundle(60, exp.ExpeditionResult.EXCEPTIONAL) == Bundle(1_250, 8, 3)
    assert [exp.treasury_reward(result) for result in exp.ExpeditionResult] == [
        0,
        1_500,
        3_000,
        5_000,
    ]
    assert not exp.is_eligible(1) and exp.is_eligible(2)


def test_stage_needs_one_option_of_each_quality():
    good = exp.ExpeditionOption("a", "A", exp.OptionQuality.FAVORABLE)
    middle = exp.ExpeditionOption("b", "B", exp.OptionQuality.NEUTRAL)
    bad = exp.ExpeditionOption("c", "C", exp.OptionQuality.POOR)
    exp.ExpeditionStage("x", (good, middle, bad))
    with pytest.raises(ValueError):
        exp.ExpeditionStage("x", (good, good, bad))
