"""Admin roles (RBAC) and the append-only audit log (B5, GDD §43.7)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from asterion.admin_cli import run as cli_run
from asterion.application.admin import (
    ROLE_PERMISSIONS,
    AdminError,
    AdminPermissionDenied,
    AdminRole,
    AdminService,
    Permission,
)
from asterion.application.chronicle import ChronicleError
from asterion.infrastructure.db.models import (
    AccountSanction,
    AdminAction,
    ChronicleCycle,
    ChronicleCycleLog,
)

OWNER, MOD, OPS, SUPPORT, NOBODY = 1, 2, 3, 4, 99
SERVER = "srv-test"
BEFORE = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def test_permission_table_matches_author_decision():
    assert ROLE_PERMISSIONS[AdminRole.SUPPORT] == {Permission.READ}
    assert ROLE_PERMISSIONS[AdminRole.MODERATOR] == {
        Permission.READ,
        Permission.SANCTION,
        Permission.RISK_REVIEW,
        Permission.REPORT_RESOLVE,
    }
    assert ROLE_PERMISSIONS[AdminRole.OPERATOR] == {Permission.READ, Permission.OPS}
    assert ROLE_PERMISSIONS[AdminRole.OWNER] == set(Permission)
    for role in (AdminRole.SUPPORT, AdminRole.MODERATOR, AdminRole.OPERATOR):
        assert Permission.ECONOMY not in ROLE_PERMISSIONS[role]
        assert Permission.ROLES not in ROLE_PERMISSIONS[role]


async def _staff(sessions) -> AdminService:
    admin = AdminService(sessions, SERVER)
    await admin.bootstrap_owner(OWNER, "primeiro dono")
    await admin.grant_role(OWNER, MOD, AdminRole.MODERATOR, "moderação")
    await admin.grant_role(OWNER, OPS, AdminRole.OPERATOR, "operação")
    await admin.grant_role(OWNER, SUPPORT, AdminRole.SUPPORT, "suporte")
    return admin


async def _audit(sessions, **where) -> list[AdminAction]:
    async with sessions() as session:
        statement = select(AdminAction).order_by(AdminAction.created_at)
        for key, value in where.items():
            statement = statement.where(getattr(AdminAction, key) == value)
        return list(await session.scalars(statement))


async def _count(sessions, model) -> int:
    async with sessions() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def test_action_without_role_is_denied_and_logged(database):
    sessions = database[1]
    admin = await _staff(sessions)
    with pytest.raises(AdminPermissionDenied):
        await admin.suspend(NOBODY, 50, reason="tentativa")
    assert await _count(sessions, AccountSanction) == 0
    [denied] = await _audit(sessions, actor_telegram_id=NOBODY)
    assert denied.outcome == "denied"
    assert denied.action == "sanction.suspend"
    assert (denied.target_type, denied.target_id) == ("account", "50")
    assert denied.reason == "tentativa"
    assert denied.details == {"permission": "sanction"}


async def test_wrong_role_is_denied_and_reads_are_checked(database):
    sessions = database[1]
    admin = await _staff(sessions)
    for actor in (OPS, SUPPORT):
        with pytest.raises(AdminPermissionDenied):
            await admin.suspend(actor, 50, reason="não pode")
    with pytest.raises(AdminPermissionDenied):
        await admin.requeue_outbox(MOD, None, reason="não pode")
    # Support only reads; a read without any role is denied and logged.
    assert await admin.active_sanctions(SUPPORT) == []
    with pytest.raises(AdminPermissionDenied):
        await admin.active_sanctions(NOBODY)
    with pytest.raises(AdminPermissionDenied):
        await admin.audit_log(MOD)
    denied = await _audit(sessions, outcome="denied")
    assert [row.action for row in denied] == [
        "sanction.suspend",
        "sanction.suspend",
        "outbox.requeue",
        "sanction.list",
        "audit.list",
    ]
    assert await _count(sessions, AccountSanction) == 0


async def test_moderator_action_and_audit_commit_together(database):
    sessions = database[1]
    admin = await _staff(sessions)
    row = await admin.suspend(MOD, 50, reason="multicontas", hours=24)
    assert row.created_by == f"tg:{MOD}"
    lifted = await admin.lift(MOD, 50, reason="recurso aceito")
    assert lifted == 1
    suspend, lift = await _audit(sessions, actor_telegram_id=MOD)
    assert (suspend.action, suspend.outcome, suspend.target_id) == ("sanction.suspend", "ok", "50")
    assert suspend.details == {"sanction_id": row.id, "hours": 24}
    assert suspend.reason == "multicontas"
    assert (lift.action, lift.reason, lift.details) == (
        "sanction.lift",
        "recurso aceito",
        {"lifted": 1},
    )


async def test_failed_or_reasonless_action_writes_no_audit(database):
    sessions = database[1]
    admin = await _staff(sessions)
    before = len(await _audit(sessions))
    with pytest.raises(AdminError, match="admin_reason_required"):
        await admin.suspend(MOD, 50, reason="  ")
    # The underlying rule fails (no Crônica scheduled): nothing of the action stays.
    with pytest.raises(ChronicleError):
        await admin.grant_pass(OWNER, 50, source="manual", reason="cortesia")
    assert len(await _audit(sessions)) == before
    assert await _count(sessions, AccountSanction) == 0


async def test_economy_actions_are_owner_only(database):
    sessions = database[1]
    admin = await _staff(sessions)
    day1 = date(2026, 12, 1)
    for actor in (MOD, OPS):
        with pytest.raises(AdminPermissionDenied):
            await admin.set_day1(actor, day1, reason="anúncio", now=BEFORE)
    assert await _count(sessions, ChronicleCycle) == 0
    calendar = await admin.set_day1(OWNER, day1, reason="anúncio oficial", now=BEFORE)
    assert calendar.day1 == day1
    async with sessions() as session:
        log = await session.scalar(select(ChronicleCycleLog))
    assert log.note == "anúncio oficial"
    [row] = await _audit(sessions, action="chronicle.set_day1", outcome="ok")
    assert (row.actor_telegram_id, row.target_id, row.details) == (
        OWNER,
        SERVER,
        {"day1": "2026-12-01"},
    )
    with pytest.raises(AdminPermissionDenied):
        await admin.set_code_active(OPS, "QUALQUER", False, reason="não pode")


async def test_operator_ops_actions(database):
    sessions = database[1]
    admin = await _staff(sessions)
    assert await admin.requeue_outbox(OPS, None, reason="worker caiu") == 0
    stats = await admin.outbox_stats(SUPPORT)
    assert stats.counts["dead"] == 0
    [row] = await _audit(sessions, action="outbox.requeue")
    assert row.details == {"ids": None, "count": 0}


async def test_roles_bootstrap_grant_and_revoke(database):
    sessions = database[1]
    admin = await _staff(sessions)
    with pytest.raises(AdminError, match="admin_bootstrap_closed"):
        await admin.bootstrap_owner(NOBODY, "golpe")
    with pytest.raises(AdminError, match="admin_role_exists"):
        await admin.grant_role(OWNER, MOD, AdminRole.MODERATOR, "de novo")
    with pytest.raises(AdminPermissionDenied):
        await admin.grant_role(MOD, NOBODY, AdminRole.OWNER, "subir")
    with pytest.raises(AdminError, match="admin_last_owner"):
        await admin.revoke_role(OWNER, OWNER, AdminRole.OWNER, "sair")
    assert await admin.revoke_role(OWNER, MOD, AdminRole.MODERATOR, "saiu da equipe") == 1
    assert await admin.roles_of(MOD) == frozenset()
    with pytest.raises(AdminPermissionDenied):
        await admin.suspend(MOD, 50, reason="sem papel agora")
    # Re-granting after a revoke is allowed (a new row; the old one stays).
    await admin.grant_role(OWNER, MOD, AdminRole.MODERATOR, "voltou")
    assert await admin.roles_of(MOD) == {AdminRole.MODERATOR}
    actions = [row.action for row in await admin.audit_log(OWNER, target_id=str(MOD))]
    assert actions.count("role.grant") >= 2 and "role.revoke" in actions


async def test_audit_log_is_append_only(database):
    sessions = database[1]
    await _staff(sessions)
    for statement in ("UPDATE admin_actions SET reason = 'x'", "DELETE FROM admin_actions"):
        with pytest.raises(DBAPIError, match="append-only"):
            async with sessions.begin() as session:
                await session.execute(text(statement))
    assert len(await _audit(sessions)) == 4


async def test_cli_requires_actor_and_reports_denial(database):
    sessions = database[1]
    await _staff(sessions)
    with pytest.raises(SystemExit):
        await cli_run(["list"], sessions)
    assert await cli_run(["--as", str(NOBODY), "suspend", "50", "--reason", "x"], sessions) == [
        "erro: admin_denied:sanction.suspend"
    ]
    assert "owner" in "\n".join(await cli_run(["--as", str(OWNER), "roles"], sessions))
    [last] = await cli_run(["--as", str(OWNER), "audit", "--limit", "1"], sessions)
    assert "denied" in last and "sanction.suspend" in last
