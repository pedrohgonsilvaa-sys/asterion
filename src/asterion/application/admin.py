"""Operator roles (RBAC) and the audit log for every administrative action (B5, GDD §43.7).

Every operator action goes through `AdminService`. Each call:

1. checks the actor's active roles inside the transaction;
2. runs the underlying service *in that same transaction* (see `_Joined`);
3. writes one `admin_actions` row before the commit, so the action and its audit
   commit or roll back together.

A denied attempt is written as an `admin_actions` row with outcome ``denied`` in its
own transaction, then `AdminPermissionDenied` is raised. Reads are checked but not
logged. Roles and permissions were chosen by the author on 2026-11-11, since the GDD
does not define them.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import AccountRiskAdmin, FlagView
from asterion.application.chronicle import ChronicleAdmin, ChronicleService, CycleStatus
from asterion.application.outbox import OutboxStats, outbox_stats, requeue_dead
from asterion.application.promo_codes import PromoCodeAdmin, PromoCodeRow
from asterion.application.sanctions import SanctionService, SanctionView
from asterion.application.social import ContentModerationAdmin, ReportResolution, ReportView
from asterion.domain.chronicle import Calendar
from asterion.infrastructure.db.models import AdminAction, AdminRoleGrant

T = TypeVar("T")

# Serialises bootstrap/grant/revoke so "no owner yet" and "last owner" checks hold.
_ROLES_LOCK = 0x41444D4E


class AdminRole(StrEnum):
    SUPPORT = "support"
    MODERATOR = "moderator"
    OPERATOR = "operator"
    OWNER = "owner"


class Permission(StrEnum):
    READ = "read"
    SANCTION = "sanction"
    RISK_REVIEW = "risk_review"
    REPORT_RESOLVE = "report_resolve"
    OPS = "ops"
    ECONOMY = "economy"
    ROLES = "roles"


ROLE_PERMISSIONS: dict[AdminRole, frozenset[Permission]] = {
    AdminRole.SUPPORT: frozenset({Permission.READ}),
    AdminRole.MODERATOR: frozenset(
        {Permission.READ, Permission.SANCTION, Permission.RISK_REVIEW, Permission.REPORT_RESOLVE}
    ),
    AdminRole.OPERATOR: frozenset({Permission.READ, Permission.OPS}),
    AdminRole.OWNER: frozenset(Permission),
}


class AdminError(ValueError):
    pass


class AdminPermissionDenied(AdminError):
    def __init__(self, actor: int, action: str, permission: Permission):
        super().__init__(f"admin_denied:{action}")
        self.actor = actor
        self.action = action
        self.permission = permission


@dataclass(frozen=True, slots=True)
class RoleView:
    telegram_id: int
    role: str
    granted_by: int
    granted_at: datetime


@dataclass(frozen=True, slots=True)
class AuditView:
    id: str
    actor_telegram_id: int
    action: str
    outcome: str
    target_type: str | None
    target_id: str | None
    reason: str | None
    details: dict[str, Any]
    created_at: datetime


class _Same:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _Joined:
    """Looks like an `async_sessionmaker`, but every `()`/`.begin()` reuses one session.

    The outer transaction owns commit and rollback, so the wrapped service and the
    audit row are atomic.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self) -> _Same:
        return _Same(self._session)

    def begin(self) -> _Same:
        return _Same(self._session)


def _reason(reason: str | None) -> str:
    if reason is None or not reason.strip():
        raise AdminError("admin_reason_required")
    return reason.strip()[:500]


