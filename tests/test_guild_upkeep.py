"""Guild Treasury, Obras, Rename, Dissolution, Succession and deletion (GDD v1.6.0 §30.2-§30.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.account import finalize_due_character_deletions
from asterion.application.guilds import GuildError, GuildService
from asterion.domain.guilds import GuildRole, ProjectKind
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterDeletionRequest,
    Guild,
    GuildAuditEntry,
    GuildInvite,
    GuildMember,
    GuildSwitchCooldown,
    GuildTreasuryEntry,
)

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
NAMES = ("Alpha", "Bravo", "Cedar", "Doran", "Elian", "Faris")
ACTORS = {name: 840001 + index for index, name in enumerate(NAMES)}


async def _seed(database, crowns: int = 500_000) -> dict[str, int]:
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
                    crowns=crowns,
                )
            )
    return ACTORS


async def _code(awaitable) -> str:
    with pytest.raises(GuildError) as error:
        await awaitable
    return error.value.code


async def _guild_with(service, a, members=("Bravo", "Cedar"), now=NOW):
    guild = await service.create_guild(a["Alpha"], "Vigilia", "VGL", now=now)
    ids = {"Alpha": guild.viewer_character_id}
    for name in members:
        invite = await service.invite(a["Alpha"], name, now=now)
        view = await service.respond_invite(a[name], invite.invite_id, accept=True, now=now)
        ids[name] = view.viewer_character_id
    return guild, ids


async def _crowns(database, name: str) -> int:
    async with database[1]() as session:
        return await session.scalar(select(Character.crowns).where(Character.name == name))


@pytest.mark.asyncio
async def test_deposits_are_final_and_obras_fund_from_wallet_or_treasury(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    await _guild_with(service, a)

    view = await service.deposit(a["Bravo"], 30_000, now=NOW)
    assert view.treasury_crowns == 30_000
    assert await _crowns(database, "Bravo") == 470_000
    assert await _code(service.deposit(a["Cedar"], 600_000, now=NOW)) == "not_enough_crowns"
    assert await _code(service.deposit(a["Cedar"], 0, now=NOW)) == "invalid_amount"

    assert await _code(service.start_project(a["Bravo"], ProjectKind.LODGING, now=NOW)) == (
        "no_permission"
    )
    view = await service.start_project(a["Alpha"], ProjectKind.LODGING, now=NOW)
    [project] = view.active_projects
    assert (project.kind, project.level, project.cost, project.status) == (
        ProjectKind.LODGING,
        1,
        20_000,
        "funding",
    )
    assert await _code(service.start_project(a["Alpha"], ProjectKind.LODGING, now=NOW)) == (
        "project_active"
    )
    await service.start_project(a["Alpha"], ProjectKind.FORGE, now=NOW)
    assert await _code(service.start_project(a["Alpha"], ProjectKind.WAR_HALL, now=NOW)) == (
        "too_many_projects"
    )

    # A member contributes from the wallet; only the Leader spends the Treasury.
    result = await service.contribute(a["Cedar"], project.project_id, 5_000, now=NOW)
    assert result.applied == 5_000
    assert (
        await _code(
            service.contribute(a["Cedar"], project.project_id, 1, from_treasury=True, now=NOW)
        )
        == "no_permission"
    )
    # Contribution is capped to what is still missing: 15.000 of the 30.000 offered.
    result = await service.contribute(
        a["Alpha"], project.project_id, 30_000, from_treasury=True, now=NOW
    )
    assert result.applied == 15_000
    assert result.guild.treasury_crowns == 15_000
    building = next(p for p in result.guild.active_projects if p.kind is ProjectKind.LODGING)
    assert building.status == "building"
    assert building.completes_at == NOW + timedelta(hours=6)
    assert await _code(service.contribute(a["Cedar"], project.project_id, 1, now=NOW)) == (
        "project_not_funding"
    )
    assert await _crowns(database, "Cedar") == 495_000

    before = await service.my_guild(a["Alpha"], now=NOW + timedelta(hours=5, minutes=59))
    assert before.capacity == 5
    after = await service.my_guild(a["Alpha"], now=NOW + timedelta(hours=6))
    assert after.capacity == 7
    assert dict(after.obra_levels)[ProjectKind.LODGING] == 1
    assert [p.kind for p in after.active_projects] == [ProjectKind.FORGE]

    nxt = await service.start_project(a["Alpha"], ProjectKind.LODGING, now=NOW + timedelta(hours=7))
    assert next(p for p in nxt.active_projects if p.kind is ProjectKind.LODGING).cost == 35_000


@pytest.mark.asyncio
async def test_rename_costs_treasury_has_recharge_and_retains_old_name(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    await _guild_with(service, a, members=("Bravo",))
    assert await _code(service.rename(a["Alpha"], name="Brasa", now=NOW)) == (
        "treasury_insufficient"
    )
    await service.deposit(a["Bravo"], 40_000, now=NOW)
    assert await _code(service.rename(a["Bravo"], name="Brasa", now=NOW)) == "no_permission"
    assert await _code(service.rename(a["Alpha"], name="Vigilia", now=NOW)) == ("rename_unchanged")
    view = await service.rename(a["Alpha"], name="Brasa", tag="brs", now=NOW)
    assert (view.name, view.tag, view.treasury_crowns) == ("Brasa", "BRS", 25_000)
    assert view.rename_available_at == NOW + timedelta(days=30)
    # Keep the Leader active, otherwise the 168h succession would hand over the role.
    await service.record_activity(a["Alpha"], now=NOW + timedelta(days=29))
    assert await _code(service.rename(a["Alpha"], tag="BRA", now=NOW + timedelta(days=29))) == (
        "rename_cooldown"
    )

    # The old Name and TAG stay reserved for 30 days.
    assert (
        await _code(
            service.create_guild(a["Cedar"], "vigilia", "XYZ", now=NOW + timedelta(days=29))
        )
        == "name_or_tag_reserved"
    )
    assert (
        await _code(service.create_guild(a["Cedar"], "Outra", "VGL", now=NOW + timedelta(days=29)))
        == "name_or_tag_reserved"
    )
    reborn = await service.create_guild(a["Cedar"], "Vigilia", "VGL", now=NOW + timedelta(days=30))
    assert reborn.name == "Vigilia"
    assert (await service.rename(a["Alpha"], tag="BRA", now=NOW + timedelta(days=30))).tag == "BRA"


@pytest.mark.asyncio
async def test_dissolution_waits_72h_freezes_treasury_and_forfeits_the_balance(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    guild, ids = await _guild_with(service, a)
    await service.deposit(a["Bravo"], 50_000, now=NOW)
    await service.start_project(a["Alpha"], ProjectKind.FORGE, now=NOW)
    forge = (await service.my_guild(a["Alpha"], now=NOW)).active_projects[0]
    await service.contribute(a["Cedar"], forge.project_id, 4_000, now=NOW)

    assert await _code(service.request_dissolution(a["Bravo"], now=NOW)) == "no_permission"
    view = await service.request_dissolution(a["Alpha"], now=NOW)
    assert view.dissolution_due_at == NOW + timedelta(hours=72)
    assert await _code(service.deposit(a["Bravo"], 1, now=NOW)) == "guild_dissolving"
    assert await _code(service.rename(a["Alpha"], name="Brasa", now=NOW)) == "guild_dissolving"
    cancelled = await service.cancel_dissolution(a["Alpha"], now=NOW + timedelta(hours=1))
    assert cancelled.dissolution_due_at is None
    await service.deposit(a["Bravo"], 1_000, now=NOW + timedelta(hours=1))

    start = NOW + timedelta(hours=2)
    await service.request_dissolution(a["Alpha"], now=start)
    assert await service.run_maintenance(now=start + timedelta(hours=71)) == 0
    assert await service.run_maintenance(now=start + timedelta(hours=72)) == 1
    assert await service.my_guild(a["Alpha"], now=start + timedelta(hours=72)) is None

    async with database[1]() as session:
        row = await session.get(Guild, guild.guild_id)
        assert (row.status, row.treasury_crowns) == ("dissolved", 0)
        assert (
            await session.scalar(
                select(func.count()).select_from(GuildMember).where(GuildMember.guild_id == row.id)
            )
            == 0
        )
        forfeit = await session.scalar(
            select(GuildTreasuryEntry.amount).where(
                GuildTreasuryEntry.guild_id == row.id, GuildTreasuryEntry.kind == "forfeit"
            )
        )
        assert forfeit == -51_000
        details = await session.scalar(
            select(GuildAuditEntry.details).where(
                GuildAuditEntry.guild_id == row.id, GuildAuditEntry.action == "guild_dissolved"
            )
        )
        assert details["forfeited_project_funds"] == 4_000
        assert await session.scalar(select(func.count()).select_from(GuildSwitchCooldown)) == 3
    # Name and TAG are free again; members wait the 12h cooldown.
    assert (
        await _code(
            service.create_guild(a["Bravo"], "Vigilia", "VGL", now=start + timedelta(hours=73))
        )
        == "switch_cooldown"
    )
    again = await service.create_guild(
        a["Doran"], "Vigilia", "VGL", now=start + timedelta(hours=73)
    )
    assert again.tag == "VGL"


@pytest.mark.asyncio
async def test_obra_in_construction_holds_the_final_dissolution(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    guild, _ids = await _guild_with(service, a, members=())
    await service.start_project(a["Alpha"], ProjectKind.LODGING, now=NOW)
    lodging = (await service.my_guild(a["Alpha"], now=NOW)).active_projects[0]
    await service.contribute(a["Alpha"], lodging.project_id, 20_000, now=NOW)  # builds to +6h
    await service.request_dissolution(a["Alpha"], now=NOW)
    # Make the 72h period end while the Obra is still under Construção.
    async with database[1].begin() as session:
        row = await session.get(Guild, guild.guild_id)
        row.dissolution_due_at = NOW + timedelta(hours=1)
    assert await service.my_guild(a["Alpha"], now=NOW + timedelta(hours=2)) is not None
    assert await service.my_guild(a["Alpha"], now=NOW + timedelta(hours=6)) is None


@pytest.mark.asyncio
async def test_inactive_leader_is_succeeded_by_the_longest_officer(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    _guild, ids = await _guild_with(service, a, members=("Bravo", "Cedar", "Doran"))
    await service.promote(a["Alpha"], ids["Cedar"], now=NOW)
    await service.promote(a["Alpha"], ids["Bravo"], now=NOW + timedelta(minutes=1))

    almost = NOW + timedelta(hours=167, minutes=59)
    await service.record_activity(a["Doran"], now=almost)
    view = await service.my_guild(a["Doran"], now=almost)
    assert next(m for m in view.members if m.role is GuildRole.LEADER).character_id == ids["Alpha"]

    later = NOW + timedelta(minutes=1) + timedelta(hours=168)
    assert await service.run_maintenance(now=later) == 1
    view = await service.my_guild(a["Doran"], now=later)
    roles = {m.character_id: m.role for m in view.members}
    assert roles[ids["Cedar"]] is GuildRole.LEADER  # Officer since NOW: the longest
    assert roles[ids["Alpha"]] is GuildRole.OFFICER
    assert roles[ids["Bravo"]] is GuildRole.OFFICER
    # A fresh Leader is not succeeded again right away.
    assert await service.run_maintenance(now=later + timedelta(hours=1)) == 0


@pytest.mark.asyncio
async def test_active_leader_keeps_the_role_and_lone_leader_is_left_alone(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    _guild, ids = await _guild_with(service, a, members=("Bravo",))
    await service.record_activity(a["Alpha"], now=NOW + timedelta(hours=100))
    await service.run_maintenance(now=NOW + timedelta(hours=200))
    view = await service.my_guild(a["Bravo"], now=NOW + timedelta(hours=200))
    assert dict((m.character_id, m.role) for m in view.members)[ids["Alpha"]] is GuildRole.LEADER

    solo = await service.create_guild(a["Faris"], "Solo", "SOL", now=NOW)
    later = NOW + timedelta(days=60)
    await service.run_maintenance(now=later)
    alone = await service.my_guild(a["Faris"], now=later)
    assert (alone.guild_id, alone.viewer_role) == (solo.guild_id, GuildRole.LEADER)


async def _request_deletion(database, name: str, actor: int) -> None:
    async with database[1].begin() as session:
        character_id = await session.scalar(select(Character.id).where(Character.name == name))
        session.add(
            CharacterDeletionRequest(
                id=uuid4(),
                character_id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name_at_request=name,
                requested_at=NOW - timedelta(days=7),
                due_at=NOW,
                status="pending",
                revision=1,
            )
        )


@pytest.mark.asyncio
async def test_deleting_the_leader_passes_the_role_and_keeps_history(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    guild, ids = await _guild_with(service, a, members=("Bravo", "Cedar"))
    await service.promote(a["Alpha"], ids["Bravo"], now=NOW)
    sent = await service.invite(a["Bravo"], "Doran", now=NOW)

    # Deleting an Officer keeps the audit log and the invites that Officer sent.
    await _request_deletion(database, "Bravo", a["Bravo"])
    assert await finalize_due_character_deletions(database[1], "ocaso", now=NOW) == 1
    async with database[1]() as session:
        invite = await session.get(GuildInvite, sent.invite_id)
        assert (invite.status, invite.inviter_character_id) == ("pending", None)
        assert (
            await session.scalar(
                select(func.count())
                .select_from(GuildAuditEntry)
                .where(GuildAuditEntry.action == "officer_promoted")
            )
            == 1
        )
        assert await session.get(GuildSwitchCooldown, (a["Bravo"], "ocaso")) is not None

    await _request_deletion(database, "Alpha", a["Alpha"])
    assert await finalize_due_character_deletions(database[1], "ocaso", now=NOW) == 1
    view = await service.my_guild(a["Cedar"], now=NOW)
    assert [(m.character_id, m.role) for m in view.members] == [(ids["Cedar"], GuildRole.LEADER)]
    assert view.guild_id == guild.guild_id


@pytest.mark.asyncio
async def test_deleting_a_sole_member_leader_dissolves_the_guild(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    guild, _ids = await _guild_with(service, a, members=())
    await service.deposit(a["Alpha"], 10_000, now=NOW)
    await _request_deletion(database, "Alpha", a["Alpha"])
    assert await finalize_due_character_deletions(database[1], "ocaso", now=NOW) == 1
    async with database[1]() as session:
        row = await session.get(Guild, guild.guild_id)
        assert (row.status, row.treasury_crowns) == ("dissolved", 0)
    assert (await service.create_guild(a["Bravo"], "Vigilia", "VGL", now=NOW)).tag == "VGL"


@pytest.mark.asyncio
async def test_permanent_ban_of_the_leader_starts_succession_at_once(database):
    a = await _seed(database)
    service = GuildService(database[1], "ocaso")
    _guild, ids = await _guild_with(service, a, members=("Bravo", "Cedar"))
    await service.promote(a["Alpha"], ids["Cedar"], now=NOW)
    # Not the Leader: nothing happens.
    assert await service.handle_permanent_ban(ids["Bravo"], now=NOW) is None
    assert await service.handle_permanent_ban(ids["Alpha"], now=NOW) == ids["Cedar"]
    view = await service.my_guild(a["Cedar"], now=NOW)
    roles = {m.character_id: m.role for m in view.members}
    assert roles[ids["Cedar"]] is GuildRole.LEADER
    assert roles[ids["Alpha"]] is GuildRole.MEMBER
