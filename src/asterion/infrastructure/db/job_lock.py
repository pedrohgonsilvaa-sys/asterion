"""Cluster-wide single execution of a scheduled job (GDD §43.6).

Each process runs its own APScheduler, so `max_instances=1` only holds per
process. `run_exclusive` takes a PostgreSQL advisory lock named after the job:
an instance that finds it taken skips that tick. The lock belongs to the
connection, so a crashed process releases it with its connection.
"""

from __future__ import annotations

import zlib
from collections.abc import Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine


def lock_key(job_id: str) -> int:
    return zlib.crc32(f"asterion-job:{job_id}".encode())


async def run_exclusive(
    engine: AsyncEngine, job_id: str, job: Callable[[], Awaitable[object]]
) -> object | None:
    """Run `job` unless another instance holds its lock. Returns None when skipped."""
    key = lock_key(job_id)
    async with engine.connect() as connection:
        if not await connection.scalar(select(func.pg_try_advisory_lock(key))):
            return None
        try:
            return await job()
        finally:
            await connection.scalar(select(func.pg_advisory_unlock(key)))
