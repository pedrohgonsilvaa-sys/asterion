"""Guild membership, invites, applications and roles.

Sources: GDD Estrutural v1.6.0 §30, §30.1, §44.1, §49.18 and §55.5.

Lock order (every write follows it, which rules out deadlocks):
Guild -> Character -> invite/application rows. Member rows are locked only
while their Guild is locked. Any write on a character's invites or
applications happens only after that character's row is locked, so one
character's entries are serialised.

Author decisions (2026-11-07) for points the GDD leaves open:
- every exit, voluntary or by removal, starts the 12h switch cooldown;
- founding a Guild also respects that cooldown;
- the Leader cannot leave; leadership must be transferred first.

Pending author review: on transfer, the old Leader becomes Officer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.domain.guilds import (
    GUILD_SWITCH_COOLDOWN,
    LODGING_CAPACITY,
    MAX_NEW_APPLICATIONS_PER_WINDOW,
    MAX_PENDING_APPLICATIONS,
    NEW_APPLICATIONS_WINDOW,
    SAME_GUILD_APPLICATION_INTERVAL,
    GuildNameError,
    GuildRole,
    Recruitment,
    accepts_entry,
    can_change_officers,
    can_invite,
    can_manage_recruitment,
    can_remove,
    can_review_applications,
    can_transfer_leadership,
    capacity_for_lodging,
    is_over_cap,
    normalize_guild_name,
    normalize_guild_tag,
)
from asterion.infrastructure.db.models import (
    Character,
    Guild,
    GuildApplication,
    GuildAuditEntry,
    GuildInvite,
    GuildMember,
    GuildSwitchCooldown,
)

DEFAULT_PAGE_SIZE = 5


class GuildError(ValueError):
    """A Guild action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GuildMemberView:
    character_id: UUID
    name: str
    level: int
    character_class: str
    role: GuildRole
    joined_at: datetime


@dataclass(frozen=True, slots=True)
class GuildView:
    guild_id: UUID
    name: str
    tag: str
    recruitment: Recruitment
    revision: int
    member_count: int
    capacity: int
    over_cap: bool
    viewer_character_id: UUID
    viewer_role: GuildRole
    members: tuple[GuildMemberView, ...]


@dataclass(frozen=True, slots=True)
class PublicGuildView:
    """§30.1 public page: never exposes Treasury or internal data."""

    guild_id: UUID
    name: str
    tag: str
    member_count: int
    capacity: int
    recruitment: Recruitment
    accepts_applications: bool


@dataclass(frozen=True, slots=True)
class GuildPage:
    items: tuple[PublicGuildView, ...]
    next_after: UUID | None


@dataclass(frozen=True, slots=True)
class GuildInviteView:
    invite_id: UUID
    guild_id: UUID
    guild_name: str
    guild_tag: str
    invitee_character_id: UUID
    invitee_name: str
    invitee_telegram_id: int
    inviter_name: str | None
    status: str


@dataclass(frozen=True, slots=True)
class GuildApplicationView:
    application_id: UUID
    guild_id: UUID
    guild_name: str
    guild_tag: str
    character_id: UUID
    character_name: str
    character_level: int
    status: str
    closed_by: str | None
    created_at: datetime


