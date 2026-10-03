"""Shared name availability and serialization for creation and renames."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.infrastructure.db.models import Character, CharacterNameReservation


def utc_now() -> datetime:
    return datetime.now(UTC)


async def lock_character_name(session: AsyncSession, server_id: str, name: str) -> None:
    """Serialize name claims across creation and rename transactions."""
    lock_key = f"character-name:{server_id}:{name.casefold()}".encode()
    signed_key = int.from_bytes(hashlib.sha256(lock_key).digest()[:8], "big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": signed_key})


async def name_available(
    session: AsyncSession,
    *,
    server_id: str,
    name: str,
    now: datetime | None = None,
    except_character_id: UUID | None = None,
) -> bool:
    now = now or utc_now()
    character_query = select(Character.id).where(
        Character.server_id == server_id,
        func.lower(Character.name) == name.lower(),
    )
    if except_character_id is not None:
        character_query = character_query.where(Character.id != except_character_id)
    if await session.scalar(character_query.limit(1)) is not None:
        return False
    return (
        await session.scalar(
            select(CharacterNameReservation.normalized_name).where(
                CharacterNameReservation.server_id == server_id,
                CharacterNameReservation.normalized_name == name.casefold(),
                CharacterNameReservation.reserved_until > now,
            )
        )
        is None
    )
