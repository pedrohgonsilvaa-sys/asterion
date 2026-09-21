from decimal import Decimal
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import text

from alembic import command


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
        assert row.ruleset_version == "gdd-1.4.2-baseline-1.0"
