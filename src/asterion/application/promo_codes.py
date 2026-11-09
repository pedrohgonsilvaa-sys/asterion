"""Códigos de Asterion (GDD §32.4, §49.19).

Lock order: PromoCode -> Character. The attempt counter commits in its own
transaction first, because a rejected code rolls its transaction back.

The prize of a random Code is derived from the redemption id and stored with the
redemption in one transaction, so a crash or retry can never draw it again.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.engagement import EngagementError, Granted, grant_bundle
from asterion.domain.engagement import (
    PROMO_ATTEMPTS_PER_HOUR,
    PROMO_ATTEMPTS_PER_MINUTE,
    PROMO_DEFAULT_DURATION,
    PROMO_SCOPES,
    Bundle,
    generate_promo_code,
    normalize_promo_code,
    promo_crowns,
    validate_promo_entry,
)
from asterion.infrastructure.db.models import Character, PromoAttempt, PromoCode, PromoRedemption


@dataclass(frozen=True, slots=True)
class PromoResult:
    code: str
    granted: Granted


@dataclass(frozen=True, slots=True)
class PromoCodeRow:
    code_id: UUID
    code: str
    active: bool
    starts_at: datetime
    expires_at: datetime
    global_limit: int | None
    uses_per_account: int
    scope: str
    redeemed: int
    reward_table: list[dict[str, Any]]


class PromoCodeService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    async def redeem(
        self, actor: int, raw_code: str, *, now: datetime | None = None
    ) -> PromoResult:
        now = now or datetime.now(UTC)
        await self._count_attempt(actor, now)
        code_text = normalize_promo_code(raw_code)
        if code_text is None:
            raise EngagementError("promo_invalid")
        async with self.sessions.begin() as session:
            code = await session.scalar(
                select(PromoCode)
                .where(PromoCode.server_id == self.server_id, PromoCode.code == code_text)
                .with_for_update()
            )
            if code is None or not code.active or now < code.starts_at:
                raise EngagementError("promo_invalid")
            if now >= code.expires_at:
                raise EngagementError("promo_expired")
            character = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if character is None:
                raise EngagementError("no_character")
            if code.global_limit is not None and code.redeemed_count >= code.global_limit:
                raise EngagementError("promo_exhausted")
            owner = (
                PromoRedemption.character_id == character.id
                if code.scope == "character"
                else PromoRedemption.telegram_id == actor
            )
            used = await session.scalar(
                select(func.count(PromoRedemption.id)).where(
                    PromoRedemption.code_id == code.id, owner
                )
            )
            if int(used or 0) >= code.uses_per_account:
                raise EngagementError("promo_already_redeemed")
            redemption_id = uuid4()
            index = _draw(code.reward_table, redemption_id)
            entry = code.reward_table[index]
            bundle = Bundle(
                crowns=promo_crowns(entry["c_multiplier"], character.level),
                basics=int(entry["basics"]),
                fragments=int(entry["fragments"]),
            )
            session.add(
                PromoRedemption(
                    id=redemption_id,
                    code_id=code.id,
                    telegram_id=actor,
                    character_id=character.id,
                    entry_index=index,
                    crowns=bundle.crowns,
                    basics=bundle.basics,
                    fragments=bundle.fragments,
                    redeemed_at=now,
                )
            )
            code.redeemed_count += 1
            granted = await grant_bundle(
                session, character, bundle, f"benefit:code:{redemption_id.hex}"
            )
            return PromoResult(code.code, granted)

    async def _count_attempt(self, actor: int, now: datetime) -> None:
        async with self.sessions.begin() as session:
            exists = await session.scalar(
                select(Character.id)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if exists is None:
                raise EngagementError("no_character")
            hour_ago = now - timedelta(hours=1)
            await session.execute(
                delete(PromoAttempt).where(
                    PromoAttempt.telegram_id == actor,
                    PromoAttempt.server_id == self.server_id,
                    PromoAttempt.attempted_at <= hour_ago,
                )
            )
            attempts = (
                await session.scalars(
                    select(PromoAttempt.attempted_at).where(
                        PromoAttempt.telegram_id == actor,
                        PromoAttempt.server_id == self.server_id,
                    )
                )
            ).all()
            minute_ago = now - timedelta(minutes=1)
            if (
                len(attempts) >= PROMO_ATTEMPTS_PER_HOUR
                or sum(item > minute_ago for item in attempts) >= PROMO_ATTEMPTS_PER_MINUTE
            ):
                raise EngagementError("promo_rate_limited")
            session.add(PromoAttempt(telegram_id=actor, server_id=self.server_id, attempted_at=now))


class PromoCodeAdmin:
    """Operator-only management; players can only redeem."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id

    async def create(
        self,
        *,
        code: str | None,
        reward_table: Sequence[dict[str, object]],
        starts_at: datetime | None = None,
        expires_at: datetime | None = None,
        global_limit: int | None = None,
        uses_per_account: int = 1,
        scope: str = "account",
        allow_above_normal: bool = False,
        note: str | None = None,
        now: datetime | None = None,
    ) -> PromoCodeRow:
        now = now or datetime.now(UTC)
        text = generate_promo_code() if code is None else normalize_promo_code(code)
        if text is None:
            raise EngagementError("promo_format")
        if scope not in PROMO_SCOPES:
            raise EngagementError("promo_scope")
        if not reward_table:
            raise EngagementError("reward_empty")
        table = [
            validate_promo_entry(dict(entry), allow_above_normal=allow_above_normal)
            for entry in reward_table
        ]
        begins = starts_at or now
        row = PromoCode(
            id=uuid4(),
            server_id=self.server_id,
            code=text,
            active=True,
            starts_at=begins,
            expires_at=expires_at or begins + PROMO_DEFAULT_DURATION,
            global_limit=global_limit,
            uses_per_account=uses_per_account,
            scope=scope,
            reward_table=table,
            redeemed_count=0,
            note=note,
            created_at=now,
        )
        try:
            async with self.sessions.begin() as session:
                session.add(row)
                await session.flush()
                return _row_view(row)
        except IntegrityError as exc:
            raise EngagementError("promo_duplicate_or_invalid") from exc

    async def list_codes(self, limit: int = 50) -> tuple[PromoCodeRow, ...]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(PromoCode)
                    .where(PromoCode.server_id == self.server_id)
                    .order_by(PromoCode.created_at.desc())
                    .limit(limit)
                )
            ).all()
            return tuple(_row_view(row) for row in rows)

    async def set_active(self, raw_code: str, active: bool) -> None:
        text = normalize_promo_code(raw_code)
        async with self.sessions.begin() as session:
            row = await session.scalar(
                select(PromoCode)
                .where(PromoCode.server_id == self.server_id, PromoCode.code == text)
                .with_for_update()
            )
            if row is None:
                raise EngagementError("promo_invalid")
            row.active = active


def _draw(table: list[dict[str, Any]], redemption_id: UUID) -> int:
    weights = [int(entry["weight"]) for entry in table]
    return random.Random(redemption_id.int).choices(range(len(table)), weights=weights)[0]


def _row_view(row: PromoCode) -> PromoCodeRow:
    return PromoCodeRow(
        row.id,
        row.code,
        row.active,
        row.starts_at,
        row.expires_at,
        row.global_limit,
        row.uses_per_account,
        row.scope,
        row.redeemed_count,
        row.reward_table,
    )
