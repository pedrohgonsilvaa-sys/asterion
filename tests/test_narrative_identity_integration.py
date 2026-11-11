"""Alda architecture case: individual narrative state survives a cooperative fight.

The three Alda choices are test-only flags, not canonical P2 content. They prove
that each character keeps a personal consequence while the same NPC exists for
all of them, and that a helper in a host's fight inherits nothing narrative.
"""

from uuid import UUID

import pytest
from sqlalchemy import select

from asterion.application.groups import GroupService
from asterion.application.narrative_identity import (
    load_narrative_context,
    resolve_character_scene,
)
from asterion.application.p1 import P1Service
from asterion.domain.narrative_identity import (
    NarrativeBeat,
    NarrativeCondition,
    NarrativeLine,
    NarrativeOption,
    NarrativeScene,
)
from asterion.infrastructure.db.models import Character, Quest, RewardEvent, Unlock
from tests.test_campaign_coop_integration import (
    _confirm_and_start,
    _create_group,
    _finish_p1_group_fight,
    _seed_enemy_at_one_hp,
    _seed_party,
)

HANDED = "test.alda.entregar"
HELPED = "test.alda.ajudar"
ABANDONED = "test.alda.abandonar"
IDENTITY = {
    0: ("remanescente", "sentinela", HANDED),
    1: ("velado", "vigia", HELPED),
    2: ("cinereo", "oraculo", ABANDONED),
}


def _flag_line(flag, line_id):
    return NarrativeLine(
        line_id, line_id, NarrativeCondition(required_flags=frozenset({flag})), priority=10
    )


SCENES = {
    "test.alda.reunion": NarrativeScene(
        scene_id="test.alda.reunion",
        beats=(
            NarrativeBeat(
                "memory",
                (
                    NarrativeLine("memory.common", "memory.common"),
                    _flag_line(HANDED, "memory.handed"),
                    _flag_line(HELPED, "memory.helped"),
                    _flag_line(ABANDONED, "memory.abandoned"),
                ),
            ),
            NarrativeBeat(
                "recognition",
                (
                    NarrativeLine("recognition.common", "recognition.common"),
                    NarrativeLine(
                        "recognition.velado",
                        "recognition.velado",
                        NarrativeCondition(races=frozenset({"velado"})),
                    ),
                    NarrativeLine(
                        "recognition.oraculo",
                        "recognition.oraculo",
                        NarrativeCondition(classes=frozenset({"oraculo"})),
                    ),
                ),
            ),
        ),
        options=(
            NarrativeOption("ask", "ask"),
            NarrativeOption(
                "watch_signal",
                "watch_signal",
                NarrativeCondition(race_classes=frozenset({("velado", "vigia")})),
            ),
        ),
    )
}


async def _characters(database, actors):
    async with database[1]() as session:
        rows = (
            await session.scalars(select(Character).where(Character.telegram_id.in_(actors)))
        ).all()
        return {row.telegram_id: row.id for row in rows}


async def _resolved(database, character_id):
    async with database[1]() as session:
        scene = await resolve_character_scene(
            session, character_id, "test.alda.reunion", scenes=SCENES
        )
    return (
        tuple(line.line_id for line in scene.lines),
        tuple(option.option_id for option in scene.options),
    )


@pytest.mark.asyncio
async def test_alda_choices_stay_individual_through_a_cooperative_fight(database, monkeypatch):
    import asterion.application.p1 as p1_module

    monkeypatch.setattr(p1_module, "uuid4", lambda: UUID(int=7101))
    actors = (993201, 993202, 993203)
    names = await _seed_party(database, actors)
    ids = await _characters(database, actors)
    async with database[1].begin() as session:
        for index, actor in enumerate(actors):
            race, klass, flag = IDENTITY[index]
            character = await session.get(Character, ids[actor])
            character.race = race
            character.character_class = klass
            session.add(Unlock(character_id=character.id, unlock_id=flag))
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P1")
            )
            if index == 0:
                quest.step = 3
                quest.state_version = 3
                quest.progress = {"pegadas": True, "sulcos": True}
            else:
                quest.status = "completed"
                quest.step = 7
                quest.progress = {"completed": True}
                session.add(
                    RewardEvent(character_id=character.id, source_id="p1.vozes_na_estrada")
                )

    host, helper, third = (ids[actor] for actor in actors)
    before = {cid: await _resolved(database, cid) for cid in (host, helper, third)}
    assert before[host] == (("memory.handed", "recognition.common"), ("ask",))
    assert before[helper] == (
        ("memory.helped", "recognition.velado"),
        ("ask", "watch_signal"),
    )
    assert before[third] == (("memory.abandoned", "recognition.oraculo"), ("ask",))
    async with database[1]() as session:
        contexts = {cid: await load_narrative_context(session, cid) for cid in before}
    assert len({context.flags for context in contexts.values()}) == 3

    # A calls B for the cooperative fight; C stays out.
    groups = GroupService(database[1], "ocaso")
    await _create_group(groups, actors[0], actors[1:2], names)
    service = P1Service(database[1], "ocaso", groups)
    proposal = await service.propose_group_combat(actors[0], 3)
    proposal_view = await groups.activity_proposal(actors[0], proposal.proposal_id)
    roles = {row.character_id: row.eligibility for row in proposal_view.participants}
    assert roles == {host: "eligible", helper: "helper"}
    started = await _confirm_and_start(
        groups, service, actors[0], proposal.proposal_id, actors[:2]
    )
    assert started.combat is not None and started.group_size == 2
    await _seed_enemy_at_one_hp(database, started.encounter_id)
    await _finish_p1_group_fight(service, actors[:2], database, started.encounter_id)

    # Reconnect and retry: resolving again reads the same personal state.
    after = {cid: await _resolved(database, cid) for cid in before}
    assert after == before
    assert await _resolved(database, helper) == before[helper]
    async with database[1]() as session:
        host_ctx = await load_narrative_context(session, host)
        helper_ctx = await load_narrative_context(session, helper)
        helper_rewards = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == helper,
                    RewardEvent.source_id == "p1.vozes_na_estrada",
                )
            )
        ).all()
    assert host_ctx.flags == frozenset({HANDED})
    assert helper_ctx.flags == frozenset({HELPED})
    assert (host_ctx.race, host_ctx.character_class) == ("remanescente", "sentinela")
    assert (helper_ctx.race, helper_ctx.character_class) == ("velado", "vigia")
    assert host_ctx.quests["P1"].step == 4
    assert helper_ctx.quests["P1"].status == "completed"
    assert helper_ctx.quests["P1"].step == 7
    assert len(helper_rewards) == 1
