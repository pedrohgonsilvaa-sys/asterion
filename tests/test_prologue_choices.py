"""Documento A: as duas escolhas do Prólogo gravam só memória do personagem."""


import pytest
from sqlalchemy import func, select

from asterion.application.narrative_choices import (
    PROLOGUE_CHOICE_ORDER,
)
from asterion.application.prologue import PrologueService
from asterion.application.world import WorldService
from asterion.bot.world_ui import render_world
from asterion.domain.narrative_choices import (
    ChoiceNode,
    build_node,
    narrative_catalog,
    prologue_catalog,
)
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import (
    Character,
    CharacterNarrativeMemory,
    NarrativeChoiceRecord,
    NpcNarrativeMemory,
    WorldState,
)
from tests.test_prologue_persistence import character, win

EXPECTED = {
    "PRO_choice_aftermath": [
        ("o1", "Examinar primeiro", {"evidence_first", "preserves_records"}),
        ("o2", "Aceitar que ainda não sabe", {"hypothesis_marked", "preserves_contradiction"}),
        ("o3", "Seguir enquanto é possível", {"pragmatic", "risk_accepting"}),
    ],
    "PRO_choice_first_fire": [
        ("o1", "Guardar o que foi visto", {"preserves_records", "evidence_first"}),
        ("o2", "Pensar em quem depende da estrada", {"community_first", "protective"}),
        ("o3", "Não deixar o medo decidir", {"risk_accepting", "questions_authority"}),
    ],
}


def test_prologue_catalog_matches_documento_a():
    catalog = prologue_catalog()
    assert tuple(catalog.nodes) == PROLOGUE_CHOICE_ORDER
    for choice_id, node in catalog.nodes.items():
        assert node.mission_id == "PRO" and node.mission_kind == "prologo"
        assert node.region == "terras_do_ocaso" and node.future_hooks == ()
        got = [(o.option_id, o.label, set(o.character_memory_tags)) for o in node.options]
        assert got == EXPECTED[choice_id]
        assert all(not o.npc_memory_targets and not o.requires for o in node.options)


def test_the_72_mission_nodes_keep_their_strict_validation():
    catalog = narrative_catalog()
    assert len(catalog.nodes) == 72
    assert "PRO" not in {node.mission_id for node in catalog.nodes.values()}
    sample = next(iter(catalog.nodes.values()))

    def raw(**changes):
        data = {
            "choice_id": sample.choice_id,
            "mission_id": sample.mission_id,
            "mission_kind": sample.mission_kind,
            "title": "t",
            "region": "r",
            "step": 1,
            "step_context": "c",
            "question": "q",
            "identity_conditions": [],
            "future_hooks": [
                {
                    "hook_id": h.hook_id,
                    "target": h.target,
                    "knowledge_holders": list(h.knowledge_holders),
                    "summary": h.summary,
                }
                for h in sample.future_hooks
            ],
            "options": [
                {
                    "option_id": o.option_id,
                    "label": o.label,
                    "character_memory_tags": list(o.character_memory_tags),
                    "npc_memory_targets": [
                        {"npc_id": t.npc_id, "tag": t.tag} for t in o.npc_memory_targets
                    ],
                }
                for o in sample.options
            ],
        }
        data.update(changes)
        return data

    assert isinstance(build_node(raw()), ChoiceNode)
    with pytest.raises(ValueError):  # a mission node without hooks is still rejected
        build_node(raw(future_hooks=[]))
    with pytest.raises(ValueError):  # contracts never carry nodes
        build_node(raw(mission_kind="contrato"))


async def _at_first_brazier(database, **kwargs):
    await character(database, **kwargs)
    service = PrologueService(database[1], "ocaso", PROFILE)
    await win(service, await service.enter(1))
    return WorldService(database[1], "ocaso")


async def _economy(database):
    async with database[1]() as session:
        row = await session.scalar(select(Character))
        world = await session.scalar(select(WorldState))
        return (row.xp, row.level, world.region, world.location)


def _callbacks(view):
    return [b.callback_data for row in render_world(view).keyboard.inline_keyboard for b in row]


async def test_old_step_is_retired_and_the_first_brazier_shows_straight_away(database):
    world = await _at_first_brazier(database)
    view = await world.resume(1)
    assert view.kind == "brazier"
    assert _callbacks(view) == ["world:rest"]
    assert "Depois da Cinza" not in render_world(view).text
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(NarrativeChoiceRecord)) == 0


async def test_old_characters_get_neutral_backfill_without_preference(database):
    world = await _at_first_brazier(database)
    await world.rest(1)  # passed the Prologue before the choices existed
    view = await world.resume(1)
    assert view.kind == "menu"
    await world.resume(1)
    async with database[1]() as session:
        records = (await session.scalars(select(NarrativeChoiceRecord))).all()
        assert {(r.choice_id, r.selected_option, r.source) for r in records} == {
            (cid, "neutral_backfill", "neutral_backfill") for cid in PROLOGUE_CHOICE_ORDER
        }
        assert await session.scalar(select(func.count()).select_from(CharacterNarrativeMemory)) == 0
        assert await session.scalar(select(func.count()).select_from(NpcNarrativeMemory)) == 0
