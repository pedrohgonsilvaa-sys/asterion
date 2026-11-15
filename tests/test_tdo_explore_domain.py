from collections import Counter
from datetime import UTC, datetime, timedelta

from asterion.application.progression import level_xp
from asterion.domain.tdo_explore import (
    BOSQUE_LOCATION_ID,
    CAMARA_LOCATION_ID,
    CHARNECA_LOCATION_ID,
    EXPLORE_TARGETS,
    REFUGIO_LOCATION_ID,
    ROAD_LOCATION_ID,
    RUINS_LOCATION_ID,
    discovery_xp,
    explore_cooldown_remaining,
    pick_explore_target,
    remaining_explore_targets,
)

ALL_TARGETS = {t.location_id for t in EXPLORE_TARGETS}


def test_targets_are_the_four_locals_without_road_or_refuge():
    assert ALL_TARGETS == {
        CHARNECA_LOCATION_ID,
        BOSQUE_LOCATION_ID,
        RUINS_LOCATION_ID,
        CAMARA_LOCATION_ID,
    }
    assert ROAD_LOCATION_ID not in ALL_TARGETS
    assert REFUGIO_LOCATION_ID not in ALL_TARGETS
    assert [t.reference_level for t in EXPLORE_TARGETS] == [4, 6, 9, 10]


def test_discovered_locals_are_never_targets_and_road_refuge_are_ignored():
    discovered = {ROAD_LOCATION_ID, REFUGIO_LOCATION_ID, BOSQUE_LOCATION_ID}
    left = {t.location_id for t in remaining_explore_targets(discovered)}
    assert left == ALL_TARGETS - {BOSQUE_LOCATION_ID}
    for i in range(200):
        assert pick_explore_target(f"s{i}", discovered).location_id != BOSQUE_LOCATION_ID


def test_four_clicks_reveal_all_four_then_no_target():
    discovered: set[str] = set()
    for i in range(4):
        target = pick_explore_target(f"click{i}", discovered)
        assert target is not None and target.location_id not in discovered
        discovered.add(target.location_id)
    assert discovered == ALL_TARGETS
    assert pick_explore_target("click4", discovered) is None


def test_draw_is_uniform_and_includes_camara():
    counts = Counter(pick_explore_target(f"u{i}", set()).location_id for i in range(4000))
    assert set(counts) == ALL_TARGETS
    for n in counts.values():
        assert 800 < n < 1200  # esperado 1000 (25%)


def test_draw_is_deterministic_per_seed():
    assert pick_explore_target("x", set()) == pick_explore_target("x", set())


def test_discovery_xp_at_cap_matches_spec():
    values = [discovery_xp(t.reference_level, 11, level_xp) for t in EXPLORE_TARGETS]
    assert values == [193, 250, 355, 395]
    assert sum(values) == 1193


def test_discovery_xp_level_one_is_120_per_local():
    values = [discovery_xp(t.reference_level, 1, level_xp) for t in EXPLORE_TARGETS]
    assert values == [120, 120, 120, 120]
    assert sum(values) == 480


def test_discovery_xp_uses_min_of_reference_and_player_level():
    assert discovery_xp(9, 5, level_xp) == discovery_xp(5, 99, level_xp)


def test_cooldown_is_three_seconds():
    now = datetime(2026, 11, 14, tzinfo=UTC)
    assert explore_cooldown_remaining(None, now) == timedelta(0)
    assert explore_cooldown_remaining(now - timedelta(seconds=1), now) == timedelta(seconds=2)
    assert explore_cooldown_remaining(now - timedelta(seconds=3), now) == timedelta(0)
    assert explore_cooldown_remaining(now - timedelta(seconds=10), now) == timedelta(0)
