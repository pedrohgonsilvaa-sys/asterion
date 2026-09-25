"""Transactional guard for future combat-configuration mutations."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.infrastructure.db.models import Character, GameActivity, HuntRound

HUNT_ROUND_CONFIGURATION_LOCK_STATUSES = ("active", "interrupted")


@dataclass(frozen=True, slots=True)
class CombatConfigurationBlocker:
    """Minimal authoritative activity metadata for a rejected mutation."""

    kind: Literal["foreground_activity", "hunt_round"]
    id: UUID
    status: str
    content_id: str | None = None


class CombatConfigurationLocked(RuntimeError):
    """Raised when an authoritative foreground activity owns the configuration lock."""

    def __init__(self, blocker: CombatConfigurationBlocker) -> None:
        self.blocker = blocker
        super().__init__("Combat configuration is locked by an authoritative activity.")


async def lock_for_combat_configuration_mutation(
    session: AsyncSession, character_id: UUID
) -> Character | None:
    """Lock a character and reject if its persisted state owns a configuration lock.

    Call inside the caller's transaction, before validating or changing any combat
    configuration. The returned Character row remains locked until that transaction
    ends. Activity creators must serialize on the same row before establishing a new
    foreground activity. Child activity rows are deliberately read without row locks:
    Character is the first lock in the current activity-start paths.

    Returns ``None`` if the character no longer exists. A blocker raises
    ``CombatConfigurationLocked`` with internal, non-player-facing metadata.
    """
    if not session.in_transaction():
        raise RuntimeError("Combat configuration guard requires an open transaction.")

    character = await session.scalar(
        select(Character)
        .where(Character.id == character_id)
        .with_for_update()
    )
    if character is None:
        return None

    activity = await session.scalar(
        select(GameActivity)
        .where(
            GameActivity.character_id == character.id,
            GameActivity.status == "active",
        )
        .limit(1)
    )
    if activity is not None:
        raise CombatConfigurationLocked(
            CombatConfigurationBlocker(
                kind="foreground_activity",
                id=activity.id,
                status=activity.status,
                content_id=activity.content_id,
            )
        )

    # Ronda may retain its configuration lock at an interruption boundary after
    # its generic foreground row has been completed (for example, before an Elite).
    # ``preparing`` is intentionally not included: no batch has been validly started.
    hunt_round = await session.scalar(
        select(HuntRound)
        .where(
            HuntRound.character_id == character.id,
            HuntRound.status.in_(HUNT_ROUND_CONFIGURATION_LOCK_STATUSES),
        )
        .limit(1)
    )
    if hunt_round is not None:
        raise CombatConfigurationLocked(
            CombatConfigurationBlocker(
                kind="hunt_round",
                id=hunt_round.id,
                status=hunt_round.status,
            )
        )

    return character
