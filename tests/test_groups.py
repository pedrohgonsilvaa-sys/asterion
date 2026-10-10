from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from asterion.application.account import finalize_due_character_deletions
from asterion.application.groups import (
    ACTIVITY_CONFIRMATION_TTL,
    GROUP_INVITE_TTL,
    ActivityEligibility,
    GroupError,
    GroupService,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterDeletionRequest,
    GroupActivityParticipant,
    GroupActivityProposal,
    SocialGroup,
    SocialGroupMember,
)

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
ACTORS = (810001, 810002, 810003, 810004, 810005)
NAMES = ("Alpha", "Bravo", "Cedar", "Doran", "Elian")


async def _seed_characters(database) -> dict[str, int]:
    sessions = database[1]
    async with sessions.begin() as session:
        for actor, name in zip(ACTORS, NAMES, strict=True):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=name,
                    race="remanescente",
                    character_class="sentinela",
                    stage="road_active",
                    ruleset_version="tdo-1.0.15",
                    hp=Decimal("100"),
                    max_hp=Decimal("100"),
                    vigor=100,
                    max_vigor=100,
                    crowns=0,
                )
            )
    return dict(zip(NAMES, ACTORS, strict=True))


def _service(database) -> GroupService:
    return GroupService(database[1], "ocaso")


async def _invite_and_join(service, leader: int, target: int, target_name: str, now=NOW):
    group = await service.group(leader)
    invite = await service.invite(
        leader,
        target_name,
        expected_group_revision=group.revision,
        now=now,
    )
    joined = await service.respond_invite(
        target,
        invite.invite_id,
        expected_revision=invite.revision,
        accept=True,
        now=now + timedelta(seconds=1),
    )
    assert joined is not None
    return joined


@pytest.mark.asyncio
async def test_persistent_group_invite_accept_refuse_expiry_and_capacity(database):
    actors = await _seed_characters(database)
    service = _service(database)
    group = await service.create_group(actors["Alpha"])
    assert len(group.members) == 1
    assert group.is_leader

    refused = await service.invite(
        actors["Alpha"],
        "Elian",
        expected_group_revision=group.revision,
        now=NOW,
    )
    assert refused.expires_at - NOW == GROUP_INVITE_TTL
    inbox = await service.incoming_invites(actors["Elian"], now=NOW + timedelta(minutes=1))
    assert len(inbox) == 1
    assert inbox[0].inviter_name == "Alpha"
    assert (
        await service.respond_invite(
            actors["Elian"],
            refused.invite_id,
            expected_revision=refused.revision,
            accept=False,
            now=NOW + timedelta(minutes=1),
        )
        is None
    )
    assert await service.incoming_invites(actors["Elian"], now=NOW + timedelta(minutes=1)) == ()

    expired = await service.invite(
        actors["Alpha"],
        "Elian",
        expected_group_revision=(await service.group(actors["Alpha"])).revision,
        now=NOW + timedelta(minutes=1),
    )
    assert await service.incoming_invites(
        actors["Elian"], now=NOW + timedelta(minutes=1) + GROUP_INVITE_TTL + timedelta(seconds=1)
    ) == ()
    with pytest.raises(GroupError, match="invite_expired"):
        await service.respond_invite(
            actors["Elian"],
            expired.invite_id,
            expected_revision=expired.revision,
            accept=True,
            now=NOW + timedelta(minutes=12),
        )

    invite = await service.invite(
        actors["Alpha"],
        "Bravo",
        expected_group_revision=(await service.group(actors["Alpha"])).revision,
        now=NOW + timedelta(minutes=12),
    )
    joined = await service.respond_invite(
        actors["Bravo"],
        invite.invite_id,
        expected_revision=invite.revision,
        accept=True,
        now=NOW + timedelta(minutes=12, seconds=1),
    )
    assert joined is not None
    assert {member.name for member in joined.members} == {"Alpha", "Bravo"}

    # A duplicated callback is a read of the already-applied decision.
    duplicate = await service.respond_invite(
        actors["Bravo"],
        invite.invite_id,
        expected_revision=invite.revision,
        accept=True,
        now=NOW + timedelta(minutes=12, seconds=2),
    )
    assert duplicate is not None
    assert len(duplicate.members) == 2

    group = await _invite_and_join(
        service, actors["Alpha"], actors["Cedar"], "Cedar", NOW + timedelta(minutes=12, seconds=3)
    )
    group = await _invite_and_join(
        service, actors["Alpha"], actors["Doran"], "Doran", NOW + timedelta(minutes=12, seconds=5)
    )
    assert len(group.members) == 4
    with pytest.raises(GroupError, match="group_full"):
        await service.invite(
            actors["Alpha"],
            "Elian",
            expected_group_revision=group.revision,
            now=NOW + timedelta(minutes=12, seconds=7),
        )



