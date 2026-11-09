"""Guild membership, invites, applications, roles, Treasury, Obras and dissolution.

Sources: GDD Estrutural v1.6.0 §30, §30.1-§30.3, §44.1, §49.10, §49.18 and §55.5.

Lock order (every write follows it, which rules out deadlocks):
Guild -> Character -> invite/application/project rows. Member rows are locked
only while their Guild is locked. Any write on a character's invites or
applications happens only after that character's row is locked, so one
character's entries are serialised.

Upkeep (finished Obras, Leader succession, due dissolution) runs lazily in its
own transaction before each action on a Guild, and in `run_maintenance` for a
periodic sweep. See `guild_upkeep.py`.

Author decisions (2026-11-07) for points the GDD leaves open:
- every exit, voluntary, by removal, dissolution or deletion, starts the 12h cooldown;
- founding a Guild also respects that cooldown;
- the Leader cannot leave; leadership must be transferred first;
- the six Obras other than Lodging can be built but have no effect yet;
- Coroas reach an Obra from a member's wallet or from the Treasury (Leader only);
- a sole-member Leader who deletes the character dissolves the Guild at once;
- an old Name/TAG stays reserved for 30 days after a rename.

Pending author review: on transfer or succession the old Leader becomes Officer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.guild_upkeep import (
    ACTIVE_PROJECT_STATES,
    audit,
    due_guild_ids,
    maintenance_due,
    promote_successor,
    record_treasury,
    settle,
    start_cooldown,
)
from asterion.application.social_graph import blocked_between
from asterion.domain.guilds import (
    DISSOLUTION_PERIOD,
    GUILD_SWITCH_COOLDOWN,
    LODGING_CAPACITY,
    MAX_ACTIVE_PROJECTS,
    MAX_NEW_APPLICATIONS_PER_WINDOW,
    MAX_PENDING_APPLICATIONS,
    MAX_PROJECT_LEVEL,
    NEW_APPLICATIONS_WINDOW,
    OLD_NAME_RETENTION,
    RENAME_COOLDOWN,
    RENAME_COST,
    SAME_GUILD_APPLICATION_INTERVAL,
    GuildNameError,
    GuildRole,
    ProjectKind,
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
    project_build_time,
    project_cost,
)
from asterion.infrastructure.db.models import (
    Character,
    Guild,
    GuildApplication,
    GuildInvite,
    GuildMember,
    GuildNameHistory,
    GuildProject,
    GuildProjectContribution,
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
class GuildProjectView:
    project_id: UUID
    kind: ProjectKind
    level: int
    status: str
    cost: int
    funded: int
    completes_at: datetime | None


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
    treasury_crowns: int = 0
    obra_levels: tuple[tuple[ProjectKind, int], ...] = ()
    active_projects: tuple[GuildProjectView, ...] = ()
    rename_available_at: datetime | None = None
    dissolution_due_at: datetime | None = None


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
    character_telegram_id: int | None = None


@dataclass(frozen=True, slots=True)
class ContributionResult:
    applied: int
    guild: GuildView


class GuildService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    # ---------------------------------------------------------------- upkeep

    async def run_maintenance(self, *, now: datetime | None = None, limit: int = 50) -> int:
        """Sweep due Obras, successions and dissolutions; safe to call often."""
        now = _utcnow(now)
        async with self.sessions() as session:
            guild_ids = await due_guild_ids(session, self.server_id, now, limit)
        for guild_id in guild_ids:
            await self._maintain(guild_id, now)
        return len(guild_ids)

    async def record_activity(self, actor: int, *, now: datetime | None = None) -> None:
        """Authenticated activity of a member; feeds the 168h Leader succession."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character_id = await session.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if character_id is None:
                return
            await session.execute(
                update(GuildMember)
                .where(GuildMember.character_id == character_id)
                .values(last_active_at=func.greatest(GuildMember.last_active_at, now))
            )

    async def _maintain(self, guild_id: UUID | None, now: datetime) -> None:
        if guild_id is None:
            return
        async with self.sessions.begin() as session:
            guild = await session.get(Guild, guild_id)
            if guild is None or not await maintenance_due(session, guild, now):
                return
            await settle(session, await self._lock_guild(session, guild_id), now)

    async def _maintain_actor(self, actor: int, now: datetime) -> None:
        async with self.sessions() as session:
            guild_id = await session.scalar(
                select(GuildMember.guild_id)
                .join(Character, Character.id == GuildMember.character_id)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            )
        await self._maintain(guild_id, now)

    # ------------------------------------------------------------------ reads

    async def my_guild(self, actor: int, *, now: datetime | None = None) -> GuildView | None:
        now = _utcnow(now)
        await self._maintain_actor(actor, now)
        await self.record_activity(actor, now=now)
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

    async def public_page(
        self, guild_id: UUID, *, now: datetime | None = None
    ) -> PublicGuildView | None:
        await self._maintain(guild_id, _utcnow(now))
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
                await self._check_name_free(session, clean_name, clean_tag, now)
                guild = Guild(
                    server_id=self.server_id,
                    name=clean_name,
                    tag=clean_tag,
                    status="active",
                    recruitment=Recruitment.CLOSED.value,
                    lodging_level=0,
                    revision=0,
                    created_at=now,
                    treasury_crowns=0,
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
                        last_active_at=now,
                    )
                )
                await self._close_other_entries(session, character.id, now)
                audit(
                    session, guild.id, "guild_founded", character.id, None, now,
                    {"name": clean_name, "tag": clean_tag},
                )  # fmt: skip
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
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
            if not can_manage_recruitment(GuildRole(membership.role)):
                raise GuildError("no_permission")
            if guild.recruitment != recruitment.value:
                guild.recruitment = recruitment.value
                guild.revision += 1
                audit(
                    session, guild.id, "recruitment_changed", character.id, None, now,
                    {"recruitment": recruitment.value},
                )  # fmt: skip
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
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
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
            if await blocked_between(session, character.id, target.id):
                raise GuildError("invite_refused")
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
            audit(session, guild.id, "invite_sent", character.id, target.id, now)
            await session.flush()
            return await self._invite_view(session, invite)

    async def cancel_invite(
        self, actor: int, invite_id: UUID, *, now: datetime | None = None
    ) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
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
            audit(
                session, guild.id, "invite_cancelled", character.id,
                invite.invitee_character_id, now,
            )  # fmt: skip

    async def respond_invite(
        self, actor: int, invite_id: UUID, *, accept: bool, now: datetime | None = None
    ) -> GuildView | None:
        now = _utcnow(now)
        async with self.sessions() as session:
            seed = await session.get(GuildInvite, invite_id)
        if seed is None:
            raise GuildError("invite_unusable")
        await self._maintain(seed.guild_id, now)
        async with self.sessions.begin() as session:
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
        await self._maintain(guild_id, now)
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
        async with self.sessions() as session:
            seed = await session.get(GuildApplication, application_id)
        if seed is None:
            raise GuildError("application_missing")
        await self._maintain(seed.guild_id, now)
        closed_reason: str | None = None
        async with self.sessions.begin() as session:
            reviewer, guild, membership = await self._actor_guild(
                session, actor, now, guild_id=seed.guild_id
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
                    session, guild, applicant, now, source="application",
                    keep_application_id=application.id, actor_id=reviewer.id,
                )  # fmt: skip
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
                session, actor, now, guild_id=seed.guild_id
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
            audit(
                session, guild.id, "application_rejected", reviewer.id,
                application.character_id, now, {"application_id": str(application.id)},
            )  # fmt: skip

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
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
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
            audit(
                session, guild.id, "leadership_transferred", character.id,
                target_character_id, now,
            )  # fmt: skip
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    async def remove_member(
        self, actor: int, target_character_id: UUID, *, now: datetime | None = None
    ) -> GuildView:
        now = _utcnow(now)
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
            if target_character_id == character.id:
                raise GuildError("cannot_target_self")
            target_character = await self._lock_character_id(session, target_character_id)
            target = await self._lock_member(session, guild.id, target_character_id)
            if not can_remove(GuildRole(membership.role), GuildRole(target.role)):
                raise GuildError("no_permission")
            await session.delete(target)
            if target_character is not None:
                await start_cooldown(
                    session, target_character.telegram_id, target_character.server_id, now
                )
            guild.revision += 1
            audit(
                session, guild.id, "member_removed", character.id, target_character_id, now,
                {"role": target.role},
            )  # fmt: skip
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    async def leave(self, actor: int, *, now: datetime | None = None) -> None:
        now = _utcnow(now)
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
            if membership.role == GuildRole.LEADER.value:
                raise GuildError("leader_must_transfer")
            await session.delete(membership)
            await start_cooldown(session, character.telegram_id, character.server_id, now)
            guild.revision += 1
            audit(session, guild.id, "member_left", character.id, None, now)

    # ------------------------------------------------------ Treasury & Obras

    async def deposit(self, actor: int, amount: int, *, now: datetime | None = None) -> GuildView:
        """A member moves Coroas into the Treasury. Final: nothing returns to a wallet."""
        now = _utcnow(now)
        _positive(amount)
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, _membership = await self._actor_guild(session, actor, now)
            _ensure_not_dissolving(guild)
            wallet = await self._lock_character_id(session, character.id)
            assert wallet is not None
            if wallet.crowns < amount:
                raise GuildError("not_enough_crowns")
            wallet.crowns -= amount
            record_treasury(session, guild, "deposit", amount, now, character_id=character.id)
            guild.revision += 1
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    async def start_project(
        self, actor: int, kind: ProjectKind, *, now: datetime | None = None
    ) -> GuildView:
        """Leader opens Financiamento for the next level of one Obra (max 2 at once)."""
        now = _utcnow(now)
        await self._maintain_actor(actor, now)
        try:
            async with self.sessions.begin() as session:
                character, guild, membership = await self._actor_guild(session, actor, now)
                if membership.role != GuildRole.LEADER.value:
                    raise GuildError("no_permission")
                _ensure_not_dissolving(guild)
                projects = (
                    await session.scalars(
                        select(GuildProject).where(
                            GuildProject.guild_id == guild.id,
                            GuildProject.status != "cancelled",
                        )
                    )
                ).all()
                active = [p for p in projects if p.status in ACTIVE_PROJECT_STATES]
                if any(p.kind == kind.value for p in active):
                    raise GuildError("project_active")
                if len(active) >= MAX_ACTIVE_PROJECTS:
                    raise GuildError("too_many_projects")
                level = 1 + sum(
                    1 for p in projects if p.kind == kind.value and p.status == "completed"
                )
                if level > MAX_PROJECT_LEVEL:
                    raise GuildError("project_max_level")
                session.add(
                    GuildProject(
                        guild_id=guild.id,
                        kind=kind.value,
                        level=level,
                        status="funding",
                        cost=project_cost(level),
                        funded=0,
                        revision=0,
                        started_at=now,
                    )
                )
                guild.revision += 1
                audit(
                    session, guild.id, "project_started", character.id, None, now,
                    {"kind": kind.value, "level": level},
                )  # fmt: skip
                await session.flush()
                return await self._guild_view(session, guild, character.id)
        except IntegrityError as exc:
            raise GuildError("project_active") from exc

    async def contribute(
        self,
        actor: int,
        project_id: UUID,
        amount: int,
        *,
        from_treasury: bool = False,
        now: datetime | None = None,
    ) -> ContributionResult:
        """Atomic contribution limited to what the Obra still needs (§30.2).

        Any member contributes from the own wallet; only the Leader spends the Treasury.
        A fully funded Obra enters Construção at once.
        """
        now = _utcnow(now)
        _positive(amount)
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
            _ensure_not_dissolving(guild)
            if from_treasury and membership.role != GuildRole.LEADER.value:
                raise GuildError("no_permission")
            wallet = await self._lock_character_id(session, character.id)
            assert wallet is not None
            project = await session.scalar(
                select(GuildProject)
                .where(GuildProject.id == project_id, GuildProject.guild_id == guild.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if project is None:
                raise GuildError("project_missing")
            if project.status != "funding":
                raise GuildError("project_not_funding")
            applied = min(amount, project.cost - project.funded)
            if from_treasury:
                if guild.treasury_crowns < applied:
                    raise GuildError("treasury_insufficient")
                record_treasury(
                    session, guild, "project_funding", -applied, now,
                    character_id=character.id, project_id=project.id,
                )  # fmt: skip
            else:
                if wallet.crowns < applied:
                    raise GuildError("not_enough_crowns")
                wallet.crowns -= applied
            session.add(
                GuildProjectContribution(
                    project_id=project.id,
                    character_id=character.id,
                    source="treasury" if from_treasury else "wallet",
                    amount=applied,
                    created_at=now,
                )
            )
            project.funded += applied
            project.revision += 1
            if project.funded == project.cost:
                project.status = "building"
                project.funded_at = now
                project.completes_at = now + project_build_time(project.level)
                audit(
                    session, guild.id, "project_funded", character.id, None, now,
                    {"kind": project.kind, "level": project.level},
                )  # fmt: skip
            guild.revision += 1
            await session.flush()
            if not from_treasury:
                # §36: review signal only; linked accounts funding one Obra are never blocked.
                contributors = await session.scalars(
                    select(Character).where(
                        Character.id.in_(
                            select(GuildProjectContribution.character_id).where(
                                GuildProjectContribution.project_id == project.id,
                                GuildProjectContribution.source == "wallet",
                            )
                        )
                    )
                )
                await record_linked_cooccurrence(
                    session,
                    server_id=self.server_id,
                    activity_kind="guild_project",
                    activity_reference=str(project.id),
                    characters=contributors.all(),
                    now=now,
                )
            return ContributionResult(
                applied=applied, guild=await self._guild_view(session, guild, character.id)
            )

    async def rename(
        self,
        actor: int,
        *,
        name: str | None = None,
        tag: str | None = None,
        now: datetime | None = None,
    ) -> GuildView:
        """15.000 Coroas from the Treasury, 30-day recharge; Name, TAG or both (§49.10)."""
        now = _utcnow(now)
        try:
            new_name = normalize_guild_name(name) if name is not None else None
            new_tag = normalize_guild_tag(tag) if tag is not None else None
        except GuildNameError as exc:
            raise GuildError(exc.code) from exc
        await self._maintain_actor(actor, now)
        try:
            async with self.sessions.begin() as session:
                character, guild, membership = await self._actor_guild(session, actor, now)
                if membership.role != GuildRole.LEADER.value:
                    raise GuildError("no_permission")
                _ensure_not_dissolving(guild)
                final_name = new_name if new_name is not None else guild.name
                final_tag = new_tag if new_tag is not None else guild.tag
                if final_name == guild.name and final_tag == guild.tag:
                    raise GuildError("rename_unchanged")
                if (
                    guild.last_renamed_at is not None
                    and now < guild.last_renamed_at + RENAME_COOLDOWN
                ):
                    raise GuildError("rename_cooldown")
                if guild.treasury_crowns < RENAME_COST:
                    raise GuildError("treasury_insufficient")
                await self._check_name_free(
                    session, final_name, final_tag, now, own_guild_id=guild.id
                )
                session.add(
                    GuildNameHistory(
                        guild_id=guild.id,
                        server_id=guild.server_id,
                        old_name=guild.name,
                        old_tag=guild.tag,
                        new_name=final_name,
                        new_tag=final_tag,
                        actor_character_id=character.id,
                        renamed_at=now,
                        reserved_until=now + OLD_NAME_RETENTION,
                    )
                )
                record_treasury(
                    session, guild, "rename", -RENAME_COST, now, character_id=character.id
                )
                audit(
                    session, guild.id, "guild_renamed", character.id, None, now,
                    {"old": f"[{guild.tag}] {guild.name}", "new": f"[{final_tag}] {final_name}"},
                )  # fmt: skip
                guild.name = final_name
                guild.tag = final_tag
                guild.last_renamed_at = now
                guild.revision += 1
                await session.flush()
                return await self._guild_view(session, guild, character.id)
        except IntegrityError as exc:
            raise GuildError("name_or_tag_taken") from exc

    async def handle_permanent_ban(
        self, character_id: UUID, *, now: datetime | None = None
    ) -> UUID | None:
        """§30.3: a permanent ban of the Leader starts succession at once, without
        waiting for inactivity. Entry point for the future moderation flow (no ban
        system exists yet). The banned Leader keeps membership as a common Member.
        Returns the new Leader, or None when there was nothing to hand over."""
        now = _utcnow(now)
        async with self.sessions() as session:
            guild_id = await session.scalar(
                select(GuildMember.guild_id).where(GuildMember.character_id == character_id)
            )
        if guild_id is None:
            return None
        async with self.sessions.begin() as session:
            guild = await self._lock_guild(session, guild_id)
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
            banned = next((m for m in members if m.character_id == character_id), None)
            if banned is None or banned.role != GuildRole.LEADER.value:
                return None
            return await promote_successor(
                session, guild, members, banned, now,
                reason="ban", old_leader_role=GuildRole.MEMBER,
            )  # fmt: skip

    # ---------------------------------------------------------- dissolution

    async def request_dissolution(self, actor: int, *, now: datetime | None = None) -> GuildView:
        """Leader starts the 72h safety period; Treasury and Obras freeze meanwhile."""
        now = _utcnow(now)
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
            if membership.role != GuildRole.LEADER.value:
                raise GuildError("no_permission")
            if guild.dissolution_due_at is not None:
                return await self._guild_view(session, guild, character.id)
            guild.dissolution_requested_at = now
            guild.dissolution_due_at = now + DISSOLUTION_PERIOD
            guild.revision += 1
            audit(session, guild.id, "dissolution_requested", character.id, None, now)
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    async def cancel_dissolution(self, actor: int, *, now: datetime | None = None) -> GuildView:
        now = _utcnow(now)
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
            if membership.role != GuildRole.LEADER.value:
                raise GuildError("no_permission")
            if guild.dissolution_due_at is not None:
                guild.dissolution_requested_at = None
                guild.dissolution_due_at = None
                guild.revision += 1
                audit(session, guild.id, "dissolution_cancelled", character.id, None, now)
            await session.flush()
            return await self._guild_view(session, guild, character.id)

    # -------------------------------------------------------------- helpers

    async def _set_role(
        self, actor: int, target_character_id: UUID, role: GuildRole, now: datetime | None
    ) -> GuildView:
        now = _utcnow(now)
        await self._maintain_actor(actor, now)
        async with self.sessions.begin() as session:
            character, guild, membership = await self._actor_guild(session, actor, now)
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
                audit(session, guild.id, action, character.id, target_character_id, now)
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
                last_active_at=now,
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
        audit(
            session, guild.id, "member_joined", actor_id or character.id, character.id, now,
            {"source": source},
        )  # fmt: skip
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

    async def _check_name_free(
        self,
        session: AsyncSession,
        name: str,
        tag: str,
        now: datetime,
        *,
        own_guild_id: UUID | None = None,
    ) -> None:
        """Active Guilds and Names/TAGs retained after a rename are both taken."""
        active = select(Guild.id).where(
            Guild.server_id == self.server_id,
            Guild.status == "active",
            or_(func.lower(Guild.name) == name.casefold(), Guild.tag == tag),
        )
        reserved = select(GuildNameHistory.id).where(
            GuildNameHistory.server_id == self.server_id,
            GuildNameHistory.reserved_until > now,
            or_(
                and_(
                    func.lower(GuildNameHistory.old_name) == name.casefold(),
                    GuildNameHistory.old_name != GuildNameHistory.new_name,
                ),
                and_(
                    GuildNameHistory.old_tag == tag,
                    GuildNameHistory.old_tag != GuildNameHistory.new_tag,
                ),
            ),
        )
        if own_guild_id is not None:
            active = active.where(Guild.id != own_guild_id)
            reserved = reserved.where(GuildNameHistory.guild_id != own_guild_id)
        if await session.scalar(active.limit(1)) is not None:
            raise GuildError("name_or_tag_taken")
        if await session.scalar(reserved.limit(1)) is not None:
            raise GuildError("name_or_tag_reserved")

    async def _actor_guild(
        self,
        session: AsyncSession,
        actor: int,
        now: datetime,
        *,
        guild_id: UUID | None = None,
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
        membership.last_active_at = max(membership.last_active_at, now)
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
            select(Character)
            .where(Character.id == character_id)
            .with_for_update()
            .execution_options(populate_existing=True)
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
        projects = (
            await session.scalars(
                select(GuildProject)
                .where(GuildProject.guild_id == guild.id, GuildProject.status != "cancelled")
                .order_by(GuildProject.started_at, GuildProject.id)
                .execution_options(populate_existing=True)
            )
        ).all()
        levels = {kind: 0 for kind in ProjectKind}
        for project in projects:
            if project.status == "completed":
                kind = ProjectKind(project.kind)
                levels[kind] = max(levels[kind], project.level)
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
            treasury_crowns=guild.treasury_crowns,
            obra_levels=tuple(levels.items()),
            active_projects=tuple(
                GuildProjectView(
                    project_id=project.id,
                    kind=ProjectKind(project.kind),
                    level=project.level,
                    status=project.status,
                    cost=project.cost,
                    funded=project.funded,
                    completes_at=project.completes_at,
                )
                for project in projects
                if project.status in ACTIVE_PROJECT_STATES
            ),
            rename_available_at=(
                guild.last_renamed_at + RENAME_COOLDOWN if guild.last_renamed_at else None
            ),
            dissolution_due_at=guild.dissolution_due_at,
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
            character_telegram_id=character.telegram_id,
        )


def _capacity(guild: Guild) -> int:
    return capacity_for_lodging(guild.lodging_level)


def _positive(amount: int) -> None:
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise GuildError("invalid_amount")


def _ensure_not_dissolving(guild: Guild) -> None:
    """§30.3: deposits freeze and no new commitments start during dissolution."""
    if guild.dissolution_due_at is not None:
        raise GuildError("guild_dissolving")


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
