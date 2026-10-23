import os
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterDoctrine,
    CombatRecord,
    Encounter,
    GameActivity,
)


def _migrate(connection, revision: str, direction: str = "upgrade") -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    getattr(command, direction)(config, revision)


@pytest_asyncio.fixture
async def schema_at_0014():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run PostgreSQL migration tests")
    schema = "test_talents_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20260930_0014"))
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.mark.asyncio
async def test_0015_talent_choices_upgrade_legacy_defaults_and_safe_downgrade(schema_at_0014):
    engine = schema_at_0014
    actor = 772199
    character_id = uuid4()
    async with engine.begin() as connection:
        assert (
            await connection.scalar(
                text("SELECT to_regclass('character_talent_choices') IS NOT NULL")
            )
            is False
        )
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:actor)"), {"actor": actor}
        )
        await connection.execute(
            text(
                "INSERT INTO characters (id, telegram_id, server_id, name, race, "
                "character_class, stage, ruleset_version, level, xp, hp, max_hp, vigor, "
                "max_vigor, crowns, combat_configuration_version) VALUES (:id, :actor, "
                "'ocaso', 'Existing', 'remanescente', 'sentinela', 'menu:ready', 'test', "
                "10, 0, 1000, 1000, 71, 100, 0, 0)"
            ),
            {"id": character_id, "actor": actor},
        )
        await connection.run_sync(lambda sync: _migrate(sync, "20260930_0015"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260930_0015"
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM character_talent_choices WHERE character_id=:character_id"
                ),
                {"character_id": character_id},
            )
            == 0
        )
        await connection.execute(
            text(
                "INSERT INTO character_talent_choices (character_id, point_slot, talent_id) "
                "VALUES (:character_id, 1, 'talent.sentinela.aco_desperto')"
            ),
            {"character_id": character_id},
        )

    with pytest.raises(RuntimeError, match="Cannot downgrade while characters have Talent choices"):
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: _migrate(sync, "20260930_0014", direction="downgrade")
            )

    async with engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM character_talent_choices WHERE character_id=:character_id"),
            {"character_id": character_id},
        )
        await connection.run_sync(
            lambda sync: _migrate(sync, "20260930_0014", direction="downgrade")
        )
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260930_0014"
        )
        assert (
            await connection.scalar(
                text("SELECT to_regclass('character_talent_choices') IS NOT NULL")
            )
            is False
        )
        await connection.run_sync(lambda sync: _migrate(sync, "20260930_0015"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260930_0015"
        )


@pytest.mark.asyncio
async def test_0028_quarantines_pre_release_nv35_rows_and_frozen_talent_ids(database):
    engine, sessions = database
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync: _migrate(sync, "20261010_0027", direction="downgrade")
        )

    character_id = uuid4()
    activity_id = uuid4()
    encounter_id = uuid4()
    actor = 772298
    lower_id = "talent.sentinela.aco_desperto"
    closed_id = "talent.sentinela.olho_de_combate"
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Clegacy",
                race="remanescente",
                character_class="sentinela",
                selected_path="bastiao",
                stage="menu:ready",
                ruleset_version="test",
                level=40,
                xp=0,
                hp=1000,
                max_hp=1000,
            )
        )
        session.add(
            GameActivity(
                id=activity_id,
                character_id=character_id,
                content_id="c1-legacy-talent-snapshot",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
        await session.flush()
        session.add(Encounter(id=encounter_id, game_activity_id=activity_id))
        await session.flush()
        session.add(
            CombatRecord(
                encounter_id=encounter_id,
                snapshot={"fighters": {"player": {"talent_ids": [lower_id, closed_id]}}},
            )
        )
        session.add(
            CharacterDoctrine(
                character_id=character_id,
                name="Antes da abertura",
                configuration={
                    "path": "bastiao",
                    "equipment": {},
                    "arts": {},
                    "talents": [
                        {"point_slot": 1, "talent_id": lower_id},
                        {"point_slot": 7, "talent_id": closed_id},
                    ],
                },
            )
        )

    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO character_talent_choices (character_id, point_slot, talent_id) "
                "VALUES (:character_id, 1, :lower_id), (:character_id, 7, :closed_id)"
            ),
            {"character_id": character_id, "lower_id": lower_id, "closed_id": closed_id},
        )
        await connection.run_sync(lambda sync: _migrate(sync, "head"))

    async with sessions() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT talent_id, publicly_acquired FROM character_talent_choices "
                    "WHERE character_id=:character_id ORDER BY point_slot"
                ),
                {"character_id": character_id},
            )
        ).all()
        assert [(row.talent_id, row.publicly_acquired) for row in rows] == [
            (lower_id, True),
            (closed_id, False),
        ]
        doctrine = await session.scalar(
            text("SELECT configuration FROM character_doctrines WHERE character_id=:id"),
            {"id": character_id},
        )
        assert doctrine["talents"] == [{"point_slot": 1, "talent_id": lower_id}]
        combat = await session.scalar(
            text("SELECT snapshot FROM combats WHERE encounter_id=:id"),
            {"id": encounter_id},
        )
        assert combat["fighters"]["player"]["talent_ids"] == [lower_id]
