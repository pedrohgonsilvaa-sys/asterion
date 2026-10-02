import os
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command


def _migrate(connection, revision: str, direction: str = "upgrade") -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    getattr(command, direction)(config, revision)


@pytest_asyncio.fixture
async def schema_at_0013():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run real PostgreSQL migration tests")
    schema = "test_character_path_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20260929_0013"))
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.mark.asyncio
async def test_0014_selected_path_defaults_null_enforces_values_and_downgrades_safely(
    schema_at_0013,
):
    engine = schema_at_0013
    actor = 771299
    character_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:actor)"), {"actor": actor}
        )
        await connection.execute(
            text(
                "INSERT INTO characters (id, telegram_id, server_id, name, race, "
                "character_class, stage, ruleset_version, level, xp, hp, max_hp, vigor, "
                "max_vigor, crowns, combat_configuration_version) VALUES "
                "(:id, :actor, 'ocaso', 'Pathmigration', 'remanescente', 'sentinela', "
                "'menu:ready', 'gdd-1.4.7-baseline-1.0', 10, 0, 1000, 1000, 100, 100, 0, 0)"
            ),
            {"id": character_id, "actor": actor},
        )
        await connection.run_sync(lambda sync: _migrate(sync, "head"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261001_0016"
        )
        assert await connection.scalar(
            text("SELECT selected_path FROM characters WHERE id = :id"), {"id": character_id}
        ) is None

    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text("UPDATE characters SET selected_path = 'not_a_path' WHERE id = :id"),
                {"id": character_id},
            )

    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE characters SET selected_path = 'bastiao' WHERE id = :id"),
            {"id": character_id},
        )

    with pytest.raises(
        RuntimeError, match="Cannot downgrade while characters have a selected Path"
    ):
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: _migrate(sync, "20260929_0013", direction="downgrade")
            )

    async with engine.begin() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261001_0016"
        )
        await connection.execute(
            text("DELETE FROM characters WHERE id = :id"), {"id": character_id}
        )
        await connection.run_sync(
            lambda sync: _migrate(sync, "20260929_0013", direction="downgrade")
        )
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260929_0013"
        )
