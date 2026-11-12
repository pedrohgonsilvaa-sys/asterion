"""Operator CLI for multi-account review (GDD §36). Never exposed to players.

Usage:
    python -m asterion.account_risk_cli --as <id> link 111 222 --reason "..." [--note "..."]
    python -m asterion.account_risk_cli --as <id> unlink 111 222 --reason "..."
    python -m asterion.account_risk_cli --as <id> links
    python -m asterion.account_risk_cli --as <id> flags [--status open|reviewed|dismissed|all]
    python -m asterion.account_risk_cli --as <id> review <flag_id> reviewed --reason "..."

``--as`` is who is acting; the role check and the audit row live in `AdminService`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.admin_cli import add_actor_argument
from asterion.application.account_risk import FlagView
from asterion.application.admin import AdminError, AdminService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.account_risk_cli")
    add_actor_argument(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    link = sub.add_parser("link", help="vincular duas contas Telegram")
    link.add_argument("first", type=int)
    link.add_argument("second", type=int)
    link.add_argument("--note")
    link.add_argument("--reason", required=True)
    unlink = sub.add_parser("unlink", help="remover vínculo entre duas contas")
    unlink.add_argument("first", type=int)
    unlink.add_argument("second", type=int)
    unlink.add_argument("--reason", required=True)
    sub.add_parser("links", help="listar vínculos")
    flags = sub.add_parser("flags", help="listar flags")
    flags.add_argument("--status", default="open", choices=("open", "reviewed", "dismissed", "all"))
    flags.add_argument("--limit", type=int, default=50)
    review = sub.add_parser("review", help="mudar o status de uma flag")
    review.add_argument("flag_id", type=UUID)
    review.add_argument("status", choices=("open", "reviewed", "dismissed"))
    review.add_argument("--note")
    review.add_argument("--reason", required=True)
    return parser


def _format_flag(flag: FlagView) -> str:
    return (
        f"{flag.id}  {flag.status:<9}  {flag.created_at:%Y-%m-%d %H:%M}  "
        f"{flag.account_a}+{flag.account_b}  {flag.server_id}  "
        f"{flag.activity_kind}:{flag.activity_reference}  "
        f"{json.dumps(flag.evidence, ensure_ascii=False, sort_keys=True)}"
        + (f"  nota={flag.review_note!r}" if flag.review_note else "")
    )


async def run(argv: Sequence[str], sessions: async_sessionmaker[AsyncSession]) -> list[str]:
    args = _parser().parse_args(argv)
    try:
        return await _dispatch(args, AdminService(sessions), args.actor)
    except AdminError as exc:
        return [f"erro: {exc}"]


async def _dispatch(args: argparse.Namespace, admin: AdminService, actor: int) -> list[str]:
    if args.command == "link":
        created = await admin.link_accounts(
            actor, args.first, args.second, reason=args.reason, note=args.note
        )
        return ["vínculo criado" if created else "vínculo já existia"]
    if args.command == "unlink":
        removed = await admin.unlink_accounts(actor, args.first, args.second, reason=args.reason)
        return ["vínculo removido" if removed else "vínculo não encontrado"]
    if args.command == "links":
        rows = await admin.account_links(actor)
        return [f"{a}+{b}" + (f"  {note}" if note else "") for a, b, note in rows] or [
            "nenhum vínculo"
        ]
    if args.command == "flags":
        status = None if args.status == "all" else args.status
        rows = await admin.risk_flags(actor, status=status, limit=args.limit)
        return [_format_flag(row) for row in rows] or ["nenhuma flag"]
    flag = await admin.review_flag(
        actor, args.flag_id, args.status, reason=args.reason, note=args.note
    )
    return [_format_flag(flag)] if flag else ["flag não encontrada"]


def main(argv: Sequence[str] | None = None) -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from asterion.infrastructure.db.session import SessionFactory, engine

    async def _main() -> list[str]:
        try:
            return await run(sys.argv[1:] if argv is None else argv, SessionFactory)
        finally:
            await engine.dispose()

    for line in asyncio.run(_main()):
        print(line)


if __name__ == "__main__":
    main()
