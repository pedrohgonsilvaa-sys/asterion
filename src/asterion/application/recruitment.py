"""Chamado de Asterion (GDD §32.2, §49.19).

Everything is keyed by account and server, so deleting a character neither frees a
new link nor repeats a payment. Each account has one character per server.

A pair of admin-linked accounts is flagged for review and still paid: §32.2 says
detection produces analysis, and the author asked for marking without blocking.

Lock order: Characters in ascending id order. A payout locks only the claimant, so
the choice of the recruiter's first 10 paying recruits is serialised by that lock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.application.engagement import EngagementError
from asterion.domain.engagement import (
    RECRUIT_LINK_WINDOW,
    RECRUIT_MAX_LEVEL_EXCLUSIVE,
    RECRUIT_MILESTONES,
    RECRUIT_PRESTIGE,
    RECRUITER_MIN_LEVEL,
    RECRUITER_PAID_RECRUITS,
    generate_recruit_code,
    normalize_recruit_code,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterCosmetic,
    RecruitmentClaim,
    RecruitmentCode,
    RecruitmentInvite,
    RecruitmentLink,
)

_CODE_ATTEMPTS = 8
_PRESTIGE_SOURCE = "chamado_de_asterion"


@dataclass(frozen=True, slots=True)
class RecruitmentView:
    code: str
    recruits: int
    recruits_at: dict[int, int]
    claimable_crowns: int
    is_recruit: bool
    can_link: bool
    recruiter_eligible: bool
    prestige: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecruitmentPayout:
    crowns: int


class RecruitmentService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int, *, now: datetime | None = None) -> RecruitmentView:
        now = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            code = await self._ensure_code(session, actor, now)
            await self._refresh_recruiter(session, actor)
            prestige = await self._grant_prestige(session, character, actor, now)
            link = await session.get(RecruitmentLink, (actor, self.server_id))
            own_due = await self._due_as_recruit(session, actor, character, link)
            paying_due = await self._due_as_recruiter(session, actor)
            links = await self._links_of(session, actor)
            return RecruitmentView(
                code=code,
                recruits=len(links),
                recruits_at={
                    milestone: sum(row.peak_level >= milestone for row in links)
                    for milestone in RECRUIT_MILESTONES
                },
                claimable_crowns=sum(RECRUIT_MILESTONES[m] for m in own_due)
                + sum(RECRUIT_MILESTONES[m] for _, m in paying_due),
                is_recruit=link is not None,
                can_link=link is None and _within_window(character, now),
                recruiter_eligible=character.level >= RECRUITER_MIN_LEVEL,
                prestige=prestige,
            )

    async def open_invite(self, actor: int, raw_code: str, *, now: datetime | None = None) -> bool:
        """A Chamado deep link. Returns False when it was stored for after creation."""
        now = now or datetime.now(UTC)
        code = normalize_recruit_code(raw_code)
        if code is None:
            raise EngagementError("recruit_code_invalid")
        async with self.sessions.begin() as session:
            await session.execute(
                insert(Account).values(telegram_id=actor).on_conflict_do_nothing()
            )
            character = await session.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if character is None:
                statement = insert(RecruitmentInvite).values(
                    telegram_id=actor, server_id=self.server_id, code=code, created_at=now
                )
                await session.execute(
                    statement.on_conflict_do_update(
                        index_elements=[RecruitmentInvite.telegram_id, RecruitmentInvite.server_id],
                        set_={"code": code, "created_at": now},
                    )
                )
                return False
        await self.link(actor, code, now=now)
        return True

    async def link(self, actor: int, raw_code: str, *, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        code = normalize_recruit_code(raw_code)
        if code is None:
            raise EngagementError("recruit_code_invalid")
        async with self.sessions.begin() as session:
            recruiter_account = await session.scalar(
                select(RecruitmentCode.telegram_id).where(
                    RecruitmentCode.server_id == self.server_id, RecruitmentCode.code == code
                )
            )
            if recruiter_account is None:
                raise EngagementError("recruit_code_invalid")
            if recruiter_account == actor:
                raise EngagementError("recruit_self")
            rows = (
                await session.scalars(
                    select(Character)
                    .where(
                        Character.server_id == self.server_id,
                        Character.telegram_id.in_({actor, recruiter_account}),
                    )
                    .order_by(Character.id)
                    .with_for_update()
                )
            ).all()
            by_account = {row.telegram_id: row for row in rows}
            character, recruiter = by_account.get(actor), by_account.get(recruiter_account)
            if character is None:
                raise EngagementError("no_character")
            if await session.get(RecruitmentLink, (actor, self.server_id)) is not None:
                raise EngagementError("recruit_already_linked")
            if not _within_window(character, now):
                raise EngagementError("recruit_window_closed")
            if recruiter is None or recruiter.level < RECRUITER_MIN_LEVEL:
                raise EngagementError("recruiter_ineligible")
            await self._write_link(session, character, recruiter, now)

    async def claim(self, actor: int, *, now: datetime | None = None) -> RecruitmentPayout:
        now = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            await self._refresh_recruiter(session, actor)
            link = await session.get(RecruitmentLink, (actor, self.server_id))
            total = 0
            for milestone in await self._due_as_recruit(session, actor, character, link):
                total += self._pay(session, actor, milestone, "recruit", character, now)
            for recruit, milestone in await self._due_as_recruiter(session, actor):
                total += self._pay(session, recruit, milestone, "recruiter", character, now)
            await self._grant_prestige(session, character, actor, now)
            if total == 0:
                raise EngagementError("nothing_to_claim")
            character.crowns += total
            return RecruitmentPayout(total)

    def _pay(self, session, recruit: int, milestone: int, side: str, character, now) -> int:
        crowns = RECRUIT_MILESTONES[milestone]
        session.add(
            RecruitmentClaim(
                recruit_telegram_id=recruit,
                server_id=self.server_id,
                milestone=milestone,
                side=side,
                character_id=character.id,
                crowns=crowns,
                claimed_at=now,
            )
        )
        return crowns

    async def _write_link(self, session, character, recruiter, now) -> None:
        session.add(
            RecruitmentLink(
                recruit_telegram_id=character.telegram_id,
                server_id=self.server_id,
                recruiter_telegram_id=recruiter.telegram_id,
                peak_level=character.level,
                pays_recruiter=False,
                linked_at=now,
            )
        )
        await session.flush()
        await record_linked_cooccurrence(
            session,
            server_id=self.server_id,
            activity_kind="recruitment",
            activity_reference=f"recruit:{character.telegram_id}",
            characters=[character, recruiter],
            now=now,
        )

    async def _ensure_code(self, session, actor: int, now: datetime) -> str:
        existing = await session.get(RecruitmentCode, (actor, self.server_id))
        if existing is not None:
            return existing.code
        for _ in range(_CODE_ATTEMPTS):
            code = generate_recruit_code()
            created = await session.scalar(
                insert(RecruitmentCode)
                .values(telegram_id=actor, server_id=self.server_id, code=code, created_at=now)
                .on_conflict_do_nothing()
                .returning(RecruitmentCode.code)
            )
            if created is not None:
                return created
        raise EngagementError("recruit_code_unavailable")

    async def _links_of(self, session, recruiter: int) -> list[RecruitmentLink]:
        return list(
            (
                await session.scalars(
                    select(RecruitmentLink)
                    .where(
                        RecruitmentLink.server_id == self.server_id,
                        RecruitmentLink.recruiter_telegram_id == recruiter,
                    )
                    .order_by(RecruitmentLink.linked_at, RecruitmentLink.recruit_telegram_id)
                )
            ).all()
        )

    async def _refresh_recruiter(self, session, recruiter: int) -> None:
        """Keep each recruit's peak level, then fill the 10 paid places (§49.19)."""
        links = await self._links_of(session, recruiter)
        if not links:
            return
        levels = dict(
            (
                await session.execute(
                    select(Character.telegram_id, Character.level).where(
                        Character.server_id == self.server_id,
                        Character.telegram_id.in_([row.recruit_telegram_id for row in links]),
                    )
                )
            ).all()
        )
        paying = sum(row.pays_recruiter for row in links)
        first_milestone = min(RECRUIT_MILESTONES)
        for row in links:
            row.peak_level = max(row.peak_level, levels.get(row.recruit_telegram_id, 0))
            if (
                not row.pays_recruiter
                and row.peak_level >= first_milestone
                and paying < RECRUITER_PAID_RECRUITS
            ):
                row.pays_recruiter = True
                paying += 1
        await session.flush()

    async def _claimed(self, session, recruit: int, side: str) -> set[int]:
        return set(
            (
                await session.scalars(
                    select(RecruitmentClaim.milestone).where(
                        RecruitmentClaim.recruit_telegram_id == recruit,
                        RecruitmentClaim.server_id == self.server_id,
                        RecruitmentClaim.side == side,
                    )
                )
            ).all()
        )

    async def _due_as_recruit(self, session, actor, character, link) -> list[int]:
        if link is None:
            return []
        link.peak_level = max(link.peak_level, character.level)
        claimed = await self._claimed(session, actor, "recruit")
        return [m for m in RECRUIT_MILESTONES if link.peak_level >= m and m not in claimed]

    async def _due_as_recruiter(self, session, recruiter: int) -> list[tuple[int, int]]:
        due: list[tuple[int, int]] = []
        for row in await self._links_of(session, recruiter):
            if not row.pays_recruiter:
                continue
            claimed = await self._claimed(session, row.recruit_telegram_id, "recruiter")
            due.extend(
                (row.recruit_telegram_id, m)
                for m in RECRUIT_MILESTONES
                if row.peak_level >= m and m not in claimed
            )
        return due

    async def _grant_prestige(self, session, character, actor, now) -> tuple[str, ...]:
        links = await self._links_of(session, actor)
        names = []
        for prestige in RECRUIT_PRESTIGE:
            if sum(row.peak_level >= prestige.milestone for row in links) < prestige.recruits:
                continue
            definition = COSMETICS_BY_ID[prestige.cosmetic_id]
            await session.execute(
                insert(CharacterCosmetic)
                .values(
                    character_id=character.id,
                    cosmetic_id=definition.cosmetic_id,
                    cosmetic_type=definition.cosmetic_type,
                    source_achievement_id=_PRESTIGE_SOURCE,
                    acquired_at=now,
                )
                .on_conflict_do_nothing()
            )
            names.append(definition.name)
        return tuple(names)

    async def _character(self, session, actor: int, *, lock: bool = False) -> Character:
        statement = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        character = await session.scalar(statement.with_for_update() if lock else statement)
        if character is None:
            raise EngagementError("no_character")
        return character


