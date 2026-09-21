# ruff: noqa: E501
import pytest
from alembic.config import Config
from sqlalchemy import text

from alembic import command


def _migrate(connection, revision):
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    command.upgrade(config, revision)


def _downgrade(connection, revision):
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    command.downgrade(config, revision)


@pytest.mark.asyncio
async def test_real_0004_0005_backfill_and_safe_roundtrip(database):
    engine, _ = database
    async with engine.begin() as connection:
        await connection.run_sync(lambda c: _downgrade(c, "20260920_0004"))
        await connection.execute(text("INSERT INTO accounts (telegram_id) VALUES (981001)"))
        await connection.execute(
            text("""
            INSERT INTO characters
              (id, telegram_id, server_id, name, race, character_class, stage, ruleset_version,
               level, xp, hp, max_hp, vigor, max_vigor)
            VALUES ('00000000-0000-0000-0000-000000000501', 981001, 'ocaso', 'Legacy',
                    'remanescente', 'sentinela', 'cinzas_na_estrada:ready_for_first_brazier',
                    'gdd-1.4.2-baseline-1.0', 1, 320, 702, 702, 100, 100)
        """)
        )
        await connection.execute(
            text("""
            INSERT INTO braziers (id, character_id, brazier_id)
            VALUES ('00000000-0000-0000-0000-000000000505',
                    '00000000-0000-0000-0000-000000000501', 'tdo.brazier.estrada')
        """)
        )
        await connection.execute(
            text("""
            INSERT INTO world_states (character_id, region, location)
            VALUES ('00000000-0000-0000-0000-000000000501', 'Terras do Ocaso', 'Estrada das Cinzas')
        """)
        )
        await connection.execute(
            text("""
            INSERT INTO achievements (id, character_id, achievement_id)
            VALUES ('00000000-0000-0000-0000-000000000506',
                    '00000000-0000-0000-0000-000000000501', 'feat.tdo.cinzas_na_estrada')
        """)
        )
        await connection.execute(
            text("""
            INSERT INTO quests (id, character_id, quest_id, title, status, step, content_version)
            VALUES ('00000000-0000-0000-0000-000000000502', '00000000-0000-0000-0000-000000000501',
                    'P1', 'Vozes na Estrada', 'active', 1, 'tdo-1.0.1')
        """)
        )
        await connection.run_sync(lambda c: _migrate(c, "head"))
        row = (
            await connection.execute(
                text("SELECT ruleset_version FROM characters WHERE telegram_id=981001")
            )
        ).scalar_one()
        assert row == "gdd-1.4.2-baseline-1.0" or row == "gdd-1.4.3-baseline-1.0"
        assert (
            await connection.execute(
                text(
                    "SELECT content_version FROM quests WHERE quest_id='P1' AND character_id='00000000-0000-0000-0000-000000000501'"
                )
            )
        ).scalar_one() == "tdo-1.0.2"
        assert (
            await connection.execute(
                text(
                    "SELECT count(*) FROM location_discoveries WHERE character_id='00000000-0000-0000-0000-000000000501' AND location_id='tdo.location.estrada_das_cinzas'"
                )
            )
        ).scalar_one() == 1
        await connection.run_sync(lambda c: _downgrade(c, "20260920_0004"))
        assert (
            await connection.execute(text("SELECT content_version FROM quests WHERE quest_id='P1'"))
        ).scalar_one() == "tdo-1.0.1"
        await connection.run_sync(lambda c: _migrate(c, "head"))


@pytest.mark.asyncio
async def test_real_0005_rejects_incompatible_p1(database):
    engine, _ = database
    async with engine.begin() as connection:
        await connection.run_sync(lambda c: _downgrade(c, "20260920_0004"))
        await connection.execute(text("INSERT INTO accounts (telegram_id) VALUES (981002)"))
        await connection.execute(
            text("""
            INSERT INTO characters
              (id, telegram_id, server_id, name, race, character_class, stage, ruleset_version,
               level, xp, hp, max_hp, vigor, max_vigor)
            VALUES ('00000000-0000-0000-0000-000000000503', 981002, 'ocaso', 'Legacytwo',
                    'remanescente', 'sentinela', 'menu:ready', 'gdd-1.4.2-baseline-1.0',
                    1, 320, 702, 702, 100, 100)
        """)
        )
        await connection.execute(
            text("""
            INSERT INTO quests (id, character_id, quest_id, title, status, step, content_version)
            VALUES ('00000000-0000-0000-0000-000000000504', '00000000-0000-0000-0000-000000000503',
                    'P1', 'Vozes na Estrada', 'active', 2, 'tdo-1.0.1')
        """)
        )
        with pytest.raises(Exception, match="Cannot migrate incompatible P1 state"):
            await connection.run_sync(lambda c: _migrate(c, "head"))
