"""Pure rules for Eventos Mundiais (GDD v1.6.0 §21, §21.1, §49.15)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from asterion.domain.equipment_stats import (
    EquipmentConfigurationSnapshot,
    EquippedItemSnapshot,
)
from asterion.domain.road import Creature
from asterion.domain.world_events import (
    WORLD_EVENT_CATALOG,
    WorldEventDefinition,
    WorldEventPhase,
    attuned_equipment,
    attuned_level,
    boss_stats,
    contribution_points,
    definition_for_slot,
    is_eligible,
    latest_slot,
    next_slot,
    occurrence_key,
    phase_scale,
    reward_bundle,
    reward_xp,
)

D = Decimal
# Tuesday 2026-11-10, 12:00 in Sao Paulo.
TUESDAY_NOON = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)

BOSS = Creature("t", "Chefe", "boss", "balanced", 1, 60, 0, ("s",), (("s", "G", D(1), 0, D(0), 0),))


def _definition(event_id: str = "evento") -> WorldEventDefinition:
    phase = WorldEventPhase(BOSS, "")
    return WorldEventDefinition(
        event_id, "Evento", "Terras do Ocaso", 10, (phase, phase, phase), ""
    )


def test_the_catalog_ships_empty_because_the_source_names_no_event():
    assert WORLD_EVENT_CATALOG == ()
    assert definition_for_slot((), TUESDAY_NOON) is None


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (TUESDAY_NOON, TUESDAY_NOON),
        (TUESDAY_NOON + timedelta(hours=7, minutes=59), TUESDAY_NOON),
        (TUESDAY_NOON + timedelta(hours=8), TUESDAY_NOON + timedelta(hours=8)),
        # Wednesday still points back to Tuesday 20:00.
        (TUESDAY_NOON + timedelta(days=1), TUESDAY_NOON + timedelta(hours=8)),
    ],
)
def test_latest_slot_follows_tuesday_thursday_saturday(moment, expected):
    assert latest_slot(moment) == expected


def test_next_slot_is_strictly_after_now():
    assert next_slot(TUESDAY_NOON) == TUESDAY_NOON + timedelta(hours=8)
    assert next_slot(TUESDAY_NOON + timedelta(hours=8)) == TUESDAY_NOON + timedelta(days=2)


def test_occurrence_key_is_stable_for_the_same_opening():
    slot = latest_slot(TUESDAY_NOON + timedelta(minutes=3))
    assert occurrence_key(slot) == "20261110T1200"


def test_rotation_is_deterministic():
    catalog = (_definition("a"), _definition("b"))
    first = definition_for_slot(catalog, TUESDAY_NOON).event_id
    assert first == definition_for_slot(catalog, TUESDAY_NOON).event_id
    second = definition_for_slot(catalog, TUESDAY_NOON + timedelta(hours=8)).event_id
    assert second != first


def test_a_definition_needs_three_phases():
    with pytest.raises(ValueError):
        WorldEventDefinition("x", "X", "R", 10, (WorldEventPhase(BOSS, ""),), "")


@pytest.mark.parametrize(
    ("participants", "attack"),
    [(0, "1"), (1, "1"), (2, "1.015"), (41, "1.60"), (42, "1.60"), (200, "1.60"), (500, "1.60")],
)
def test_attack_scale_has_the_sixty_percent_cap(participants, attack):
    assert phase_scale(participants).attack == D(attack)


def test_hp_scale_caps_participants_at_200():
    assert phase_scale(1).hp == D(1)
    assert phase_scale(200).hp == phase_scale(900).hp
    assert phase_scale(2).hp == D(2) ** D("0.88")


def test_boss_uses_the_solo_dungeon_base_with_a_single_rounding():
    stats = boss_stats(BOSS, 60, 1)
    assert stats.hp == D(7735)  # 15470/6 x 3.00, rounded once
    assert stats.attack == D(446)  # 2432/6 x 1.10
    assert stats.agility == D(304)


@pytest.mark.parametrize(
    ("phases", "actions", "major", "expected"),
    [
        (2, 8, 0, True),
        (3, 4, 1, True),
        (1, 50, 3, False),
        (2, 7, 0, False),
        (2, 3, 1, False),
        (0, 0, 0, False),
    ],
)
def test_one_hit_and_leaving_is_not_enough(phases, actions, major, expected):
    assert is_eligible(phases, actions, major) is expected


def test_major_contribution_is_worth_four_actions():
    assert contribution_points(3, 2) == 11


def test_reward_follows_the_event_level():
    bundle = reward_bundle(10)
    assert (bundle.crowns, bundle.basics, bundle.fragments) == (100, 2, 1)  # 0.40 x C(10)=250
    assert reward_bundle(60).crowns == 400  # 0.40 x 1000
    assert reward_xp(1000) == 80


@pytest.mark.parametrize(
    ("player", "event", "expected"), [(60, 10, 15), (12, 10, 12), (15, 10, 15), (60, 58, 60)]
)
def test_attunement_level(player, event, expected):
    assert attuned_level(player, event) == expected


def _item(item_id: str, level: int, value: str = "100") -> EquippedItemSnapshot:
    return EquippedItemSnapshot(
        item_id,
        "principal",
        "1H",
        level,
        "epic",
        0,
        (("attack", D(value)),),
        (("hp", D("5")),),
    )


def test_attunement_only_shrinks_flat_parcels_above_the_level():
    equipment = EquipmentConfigurationSnapshot(1, (_item("a", 60), _item("b", 10)))
    result = attuned_equipment(equipment, 15)
    above, below = result.items
    assert above.core[0][1] < D(100)
    assert above.secondaries == equipment.items[0].secondaries
    assert above.rarity == "epic"
    assert below == equipment.items[1]
