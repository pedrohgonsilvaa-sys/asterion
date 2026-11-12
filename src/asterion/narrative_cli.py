"""Operator CLI to audit one character's narrative choices. Never exposed to players.

Usage:
    python -m asterion.narrative_cli --as <id> audit <character_id>

Prints ``choice_id → option → memories → future_hooks`` (Ação × Consequência §6.1).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.admin_cli import add_actor_argument
from asterion.application.admin import AdminError, AdminService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.narrative_cli")
    add_actor_argument(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="cadeia de escolhas de um personagem")
    audit.add_argument("character_id", type=UUID)
    return parser


def format_chain(chain: list[dict]) -> list[str]:
    lines = []
    for item in chain:
        npc = ", ".join(f"{m['npc_id']}:{m['tag']}({m['knowledge']})" for m in item["npc_memories"])
        lines.append(
            f"{item['choice_id']} [{item['mission_id']}] → {item['selected_option']}"
            f" ({item['source']}, {item['committed_at']})"
        )
        lines.append(f"    personagem: {', '.join(item['character_memories']) or '—'}")
        lines.append(f"    NPC: {npc or '—'}")
        lines.append(f"    ganchos: {', '.join(item['future_hooks']) or '—'}")
        if item["identity_conditions"]:
            lines.append(f"    identidade: {', '.join(item['identity_conditions'])}")
    return lines or ["nenhuma escolha registrada"]


async def run(argv: Sequence[str], sessions: async_sessionmaker[AsyncSession]) -> list[str]:
    args = _parser().parse_args(argv)
    try:
        chain = await AdminService(sessions).narrative_audit(args.actor, args.character_id)
    except AdminError as exc:
        return [f"erro: {exc}"]
    return format_chain(chain)


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