class AdminService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str | None = None,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.sessions = sessions
        self.server_id = server_id
        self._now = now

    # -- core -----------------------------------------------------------------

    async def roles_of(self, telegram_id: int) -> frozenset[AdminRole]:
        async with self.sessions() as session:
            return await self._roles(session, telegram_id)

    async def _roles(self, session: AsyncSession, telegram_id: int) -> frozenset[AdminRole]:
        rows = await session.scalars(
            select(AdminRoleGrant.role).where(
                AdminRoleGrant.telegram_id == telegram_id, AdminRoleGrant.revoked_at.is_(None)
            )
        )
        return frozenset(AdminRole(role) for role in rows)

    async def _allowed(self, session: AsyncSession, actor: int, permission: Permission) -> bool:
        roles = await self._roles(session, actor)
        return any(permission in ROLE_PERMISSIONS[role] for role in roles)

    async def _deny(
        self,
        actor: int,
        action: str,
        permission: Permission,
        target: tuple[str, Any] | None,
        reason: str | None,
    ) -> AdminPermissionDenied:
        async with self.sessions.begin() as session:
            session.add(
                self._row(
                    actor, action, "denied", target, reason, {"permission": permission.value}
                )
            )
        return AdminPermissionDenied(actor, action, permission)

    def _row(self, actor, action, outcome, target, reason, details) -> AdminAction:
        return AdminAction(
            actor_telegram_id=actor,
            action=action,
            outcome=outcome,
            target_type=target[0] if target else None,
            target_id=str(target[1])[:64] if target else None,
            reason=reason.strip()[:500] if reason and reason.strip() else None,
            details=details,
            created_at=self._now(),
        )

    async def _read(
        self,
        actor: int,
        action: str,
        call: Callable[[Any], Awaitable[T]],
        permission: Permission = Permission.READ,
    ) -> T:
        async with self.sessions() as session:
            if await self._allowed(session, actor, permission):
                return await call(_Joined(session))
        raise await self._deny(actor, action, permission, None, None)

    async def _act(
        self,
        actor: int,
        action: str,
        permission: Permission,
        reason: str | None,
        call: Callable[[Any], Awaitable[T]],
        *,
        target: tuple[str, Any] | None = None,
        details: Callable[[T], dict[str, Any]] | None = None,
    ) -> T:
        async with self.sessions.begin() as session:
            allowed = await self._allowed(session, actor, permission)
            if allowed:
                text_reason = _reason(reason)
                result = await call(_Joined(session))
                session.add(
                    self._row(
                        actor,
                        action,
                        "ok",
                        target,
                        text_reason,
                        details(result) if details else {},
                    )
                )
                await session.flush()
                return result
        raise await self._deny(actor, action, permission, target, reason)

    def _server(self) -> str:
        if self.server_id is None:
            raise AdminError("admin_server_required")
        return self.server_id

    # -- roles ----------------------------------------------------------------

    async def bootstrap_owner(self, telegram_id: int, reason: str) -> RoleView:
        """Create the first Dono. Works only while no active Dono exists."""
        text_reason = _reason(reason)
        async with self.sessions.begin() as session:
            await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ROLES_LOCK})
            owners = await session.scalar(
                select(func.count())
                .select_from(AdminRoleGrant)
                .where(
                    AdminRoleGrant.role == AdminRole.OWNER.value,
                    AdminRoleGrant.revoked_at.is_(None),
                )
            )
            if owners:
                raise AdminError("admin_bootstrap_closed")
            row = self._grant_row(telegram_id, AdminRole.OWNER, telegram_id)
            session.add(row)
            session.add(
                self._row(
                    telegram_id,
                    "role.bootstrap_owner",
                    "ok",
                    ("account", telegram_id),
                    text_reason,
                    {"role": AdminRole.OWNER.value},
                )
            )
            return _role_view(row)

    def _grant_row(self, telegram_id: int, role: AdminRole, by: int) -> AdminRoleGrant:
        return AdminRoleGrant(
            telegram_id=telegram_id, role=role.value, granted_by=by, granted_at=self._now()
        )

    async def grant_role(
        self, actor: int, telegram_id: int, role: AdminRole, reason: str
    ) -> RoleView:
        async def call(joined: _Joined) -> RoleView:
            async with joined.begin() as session:
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ROLES_LOCK}
                )
                if role in await self._roles(session, telegram_id):
                    raise AdminError("admin_role_exists")
                row = self._grant_row(telegram_id, role, actor)
                session.add(row)
                return _role_view(row)

        return await self._act(
            actor,
            "role.grant",
            Permission.ROLES,
            reason,
            call,
            target=("account", telegram_id),
            details=lambda _: {"role": role.value},
        )

    async def revoke_role(self, actor: int, telegram_id: int, role: AdminRole, reason: str) -> int:
        async def call(joined: _Joined) -> int:
            async with joined.begin() as session:
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ROLES_LOCK}
                )
                active = AdminRoleGrant.revoked_at.is_(None)
                if role is AdminRole.OWNER:
                    owners = await session.scalar(
                        select(func.count())
                        .select_from(AdminRoleGrant)
                        .where(AdminRoleGrant.role == role.value, active)
                    )
                    if owners == 1 and role in await self._roles(session, telegram_id):
                        raise AdminError("admin_last_owner")
                rows = (
                    await session.scalars(
                        select(AdminRoleGrant)
                        .where(
                            AdminRoleGrant.telegram_id == telegram_id,
                            AdminRoleGrant.role == role.value,
                            active,
                        )
                        .with_for_update()
                    )
                ).all()
                for row in rows:
                    row.revoked_at, row.revoked_by = self._now(), actor
                return len(rows)

        return await self._act(
            actor,
            "role.revoke",
            Permission.ROLES,
            reason,
            call,
            target=("account", telegram_id),
            details=lambda count: {"role": role.value, "revoked": count},
        )

    async def list_roles(self, actor: int) -> list[RoleView]:
        async def call(joined: _Joined) -> list[RoleView]:
            async with joined() as session:
                rows = await session.scalars(
                    select(AdminRoleGrant)
                    .where(AdminRoleGrant.revoked_at.is_(None))
                    .order_by(AdminRoleGrant.telegram_id, AdminRoleGrant.role)
                )
                return [_role_view(row) for row in rows]

        return await self._read(actor, "role.list", call)

    async def audit_log(
        self, actor: int, *, target_id: str | None = None, limit: int = 50
    ) -> list[AuditView]:
        async def call(joined: _Joined) -> list[AuditView]:
            async with joined() as session:
                statement = select(AdminAction).order_by(AdminAction.created_at.desc())
                if target_id is not None:
                    statement = statement.where(AdminAction.target_id == target_id)
                rows = await session.scalars(statement.limit(limit))
                return [_audit_view(row) for row in rows]

        return await self._read(actor, "audit.list", call, Permission.ROLES)

    # -- sanctions (Moderador) -------------------------------------------------

    async def suspend(
        self, actor: int, telegram_id: int, *, reason: str, hours: int | None = None
    ) -> SanctionView:
        return await self._act(
            actor,
            "sanction.suspend",
            Permission.SANCTION,
            reason,
            lambda s: SanctionService(s, now=self._now).suspend(
                telegram_id, reason=_reason(reason), by=f"tg:{actor}", hours=hours
            ),
            target=("account", telegram_id),
            details=lambda row: {"sanction_id": row.id, "hours": hours},
        )

    async def lift(self, actor: int, telegram_id: int, *, reason: str) -> int:
        return await self._act(
            actor,
            "sanction.lift",
            Permission.SANCTION,
            reason,
            lambda s: SanctionService(s, now=self._now).lift(telegram_id, by=f"tg:{actor}"),
            target=("account", telegram_id),
            details=lambda count: {"lifted": count},
        )

    async def active_sanctions(self, actor: int) -> list[SanctionView]:
        return await self._read(actor, "sanction.list", lambda s: SanctionService(s).active())

    async def sanction_history(self, actor: int, telegram_id: int) -> list[SanctionView]:
        return await self._read(
            actor, "sanction.history", lambda s: SanctionService(s).history(telegram_id)
        )

    # -- antiexploit §36 (Moderador) ------------------------------------------

    async def link_accounts(
        self, actor: int, first: int, second: int, *, reason: str, note: str | None = None
    ) -> bool:
        return await self._act(
            actor,
            "risk.link",
            Permission.RISK_REVIEW,
            reason,
            lambda s: AccountRiskAdmin(s).link(first, second, note=note),
            target=("account_pair", f"{min(first, second)}+{max(first, second)}"),
            details=lambda created: {"created": created},
        )

    async def unlink_accounts(self, actor: int, first: int, second: int, *, reason: str) -> bool:
        return await self._act(
            actor,
            "risk.unlink",
            Permission.RISK_REVIEW,
            reason,
            lambda s: AccountRiskAdmin(s).unlink(first, second),
            target=("account_pair", f"{min(first, second)}+{max(first, second)}"),
            details=lambda removed: {"removed": removed},
        )

    async def review_flag(
        self, actor: int, flag_id: UUID, status: str, *, reason: str, note: str | None = None
    ) -> FlagView | None:
        return await self._act(
            actor,
            "risk.review_flag",
            Permission.RISK_REVIEW,
            reason,
            lambda s: AccountRiskAdmin(s).review(flag_id, status, note=note),
            target=("risk_flag", flag_id),
            details=lambda flag: {"status": status, "found": flag is not None},
        )

    async def account_links(self, actor: int) -> list[tuple[int, int, str | None]]:
        return await self._read(actor, "risk.links", lambda s: AccountRiskAdmin(s).links())

    async def risk_flags(
        self, actor: int, *, status: str | None, limit: int = 50
    ) -> list[FlagView]:
        return await self._read(
            actor, "risk.flags", lambda s: AccountRiskAdmin(s).flags(status=status, limit=limit)
        )

    # -- content reports §31.1 (Moderador) ------------------------------------

    async def list_reports(self, actor: int, status: str) -> tuple[ReportView, ...]:
        return await self._read(
            actor, "report.list", lambda s: ContentModerationAdmin(s).list_reports(status)
        )

    async def resolve_report(
        self, actor: int, report_id: UUID, *, uphold: bool, reason: str, note: str | None = None
    ) -> ReportResolution:
        return await self._act(
            actor,
            "report.resolve",
            Permission.REPORT_RESOLVE,
            reason,
            lambda s: ContentModerationAdmin(s).resolve(report_id, uphold=uphold, note=note),
            target=("content_report", report_id),
            details=lambda result: {"uphold": uphold, "removed": result.removed},
        )

    # -- outbox §43.5 (Operador) ----------------------------------------------

    async def outbox_stats(self, actor: int) -> OutboxStats:
        return await self._read(actor, "outbox.stats", outbox_stats)

    async def requeue_outbox(self, actor: int, ids: list[UUID] | None, *, reason: str) -> int:
        return await self._act(
            actor,
            "outbox.requeue",
            Permission.OPS,
            reason,
            lambda s: requeue_dead(s, ids),
            target=("outbox", "dead"),
            details=lambda count: {
                "ids": [str(i) for i in ids] if ids is not None else None,
                "count": count,
            },
        )

    # -- Crônica (status: leitura; maintenance: Operador; resto: Dono) ---------

    async def chronicle_status(self, actor: int) -> CycleStatus | None:
        return await self._read(
            actor, "chronicle.status", lambda s: ChronicleAdmin(s, self._server()).status()
        )

    async def chronicle_maintenance(self, actor: int, *, reason: str) -> None:
        return await self._act(
            actor,
            "chronicle.maintenance",
            Permission.OPS,
            reason,
            lambda s: ChronicleService(s, self._server()).run_maintenance(),
            target=("server", self.server_id),
        )

    async def set_day1(
        self, actor: int, day1: date, *, reason: str, now: datetime | None = None
    ) -> Calendar:
        return await self._act(
            actor,
            "chronicle.set_day1",
            Permission.ECONOMY,
            reason,
            lambda s: ChronicleAdmin(s, self._server()).set_day1(day1, _reason(reason), now=now),
            target=("server", self.server_id),
            details=lambda _: {"day1": day1.isoformat()},
        )

    async def extend_chronicle(
        self, actor: int, end_at: datetime, *, reason: str, now: datetime | None = None
    ) -> Calendar:
        return await self._act(
            actor,
            "chronicle.extend",
            Permission.ECONOMY,
            reason,
            lambda s: ChronicleAdmin(s, self._server()).extend(end_at, _reason(reason), now=now),
            target=("server", self.server_id),
            details=lambda _: {"end_at": end_at.isoformat()},
        )

    async def grant_pass(
        self,
        actor: int,
        telegram_id: int,
        *,
        source: str,
        reason: str,
        now: datetime | None = None,
    ) -> datetime:
        return await self._act(
            actor,
            "chronicle.pass_grant",
            Permission.ECONOMY,
            reason,
            lambda s: ChronicleAdmin(s, self._server()).grant_pass(telegram_id, source, now=now),
            target=("account", telegram_id),
            details=lambda at: {"source": source, "premium_at": at.isoformat()},
        )

    # -- Códigos de Asterion (lista: leitura; resto: Dono) ---------------------

    async def list_codes(self, actor: int) -> tuple[PromoCodeRow, ...]:
        return await self._read(
            actor, "code.list", lambda s: PromoCodeAdmin(s, self._server()).list_codes()
        )

    async def create_code(self, actor: int, *, reason: str, **fields: Any) -> PromoCodeRow:
        return await self._act(
            actor,
            "code.create",
            Permission.ECONOMY,
            reason,
            lambda s: PromoCodeAdmin(s, self._server()).create(**fields),
            target=("promo_code", fields.get("code")),
            details=lambda row: {
                "code": row.code,
                "expires_at": row.expires_at.isoformat(),
                "global_limit": row.global_limit,
            },
        )

    async def set_code_active(self, actor: int, code: str, active: bool, *, reason: str) -> None:
        return await self._act(
            actor,
            "code.enable" if active else "code.disable",
            Permission.ECONOMY,
            reason,
            lambda s: PromoCodeAdmin(s, self._server()).set_active(code, active),
            target=("promo_code", code),
        )


def _role_view(row: AdminRoleGrant) -> RoleView:
    return RoleView(row.telegram_id, row.role, row.granted_by, row.granted_at)


def _audit_view(row: AdminAction) -> AuditView:
    return AuditView(
        str(row.id),
        row.actor_telegram_id,
        row.action,
        row.outcome,
        row.target_type,
        row.target_id,
        row.reason,
        dict(row.details or {}),
        row.created_at,
    )
