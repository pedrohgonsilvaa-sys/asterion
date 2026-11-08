"""Operator CLI for Códigos de Asterion and content reports. Never exposed to players.

Usage:
    python -m asterion.engagement_cli code-create --c 0.25 --basics 2 --fragments 1 [--code NOME]
        [--days 30] [--global-limit N] [--uses 1] [--scope account|character]
        [--allow-above-normal] [--table tabela.json] [--note "..."]
    python -m asterion.engagement_cli code-list
    python -m asterion.engagement_cli code-disable NOME
    python -m asterion.engagement_cli code-enable NOME
    python -m asterion.engagement_cli reports [--status open|upheld|dismissed|all]
    python -m asterion.engagement_cli report-resolve <id> upheld|dismissed [--note "..."]

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

from asterion.application.engagement import EngagementError
from asterion.application.promo_codes import PromoCodeAdmin
from asterion.application.social import ContentModerationAdmin, SocialError
from asterion.config import Settings, get_settings
from asterion.domain.engagement import PromoRewardError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.engagement_cli")
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
    sub.add_parser("code-list", help="listar Códigos")
    for name in ("code-disable", "code-enable"):
        sub.add_parser(name).add_argument("code")
    reports = sub.add_parser("reports", help="listar denúncias")
    reports.add_argument("--status", default="open")
    resolve = sub.add_parser("report-resolve", help="resolver uma denúncia")
    resolve.add_argument("report_id", type=UUID)
    resolve.add_argument("decision", choices=("upheld", "dismissed"))
    resolve.add_argument("--note")
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
    codes = PromoCodeAdmin(sessions, settings.server_id)
    moderation = ContentModerationAdmin(sessions)
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
        row = await codes.create(
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
        for row in await codes.list_codes():
            print(
                f"{row.code} ativo={row.active} resgates={row.redeemed} "
                f"limite={row.global_limit} expira={row.expires_at.isoformat()}"
            )
    elif args.command in {"code-disable", "code-enable"}:
        await codes.set_active(args.code, args.command == "code-enable")
        print("Feito.")
    elif args.command == "reports":
        for report in await moderation.list_reports(args.status):
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
        result = await moderation.resolve(
            args.report_id, uphold=args.decision == "upheld", note=args.note
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
    except (EngagementError, SocialError, PromoRewardError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
