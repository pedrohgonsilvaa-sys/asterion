"""Persistent social groups and transactional shared-activity ready checks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.infrastructure.db.models import (
    Character,
    GroupActivityParticipant,
    GroupActivityProposal,
    SocialGroup,
    SocialGroupInvite,
    SocialGroupMember,
)

MAX_GROUP_SIZE = 4
GROUP_INVITE_TTL = timedelta(minutes=10)
ACTIVITY_CONFIRMATION_TTL = timedelta(seconds=60)
ACTIVE_PROPOSAL_STATES = ("pending", "ready", "started")


class GroupError(ValueError):
    """A group or activity-confirmation action is invalid for current state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GroupMemberView:
    character_id: UUID
    name: str
    level: int
    character_class: str
    joined_at: datetime
    is_leader: bool


@dataclass(frozen=True, slots=True)
class GroupView:
    group_id: UUID
    revision: int
    leader_character_id: UUID
    is_leader: bool
    members: tuple[GroupMemberView, ...]


@dataclass(frozen=True, slots=True)
class GroupInviteView:
    invite_id: UUID
    revision: int
    group_id: UUID
    inviter_name: str
    invitee_name: str
    invitee_telegram_id: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IncomingInviteView:
    invite_id: UUID
    revision: int
    group_id: UUID
    group_leader_name: str
    inviter_name: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ActivityEligibility:
    status: str
    fingerprint: str | None = None
    snapshot: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ActivityParticipantView:
    character_id: UUID
    name: str
    eligibility: str
    response: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class ActivityProposalView:
    proposal_id: UUID
    group_id: UUID
    activity_type: str
    proposer_character_id: UUID
    journey_reference_character_id: UUID | None
    context_payload: dict[str, Any]
    status: str
    revision: int
    cancel_reason: str | None
    activity_reference: str | None
    created_at: datetime
    expires_at: datetime
    participants: tuple[ActivityParticipantView, ...]
    viewer_eligibility: str | None = None
    viewer_response: str | None = None


@dataclass(frozen=True, slots=True)
class ActivityStartResult:
    proposal: ActivityProposalView
    started: bool
    activity_reference: str | None
    reason: str | None = None


EligibilityResolver = Callable[
    [AsyncSession, Character, dict[str, Any]], Awaitable[ActivityEligibility]
]
ActivityCreator = Callable[
    [AsyncSession, GroupActivityProposal, Sequence[Character]], Awaitable[str]
]


