"""Vínculos: friends, blocks, Recentes, public profile and Relatos.

Sources: GDD Estrutural v1.6.0 §31, §31.1 and §49.18.

Lock order (every write follows it, which rules out deadlocks):
Characters in ascending id order -> FriendRequest. The limits are counted after
those locks, so two concurrent requests cannot exceed them.

Telegram IDs never leave this module. Views carry the immutable character id.

Author decisions (2026-11-08) for points the GDD leaves open: Recentes come from
Grupo, Masmorra, Arena/Duelo and Troca Direta (see social_graph); a block also
stops Duel challenges; links and @mentions are refused when saving a História;
reports go to an operator queue. Directed LFG does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.application.social_graph import blocked_between
from asterion.domain.arena import PLACEMENT_MATCHES, elo_for
from asterion.domain.social import (
    MAX_BLOCKED,
    MAX_FRIENDS,
    MAX_RECEIVED_REQUESTS,
    MAX_RECENTS,
    MAX_SENT_REQUESTS,
    MAX_STORY_CHARACTERS,
    PAGE_SIZE,
    RECENT_WINDOW,
    SEARCH_LIMIT_PER_MINUTE,
    SEARCH_MIN_CHARACTERS,
    SEARCH_RESULT_LIMIT,
    SEARCH_WINDOW,
    STORY_SHARE_COOLDOWN,
    escape_like,
    story_is_allowed,
)
from asterion.infrastructure.db.models import (
    Achievement,
    ArenaProfile,
    Character,
    CharacterBlock,
    CharacterCosmeticSelection,
    CharacterProfile,
    ContentReport,
    FriendRequest,
    Friendship,
    Guild,
    GuildInvite,
    GuildMember,
    PlayerSearchAttempt,
    RecentContact,
    Relato,
    SocialGroupInvite,
)


class SocialError(ValueError):
    """A Vínculos action is invalid for the current, revalidated state."""

    def __init__(self, code: str, available_at: datetime | None = None):
        self.code = code
        self.available_at = available_at
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PlayerCard:
    character_id: UUID
    name: str
    level: int
    character_class: str


@dataclass(frozen=True, slots=True)
class CardPage:
    cards: tuple[PlayerCard, ...]
    page: int
    total: int


@dataclass(frozen=True, slots=True)
class RequestView:
    request_id: UUID
    card: PlayerCard


@dataclass(frozen=True, slots=True)
class RequestsView:
    incoming: tuple[RequestView, ...]
    outgoing: tuple[RequestView, ...]


@dataclass(frozen=True, slots=True)
class PublicProfile:
    character_id: UUID
    name: str
    level: int
    legacy_level: int
    race: str
    character_class: str
    selected_path: str | None
    guild: str | None
    title: str | None
    elo: str | None
    feats: int
    history: str | None
    is_self: bool
    is_friend: bool
    blocked_by_me: bool
    blocked_me: bool
    outgoing_request_id: UUID | None
    incoming_request_id: UUID | None


@dataclass(frozen=True, slots=True)
class RelatoView:
    relato_id: UUID
    character_id: UUID
    author_name: str
    body: str


@dataclass(frozen=True, slots=True)
class ReportView:
    report_id: UUID
    kind: str
    target_key: str
    snapshot: str
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReportResolution:
    """Where the published Relato lives, so the operator tool can delete the message."""

    removed: bool
    chat_id: int | None
    message_id: int | None


class SocialService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    # ----------------------------------------------------------------- search

    async def search(
        self, actor: int, query: str, *, now: datetime | None = None
    ) -> tuple[PlayerCard, ...]:
        now = _utcnow(now)
        name = query.strip()
        if len(name) < SEARCH_MIN_CHARACTERS or len(name) > 16:
            raise SocialError("query_invalid")
        async with self.sessions.begin() as session:
            character = await self._actor(session, actor, lock=True)
            await session.execute(
                delete(PlayerSearchAttempt).where(
                    PlayerSearchAttempt.character_id == character.id,
                    PlayerSearchAttempt.attempted_at <= now - SEARCH_WINDOW,
                )
            )
            used = await session.scalar(
                select(func.count(PlayerSearchAttempt.id)).where(
                    PlayerSearchAttempt.character_id == character.id
                )
            )
            if int(used or 0) >= SEARCH_LIMIT_PER_MINUTE:
                raise SocialError("search_rate_limited")
            session.add(PlayerSearchAttempt(character_id=character.id, attempted_at=now))
            rows = (
                await session.scalars(
                    select(Character)
                    .where(
                        Character.server_id == self.server_id,
                        Character.id != character.id,
                        func.lower(Character.name).like(
                            f"{escape_like(name.casefold())}%", escape="\\"
                        ),
                    )
                    .order_by(func.lower(Character.name))
                    .limit(SEARCH_RESULT_LIMIT)
                )
            ).all()
            return tuple(_card(row) for row in rows)

    # ---------------------------------------------------------------- friends

    async def send_request(
        self, actor: int, target_id: UUID, *, now: datetime | None = None
    ) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            actor_id, target = await self._lock_pair(session, actor, target_id)
            if target.id == actor_id:
                raise SocialError("self")
            if await blocked_between(session, actor_id, target.id):
                raise SocialError("unavailable")
            if await self._friendship(session, actor_id, target.id) is not None:
                raise SocialError("already_friends")
            if await self._request_between(session, target.id, actor_id) is not None:
                raise SocialError("incoming_pending")
            if await self._request_between(session, actor_id, target.id) is not None:
                return
            if await self._friend_count(session, actor_id) >= MAX_FRIENDS:
                raise SocialError("friends_full")
            if await self._friend_count(session, target.id) >= MAX_FRIENDS:
                raise SocialError("target_full")
            sent = await self._count(
                session, FriendRequest.id, FriendRequest.sender_character_id == actor_id
            )
            if sent >= MAX_SENT_REQUESTS:
                raise SocialError("sent_full")
            received = await self._count(
                session, FriendRequest.id, FriendRequest.recipient_character_id == target.id
            )
            if received >= MAX_RECEIVED_REQUESTS:
                raise SocialError("target_full")
            session.add(
                FriendRequest(
                    sender_character_id=actor_id,
                    recipient_character_id=target.id,
                    created_at=now,
                )
            )

    async def respond_request(
        self, actor: int, request_id: UUID, *, accept: bool, now: datetime | None = None
    ) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            request = await self._locked_request(session, actor, request_id)
            me = await self._actor(session, actor)
            if request.recipient_character_id != me.id:
                raise SocialError("request_gone")
            if accept:
                sender = request.sender_character_id
                if await blocked_between(session, me.id, sender):
                    raise SocialError("unavailable")
                if await self._friend_count(session, me.id) >= MAX_FRIENDS:
                    raise SocialError("friends_full")
                if await self._friend_count(session, sender) >= MAX_FRIENDS:
                    raise SocialError("target_full")
                first, second = sorted((me.id, sender))
                session.add(Friendship(character_a=first, character_b=second, created_at=now))
            await session.delete(request)

    async def cancel_request(self, actor: int, request_id: UUID) -> None:
        async with self.sessions.begin() as session:
            request = await self._locked_request(session, actor, request_id)
            me = await self._actor(session, actor)
            if request.sender_character_id != me.id:
                raise SocialError("request_gone")
            await session.delete(request)

    async def remove_friend(self, actor: int, target_id: UUID) -> None:
        async with self.sessions.begin() as session:
            actor_id, target = await self._lock_pair(session, actor, target_id)
            first, second = sorted((actor_id, target.id))
            await session.execute(
                delete(Friendship).where(
                    Friendship.character_a == first, Friendship.character_b == second
                )
            )

    # ----------------------------------------------------------------- blocks

    async def block(self, actor: int, target_id: UUID, *, now: datetime | None = None) -> None:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            actor_id, target = await self._lock_pair(session, actor, target_id)
            if target.id == actor_id:
                raise SocialError("self")
            existing = await session.get(CharacterBlock, (actor_id, target.id))
            if existing is not None:
                return
            count = await self._count(
                session,
                CharacterBlock.blocked_character_id,
                CharacterBlock.blocker_character_id == actor_id,
            )
            if count >= MAX_BLOCKED:
                raise SocialError("blocked_full")
            session.add(
                CharacterBlock(
                    blocker_character_id=actor_id,
                    blocked_character_id=target.id,
                    created_at=now,
                )
            )
            first, second = sorted((actor_id, target.id))
            await session.execute(
                delete(Friendship).where(
                    Friendship.character_a == first, Friendship.character_b == second
                )
            )
            await session.execute(
                delete(FriendRequest).where(
                    or_(
                        (FriendRequest.sender_character_id == actor_id)
                        & (FriendRequest.recipient_character_id == target.id),
                        (FriendRequest.sender_character_id == target.id)
                        & (FriendRequest.recipient_character_id == actor_id),
                    )
                )
            )
            target_id = target.id
        # Separate transaction: answering a Group invite locks the invite before the
        # character, the opposite of the order above. New invites are already refused.
        async with self.sessions.begin() as session:
            for invite in (SocialGroupInvite, GuildInvite):
                await session.execute(
                    update(invite)
                    .where(
                        invite.status == "pending",
                        or_(
                            (invite.inviter_character_id == actor_id)
                            & (invite.invitee_character_id == target_id),
                            (invite.inviter_character_id == target_id)
                            & (invite.invitee_character_id == actor_id),
                        ),
                    )
                    .values(status="cancelled", responded_at=now, revision=invite.revision + 1)
                )

    async def unblock(self, actor: int, target_id: UUID) -> None:
        async with self.sessions.begin() as session:
            actor_id, target = await self._lock_pair(session, actor, target_id)
            await session.execute(
                delete(CharacterBlock).where(
                    CharacterBlock.blocker_character_id == actor_id,
                    CharacterBlock.blocked_character_id == target.id,
                )
            )

    # ------------------------------------------------------------------ lists

    async def friends(self, actor: int, page: int = 0) -> CardPage:
        async with self.sessions() as session:
            me = await self._actor(session, actor)
            other = _other_side(me.id)
            return await self._page(
                session,
                select(other).where(or_(Friendship.character_a == me.id, _is_b(me.id))),
                page,
            )

    async def blocked(self, actor: int, page: int = 0) -> CardPage:
        async with self.sessions() as session:
            me = await self._actor(session, actor)
            return await self._page(
                session,
                select(CharacterBlock.blocked_character_id).where(
                    CharacterBlock.blocker_character_id == me.id
                ),
                page,
            )

    async def recents(self, actor: int, page: int = 0, *, now: datetime | None = None) -> CardPage:
        now = _utcnow(now)
        async with self.sessions() as session:
            me = await self._actor(session, actor)
            ids = list(
                (
                    await session.scalars(
                        select(RecentContact.other_character_id)
                        .where(
                            RecentContact.character_id == me.id,
                            RecentContact.last_seen_at >= now - RECENT_WINDOW,
                        )
                        .order_by(RecentContact.last_seen_at.desc())
                        .limit(MAX_RECENTS)
                    )
                ).all()
            )
            return await self._cards_page(session, ids, page)

    async def requests(self, actor: int) -> RequestsView:
        async with self.sessions() as session:
            me = await self._actor(session, actor)
            incoming = await self._request_views(
                session,
                FriendRequest.recipient_character_id == me.id,
                FriendRequest.sender_character_id,
            )
            outgoing = await self._request_views(
                session,
                FriendRequest.sender_character_id == me.id,
                FriendRequest.recipient_character_id,
            )
            return RequestsView(incoming, outgoing)

    # ---------------------------------------------------------------- profile

    async def public_profile(self, actor: int, target_id: UUID) -> PublicProfile:
        async with self.sessions() as session:
            me = await self._actor(session, actor)
            target = await session.get(Character, target_id)
            if target is None or target.server_id != self.server_id:
                raise SocialError("not_found")
            history = await session.scalar(
                select(CharacterProfile.history).where(CharacterProfile.character_id == target.id)
            )
            title_id = await session.scalar(
                select(CharacterCosmeticSelection.cosmetic_id).where(
                    CharacterCosmeticSelection.character_id == target.id,
                    CharacterCosmeticSelection.cosmetic_type == "title",
                )
            )
            guild = await session.scalar(
                select(Guild.name)
                .join(GuildMember, GuildMember.guild_id == Guild.id)
                .where(GuildMember.character_id == target.id, Guild.status == "active")
            )
            arena = await session.get(ArenaProfile, target.id)
            feats = await self._count(
                session, Achievement.id, Achievement.character_id == target.id
            )
            outgoing = await self._request_between(session, me.id, target.id)
            incoming = await self._request_between(session, target.id, me.id)
            return PublicProfile(
                character_id=target.id,
                name=target.name,
                level=target.level,
                legacy_level=target.legacy_level,
                race=target.race,
                character_class=target.character_class,
                selected_path=target.selected_path,
                guild=guild,
                title=COSMETICS_BY_ID[title_id].name if title_id in COSMETICS_BY_ID else None,
                elo=(
                    elo_for(arena.renome)
                    if arena is not None and arena.placement_played >= PLACEMENT_MATCHES
                    else None
                ),
                feats=feats,
                history=history or None,
                is_self=target.id == me.id,
                is_friend=await self._friendship(session, me.id, target.id) is not None,
                blocked_by_me=await session.get(CharacterBlock, (me.id, target.id)) is not None,
                blocked_me=await session.get(CharacterBlock, (target.id, me.id)) is not None,
                outgoing_request_id=outgoing.id if outgoing is not None else None,
                incoming_request_id=incoming.id if incoming is not None else None,
            )

    # ---------------------------------------------------------------- Relatos

    async def share_story(self, actor: int, *, now: datetime | None = None) -> RelatoView:
        """Reserve the snapshot; the caller posts it and then attaches or reverts."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._actor(session, actor, lock=True)
            history = await session.scalar(
                select(CharacterProfile.history).where(
                    CharacterProfile.character_id == character.id
                )
            )
            if not history:
                raise SocialError("no_story")
            if len(history) > MAX_STORY_CHARACTERS:
                raise SocialError("story_too_long")
            if not story_is_allowed(history):
                raise SocialError("story_forbidden")
            last = await session.scalar(
                select(func.max(Relato.created_at)).where(Relato.character_id == character.id)
            )
            if last is not None and now < last + STORY_SHARE_COOLDOWN:
                raise SocialError("share_cooldown", last + STORY_SHARE_COOLDOWN)
            relato = Relato(
                id=uuid4(),
                server_id=self.server_id,
                character_id=character.id,
                author_name=character.name,
                body=history,
                status="published",
                created_at=now,
            )
            session.add(relato)
            return RelatoView(relato.id, character.id, character.name, history)

    async def attach_relato(self, relato_id: UUID, chat_id: int, message_id: int) -> None:
        async with self.sessions.begin() as session:
            await session.execute(
                update(Relato)
                .where(Relato.id == relato_id)
                .values(chat_id=chat_id, message_id=message_id)
            )

    async def revert_relato(self, relato_id: UUID) -> None:
        """The post failed, so the Recarga must not be spent."""
        async with self.sessions.begin() as session:
            await session.execute(delete(Relato).where(Relato.id == relato_id))

    async def relato(self, relato_id: UUID) -> RelatoView:
        async with self.sessions() as session:
            row = await session.get(Relato, relato_id)
            if row is None or row.server_id != self.server_id or row.status != "published":
                raise SocialError("not_found")
            return RelatoView(row.id, row.character_id, row.author_name, row.body)

    # ---------------------------------------------------------------- reports

    async def report_history(
        self, actor: int, target_id: UUID, *, now: datetime | None = None
    ) -> None:
        async with self.sessions.begin() as session:
            me = await self._actor(session, actor)
            if me.id == target_id:
                raise SocialError("self")
            history = await session.scalar(
                select(CharacterProfile.history)
                .join(Character, Character.id == CharacterProfile.character_id)
                .where(
                    CharacterProfile.character_id == target_id,
                    Character.server_id == self.server_id,
                )
            )
            if not history:
                raise SocialError("not_found")
            await self._file_report(
                session, me.id, "history", f"history:{target_id.hex}", target_id, None, history, now
            )

    async def report_relato(
        self, actor: int, relato_id: UUID, *, now: datetime | None = None
    ) -> None:
        async with self.sessions.begin() as session:
            me = await self._actor(session, actor)
            row = await session.get(Relato, relato_id)
            if row is None or row.server_id != self.server_id or row.status != "published":
                raise SocialError("not_found")
            if row.character_id == me.id:
                raise SocialError("self")
            await self._file_report(
                session,
                me.id,
                "relato",
                f"relato:{relato_id.hex}",
                row.character_id,
                relato_id,
                row.body,
                now,
            )

    async def _file_report(
        self, session, reporter, kind, target_key, target, relato_id, snapshot, now
    ) -> None:
        """Repeating an open report is a no-op, so tapping twice files one item."""
        await session.execute(
            insert(ContentReport)
            .values(
                id=uuid4(),
                server_id=self.server_id,
                kind=kind,
                target_key=target_key,
                reporter_character_id=reporter,
                target_character_id=target,
                relato_id=relato_id,
                snapshot=snapshot,
                status="open",
                created_at=_utcnow(now),
            )
            .on_conflict_do_nothing()
        )

    # ---------------------------------------------------------------- helpers

    async def _actor(self, session, actor: int, *, lock: bool = False) -> Character:
        statement = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        character = await session.scalar(statement.with_for_update() if lock else statement)
        if character is None:
            raise SocialError("no_character")
        return character

    async def _lock_pair(self, session, actor: int, target_id: UUID) -> tuple[UUID, Character]:
        me = await self._actor(session, actor)
        rows = (
            await session.scalars(
                select(Character)
                .where(Character.id.in_({me.id, target_id}))
                .order_by(Character.id)
                .with_for_update()
            )
        ).all()
        target = next((row for row in rows if row.id == target_id), None)
        if target is None or target.server_id != self.server_id:
            raise SocialError("not_found")
        return me.id, target

    async def _locked_request(self, session, actor: int, request_id: UUID) -> FriendRequest:
        seed = await session.get(FriendRequest, request_id)
        if seed is None:
            raise SocialError("request_gone")
        sender, recipient = seed.sender_character_id, seed.recipient_character_id
        await session.execute(
            select(Character.id)
            .where(Character.id.in_({sender, recipient}))
            .order_by(Character.id)
            .with_for_update()
        )
        request = await session.scalar(
            select(FriendRequest)
            .where(FriendRequest.id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if request is None:
            raise SocialError("request_gone")
        return request

    @staticmethod
    async def _count(session, column, *where) -> int:
        return int(await session.scalar(select(func.count(column)).where(*where)) or 0)

    async def _friend_count(self, session, character_id: UUID) -> int:
        return await self._count(
            session,
            Friendship.created_at,
            or_(Friendship.character_a == character_id, Friendship.character_b == character_id),
        )

    @staticmethod
    async def _friendship(session, first: UUID, second: UUID) -> Friendship | None:
        return await session.get(Friendship, tuple(sorted((first, second))))

    @staticmethod
    async def _request_between(session, sender: UUID, recipient: UUID) -> FriendRequest | None:
        return await session.scalar(
            select(FriendRequest).where(
                FriendRequest.sender_character_id == sender,
                FriendRequest.recipient_character_id == recipient,
            )
        )

    async def _page(self, session, id_query, page: int) -> CardPage:
        ids = list((await session.scalars(id_query)).all())
        rows = (
            await session.scalars(
                select(Character).where(Character.id.in_(ids)).order_by(func.lower(Character.name))
            )
        ).all()
        return _slice([row for row in rows], page)

    async def _cards_page(self, session, ids: list[UUID], page: int) -> CardPage:
        by_id = {
            row.id: row
            for row in (await session.scalars(select(Character).where(Character.id.in_(ids)))).all()
        }
        return _slice([by_id[item] for item in ids if item in by_id], page)

    async def _request_views(self, session, where, other_column) -> tuple[RequestView, ...]:
        rows = (
            await session.execute(
                select(FriendRequest.id, Character)
                .join(Character, Character.id == other_column)
                .where(where)
                .order_by(FriendRequest.created_at)
            )
        ).all()
        return tuple(RequestView(request_id, _card(row)) for request_id, row in rows)


class ContentModerationAdmin:
    """Operator-only queue for §31.1. Removal never touches progression or economy."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self.sessions = sessions

    async def list_reports(self, status: str, limit: int = 50) -> tuple[ReportView, ...]:
        async with self.sessions() as session:
            statement = select(ContentReport).order_by(ContentReport.created_at).limit(limit)
            if status != "all":
                statement = statement.where(ContentReport.status == status)
            rows = (await session.scalars(statement)).all()
            return tuple(
                ReportView(
                    row.id, row.kind, row.target_key, row.snapshot, row.status, row.created_at
                )
                for row in rows
            )

    async def resolve(
        self, report_id: UUID, *, uphold: bool, note: str | None, now: datetime | None = None
    ) -> ReportResolution:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            report = await session.get(ContentReport, report_id, with_for_update=True)
            if report is None:
                raise SocialError("not_found")
            removed, chat_id, message_id = False, None, None
            if uphold and report.kind == "relato" and report.relato_id is not None:
                relato = await session.get(Relato, report.relato_id, with_for_update=True)
                if relato is not None and relato.status == "published":
                    relato.status, relato.removed_at = "removed", now
                    removed, chat_id, message_id = True, relato.chat_id, relato.message_id
            if uphold and report.kind == "history" and report.target_character_id is not None:
                await session.scalar(
                    select(Character.id)
                    .where(Character.id == report.target_character_id)
                    .with_for_update()
                )
                profile = await session.scalar(
                    select(CharacterProfile)
                    .where(CharacterProfile.character_id == report.target_character_id)
                    .with_for_update()
                )
                # An edited text was not what the report saw, so it stays.
                if profile is not None and profile.history == report.snapshot:
                    profile.history = None
                    profile.revision += 1
                    profile.updated_at = now
                    removed = True
            await session.execute(
                update(ContentReport)
                .where(
                    ContentReport.target_key == report.target_key, ContentReport.status == "open"
                )
                .values(
                    status="upheld" if uphold else "dismissed", reviewed_at=now, review_note=note
                )
            )
            return ReportResolution(removed, chat_id, message_id)


def _utcnow(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _card(row: Character) -> PlayerCard:
    return PlayerCard(row.id, row.name, row.level, row.character_class)


def _slice(rows: list[Character], page: int) -> CardPage:
    total = len(rows)
    last = max(0, (total - 1) // PAGE_SIZE)
    page = min(max(0, page), last)
    chunk = rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    return CardPage(tuple(_card(row) for row in chunk), page, total)


def _is_b(character_id: UUID):
    return Friendship.character_b == character_id


def _other_side(character_id: UUID):
    from sqlalchemy import case

    return case(
        (Friendship.character_a == character_id, Friendship.character_b),
        else_=Friendship.character_a,
    )
