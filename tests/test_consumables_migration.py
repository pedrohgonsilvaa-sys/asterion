"""Physical compatibility checks for migration 20260924_0009 on PostgreSQL."""

import os
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from asterion.application.inventory import InventoryService


def _migrate(sync_connection, revision: str, direction: str = "upgrade") -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = sync_connection
    getattr(command, direction)(config, revision)


@pytest_asyncio.fixture
async def schema_at_0008():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run real PostgreSQL migration tests")

    schema = "test_consumables_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda sync: _migrate(sync, "20260923_0008"))
        yield engine, async_sessionmaker(engine, expire_on_commit=False), schema
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
                "WHERE table_schema = current_schema() AND table_name = :table "
                "AND column_name = :column)"
            ),
            {"table": table, "column": column},
        )
    )


async def _stock_constraints(connection) -> set[str]:
    rows = await connection.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'consumable_stacks'::regclass ORDER BY conname"
        )
    )
    return set(rows.scalars())


async def _stock_rows(connection, character_id) -> list[tuple[str, int]]:
    rows = await connection.execute(
        text(
            "SELECT consumable_id, quantity FROM consumable_stacks "
            "WHERE character_id=:character_id ORDER BY consumable_id"
        ),
        {"character_id": character_id},
    )
    return list(rows.tuples())


async def _current_revision(connection) -> str:
    return await connection.scalar(text("SELECT version_num FROM alembic_version"))


@pytest.mark.asyncio
async def test_0008_stock_survives_global_consumables_upgrade_downgrade_and_reupgrade(
    schema_at_0008,
):
    engine, sessions, _ = schema_at_0008
    character_id = uuid4()
    actor = 887766554401
    expected_stock = [
        ("consumable.heal", 4),
        ("consumable.legacy.zero", 0),
        ("consumable.purification", 2),
    ]

    async with engine.begin() as connection:
        assert await _column_exists(connection, "characters", "tracked_secondary_quest_id")
        assert not await _column_exists(connection, "characters", "vigor_consumable_cycle")
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:actor)"), {"actor": actor}
        )
        await connection.execute(
            text(
                "INSERT INTO characters (id, telegram_id, server_id, name, race, "
                "character_class, stage, ruleset_version, level, xp, hp, max_hp, vigor, "
                "max_vigor, crowns) VALUES (:id, :actor, 'ocaso', 'Migrado', 'remanescente', "
                "'sentinela', 'menu:ready', 'gdd-1.4.6-baseline-1.0', 1, 0, 702, 702, "
                "100, 100, 0)"
            ),
            {"id": character_id, "actor": actor},
        )
        for item_id, quantity in expected_stock:
            await connection.execute(
                text(
                    "INSERT INTO consumable_stacks "
                    "(id, character_id, consumable_id, quantity) "
                    "VALUES (:id, :character_id, :item_id, :quantity)"
                ),
                {
                    "id": uuid4(),
                    "character_id": character_id,
                    "item_id": item_id,
                    "quantity": quantity,
                },
            )
        assert await _stock_rows(connection, character_id) == expected_stock
        assert await _stock_constraints(connection) == {
            "ck_consumable_quantity",
            "consumable_stacks_pkey",
            "uq_character_consumable",
            "consumable_stacks_character_id_fkey",
        }
        await connection.run_sync(lambda sync: _migrate(sync, "20260924_0009"))
        assert await _current_revision(connection) == "20260924_0009"
        assert await _column_exists(connection, "characters", "vigor_consumable_cycle")
        assert await _stock_rows(connection, character_id) == expected_stock
        assert await _stock_constraints(connection) == {
            "ck_consumable_quantity",
            "consumable_stacks_pkey",
            "uq_character_consumable",
            "consumable_stacks_character_id_fkey",
        }

    view = await InventoryService(sessions, "ocaso").category(actor, "consumables")
    assert view is not None
    assert [(item.key, item.quantity) for item in view.entries] == [
        ("consumable.heal", 4),
        ("consumable.purification", 2),
    ]
    assert [item.title for item in view.entries] == [
        "Poção de Cura",
        "Preparado de Purificação",
    ]

    downgrade_sql = []

    def capture_sql(_connection, _cursor, statement, _parameters, _context, _executemany):
        downgrade_sql.append(statement.lower())

    event.listen(engine.sync_engine, "before_cursor_execute", capture_sql)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: _migrate(sync, "20260923_0008", direction="downgrade")
            )
            assert await _current_revision(connection) == "20260923_0008"
            assert await _column_exists(connection, "consumable_stacks", "quantity")
            assert not await _column_exists(connection, "characters", "vigor_consumable_cycle")
            assert await _stock_rows(connection, character_id) == expected_stock
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_sql)

    lock_index = next(
        index for index, statement in enumerate(downgrade_sql)
        if "lock table characters in share row exclusive mode" in statement
    )
    preflight_index = next(
        index for index, statement in enumerate(downgrade_sql)
        if "vigor_consumable_cycle is not null" in statement
    )
    assert lock_index < preflight_index

    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: _migrate(sync, "20260924_0009"))
        assert await _current_revision(connection) == "20260924_0009"
        assert await _stock_rows(connection, character_id) == expected_stock
        await connection.execute(
            text(
                "UPDATE characters SET vigor_consumable_cycle = DATE '2026-09-24' WHERE id=:id"
            ),
            {"id": character_id},
        )

    with pytest.raises(RuntimeError, match="Cannot downgrade used Vigor Consumable cycle state"):
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: _migrate(sync, "20260923_0008", direction="downgrade")
            )

    async with engine.connect() as connection:
        assert await _current_revision(connection) == "20260924_0009"
        assert await _column_exists(connection, "characters", "vigor_consumable_cycle")
        assert await _stock_rows(connection, character_id) == expected_stock
        cycle = await connection.scalar(
            text("SELECT vigor_consumable_cycle FROM characters WHERE id=:id"),
            {"id": character_id},
        )
        assert str(cycle) == "2026-09-24"

    async with engine.connect() as migration_lock:
        lock_transaction = await migration_lock.begin()
        try:
            await migration_lock.execute(
                text("LOCK TABLE characters IN SHARE ROW EXCLUSIVE MODE")
            )
            async with engine.connect() as writer:
                writer_transaction = await writer.begin()
                try:
                    await writer.execute(text("SET LOCAL lock_timeout = '100ms'"))
                    with pytest.raises(DBAPIError):
                        await writer.execute(
                            text("UPDATE characters SET vigor=vigor WHERE id=:id"),
                            {"id": character_id},
                        )
                finally:
                    await writer_transaction.rollback()
        finally:
            await lock_transaction.rollback()

    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE characters SET vigor=vigor WHERE id=:id"), {"id": character_id}
        )
