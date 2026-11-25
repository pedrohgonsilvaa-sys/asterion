"""PostgreSQL integration tests use isolated, randomly named schemas."""

import asyncio
import os
import sys
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command

from asterion.application.creation import CreationService

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def pytest_collection_modifyitems(items):
    """Run each CI shard on a deterministic subset of test files."""
    total = int(os.environ.get("ASTERION_TEST_SHARDS", "1"))
    shard = int(os.environ.get("ASTERION_TEST_SHARD", "1"))
    if total <= 1:
        return
    if not 1 <= shard <= total:
        raise pytest.UsageError(
            f"ASTERION_TEST_SHARD must be between 1 and {total}, got {shard}"
        )

    groups = {}
    for item in items:
        groups.setdefault(str(item.path), []).append(item)

    shard_paths = [set() for _ in range(total)]
    shard_sizes = [0] * total

    for path, group in sorted(groups.items(), key=lambda pair: -len(pair[1])):
        target = min(range(total), key=lambda index: shard_sizes[index])
        shard_paths[target].add(path)
        shard_sizes[target] += len(group)

    selected = []
    deselected = []
    for item in items:
        if str(item.path) in shard_paths[shard - 1]:
            selected.append(item)
        else:
            deselected.append(item)

    items[:] = selected
    if deselected:
        item.config.hook.pytest_deselected(items=deselected)


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
        if os.getenv("ASTERION_TEST_PRESERVE_SCHEMA") == "1":
            print(f"TEST_SCHEMA_PRESERVED={schema}", flush=True)
        else:
            async with admin.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest.fixture
def service(database):
    return CreationService(database[1], "ocaso")


@pytest.fixture(autouse=True)
def _deterministic_prologue_enemy(monkeypatch):
    """The prologue draws Cão or Corvo; tests pin the Cão unless they override this."""
    monkeypatch.setattr("asterion.application.prologue.choose_enemy_id", lambda: "dog_cinereo")


@pytest.fixture(autouse=True)
def _frozen_turn_clock():
    """Combat turn deadlines follow a controllable clock; tests do not race 10 seconds."""
    from asterion.domain import turn_clock

    state = {"t": 1_000_000.0}
    turn_clock.set_clock(lambda: state["t"])
    yield state
    turn_clock.set_clock(None)
