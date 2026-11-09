"""Pure rules of Crônica I and its Trilha (GDD §5, §49.16; proposta v0.2)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from asterion.domain.chronicle import (
    CHAPTER_COMPLETION_POINTS,
    CHAPTERS,
    CHRONICLE_COSMETICS_BY_ID,
    FINAL_PHASE_OBJECTIVES,
    FREE_TRACK,
    MAX_POINTS,
    PREMIUM_TRACK,
    REPEATABLE_MAX,
    TIMEZONE,
    Layer,
    Outcome,
    Phase,
    calendar_for,
    can_conclude,
    claimable,
    daily_cycle,
    elo_reward_tier,
    layers_for,
    milestones_reached,
    objectives_of,
    repeatable_cap,
    required_objectives,
    resolve_main,
    resolve_runoff,
    shuffled_options,
    vote_eligible,
)
from asterion.domain.pvp_flavor import PVP_FLAVOR, pvp_flavor

DAY1 = date(2026, 12, 1)


def _local(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TIMEZONE)


def test_calendar_derives_every_date_from_day1():
    calendar = calendar_for(DAY1)
    assert calendar.starts_at == _local(DAY1, 6)
    assert [calendar.chapter_opens_at(n).date() for n in range(1, 9)] == [
        DAY1 + timedelta(days=7 * k) for k in range(8)
    ]
    assert calendar.vote_opens_at == calendar.chapter_opens_at(8)  # D50
    assert calendar.end_at == _local(DAY1 + timedelta(days=55), 21)  # D56 21:00
    assert calendar.vote_closes_at == calendar.end_at - timedelta(hours=48)
    assert calendar.runoff_closes_at == calendar.vote_closes_at + timedelta(hours=24)
    assert calendar.finalization_at == calendar.end_at + timedelta(hours=2)
    assert calendar.rescue_ends_at == calendar.end_at + timedelta(days=14)


def test_phases_and_cutoff_with_grace():
    calendar = calendar_for(DAY1)
    end = calendar.end_at
    assert calendar.phase(calendar.starts_at - timedelta(seconds=1)) is Phase.SCHEDULED
    assert calendar.phase(calendar.starts_at) is Phase.ACTIVE
    assert calendar.phase(end) is Phase.CLOSING
    assert calendar.phase(calendar.finalization_at) is Phase.RESCUE
    assert calendar.phase(calendar.rescue_ends_at) is Phase.ARCHIVED
    assert not calendar.accepts_progress(calendar.starts_at - timedelta(seconds=1))
    assert calendar.accepts_progress(end - timedelta(seconds=1))
    assert not calendar.accepts_progress(end)
    started = end - timedelta(minutes=5)
    assert calendar.accepts_progress(end + timedelta(hours=1), started)
    assert not calendar.accepts_progress(calendar.finalization_at, started)
    assert not calendar.accepts_progress(end + timedelta(hours=1), end)


def test_chapters_open_every_seven_days_and_stay_open():
    calendar = calendar_for(DAY1)
    assert calendar.chapters_open(calendar.starts_at) == 1
    assert calendar.chapters_open(calendar.chapter_opens_at(4) - timedelta(seconds=1)) == 3
    assert calendar.chapters_open(calendar.end_at) == 8


def test_vote_rounds():
    calendar = calendar_for(DAY1)
    assert calendar.vote_round(calendar.vote_opens_at - timedelta(seconds=1)) is None
    assert calendar.vote_round(calendar.vote_opens_at) == "main"
    assert calendar.vote_round(calendar.vote_closes_at) == "runoff"
    assert calendar.vote_round(calendar.runoff_closes_at) is None


def test_extension_must_keep_the_vote_window():
    with pytest.raises(ValueError):
        calendar_for(DAY1, _local(DAY1 + timedelta(days=50), 21))


def test_daily_cycle_turns_at_six():
    assert daily_cycle(_local(DAY1, 5, 59)) == DAY1 - timedelta(days=1)
    assert daily_cycle(_local(DAY1, 6)) == DAY1


def test_every_chapter_offers_500_unique_points():
    for chapter in CHAPTERS:
        assert sum(item.points for item in objectives_of(chapter.number)) == 250
    total = sum(250 + CHAPTER_COMPLETION_POINTS for _ in CHAPTERS)
    assert total == MAX_POINTS
    assert repeatable_cap(8) == REPEATABLE_MAX == 1200
    assert repeatable_cap(1) == 150
    assert repeatable_cap(0) == 0


def test_final_phase_objectives_and_minimum_levels():
    assert FINAL_PHASE_OBJECTIVES == {
        "cap_07_obj_04",
        "cap_08_obj_01",
        "cap_08_obj_02",
        "cap_08_obj_03",
        "cap_08_obj_04",
    }
    levels = {item.objective_id: item.min_level for item in objectives_of(4) + objectives_of(6)}
    assert levels["cap_04_obj_04"] == 5
    assert levels["cap_06_obj_04"] == 3


def test_conclusion_needs_only_mandatory_objectives():
    required = required_objectives(2)
    assert "cap_02_obj_04" not in required
    assert can_conclude(2, required)
    assert not can_conclude(2, set(required) - {"cap_02_obj_01"})


def test_free_track_matches_the_gdd_economy():
    rewards = FREE_TRACK.values()
    assert sorted(FREE_TRACK) == list(range(2, 41, 2))
    assert sum(item.crowns for item in rewards) == 5000
    assert sum(item.basics for item in rewards) == 30
    assert sum(item.fragments for item in rewards) == 20
    assert sum(item.cosmetic_id is not None for item in rewards) == 5


def test_premium_track_is_cosmetic_only():
    assert sorted(PREMIUM_TRACK) == list(range(4, 41, 4))
    for reward in PREMIUM_TRACK.values():
        assert reward.crowns == reward.basics == reward.fragments == 0
        assert reward.cosmetic_id in CHRONICLE_COSMETICS_BY_ID


def test_claimable_uses_the_same_points_for_both_tracks():
    assert milestones_reached(399) == 3
    assert milestones_reached(9999) == 40
    assert claimable(400, False, ()) == (("free", 2), ("free", 4))
    assert claimable(400, True, [("free", 2)]) == (("free", 4), ("premium", 4))


def test_vote_eligibility_and_tally():
    assert vote_eligible(4, 1)
    assert not vote_eligible(3, 5)
    assert not vote_eligible(8, 0)
    assert resolve_main([Outcome.SELAR, Outcome.SELAR, Outcome.DESTRUIR]).outcome is Outcome.SELAR
    tie = resolve_main([Outcome.SELAR, Outcome.DESTRUIR])
    assert tie.outcome is None and tie.runoff == (Outcome.SELAR, Outcome.DESTRUIR)
    assert resolve_main([]).runoff == (
        Outcome.SELAR,
        Outcome.ESTABILIZAR,
        Outcome.HERDEIROS,
        Outcome.DESTRUIR,
    )
    options = (Outcome.SELAR, Outcome.DESTRUIR)
    assert resolve_runoff([Outcome.DESTRUIR], options) is Outcome.DESTRUIR
    assert resolve_runoff([Outcome.SELAR, Outcome.DESTRUIR], options) is Outcome.EM_ESPERA
    assert resolve_runoff([Outcome.HERDEIROS], options) is Outcome.EM_ESPERA


def test_options_are_shuffled_per_player_but_stable():
    first = shuffled_options(1)
    assert first == shuffled_options(1)
    assert sorted(first) == sorted(shuffled_options(2))
    assert len({shuffled_options(account) for account in range(50)}) > 1


def test_spoiler_layers_follow_the_campaign():
    assert layers_for({"P1", "P6"}) == {Layer.C1}
    assert Layer.C3 in layers_for({"P29"})


def test_elo_reward_tier():
    assert elo_reward_tier(2500, 19) is None
    assert elo_reward_tier(2500, 20) == "Arauto III"
    assert elo_reward_tier(3100, 25) == "Arauto I"
    assert elo_reward_tier(3100, 30) == "Regente"


def test_pvp_flavor_respects_the_micro_combat_hard_limit():
    for modes in PVP_FLAVOR.values():
        for lines in modes.values():
            assert len(lines) == 3
            assert all(len(line) <= 140 for line in lines)
    assert pvp_flavor("arena", "win", "x") == pvp_flavor("arena", "win", "x")
