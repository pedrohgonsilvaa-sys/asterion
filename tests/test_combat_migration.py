from decimal import Decimal
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import text

from alembic import command
from asterion.application.world import WorldService
from tests.test_prologue_persistence import character as seed_character


async def test_v142_migration_adopts_intro_character_and_is_reversible(database):
    engine = database[0]
    async with engine.begin() as connection:

        def downgrade(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.downgrade(config, "20260920_0002")

        await connection.run_sync(downgrade)
        actor = 998877665544
        character_id = uuid4()
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:actor)"),
            {
                "actor": actor,
            },
        )
        await connection.execute(
            text("""
            INSERT INTO characters (
                id, telegram_id, server_id, name, race, character_class,
                stage, ruleset_version
            ) VALUES (
                :id, :actor, 'ocaso', 'Migrado', 'remanescente', 'sentinela',
                'cinzas_na_estrada:intro', 'gdd-1.4.1-baseline-1.0'
            )
        """),
            {"id": character_id, "actor": actor},
        )

        def upgrade(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.upgrade(config, "head")
            command.check(config)

        await connection.run_sync(upgrade)
        row = (
            await connection.execute(
                text("""
            SELECT level, xp, hp, max_hp, ruleset_version FROM characters WHERE id = :id
        """),
                {"id": character_id},
            )
        ).one()
        assert row.level == 1 and row.xp == 0
        assert row.hp == row.max_hp == Decimal("712.530")
        assert row.ruleset_version == "gdd-1.4.3-baseline-1.0"


async def test_ready_brazier_legacy_backfill_then_rest(database):
    engine, sessions = database
    async with engine.begin() as connection:

        def downgrade(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.downgrade(config, "20260920_0003")

        await connection.run_sync(downgrade)
        actor, character_id = 998877665545, uuid4()
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:actor)"), {"actor": actor}
        )
        await connection.execute(
            text("""
            INSERT INTO characters (id, telegram_id, server_id, name, race, character_class,
                stage, ruleset_version, level, xp, hp, max_hp)
            VALUES (:id, :actor, 'ocaso', 'Legado', 'remanescente', 'sentinela',
                'cinzas_na_estrada:ready_for_first_brazier',
                'gdd-1.4.2-baseline-1.0', 1, 320, 700, 712.530)
        """),
            {"id": character_id, "actor": actor},
        )

        def upgrade(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.upgrade(config, "head")

        await connection.run_sync(upgrade)
        row = (
            await connection.execute(
                text("SELECT ruleset_version FROM characters WHERE id=:id"), {"id": character_id}
            )
        ).one()
        assert row.ruleset_version == "gdd-1.4.3-baseline-1.0"
        assert (
            await connection.execute(
                text("SELECT count(*) FROM braziers WHERE character_id=:id"), {"id": character_id}
            )
        ).scalar() == 1
        assert (
            await connection.execute(
                text("SELECT count(*) FROM world_states WHERE character_id=:id"),
                {"id": character_id},
            )
        ).scalar() == 1
        assert (
            await connection.execute(
                text("SELECT count(*) FROM achievements WHERE character_id=:id"),
                {"id": character_id},
            )
        ).scalar() == 0
        assert (
            await connection.execute(
                text("SELECT count(*) FROM quests WHERE character_id=:id"), {"id": character_id}
            )
        ).scalar() == 0
    world = WorldService(sessions, "ocaso")
    view = await world.resume(actor)
    assert view is not None and view.kind == "brazier"
    menu = await world.rest(actor)
    assert menu is not None and menu.kind == "menu"
    async with sessions() as session:
        assert (
            await session.execute(
                text("SELECT count(*) FROM achievements WHERE character_id=:id"),
                {"id": character_id},
            )
        ).scalar() == 1
        assert (
            await session.execute(
                text("SELECT count(*) FROM quests WHERE character_id=:id"), {"id": character_id}
            )
        ).scalar() == 1


async def test_brazier_migration_downgrade_blocks_populated_state(database):
    await seed_character(database)
    engine = database[0]
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO braziers (id, character_id, brazier_id) "
                "SELECT gen_random_uuid(), id, 'tdo.brazier.estrada' "
                "FROM characters LIMIT 1"
            )
        )

        def downgrade(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.downgrade(config, "20260920_0003")

        try:
            await connection.run_sync(downgrade)
        except RuntimeError as exc:
            assert str(exc) == "Cannot downgrade populated brazier/menu state"
        else:
            raise AssertionError("populated brazier state must block downgrade")
        assert (await connection.execute(text("SELECT count(*) FROM braziers"))).scalar() == 1
