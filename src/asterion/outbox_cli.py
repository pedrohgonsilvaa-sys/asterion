"""Operator CLI for the Outbox (GDD §43.5). Never exposed to players.

Usage:
    python -m asterion.outbox_cli stats
    python -m asterion.outbox_cli requeue [--id <uuid> ...]   # dead -> pending
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from uuid import UUID

from asterion.application.outbox import outbox_stats, requeue_dead
from asterion.infrastructure.db.session import SessionFactory


async def run(argv: Sequence[str], sessions=SessionFactory) -> int:
    parser = argparse.ArgumentParser(prog="asterion.outbox_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="contagem por status e idade da fila")
    requeue = sub.add_parser("requeue", help="devolver mensagens dead para pending")
    requeue.add_argument("--id", dest="ids", type=UUID, action="append")
    args = parser.parse_args(argv)
    if args.command == "stats":
        stats = await outbox_stats(sessions)
        for status, n in stats.counts.items():
            print(f"{status:<11}{n}")
        age = stats.oldest_open_age_seconds
        print("mais antiga aberta: " + ("-" if age is None else f"{age:.0f}s"))
        return 0
    print(f"{await requeue_dead(sessions, args.ids)} mensagem(ns) devolvida(s) para pending")
    return 0


def main() -> None:
    sys.exit(asyncio.run(run(sys.argv[1:])))


if __name__ == "__main__":
    main()
