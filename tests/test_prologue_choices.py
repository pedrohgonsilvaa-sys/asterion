"""Documento A: as duas escolhas do Prólogo gravam só memória do personagem."""

import asyncio

import pytest
from sqlalchemy import func, select

from asterion.application.narrative_choices import (
    PROLOGUE_CHOICE_ORDER,
    commit_prologue_choice,
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
    NpcRapport,
    Quest,
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


async def test_flow_screens_and_memory_only(database):
    world = await _at_first_brazier(database)
    before = await _economy(database)
    view = await world.resume(1)
    assert view.prologue_choice.choice_id == "PRO_choice_aftermath"
    assert _callbacks(view) == ["pro:a:o1", "pro:a:o2", "pro:a:o3"]

    view = await world.choose_prologue(1, "PRO_choice_aftermath", "o2")
    assert view.prologue_choice.choice_id == "PRO_choice_first_fire"
    assert _callbacks(view) == ["pro:f:o1", "pro:f:o2", "pro:f:o3"]

    view = await world.choose_prologue(1, "PRO_choice_first_fire", "o3")
    assert view.prologue_choice is None and view.kind == "brazier"
    assert "world:rest" in _callbacks(view)
    async with database[1]() as session:
        tags = set(await session.scalars(select(CharacterNarrativeMemory.tag)))
        assert tags == {
            "hypothesis_marked",
            "preserves_contradiction",
            "risk_accepting",
            "questions_authority",
        }
        assert await session.scalar(select(func.count()).select_from(NpcNarrativeMemory)) == 0
        assert await session.scalar(select(func.count()).select_from(NpcRapport)) == 0
    assert await _economy(database) == before

    menu = await world.rest(1)
    assert menu.kind == "menu"
    async with database[1]() as session:
        assert (await session.scalar(select(Quest))).quest_id == "P1"


async def test_duplicate_concurrent_and_changed_callbacks_keep_the_first_choice(database):
    world = await _at_first_brazier(database)
    await asyncio.gather(
        *(world.choose_prologue(1, "PRO_choice_aftermath", "o1") for _ in range(6))
    )
    await world.choose_prologue(1, "PRO_choice_aftermath", "o3")
    async with database[1]() as session:
        records = (await session.scalars(select(NarrativeChoiceRecord))).all()
        assert [(r.choice_id, r.selected_option, r.source) for r in records] == [
            ("PRO_choice_aftermath", "o1", "player")
        ]
        count = await session.scalar(select(func.count()).select_from(CharacterNarrativeMemory))
        assert count == 2


async def test_out_of_order_unknown_and_wrong_stage_are_rejected(database):
    world = await _at_first_brazier(database)
    view = await world.choose_prologue(1, "PRO_choice_first_fire", "o1")
    assert view.prologue_choice.choice_id == "PRO_choice_aftermath"
    await world.choose_prologue(1, "PRO_choice_aftermath", "o9")
    await world.choose_prologue(1, "P1_choice_nope", "o1")
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(NarrativeChoiceRecord)) == 0
    await world.choose_prologue(1, "PRO_choice_aftermath", "o1")
    await world.choose_prologue(1, "PRO_choice_first_fire", "o1")
    await world.rest(1)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character))
        assert row.stage == "menu:ready"
        again = await commit_prologue_choice(session, row, "PRO_choice_aftermath", "o2")
        assert again is not None and not again.created and again.selected_option == "o1"
        assert await session.scalar(select(func.count()).select_from(NarrativeChoiceRecord)) == 2


@pytest.mark.parametrize("race,klass", [("alvorano", "luminar"), ("velado", "tecelao")])
async def test_race_and_class_never_change_options(database, race, klass):
    world = await _at_first_brazier(database, cls=klass, race=race)
    view = await world.resume(1)
    assert [o for o, _ in view.prologue_choice.options] == ["o1", "o2", "o3"]
    assert [label for _, label in view.prologue_choice.options] == [
        label for _, label, _ in EXPECTED["PRO_choice_aftermath"]
    ]


async def test_old_characters_get_neutral_backfill_without_preference(database):
    world = await _at_first_brazier(database)
    await world.rest(1)  # passed the Prologue before the choices existed
    view = await world.resume(1)
    assert view.kind == "menu" and view.prologue_choice is None
    await world.resume(1)
    async with database[1]() as session:
        records = (await session.scalars(select(NarrativeChoiceRecord))).all()
        assert {(r.choice_id, r.selected_option, r.source) for r in records} == {
            (cid, "neutral_backfill", "neutral_backfill") for cid in PROLOGUE_CHOICE_ORDER
        }
        assert await session.scalar(select(func.count()).select_from(CharacterNarrativeMemory)) == 0
        assert await session.scalar(select(func.count()).select_from(NpcNarrativeMemory)) == 0
