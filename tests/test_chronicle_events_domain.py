"""O Compasso and the Crônica Event schedule (proposal v0.2 §0.3.8, §8, §11.5)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from asterion.domain.chronicle import calendar_for
from asterion.domain.chronicle_content import CONFINS, OCASO
from asterion.domain.chronicle_events import (
    ADD_KEY,
    ALL_DEFINITIONS,
    DEFINITIONS,
    OBJECTIVE_FAMILY,
    RESSONANCIA,
    RESSONANCIA_PLENA,
    configure_compasso,
    definitions_for_slot,
    enemy_specs,
    family_for_slot,
    next_chronicle_slot,
    next_occurrence,
)
from asterion.domain.road import (
    CR01_O_COMPASSO,
    CREATURE_CATALOG,
    CreatureCombatantSpec,
    create_creature_party_combat,
)
from asterion.domain.world_events import EVENT_TIMEZONE, occurrence_key

D = Decimal
CAL = calendar_for(date(2026, 12, 1))  # Tuesday


def _slot(day: int, hour: int = 12) -> datetime:
    return datetime.combine(CAL.day1 + timedelta(days=day - 1), datetime.min.time()).replace(
        hour=hour, tzinfo=EVENT_TIMEZONE
    )


def test_every_crônica_slot_runs_six_versions_and_plena_from_day_43():
    assert family_for_slot(CAL, _slot(1) - timedelta(days=7)) is None
    assert family_for_slot(CAL, _slot(1)) == RESSONANCIA
    assert family_for_slot(CAL, _slot(38, 20)) == RESSONANCIA
    assert family_for_slot(CAL, _slot(43)) == RESSONANCIA_PLENA
    assert family_for_slot(CAL, CAL.end_at) is None
    versions = definitions_for_slot(CAL, _slot(3))
    assert [(item.region, item.reference_level) for item in versions] == [
        (OCASO, 10),
        ("Vales dos Enforcados", 20),
        ("Planícies de Nareth", 30),
        ("Várzeas Carmesins", 40),
        ("Altos Cinéreos", 50),
        (CONFINS, 60),
    ]
    assert all(item.attuned and item.family == RESSONANCIA for item in versions)


def test_versions_have_distinct_keys_that_fit_the_columns():
    keys = {occurrence_key(_slot(1), item.version) for item in ALL_DEFINITIONS}
    assert len(keys) == len(ALL_DEFINITIONS) == 12
    assert all(len(key) <= 32 for key in keys)
    assert all(len(item.event_id) <= 64 for item in ALL_DEFINITIONS)
    assert occurrence_key(_slot(1)) not in keys  # normal Events keep their key


def test_event_objectives_accept_their_own_event():
    assert OBJECTIVE_FAMILY == {
        "cap_04_obj_03": RESSONANCIA,
        "cap_07_obj_04": RESSONANCIA_PLENA,
        "cap_08_obj_03": RESSONANCIA_PLENA,
    }


def test_next_occurrence_is_live_during_the_entry_window():
    live = next_occurrence(CAL, RESSONANCIA, _slot(22) + timedelta(minutes=10))
    assert live is not None and live.live and live.at == _slot(22)
    after = next_occurrence(CAL, RESSONANCIA, _slot(22) + timedelta(minutes=20))
    assert after is not None and not after.live and after.at == _slot(22, 20)
    # Ressonância stops when the Plena starts, so cap_04_obj_03 ends at D43.
    assert next_occurrence(CAL, RESSONANCIA, _slot(41, 21)) is None
    plena = next_occurrence(CAL, RESSONANCIA_PLENA, _slot(1))
    assert plena is not None and plena.at == _slot(43)
    assert next_occurrence(CAL, RESSONANCIA_PLENA, CAL.end_at) is None
    before = next_chronicle_slot(CAL, _slot(1) - timedelta(days=10))
    assert before == _slot(1)
    assert next_chronicle_slot(CAL, CAL.end_at) is None


def test_compasso_kit_follows_the_proposal():
    assert CR01_O_COMPASSO in CREATURE_CATALOG
    assert (CR01_O_COMPASSO.category, CR01_O_COMPASSO.archetype) == ("boss", "balanced")
    kit = {item[0]: item for item in CR01_O_COMPASSO.actions}
    assert kit["batida"][2] == D("1.00")
    assert kit["onda_de_compasso"][2:4] == (D("0.75"), 0) and kit["onda_de_compasso"][9] == 3
    assert kit["onda_de_compasso"][15] == "all_opponents"
    assert kit["contratempo"][2] == D("0.95") and kit["contratempo"][4:6] == (D("0.10"), 2)
    assert kit["batida_plena"][2] == D("1.10") and kit["batida_plena"][8:10] == (True, 4)
    assert kit["ressonancia"][13] == 2 and kit["ressonancia"][18] == 1
    assert kit["ressonancia"][22] == D("0.06")
    assert CR01_O_COMPASSO.ai_priority == (
        "ressonancia",
        "batida_plena",
        "onda_de_compasso",
        "contratempo",
        "batida",
    )


def _combat(family: str, phase: int, *, resonance: bool = True):
    definition = DEFINITIONS[family][0]
    base = CreatureCombatantSpec(CR01_O_COMPASSO, definition.reference_level, "enemy")
    return create_creature_party_combat(
        uuid4(),
        "Ana",
        "sentinela",
        "remanescente",
        D("100"),
        enemy_specs(definition, phase, base),
        player_level=10,
        configure_combat=lambda state: configure_compasso(state, phase, resonance=resonance),
    )


def _gates(combat) -> dict[str, tuple[str, ...]]:
    """Base action id -> phase gate (multi-enemy combats prefix keys with ``eN_``)."""
    return {
        re.sub(r"^e\d+_", "", key): action.phase_ids for key, action in combat.enemy_actions.items()
    }


def test_phase_gates_and_the_once_per_participant_resonance():
    first = _combat(RESSONANCIA, 1)
    assert first.phase_id == "phase_i"
    gates = _gates(first)
    assert gates["onda_de_compasso"] == gates["batida_plena"] == ("phase_ii", "phase_iii")
    assert gates["ressonancia"] == ("phase_iii",)
    assert gates["batida"] == gates["contratempo"] == ()
    contratempo = next(
        action for key, action in first.enemy_actions.items() if key.endswith("contratempo")
    )
    assert contratempo.skip_if_target_effect_active == "cr01.contratempo"
    assert _combat(RESSONANCIA, 3).phase_id == "phase_iii"
    spent = _combat(RESSONANCIA, 3, resonance=False)
    assert _gates(spent)["ressonancia"] == ("cr01.compasso.spent",)


def test_only_the_plena_phase_two_has_the_repetidor():
    assert ADD_KEY not in _combat(RESSONANCIA, 2).fighters
    assert ADD_KEY not in _combat(RESSONANCIA_PLENA, 1).fighters
    plena = _combat(RESSONANCIA_PLENA, 2)
    add = plena.fighters[ADD_KEY]
    assert add.name == "Repetidor"
    reference = create_creature_party_combat(
        uuid4(),
        "Ana",
        "sentinela",
        "remanescente",
        D("100"),
        (
            CreatureCombatantSpec(
                next(
                    item
                    for item in CREATURE_CATALOG
                    if item.creature_id == "creature.cr01.repetidor"
                ),
                10,
                "enemy",
            ),
        ),
        player_level=10,
    )
    assert add.stats.hp == reference.fighters["enemy"].stats.hp * D("0.30")


def test_versions_screen_offers_one_button_per_open_version():
    from asterion.application.world_events import WorldEventHubView, WorldEventVersion
    from asterion.bot.world_event_ui import render_world_event

    view = WorldEventHubView(
        None,
        None,
        versions=(
            WorldEventVersion(uuid4(), "Ressonância", OCASO, 10, 3),
            WorldEventVersion(uuid4(), "Ressonância", "Vales dos Enforcados", 20, 0),
        ),
        seconds_to_start=120,
    )
    screen = render_world_event(view)
    assert "Ressonância" in screen.text and "120s" in screen.text
    entries = [
        row[0].callback_data
        for row in screen.keyboard.inline_keyboard
        if row[0].callback_data.startswith("wev:in:")
    ]
    assert len(entries) == 2


def test_chapter_line_tells_when_and_where():
    from asterion.application.chronicle_activities import ActionView
    from asterion.bot.chronicle_ui import _action_line
    from asterion.domain.chronicle import OBJECTIVES_BY_ID

    objective = OBJECTIVES_BY_ID["cap_04_obj_03"]
    upcoming = ActionView(objective, OCASO, False, event_at=_slot(24, 20))
    assert _action_line(upcoming) == (
        "📍 Ressonância · Quinta 24/12 às 20:00 · Eventos Mundiais, versão Terras do Ocaso"
    )
    live = ActionView(objective, OCASO, False, event_at=_slot(22), event_live=True)
    assert "acontecendo agora, entrada até 12:15" in _action_line(live)
