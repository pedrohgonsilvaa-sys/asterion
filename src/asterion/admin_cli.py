"""Operator CLI for suspensions, admin roles and the audit log. Never exposed to players.

Every command except ``bootstrap-owner`` needs ``--as <telegram_id>`` (who is acting);
the role check and the audit row happen in `AdminService`, not here.

Usage:
    python -m asterion.admin_cli bootstrap-owner <telegram_id> --reason "motivo"
    python -m asterion.admin_cli --as <id> suspend <telegram_id> --reason "motivo" [--hours 72]
    python -m asterion.admin_cli --as <id> lift <telegram_id> --reason "motivo"
    python -m asterion.admin_cli --as <id> list
    python -m asterion.admin_cli --as <id> history <telegram_id>
    python -m asterion.admin_cli --as <id> role-grant <telegram_id> <role> --reason "motivo"
    python -m asterion.admin_cli --as <id> role-revoke <telegram_id> <role> --reason "motivo"
    python -m asterion.admin_cli --as <id> roles
    python -m asterion.admin_cli --as <id> audit [--target <id>] [--limit 50]

Roles: support (só leitura), moderator, operator, owner.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.admin import AdminError, AdminRole, AdminService
from asterion.application.sanctions import SanctionView

_ROLES = [role.value for role in AdminRole]


def add_actor_argument(parser: argparse.ArgumentParser, *, required: bool = True) -> None:
    parser.add_argument(
        "--as",
        dest="actor",
        type=int,
        required=required,
        help="telegram_id de quem está agindo (precisa de papel de administração)",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.admin_cli")
    add_actor_argument(parser, required=False)
    sub = parser.add_subparsers(dest="command", required=True)
    boot = sub.add_parser("bootstrap-owner", help="criar o primeiro Dono (só sem Dono ativo)")
    boot.add_argument("telegram_id", type=int)
    boot.add_argument("--reason", required=True)
    suspend = sub.add_parser("suspend", help="suspender uma conta")
    suspend.add_argument("telegram_id", type=int)
    suspend.add_argument("--reason", required=True)
    suspend.add_argument("--hours", type=int, help="sem isso, a suspensão não expira")
    lift = sub.add_parser("lift", help="encerrar as suspensões ativas de uma conta")
    lift.add_argument("telegram_id", type=int)
    lift.add_argument("--reason", required=True)
    sub.add_parser("list", help="listar suspensões ativas")
    history = sub.add_parser("history", help="histórico de uma conta")
    history.add_argument("telegram_id", type=int)
    for name in ("role-grant", "role-revoke"):
        role = sub.add_parser(name)
        role.add_argument("telegram_id", type=int)
        role.add_argument("role", choices=_ROLES)
        role.add_argument("--reason", required=True)
    sub.add_parser("roles", help="listar papéis ativos")
    audit = sub.add_parser("audit", help="registro de ações administrativas (só Dono)")
    audit.add_argument("--target")
    audit.add_argument("--limit", type=int, default=50)
    return parser


def _line(row: SanctionView) -> str:
    until = f"{row.expires_at:%Y-%m-%d %H:%M}" if row.expires_at else "sem fim"
    state = f"encerrada {row.revoked_at:%Y-%m-%d %H:%M}" if row.revoked_at else "ativa"
    return (
        f"{row.telegram_id}  {state}  desde {row.created_at:%Y-%m-%d %H:%M}  até {until}  "
        f"por {row.created_by}  motivo={row.reason!r}"
    )


async def _dispatch(args: argparse.Namespace, admin: AdminService) -> list[str]:
    if args.command == "bootstrap-owner":
        row = await admin.bootstrap_owner(args.telegram_id, args.reason)
        return [f"{row.telegram_id} agora é {row.role}"]
    actor = args.actor
    if args.command == "suspend":
        row = await admin.suspend(actor, args.telegram_id, reason=args.reason, hours=args.hours)
        return [_line(row)]
    if args.command == "lift":
        count = await admin.lift(actor, args.telegram_id, reason=args.reason)
        return [f"{count} suspensão(ões) encerrada(s)"]
    if args.command == "list":
        return [_line(r) for r in await admin.active_sanctions(actor)] or [
            "nenhuma suspensão ativa"
        ]
    if args.command == "history":
        return [_line(r) for r in await admin.sanction_history(actor, args.telegram_id)] or [
            "sem histórico"
        ]
    if args.command == "role-grant":
        row = await admin.grant_role(actor, args.telegram_id, AdminRole(args.role), args.reason)
        return [f"{row.telegram_id} agora é {row.role}"]
    if args.command == "role-revoke":
        count = await admin.revoke_role(
            actor, args.telegram_id, AdminRole(args.role), args.reason
        )
        return [f"{count} papel(éis) revogado(s)"]
    if args.command == "roles":
        return [
            f"{r.telegram_id}  {r.role}  por {r.granted_by}  desde {r.granted_at:%Y-%m-%d %H:%M}"
            for r in await admin.list_roles(actor)
        ] or ["nenhum papel ativo"]
    rows = await admin.audit_log(actor, target_id=args.target, limit=args.limit)
    return [
        f"{r.created_at:%Y-%m-%d %H:%M}  {r.outcome:<6}  {r.actor_telegram_id}  {r.action}  "
        f"{r.target_type}:{r.target_id}  motivo={r.reason!r}  "
        f"{json.dumps(r.details, ensure_ascii=False, sort_keys=True)}"
        for r in rows
    ] or ["registro vazio"]


async def run(argv: Sequence[str], sessions: async_sessionmaker[AsyncSession]) -> list[str]:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command != "bootstrap-owner" and args.actor is None:
        parser.error("--as <telegram_id> é obrigatório")
    try:
        return await _dispatch(args, AdminService(sessions))
    except AdminError as exc:
        return [f"erro: {exc}"]


def main(argv: Sequence[str] | None = None) -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from asterion.infrastructure.db.session import SessionFactory, engine

    async def _main() -> list[str]:
        try:
            return await run(sys.argv[1:] if argv is None else argv, SessionFactory)
        finally:
            await engine.dispose()

    lines = asyncio.run(_main())
    for line in lines:
        print(line)
    if lines and lines[0].startswith("erro: "):
        sys.exit(1)


if __name__ == "__main__":
    main()
