"""Ação × Consequência v1.0.0 on PostgreSQL: commit once, scoped memory, legitimate hooks."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.narrative_choices import (
    NarrativeChoiceError,
    audit_character_choices,
    backfill_neutral_choice,
    commit_narrative_choice,
    npc_rapport,
    resolve_future_hook,
    resolve_future_reaction,
)
from asterion.application.p1 import P1Service
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.narrative_choices import build_catalog
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterNarrativeMemory,
    CodexEntry,
    NarrativeChoiceRecord,
    NpcNarrativeMemory,
    Quest,
    WorldState,
)
from asterion.narrative_cli import format_chain
from tests.test_narrative_choices_domain import _synthetic
from tests.test_p2_integration import _seed as _seed_p2
from tests.test_s1_integration import _seed_s1


async def _character(sessions, actor, *, race="remanescente", klass="sentinela"):
    character_id = uuid4()
    stats = resolve_combat_stats(klass, 3, race)
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Nar{chr(ord('a') + actor % 26)}",
                race=race,
                character_class=klass,
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=3,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=77,
                max_vigor=100,
                crowns=11,
            )
        )
        await session.flush()
        session.add(
            WorldState(
                character_id=character_id, region="Terras do Ocaso", location="Refúgio do Ocaso"
            )
        )
    return character_id


async def _quest(sessions, character_id, quest_id, step, status="active"):
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=quest_id,
                title=quest_id,
                status=status,
                step=step,
                content_version="tdo-1.0.2",
            )
        )


async def _load(session, character_id, quest_id="P1"):
    character = await session.get(Character, character_id)
    quest = await session.scalar(
        select(Quest).where(Quest.character_id == character_id, Quest.quest_id == quest_id)
    )
    return character, quest


async def _count(session, model, character_id):
    return await session.scalar(
        select(func.count()).select_from(model).where(model.character_id == character_id)
    )


@pytest.mark.asyncio
async def test_p1_posture_commits_once_and_p2_alda_reacts_from_her_own_memory(database):
    """Vertical slice: P1 action changes the P2 reaction, without a new mission."""
    _, sessions = database
    actor = 991001
    character_id, p2 = await _seed_p2(database, actor, p1_status="active")
    async with sessions.begin() as session:
        quest = await session.scalar(select(Quest).where(Quest.character_id == character_id))
        quest.step, quest.state_version = 5, 4
    p1 = P1Service(sessions, "ocaso")

    first = await p1.choose_posture(actor, 4, "o3")
    assert first.step == 6 and first.narrative.selected_option == "o3"
    # Reconnect / retry / duplicated callback with the old version, even another option.
    for option in ("o3", "o1"):
        again = await p1.choose_posture(actor, 4, option)
        assert again.step == 6 and again.narrative.selected_option == "o3"

    async with sessions() as session:
        assert await _count(session, NarrativeChoiceRecord, character_id) == 1
        npc = set(
            (
                await session.execute(
                    select(NpcNarrativeMemory.npc_id, NpcNarrativeMemory.tag).where(
                        NpcNarrativeMemory.character_id == character_id
                    )
                )
            ).all()
        )
        assert npc == {("alda", "curiosidade_ativa"), ("oren", "investigador")}
        assert await npc_rapport(session, character_id, "alda") == "neutral"

    async with sessions.begin() as session:
        quest = await session.scalar(select(Quest).where(Quest.character_id == character_id))
        quest.status, quest.step = "completed", 7
    offer = await p2.alda(actor)
    assert offer.kind == "offer"
    assert [line.speaker_name for line in offer.future_reactions] == ["Alda Veyr"]
    assert offer.future_reactions[0].text.startswith("Você perguntou pelos sinais")


@pytest.mark.asyncio
async def test_p2_without_registered_p1_choice_uses_common_fallback(database):
    _, sessions = database
    actor = 991002
    character_id, p2 = await _seed_p2(database, actor)
    assert (await p2.alda(actor)).future_reactions == ()
    # Migration: the character passed P1 before the system existed.
    async with sessions.begin() as session:
        assert await backfill_neutral_choice(session, character_id, "P1_choice_posture")
        assert not await backfill_neutral_choice(session, character_id, "P1_choice_posture")
    async with sessions() as session:
        assert await _count(session, CharacterNarrativeMemory, character_id) == 0
        assert await _count(session, NpcNarrativeMemory, character_id) == 0
    assert (await p2.alda(actor)).future_reactions == ()


@pytest.mark.asyncio
async def test_concurrent_duplicate_callbacks_never_replicate_consequences(database):
    _, sessions = database
    character_id = await _character(sessions, 991003)
    await _quest(sessions, character_id, "P2", 5)

    async def commit(option):
        async with sessions.begin() as session:
            character, quest = await _load(session, character_id, "P2")
            return await commit_narrative_choice(
                session, character, quest, "P2_evidentiary_posture", option
            )

    results = await asyncio.gather(commit("o1"), commit("o2"), commit("o1"))
    assert sum(result.created for result in results) == 1
    assert len({result.selected_option for result in results}) == 1
    async with sessions() as session:
        assert await _count(session, NarrativeChoiceRecord, character_id) == 1
        assert await _count(session, CharacterNarrativeMemory, character_id) == 1
        assert await _count(session, NpcNarrativeMemory, character_id) == 1


@pytest.mark.asyncio
async def test_choice_touches_no_economy_world_state_or_codex(database):
    _, sessions = database
    character_id = await _character(sessions, 991004)
    await _quest(sessions, character_id, "P2", 5)
    async with sessions() as session:
        before_character = await session.get(Character, character_id)
        before = (before_character.xp, before_character.crowns, before_character.level)
        world_before = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        world_before = (world_before.region, world_before.location)
    async with sessions.begin() as session:
        character, quest = await _load(session, character_id, "P2")
        progress_before = dict(quest.progress)
        step_before = quest.step
        await commit_narrative_choice(session, character, quest, "P2_evidentiary_posture", "o2")
        assert quest.progress == progress_before and quest.step == step_before
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert (character.xp, character.crowns, character.level) == before
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        assert (world.region, world.location) == world_before
        assert await _count(session, CodexEntry, character_id) == 0


@pytest.mark.asyncio
async def test_boss_guest_cannot_commit_the_host_choice(database):
    """Coop never shares narrative: the guest has no access to the host's node."""
    _, sessions = database
    host = await _character(sessions, 991005)
    guest = await _character(sessions, 991006)
    await _quest(sessions, host, "P6", 7)
    async with sessions.begin() as session:
        guest_character = await session.get(Character, guest)
        _, host_quest = await _load(session, host, "P6")
        with pytest.raises(NarrativeChoiceError) as error:
            await commit_narrative_choice(
                session, guest_character, host_quest, "P6_anchor_posture", "o1"
            )
        assert error.value.code == "quest_mismatch"
    async with sessions() as session:
        assert await _count(session, NarrativeChoiceRecord, host) == 0
        assert await _count(session, NarrativeChoiceRecord, guest) == 0