@pytest.mark.asyncio
async def test_group_leadership_kick_leave_and_offline_persistence(database):
    actors = await _seed_characters(database)
    service = _service(database)
    group = await service.create_group(actors["Alpha"])
    group = await _invite_and_join(service, actors["Alpha"], actors["Bravo"], "Bravo")
    transferred = await service.transfer_leadership(
        actors["Alpha"],
        next(member.character_id for member in group.members if member.name == "Bravo"),
        expected_group_revision=group.revision,
    )
    assert not transferred.is_leader
    assert next(member for member in transferred.members if member.name == "Bravo").is_leader
    assert await GroupService(database[1], "ocaso").group(actors["Bravo"]) is not None
    with pytest.raises(GroupError, match="leader_only"):
        await service.invite(
            actors["Alpha"],
            "Cedar",
            expected_group_revision=transferred.revision,
            now=NOW,
        )

    alpha_id = next(member.character_id for member in transferred.members if member.name == "Alpha")
    after_kick = await service.kick(
        actors["Bravo"], alpha_id, expected_group_revision=transferred.revision
    )
    assert [member.name for member in after_kick.members] == ["Bravo"]
    # A character that was kicked has no group, while the group survives for its leader.
    assert await service.group(actors["Alpha"]) is None
    assert await service.group(actors["Bravo"]) is not None

    assert await service.leave(actors["Bravo"], expected_group_revision=after_kick.revision) is None
    assert await service.group(actors["Bravo"]) is None


@pytest.mark.asyncio
async def test_ready_check_requires_unanimity_then_starts_once_in_same_transaction(database):
    actors = await _seed_characters(database)
    service = _service(database)
    group = await service.create_group(actors["Alpha"])
    group = await _invite_and_join(service, actors["Alpha"], actors["Bravo"], "Bravo")
    group = await _invite_and_join(service, actors["Alpha"], actors["Cedar"], "Cedar")
    group_revision = group.revision
    ids = {member.name: member.character_id for member in group.members}

    async def eligibility(_session, character, _context):
        if character.name == "Cedar":
            return ActivityEligibility("ineligible", fingerprint="different-location")
        return ActivityEligibility(
            "helper" if character.name == "Bravo" else "eligible",
            fingerprint=f"checkpoint:{character.name}:P1-2",
            snapshot={"checkpoint": "P1-2", "revision": 3},
        )

    proposal = await service.propose_activity(
        actors["Alpha"],
        activity_type="campaign_boss",
        participant_character_ids=(ids["Alpha"], ids["Bravo"], ids["Cedar"]),
        journey_reference_character_id=ids["Alpha"],
        context_payload={"mission": "P1", "objective": "scripted_dog"},
        eligibility_resolver=eligibility,
        now=NOW,
    )
    assert proposal.expires_at - proposal.created_at == ACTIVITY_CONFIRMATION_TTL
    assert proposal.status == "pending"
    assert {p.eligibility for p in proposal.participants} == {
        "eligible",
        "helper",
        "ineligible",
    }
    assert next(p for p in proposal.participants if p.name == "Cedar").eligibility == "ineligible"
    assert next(p for p in proposal.participants if p.name == "Alpha").response == "accepted"
    with pytest.raises(GroupError, match="not_ready"):
        await service.start_activity(
            actors["Alpha"],
            proposal.proposal_id,
            expected_revision=proposal.revision,
            eligibility_resolver=eligibility,
            create_activity=_create_activity,
            now=NOW + timedelta(seconds=2),
        )

    confirmed = await service.respond_activity(
        actors["Bravo"],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
        now=NOW + timedelta(seconds=3),
    )
    assert confirmed.status == "ready"

    created: list[UUID] = []

    async def create_once(_session, record, roster):
        created.append(record.id)
        assert {character.name for character in roster} == {"Alpha", "Bravo"}
        return f"campaign:{record.id.hex}"

    started = await service.start_activity(
        actors["Alpha"],
        proposal.proposal_id,
        expected_revision=confirmed.revision,
        eligibility_resolver=eligibility,
        create_activity=create_once,
        now=NOW + timedelta(seconds=4),
    )
    assert started.started
    assert started.activity_reference == f"campaign:{proposal.proposal_id.hex}"
    assert created == [proposal.proposal_id]

    duplicate = await service.start_activity(
        actors["Alpha"],
        proposal.proposal_id,
        expected_revision=confirmed.revision,
        eligibility_resolver=eligibility,
        create_activity=create_once,
        now=NOW + timedelta(seconds=5),
    )
    assert duplicate.started
    assert duplicate.activity_reference == started.activity_reference
    assert created == [proposal.proposal_id]

    with pytest.raises(GroupError, match="activity_in_progress"):
        await service.leave(actors["Bravo"], expected_group_revision=group_revision)
    finished = await service.finish_activity(proposal.proposal_id, succeeded=True)
    assert finished.status == "completed"


