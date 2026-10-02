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
async def schema_at_0016():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run PostgreSQL migration tests")
    schema = "test_professions_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20261001_0016"))
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.mark.asyncio
async def test_0017_profession_and_crafting_state_upgrade_constraints_and_safe_downgrade(
    schema_at_0016,
):
    engine = schema_at_0016
    actor = 998877665501
    character_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:actor)"), {"actor": actor}
        )
        await connection.execute(
            text(
                "INSERT INTO characters (id, telegram_id, server_id, name, race, "
                "character_class, stage, ruleset_version, level, xp, hp, max_hp, vigor, "
                "max_vigor, crowns, combat_configuration_version) VALUES (:id, :actor, "
                "'ocaso', 'Profissional', 'remanescente', 'sentinela', 'menu:ready', 'test', "
                "10, 0, 702, 702, 100, 100, 5000, 0)"
            ),
            {"id": character_id, "actor": actor},
        )
        await connection.run_sync(lambda sync: _migrate(sync, "head"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261002_0017"
        )
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM character_professions WHERE character_id=:id"),
                {"id": character_id},
            )
            == 0
        )

        with pytest.raises(IntegrityError):
            async with connection.begin_nested():
                await connection.execute(
                    text(
                        "INSERT INTO character_professions "
                        "(character_id, slot, profession_id, level, pxp) "
                        "VALUES (:id, 'secondary', 'alchemist', 16, 0)"
                    ),
                    {"id": character_id},
                )

        await connection.execute(
            text(
                "INSERT INTO character_professions "
                "(character_id, slot, profession_id, level, pxp) "
                "VALUES (:id, 'primary', 'blacksmith', 20, 145), "
                "(:id, 'secondary', 'alchemist', 15, 0)"
            ),
            {"id": character_id},
        )
        await connection.execute(
            text(
                "INSERT INTO crafting_receipts "
                "(id, character_id, recipe_id, source_key, status, preview_fingerprint, seed) "
                "VALUES (:receipt, :id, 'recipe.tdo.test', 'craft:test', "
                "'preview', 'fingerprint', 'seed')"
            ),
            {"id": character_id, "receipt": uuid4()},
        )

    with pytest.raises(RuntimeError, match="crafting_receipts contains character data"):
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: _migrate(sync, "20261001_0016", direction="downgrade")
            )

    async with engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM crafting_receipts WHERE character_id=:id"),
            {"id": character_id},
        )
        await connection.execute(
            text("DELETE FROM character_professions WHERE character_id=:id"),
            {"id": character_id},
        )
        await connection.run_sync(
            lambda sync: _migrate(sync, "20261001_0016", direction="downgrade")
        )
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261001_0016"
        )
        assert await connection.scalar(text("SELECT to_regclass('character_professions')")) is None
        assert await connection.scalar(text("SELECT to_regclass('crafting_receipts')")) is None
        await connection.run_sync(lambda sync: _migrate(sync, "head"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261002_0017"
        )
