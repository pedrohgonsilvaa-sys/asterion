"""Transaction helpers for sharing objective evidence with present group members."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.infrastructure.db.models import (
    CampaignObjectiveCredit,
    Character,
    GameActivity,
    Quest,
    SocialGroup,
    SocialGroupMember,
    WorldState,
)


@dataclass(frozen=True, slots=True)
class PresentCampaignMember:
    character: Character
    quest: Quest
    world: WorldState


async def lock_campaign_roster(
    session: AsyncSession, character_id: UUID
) -> tuple[UUID | None, tuple[UUID, ...]]:
    """Lock group first, then characters in stable order for quest transactions."""
    membership = await session.scalar(
        select(SocialGroupMember).where(SocialGroupMember.character_id == character_id)
    )
    if membership is None:
        await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        return None, (character_id,)

    group = await session.scalar(
        select(SocialGroup)
        .where(SocialGroup.id == membership.group_id)
        .with_for_update()
    )
    membership = await session.scalar(
        select(SocialGroupMember)
        .where(SocialGroupMember.character_id == character_id)
        .with_for_update()
    )
    if (
        group is None
        or group.status != "active"
        or membership is None
        or membership.group_id != group.id
    ):
        await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        return None, (character_id,)

    character_ids = tuple(
        sorted(
            (
                await session.scalars(
                    select(SocialGroupMember.character_id).where(
                        SocialGroupMember.group_id == group.id
                    )
                )
            ).all()
        )
    )
    await session.scalars(
        select(Character)
        .where(Character.id.in_(character_ids))
        .order_by(Character.id)
        .with_for_update()
    )
    return group.id, character_ids


async def campaign_roster_ids(
    session: AsyncSession, character_id: UUID
) -> tuple[UUID, ...]:
    """Return the roster after lock_campaign_roster has serialized membership changes."""
    membership = await session.scalar(
        select(SocialGroupMember).where(SocialGroupMember.character_id == character_id)
    )
    if membership is None:
        return (character_id,)
    group = await session.get(SocialGroup, membership.group_id)
    if group is None or group.status != "active":
        return (character_id,)
    return tuple(
        sorted(
            (
                await session.scalars(
                    select(SocialGroupMember.character_id).where(
                        SocialGroupMember.group_id == group.id
                    )
                )
            ).all()
        )
    )


async def present_campaign_members(
    session: AsyncSession,
    *,
    character_ids: tuple[UUID, ...],
    quest_id: str,
    content_version: str,
    step: int,
    region: str,
    location: str,
) -> tuple[PresentCampaignMember, ...]:
    """Select only active, same-checkpoint members physically present at the objective."""
    rows = list(
        (
            await session.execute(
                select(Character, Quest, WorldState)
                .join(Quest, Quest.character_id == Character.id)
                .join(WorldState, WorldState.character_id == Character.id)
                .where(
                    Character.id.in_(character_ids),
                    Quest.quest_id == quest_id,
                    Quest.content_version == content_version,
                    Quest.status == "active",
                    Quest.step == step,
                    WorldState.region == region,
                    WorldState.location == location,
                )
                .order_by(Character.id)
                .with_for_update()
            )
        ).all()
    )
    active_ids = set(
        (
            await session.scalars(
                select(GameActivity.character_id).where(
                    GameActivity.character_id.in_(character_ids),
                    GameActivity.status == "active",
                )
            )
        ).all()
    )
    return tuple(
        PresentCampaignMember(character, quest, world)
        for character, quest, world in rows
        if character.id not in active_ids
    )


async def record_campaign_objective_credit(
    session: AsyncSession,
    *,
    character_id: UUID,
    quest_id: str,
    objective_id: str,
    source_key: str,
    evidence: dict,
) -> None:
    """Persist one idempotent, per-character record of shared objective evidence."""
    existing = await session.scalar(
        select(CampaignObjectiveCredit.id).where(
            CampaignObjectiveCredit.character_id == character_id,
            CampaignObjectiveCredit.quest_id == quest_id,
            CampaignObjectiveCredit.objective_id == objective_id,
            CampaignObjectiveCredit.source_key == source_key,
        )
    )
    if existing is None:
        session.add(
            CampaignObjectiveCredit(
                id=uuid4(),
                character_id=character_id,
                quest_id=quest_id,
                objective_id=objective_id,
                source_key=source_key,
                evidence=evidence,
            )
        )
