from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import text

from alembic import command


def _run_migration(sync_connection, revision, direction):
    config = Config("alembic.ini")
    config.attributes["connection"] = sync_connection
    getattr(command, direction)(config, revision)


@pytest.mark.asyncio
async def test_0006_backfills_only_completed_tutorial_knowledge(database):
    engine, _ = database
    character_id = uuid4()
    activity_id = uuid4()
    other_character_id = uuid4()
    other_activity_id = uuid4()
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: _run_migration(sync, "20260921_0005", "downgrade"))
        await connection.execute(
            text("INSERT INTO accounts (telegram_id) VALUES (:telegram_id), (:other_telegram_id)"),
            {"telegram_id": 990001, "other_telegram_id": 990002},
        )
        await connection.execute(
            text(
                "INSERT INTO characters "
                "(id, telegram_id, server_id, name, race, character_class, stage, "
                "ruleset_version, level, xp, hp, max_hp, vigor, max_vigor, crowns) "
                "VALUES (:id, 990001, 'ocaso', 'Heroa', 'remanescente', 'sentinela', "
                "'menu:ready', 'gdd-1.4.3-baseline-1.0', 1, 0, 702, 702, 100, 100, 0), "
                "(:other_id, 990002, 'ocaso', 'Herob', 'remanescente', 'sentinela', "
                "'menu:ready', 'gdd-1.4.3-baseline-1.0', 1, 0, 702, 702, 100, 100, 0)"
            ),
            {"id": character_id, "other_id": other_character_id},
        )
        await connection.execute(
            text(
                "INSERT INTO game_activities "
                "(id, character_id, content_id, status, state_version, ruleset_version) "
                "VALUES (:id, :character_id, 'prologue_first_combat', 'completed', 1, "
                "'gdd-1.4.3-baseline-1.0'), "
                "(:other_id, :other_character_id, 'prologue_first_combat', 'active', 0, "
                "'gdd-1.4.3-baseline-1.0')"
            ),
            {
                "id": activity_id,
                "character_id": character_id,
                "other_id": other_activity_id,
                "other_character_id": other_character_id,
            },
        )
        await connection.run_sync(lambda sync: _run_migration(sync, "head", "upgrade"))
        rows = (
            await connection.execute(
                text(
                    "SELECT character_id, bkp, stage FROM bestiary_entries "
                    "WHERE creature_id='dog_cinereo' ORDER BY character_id"
                )
            )
        ).all()
        evidence = (
            await connection.execute(
                text(
                    "SELECT evidence_id FROM bestiary_evidence "
                    "WHERE character_id=:character_id ORDER BY evidence_id"
                ),
                {"character_id": character_id},
            )
        ).scalars().all()
    assert rows == [(character_id, 7, "observed")]
    assert evidence == ["first_combat", "first_observation"]
