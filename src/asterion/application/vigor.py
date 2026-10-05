"""Server-authoritative continuous character Vigor regeneration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.infrastructure.db.models import Character

REGEN_INTERVAL_SECONDS = 14 * 60 + 24


def utcnow() -> datetime:
    """Clock boundary kept replaceable for deterministic service tests."""
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def reconcile_vigor_state(character: Character, *, now: datetime | None = None) -> int:
    """Apply elapsed regeneration to an already locked Character row.

    Partial time is carried forward while below cap. Time spent at cap and
    future-skewed anchors are discarded so they can never bank Vigor.
    The caller must hold a row lock before persisting this mutation.
    """
    current_time = _aware(now or utcnow())
    anchor = character.vigor_regen_at
    if anchor is None:
        # Defensive compatibility for transient instances created outside ORM
        # defaults; persisted rows are NOT NULL after migration 0021.
        character.vigor_regen_at = current_time
        return 0

    anchor = _aware(anchor)
    vigor = max(0, min(int(character.vigor), int(character.max_vigor)))
    character.vigor = vigor

    if vigor >= character.max_vigor:
        character.vigor_regen_at = current_time
        return 0

    if anchor > current_time:
        character.vigor_regen_at = current_time
        return 0

    elapsed_seconds = (current_time - anchor).total_seconds()
    ticks = int(elapsed_seconds // REGEN_INTERVAL_SECONDS)
    if ticks <= 0:
        return 0

    gained = min(ticks, int(character.max_vigor) - vigor)
    character.vigor = vigor + gained
    if character.vigor >= character.max_vigor:
        # Reaching cap discards excess elapsed ticks and fractional time.
        character.vigor_regen_at = current_time
    else:
        # Carry only the sub-interval remainder into the next window.
        character.vigor_regen_at = anchor + timedelta(seconds=ticks * REGEN_INTERVAL_SECONDS)
    return gained


def add_vigor_state(character: Character, amount: int, *, now: datetime | None = None) -> int:
    """Apply a non-regeneration Vigor gain after natural reconciliation."""
    if amount <= 0:
        return 0
    current_time = _aware(now or utcnow())
    before = int(character.vigor)
    character.vigor = min(int(character.max_vigor), before + int(amount))
    gained = character.vigor - before
    if character.vigor >= character.max_vigor:
        # A potion/refund that reaches cap cannot leave old time banked.
        character.vigor_regen_at = current_time
    return gained


async def reconcile_character_vigor(
    session: AsyncSession,
    character: Character,
    *,
    now: datetime | None = None,
) -> int:
    """Lock the character and reconcile Vigor exactly once transactionally."""
    locked = await session.scalar(
        select(Character)
        .where(Character.id == character.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if locked is None:
        return 0
    return reconcile_vigor_state(locked, now=now)