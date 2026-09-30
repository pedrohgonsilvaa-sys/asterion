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
async def schema_at_0012():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run real PostgreSQL migration tests")
    schema = "test_active_arts_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20260929_0012"))
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.mark.asyncio
async def test_0013_active_art_slots_constraints_and_safe_downgrade(schema_at_0012):
    engine = schema_at_0012
    actor = 771100
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
                "(:id, :actor, 'ocaso', 'Artmigration', 'remanescente', 'sentinela', "
                "'menu:ready', 'gdd-1.4.7-baseline-1.0', 10, 0, 1000, 1000, 100, 100, 0, 0)"
            ),
            {"id": character_id, "actor": actor},
        )
        await connection.run_sync(lambda sync: _migrate(sync, "20260929_0013"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260929_0013"
        )
        constraints = set(
            (
                await connection.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conrelid='character_active_art_slots'::regclass"
                    )
                )
            ).scalars()
        )
        assert constraints == {
            "ck_character_active_art_slot",
            "fk_character_active_art_slots_character_id_characters",
            "pk_character_active_art_slots",
            "uq_character_active_art",
        }
        await connection.execute(
            text(
                "INSERT INTO character_active_art_slots (character_id, slot, art_id) "
                "VALUES (:character_id, 1, 'class_art.sentinela.golpe_de_guarda')"
            ),
            {"character_id": character_id},
        )

    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO character_active_art_slots (character_id, slot, art_id) "
                    "VALUES (:character_id, 4, 'class_art.sentinela.quebra_postura')"
                ),
                {"character_id": character_id},
            )

    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO character_active_art_slots (character_id, slot, art_id) "
                    "VALUES (:character_id, 2, 'class_art.sentinela.golpe_de_guarda')"
                ),
                {"character_id": character_id},
            )

    with pytest.raises(RuntimeError, match="Cannot downgrade while characters have equipped"):
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: _migrate(sync, "20260929_0012", direction="downgrade")
            )

    async with engine.begin() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260929_0013"
        )
        await connection.execute(text("DELETE FROM character_active_art_slots"))
        await connection.run_sync(
            lambda sync: _migrate(sync, "20260929_0012", direction="downgrade")
        )
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260929_0012"
        )
