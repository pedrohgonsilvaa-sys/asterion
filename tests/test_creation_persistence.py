import asyncio
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from asterion.application.creation import CreationService
from asterion.domain.creation import CLASSES, PROLOGUE, RACES, RULESET, NamePolicy
from asterion.infrastructure.db.models import Account, Character, CreationDraft


async def click(service, actor, state, action):
    return await service.callback(actor, state.id, state.version, action)


async def ready(service, actor=1, name="Luiken"):
    state = await service.start(actor)
    state = await service.name(actor, name, 1)
    for action in ("r0", "choose", "c1", "choose"):
        state = await click(service, actor, state, action)
    assert state.step == "confirm"
    return state


async def test_new_start_and_parallel_start_have_one_draft(service, database):
    states = await asyncio.gather(*(service.start(1) for _ in range(8)))
    assert all(state == states[0] for state in states)
    assert states[0].step == "name"
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(CreationDraft)) == 1


async def test_restart_every_step_including_detail_and_errors(service, database):
    state = await service.start(1)

    async def reconnect(expected):
        # New pool and service; no Python/Redis/FSM state survives this reconnect.
        await database[0].dispose()
        assert await CreationService(database[1], "ocaso").start(1) == expected

    await reconnect(state)
    state = await service.name(1, "Inválido", 1)
    assert state.error == "format"
    await reconnect(state)
    state = await service.name(1, "Luiken", 2)
    await reconnect(state)
    for action in ("r0", "choose", "c1", "choose"):
        state = await click(service, 1, state, action)
        await reconnect(state)
    state = await click(service, 1, state, "confirm")
    assert state.step == PROLOGUE
    persisted = await service.start(1)
    assert persisted.step == PROLOGUE
    assert persisted.id == state.id
    await reconnect(persisted)


async def test_navigation_and_back_buttons(service):
    state = await service.start(1)
    state = await service.name(1, "Luiken", 1)
    for action, expected in [
        ("backname", "name"),
    ]:
        state = await click(service, 1, state, action)
        assert state.step == expected
    state = await service.name(1, "LUIKEN", 2)
    for action, expected in [
        ("r0", "race:remanescente"),
        ("races", "race"),
        ("r1", "race:velado"),
        ("choose", "class"),
        ("races", "race"),
        ("r4", "race:alvorano"),
        ("choose", "class"),
        ("c0", "class:sentinela"),
        ("classes", "class"),
        ("c5", "class:luminar"),
        ("choose", "confirm"),
        ("classes", "class"),
        ("c1", "class:errante"),
        ("choose", "confirm"),
    ]:
        state = await click(service, 1, state, action)
        assert state.step == expected
    assert (state.name, state.race, state.character_class) == ("Luiken", "alvorano", "errante")


async def test_confirmation_edits_preserve_other_choices(service):
    state = await ready(service)
    state = await click(service, 1, state, "name")
    state = await service.name(1, "Aster", 2)
    assert (state.step, state.name, state.race, state.character_class) == (
        "confirm",
        "Aster",
        "remanescente",
        "errante",
    )
    for action in ("race", "r4", "choose"):
        state = await click(service, 1, state, action)
    assert (state.step, state.name, state.race, state.character_class) == (
        "confirm",
        "Aster",
        "alvorano",
        "errante",
    )
    for action in ("class", "c5", "choose"):
        state = await click(service, 1, state, action)
    assert (state.step, state.name, state.race, state.character_class) == (
        "confirm",
        "Aster",
        "alvorano",
        "luminar",
    )


async def test_stale_duplicate_foreign_and_incompatible_callbacks(service, database):
    state = await service.start(1)
    state = await service.name(1, "Luiken", 1)
    device_two = CreationService(database[1], "ocaso")
    states = await asyncio.gather(
        click(service, 1, state, "r0"),
        click(device_two, 1, state, "r0"),
    )
    current = await service.start(1)
    assert states == [current, current]
    assert current.version == state.version + 1
    assert await click(service, 1, state, "backname") == current
    assert await click(service, 1, current, "confirm") == current
    stranger = await service.start(2)
    assert await click(service, 2, current, "choose") == stranger
    other_server = CreationService(database[1], "other")
    other_draft = await other_server.start(1)
    assert await click(other_server, 1, current, "choose") == other_draft


async def test_duplicate_text_does_not_overwrite_a_later_name_edit(service):
    state = await ready(service)
    state = await click(service, 1, state, "name")
    assert await service.name(1, "Luiken", 1) == state
    state = await service.name(1, "Aster", 2)
    assert state.name == "Aster"


