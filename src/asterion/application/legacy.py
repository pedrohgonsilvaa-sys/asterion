"""Public, transactional first Legacy Ascension flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account import _has_foreground
from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.guild_battle_locks import character_roster_locked
from asterion.domain.legacy import legacy_xp_factor
from asterion.infrastructure.db.models import (
    Brazier,
    CampaignJourney,
    CampaignJourneyMember,
    CampaignObjectiveCredit,
    Character,
    CharacterEquipmentSlot,
    EquipmentItem,
    GroupActivityParticipant,
    GroupActivityProposal,
    LegacyAscensionConfirmation,
    LegacyAscensionRecord,
    PvpveQueue,
    PvpveQueueMember,
    Quest,
    RewardEvent,
    Unlock,
    WorldState,
)

P36_QUEST_ID = "P36"
P36_CAMPAIGN_UNLOCK = "unlock.campaign.first_journey_complete"
P36_CONTENT_VERSION = "confins-1.0.0"
P36_REWARD_SOURCE = "mission.confins.p36"
P36_COMPLETION_OBJECTIVE = "p36.completed"
P36_COMPLETION_SOURCE_PREFIX = "p36.completed:"
REFUGE = "Refúgio do Ocaso"
REFUGE_REGION = "Terras do Ocaso"
REFUGE_BRAZIER = "tdo.brazier.refugio_do_ocaso"
CONFIRMATION_LIFETIME = timedelta(minutes=10)


class LegacyReason(StrEnum):
    LEVEL_REQUIRED = "level_required"
    CAMPAIGN_REQUIRED = "campaign_required"
    SAFE_LOCATION_REQUIRED = "safe_location_required"
    ACTIVITY_LOCKED = "activity_locked"
    LEGACY_TRANSITION_UNDEFINED = "legacy_transition_undefined"


class LegacyActionRejected(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class LegacyView:
    character_name: str
    level: int
    xp: int
    legacy_level: int
    xp_factor: str
    configuration_version: int
    location: str | None
    campaign_complete: bool
    can_ascend: bool
    reasons: tuple[LegacyReason, ...]


@dataclass(frozen=True, slots=True)
class LegacyPreparation:
    view: LegacyView
    confirmation_key: UUID | None
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class LegacyResult:
    succeeded: bool
    reason: str | None
    legacy_level: int
    level: int
    xp: int
    location: str | None


class LegacyService:
    """Own the only public path for the first Ascension.

    Every mutation locks Character first, matching activity/configuration writers.
    The confirmation key is single-use, short-lived, and tied to the current
    combat-configuration version. Campaign completion is proven by the P36 Quest,
    canonical campaign unlock, and the idempotent P36 completion reward event.
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> LegacyView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view(session, character)

    async def prepare(
        self, actor: int, *, expected_configuration_version: int
    ) -> LegacyPreparation | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            if character.combat_configuration_version != expected_configuration_version:
                raise LegacyActionRejected("stale_configuration")
            view = await self._view(session, character)
            if not view.can_ascend:
                return LegacyPreparation(view, None, None)

            row = await session.scalar(
                select(LegacyAscensionConfirmation)
                .where(LegacyAscensionConfirmation.character_id == character.id)
                .with_for_update()
            )
            now = datetime.now(UTC)
            key = uuid4()
            expires_at = now + CONFIRMATION_LIFETIME
            if row is None:
                row = LegacyAscensionConfirmation(
                    character_id=character.id,
                    confirmation_key=key,
                    expected_configuration_version=character.combat_configuration_version,
                    created_at=now,
                    expires_at=expires_at,
                )
                session.add(row)
            else:
                row.confirmation_key = key
                row.expected_configuration_version = character.combat_configuration_version
                row.created_at = now
                row.expires_at = expires_at
            await session.flush()
            return LegacyPreparation(view, key, expires_at)

    async def cancel(self, actor: int, confirmation_key: UUID) -> bool:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return False
            row = await session.scalar(
                select(LegacyAscensionConfirmation)
                .where(LegacyAscensionConfirmation.character_id == character.id)
                .with_for_update()
            )
            if row is None or row.confirmation_key != confirmation_key:
                return False
            await session.delete(row)
            return True

    async def confirm(self, actor: int, confirmation_key: UUID) -> LegacyResult | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            confirmation = await session.scalar(
                select(LegacyAscensionConfirmation)
                .where(LegacyAscensionConfirmation.character_id == character.id)
                .with_for_update()
            )
            if confirmation is None or confirmation.confirmation_key != confirmation_key:
                raise LegacyActionRejected("stale_confirmation")

            now = datetime.now(UTC)
            if (
                confirmation.expires_at <= now
                or confirmation.expected_configuration_version
                != character.combat_configuration_version
            ):
                await session.delete(confirmation)
                return self._result(character, False, "stale_confirmation")

            view = await self._view(session, character)
            if not view.can_ascend:
                await session.delete(confirmation)
                reason = view.reasons[0].value if view.reasons else "ineligible"
                return self._result(character, False, reason)

            # Level-gated equipment is kept in the inventory as the same item
            # instance. Only its equipped-slot reference is removed.
            ineligible_item_ids = select(EquipmentItem.id).where(
                EquipmentItem.character_id == character.id,
                EquipmentItem.item_level > 1,
            )
            await session.execute(
                CharacterEquipmentSlot.__table__.delete().where(
                    CharacterEquipmentSlot.character_id == character.id,
                    CharacterEquipmentSlot.equipment_item_id.in_(ineligible_item_ids),
                )
            )

            previous_level = character.level
            previous_xp = character.xp
            previous_version = character.combat_configuration_version
            character.legacy_level = 1
            character.level = 1
            character.xp = 0
            character.combat_configuration_version += 1

            equipment = await load_equipment_configuration(session, character)
            reconcile_character_hp(character, equipment)

            world = await session.scalar(
                select(WorldState)
                .where(WorldState.character_id == character.id)
                .with_for_update()
            )
            if world is None:
                raise RuntimeError("Safe world state disappeared during Legacy transaction.")
            world.region = REFUGE_REGION
            world.location = REFUGE

            session.add(
                LegacyAscensionRecord(
                    character_id=character.id,
                    legacy_level_after=1,
                    character_level_before=previous_level,
                    xp_before=previous_xp,
                    campaign_quest_id=P36_QUEST_ID,
                    operation_key=confirmation.confirmation_key,
                    configuration_version_before=previous_version,
                )
            )
            session.add(
                RewardEvent(
                    character_id=character.id,
                    source_id=f"legacy.ascension:{character.id}:1",
                )
            )
            await session.delete(confirmation)
            await session.flush()

            # The persisted Art slots remain remembered. The active-art loader
            # omits level-ineligible Arts from subsequent combat snapshots.
            await load_active_art_configuration(session, character)
            return LegacyResult(True, None, 1, 1, 0, REFUGE)

    async def _view(self, session: AsyncSession, character: Character) -> LegacyView:
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == P36_QUEST_ID,
            )
        )
        unlock_exists = await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == P36_CAMPAIGN_UNLOCK,
            )
        )
        completion_credit = await session.scalar(
            select(CampaignObjectiveCredit).where(
                CampaignObjectiveCredit.character_id == character.id,
                CampaignObjectiveCredit.quest_id == P36_QUEST_ID,
                CampaignObjectiveCredit.objective_id == P36_COMPLETION_OBJECTIVE,
                CampaignObjectiveCredit.source_key
                == f"{P36_COMPLETION_SOURCE_PREFIX}{character.id}",
            )
        )
        completion_reward = await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P36_REWARD_SOURCE,
            )
        )
        evidence = completion_credit.evidence if completion_credit is not None else {}
        progress = quest.progress if quest is not None else {}
        campaign_complete = bool(
            quest is not None
            and quest.status == "completed"
            and quest.step == 8
            and quest.content_version == P36_CONTENT_VERSION
            and progress.get("completed") is True
            and progress.get("campaign_completed") is True
            and progress.get("legacy_eligible") is True
            and progress.get("completed_steps") == list(range(1, 9))
            and evidence.get("mission_id") == P36_REWARD_SOURCE
            and evidence.get("first_journey_complete") is True
            and evidence.get("legacy_eligible") is True
            and unlock_exists is not None
            and completion_reward is not None
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        brazier = await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == REFUGE_BRAZIER,
            )
        )
        safe_location = bool(
            world is not None
            and world.region == REFUGE_REGION
            and world.location == REFUGE
            and brazier is not None
        )
        reasons: list[LegacyReason] = []
        if character.legacy_level != 0:
            reasons.append(LegacyReason.LEGACY_TRANSITION_UNDEFINED)
        if character.level != 60:
            reasons.append(LegacyReason.LEVEL_REQUIRED)
        if not campaign_complete:
            reasons.append(LegacyReason.CAMPAIGN_REQUIRED)
        if not safe_location:
            reasons.append(LegacyReason.SAFE_LOCATION_REQUIRED)
        if await self._has_incompatible_activity(session, character.id):
            reasons.append(LegacyReason.ACTIVITY_LOCKED)
        can_ascend = character.legacy_level == 0 and not reasons
        return LegacyView(
            character.name,
            character.level,
            character.xp,
            character.legacy_level,
            str(legacy_xp_factor(character.legacy_level)),
            character.combat_configuration_version,
            world.location if world is not None else None,
            campaign_complete,
            can_ascend,
            tuple(reasons),
        )

    async def _has_incompatible_activity(self, session: AsyncSession, character_id: UUID) -> bool:
        if await _has_foreground(session, character_id):
            return True
        if await character_roster_locked(session, character_id):
            return True
        journey_lock = await session.scalar(
            select(CampaignJourney.id)
            .join(
                CampaignJourneyMember,
                CampaignJourneyMember.journey_id == CampaignJourney.id,
            )
            .where(
                CampaignJourneyMember.character_id == character_id,
                CampaignJourneyMember.status == "active",
                CampaignJourney.status.in_(("active", "paused")),
            )
            .limit(1)
        )
        if journey_lock is not None:
            return True
        now = datetime.now(UTC)
        reserved_proposals = select(GroupActivityParticipant.proposal_id).where(
            GroupActivityParticipant.character_id == character_id,
            GroupActivityParticipant.reservation_state == "active",
        )
        group_lock = await session.scalar(
            select(GroupActivityProposal.id)
            .where(
                GroupActivityProposal.status.in_(("pending", "ready")),
                GroupActivityProposal.expires_at > now,
                or_(
                    GroupActivityProposal.proposer_character_id == character_id,
                    GroupActivityProposal.id.in_(reserved_proposals),
                ),
            )
            .limit(1)
        )
        if group_lock is not None:
            return True
        queue_lock = await session.scalar(
            select(PvpveQueueMember.queue_id)
            .join(PvpveQueue, PvpveQueue.id == PvpveQueueMember.queue_id)
            .where(
                PvpveQueueMember.character_id == character_id,
                PvpveQueue.status.in_(("waiting", "matched")),
                PvpveQueue.expires_at > now,
            )
            .limit(1)
        )
        return queue_lock is not None

    async def _character(self, session: AsyncSession, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _lock_character(self, session: AsyncSession, actor: int) -> Character | None:
        return await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
            .with_for_update()
        )

    @staticmethod
    def _result(character: Character, succeeded: bool, reason: str | None) -> LegacyResult:
        return LegacyResult(
            succeeded,
            reason,
            character.legacy_level,
            character.level,
            character.xp,
            REFUGE if succeeded else None,
        )
