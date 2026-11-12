"""Operator CLI for Códigos de Asterion and content reports. Never exposed to players.

Usage:
    python -m asterion.engagement_cli --as <id> code-create --reason "..." --c 0.25 --basics 2
        --fragments 1 [--code NOME] [--days 30] [--global-limit N] [--uses 1]
        [--scope account|character] [--allow-above-normal] [--table tabela.json] [--note "..."]
    python -m asterion.engagement_cli --as <id> code-list
    python -m asterion.engagement_cli --as <id> code-disable NOME --reason "..."
    python -m asterion.engagement_cli --as <id> code-enable NOME --reason "..."
    python -m asterion.engagement_cli --as <id> reports [--status open|upheld|dismissed|all]
    python -m asterion.engagement_cli --as <id> report-resolve <id> upheld|dismissed --reason "..."

``--as`` is who is acting; the role check and the audit row live in `AdminService`.

Without --code the Code is generated. --table reads a JSON list of
{"weight", "c_multiplier", "basics", "fragments"} for a random prize.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.admin_cli import add_actor_argument
from asterion.application.admin import AdminError, AdminService
from asterion.application.engagement import EngagementError
from asterion.application.social import SocialError
from asterion.config import Settings, get_settings
from asterion.domain.engagement import PromoRewardError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.engagement_cli")
    add_actor_argument(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("code-create", help="criar um Código de Asterion")
    create.add_argument("--code")
    create.add_argument("--c", default="0")
    create.add_argument("--basics", type=int, default=0)
    create.add_argument("--fragments", type=int, default=0)
    create.add_argument("--table", type=Path)
    create.add_argument("--days", type=int)
    create.add_argument("--global-limit", type=int)
    create.add_argument("--uses", type=int, default=1)
    create.add_argument("--scope", choices=("account", "character"), default="account")
    create.add_argument("--allow-above-normal", action="store_true")
    create.add_argument("--note")
    create.add_argument("--reason", required=True)
    sub.add_parser("code-list", help="listar Códigos")
    for name in ("code-disable", "code-enable"):
        toggle = sub.add_parser(name)
        toggle.add_argument("code")
        toggle.add_argument("--reason", required=True)
    reports = sub.add_parser("reports", help="listar denúncias")
    reports.add_argument("--status", default="open")
    resolve = sub.add_parser("report-resolve", help="resolver uma denúncia")
    resolve.add_argument("report_id", type=UUID)
    resolve.add_argument("decision", choices=("upheld", "dismissed"))
    resolve.add_argument("--note")
    resolve.add_argument("--reason", required=True)
    return parser


async def _delete_message(settings: Settings, chat_id: int, message_id: int) -> bool:
    if not settings.telegram_bot_token:
        return False
    bot = Bot(settings.telegram_bot_token)
    try:
        return await bot.delete_message(chat_id, message_id)
    except TelegramAPIError:
        return False
    finally:
        await bot.session.close()


async def run(
    args: argparse.Namespace, sessions: async_sessionmaker[AsyncSession], settings: Settings
) -> int:
    admin = AdminService(sessions, settings.server_id)
    actor = args.actor
    if args.command == "code-create":
        table = (
            json.loads(args.table.read_text(encoding="utf-8"))
            if args.table
            else [
                {
                    "weight": 1,
                    "c_multiplier": args.c,
                    "basics": args.basics,
                    "fragments": args.fragments,
                }
            ]
        )
        now = datetime.now(UTC)
        row = await admin.create_code(
            actor,
            reason=args.reason,
            code=args.code,
            reward_table=table,
            expires_at=now + timedelta(days=args.days) if args.days else None,
            global_limit=args.global_limit,
            uses_per_account=args.uses,
            scope=args.scope,
            allow_above_normal=args.allow_above_normal,
            note=args.note,
            now=now,
        )
        print(f"Código criado: {row.code} (expira em {row.expires_at.isoformat()})")
    elif args.command == "code-list":
        for row in await admin.list_codes(actor):
            print(
                f"{row.code} ativo={row.active} resgates={row.redeemed} "
                f"limite={row.global_limit} expira={row.expires_at.isoformat()}"
            )
    elif args.command in {"code-disable", "code-enable"}:
        await admin.set_code_active(
            actor, args.code, args.command == "code-enable", reason=args.reason
        )
        print("Feito.")
    elif args.command == "reports":
        for report in await admin.list_reports(actor, args.status):
            print(
                json.dumps(
                    {
                        "id": str(report.report_id),
                        "kind": report.kind,
                        "status": report.status,
                        "created_at": report.created_at.isoformat(),
                        "text": report.snapshot,
                    },
                    ensure_ascii=False,
                )
            )
    elif args.command == "report-resolve":
        result = await admin.resolve_report(
            actor,
            args.report_id,
            uphold=args.decision == "upheld",
            reason=args.reason,
            note=args.note,
        )
        print("Texto removido." if result.removed else "Nada foi removido.")
        if result.chat_id is not None and result.message_id is not None:
            deleted = await _delete_message(settings, result.chat_id, result.message_id)
            if not deleted:
                print(f"Apague à mão a mensagem {result.message_id} do tópico Relatos.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    async def execute() -> int:
        from asterion.infrastructure.db.session import SessionFactory

        return await run(args, SessionFactory, get_settings())

    try:
        return asyncio.run(execute())
    except (AdminError, EngagementError, SocialError, PromoRewardError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