async def _create_activity(_session, proposal, _roster):
    return f"campaign:{proposal.id.hex}"


@pytest.mark.asyncio
async def test_ready_check_expiry_decline_and_revalidation_release_reservations(database):
    actors = await _seed_characters(database)
    service = _service(database)
    group = await service.create_group(actors["Alpha"])
    group = await _invite_and_join(service, actors["Alpha"], actors["Bravo"], "Bravo")
    ids = {member.name: member.character_id for member in group.members}
    stale = {"Bravo": False}

    async def eligibility(_session, character, _context):
        if character.name == "Bravo" and stale["Bravo"]:
            return ActivityEligibility("ineligible", fingerprint="not-at-checkpoint")
        return ActivityEligibility("eligible", fingerprint="P1:signal-two")

    proposal = await service.propose_activity(
        actors["Alpha"],
        activity_type="campaign",
        participant_character_ids=(ids["Alpha"], ids["Bravo"]),
        eligibility_resolver=eligibility,
        now=NOW,
    )
    declined = await service.respond_activity(
        actors["Bravo"],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=False,
        now=NOW + timedelta(seconds=1),
    )
    assert declined.status == "declined"

    proposal = await service.propose_activity(
        actors["Alpha"],
        activity_type="campaign",
        participant_character_ids=(ids["Alpha"], ids["Bravo"]),
        eligibility_resolver=eligibility,
        now=NOW + timedelta(minutes=1),
    )
    ready = await service.respond_activity(
        actors["Bravo"],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
        now=NOW + timedelta(minutes=1, seconds=1),
    )
    stale["Bravo"] = True
    created: list[str] = []

    async def create_should_not_run(_session, _record, _roster):
        created.append("created")
        return "must-not-exist"

    result = await service.start_activity(
        actors["Alpha"],
        proposal.proposal_id,
        expected_revision=ready.revision,
        eligibility_resolver=eligibility,
        create_activity=create_should_not_run,
        now=NOW + timedelta(minutes=1, seconds=2),
    )
    assert not result.started
    assert result.reason == "eligibility_changed"
    assert result.proposal.status == "cancelled"
    assert created == []

    proposal = await service.propose_activity(
        actors["Alpha"],
        activity_type="campaign",
        participant_character_ids=(ids["Alpha"], ids["Bravo"]),
        eligibility_resolver=eligibility,
        now=NOW + timedelta(minutes=2),
    )
    expired = await service.activity_proposal(
        actors["Alpha"],
        proposal.proposal_id,
        now=NOW + timedelta(minutes=2) + ACTIVITY_CONFIRMATION_TTL,
    )
    assert expired.status == "expired"


@pytest.mark.asyncio
async def test_activity_membership_callbacks_are_revision_stale_safe(database):
    actors = await _seed_characters(database)
    service = _service(database)
    group = await service.create_group(actors["Alpha"])
    group = await _invite_and_join(service, actors["Alpha"], actors["Bravo"], "Bravo")
    ids = {member.name: member.character_id for member in group.members}

    async def eligibility(_session, _character, _context):
        return ActivityEligibility("eligible", fingerprint="same-checkpoint")

    proposal = await service.propose_activity(
        actors["Alpha"],
        activity_type="campaign",
        participant_character_ids=(ids["Alpha"], ids["Bravo"]),
        eligibility_resolver=eligibility,
        now=NOW,
    )
    with pytest.raises(GroupError, match="stale"):
        await service.respond_activity(
            actors["Bravo"],
            proposal.proposal_id,
            expected_revision=proposal.revision + 1,
            accept=True,
            now=NOW + timedelta(seconds=1),
        )
    current = await service.activity_proposal(
        actors["Alpha"], proposal.proposal_id, now=NOW + timedelta(seconds=1)
    )
    assert current.status == "pending"


