"""Operator CLI for the Outbox (GDD §43.5). Never exposed to players.

Usage:
    python -m asterion.outbox_cli --as <id> stats
    python -m asterion.outbox_cli --as <id> requeue --reason "..." [--id <uuid> ...]

``--as`` is who is acting; the role check and the audit row live in `AdminService`.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from uuid import UUID

from asterion.admin_cli import add_actor_argument
from asterion.application.admin import AdminError, AdminService
from asterion.infrastructure.db.session import SessionFactory


async def run(argv: Sequence[str], sessions=SessionFactory) -> int:
    parser = argparse.ArgumentParser(prog="asterion.outbox_cli")
    add_actor_argument(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="contagem por status e idade da fila")
    requeue = sub.add_parser("requeue", help="devolver mensagens dead para pending")
    requeue.add_argument("--id", dest="ids", type=UUID, action="append")
    requeue.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    admin = AdminService(sessions)
    try:
        if args.command == "stats":
            stats = await admin.outbox_stats(args.actor)
            for status, n in stats.counts.items():
                print(f"{status:<11}{n}")
            age = stats.oldest_open_age_seconds
            print("mais antiga aberta: " + ("-" if age is None else f"{age:.0f}s"))
            return 0
        count = await admin.requeue_outbox(args.actor, args.ids, reason=args.reason)
    except AdminError as exc:
        print(f"erro: {exc}")
        return 1
    print(f"{count} mensagem(ns) devolvida(s) para pending")
    return 0


def main() -> None:
    sys.exit(asyncio.run(run(sys.argv[1:])))


if __name__ == "__main__":
    main()
