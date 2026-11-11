"""Códice and Bestiário screens cover the six Regions and keep button keys unique."""

from __future__ import annotations

from collections import Counter

from asterion.application.character_surfaces import BestiaryRecordView, KnowledgeView
from asterion.application.knowledge_catalog import (
    CODEX_ENTRIES,
    CONFINS_REGION_ID,
    CR01_BESTIARY_GROUP,
    CREATURE_PRESENTATION,
)
from asterion.bot.character_surfaces_ui import (
    CODEX_ENTRY_BY_KEY,
    CODEX_ENTRY_KEYS,
    _codex_region_id,
    _region_labels,
    render_bestiary_region,
    render_bestiary_root,
)


def test_codex_button_keys_are_unique_and_fit_a_callback():
    assert not [key for key, count in Counter(CODEX_ENTRY_KEYS.values()).items() if count > 1]
    assert CODEX_ENTRY_BY_KEY[CODEX_ENTRY_KEYS["codex.altos.regiao"]] == "codex.altos.regiao"
    assert CODEX_ENTRY_BY_KEY[CODEX_ENTRY_KEYS["codex.confins.regiao"]] == "codex.confins.regiao"
    assert max(len(f"kb:e:{key}".encode()) for key in CODEX_ENTRY_KEYS.values()) <= 64


def test_every_local_and_creature_has_a_region_screen():
    labels = _region_labels()
    assert len(labels) == 6
    for entry in CODEX_ENTRIES:
        if entry.location_id:
            assert _codex_region_id(entry.location_id) in labels, entry.entry_id
    for presentation in CREATURE_PRESENTATION.values():
        assert presentation.region_id in labels or presentation.region_id == CR01_BESTIARY_GROUP


def _record(creature_id: str, name: str) -> BestiaryRecordView:
    return BestiaryRecordView(creature_id, name, "observed", "Observado", (), (), (), ())


def test_bestiary_lists_confins_in_region_order_and_the_cronica_last():
    view = KnowledgeView(
        "sentinela",
        (),
        (
            _record("cao_nevoa", "Cão de Névoa"),
            _record("creature.cr01.repetidor", "Repetidor"),
        ),
        (),
        frozenset(),
    )
    root = render_bestiary_root(view).text
    assert root.index("Confins do Véu") < root.index("Crônica I")
    assert "Cão de Névoa" in render_bestiary_region(view, CONFINS_REGION_ID).text