class GroupService:
    """Manage persistent social membership and prepare immutable activity rosters.

    Group membership is deliberately separate from an activity roster. The latter is
    created only after every selected eligible/helper participant consents and the
    caller's eligibility resolver succeeds again inside the activity-creation
    transaction.
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    async def group(self, actor: int) -> GroupView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            membership = await session.get(SocialGroupMember, character.id)
            if membership is None:
                return None
            group = await session.get(SocialGroup, membership.group_id)
            if group is None or group.status != "active":
                return None
            return await self._group_view(session, character, group)

    async def create_group(self, actor: int) -> GroupView:
        try:
            async with self.sessions.begin() as session:
                character = await self._character(session, actor, lock=True)
                if character is None:
                    raise GroupError("character_missing")
                existing = await session.get(SocialGroupMember, character.id)
                if existing is not None:
                    raise GroupError("already_in_group")
                group = SocialGroup(
                    server_id=self.server_id,
                    leader_character_id=character.id,
                    status="active",
                    revision=0,
                )
                session.add(group)
                await session.flush()
                session.add(SocialGroupMember(group_id=group.id, character_id=character.id))
                await session.flush()
                return await self._group_view(session, character, group)
        except IntegrityError as exc:
            raise GroupError("already_in_group") from exc

    async def invite(
        self,
        actor: int,
        target_name: str,
        *,
        expected_group_revision: int | None = None,
        now: datetime | None = None,
    ) -> GroupInviteView:
        now = _utcnow(now)
        name = target_name.strip()
        if not name or len(name) > 16:
            raise GroupError("character_not_found")
        async with self.sessions.begin() as session:
            actor_character = await self._character(session, actor)
            if actor_character is None:
                raise GroupError("character_missing")
            membership = await session.get(SocialGroupMember, actor_character.id)
            if membership is None:
                raise GroupError("not_in_group")
            group = await session.scalar(
                select(SocialGroup)
                .where(SocialGroup.id == membership.group_id)
                .with_for_update()
            )
            if group is None or group.status != "active":
                raise GroupError("not_in_group")
            if group.revision != expected_group_revision and expected_group_revision is not None:
                raise GroupError("stale")
            if group.leader_character_id != actor_character.id:
                raise GroupError("leader_only")
            if await session.get(SocialGroupMember, actor_character.id) is None:
                raise GroupError("not_in_group")
            target = await session.scalar(
                select(Character)
                .where(
                    Character.server_id == self.server_id,
                    func.lower(Character.name) == name.casefold(),
                )
                .with_for_update()
            )
            if target is None:
                raise GroupError("character_not_found")
            if target.id == actor_character.id:
                raise GroupError("cannot_invite_self")
            if await session.get(SocialGroupMember, target.id) is not None:
                raise GroupError("already_in_group")
            count = await self._member_count(session, group.id)
            if count >= MAX_GROUP_SIZE:
                raise GroupError("group_full")
            await session.execute(
                update(SocialGroupInvite)
                .where(
                    SocialGroupInvite.group_id == group.id,
                    SocialGroupInvite.invitee_character_id == target.id,
                    SocialGroupInvite.status == "pending",
                    SocialGroupInvite.expires_at <= now,
                )
                .values(status="expired", responded_at=now, revision=SocialGroupInvite.revision + 1)
            )
            pending = await session.scalar(
                select(SocialGroupInvite.id).where(
                    SocialGroupInvite.group_id == group.id,
                    SocialGroupInvite.invitee_character_id == target.id,
                    SocialGroupInvite.status == "pending",
                )
            )
            if pending is not None:
                raise GroupError("invite_pending")
            invite = SocialGroupInvite(
                group_id=group.id,
                inviter_character_id=actor_character.id,
                invitee_character_id=target.id,
                status="pending",
                revision=0,
                created_at=now,
                expires_at=now + GROUP_INVITE_TTL,
            )
            session.add(invite)
            group.revision += 1
            await session.flush()
            return GroupInviteView(
                invite_id=invite.id,
                revision=invite.revision,
                group_id=group.id,
                inviter_name=actor_character.name,
                invitee_name=target.name,
                invitee_telegram_id=target.telegram_id,
                expires_at=invite.expires_at,
            )

    async def incoming_invites(
        self, actor: int, *, now: datetime | None = None
    ) -> tuple[IncomingInviteView, ...]:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return ()
            await session.execute(
                update(SocialGroupInvite)
                .where(
                    SocialGroupInvite.invitee_character_id == character.id,
                    SocialGroupInvite.status == "pending",
                    SocialGroupInvite.expires_at <= now,
                )
                .values(status="expired", responded_at=now, revision=SocialGroupInvite.revision + 1)
            )
            rows = (
                await session.execute(
                    select(SocialGroupInvite, SocialGroup, Character)
                    .join(SocialGroup, SocialGroup.id == SocialGroupInvite.group_id)
                    .join(Character, Character.id == SocialGroupInvite.inviter_character_id)
                    .where(
                        SocialGroupInvite.invitee_character_id == character.id,
                        SocialGroupInvite.status == "pending",
                        SocialGroupInvite.expires_at > now,
                        SocialGroup.status == "active",
                    )
                    .order_by(SocialGroupInvite.created_at, SocialGroupInvite.id)
                )
            ).all()
            views = []
            for invite, group, inviter in rows:
                views.append(
                    IncomingInviteView(
                        invite_id=invite.id,
                        revision=invite.revision,
                        group_id=group.id,
                        group_leader_name=await self._leader_name(session, group),
                        inviter_name=inviter.name,
                        expires_at=invite.expires_at,
                    )
                )
            return tuple(views)

    async def respond_invite(
        self,
        actor: int,
        invite_id: UUID,
        *,
        expected_revision: int,
        accept: bool,
        now: datetime | None = None,
    ) -> GroupView | None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            invite_seed = await session.get(SocialGroupInvite, invite_id)
            if invite_seed is None:
                raise GroupError("invite_expired")
            group = await session.scalar(
                select(SocialGroup)
                .where(SocialGroup.id == invite_seed.group_id)
                .with_for_update()
            )
            invite = await session.scalar(
                select(SocialGroupInvite)
                .where(SocialGroupInvite.id == invite_id)
                .with_for_update()
            )
            target = await self._character(session, actor, lock=True)
            if target is None:
                raise GroupError("character_missing")
            if invite is None or invite.invitee_character_id != target.id:
                raise GroupError("invite_expired")
            desired = "accepted" if accept else "declined"
            if invite.status == desired:
                if accept:
                    return await self.group_for_character(session, target, invite.group_id)
                return None
            if invite.status != "pending" or group is None or group.status != "active":
                raise GroupError("invite_expired")
            if invite.revision != expected_revision:
                raise GroupError("stale")
            if invite.expires_at <= now:
                invite.status = "expired"
                invite.revision += 1
                invite.responded_at = now
                return None
            if not accept:
                invite.status = "declined"
                invite.revision += 1
                invite.responded_at = now
                group.revision += 1
                return None
            if target.server_id != group.server_id or group.server_id != self.server_id:
                raise GroupError("wrong_server")
            if await session.get(SocialGroupMember, target.id) is not None:
                raise GroupError("already_in_group")
            if await self._member_count(session, group.id) >= MAX_GROUP_SIZE:
                raise GroupError("group_full")
            session.add(SocialGroupMember(group_id=group.id, character_id=target.id))
            invite.status = "accepted"
            invite.revision += 1
            invite.responded_at = now
            group.revision += 1
            await session.flush()
            return await self._group_view(session, target, group)

    async def cancel_invite(
        self,
        actor: int,
        invite_id: UUID,
        *,
        expected_group_revision: int,
        now: datetime | None = None,
    ) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                raise GroupError("character_missing")
            membership = await session.get(SocialGroupMember, character.id)
            if membership is None:
                raise GroupError("not_in_group")
            group = await session.scalar(
                select(SocialGroup)
                .where(SocialGroup.id == membership.group_id)
                .with_for_update()
            )
            if group is None or group.leader_character_id != character.id:
                raise GroupError("leader_only")
            invite = await session.scalar(
                select(SocialGroupInvite)
                .where(SocialGroupInvite.id == invite_id, SocialGroupInvite.group_id == group.id)
                .with_for_update()
            )
            if invite is None:
                raise GroupError("invite_expired")
            if invite.status == "cancelled":
                return
            if group.revision != expected_group_revision:
                raise GroupError("stale")
            if invite.status != "pending":
                raise GroupError("invite_expired")
            invite.status = "cancelled"
            invite.responded_at = now
            invite.revision += 1
            group.revision += 1

    async def leave(self, actor: int, *, expected_group_revision: int) -> GroupView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                raise GroupError("character_missing")
            membership_seed = await session.get(SocialGroupMember, character.id)
            if membership_seed is None:
                return None
            group = await session.scalar(
                select(SocialGroup)
                .where(SocialGroup.id == membership_seed.group_id)
                .with_for_update()
            )
            if group is None or group.status != "active":
                return None
            if group.revision != expected_group_revision:
                raise GroupError("stale")
            await self._lock_characters(session, (character.id,))
            membership = await session.scalar(
                select(SocialGroupMember)
                .where(SocialGroupMember.character_id == character.id)
                .with_for_update()
            )
            if membership is None or membership.group_id != group.id:
                return None
            if await self._has_active_reservation(session, character.id):
                raise GroupError("activity_in_progress")
            await session.delete(membership)
            await session.flush()
            remaining = list(
                (
                    await session.scalars(
                        select(SocialGroupMember)
                        .where(SocialGroupMember.group_id == group.id)
                        .order_by(SocialGroupMember.joined_at, SocialGroupMember.character_id)
                    )
                ).all()
            )
            group.revision += 1
            if not remaining:
                group.status = "disbanded"
                group.leader_character_id = character.id
                await session.execute(
                    update(SocialGroupInvite)
                    .where(
                        SocialGroupInvite.group_id == group.id,
                        SocialGroupInvite.status == "pending",
                    )
                    .values(
                        status="cancelled",
                        responded_at=func.now(),
                        revision=SocialGroupInvite.revision + 1,
                    )
                )
                return None
            if group.leader_character_id == character.id:
                group.leader_character_id = remaining[0].character_id
            return await self._group_view(session, character, group)

    async def kick(
        self,
        actor: int,
        target_character_id: UUID,
        *,
        expected_group_revision: int,
    ) -> GroupView:
        async with self.sessions.begin() as session:
            actor_character = await self._character(session, actor)
            if actor_character is None:
                raise GroupError("character_missing")
            membership = await session.get(SocialGroupMember, actor_character.id)
            if membership is None:
                raise GroupError("not_in_group")
            group = await session.scalar(
                select(SocialGroup)
                .where(SocialGroup.id == membership.group_id)
                .with_for_update()
            )
            if group is None or group.status != "active":
                raise GroupError("not_in_group")
            if group.leader_character_id != actor_character.id:
                raise GroupError("leader_only")
            if target_character_id == actor_character.id:
                raise GroupError("cannot_kick_self")
            await self._lock_characters(session, (actor_character.id, target_character_id))
            if group.revision != expected_group_revision:
                raise GroupError("stale")
            if await self._has_active_reservation(session, target_character_id):
                raise GroupError("activity_in_progress")
            target_membership = await session.scalar(
                select(SocialGroupMember)
                .where(
                    SocialGroupMember.character_id == target_character_id,
                    SocialGroupMember.group_id == group.id,
                )
                .with_for_update()
            )
            if target_membership is None:
                raise GroupError("not_group_member")
            await session.delete(target_membership)
            group.revision += 1
            await session.flush()
            return await self._group_view(session, actor_character, group)

    async def transfer_leadership(
        self,
        actor: int,
        target_character_id: UUID,
        *,
        expected_group_revision: int,
    ) -> GroupView:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                raise GroupError("character_missing")
            membership = await session.get(SocialGroupMember, character.id)
            if membership is None:
                raise GroupError("not_in_group")
            group = await session.scalar(
                select(SocialGroup)
                .where(SocialGroup.id == membership.group_id)
                .with_for_update()
            )
            if group is None or group.status != "active":
                raise GroupError("not_in_group")
            if group.revision != expected_group_revision:
                raise GroupError("stale")
            if group.leader_character_id != character.id:
                raise GroupError("leader_only")
            if target_character_id == character.id:
                return await self._group_view(session, character, group)
            if await session.get(SocialGroupMember, target_character_id) is None:
                raise GroupError("not_group_member")
            target_membership = await session.scalar(
                select(SocialGroupMember).where(
                    SocialGroupMember.character_id == target_character_id,
                    SocialGroupMember.group_id == group.id,
                )
            )
            if target_membership is None:
                raise GroupError("not_group_member")
            await self._lock_characters(session, (character.id, target_character_id))
            group.leader_character_id = target_character_id
            group.revision += 1
            return await self._group_view(session, character, group)

    async def propose_activity(
        self,
        actor: int,
        *,
        activity_type: str,
        participant_character_ids: Sequence[UUID],
        eligibility_resolver: EligibilityResolver,
        context_payload: dict[str, Any] | None = None,
        journey_reference_character_id: UUID | None = None,
        now: datetime | None = None,
    ) -> ActivityProposalView:
        now = _utcnow(now)
        participant_ids = tuple(participant_character_ids)
        if not activity_type or len(activity_type) > 32:
            raise GroupError("activity_type_invalid")
        if not participant_ids or len(participant_ids) > MAX_GROUP_SIZE:
            raise GroupError("roster_size_invalid")
        if len(set(participant_ids)) != len(participant_ids):
            raise GroupError("roster_invalid")
        payload = dict(context_payload or {})
        try:
            async with self.sessions.begin() as session:
                proposer = await self._character(session, actor)
                if proposer is None:
                    raise GroupError("character_missing")
                proposer_membership = await session.get(SocialGroupMember, proposer.id)
                if proposer_membership is None:
                    raise GroupError("not_in_group")
                group = await session.scalar(
                    select(SocialGroup)
                    .where(SocialGroup.id == proposer_membership.group_id)
                    .with_for_update()
                )
                if group is None or group.status != "active":
                    raise GroupError("not_in_group")
                selected = set(participant_ids)
                if proposer.id not in selected:
                    raise GroupError("proposer_not_in_roster")
                group_members = set(
                    (
                        await session.scalars(
                            select(SocialGroupMember.character_id).where(
                                SocialGroupMember.group_id == group.id
                            )
                        )
                    ).all()
                )
                if not selected <= group_members:
                    raise GroupError("roster_not_group_subset")
                if journey_reference_character_id is not None and (
                    journey_reference_character_id not in group_members
                ):
                    raise GroupError("journey_reference_not_member")
                candidates = await self._lock_characters(session, participant_ids)
                if len(candidates) != len(participant_ids) or any(
                    candidate.server_id != self.server_id for candidate in candidates
                ):
                    raise GroupError("roster_character_missing")
                proposal = GroupActivityProposal(
                    group_id=group.id,
                    activity_type=activity_type,
                    proposer_character_id=proposer.id,
                    journey_reference_character_id=journey_reference_character_id,
                    context_payload=payload,
                    status="pending",
                    revision=0,
                    created_at=now,
                    expires_at=now + ACTIVITY_CONFIRMATION_TTL,
                )
                session.add(proposal)
                await session.flush()
                eligible_count = 0
                candidate_by_id = {candidate.id: candidate for candidate in candidates}
                for ordinal, character_id in enumerate(participant_ids):
                    candidate = candidate_by_id[character_id]
                    result = await eligibility_resolver(session, candidate, payload)
                    _validate_eligibility(result)
                    if candidate.id == proposer.id and result.status == "ineligible":
                        raise GroupError("proposer_ineligible")
                    is_included = result.status != "ineligible"
                    if is_included:
                        eligible_count += 1
                        if await self._has_active_reservation(session, candidate.id):
                            raise GroupError("participant_busy")
                    responded_at = (
                        now if candidate.id == proposer.id and is_included else None
                    )
                    session.add(
                        GroupActivityParticipant(
                            proposal_id=proposal.id,
                            character_id=candidate.id,
                            ordinal=ordinal,
                            eligibility=result.status,
                            eligibility_fingerprint=result.fingerprint,
                            eligibility_snapshot=dict(result.snapshot or {}),
                            response=(
                                "not_required"
                                if not is_included
                                else ("accepted" if candidate.id == proposer.id else "pending")
                            ),
                            reservation_state="active" if is_included else "released",
                            responded_at=responded_at,
                        )
                    )
                if eligible_count == 0:
                    raise GroupError("empty_eligible_roster")
                await session.flush()
                remaining = await self._pending_response_count(session, proposal.id)
                if remaining == 0:
                    proposal.status = "ready"
                    proposal.revision += 1
                return await self._proposal_view(session, proposer.id, proposal)
        except IntegrityError as exc:
            raise GroupError("participant_busy") from exc

    async def respond_activity(
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
        accept: bool,
        now: datetime | None = None,
    ) -> ActivityProposalView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            seed = await session.get(GroupActivityProposal, proposal_id)
            if seed is None:
                raise GroupError("proposal_expired")
            group = await session.scalar(
                select(SocialGroup).where(SocialGroup.id == seed.group_id).with_for_update()
            )
            proposal = await session.scalar(
                select(GroupActivityProposal)
                .where(GroupActivityProposal.id == proposal_id)
                .with_for_update()
            )
            character = await self._character(session, actor)
            if character is None:
                raise GroupError("character_missing")
            participant = await session.scalar(
                select(GroupActivityParticipant)
                .where(
                    GroupActivityParticipant.proposal_id == proposal_id,
                    GroupActivityParticipant.character_id == character.id,
                )
                .with_for_update()
            )
            if proposal is None or group is None or participant is None:
                raise GroupError("not_participant")
            desired = "accepted" if accept else "declined"
            if participant.response == desired:
                return await self._proposal_view(session, character.id, proposal)
            if proposal.status not in {"pending", "ready"}:
                return await self._proposal_view(session, character.id, proposal)
            if proposal.revision != expected_revision:
                raise GroupError("stale")
            if participant.eligibility == "ineligible":
                raise GroupError("participant_ineligible")
            if now >= proposal.expires_at:
                proposal.status = "expired"
                proposal.revision += 1
                await self._release_proposal(session, proposal.id)
                return await self._proposal_view(session, character.id, proposal)
            participant.response = desired
            participant.responded_at = now
            proposal.revision += 1
            if not accept:
                proposal.status = "declined"
                await self._release_proposal(session, proposal.id)
            elif await self._pending_response_count(session, proposal.id) == 0:
                proposal.status = "ready"
            else:
                proposal.status = "pending"
            await session.flush()
            return await self._proposal_view(session, character.id, proposal)

    async def start_activity(
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
        eligibility_resolver: EligibilityResolver,
        create_activity: ActivityCreator,
        now: datetime | None = None,
    ) -> ActivityStartResult:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            seed = await session.get(GroupActivityProposal, proposal_id)
            if seed is None:
                raise GroupError("proposal_expired")
            group = await session.scalar(
                select(SocialGroup).where(SocialGroup.id == seed.group_id).with_for_update()
            )
            proposal = await session.scalar(
                select(GroupActivityProposal)
                .where(GroupActivityProposal.id == proposal_id)
                .with_for_update()
            )
            proposer = await self._character(session, actor)
            if proposal is None or group is None or proposer is None:
                raise GroupError("proposal_expired")
            actor_participant = await session.get(
                GroupActivityParticipant, (proposal.id, proposer.id)
            )
            if actor_participant is None:
                raise GroupError("not_participant")
            if proposal.status == "started":
                view = await self._proposal_view(session, proposer.id, proposal)
                return ActivityStartResult(view, True, proposal.activity_reference)
            if proposal.status != "ready":
                raise GroupError("not_ready")
            if proposal.revision != expected_revision:
                raise GroupError("stale")
            participant_rows = list(
                (
                    await session.scalars(
                        select(GroupActivityParticipant)
                        .where(GroupActivityParticipant.proposal_id == proposal.id)
                        .order_by(GroupActivityParticipant.ordinal)
                        .with_for_update()
                    )
                ).all()
            )
            included = [row for row in participant_rows if row.eligibility != "ineligible"]
            if not included or any(row.response != "accepted" for row in included):
                raise GroupError("consent_incomplete")
            characters = await self._lock_characters(
                session, [row.character_id for row in included]
            )
            by_id = {character.id: character for character in characters}
            invalid_reason = None
            for row in included:
                character = by_id.get(row.character_id)
                if character is None or character.server_id != self.server_id:
                    invalid_reason = "participant_missing"
                    break
                current = await eligibility_resolver(
                    session, character, proposal.context_payload
                )
                _validate_eligibility(current)
                if (
                    current.status != row.eligibility
                    or current.fingerprint != row.eligibility_fingerprint
                    or dict(current.snapshot or {}) != dict(row.eligibility_snapshot or {})
                ):
                    invalid_reason = "eligibility_changed"
                    break
            if now >= proposal.expires_at:
                invalid_reason = "confirmation_expired"
            if invalid_reason:
                proposal.status = "cancelled"
                proposal.cancel_reason = invalid_reason
                proposal.revision += 1
                await self._release_proposal(session, proposal.id)
                await session.flush()
                view = await self._proposal_view(session, proposer.id, proposal)
                return ActivityStartResult(view, False, None, invalid_reason)
            created_reference = await create_activity(
                session, proposal, tuple(by_id[row.character_id] for row in included)
            )
            if not created_reference or len(created_reference) > 96:
                raise GroupError("activity_creation_invalid")
            proposal.activity_reference = created_reference
            proposal.status = "started"
            proposal.started_at = now
            proposal.revision += 1
            await session.flush()
            view = await self._proposal_view(session, proposer.id, proposal)
            return ActivityStartResult(view, True, created_reference)

    async def finish_activity(
        self, proposal_id: UUID, *, succeeded: bool, now: datetime | None = None
    ) -> ActivityProposalView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            seed = await session.get(GroupActivityProposal, proposal_id)
            if seed is None:
                raise GroupError("proposal_expired")
            await session.scalar(
                select(SocialGroup).where(SocialGroup.id == seed.group_id).with_for_update()
            )
            proposal = await session.scalar(
                select(GroupActivityProposal)
                .where(GroupActivityProposal.id == proposal_id)
                .with_for_update()
            )
            if proposal is None:
                raise GroupError("proposal_expired")
            if proposal.status in {"completed", "failed"}:
                return await self._proposal_view(session, proposal.proposer_character_id, proposal)
            if proposal.status != "started":
                raise GroupError("activity_not_started")
            proposal.status = "completed" if succeeded else "failed"
            proposal.finished_at = now
            proposal.revision += 1
            await self._release_proposal(session, proposal.id)
            await session.flush()
            return await self._proposal_view(session, proposal.proposer_character_id, proposal)

    async def activity_proposal(
        self, actor: int, proposal_id: UUID, *, now: datetime | None = None
    ) -> ActivityProposalView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            seed = await session.get(GroupActivityProposal, proposal_id)
            if seed is None:
                raise GroupError("proposal_expired")
            group = await session.scalar(
                select(SocialGroup).where(SocialGroup.id == seed.group_id).with_for_update()
            )
            proposal = await session.scalar(
                select(GroupActivityProposal)
                .where(GroupActivityProposal.id == proposal_id)
                .with_for_update()
            )
            character = await self._character(session, actor)
            if proposal is None or group is None or character is None:
                raise GroupError("proposal_expired")
            participant = await session.get(
                GroupActivityParticipant, (proposal.id, character.id)
            )
            if participant is None:
                raise GroupError("not_participant")
            if proposal.status in {"pending", "ready"} and now >= proposal.expires_at:
                proposal.status = "expired"
                proposal.revision += 1
                await self._release_proposal(session, proposal.id)
            return await self._proposal_view(session, character.id, proposal)

    async def activity_proposals(
        self, actor: int, *, now: datetime | None = None
    ) -> tuple[ActivityProposalView, ...]:
        """List current confirmations addressed to this character's social group."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return ()
            proposals = list(
                (
                    await session.scalars(
                        select(GroupActivityProposal)
                        .join(
                            GroupActivityParticipant,
                            GroupActivityParticipant.proposal_id == GroupActivityProposal.id,
                        )
                        .where(
                            GroupActivityParticipant.character_id == character.id,
                            GroupActivityParticipant.reservation_state == "active",
                            GroupActivityProposal.status.in_(("pending", "ready")),
                        )
                        .order_by(GroupActivityProposal.created_at, GroupActivityProposal.id)
                        .with_for_update(of=GroupActivityProposal)
                    )
                ).all()
            )
            views = []
            for proposal in proposals:
                if now >= proposal.expires_at:
                    proposal.status = "expired"
                    proposal.revision += 1
                    proposal.cancel_reason = "confirmation_expired"
                    await self._release_proposal(session, proposal.id)
                views.append(await self._proposal_view(session, character.id, proposal))
            return tuple(views)

    async def _character(
        self, session: AsyncSession, actor: int, *, lock: bool = False
    ) -> Character | None:
        statement = select(Character).where(
            Character.telegram_id == actor,
            Character.server_id == self.server_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    async def _group_view(
        self, session: AsyncSession, character: Character, group: SocialGroup
    ) -> GroupView:
        rows = (
            await session.execute(
                select(SocialGroupMember, Character)
                .join(Character, Character.id == SocialGroupMember.character_id)
                .where(SocialGroupMember.group_id == group.id)
                .order_by(SocialGroupMember.joined_at, Character.id)
            )
        ).all()
        return GroupView(
            group_id=group.id,
            revision=group.revision,
            leader_character_id=group.leader_character_id,
            is_leader=group.leader_character_id == character.id,
            members=tuple(
                GroupMemberView(
                    character_id=member.character_id,
                    name=member_character.name,
                    level=member_character.level,
                    character_class=member_character.character_class,
                    joined_at=member.joined_at,
                    is_leader=member.character_id == group.leader_character_id,
                )
                for member, member_character in rows
            ),
        )

    async def group_for_character(
        self, session: AsyncSession, character: Character, group_id: UUID
    ) -> GroupView | None:
        membership = await session.get(SocialGroupMember, character.id)
        group = await session.get(SocialGroup, group_id)
        if membership is None or membership.group_id != group_id or group is None:
            return None
        return await self._group_view(session, character, group)

    async def _member_count(self, session: AsyncSession, group_id: UUID) -> int:
        return int(
            await session.scalar(
                select(func.count()).select_from(SocialGroupMember).where(
                    SocialGroupMember.group_id == group_id
                )
            )
            or 0
        )

    async def _leader_name(self, session: AsyncSession, group: SocialGroup) -> str:
        return str(
            await session.scalar(
                select(Character.name).where(Character.id == group.leader_character_id)
            )
            or "Grupo"
        )

    async def _lock_characters(
        self, session: AsyncSession, character_ids: Sequence[UUID]
    ) -> list[Character]:
        unique_ids = tuple(sorted(set(character_ids), key=str))
        if not unique_ids:
            return []
        return list(
            (
                await session.scalars(
                    select(Character)
                    .where(Character.id.in_(unique_ids))
                    .order_by(Character.id)
                    .with_for_update()
                )
            ).all()
        )

    async def _has_active_reservation(self, session: AsyncSession, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(GroupActivityParticipant.proposal_id)
                .join(
                    GroupActivityProposal,
                    GroupActivityProposal.id == GroupActivityParticipant.proposal_id,
                )
                .where(
                    GroupActivityParticipant.character_id == character_id,
                    GroupActivityParticipant.reservation_state == "active",
                    GroupActivityProposal.status.in_(ACTIVE_PROPOSAL_STATES),
                )
                .limit(1)
            )
        )

    async def _pending_response_count(self, session: AsyncSession, proposal_id: UUID) -> int:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(GroupActivityParticipant)
                .where(
                    GroupActivityParticipant.proposal_id == proposal_id,
                    GroupActivityParticipant.eligibility != "ineligible",
                    GroupActivityParticipant.response == "pending",
                )
            )
            or 0
        )

    async def _release_proposal(self, session: AsyncSession, proposal_id: UUID) -> None:
        await session.execute(
            update(GroupActivityParticipant)
            .where(GroupActivityParticipant.proposal_id == proposal_id)
            .values(reservation_state="released")
        )

    async def _proposal_view(
        self, session: AsyncSession, viewer_id: UUID, proposal: GroupActivityProposal
    ) -> ActivityProposalView:
        rows = (
            await session.execute(
                select(GroupActivityParticipant, Character)
                .join(Character, Character.id == GroupActivityParticipant.character_id)
                .where(GroupActivityParticipant.proposal_id == proposal.id)
                .order_by(GroupActivityParticipant.ordinal)
            )
        ).all()
        viewer = next(
            (
                participant
                for participant, _character in rows
                if participant.character_id == viewer_id
            ),
            None,
        )
        return ActivityProposalView(
            proposal_id=proposal.id,
            group_id=proposal.group_id,
            activity_type=proposal.activity_type,
            proposer_character_id=proposal.proposer_character_id,
            journey_reference_character_id=proposal.journey_reference_character_id,
            context_payload=dict(proposal.context_payload or {}),
            status=proposal.status,
            revision=proposal.revision,
            cancel_reason=proposal.cancel_reason,
            activity_reference=proposal.activity_reference,
            created_at=proposal.created_at,
            expires_at=proposal.expires_at,
            participants=tuple(
                ActivityParticipantView(
                    character_id=participant.character_id,
                    name=character.name,
                    eligibility=participant.eligibility,
                    response=participant.response,
                    ordinal=participant.ordinal,
                )
                for participant, character in rows
            ),
            viewer_eligibility=viewer.eligibility if viewer is not None else None,
            viewer_response=viewer.response if viewer is not None else None,
        )


