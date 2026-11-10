"""Catalog rules of the Crônica activities: coverage, counts and spoiler limits (§0.2)."""

from __future__ import annotations

import pytest

from asterion.domain.chronicle import OBJECTIVES, ObjectiveKind
from asterion.domain.chronicle_content import (
    DESBRAVAR_STEPS,
    NPC_STEPS,
    READING_STEPS,
    REGIONS,
)
from asterion.domain.road import EXPLORATION_PROFILES

_SPOILERS = ("Nó Central", "Âncora Central", "Regência", "Desvelados", "Hemaris", "Avesso")
_FOCUS_ONLY = ("Claustro", "Dara Venn", "Iven Raal", "Talen Orm", "Ilyan Korr", "Sel Ardan")


def _ids(kind: ObjectiveKind) -> set[str]:
    return {item.objective_id for item in OBJECTIVES if item.kind is kind}


def test_every_objective_of_the_three_kinds_has_content():
    assert set(NPC_STEPS) == _ids(ObjectiveKind.NPC)
    assert set(READING_STEPS) == _ids(ObjectiveKind.EVIDENCE)
    assert set(DESBRAVAR_STEPS) == _ids(ObjectiveKind.DESBRAVAR)


@pytest.mark.parametrize(
    ("objective_id", "count"),
    [
        ("cap_01_obj_03", 3),
        ("cap_03_obj_02", 3),
        ("cap_05_obj_02", 4),
        ("cap_07_obj_01", 8),  # 4 Leituras, each confirmed at 2 points
    ],
)
def test_reading_points_match_the_proposal(objective_id, count):
    points = READING_STEPS[objective_id]
    assert len(points) == count == len({item.point_id for item in points})
    chapter = objective_id[4:6]
    assert all(item.point_id.startswith(f"lei_cr01_c{chapter}_") for item in points)


def _safe_texts():
    for step in NPC_STEPS.values():
        yield step.text
        if step.mirror:
            yield step.mirror
    for step in DESBRAVAR_STEPS.values():
        yield step.text
        if step.mirror:
            yield step.mirror
    for points in READING_STEPS.values():
        for point in points:
            yield point.text
            if point.mirror_text:
                yield point.mirror_text


def _mirror_texts():
    for step in (*NPC_STEPS.values(), *DESBRAVAR_STEPS.values()):
        if step.mirror:
            yield step.mirror
    for points in READING_STEPS.values():
        for point in points:
            if point.mirror_text:
                yield point.mirror_text
                yield point.mirror_label or ""


@pytest.mark.parametrize("text", list(_safe_texts()))
def test_base_texts_name_no_layered_term(text):
    assert not any(term in text for term in _SPOILERS)


@pytest.mark.parametrize("text", list(_mirror_texts()))
def test_mirror_texts_name_nothing_of_the_focus_region(text):
    assert not any(term in text for term in _FOCUS_ONLY)


def test_every_resonance_local_has_a_narrative_category():
    for region in REGIONS:
        for local_id in region.locals:
            profile = EXPLORATION_PROFILES[local_id]
            assert "narrative" in dict(profile.category_weights), local_id