@pytest.mark.asyncio
async def test_unavailable_identity_option_and_unknown_option_are_refused(database):
    _, sessions = database
    character_id = await _character(sessions, 991007, klass="luminar")
    await _quest(sessions, character_id, "P1", 5)
    catalog = build_catalog([_synthetic(requires=[{"kind": "class", "values": ["vigia"]}])])
    async with sessions.begin() as session:
        character, quest = await _load(session, character_id)
        for option, code in (("o1", "option_unavailable"), ("o9", "option_unknown")):
            with pytest.raises(NarrativeChoiceError) as error:
                await commit_narrative_choice(
                    session, character, quest, "P1_test", option, catalog=catalog
                )
            assert error.value.code == code
        result = await commit_narrative_choice(
            session, character, quest, "P1_test", "o2", catalog=catalog
        )
        assert result.created


@pytest.mark.asyncio
async def test_hook_requires_the_npc_to_hold_the_memory(database):
    """S7 o1 is known by Dara only; a hook read by Iven alone must fall back."""
    _, sessions = database
    character_id = await _character(sessions, 991008)
    await _quest(sessions, character_id, "S7", 3)
    data = _synthetic()
    data["future_hooks"].append(
        {"hook_id": "P1_test->P3", "target": "P3", "knowledge_holders": [], "summary": ""}
    )
    data["options"][1]["npc_memory_targets"] = [{"npc_id": "iven", "tag": "cautela"}]
    data["future_hooks"].append(
        {"hook_id": "P1_test->P4", "target": "P4", "knowledge_holders": ["iven"], "summary": ""}
    )
    catalog = build_catalog([data])
    await _quest(sessions, character_id, "P1", 5)
    async with sessions.begin() as session:
        character, quest = await _load(session, character_id)
        await commit_narrative_choice(session, character, quest, "P1_test", "o1", catalog=catalog)
    async with sessions() as session:
        assert (
            await resolve_future_hook(session, character_id, "P1_test->P2", catalog=catalog) == "o1"
        )
        assert (
            await resolve_future_hook(session, character_id, "P1_test->P3", catalog=catalog) == "o1"
        )
        assert (
            await resolve_future_hook(session, character_id, "P1_test->P4", catalog=catalog) is None
        )


