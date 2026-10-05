import pytest
from alembic.config import Config
from sqlalchemy import select, text

from alembic import command
from asterion.infrastructure.db.models import Character
from tests.test_road_integration import _seed_road


@pytest.mark.asyncio
async def test_0021_upgrade_preserves_existing_vigor_and_backfills_anchor(database):
    actor = 772806
    _actor, _service = await _seed_road(database, actor=actor, vigor=24)
    engine, sessions = database

    async with engine.begin() as connection:
        def downgrade(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.downgrade(config, "20261003_0020")

        await connection.run_sync(downgrade)

    async with engine.connect() as connection:
        existing_vigor = await connection.scalar(
            text("SELECT vigor FROM characters WHERE telegram_id = :actor"),
            {"actor": actor},
        )
        assert existing_vigor == 24

    async with engine.begin() as connection:
        def upgrade(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.upgrade(config, "head")

        await connection.run_sync(upgrade)

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.vigor == 24
        assert character.vigor_regen_at is not None
        assert character.vigor_regen_at.tzinfo is not None