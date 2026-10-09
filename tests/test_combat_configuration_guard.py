import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select, text

import asterion.application.pvpve as pvpve_module
from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.road import ROAD
from asterion.infrastructure.db.models import Character, GameActivity, HuntRound
from tests.test_road_integration import _seed_road


async def _character_id(database, actor: int):
    _, sessions = database
    async with sessions() as session:
        return await session.scalar(
            select(Character.id).where(Character.telegram_id == actor)
        )


async def _wait_for_postgres_lock(database, query_fragment: str) -> None:
    """Wait until PostgreSQL reports the competing query blocked on a row lock."""
    _, sessions = database
    deadline = asyncio.get_running_loop().time() + 5
    statement = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
              AND wait_event_type = 'Lock'
              AND query ILIKE :query_pattern
        )
        """
    )
    while asyncio.get_running_loop().time() < deadline:
        async with sessions() as observer:
            waiting = await observer.scalar(
                statement, {"query_pattern": f"%{query_fragment}%"}
            )
        if waiting:
            return
        # Polling only observes PostgreSQL's lock table; the database lock controls
        # when the competing operation may continue.
        await asyncio.sleep(0.01)
    raise AssertionError(f"No PostgreSQL lock wait observed for {query_fragment}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("blocker_kind", "status", "blocked"),
    [
        (None, None, False),
        ("activity", "active", True),
        ("activity", "completed", False),
        ("activity", "failed", False),
        ("round", "preparing", False),
        ("round", "active", True),
        ("round", "interrupted", True),
        ("round", "completed", False),
        ("round", "cancelled", False),
        ("round", "defeated", False),
        ("round", "ended", False),
    ],
)
async def test_guard_uses_authoritative_foreground_and_round_states(
    database, blocker_kind, status, blocked
):
    actor = 884001
    await _seed_road(database, actor=actor)
    character_id = await _character_id(database, actor)
    assert character_id is not None

    if blocker_kind == "activity":
        async with database[1].begin() as session:
            session.add(
                GameActivity(
                    id=uuid4(),
                    character_id=character_id,
                    content_id="test.combat",
                    status=status,
                    state_version=0,
                    ruleset_version="test-ruleset",
                )
            )
    elif blocker_kind == "round":
        async with database[1].begin() as session:
            session.add(
                HuntRound(
                    id=uuid4(),
                    character_id=character_id,
                    status=status,
                    batch_size=5,
                    seed="test-round",
                )
            )

    if blocked:
        with pytest.raises(CombatConfigurationLocked) as raised:
            async with database[1].begin() as session:
                await lock_for_combat_configuration_mutation(session, character_id)
        assert raised.value.blocker.status == status
        assert raised.value.blocker.kind == (
            "foreground_activity" if blocker_kind == "activity" else "hunt_round"
        )
    else:
        async with database[1].begin() as session:
            character = await lock_for_combat_configuration_mutation(session, character_id)
            assert character is not None and character.id == character_id


@pytest.mark.asyncio
async def test_guard_requires_caller_owned_transaction(database):
    actor = 884002
    await _seed_road(database, actor=actor)
    character_id = await _character_id(database, actor)
    assert character_id is not None

    async with database[1]() as session:
        with pytest.raises(RuntimeError, match="open transaction"):
            await lock_for_combat_configuration_mutation(session, character_id)


@pytest.mark.asyncio
async def test_postgres_activity_start_first_is_seen_after_character_lock(database, monkeypatch):
    actor = 884003
    actor, service = await _seed_road(database, actor=actor)
    await service.travel(actor, ROAD)
    character_id = await _character_id(database, actor)
    assert character_id is not None

    creation_reached = asyncio.Event()
    allow_creation = asyncio.Event()
    original_queue = pvpve_module.PvpveService.queue_manual_hunt.__get__(service.pvpve)

    async def pause_after_character_lock(session, character, world, profile):
        creation_reached.set()
        await allow_creation.wait()
        return await original_queue(session, character, world, profile)

    monkeypatch.setattr(
        service.pvpve,
        "queue_manual_hunt",
        pause_after_character_lock,
    )
    activity_task = asyncio.create_task(service.start_hunt(actor))
    mutation_task = None
    try:
        await asyncio.wait_for(creation_reached.wait(), timeout=5)

        async def attempt_mutation():
            async with database[1].begin() as session:
                return await lock_for_combat_configuration_mutation(session, character_id)

        mutation_task = asyncio.create_task(attempt_mutation())
        await _wait_for_postgres_lock(database, "characters")
        allow_creation.set()
        activity = await asyncio.wait_for(activity_task, timeout=5)
        assert activity is not None and activity.kind == "hunt_queue"
        with pytest.raises(CombatConfigurationLocked) as raised:
            await asyncio.wait_for(mutation_task, timeout=5)
        assert raised.value.blocker.kind == "foreground_activity"
        assert raised.value.blocker.id == activity.activity_id
    finally:
        allow_creation.set()
        for task in (activity_task, mutation_task):
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_postgres_guard_first_serializes_real_road_activity_start(database):
    actor = 884004
    actor, service = await _seed_road(database, actor=actor)
    await service.travel(actor, ROAD)
    character_id = await _character_id(database, actor)
    assert character_id is not None

    async with database[1].begin() as session:
        character = await lock_for_combat_configuration_mutation(session, character_id)
        assert character is not None
        activity_task = asyncio.create_task(service.start_hunt(actor))
        await _wait_for_postgres_lock(database, "characters")

    activity = await asyncio.wait_for(activity_task, timeout=5)
    assert activity is not None and activity.kind == "combat"
    with pytest.raises(CombatConfigurationLocked) as raised:
        async with database[1].begin() as session:
            await lock_for_combat_configuration_mutation(session, character_id)
    assert raised.value.blocker.kind == "foreground_activity"
    assert raised.value.blocker.id == activity.activity_id
