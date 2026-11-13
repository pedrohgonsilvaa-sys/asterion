"""Catálogos de Eventos Públicos e Provações do Juramento (conteúdo de 2026-11-13)."""

from __future__ import annotations

from asterion.domain.engagement import REGION_SUPPLY
from asterion.domain.oaths import OATH_TRIAL_CATALOG
from asterion.domain.world_events import WORLD_EVENT_CATALOG

ELITE_BOSS = ("elite", "elite", "boss")


def _creatures():
    for event in WORLD_EVENT_CATALOG:
        for phase in event.phases:
            yield phase.creature
    for trial in OATH_TRIAL_CATALOG:
        for encounter in trial.encounters:
            yield encounter.creature


def test_six_events_one_per_region_with_unique_ids() -> None:
    assert len(WORLD_EVENT_CATALOG) == 6
    assert [e.region for e in WORLD_EVENT_CATALOG] == list(REGION_SUPPLY)
    assert len({e.event_id for e in WORLD_EVENT_CATALOG}) == 6
    for event in WORLD_EVENT_CATALOG:
        assert event.event_id == event.event_id.lower()
        assert len(event.phases) == 3
        assert all(phase.creature.category == "boss" for phase in event.phases)


def test_attuned_events_are_the_last_three() -> None:
    assert [e.attuned for e in WORLD_EVENT_CATALOG] == [False] * 3 + [True] * 3
    assert [e.reference_level for e in WORLD_EVENT_CATALOG] == [10, 20, 30, 40, 50, 60]


def test_eleven_trials_are_elite_elite_boss() -> None:
    assert len(OATH_TRIAL_CATALOG) == 11
    assert len({t.trial_id for t in OATH_TRIAL_CATALOG}) == 11
    for trial in OATH_TRIAL_CATALOG:
        categories = tuple(e.creature.category for e in trial.encounters)
        assert categories == ELITE_BOSS


def test_creature_ids_are_unique_and_kits_are_valid() -> None:
    creatures = list(_creatures())
    assert len(creatures) == 51
    assert len({c.creature_id for c in creatures}) == 51
    for creature in creatures:
        action_ids = {action[0] for action in creature.actions}
        assert len(action_ids) == len(creature.actions) == 3
        assert set(creature.ai) <= action_ids
        assert set(creature.ai_priority) <= action_ids


def test_every_text_is_filled() -> None:
    for event in WORLD_EVENT_CATALOG:
        assert event.name and event.conclusion_flavor
        assert all(phase.flavor for phase in event.phases)
    for trial in OATH_TRIAL_CATALOG:
        assert trial.name and trial.conclusion_flavor
        assert all(encounter.flavor for encounter in trial.encounters)
