"""Operator CLI for account suspensions. Never exposed to players.

Usage:
    python -m asterion.admin_cli suspend <telegram_id> --reason "motivo" [--hours 72] [--by nome]
    python -m asterion.admin_cli lift <telegram_id> [--by nome]
    python -m asterion.admin_cli list
    python -m asterion.admin_cli history <telegram_id>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.sanctions import SanctionService, SanctionView


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.admin_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    suspend = sub.add_parser("suspend", help="suspender uma conta")
    suspend.add_argument("telegram_id", type=int)
    suspend.add_argument("--reason", required=True)
    suspend.add_argument("--hours", type=int, help="sem isso, a suspensão não expira")
    suspend.add_argument("--by", default="operador")
    lift = sub.add_parser("lift", help="encerrar as suspensões ativas de uma conta")
    lift.add_argument("telegram_id", type=int)
    lift.add_argument("--by", default="operador")
    sub.add_parser("list", help="listar suspensões ativas")
    history = sub.add_parser("history", help="histórico de uma conta")
    history.add_argument("telegram_id", type=int)
    return parser


def _line(row: SanctionView) -> str:
    until = f"{row.expires_at:%Y-%m-%d %H:%M}" if row.expires_at else "sem fim"
    state = f"encerrada {row.revoked_at:%Y-%m-%d %H:%M}" if row.revoked_at else "ativa"
    return (
        f"{row.telegram_id}  {state}  desde {row.created_at:%Y-%m-%d %H:%M}  até {until}  "
        f"por {row.created_by}  motivo={row.reason!r}"
    )


async def run(argv: Sequence[str], sessions: async_sessionmaker[AsyncSession]) -> list[str]:
    args = _parser().parse_args(argv)
    service = SanctionService(sessions)
    if args.command == "suspend":
        row = await service.suspend(
            args.telegram_id, reason=args.reason, by=args.by, hours=args.hours
        )
        return [_line(row)]
    if args.command == "lift":
        count = await service.lift(args.telegram_id, by=args.by)
        return [f"{count} suspensão(ões) encerrada(s)"]
    if args.command == "list":
        return [_line(r) for r in await service.active()] or ["nenhuma suspensão ativa"]
    return [_line(r) for r in await service.history(args.telegram_id)] or ["sem histórico"]


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