async def prepare_character_deletion(session: AsyncSession, character_id: UUID) -> bool:
    """Preserve social groups and refuse deletion during a frozen live roster.

    The account deletion workflow must lock the containing SocialGroup before it
    locks Character, matching the lock order used by group mutations.
    """
    membership = await session.get(SocialGroupMember, character_id)
    if membership is None:
        return True
    group = await session.scalar(
        select(SocialGroup)
        .where(SocialGroup.id == membership.group_id)
        .with_for_update()
    )
    if group is None:
        return True

    live_activity = await session.scalar(
        select(GroupActivityParticipant.proposal_id)
        .join(
            GroupActivityProposal,
            GroupActivityProposal.id == GroupActivityParticipant.proposal_id,
        )
        .where(
            GroupActivityParticipant.character_id == character_id,
            GroupActivityParticipant.reservation_state == "active",
            GroupActivityProposal.status == "started",
        )
        .limit(1)
    )
    if live_activity is not None:
        return False

    pending_proposals = list(
        (
            await session.scalars(
                select(GroupActivityProposal)
                .join(
                    GroupActivityParticipant,
                    GroupActivityParticipant.proposal_id == GroupActivityProposal.id,
                )
                .where(
                    GroupActivityParticipant.character_id == character_id,
                    GroupActivityParticipant.reservation_state == "active",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .with_for_update(of=GroupActivityProposal)
            )
        ).all()
    )
    for proposal in pending_proposals:
        proposal.status = "cancelled"
        proposal.cancel_reason = "participant_deletion"
        proposal.revision += 1
        await session.execute(
            update(GroupActivityParticipant)
            .where(GroupActivityParticipant.proposal_id == proposal.id)
            .values(reservation_state="released")
        )

    if group.leader_character_id == character_id:
        successor = await session.scalar(
            select(SocialGroupMember.character_id)
            .where(
                SocialGroupMember.group_id == group.id,
                SocialGroupMember.character_id != character_id,
            )
            .order_by(SocialGroupMember.joined_at, SocialGroupMember.character_id)
            .limit(1)
        )
        if successor is None:
            group.status = "disbanded"
        else:
            group.leader_character_id = successor
    group.revision += 1
    return True


def _utcnow(value: datetime | None) -> datetime:
    now = value or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(UTC)


def _validate_eligibility(value: ActivityEligibility) -> None:
    if value.status not in {"eligible", "helper", "ineligible"}:
        raise GroupError("eligibility_invalid")
    if value.fingerprint is not None and len(value.fingerprint) > 64:
        raise GroupError("eligibility_invalid")
    if value.snapshot is not None and not isinstance(value.snapshot, dict):
        raise GroupError("eligibility_invalid")
