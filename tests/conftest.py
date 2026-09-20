"""PostgreSQL integration tests use isolated, randomly named schemas."""

import os
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from asterion.application.creation import CreationService


@pytest_asyncio.fixture
async def database():
    url = os.environ.get("ASTERION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ASTERION_TEST_DATABASE_URL to run real PostgreSQL integration tests")
    schema = "test_creation_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:

            def migrate(sync_connection):
                config = Config("alembic.ini")
                config.attributes["connection"] = sync_connection
                command.upgrade(config, "head")

            await connection.run_sync(migrate)
        yield engine, async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.fixture
def service(database):
    return CreationService(database[1], "ocaso")
