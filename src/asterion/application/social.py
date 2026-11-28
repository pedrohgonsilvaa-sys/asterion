"""Perfil público, Relatos e denúncias de conteúdo.

Sources: GDD Estrutural v1.6.0 §31.1 and §49.18.

Vínculos (Amigos, Pedidos, Bloqueados, Recentes e Buscar Jogador) saiu do produto por
decisão do autor; o Grupo segue independente. As tabelas antigas ficam no banco, sem uso.

Telegram IDs never leave this module. Views carry the immutable character id.

Author decisions (2026-11-08) for points the GDD leaves open: links and @mentions are
refused when saving a História; reports go to an operator queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.domain.arena import PLACEMENT_MATCHES, elo_for
from asterion.domain.social import (
    MAX_STORY_CHARACTERS,
    STORY_SHARE_COOLDOWN,
    story_is_allowed,
)
from asterion.infrastructure.db.models import (
    Achievement,
    ArenaProfile,
    Character,
    CharacterCosmeticSelection,
    CharacterProfile,
    ContentReport,
    Guild,
    GuildMember,
    Relato,
)


class SocialError(ValueError):
    """A Perfil/Relato action is invalid for the current, revalidated state."""

    def __init__(self, code: str, available_at: datetime | None = None):
        self.code = code
        self.available_at = available_at
        super().__init__(code)


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
            return PublicProfile(
                character_id=target.id,
                name=target.name,
                level=target.level,
                legacy_level=target.legacy_level,
                race=target.race,
                character_class=target.character_class,
                selected_path=target.selected_path,
                guild=guild,
                title=(
                    COSMETICS_BY_ID[title_id].name if title_id in COSMETICS_BY_ID else target.title
                ),
                elo=(
                    elo_for(arena.renome)
                    if arena is not None and arena.placement_played >= PLACEMENT_MATCHES
                    else None
                ),
                feats=feats,
                history=history or None,
                is_self=target.id == me.id,
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

    @staticmethod
    async def _count(session, column, *where) -> int:
        return int(await session.scalar(select(func.count(column)).where(*where)) or 0)

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
                    profile.history_title = None
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
