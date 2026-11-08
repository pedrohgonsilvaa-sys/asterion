"""Guild upkeep shared by the service and character deletion.

Completes due Obras, runs Leader succession and finalizes dissolution
(GDD v1.6.0 §30.2, §30.3, §49.18). Every function here expects the Guild row
to be already locked by the caller (lock order: Guild -> Character -> rows).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.guilds import (
    LEADER_INACTIVITY_LIMIT,
    GuildRole,
    ProjectKind,
    SuccessionCandidate,
    pick_successor,
)
from asterion.infrastructure.db.models import (
    Character,
    Guild,
    GuildApplication,
    GuildAuditEntry,
    GuildInvite,
    GuildMember,
    GuildProject,
    GuildSwitchCooldown,
    GuildTreasuryEntry,
)

ACTIVE_PROJECT_STATES = ("funding", "building")


def audit(
    session: AsyncSession,
    guild_id: UUID,
    action: str,
    actor_id: UUID | None,
    target_id: UUID | None,
    now: datetime,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        GuildAuditEntry(
            guild_id=guild_id,
            action=action,
            actor_character_id=actor_id,
            target_character_id=target_id,
            details=details or {},
            created_at=now,
        )
    )


async def start_cooldown(
    session: AsyncSession, telegram_id: int, server_id: str, now: datetime
) -> None:
    """Every exit starts the 12h switch cooldown for the account + server."""
    statement = insert(GuildSwitchCooldown).values(
        telegram_id=telegram_id, server_id=server_id, last_exit_at=now
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[GuildSwitchCooldown.telegram_id, GuildSwitchCooldown.server_id],
            set_={"last_exit_at": statement.excluded.last_exit_at},
        )
    )


def record_treasury(
    session: AsyncSession,
    guild: Guild,
    kind: str,
    amount: int,
    now: datetime,
    *,
    character_id: UUID | None = None,
    project_id: UUID | None = None,
) -> None:
    """Apply a signed Treasury movement and append it to the ledger."""
    balance = guild.treasury_crowns + amount
    if balance < 0:
        raise ValueError("treasury cannot go negative")
    guild.treasury_crowns = balance
    session.add(
        GuildTreasuryEntry(
            guild_id=guild.id,
            kind=kind,
            amount=amount,
            balance_after=balance,
            character_id=character_id,
            project_id=project_id,
            created_at=now,
        )
    )


def leader_inactive(member: GuildMember, now: datetime) -> bool:
    """168h without authenticated activity, counted from when the role began."""
    since = max(member.last_active_at, member.role_since)
    return since + LEADER_INACTIVITY_LIMIT <= now


async def maintenance_due(session: AsyncSession, guild: Guild, now: datetime) -> bool:
    """Cheap, lock-free check so reads only lock a Guild when something is due."""
    if guild.status != "active":
        return False
    if guild.dissolution_due_at is not None and guild.dissolution_due_at <= now:
        return True
    project_due = await session.scalar(
        select(GuildProject.id)
        .where(
            GuildProject.guild_id == guild.id,
            GuildProject.status == "building",
            GuildProject.completes_at <= now,
        )
        .limit(1)
    )
    if project_due is not None:
        return True
    members = (
        await session.scalars(select(GuildMember).where(GuildMember.guild_id == guild.id))
    ).all()
    leaders = [m for m in members if m.role == GuildRole.LEADER.value]
    if not leaders:
        return True
    return len(members) > 1 and leader_inactive(leaders[0], now)


async def settle(session: AsyncSession, guild: Guild, now: datetime) -> None:
    """Bring a locked, active Guild up to date. Idempotent."""
    if guild.status != "active":
        return
    await _complete_due_projects(session, guild, now)
    members = list(
        (
            await session.scalars(
                select(GuildMember)
                .where(GuildMember.guild_id == guild.id)
                .order_by(GuildMember.character_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
    )
    leader = next((m for m in members if m.role == GuildRole.LEADER.value), None)
    if not members:
        await finalize_dissolution(session, guild, now, reason="no_members")
        return
    if leader is None:
        await promote_successor(session, guild, members, None, now, reason="leader_missing")
    elif len(members) > 1 and leader_inactive(leader, now):
        await promote_successor(session, guild, members, leader, now, reason="inactivity")
    if guild.dissolution_due_at is not None and guild.dissolution_due_at <= now:
        building = await session.scalar(
            select(GuildProject.id)
            .where(GuildProject.guild_id == guild.id, GuildProject.status == "building")
            .limit(1)
        )
        # §30.3: an Obra under Construção must finish before the final dissolution.
        if building is None:
            await finalize_dissolution(session, guild, now, reason="requested")


async def _complete_due_projects(session: AsyncSession, guild: Guild, now: datetime) -> None:
    due = (
        await session.scalars(
            select(GuildProject)
            .where(
                GuildProject.guild_id == guild.id,
                GuildProject.status == "building",
                GuildProject.completes_at <= now,
            )
            .order_by(GuildProject.completes_at, GuildProject.id)
            .with_for_update()
        )
    ).all()
    for project in due:
        project.status = "completed"
        project.closed_at = project.completes_at
        project.revision += 1
        if project.kind == ProjectKind.LODGING.value:
            guild.lodging_level = max(guild.lodging_level, project.level)
        guild.revision += 1
        audit(
            session, guild.id, "project_completed", None, None, now,
            {"kind": project.kind, "level": project.level},
        )  # fmt: skip


async def promote_successor(
    session: AsyncSession,
    guild: Guild,
    members: list[GuildMember],
    old_leader: GuildMember | None,
    now: datetime,
    *,
    reason: str,
    old_leader_role: GuildRole = GuildRole.OFFICER,
) -> UUID | None:
    """§49.18 succession. The old Leader, if still a member, becomes Officer
    (or `old_leader_role`, e.g. Member after a permanent ban)."""
    candidates = [
        SuccessionCandidate(
            character_id=m.character_id,
            role=GuildRole(m.role),
            role_since=m.role_since,
            joined_at=m.joined_at,
        )
        for m in members
        if m is not old_leader
    ]
    successor_id = pick_successor(candidates)
    if successor_id is None:
        return None
    if old_leader is not None:
        old_leader.role = old_leader_role.value
        old_leader.role_since = now
        await session.flush()  # free the single-Leader index first
    successor = next(m for m in members if m.character_id == successor_id)
    successor.role = GuildRole.LEADER.value
    successor.role_since = now
    guild.revision += 1
    audit(
        session, guild.id, "leadership_succeeded",
        old_leader.character_id if old_leader else None, successor_id, now,
        {"reason": reason},
    )  # fmt: skip
    await session.flush()
    return successor_id


async def finalize_dissolution(
    session: AsyncSession,
    guild: Guild,
    now: datetime,
    *,
    reason: str,
    actor_id: UUID | None = None,
) -> None:
    """Close the Guild for good. Funding still in an Obra and the Treasury are lost
    (a sink, with explicit record); every member leaves with the 12h cooldown."""
    projects = (
        await session.scalars(
            select(GuildProject)
            .where(
                GuildProject.guild_id == guild.id,
                GuildProject.status.in_(ACTIVE_PROJECT_STATES),
            )
            .with_for_update()
        )
    ).all()
    lost_in_projects = 0
    for project in projects:
        lost_in_projects += project.funded
        project.status = "cancelled"
        project.closed_at = now
        project.revision += 1
    forfeited = guild.treasury_crowns
    if forfeited > 0:
        record_treasury(session, guild, "forfeit", -forfeited, now)
    await session.execute(
        update(GuildInvite)
        .where(GuildInvite.guild_id == guild.id, GuildInvite.status == "pending")
        .values(status="invalidated", responded_at=now, revision=GuildInvite.revision + 1)
        .execution_options(synchronize_session=False)
    )
    await session.execute(
        update(GuildApplication)
        .where(GuildApplication.guild_id == guild.id, GuildApplication.status == "pending")
        .values(
            status="cancelled",
            closed_by="system",
            resolved_at=now,
            revision=GuildApplication.revision + 1,
        )
        .execution_options(synchronize_session=False)
    )
    rows = (
        await session.execute(
            select(GuildMember, Character.telegram_id, Character.server_id)
            .join(Character, Character.id == GuildMember.character_id)
            .where(GuildMember.guild_id == guild.id)
        )
    ).all()
    for member, telegram_id, server_id in rows:
        await start_cooldown(session, telegram_id, server_id, now)
        await session.delete(member)
    guild.status = "dissolved"
    guild.dissolved_at = now
    guild.revision += 1
    audit(
        session, guild.id, "guild_dissolved", actor_id, None, now,
        {
            "reason": reason,
            "forfeited_treasury": forfeited,
            "forfeited_project_funds": lost_in_projects,
        },
    )  # fmt: skip
    await session.flush()


async def prepare_guild_departure(session: AsyncSession, character_id: UUID, now: datetime) -> None:
    """Resolve the Guild before a character is deleted (§9 deletion workflow).

    The caller must already hold the Guild lock. A deleted Leader passes the role
    by §49.18 succession; a sole-member Leader dissolves the Guild at once
    (author decision 2026-11-07). The account keeps the 12h cooldown, so
    recreating a character never resets it.
    """
    member = await session.scalar(
        select(GuildMember)
        .where(GuildMember.character_id == character_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if member is None:
        return
    guild = await session.get(Guild, member.guild_id)
    character = await session.get(Character, character_id)
    assert guild is not None and character is not None
    if guild.status != "active":
        return
    was_leader = member.role == GuildRole.LEADER.value
    others = list(
        (
            await session.scalars(
                select(GuildMember)
                .where(GuildMember.guild_id == guild.id, GuildMember.character_id != character_id)
                .order_by(GuildMember.character_id)
                .with_for_update()
            )
        ).all()
    )
    if was_leader and not others:
        await finalize_dissolution(session, guild, now, reason="leader_deleted")
        return
    await session.delete(member)
    await session.flush()
    if was_leader:
        await promote_successor(session, guild, others, None, now, reason="leader_deleted")
    await start_cooldown(session, character.telegram_id, character.server_id, now)
    guild.revision += 1
    audit(session, guild.id, "member_deleted", None, None, now, {"role": member.role})
    await session.flush()


async def due_guild_ids(
    session: AsyncSession, server_id: str, now: datetime, limit: int
) -> list[UUID]:
    """Guilds with upkeep due, for a periodic sweep."""
    inactive_leader = (
        select(GuildMember.guild_id)
        .where(
            GuildMember.role == GuildRole.LEADER.value,
            func.greatest(GuildMember.last_active_at, GuildMember.role_since)
            <= now - LEADER_INACTIVITY_LIMIT,
            # A lone Leader has nobody to pass the role to.
            GuildMember.guild_id.in_(
                select(GuildMember.guild_id).group_by(GuildMember.guild_id).having(func.count() > 1)
            ),
        )
        .scalar_subquery()
    )
    due_project = (
        select(GuildProject.guild_id)
        .where(GuildProject.status == "building", GuildProject.completes_at <= now)
        .scalar_subquery()
    )
    rows = await session.scalars(
        select(Guild.id)
        .where(
            Guild.server_id == server_id,
            Guild.status == "active",
            (Guild.dissolution_due_at <= now)
            | Guild.id.in_(due_project)
            | Guild.id.in_(inactive_leader),
        )
        .order_by(Guild.id)
        .limit(limit)
    )
    return list(rows.all())