@pytest.mark.asyncio
async def test_due_character_deletion_transfers_group_leadership_and_cancels_ready_check(
    database,
):
    actors = await _seed_characters(database)
    service = _service(database)
    group = await service.create_group(actors["Alpha"])
    group = await _invite_and_join(service, actors["Alpha"], actors["Bravo"], "Bravo")
    alpha_id = next(member.character_id for member in group.members if member.name == "Alpha")
    bravo_id = next(member.character_id for member in group.members if member.name == "Bravo")

    async def eligibility(_session, _character, _context):
        return ActivityEligibility("eligible", fingerprint="P1:checkpoint-1")

    proposal = await service.propose_activity(
        actors["Bravo"],
        activity_type="campaign",
        participant_character_ids=(alpha_id, bravo_id),
        journey_reference_character_id=bravo_id,
        eligibility_resolver=eligibility,
        now=NOW,
    )
    ready = await service.respond_activity(
        actors["Alpha"],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
        now=NOW + timedelta(seconds=1),
    )
    assert ready.status == "ready"

    async with database[1].begin() as session:
        session.add(
            CharacterDeletionRequest(
                id=uuid4(),
                character_id=alpha_id,
                telegram_id=actors["Alpha"],
                server_id="ocaso",
                name_at_request="Alpha",
                requested_at=NOW - timedelta(days=7),
                due_at=NOW,
                status="pending",
                revision=1,
            )
        )

    assert await finalize_due_character_deletions(database[1], "ocaso", now=NOW) == 1

    surviving_group = await service.group(actors["Bravo"])
    assert surviving_group is not None
    assert surviving_group.leader_character_id == bravo_id
    assert [member.name for member in surviving_group.members] == ["Bravo"]
    cancelled = await service.activity_proposal(
        actors["Bravo"], proposal.proposal_id, now=NOW + timedelta(seconds=2)
    )
    assert cancelled.status == "cancelled"
    assert cancelled.cancel_reason == "participant_deletion"
    async with database[1]() as session:
        assert await session.get(Character, alpha_id) is None
        participants = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant).where(
                        GroupActivityParticipant.proposal_id == proposal.proposal_id
                    )
                )
            ).all()
        )
        assert len(participants) == 1
        assert participants[0].character_id == bravo_id
        assert participants[0].reservation_state == "released"


@pytest.mark.asyncio
async def test_due_character_deletion_waits_for_live_group_roster(database):
    actors = await _seed_characters(database)
    service = _service(database)
    group = await service.create_group(actors["Alpha"])
    group = await _invite_and_join(service, actors["Alpha"], actors["Bravo"], "Bravo")
    alpha_id = next(member.character_id for member in group.members if member.name == "Alpha")
    bravo_id = next(member.character_id for member in group.members if member.name == "Bravo")

    async def eligibility(_session, _character, _context):
        return ActivityEligibility("eligible", fingerprint="P1:checkpoint-1")

    proposal = await service.propose_activity(
        actors["Alpha"],
        activity_type="campaign",
        participant_character_ids=(alpha_id, bravo_id),
        eligibility_resolver=eligibility,
        now=NOW,
    )
    ready = await service.respond_activity(
        actors["Bravo"],
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
        now=NOW + timedelta(seconds=1),
    )
    started = await service.start_activity(
        actors["Alpha"],
        proposal.proposal_id,
        expected_revision=ready.revision,
        eligibility_resolver=eligibility,
        create_activity=_create_activity,
        now=NOW + timedelta(seconds=2),
    )
    assert started.started

    async with database[1].begin() as session:
        session.add(
            CharacterDeletionRequest(
                id=uuid4(),
                character_id=alpha_id,
                telegram_id=actors["Alpha"],
                server_id="ocaso",
                name_at_request="Alpha",
                requested_at=NOW - timedelta(days=7),
                due_at=NOW,
                status="pending",
                revision=1,
            )
        )

    assert await finalize_due_character_deletions(database[1], "ocaso", now=NOW) == 0
    async with database[1]() as session:
        assert await session.get(Character, alpha_id) is not None
        persisted = await session.get(GroupActivityProposal, proposal.proposal_id)
        membership = await session.get(SocialGroupMember, alpha_id)
        social_group = await session.get(SocialGroup, group.group_id)
        participant = await session.get(GroupActivityParticipant, (proposal.proposal_id, alpha_id))
        assert persisted is not None and persisted.status == "started"
        assert membership is not None and social_group is not None
        assert participant is not None and participant.reservation_state == "active"