async def test_concurrent_confirmation_is_idempotent_across_devices(service, database):
    state = await ready(service)
    device_two = CreationService(database[1], "ocaso")
    results = await asyncio.gather(
        *(click(device_two if i % 2 else service, 1, state, "confirm") for i in range(8))
    )
    assert len({result.id for result in results}) == 1
    assert all(result.step == PROLOGUE for result in results)
    assert (await service.name(1, "Another", 3)).step == PROLOGUE
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(Character)) == 1
        character = await session.scalar(select(Character))
        draft = await session.scalar(select(CreationDraft))
        assert (character.name, character.race, character.character_class) == (
            "Luiken",
            "remanescente",
            "errante",
        )
        assert character.stage == PROLOGUE and character.ruleset_version == RULESET
        assert draft.step == "completed"


async def test_name_race_has_one_winner_and_retry_preserves_choices(service, database):
    first, second = await asyncio.gather(ready(service, 1, "LUIKEN"), ready(service, 2, "luiken"))
    results = await asyncio.gather(
        click(service, 1, first, "confirm"),
        click(service, 2, second, "confirm"),
    )
    assert sorted(result.step for result in results) == [PROLOGUE, "name"]
    loser_index = next(i for i, result in enumerate(results) if result.step == "name")
    loser = results[loser_index]
    assert loser.error == "unavailable"
    assert loser.race == "remanescente" and loser.character_class == "errante"
    assert await service.start(loser_index + 1) == loser
    renamed = await service.name(loser_index + 1, "Another", 2)
    assert renamed.step == "confirm"
    assert (await click(service, loser_index + 1, renamed, "confirm")).step == PROLOGUE
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(Character)) == 2


async def test_case_insensitive_name_scope_and_account_server_scope(service, database):
    state = await ready(service)
    await click(service, 1, state, "confirm")
    await service.start(2)
    denied = await service.name(2, "lUiKeN", 1)
    assert denied.error == "unavailable"
    other = CreationService(database[1], "other")
    other_state = await ready(other, 1, "lUiKeN")
    assert (await click(other, 1, other_state, "confirm")).step == PROLOGUE


async def test_configurable_policy_rechecked_at_commit(service, database):
    state = await ready(service)
    moderated = CreationService(database[1], "ocaso", NamePolicy(frozenset({"LUIKEN"})))
    denied = await click(moderated, 1, state, "confirm")
    assert denied.step == "name" and denied.error == "unavailable"
    assert (await moderated.name(1, "Luiken", 2)).error == "unavailable"
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(Character)) == 0


async def test_database_constraints_cannot_be_bypassed(service, database):
    state = await ready(service)
    await click(service, 1, state, "confirm")
    await service.start(2)
    for actor, name, race, cls in [
        (1, "Another", RACES[0], CLASSES[0]),
        (2, "Luiken", RACES[0], CLASSES[0]),
        (2, "luiken", RACES[0], CLASSES[0]),
        (2, "Bad1", RACES[0], CLASSES[0]),
        (2, "Another", "invented", CLASSES[0]),
        (2, "Another", RACES[0], "invented"),
    ]:
        with pytest.raises(IntegrityError):
            async with database[1].begin() as session:
                session.add(
                    Character(
                        telegram_id=actor,
                        server_id="ocaso",
                        name=name,
                        race=race,
                        character_class=cls,
                        stage=PROLOGUE,
                        ruleset_version=RULESET,
                    )
                )


async def test_failed_commit_rolls_back_character_and_draft(service, database):
    state = await ready(service)
    async with database[0].begin() as connection:
        await connection.execute(
            text("""
            CREATE FUNCTION reject_completion() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF NEW.step = 'completed' THEN RAISE EXCEPTION 'test rollback'; END IF;
              RETURN NEW;
            END $$
        """)
        )
        await connection.execute(
            text("""
            CREATE TRIGGER test_failure BEFORE UPDATE ON creation_drafts
            FOR EACH ROW EXECUTE FUNCTION reject_completion()
        """)
        )
    with pytest.raises(Exception, match="test rollback"):
        await click(service, 1, state, "confirm")
    assert await service.start(1) == state
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(Character)) == 0


async def test_migration_downgrade_and_upgrade(database):
    async with database[0].begin() as connection:

        def migrate(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.downgrade(config, "20260920_0001")
            command.upgrade(config, "head")
            command.check(config)

        await connection.run_sync(migrate)


async def test_callback_without_draft_cannot_create_state(service, database):
    assert await service.callback(10, uuid4(), 0, "r0") is None
    assert await service.resume(10) is None
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(Account)) == 0


async def test_forged_actions_are_safe_and_do_not_change_version(service):
    await service.start(1)
    state = await service.name(1, "Luiken", 1)
    for action in ("r²", "r-1", "r9", "r00", "r999999999999", "c0", "confirm", "choose"):
        assert await click(service, 1, state, action) == state
