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
    PLAYER_SOURCE,
    ChoiceNode,
    CommittedChoice,
    build_node,
    legitimate_reaction,
    narrative_catalog,
    prologue_catalog,
    reaction_lines,
    resolve_hook,
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
        assert node.region == "terras_do_ocaso" and len(node.future_hooks) == 3
        got = [(o.option_id, o.label, set(o.character_memory_tags)) for o in node.options]
        assert got == EXPECTED[choice_id]
        assert all(not o.npc_memory_targets and not o.requires for o in node.options)


HOOKS = {
    "PRO_choice_aftermath->P1": ("o1", "alda"),
    "PRO_choice_aftermath->S1": ("o2", "oren"),
    "PRO_choice_aftermath->S5": ("o3", "oren"),
    "PRO_choice_first_fire->P1": ("o1", "alda"),
    "PRO_choice_first_fire->S1": ("o2", "oren"),
    "PRO_choice_first_fire->S5": ("o3", "oren"),
}


def _choice(choice_id, option_id, source=PLAYER_SOURCE):
    # The Prologue never writes NPC memory: the committed choice carries none.
    return CommittedChoice(choice_id, option_id, source, frozenset())


def test_six_hooks_map_one_to_one_to_the_options():
    catalog = prologue_catalog()
    seen = {}
    for node in catalog.nodes.values():
        assert sorted(h.when_option for h in node.future_hooks) == ["o1", "o2", "o3"]
        for hook in node.future_hooks:
            assert hook.basis == "character_memory" and hook.knowledge_holders == ()
            assert hook.hook_id == f"{node.choice_id}->{hook.target}"
            seen[hook.hook_id] = hook.when_option
    assert seen == {hook_id: option for hook_id, (option, _) in HOOKS.items()}


def test_each_option_shows_only_its_own_reaction_without_npc_memory():
    catalog = prologue_catalog()
    for hook_id, (option_id, speaker) in HOOKS.items():
        node, hook = catalog.hook(hook_id)
        for other in ("o1", "o2", "o3"):
            line = legitimate_reaction(node, hook, _choice(node.choice_id, other))
            if other == option_id:
                assert line is not None and line.speaker == speaker and line.draft
                assert line.text.startswith(("Alda ", "Oren "))
            else:
                assert line is None
        # no choice, another choice or a backfilled character: no invented reaction
        assert legitimate_reaction(node, hook, None) is None
        backfilled = _choice(node.choice_id, option_id, "neutral_backfill")
        assert resolve_hook(node, hook, backfilled) is None
        other_node = next(n for n in catalog.nodes.values() if n is not node)
        assert resolve_hook(node, hook, _choice(other_node.choice_id, option_id)) is None


def test_prologue_reactions_are_the_six_draft_texts_of_documento_a():
    from pathlib import Path

    doc = Path("docs/specs/ASTERION_DECISOES_PROLOGO_E_CONTRATOS_v1_0_0.md").read_text(
        encoding="utf-8"
    )
    section = doc.split("## 6. Ganchos futuros", 1)[1].split("\n## 7.", 1)[0]
    texts = {line[2:].strip() for line in section.splitlines() if line.startswith("> ")}
    lines = {k: v for k, v in reaction_lines().items() if k[0].startswith("PRO_")}
    assert len(lines) == 6 and all(v.draft for v in lines.values())
    assert {v.text for v in lines.values()} == texts


def test_prologue_hook_validation_rejects_malformed_hooks():
    node = next(iter(prologue_catalog().nodes.values()))

    def raw(hooks):
        return {
            "choice_id": node.choice_id,
            "mission_id": "PRO",
            "mission_kind": "prologo",
            "title": "t",
            "region": "r",
            "step": None,
            "step_context": "c",
            "question": "q",
            "identity_conditions": [],
            "future_hooks": hooks,
            "options": [
                {
                    "option_id": o.option_id,
                    "label": o.label,
                    "memory_type": o.memory_type,
                    "character_memory_tags": list(o.character_memory_tags),
                    "npc_memory_targets": [],
                }
                for o in node.options
            ],
        }

    good = [
        {
            "hook_id": f"{node.choice_id}->P1",
            "target": "P1",
            "knowledge_holders": [],
            "summary": "s",
            "when_option": "o1",
            "basis": "character_memory",
        }
    ]
    build_node(raw(good))
    for change in (
        {"when_option": "o9"},
        {"when_option": None},
        {"basis": "npc_memory"},
        {"knowledge_holders": ["alda"]},
        {"hook_id": "OTHER->P1"},
    ):
        with pytest.raises(ValueError):
            build_node(raw([{**good[0], **change}]))
    with pytest.raises(ValueError):  # two hooks on the same option
        build_node(raw([good[0], {**good[0], "hook_id": f"{node.choice_id}->S1"}]))


def test_the_72_mission_hooks_are_untouched_by_the_prologue_mechanism():
    catalog = narrative_catalog()
    assert len(catalog.nodes) == 72
    hooks = [h for node in catalog.nodes.values() for h in node.future_hooks]
    assert hooks and all(h.basis == "npc_memory" and h.when_option is None for h in hooks)


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
