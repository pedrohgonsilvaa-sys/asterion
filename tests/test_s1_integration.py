import pytest
from sqlalchemy import select

from asterion.application.s1 import (
    CODEX_ROAD,
    LIGHTS_FRAGMENT,
    REWARD_SOURCE,
    S1Service,
)
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CodexFragment,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)
from tests.test_road_integration import _seed_road


async def _seed_s1(database, actor: int):
    await _seed_road(database, actor)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.level = 2
        character.xp = 0
        await session.commit()
    return S1Service(sessions, "ocaso")


@pytest.mark.asyncio
async def test_s1_requires_explicit_acceptance_at_oren(database):
    actor = 774001
    service = await _seed_s1(database, actor)

    oren = await service.oren(actor)
    assert oren is not None
    assert oren.available is True
    assert oren.status == "unaccepted"

    offer = await service.offer(actor)
    assert offer.kind == "offer"
    async with database[1]() as session:
        assert await session.scalar(
            select(Quest).where(Quest.quest_id == "S1")
        ) is None

    accepted = await service.accept(actor)
    assert accepted.status == "active"
    assert accepted.step == 1
    assert accepted.progress["points"] == []
    assert accepted.tracked is False


@pytest.mark.asyncio
async def test_s1_points_are_any_order_idempotent_and_road_scoped(database):
    actor = 774002
    service = await _seed_s1(database, actor)
    accepted = await service.accept(actor)

    # Objective cannot progress while the character is still in the Refuge.
    blocked = await service.investigate_point(actor, 3, accepted.state_version)
    assert blocked.step == 1
    assert blocked.progress["points"] == []

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = "Estrada das Cinzas"
        await session.commit()

    first = await service.investigate_point(actor, 3, accepted.state_version)
    assert first.progress["points"] == [3]
    duplicate = await service.investigate_point(actor, 3, first.state_version)
    assert duplicate.progress["points"] == [3]
    second = await service.investigate_point(actor, 1, first.state_version)
    assert second.progress["points"] == [1, 3]
    third = await service.investigate_point(actor, 2, second.state_version)
    assert third.step == 2
    assert third.progress["points"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_s1_abandon_resets_transient_progress_but_preserves_codex(database):
    actor = 774003
    service = await _seed_s1(database, actor)
    accepted = await service.accept(actor)

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = "Estrada das Cinzas"
        await session.commit()

    view = accepted
    for point in (1, 2, 3):
        view = await service.investigate_point(actor, point, view.state_version)
    view = await service.examine_ashes(actor, view.state_version)
    observed = await service.observe_light(actor, view.state_version)
    assert observed.step == 4
    assert observed.fragment_new_this_attempt is True

    tracked = await service.toggle_tracking(actor, observed.state_version)
    assert tracked.tracked is True
    abandoned = await service.abandon(actor, tracked.state_version)
    assert abandoned.status == "abandoned"
    assert abandoned.step == 1
    assert abandoned.progress == {}
    assert abandoned.tracked is False

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.tracked_secondary_quest_id is None
        assert await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == CODEX_ROAD,
            )
        )
        assert await session.scalar(
            select(CodexFragment).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == LIGHTS_FRAGMENT,
            )
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = "Refúgio do Ocaso"
        await session.commit()

    offer = await service.offer(actor)
    assert offer.reacceptable is True
    restarted = await service.accept(actor, reaccept=True)
    assert restarted.status == "active"
    assert restarted.step == 1
    assert restarted.progress["points"] == []


@pytest.mark.asyncio
async def test_s1_completion_is_atomic_idempotent_and_clears_tracking(database):
    actor = 774004
    service = await _seed_s1(database, actor)
    accepted = await service.accept(actor)

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = "Estrada das Cinzas"
        await session.commit()

    view = accepted
    for point in (2, 1, 3):
        view = await service.investigate_point(actor, point, view.state_version)
    view = await service.examine_ashes(actor, view.state_version)
    view = await service.observe_light(actor, view.state_version)
    view = await service.toggle_tracking(actor, view.state_version)
    assert view.tracked is True

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = "Refúgio do Ocaso"
        await session.commit()

    completed = await service.complete_with_oren(actor, view.state_version)
    assert completed.status == "completed"
    assert completed.fragment_new_this_attempt is True

    stale = await service.complete_with_oren(actor, view.state_version)
    assert stale.status == "completed"

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == "S1",
            )
        )
        assert quest.status == "completed"
        assert character.xp == 1140
        assert character.crowns == 60
        assert character.tracked_secondary_quest_id is None
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == REWARD_SOURCE,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event.id
                )
            )
        ).all()
        assert sorted((row.kind, row.quantity) for row in components) == [
            ("crowns", 60),
            ("xp", 1140),
        ]


@pytest.mark.asyncio
async def test_s1_existing_lights_fragment_is_not_announced_as_new(database):
    actor = 774005
    service = await _seed_s1(database, actor)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            CodexEntry(character_id=character.id, entry_id=CODEX_ROAD)
        )
        session.add(
            CodexFragment(
                character_id=character.id,
                entry_id=CODEX_ROAD,
                fragment_id=LIGHTS_FRAGMENT,
            )
        )
        await session.commit()

    accepted = await service.accept(actor)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = "Estrada das Cinzas"
        await session.commit()

    view = accepted
    for point in (1, 2, 3):
        view = await service.investigate_point(actor, point, view.state_version)
    view = await service.examine_ashes(actor, view.state_version)
    view = await service.observe_light(actor, view.state_version)
    assert view.fragment_owned is True
    assert view.fragment_new_this_attempt is False
