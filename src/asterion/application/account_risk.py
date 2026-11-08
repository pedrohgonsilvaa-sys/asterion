"""Multi-account review signals (GDD §36).

Owning several Telegram accounts is allowed; using them *together* in the same
shared activity is not. Association alone never proves guilt, so this module
only records review items. It never blocks, punishes or bans anything.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.infrastructure.db.models import AccountLink, AccountRiskFlag, Character

ActivityKind = Literal[
    "group_activity",
    "dungeon_run",
    "guild_project",
    "market_purchase",
    "direct_trade",
    "arena_match",
    "duel",
]
FlagStatus = Literal["open", "reviewed", "dismissed"]
FLAG_STATUSES: frozenset[str] = frozenset({"open", "reviewed", "dismissed"})


def _pair(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


async def record_linked_cooccurrence(
    session: AsyncSession,
    *,
    server_id: str,
    activity_kind: ActivityKind,
    activity_reference: str,
    characters: Iterable[Character],
    now: datetime | None = None,
) -> int:
    """Flag every admin-linked account pair present in one shared activity.

    Runs inside the caller's transaction. Idempotent per activity and pair.
    Returns how many new flags were written.
    """
    by_account: dict[int, list[str]] = {}
    for character in characters:
        by_account.setdefault(character.telegram_id, []).append(str(character.id))
    if len(by_account) < 2:
        return 0
    pairs = sorted({_pair(a, b) for a, b in combinations(by_account, 2)})
    linked = (
        await session.execute(
            select(AccountLink.account_a, AccountLink.account_b).where(
                tuple_(AccountLink.account_a, AccountLink.account_b).in_(pairs)
            )
        )
    ).all()
    if not linked:
        return 0
    created_at = now or datetime.now(UTC)
    rows = [
        {
            "account_a": a,
            "account_b": b,
            "server_id": server_id,
            "activity_kind": activity_kind,
            "activity_reference": activity_reference,
            "evidence": {
                "characters": {str(a): by_account[a], str(b): by_account[b]},
                "participant_accounts": len(by_account),
            },
            "status": "open",
            "created_at": created_at,
        }
        for a, b in sorted(linked)
    ]
    result = await session.execute(
        insert(AccountRiskFlag)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_account_risk_flag_activity_pair")
        .returning(AccountRiskFlag.id)
    )
    return len(result.all())


@dataclass(frozen=True, slots=True)
class FlagView:
    id: UUID
    account_a: int
    account_b: int
    server_id: str
    activity_kind: str
    activity_reference: str
    evidence: dict
    status: str
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class AccountRiskAdmin:
    """Operator-only maintenance of links and review of flags (no player surface)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def link(self, first: int, second: int, *, note: str | None = None) -> bool:
        if first == second:
            raise ValueError("an account cannot be linked to itself")
        a, b = _pair(first, second)
        async with self.sessions.begin() as session:
            result = await session.execute(
                insert(AccountLink)
                .values(account_a=a, account_b=b, note=note)
                .on_conflict_do_nothing(index_elements=["account_a", "account_b"])
                .returning(AccountLink.account_a)
            )
            return result.first() is not None

    async def unlink(self, first: int, second: int) -> bool:
        a, b = _pair(first, second)
        async with self.sessions.begin() as session:
            result = await session.execute(
                delete(AccountLink)
                .where(AccountLink.account_a == a, AccountLink.account_b == b)
                .returning(AccountLink.account_a)
            )
            return result.first() is not None

    async def links(self) -> list[tuple[int, int, str | None]]:
        async with self.sessions() as session:
            rows = await session.execute(
                select(AccountLink.account_a, AccountLink.account_b, AccountLink.note).order_by(
                    AccountLink.account_a, AccountLink.account_b
                )
            )
            return [tuple(row) for row in rows.all()]

    async def flags(self, *, status: str | None = "open", limit: int = 50) -> list[FlagView]:
        if status is not None and status not in FLAG_STATUSES:
            raise ValueError(f"unknown status: {status}")
        query = select(AccountRiskFlag).order_by(AccountRiskFlag.created_at, AccountRiskFlag.id)
        if status is not None:
            query = query.where(AccountRiskFlag.status == status)
        async with self.sessions() as session:
            rows = (await session.scalars(query.limit(limit))).all()
            return [_view(row) for row in rows]

    async def review(
        self,
        flag_id: UUID,
        status: FlagStatus,
        *,
        note: str | None = None,
        now: datetime | None = None,
    ) -> FlagView | None:
        if status not in FLAG_STATUSES:
            raise ValueError(f"unknown status: {status}")
        async with self.sessions.begin() as session:
            row = await session.get(AccountRiskFlag, flag_id, with_for_update=True)
            if row is None:
                return None
            row.status = status
            row.review_note = note
            row.reviewed_at = None if status == "open" else (now or datetime.now(UTC))
            await session.flush()
            return _view(row)


def _view(row: AccountRiskFlag) -> FlagView:
    return FlagView(
        id=row.id,
        account_a=row.account_a,
        account_b=row.account_b,
        server_id=row.server_id,
        activity_kind=row.activity_kind,
        activity_reference=row.activity_reference,
        evidence=dict(row.evidence or {}),
        status=row.status,
        review_note=row.review_note,
        created_at=row.created_at,
        reviewed_at=row.reviewed_at,
    )