async def link_pending_invite(
    session: AsyncSession, telegram_id: int, server_id: str, character_id, now: datetime
) -> None:
    """Consume a Chamado link opened before creation, in the creation transaction.

    An invalid invite is simply dropped: it must never stop a character from being
    created. The recruiter's level only grows, so reading it needs no lock.
    """
    invite = await session.get(RecruitmentInvite, (telegram_id, server_id))
    if invite is None:
        return
    await session.delete(invite)
    recruiter_account = await session.scalar(
        select(RecruitmentCode.telegram_id).where(
            RecruitmentCode.server_id == server_id, RecruitmentCode.code == invite.code
        )
    )
    if recruiter_account is None or recruiter_account == telegram_id:
        return
    if await session.get(RecruitmentLink, (telegram_id, server_id)) is not None:
        return
    character = await session.get(Character, character_id)
    recruiter = await session.scalar(
        select(Character).where(
            Character.telegram_id == recruiter_account, Character.server_id == server_id
        )
    )
    if character is None or recruiter is None or recruiter.level < RECRUITER_MIN_LEVEL:
        return
    session.add(
        RecruitmentLink(
            recruit_telegram_id=telegram_id,
            server_id=server_id,
            recruiter_telegram_id=recruiter_account,
            peak_level=max(1, int(character.level or 1)),
            pays_recruiter=False,
            linked_at=now,
        )
    )
    await session.flush()
    await record_linked_cooccurrence(
        session,
        server_id=server_id,
        activity_kind="recruitment",
        activity_reference=f"recruit:{telegram_id}",
        characters=[character, recruiter],
        now=now,
    )


def _within_window(character: Character, now: datetime) -> bool:
    if character.created_at is None or character.level >= RECRUIT_MAX_LEVEL_EXCLUSIVE:
        return False
    return now <= character.created_at + RECRUIT_LINK_WINDOW
