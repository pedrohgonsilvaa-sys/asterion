"""Operator CLI for the Crônica. Never exposed to players.

Usage:
    python -m asterion.chronicle_cli --as <id> status
    python -m asterion.chronicle_cli --as <id> set-day1 2026-12-01 --note "anúncio oficial"
    python -m asterion.chronicle_cli --as <id> extend 2027-01-27T21:00 --note "falha do servidor"
    python -m asterion.chronicle_cli --as <id> pass-grant <telegram_id> --reason "..."
    python -m asterion.chronicle_cli --as <id> maintenance --reason "..."

``--as`` is who is acting; the role check and the audit row live in `AdminService`.
For set-day1 and extend the ``--note`` is also the audit reason.

Times are America/Sao_Paulo. Without a Day 1 nothing of the Crônica opens. Day 1
may change until the Crônica starts; after that only ``extend`` (GDD §5.3) moves
T, before the vote closes, and every change is logged with its note.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.admin_cli import add_actor_argument
from asterion.application.admin import AdminService
from asterion.application.chronicle import ChronicleError
from asterion.config import Settings, get_settings
from asterion.domain.chronicle import TIMEZONE, Calendar


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.chronicle_cli")
    add_actor_argument(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="mostrar o calendário da Crônica")
    day1 = sub.add_parser("set-day1", help="definir ou trocar o Dia 1 antes do início")
    day1.add_argument("day1", type=date.fromisoformat)
    day1.add_argument("--note", required=True)
    extend = sub.add_parser("extend", help="extensão excepcional de T (§5.3)")
    extend.add_argument("end_at", type=datetime.fromisoformat)
    extend.add_argument("--note", required=True)
    grant = sub.add_parser("pass-grant", help="ativar o Passe da Crônica de uma conta")
    grant.add_argument("telegram_id", type=int)
    grant.add_argument("--source", default="manual")
    grant.add_argument("--reason", required=True)
    maintenance = sub.add_parser("maintenance", help="rodar uma vez a manutenção da Crônica")
    maintenance.add_argument("--reason", required=True)
    return parser


def _when(moment: datetime) -> str:
    return moment.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M")


def _print_calendar(calendar: Calendar) -> None:
    print(f"Dia 1 ............ {_when(calendar.starts_at)}")
    for chapter in range(2, 9):
        print(f"Capítulo {chapter} ....... {_when(calendar.chapter_opens_at(chapter))}")
    print(f"Voto abre ........ {_when(calendar.vote_opens_at)}")
    print(f"Voto fecha ....... {_when(calendar.vote_closes_at)}")
    print(f"Runoff fecha ..... {_when(calendar.runoff_closes_at)}")
    print(f"T (fim) .......... {_when(calendar.end_at)}")
    print(f"Finalização ...... {_when(calendar.finalization_at)}")
    print(f"Fim do resgate ... {_when(calendar.rescue_ends_at)}")


async def run(
    args: argparse.Namespace, sessions: async_sessionmaker[AsyncSession], settings: Settings
) -> int:
    admin = AdminService(sessions, settings.server_id)
    actor = args.actor
    if args.command == "status":
        status = await admin.chronicle_status(actor)
        if status is None:
            print("Sem Dia 1 configurado: a Crônica não abre.")
            return 0
        _print_calendar(status.calendar)
        print(f"Fase ............. {status.phase.value}")
        print(f"Desfecho ......... {status.outcome or '—'}")
        if status.runoff_options:
            print(f"Runoff entre ..... {', '.join(status.runoff_options)}")
        return 0
    if args.command == "set-day1":
        _print_calendar(await admin.set_day1(actor, args.day1, reason=args.note))
        return 0
    if args.command == "extend":
        end_at = args.end_at
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=TIMEZONE)
        _print_calendar(await admin.extend_chronicle(actor, end_at, reason=args.note))
        return 0
    if args.command == "pass-grant":
        activated = await admin.grant_pass(
            actor, args.telegram_id, source=args.source, reason=args.reason
        )
        print(f"Passe ativo desde {_when(activated)}.")
        return 0
    await admin.chronicle_maintenance(actor, reason=args.reason)
    print("Manutenção executada.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    async def execute() -> int:
        from asterion.infrastructure.db.session import SessionFactory

        return await run(args, SessionFactory, get_settings())

    try:
        return asyncio.run(execute())
    except (ChronicleError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
