import os
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command


def _migrate(connection, revision: str, direction: str = "upgrade") -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    getattr(command, direction)(config, revision)


@pytest_asyncio.fixture
async def schema_at_0010():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run real PostgreSQL migration tests")

    schema = "test_hunt_context_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20260925_0010"))
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.mark.asyncio
async def test_0011_backfills_legacy_hunt_context_and_requires_local_id(schema_at_0010):
    engine = schema_at_0010
    character_id = uuid4()
    activity_id = uuid4()
    hunt_context_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (990011)")
        )
        await connection.execute(
            text(
                "INSERT INTO characters "
                "(id, telegram_id, server_id, name, race, character_class, stage, "
                "ruleset_version, hp, max_hp) VALUES "
                "(:id, 990011, 'ocaso', 'Heroa', 'remanescente', 'sentinela', "
                "'menu:ready', 'gdd-1.4.3-baseline-1.0', 702, 702)"
            ),
            {"id": character_id},
        )
        await connection.execute(
            text(
                "INSERT INTO game_activities "
                "(id, character_id, content_id, status, state_version, ruleset_version) "
                "VALUES (:id, :character_id, 'road_manual_hunt', 'completed', 1, "
                "'gdd-1.4.3-baseline-1.0')"
            ),
            {"id": activity_id, "character_id": character_id},
        )
        await connection.execute(
            text(
                "INSERT INTO hunt_contexts "
                "(id, game_activity_id, character_id, creature_id, category, enemy_level, "
                "seed, loot_profile) VALUES (:id, :activity_id, :character_id, 'dog_cinereo', "
                "'common', 1, 'migration-seed', 'hunt')"
            ),
            {"id": hunt_context_id, "activity_id": activity_id, "character_id": character_id},
        )
        await connection.run_sync(lambda sync: _migrate(sync, "20260926_0011"))
        local_id = await connection.scalar(
            text("SELECT local_id FROM hunt_contexts WHERE game_activity_id=:activity_id"),
            {"activity_id": activity_id},
        )
        nullable = await connection.scalar(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_schema=current_schema() AND table_name='hunt_contexts' "
                "AND column_name='local_id'"
            )
        )
    assert local_id == "tdo.location.estrada_das_cinzas"
    assert nullable == "NO"
