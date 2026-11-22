"""Public, transactional Legacy Ascension flow (Legado I through V)."""

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
from asterion.application.safe_location import current_permanent_brazier
from asterion.domain.legacy import (
    LEGACY_ASCENSION_LEVEL,
    MAX_LEGACY_LEVEL,
    legacy_ascension_cost,
    legacy_xp_factor,
)
from asterion.infrastructure.db.models import (
    CampaignJourney,
    CampaignJourneyMember,
    Character,
    CharacterEquipmentSlot,
    EquipmentItem,
    GroupActivityParticipant,
    GroupActivityProposal,
    LegacyAscensionConfirmation,
    LegacyAscensionRecord,
    PvpveQueue,
    PvpveQueueMember,
    RewardEvent,
    WorldState,
)

REFUGE = "Refúgio do Ocaso"
REFUGE_REGION = "Terras do Ocaso"
REFUGE_BRAZIER = "tdo.brazier.refugio_do_ocaso"
CONFIRMATION_LIFETIME = timedelta(minutes=10)


class LegacyReason(StrEnum):
    LEVEL_REQUIRED = "level_required"
    CROWNS_REQUIRED = "crowns_required"
    SAFE_LOCATION_REQUIRED = "safe_location_required"
    ACTIVITY_LOCKED = "activity_locked"
    LEGACY_MAX_REACHED = "legacy_max_reached"


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
    crowns: int
    ascension_cost: int
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
    """Own the only public path for Legado ascension (I through V).

    Each rank requires the previous one (the stored rank itself) and Nv.60, plus a
    permanent Braseiro and no incompatible activity. The rank cost is paid in
    Coroas inside the same transaction. Campaign progress is not required.

    Every mutation locks Character first, matching activity/configuration writers.
    The confirmation key is single-use, short-lived, and tied to the current
    combat-configuration version.
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

            next_legacy_level = character.legacy_level + 1
            cost = legacy_ascension_cost(character.legacy_level)
            previous_level = character.level
            previous_xp = character.xp
            previous_version = character.combat_configuration_version
            character.crowns -= cost
            character.legacy_level = next_legacy_level
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
                    legacy_level_after=next_legacy_level,
                    character_level_before=previous_level,
                    xp_before=previous_xp,
                    campaign_quest_id=None,
                    operation_key=confirmation.confirmation_key,
                    configuration_version_before=previous_version,
                )
            )
            session.add(
                RewardEvent(
                    character_id=character.id,
                    source_id=f"legacy.ascension:{character.id}:{next_legacy_level}",
                )
            )
            await session.delete(confirmation)
            await session.flush()

            # The persisted Art slots remain remembered. The active-art loader
            # omits level-ineligible Arts from subsequent combat snapshots.
            await load_active_art_configuration(session, character)
            return LegacyResult(True, None, next_legacy_level, 1, 0, REFUGE)

    async def _view(self, session: AsyncSession, character: Character) -> LegacyView:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        # Any discovered permanent Braseiro is safe. P36 ends in the Confins and
        # Braseiro travel never crosses regions, so requiring the Refúgio do
        # Ocaso would make the first Ascensão unreachable.
        safe_location = (
            await current_permanent_brazier(session, character.id) is not None
        )
        cost = legacy_ascension_cost(character.legacy_level)
        reasons: list[LegacyReason] = []
        if character.legacy_level >= MAX_LEGACY_LEVEL:
            reasons.append(LegacyReason.LEGACY_MAX_REACHED)
        if character.level != LEGACY_ASCENSION_LEVEL:
            reasons.append(LegacyReason.LEVEL_REQUIRED)
        if character.crowns < cost:
            reasons.append(LegacyReason.CROWNS_REQUIRED)
        if not safe_location:
            reasons.append(LegacyReason.SAFE_LOCATION_REQUIRED)
        if await self._has_incompatible_activity(session, character.id):
            reasons.append(LegacyReason.ACTIVITY_LOCKED)
        can_ascend = not reasons
        return LegacyView(
            character.name,
            character.level,
            character.xp,
            character.legacy_level,
            str(legacy_xp_factor(character.legacy_level)),
            character.combat_configuration_version,
            world.location if world is not None else None,
            character.crowns,
            cost,
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
