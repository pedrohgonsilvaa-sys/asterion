"""PostgreSQL migration and constraint checks for equippable EquipmentItems."""

import json
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
async def schema_at_0009():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run real PostgreSQL migration tests")

    schema = "test_equipment_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20260924_0009"))
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


async def _column_exists(connection, table: str, column: str) -> bool:
    return bool(
        await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_schema=current_schema() AND table_name=:table "
                "AND column_name=:column)"
            ),
            {"table": table, "column": column},
        )
    )


async def _table_exists(connection, table: str) -> bool:
    return bool(
        await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema=current_schema() AND table_name=:table)"
            ),
            {"table": table},
        )
    )


@pytest.mark.asyncio
async def test_0009_equipment_upgrade_constraints_safe_downgrade_and_reupgrade(
    schema_at_0009,
):
    engine = schema_at_0009
    actor = 907201
    character_id = uuid4()
    equipment_id = uuid4()
    second_equipment_id = uuid4()
    source_key = "migration:equipment:stable"

    async with engine.begin() as connection:
        assert not await _column_exists(
            connection, "characters", "combat_configuration_version"
        )
        assert not await _table_exists(connection, "character_equipment_slots")
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:actor)"), {"actor": actor}
        )
        await connection.execute(
            text(
                "INSERT INTO characters (id, telegram_id, server_id, name, race, "
                "character_class, stage, ruleset_version, level, xp, hp, max_hp, vigor, "
                "max_vigor, crowns) VALUES (:id, :actor, 'ocaso', 'Migrate', "
                "'remanescente', 'sentinela', 'menu:ready', 'gdd-1.4.6-baseline-1.0', "
                "7, 120, 702, 702, 100, 100, 0)"
            ),
            {"id": character_id, "actor": actor},
        )
        await connection.execute(
            text(
                "INSERT INTO equipment_items (id, character_id, source_key, item_name, "
                "rarity, slot, item_level, bound, payload) VALUES (:id, :character_id, "
                ":source_key, 'Arma Pesada', 'Raro', '2H', 7, false, CAST(:payload AS jsonb))"
            ),
            {
                "id": equipment_id,
                "character_id": character_id,
                "source_key": source_key,
                "payload": json.dumps({"slot": "2H", "item_name": "Arma Pesada"}),
            },
        )
        await connection.execute(
            text(
                "INSERT INTO equipment_items (id, character_id, source_key, item_name, "
                "rarity, slot, item_level, bound, payload) VALUES (:id, :character_id, "
                ":source_key, 'Elmo', 'Comum', 'Cabeça', 1, false, CAST(:payload AS jsonb))"
            ),
            {
                "id": second_equipment_id,
                "character_id": character_id,
                "source_key": "migration:equipment:second",
                "payload": json.dumps({"slot": "Cabeça", "item_name": "Elmo"}),
            },
        )
        await connection.run_sync(lambda sync: _migrate(sync, "head"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261002_0017"
        )
        assert await _column_exists(
            connection, "characters", "combat_configuration_version"
        )
        assert await _table_exists(connection, "character_equipment_slots")
        assert await connection.scalar(
            text("SELECT combat_configuration_version FROM characters WHERE id=:id"),
            {"id": character_id},
        ) == 0
        assert await connection.scalar(
            text("SELECT id FROM equipment_items WHERE source_key=:source_key"),
            {"source_key": source_key},
        ) == equipment_id
        constraints = set(
            (
                await connection.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conrelid='character_equipment_slots'::regclass"
                    )
                )
            ).scalars()
        )
        assert constraints == {
            "ck_character_equipment_slots_slot",
            "fk_character_equipment_slots_character_id_characters",
            "fk_character_equipment_slots_equipment_item_id_equipment_items",
            "pk_character_equipment_slots",
            "uq_equipment_slot_item",
        }

    slot_values = {
        "character_id": character_id,
        "slot": "Principal",
        "equipment_item_id": equipment_id,
    }
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO character_equipment_slots "
                "(character_id, slot, equipment_item_id) "
                "VALUES (:character_id, :slot, :equipment_item_id)"
            ),
            slot_values,
        )
    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO character_equipment_slots "
                    "(character_id, slot, equipment_item_id) "
                    "VALUES (:character_id, 'Cabeça', :equipment_item_id)"
                ),
                {
                    "character_id": character_id,
                    "equipment_item_id": equipment_id,
                },
            )
    with pytest.raises(IntegrityError):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO character_equipment_slots "
                    "(character_id, slot, equipment_item_id) "
                    "VALUES (:character_id, '2H', :equipment_item_id)"
                ),
                {
                    "character_id": character_id,
                    "equipment_item_id": second_equipment_id,
                },
            )

    with pytest.raises(RuntimeError, match="Cannot downgrade while characters have equipped"):
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20260924_0009", "downgrade"))
    async with engine.begin() as connection:
        assert await connection.scalar(
            text("SELECT equipment_item_id FROM character_equipment_slots WHERE slot='Principal'")
        ) == equipment_id
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261002_0017"
        )
        await connection.execute(text("DELETE FROM character_equipment_slots"))
        await connection.run_sync(lambda sync: _migrate(sync, "20260924_0009", "downgrade"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260924_0009"
        )
        assert not await _column_exists(
            connection, "characters", "combat_configuration_version"
        )
        assert not await _table_exists(connection, "character_equipment_slots")
        assert await connection.scalar(
            text("SELECT id FROM equipment_items WHERE source_key=:source_key"),
            {"source_key": source_key},
        ) == equipment_id
        await connection.run_sync(lambda sync: _migrate(sync, "head"))
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20261002_0017"
        )
        assert await connection.scalar(
            text("SELECT combat_configuration_version FROM characters WHERE id=:id"),
            {"id": character_id},
        ) == 0
        assert await connection.scalar(
            text("SELECT id FROM equipment_items WHERE source_key=:source_key"),
            {"source_key": source_key},
        ) == equipment_id