class GuildService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    # ------------------------------------------------------------------ reads

    async def my_guild(self, actor: int) -> GuildView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            membership = await session.get(GuildMember, character.id)
            if membership is None:
                return None
            guild = await session.get(Guild, membership.guild_id)
            if guild is None or guild.status != "active":
                return None
            return await self._guild_view(session, guild, character.id)

    async def public_page(self, guild_id: UUID) -> PublicGuildView | None:
        async with self.sessions() as session:
            guild = await session.get(Guild, guild_id)
            if guild is None or guild.status != "active" or guild.server_id != self.server_id:
                return None
            return self._public_view(guild, await self._member_count(session, guild.id))

    async def search(self, query: str) -> tuple[PublicGuildView, ...]:
        """Exact search by official Name or TAG, restricted to this server."""
        text_query = query.strip()
        if not text_query.isascii() or not text_query.isalpha():
            return ()
        conditions = [func.lower(Guild.name) == text_query.casefold()]
        if len(text_query) == 3:
            conditions.append(Guild.tag == text_query.upper())
        async with self.sessions() as session:
            guilds = (
                await session.scalars(
                    select(Guild)
                    .where(
                        Guild.server_id == self.server_id,
                        Guild.status == "active",
                        or_(*conditions),
                    )
                    .order_by(Guild.id)
                )
            ).all()
            counts = await self._member_counts(session, [guild.id for guild in guilds])
            return tuple(self._public_view(guild, counts.get(guild.id, 0)) for guild in guilds)

    async def recruiting(
        self, *, after: UUID | None = None, limit: int = DEFAULT_PAGE_SIZE
    ) -> GuildPage:
        """Open Guilds with a free slot, paged by stable `guild_id` (not a ranking)."""
        if limit < 1:
            raise ValueError("limit must be positive")
        counts = (
            select(GuildMember.guild_id, func.count().label("members"))
            .group_by(GuildMember.guild_id)
            .subquery()
        )
        capacity = case(
            {level: value for level, value in enumerate(LODGING_CAPACITY)},
            value=Guild.lodging_level,
        )
        member_count = func.coalesce(counts.c.members, 0)
        statement = (
            select(Guild, member_count)
            .outerjoin(counts, counts.c.guild_id == Guild.id)
            .where(
                Guild.server_id == self.server_id,
                Guild.status == "active",
                Guild.recruitment == Recruitment.OPEN.value,
                member_count < capacity,
            )
            .order_by(Guild.id)
            .limit(limit + 1)
        )
        if after is not None:
            statement = statement.where(Guild.id > after)
        async with self.sessions() as session:
            rows = (await session.execute(statement)).all()
        items = tuple(self._public_view(guild, int(count)) for guild, count in rows[:limit])
        next_after = items[-1].guild_id if len(rows) > limit else None
        return GuildPage(items=items, next_after=next_after)

    async def incoming_invites(self, actor: int) -> tuple[GuildInviteView, ...]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return ()
            invites = (
                await session.scalars(
                    select(GuildInvite)
                    .join(Guild, Guild.id == GuildInvite.guild_id)
                    .where(
                        GuildInvite.invitee_character_id == character.id,
                        GuildInvite.status == "pending",
                        Guild.status == "active",
                    )
                    .order_by(GuildInvite.created_at, GuildInvite.id)
                )
            ).all()
            return tuple([await self._invite_view(session, invite) for invite in invites])

    async def my_applications(self, actor: int) -> tuple[GuildApplicationView, ...]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return ()
            applications = (
                await session.scalars(
                    select(GuildApplication)
                    .where(GuildApplication.character_id == character.id)
                    .order_by(GuildApplication.created_at.desc(), GuildApplication.id)
                )
            ).all()
            return tuple([await self._application_view(session, item) for item in applications])

    async def received_applications(self, actor: int) -> tuple[GuildApplicationView, ...]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                raise GuildError("character_missing")
            membership = await session.get(GuildMember, character.id)
            if membership is None:
                raise GuildError("not_in_guild")
            if not can_review_applications(GuildRole(membership.role)):
                raise GuildError("no_permission")
            applications = (
                await session.scalars(
                    select(GuildApplication)
                    .where(
                        GuildApplication.guild_id == membership.guild_id,
                        GuildApplication.status == "pending",
                    )
                    .order_by(GuildApplication.created_at, GuildApplication.id)
                )
            ).all()
            return tuple([await self._application_view(session, item) for item in applications])

    # ----------------------------------------------------------- founding

    async def create_guild(
        self, actor: int, name: str, tag: str, *, now: datetime | None = None
    ) -> GuildView:
        """§55.5: founding costs nothing; the founder becomes Leader."""
        now = _utcnow(now)
        try:
            clean_name = normalize_guild_name(name)
            clean_tag = normalize_guild_tag(tag)
        except GuildNameError as exc:
            raise GuildError(exc.code) from exc
        try:
            async with self.sessions.begin() as session:
                character = await self._character(session, actor, lock=True)
                if character is None:
                    raise GuildError("character_missing")
                if await session.get(GuildMember, character.id) is not None:
                    raise GuildError("already_in_guild")
                await self._check_cooldown(session, character, now)
                await self._check_name_free(session, clean_name, clean_tag)
                guild = Guild(
                    server_id=self.server_id,
                    name=clean_name,
                    tag=clean_tag,
                    status="active",
                    recruitment=Recruitment.CLOSED.value,
                    lodging_level=0,
                    revision=0,
                    created_at=now,
                )
                session.add(guild)
                await session.flush()
                session.add(
                    GuildMember(
                        character_id=character.id,
                        guild_id=guild.id,
                        role=GuildRole.LEADER.value,
                        joined_at=now,
                        role_since=now,
                    )
                )
                await self._close_other_entries(session, character.id, now)
                self._audit(
                    session,
                    guild.id,
                    "guild_founded",
                    character.id,
                    None,
                    now,
                    {"name": clean_name, "tag": clean_tag},
                )
                await session.flush()
                return await self._guild_view(session, guild, character.id)
        except IntegrityError as exc:
            # Concurrent founding grabbed the Name/TAG, or the founder joined elsewhere.
            raise GuildError("name_or_tag_taken") from exc

    # --------------------------------------------------------- recruitment

    async def set_recruitment(
        self, actor: int, recruitment: Recruitment, *, now: datetime | None = None
    ) -> GuildView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor)
            if not can_manage_recruitment(GuildRole(membership.role)):
                raise GuildError("no_permission")
            if guild.recruitment != recruitment.value:
                guild.recruitment = recruitment.value
                guild.revision += 1
                self._audit(
                    session,
                    guild.id,
                    "recruitment_changed",
                    character.id,
                    None,
                    now,
                    {"recruitment": recruitment.value},
                )
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    # -------------------------------------------------------------- invites

    async def invite(
        self, actor: int, target_name: str, *, now: datetime | None = None
    ) -> GuildInviteView:
        now = _utcnow(now)
        name = target_name.strip()
        if not name or len(name) > 16:
            raise GuildError("character_not_found")
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor)
            if not can_invite(GuildRole(membership.role)):
                raise GuildError("no_permission")
            target = await session.scalar(
                select(Character)
                .where(
                    Character.server_id == self.server_id,
                    func.lower(Character.name) == name.casefold(),
                )
                .with_for_update()
            )
            if target is None:
                raise GuildError("character_not_found")
            if target.id == character.id:
                raise GuildError("cannot_invite_self")
            if await session.get(GuildMember, target.id) is not None:
                raise GuildError("target_in_guild")
            if not accepts_entry(await self._member_count(session, guild.id), _capacity(guild)):
                raise GuildError("guild_full")
            existing = await session.scalar(
                select(GuildInvite).where(
                    GuildInvite.guild_id == guild.id,
                    GuildInvite.invitee_character_id == target.id,
                    GuildInvite.status == "pending",
                )
            )
            if existing is not None:
                # §55.5: an invite is idempotent; one active per Guild and character.
                return await self._invite_view(session, existing)
            invite = GuildInvite(
                guild_id=guild.id,
                inviter_character_id=character.id,
                invitee_character_id=target.id,
                status="pending",
                revision=0,
                created_at=now,
            )
            session.add(invite)
            guild.revision += 1
            self._audit(session, guild.id, "invite_sent", character.id, target.id, now, {})
            await session.flush()
            return await self._invite_view(session, invite)

    async def cancel_invite(
        self, actor: int, invite_id: UUID, *, now: datetime | None = None
    ) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor)
            if not can_invite(GuildRole(membership.role)):
                raise GuildError("no_permission")
            seed = await session.get(GuildInvite, invite_id)
            if seed is None or seed.guild_id != guild.id:
                raise GuildError("invite_unusable")
            await self._lock_character_id(session, seed.invitee_character_id)
            invite = await self._lock_invite(session, invite_id)
            if invite.status == "cancelled":
                return
            if invite.status != "pending":
                raise GuildError("invite_unusable")
            invite.status = "cancelled"
            invite.revision += 1
            invite.responded_at = now
            guild.revision += 1
            self._audit(
                session,
                guild.id,
                "invite_cancelled",
                character.id,
                invite.invitee_character_id,
                now,
                {},
            )

    async def respond_invite(
        self, actor: int, invite_id: UUID, *, accept: bool, now: datetime | None = None
    ) -> GuildView | None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            seed = await session.get(GuildInvite, invite_id)
            if seed is None:
                raise GuildError("invite_unusable")
            guild = await self._lock_guild(session, seed.guild_id)
            character = await self._character(session, actor, lock=True)
            if character is None:
                raise GuildError("character_missing")
            invite = await self._lock_invite(session, invite_id)
            if invite.invitee_character_id != character.id:
                raise GuildError("invite_unusable")
            if invite.status == "accepted" and accept:
                return await self._guild_view(session, guild, character.id)
            if invite.status == "declined" and not accept:
                return None
            if invite.status != "pending" or guild.status != "active":
                raise GuildError("invite_unusable")
            if not accept:
                invite.status = "declined"
                invite.revision += 1
                invite.responded_at = now
                guild.revision += 1
                return None
            await self._admit(
                session, guild, character, now, source="invite", keep_invite_id=invite.id
            )
            invite.status = "accepted"
            invite.revision += 1
            invite.responded_at = now
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    # --------------------------------------------------------- applications

    async def apply(
        self, actor: int, guild_id: UUID, *, now: datetime | None = None
    ) -> GuildApplicationView:
        now = _utcnow(now)
        try:
            async with self.sessions.begin() as session:
                guild = await self._lock_guild(session, guild_id)
                if guild.status != "active" or guild.server_id != self.server_id:
                    raise GuildError("guild_missing")
                character = await self._character(session, actor, lock=True)
                if character is None:
                    raise GuildError("character_missing")
                if await session.get(GuildMember, character.id) is not None:
                    raise GuildError("already_in_guild")
                if guild.recruitment != Recruitment.OPEN.value:
                    raise GuildError("recruitment_closed")
                if not accepts_entry(await self._member_count(session, guild.id), _capacity(guild)):
                    raise GuildError("guild_full")
                await self._check_cooldown(session, character, now)
                await self._check_application_limits(session, character.id, guild.id, now)
                application = GuildApplication(
                    guild_id=guild.id,
                    character_id=character.id,
                    server_id=self.server_id,
                    status="pending",
                    revision=0,
                    created_at=now,
                )
                session.add(application)
                await session.flush()
                return await self._application_view(session, application)
        except IntegrityError as exc:
            raise GuildError("application_pending") from exc

    async def cancel_application(
        self, actor: int, application_id: UUID, *, now: datetime | None = None
    ) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            seed = await session.get(GuildApplication, application_id)
            if seed is None:
                raise GuildError("application_missing")
            await self._lock_guild(session, seed.guild_id)
            character = await self._character(session, actor, lock=True)
            if character is None or character.id != seed.character_id:
                raise GuildError("application_missing")
            application = await self._lock_application(session, application_id)
            if application.status == "cancelled" and application.closed_by == "player":
                return
            if application.status != "pending":
                raise GuildError("application_closed")
            _close_application(application, "cancelled", now, closed_by="player")

    async def approve_application(
        self, actor: int, application_id: UUID, *, now: datetime | None = None
    ) -> GuildApplicationView:
        """§30.1: approving is the immediate, atomic entry attempt."""
        now = _utcnow(now)
        closed_reason: str | None = None
        async with self.sessions.begin() as session:
            seed = await session.get(GuildApplication, application_id)
            if seed is None:
                raise GuildError("application_missing")
            reviewer, guild, membership = await self._actor_guild(
                session, actor, guild_id=seed.guild_id
            )
            if not can_review_applications(GuildRole(membership.role)):
                raise GuildError("no_permission")
            applicant = await self._lock_character_id(session, seed.character_id)
            application = await self._lock_application(session, application_id)
            if application.status == "approved":
                return await self._application_view(session, application)
            if application.status != "pending":
                raise GuildError("application_closed")
            if applicant is None:
                raise GuildError("application_missing")
            if await session.get(GuildMember, applicant.id) is not None:
                # Already in another Guild: the system closes this application for good.
                _close_application(application, "cancelled", now, closed_by="system")
                closed_reason = "already_in_guild"
            else:
                # Full Guild or running cooldown raise here; the application stays Pending.
                await self._admit(
                    session,
                    guild,
                    applicant,
                    now,
                    source="application",
                    keep_application_id=application.id,
                    actor_id=reviewer.id,
                )
                _close_application(application, "approved", now, resolved_by=reviewer.id)
                await session.flush()
                return await self._application_view(session, application)
        assert closed_reason is not None
        raise GuildError(closed_reason)

    async def reject_application(
        self, actor: int, application_id: UUID, *, now: datetime | None = None
    ) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            seed = await session.get(GuildApplication, application_id)
            if seed is None:
                raise GuildError("application_missing")
            reviewer, guild, membership = await self._actor_guild(
                session, actor, guild_id=seed.guild_id
            )
            if not can_review_applications(GuildRole(membership.role)):
                raise GuildError("no_permission")
            await self._lock_character_id(session, seed.character_id)
            application = await self._lock_application(session, application_id)
            if application.status == "rejected":
                return
            if application.status != "pending":
                raise GuildError("application_closed")
            _close_application(application, "rejected", now, resolved_by=reviewer.id)
            self._audit(
                session,
                guild.id,
                "application_rejected",
                reviewer.id,
                application.character_id,
                now,
                {"application_id": str(application.id)},
            )

    # ---------------------------------------------------------------- roles

    async def promote(
        self, actor: int, target_character_id: UUID, *, now: datetime | None = None
    ) -> GuildView:
        return await self._set_role(actor, target_character_id, GuildRole.OFFICER, now)

    async def demote(
        self, actor: int, target_character_id: UUID, *, now: datetime | None = None
    ) -> GuildView:
        return await self._set_role(actor, target_character_id, GuildRole.MEMBER, now)

    async def transfer_leadership(
        self, actor: int, target_character_id: UUID, *, now: datetime | None = None
    ) -> GuildView:
        """The old Leader becomes Officer."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor)
            if not can_transfer_leadership(GuildRole(membership.role)):
                raise GuildError("no_permission")
            if target_character_id == character.id:
                raise GuildError("cannot_target_self")
            target = await self._lock_member(session, guild.id, target_character_id)
            membership.role = GuildRole.OFFICER.value
            membership.role_since = now
            await session.flush()  # free the single-Leader index before promoting
            target.role = GuildRole.LEADER.value
            target.role_since = now
            guild.revision += 1
            self._audit(
                session,
                guild.id,
                "leadership_transferred",
                character.id,
                target_character_id,
                now,
                {},
            )
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    async def remove_member(
        self, actor: int, target_character_id: UUID, *, now: datetime | None = None
    ) -> GuildView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor)
            if target_character_id == character.id:
                raise GuildError("cannot_target_self")
            target_character = await self._lock_character_id(session, target_character_id)
            target = await self._lock_member(session, guild.id, target_character_id)
            if not can_remove(GuildRole(membership.role), GuildRole(target.role)):
                raise GuildError("no_permission")
            await session.delete(target)
            if target_character is not None:
                await self._start_cooldown(session, target_character, now)
            guild.revision += 1
            self._audit(
                session,
                guild.id,
                "member_removed",
                character.id,
                target_character_id,
                now,
                {"role": target.role},
            )
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    async def leave(self, actor: int, *, now: datetime | None = None) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor)
            if membership.role == GuildRole.LEADER.value:
                raise GuildError("leader_must_transfer")
            await session.delete(membership)
            await self._start_cooldown(session, character, now)
            guild.revision += 1
            self._audit(session, guild.id, "member_left", character.id, None, now, {})

    # -------------------------------------------------------------- helpers

    async def _set_role(
        self, actor: int, target_character_id: UUID, role: GuildRole, now: datetime | None
    ) -> GuildView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor)
            if not can_change_officers(GuildRole(membership.role)):
                raise GuildError("no_permission")
            if target_character_id == character.id:
                raise GuildError("cannot_target_self")
            target = await self._lock_member(session, guild.id, target_character_id)
            if target.role == GuildRole.LEADER.value:
                raise GuildError("no_permission")
            if target.role != role.value:
                target.role = role.value
                target.role_since = now
                guild.revision += 1
                action = "officer_promoted" if role is GuildRole.OFFICER else "officer_demoted"
                self._audit(session, guild.id, action, character.id, target_character_id, now, {})
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    async def _admit(
        self,
        session: AsyncSession,
        guild: Guild,
        character: Character,
        now: datetime,
        *,
        source: str,
        keep_invite_id: UUID | None = None,
        keep_application_id: UUID | None = None,
        actor_id: UUID | None = None,
    ) -> None:
        """Atomic entry (§30.1). Guild and Character must already be locked."""
        if guild.status != "active":
            raise GuildError("guild_missing")
        if character.server_id != guild.server_id or guild.server_id != self.server_id:
            raise GuildError("wrong_server")
        if await session.get(GuildMember, character.id) is not None:
            raise GuildError("already_in_guild")
        await self._check_cooldown(session, character, now)
        if not accepts_entry(await self._member_count(session, guild.id), _capacity(guild)):
            raise GuildError("guild_full")
        session.add(
            GuildMember(
                character_id=character.id,
                guild_id=guild.id,
                role=GuildRole.MEMBER.value,
                joined_at=now,
                role_since=now,
            )
        )
        await self._close_other_entries(
            session,
            character.id,
            now,
            keep_invite_id=keep_invite_id,
            keep_application_id=keep_application_id,
        )
        guild.revision += 1
        self._audit(
            session,
            guild.id,
            "member_joined",
            actor_id or character.id,
            character.id,
            now,
            {"source": source},
        )
        await session.flush()

    async def _close_other_entries(
        self,
        session: AsyncSession,
        character_id: UUID,
        now: datetime,
        *,
        keep_invite_id: UUID | None = None,
        keep_application_id: UUID | None = None,
    ) -> None:
        """After an entry, other invites become unusable and applications are system-cancelled."""
        invites = update(GuildInvite).where(
            GuildInvite.invitee_character_id == character_id,
            GuildInvite.status == "pending",
        )
        if keep_invite_id is not None:
            invites = invites.where(GuildInvite.id != keep_invite_id)
        await session.execute(
            invites.values(
                status="invalidated", responded_at=now, revision=GuildInvite.revision + 1
            ).execution_options(synchronize_session=False)
        )
        applications = update(GuildApplication).where(
            GuildApplication.character_id == character_id,
            GuildApplication.status == "pending",
        )
        if keep_application_id is not None:
            applications = applications.where(GuildApplication.id != keep_application_id)
        await session.execute(
            applications.values(
                status="cancelled",
                closed_by="system",
                resolved_at=now,
                revision=GuildApplication.revision + 1,
            ).execution_options(synchronize_session=False)
        )

    async def _check_cooldown(
        self, session: AsyncSession, character: Character, now: datetime
    ) -> None:
        cooldown = await session.get(
            GuildSwitchCooldown, (character.telegram_id, character.server_id)
        )
        if cooldown is not None and now < cooldown.last_exit_at + GUILD_SWITCH_COOLDOWN:
            raise GuildError("switch_cooldown")

    async def _start_cooldown(
        self, session: AsyncSession, character: Character, now: datetime
    ) -> None:
        statement = insert(GuildSwitchCooldown).values(
            telegram_id=character.telegram_id, server_id=character.server_id, last_exit_at=now
        )
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[GuildSwitchCooldown.telegram_id, GuildSwitchCooldown.server_id],
                set_={"last_exit_at": statement.excluded.last_exit_at},
            )
        )

    async def _check_application_limits(
        self, session: AsyncSession, character_id: UUID, guild_id: UUID, now: datetime
    ) -> None:
        """§49.18: 3 Pending, 6 new per 60 min, 1 per Guild per 10 min."""
        mine = (
            select(func.count())
            .select_from(GuildApplication)
            .where(GuildApplication.character_id == character_id)
        )
        pending_here = await session.scalar(
            mine.where(GuildApplication.guild_id == guild_id, GuildApplication.status == "pending")
        )
        if pending_here:
            raise GuildError("application_pending")
        pending = await session.scalar(mine.where(GuildApplication.status == "pending"))
        if (pending or 0) >= MAX_PENDING_APPLICATIONS:
            raise GuildError("too_many_pending")
        recent = await session.scalar(
            mine.where(GuildApplication.created_at > now - NEW_APPLICATIONS_WINDOW)
        )
        if (recent or 0) >= MAX_NEW_APPLICATIONS_PER_WINDOW:
            raise GuildError("application_rate_limited")
        same_guild = await session.scalar(
            mine.where(
                GuildApplication.guild_id == guild_id,
                GuildApplication.created_at > now - SAME_GUILD_APPLICATION_INTERVAL,
            )
        )
        if same_guild:
            raise GuildError("application_rate_limited")

    async def _check_name_free(self, session: AsyncSession, name: str, tag: str) -> None:
        taken = await session.scalar(
            select(Guild.id).where(
                Guild.server_id == self.server_id,
                Guild.status == "active",
                or_(func.lower(Guild.name) == name.casefold(), Guild.tag == tag),
            )
        )
        if taken is not None:
            raise GuildError("name_or_tag_taken")

    async def _actor_guild(
        self, session: AsyncSession, actor: int, *, guild_id: UUID | None = None
    ) -> tuple[Character, Guild, GuildMember]:
        """Lock the actor's Guild, then re-read the actor's membership under that lock."""
        character = await self._character(session, actor)
        if character is None:
            raise GuildError("character_missing")
        seed = await session.get(GuildMember, character.id)
        target_guild_id = guild_id if guild_id is not None else (seed.guild_id if seed else None)
        if target_guild_id is None:
            raise GuildError("not_in_guild")
        guild = await self._lock_guild(session, target_guild_id)
        if guild.status != "active":
            raise GuildError("not_in_guild")
        membership = await session.scalar(
            select(GuildMember)
            .where(GuildMember.character_id == character.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if membership is None or membership.guild_id != guild.id:
            # Covers lost membership and a stale button from another Guild (§44.1).
            raise GuildError("no_permission" if guild_id is not None else "not_in_guild")
        return character, guild, membership

    async def _character(
        self, session: AsyncSession, actor: int, *, lock: bool = False
    ) -> Character | None:
        statement = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    async def _lock_character_id(
        self, session: AsyncSession, character_id: UUID
    ) -> Character | None:
        return await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )

    async def _lock_guild(self, session: AsyncSession, guild_id: UUID) -> Guild:
        guild = await session.scalar(
            select(Guild)
            .where(Guild.id == guild_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if guild is None or guild.server_id != self.server_id:
            raise GuildError("guild_missing")
        return guild

    async def _lock_member(
        self, session: AsyncSession, guild_id: UUID, character_id: UUID
    ) -> GuildMember:
        member = await session.scalar(
            select(GuildMember)
            .where(GuildMember.character_id == character_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if member is None or member.guild_id != guild_id:
            raise GuildError("target_not_member")
        return member

    async def _lock_invite(self, session: AsyncSession, invite_id: UUID) -> GuildInvite:
        invite = await session.scalar(
            select(GuildInvite)
            .where(GuildInvite.id == invite_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if invite is None:
            raise GuildError("invite_unusable")
        return invite

    async def _lock_application(
        self, session: AsyncSession, application_id: UUID
    ) -> GuildApplication:
        application = await session.scalar(
            select(GuildApplication)
            .where(GuildApplication.id == application_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if application is None:
            raise GuildError("application_missing")
        return application

    async def _member_count(self, session: AsyncSession, guild_id: UUID) -> int:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(GuildMember)
                .where(GuildMember.guild_id == guild_id)
            )
            or 0
        )

    async def _member_counts(
        self, session: AsyncSession, guild_ids: Sequence[UUID]
    ) -> dict[UUID, int]:
        if not guild_ids:
            return {}
        rows = await session.execute(
            select(GuildMember.guild_id, func.count())
            .where(GuildMember.guild_id.in_(guild_ids))
            .group_by(GuildMember.guild_id)
        )
        return {guild_id: int(count) for guild_id, count in rows.all()}

    async def _guild_view(self, session: AsyncSession, guild: Guild, viewer_id: UUID) -> GuildView:
        rows = (
            await session.execute(
                select(GuildMember, Character)
                .join(Character, Character.id == GuildMember.character_id)
                .where(GuildMember.guild_id == guild.id)
                .order_by(GuildMember.joined_at, GuildMember.character_id)
                .execution_options(populate_existing=True)
            )
        ).all()
        members = tuple(
            GuildMemberView(
                character_id=member.character_id,
                name=character.name,
                level=character.level,
                character_class=character.character_class,
                role=GuildRole(member.role),
                joined_at=member.joined_at,
            )
            for member, character in rows
        )
        viewer_role = next(
            (member.role for member in members if member.character_id == viewer_id), None
        )
        if viewer_role is None:
            raise GuildError("not_in_guild")
        capacity = _capacity(guild)
        return GuildView(
            guild_id=guild.id,
            name=guild.name,
            tag=guild.tag,
            recruitment=Recruitment(guild.recruitment),
            revision=guild.revision,
            member_count=len(members),
            capacity=capacity,
            over_cap=is_over_cap(len(members), capacity),
            viewer_character_id=viewer_id,
            viewer_role=viewer_role,
            members=members,
        )

    def _public_view(self, guild: Guild, member_count: int) -> PublicGuildView:
        capacity = _capacity(guild)
        recruitment = Recruitment(guild.recruitment)
        return PublicGuildView(
            guild_id=guild.id,
            name=guild.name,
            tag=guild.tag,
            member_count=member_count,
            capacity=capacity,
            recruitment=recruitment,
            accepts_applications=(
                recruitment is Recruitment.OPEN and accepts_entry(member_count, capacity)
            ),
        )

    async def _invite_view(self, session: AsyncSession, invite: GuildInvite) -> GuildInviteView:
        guild = await session.get(Guild, invite.guild_id)
        invitee = await session.get(Character, invite.invitee_character_id)
        inviter = (
            await session.get(Character, invite.inviter_character_id)
            if invite.inviter_character_id is not None
            else None
        )
        assert guild is not None and invitee is not None
        return GuildInviteView(
            invite_id=invite.id,
            guild_id=guild.id,
            guild_name=guild.name,
            guild_tag=guild.tag,
            invitee_character_id=invitee.id,
            invitee_name=invitee.name,
            invitee_telegram_id=invitee.telegram_id,
            inviter_name=inviter.name if inviter is not None else None,
            status=invite.status,
        )

    async def _application_view(
        self, session: AsyncSession, application: GuildApplication
    ) -> GuildApplicationView:
        guild = await session.get(Guild, application.guild_id)
        character = await session.get(Character, application.character_id)
        assert guild is not None and character is not None
        return GuildApplicationView(
            application_id=application.id,
            guild_id=guild.id,
            guild_name=guild.name,
            guild_tag=guild.tag,
            character_id=character.id,
            character_name=character.name,
            character_level=character.level,
            status=application.status,
            closed_by=application.closed_by,
            created_at=application.created_at,
        )

    def _audit(
        self,
        session: AsyncSession,
        guild_id: UUID,
        action: str,
        actor_id: UUID | None,
        target_id: UUID | None,
        now: datetime,
        details: dict[str, Any],
    ) -> None:
        session.add(
            GuildAuditEntry(
                guild_id=guild_id,
                action=action,
                actor_character_id=actor_id,
                target_character_id=target_id,
                details=details,
                created_at=now,
            )
        )


def _capacity(guild: Guild) -> int:
    return capacity_for_lodging(guild.lodging_level)


def _close_application(
    application: GuildApplication,
    status: str,
    now: datetime,
    *,
    closed_by: str | None = None,
    resolved_by: UUID | None = None,
) -> None:
    application.status = status
    application.closed_by = closed_by
    application.resolved_at = now
    application.resolved_by_character_id = resolved_by
    application.revision += 1


def _utcnow(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return value
