"""Operator CLI for multi-account review (GDD §36). Never exposed to players.

Usage:
    python -m asterion.account_risk_cli link 111 222 --note "mesmo dono, declarado"
    python -m asterion.account_risk_cli unlink 111 222
    python -m asterion.account_risk_cli links
    python -m asterion.account_risk_cli flags [--status open|reviewed|dismissed|all] [--limit N]
    python -m asterion.account_risk_cli review <flag_id> reviewed|dismissed|open [--note "..."]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import AccountRiskAdmin, FlagView


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.account_risk_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    link = sub.add_parser("link", help="vincular duas contas Telegram")
    link.add_argument("first", type=int)
    link.add_argument("second", type=int)
    link.add_argument("--note")
    unlink = sub.add_parser("unlink", help="remover vínculo entre duas contas")
    unlink.add_argument("first", type=int)
    unlink.add_argument("second", type=int)
    sub.add_parser("links", help="listar vínculos")
    flags = sub.add_parser("flags", help="listar flags")
    flags.add_argument("--status", default="open", choices=("open", "reviewed", "dismissed", "all"))
    flags.add_argument("--limit", type=int, default=50)
    review = sub.add_parser("review", help="mudar o status de uma flag")
    review.add_argument("flag_id", type=UUID)
    review.add_argument("status", choices=("open", "reviewed", "dismissed"))
    review.add_argument("--note")
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
    admin = AccountRiskAdmin(sessions)
    if args.command == "link":
        created = await admin.link(args.first, args.second, note=args.note)
        return ["vínculo criado" if created else "vínculo já existia"]
    if args.command == "unlink":
        removed = await admin.unlink(args.first, args.second)
        return ["vínculo removido" if removed else "vínculo não encontrado"]
    if args.command == "links":
        rows = await admin.links()
        return [f"{a}+{b}" + (f"  {note}" if note else "") for a, b, note in rows] or [
            "nenhum vínculo"
        ]
    if args.command == "flags":
        status = None if args.status == "all" else args.status
        rows = await admin.flags(status=status, limit=args.limit)
        return [_format_flag(row) for row in rows] or ["nenhuma flag"]
    flag = await admin.review(args.flag_id, args.status, note=args.note)
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
