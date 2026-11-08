"""PostgreSQL integration tests for Guild core (GDD v1.6.0 §30, §49.18, §55.5)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.guilds import GuildError, GuildService
from asterion.domain.guilds import GuildRole, Recruitment
from asterion.infrastructure.db.models import (
    Account,
    Character,
    GuildApplication,
    GuildAuditEntry,
    GuildInvite,
    GuildMember,
)

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
NAMES = (
    "Alpha", "Bravo", "Cedar", "Doran", "Elian", "Faris", "Gwyn", "Halor", "Ilsa", "Joren",
)  # fmt: skip
ACTORS = {name: 830001 + index for index, name in enumerate(NAMES)}


async def _seed(database) -> dict[str, int]:
    async with database[1].begin() as session:
        for name, actor in ACTORS.items():
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
    return ACTORS


def _service(database) -> GuildService:
    return GuildService(database[1], "ocaso")


async def _code(awaitable) -> str:
    with pytest.raises(GuildError) as error:
        await awaitable
    return error.value.code


async def _invite_in(service, inviter: int, target: int, name: str, now=NOW):
    invite = await service.invite(inviter, name, now=now)
    return await service.respond_invite(target, invite.invite_id, accept=True, now=now)


async def _character_id(database, name: str):
    async with database[1]() as session:
        return await session.scalar(select(Character.id).where(Character.name == name))


@pytest.mark.asyncio
async def test_founding_is_free_unique_and_makes_the_founder_leader(database):
    a = await _seed(database)
    service = _service(database)
    guild = await service.create_guild(a["Alpha"], "Vigilia", "vgl", now=NOW)
    assert (guild.name, guild.tag, guild.viewer_role) == ("Vigilia", "VGL", GuildRole.LEADER)
    assert (guild.member_count, guild.capacity, guild.recruitment) == (1, 5, Recruitment.CLOSED)

    assert await _code(service.create_guild(a["Bravo"], "VIGILIA", "XYZ")) == ("name_or_tag_taken")
    assert await _code(service.create_guild(a["Bravo"], "Outra", "VGL")) == "name_or_tag_taken"
    assert await _code(service.create_guild(a["Bravo"], "Os Vigias", "ABC")) == "invalid_name"
    assert await _code(service.create_guild(a["Bravo"], "Outra", "A1C")) == "invalid_tag"
    assert await _code(service.create_guild(a["Alpha"], "Segunda", "SEG")) == "already_in_guild"


@pytest.mark.asyncio
async def test_invites_need_officer_rights_are_idempotent_and_die_after_another_entry(database):
    a = await _seed(database)
    service = _service(database)
    first = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    second = await service.create_guild(a["Bravo"], "Brasa", "BRS", now=NOW)

    sent = await service.invite(a["Alpha"], "cedar", now=NOW)
    again = await service.invite(a["Alpha"], "Cedar", now=NOW)
    assert again.invite_id == sent.invite_id
    rival = await service.invite(a["Bravo"], "Cedar", now=NOW)
    assert {i.guild_id for i in await service.incoming_invites(a["Cedar"])} == {
        first.guild_id,
        second.guild_id,
    }

    joined = await service.respond_invite(a["Cedar"], sent.invite_id, accept=True, now=NOW)
    assert joined.viewer_role is GuildRole.MEMBER
    assert (
        await _code(service.respond_invite(a["Cedar"], rival.invite_id, accept=True, now=NOW))
        == "invite_unusable"
    )
    assert await service.incoming_invites(a["Cedar"]) == ()

    # A common Member cannot invite; an Officer can, and may cancel Guild invites.
    assert await _code(service.invite(a["Cedar"], "Doran", now=NOW)) == "no_permission"
    await service.promote(a["Alpha"], joined.viewer_character_id, now=NOW)
    officer_invite = await service.invite(a["Cedar"], "Doran", now=NOW)
    await service.cancel_invite(a["Cedar"], officer_invite.invite_id, now=NOW)
    assert (
        await _code(
            service.respond_invite(a["Doran"], officer_invite.invite_id, accept=True, now=NOW)
        )
        == "invite_unusable"
    )
    assert await _code(service.invite(a["Alpha"], "Bravo", now=NOW)) == "target_in_guild"


@pytest.mark.asyncio
async def test_closed_guild_still_invites_and_full_guild_blocks_every_entry(database):
    a = await _seed(database)
    service = _service(database)
    guild = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    assert guild.recruitment is Recruitment.CLOSED
    for name in ("Bravo", "Cedar", "Doran", "Elian"):
        await _invite_in(service, a["Alpha"], a[name], name)
    full = await service.my_guild(a["Alpha"], now=NOW)
    assert (full.member_count, full.capacity) == (5, 5)

    assert await _code(service.invite(a["Alpha"], "Faris", now=NOW)) == "guild_full"
    await service.set_recruitment(a["Alpha"], Recruitment.OPEN, now=NOW)
    assert await _code(service.apply(a["Faris"], guild.guild_id, now=NOW)) == "guild_full"
    page = await service.public_page(guild.guild_id, now=NOW)
    assert page.accepts_applications is False
    assert (await service.recruiting()).items == ()


@pytest.mark.asyncio
async def test_application_limits_from_section_49_18(database):
    a = await _seed(database)
    service = _service(database)
    guild_ids = []
    for leader, name, tag in (
        ("Alpha", "Vigilia", "VGL"),
        ("Bravo", "Brasa", "BRS"),
        ("Cedar", "Cinza", "CNZ"),
        ("Doran", "Dobra", "DBR"),
    ):
        created = await service.create_guild(a[leader], name, tag, now=NOW)
        await service.set_recruitment(a[leader], Recruitment.OPEN, now=NOW)
        guild_ids.append(created.guild_id)

    applicant = a["Joren"]
    first = await service.apply(applicant, guild_ids[0], now=NOW)
    assert first.status == "pending"
    assert await _code(service.apply(applicant, guild_ids[0], now=NOW)) == "application_pending"
    await service.apply(applicant, guild_ids[1], now=NOW)
    await service.apply(applicant, guild_ids[2], now=NOW)
    assert await _code(service.apply(applicant, guild_ids[3], now=NOW)) == "too_many_pending"

    # Cancelling frees a slot, but the same Guild waits 10 min.
    await service.cancel_application(applicant, first.application_id, now=NOW)
    at = NOW + timedelta(minutes=5)
    assert await _code(service.apply(applicant, guild_ids[0], now=at)) == (
        "application_rate_limited"
    )
    await service.apply(applicant, guild_ids[3], now=at)  # 4th created

    async def reapply(guild_index: int, minutes: int) -> None:
        pending = {x.guild_id: x for x in await service.my_applications(applicant)
                   if x.status == "pending"}  # fmt: skip
        when = NOW + timedelta(minutes=minutes)
        await service.cancel_application(
            applicant, pending[guild_ids[guild_index]].application_id, now=when
        )
        await service.apply(applicant, guild_ids[guild_index], now=when)

    await reapply(1, 11)  # 5th created
    await reapply(2, 12)  # 6th created
    pending = [x for x in await service.my_applications(applicant) if x.status == "pending"]
    assert len(pending) == 3
    await service.cancel_application(
        applicant, pending[0].application_id, now=NOW + timedelta(minutes=20)
    )

    # Six new applications per 60 minutes, whatever their state.
    assert (
        await _code(service.apply(applicant, guild_ids[0], now=NOW + timedelta(minutes=20)))
        == "application_rate_limited"
    )
    resumed = await service.apply(applicant, guild_ids[0], now=NOW + timedelta(minutes=61))
    assert resumed.status == "pending"


@pytest.mark.asyncio
async def test_closed_recruitment_blocks_new_applications_but_keeps_pending(database):
    a = await _seed(database)
    service = _service(database)
    guild = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    assert await _code(service.apply(a["Bravo"], guild.guild_id, now=NOW)) == ("recruitment_closed")
    assert (
        await _code(service.set_recruitment(a["Bravo"], Recruitment.OPEN, now=NOW))
        == "not_in_guild"
    )
    await service.set_recruitment(a["Alpha"], Recruitment.OPEN, now=NOW)
    application = await service.apply(a["Bravo"], guild.guild_id, now=NOW)
    await service.set_recruitment(a["Alpha"], Recruitment.CLOSED, now=NOW)
    received = await service.received_applications(a["Alpha"])
    assert [x.application_id for x in received] == [application.application_id]
    approved = await service.approve_application(a["Alpha"], application.application_id, now=NOW)
    assert approved.status == "approved"


@pytest.mark.asyncio
async def test_approval_is_atomic_entry_and_closes_every_other_entry(database):
    a = await _seed(database)
    service = _service(database)
    first = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    second = await service.create_guild(a["Bravo"], "Brasa", "BRS", now=NOW)
    for actor in (a["Alpha"], a["Bravo"]):
        await service.set_recruitment(actor, Recruitment.OPEN, now=NOW)
    app_first = await service.apply(a["Cedar"], first.guild_id, now=NOW)
    app_second = await service.apply(a["Cedar"], second.guild_id, now=NOW)
    invite = await service.invite(a["Bravo"], "Cedar", now=NOW)

    approved = await service.approve_application(a["Alpha"], app_first.application_id, now=NOW)
    assert approved.status == "approved"
    statuses = {x.application_id: (x.status, x.closed_by) for x in
                await service.my_applications(a["Cedar"])}  # fmt: skip
    assert statuses[app_second.application_id] == ("cancelled", "system")
    async with database[1]() as session:
        assert (await session.get(GuildInvite, invite.invite_id)).status == "invalidated"
    assert (
        await _code(service.approve_application(a["Bravo"], app_second.application_id, now=NOW))
        == "application_closed"
    )
    assert (
        await service.approve_application(a["Alpha"], app_first.application_id, now=NOW)
    ).status == "approved"


@pytest.mark.asyncio
async def test_failed_approval_keeps_pending_and_lost_role_cannot_approve(database):
    a = await _seed(database)
    service = _service(database)
    guild = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    await service.set_recruitment(a["Alpha"], Recruitment.OPEN, now=NOW)
    bravo = await _invite_in(service, a["Alpha"], a["Bravo"], "Bravo")
    await service.promote(a["Alpha"], bravo.viewer_character_id, now=NOW)
    applications = [
        await service.apply(a[name], guild.guild_id, now=NOW)
        for name in ("Cedar", "Doran", "Elian", "Faris")
    ]
    for application in applications[:3]:
        await service.approve_application(a["Bravo"], application.application_id, now=NOW)
    assert (
        await _code(
            service.approve_application(a["Alpha"], applications[3].application_id, now=NOW)
        )
        == "guild_full"
    )
    still = await service.my_applications(a["Faris"])
    assert still[0].status == "pending"

    # The Officer loses the role: an old Approve button grants nothing (§44.1).
    await service.demote(a["Alpha"], bravo.viewer_character_id, now=NOW)
    assert (
        await _code(service.reject_application(a["Bravo"], applications[3].application_id, now=NOW))
        == "no_permission"
    )
    await service.reject_application(a["Alpha"], applications[3].application_id, now=NOW)
    assert (await service.my_applications(a["Faris"]))[0].status == "rejected"


@pytest.mark.asyncio
async def test_application_of_someone_who_joined_elsewhere_is_closed_by_the_system(database):
    a = await _seed(database)
    service = _service(database)
    guild = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    await service.set_recruitment(a["Alpha"], Recruitment.OPEN, now=NOW)
    application = await service.apply(a["Cedar"], guild.guild_id, now=NOW)
    await service.create_guild(a["Bravo"], "Brasa", "BRS", now=NOW)
    # Joining by invite already system-cancels the pending application.
    await _invite_in(service, a["Bravo"], a["Cedar"], "Cedar")
    assert (
        await _code(service.approve_application(a["Alpha"], application.application_id, now=NOW))
        == "application_closed"
    )
    mine = await service.my_applications(a["Cedar"])
    assert (mine[0].status, mine[0].closed_by) == ("cancelled", "system")


@pytest.mark.asyncio
async def test_roles_removal_leave_and_the_12h_switch_cooldown(database):
    a = await _seed(database)
    service = _service(database)
    guild = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    bravo = await _invite_in(service, a["Alpha"], a["Bravo"], "Bravo")
    cedar = await _invite_in(service, a["Alpha"], a["Cedar"], "Cedar")
    doran = await _invite_in(service, a["Alpha"], a["Doran"], "Doran")
    bravo_id, cedar_id, doran_id = (
        bravo.viewer_character_id,
        cedar.viewer_character_id,
        doran.viewer_character_id,
    )
    alpha_id = guild.viewer_character_id
    await service.promote(a["Alpha"], bravo_id, now=NOW)
    await service.promote(a["Alpha"], cedar_id, now=NOW)

    assert await _code(service.remove_member(a["Bravo"], cedar_id, now=NOW)) == "no_permission"
    assert await _code(service.remove_member(a["Bravo"], alpha_id, now=NOW)) == "no_permission"
    assert await _code(service.promote(a["Bravo"], doran_id, now=NOW)) == "no_permission"
    assert await _code(service.leave(a["Alpha"], now=NOW)) == "leader_must_transfer"

    await service.remove_member(a["Bravo"], doran_id, now=NOW)
    await service.leave(a["Cedar"], now=NOW)
    await service.create_guild(a["Elian"], "Brasa", "BRS", now=NOW)
    for actor in (a["Doran"], a["Cedar"]):
        assert await _code(service.create_guild(actor, "Nova", "NOV", now=NOW)) == (
            "switch_cooldown"
        )
    invite = await service.invite(a["Elian"], "Doran", now=NOW)
    almost = NOW + timedelta(hours=11, minutes=59)
    assert (
        await _code(service.respond_invite(a["Doran"], invite.invite_id, accept=True, now=almost))
        == "switch_cooldown"
    )
    joined = await service.respond_invite(
        a["Doran"], invite.invite_id, accept=True, now=NOW + timedelta(hours=12)
    )
    assert joined.name == "Brasa"

    moved = await service.transfer_leadership(a["Alpha"], bravo_id, now=NOW)
    roles = {member.character_id: member.role for member in moved.members}
    assert roles[bravo_id] is GuildRole.LEADER
    assert roles[alpha_id] is GuildRole.OFFICER
    await service.leave(a["Alpha"], now=NOW)
    async with database[1]() as session:
        actions = set(
            (
                await session.scalars(
                    select(GuildAuditEntry.action).where(GuildAuditEntry.guild_id == guild.guild_id)
                )
            ).all()
        )
    assert {
        "guild_founded",
        "invite_sent",
        "member_joined",
        "officer_promoted",
        "member_removed",
        "member_left",
        "leadership_transferred",
    } <= actions


@pytest.mark.asyncio
async def test_search_public_page_and_stable_recruiting_pages(database):
    a = await _seed(database)
    service = _service(database)
    created = []
    for leader, name, tag in (
        ("Alpha", "Vigilia", "VGL"),
        ("Bravo", "Brasa", "BRS"),
        ("Cedar", "Cinza", "CNZ"),
    ):
        guild = await service.create_guild(a[leader], name, tag, now=NOW)
        created.append(guild.guild_id)
    for actor in (a["Alpha"], a["Bravo"]):
        await service.set_recruitment(actor, Recruitment.OPEN, now=NOW)

    by_tag = await service.search("cnz")
    assert [(g.name, g.accepts_applications) for g in by_tag] == [("Cinza", False)]
    assert [g.tag for g in await service.search("brasa")] == ["BRS"]
    assert await service.search("Bra sa") == ()
    other_server = GuildService(database[1], "outro")
    assert await other_server.search("Brasa") == ()
    assert await other_server.public_page(created[0], now=NOW) is None

    first = await service.recruiting(limit=1)
    second = await service.recruiting(after=first.next_after, limit=1)
    assert second.next_after is None
    assert {first.items[0].tag, second.items[0].tag} == {"VGL", "BRS"}
    page = await service.public_page(created[0], now=NOW)
    assert (page.name, page.tag, page.member_count, page.capacity) == ("Vigilia", "VGL", 1, 5)


@pytest.mark.asyncio
async def test_concurrent_entries_never_exceed_capacity_or_double_membership(database):
    a = await _seed(database)
    service = _service(database)
    guild = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=NOW)
    rival = await service.create_guild(a["Bravo"], "Brasa", "BRS", now=NOW)
    for actor in (a["Alpha"], a["Bravo"]):
        await service.set_recruitment(actor, Recruitment.OPEN, now=NOW)
    for name in ("Cedar", "Doran", "Elian"):
        await _invite_in(service, a["Alpha"], a[name], name)

    # Last slot: two approvals and one invite acceptance race.
    racers = [await service.apply(a[name], guild.guild_id, now=NOW) for name in ("Faris", "Gwyn")]
    invite = await service.invite(a["Alpha"], "Halor", now=NOW)
    results = await asyncio.gather(
        service.approve_application(a["Alpha"], racers[0].application_id, now=NOW),
        service.approve_application(a["Alpha"], racers[1].application_id, now=NOW),
        service.respond_invite(a["Halor"], invite.invite_id, accept=True, now=NOW),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert all(r.code == "guild_full" for r in results if isinstance(r, GuildError))

    # Same character approved by two Guilds at once: exactly one membership.
    third = await service.create_guild(a["Ilsa"], "Cinza", "CNZ", now=NOW)
    await service.set_recruitment(a["Ilsa"], Recruitment.OPEN, now=NOW)
    pair = [
        await service.apply(a["Joren"], gid, now=NOW) for gid in (rival.guild_id, third.guild_id)
    ]
    joren_results = await asyncio.gather(
        service.approve_application(a["Bravo"], pair[0].application_id, now=NOW),
        service.approve_application(a["Ilsa"], pair[1].application_id, now=NOW),
        return_exceptions=True,
    )
    joren_id = await _character_id(database, "Joren")
    async with database[1]() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(GuildMember)
            .where(GuildMember.guild_id == guild.guild_id)
        )
        joren = await session.scalar(
            select(func.count())
            .select_from(GuildMember)
            .where(GuildMember.character_id == joren_id)
        )
        approved = await session.scalar(
            select(func.count())
            .select_from(GuildApplication)
            .where(GuildApplication.character_id == joren_id, GuildApplication.status == "approved")
        )
    assert count == 5
    assert joren == 1
    assert approved == 1
    assert sum(not isinstance(result, Exception) for result in joren_results) == 1