@pytest.mark.asyncio
async def test_s1_abandon_and_reaccept_keep_the_single_memory(database):
    _, sessions = database
    actor = 991009
    service = await _seed_s1(database, actor)
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
    accepted = await service.accept(actor)
    async with sessions.begin() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "S1")
        )
        quest.step, quest.progress = 4, {"light_observed": True}
        quest.state_version = accepted.state_version
    view = await service.choose_response(actor, accepted.state_version, "o2")
    assert view.narrative.selected_option == "o2"
    abandoned = await service.abandon(actor, view.state_version)
    assert abandoned.status == "abandoned"
    reaccepted = await service.accept(actor, reaccept=True)
    async with sessions.begin() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "S1")
        )
        quest.step, quest.progress = 4, {"light_observed": True}
    again = await service.choose_response(actor, reaccepted.state_version, "o1")
    assert again.narrative.selected_option == "o2" and not again.narrative.pending
    async with sessions() as session:
        assert await _count(session, NarrativeChoiceRecord, character.id) == 1
        assert await _count(session, CharacterNarrativeMemory, character.id) == 1
        assert await resolve_future_hook(session, character.id, "S1_response_to_light->S5") == "o2"
        line = await resolve_future_reaction(session, character.id, "S1_response_to_light->S5")
        assert line.speaker_name == "Oren Cal" and line.text.startswith("Você deixou a luz")


@pytest.mark.asyncio
async def test_principal_reset_keeps_memory_and_audit_shows_the_full_chain(database):
    _, sessions = database
    character_id = await _character(sessions, 991010, race="velado", klass="oraculo")
    await _quest(sessions, character_id, "P11", 5)
    async with sessions.begin() as session:
        character, quest = await _load(session, character_id, "P11")
        await commit_narrative_choice(session, character, quest, "P11_conflicting_evidence", "o1")
        # A Principal interrupted or restarted (defeat, retry) never erases memory.
        quest.step, quest.progress = 1, {}
    async with sessions() as session:
        chain = await audit_character_choices(session, character_id)
    assert chain == [
        {
            "choice_id": "P11_conflicting_evidence",
            "mission_id": "P11",
            "step_context": chain[0]["step_context"],
            "selected_option": "o1",
            "source": "player",
            "committed_at": chain[0]["committed_at"],
            "character_memories": ["conserva_duvida"],
            "npc_memories": [
                {"npc_id": "dara", "tag": "cauteloso", "knowledge": "witnessed"},
                {"npc_id": "iven", "tag": "cauteloso", "knowledge": "witnessed"},
            ],
            "future_hooks": ["P11_conflicting_evidence->P12"],
            "identity_conditions": ["race_class:velado+oraculo"],
        }
    ]
    lines = format_chain(chain)
    assert lines[0].startswith("P11_conflicting_evidence [P11] → o1")
