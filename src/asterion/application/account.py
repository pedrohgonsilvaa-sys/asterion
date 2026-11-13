"""Persistent character settings, account identity, and deletion workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.character_names import lock_character_name, name_available, utc_now
from asterion.application.groups import prepare_character_deletion
from asterion.application.guild_upkeep import prepare_guild_departure
from asterion.domain.creation import NamePolicy, normalize_name
from asterion.infrastructure.db.models import (
    Character,
    CharacterAccountInput,
    CharacterDeletionRequest,
    CharacterDoctrineInput,
    CharacterNameReservation,
    CharacterNotificationPreference,
    CharacterPendingInput,
    CharacterProfile,
    CharacterRenameHistory,
    ClassTrialState,
    CreationDraft,
    CreationInput,
    DungeonLobby,
    DungeonLobbyMember,
    DungeonMatchQueue,
    DungeonRun,
    DungeonRunMember,
    GameActivity,
    Guild,
    GuildMember,
    HuntRound,
    SocialGroup,
    SocialGroupMember,
)

NOTIFICATION_CATEGORIES = frozenset(
    {"essentials", "events", "competitive", "guild", "market", "chronicle"}
)
RENAME_COST = 2500
RENAME_COOLDOWN = timedelta(days=30)
NAME_RESERVATION_PERIOD = timedelta(days=30)
DELETION_PERIOD = timedelta(days=7)
ACTIVE_LOBBY_MEMBER_STATES = ("invited", "joined", "queued", "matched", "confirmed")


async def notification_enabled(
    session: AsyncSession, character_id: UUID, category: str
) -> bool:
    """Read a per-character category, defaulting sparse preference rows to enabled."""
    if category not in NOTIFICATION_CATEGORIES:
        raise ValueError("Unknown notification category")
    value = await session.scalar(
        select(CharacterNotificationPreference.enabled).where(
            CharacterNotificationPreference.character_id == character_id,
            CharacterNotificationPreference.category == category,
        )
    )
    return True if value is None else bool(value)


class AccountRejected(RuntimeError):
    def __init__(self, code: str, *, due_at: datetime | None = None) -> None:
        self.code = code
        self.due_at = due_at
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class NotificationPreferenceView:
    enabled: bool
    revision: int


@dataclass(frozen=True, slots=True)
class AccountView:
    character_id: UUID
    name: str
    level: int
    crowns: int
    rename_available_at: datetime | None
    deletion_due_at: datetime | None
    deletion_revision: int | None
    deletion_preview_id: UUID | None = None

    @property
    def deletion_pending(self) -> bool:
        return self.deletion_due_at is not None


@dataclass(frozen=True, slots=True)
class RenameInputView:
    status: str
    revision: int
    current_name: str
    new_name: str | None
    error: str | None


@dataclass(frozen=True, slots=True)
class DeletionResult:
    pending: bool
    due_at: datetime | None
    revision: int | None
    changed: bool


async def finalize_due_character_deletions(
    sessions: async_sessionmaker[AsyncSession],
    server_id: str,
    *,
    now: datetime | None = None,
    character_id: UUID | None = None,
    limit: int = 100,
) -> int:
    """Finalize due requests idempotently; usable by lazy login and maintenance jobs."""
    now = now or utc_now()
    async with sessions.begin() as session:
        query = (
            select(CharacterDeletionRequest.id, CharacterDeletionRequest.character_id)
            .where(
                CharacterDeletionRequest.server_id == server_id,
                CharacterDeletionRequest.status == "pending",
                CharacterDeletionRequest.due_at <= now,
            )
            .order_by(CharacterDeletionRequest.due_at, CharacterDeletionRequest.id)
            .limit(max(1, limit))
        )
        if character_id is not None:
            query = query.where(CharacterDeletionRequest.character_id == character_id)
        requests = list((await session.execute(query)).all())
        finalized = 0
        for request_id, candidate_character_id in requests:
            # Group mutations lock Group before Character. Keep the same order
            # when a due deletion needs to transfer leadership or cancel a ready
            # check, otherwise deletion could deadlock against an invite/roster
            # mutation. If membership changed while we waited, retry next pass.
            candidate_group_id = await session.scalar(
                select(SocialGroupMember.group_id).where(
                    SocialGroupMember.character_id == candidate_character_id
                )
            )
            locked_group = None
            if candidate_group_id is not None:
                locked_group = await session.scalar(
                    select(SocialGroup)
                    .where(SocialGroup.id == candidate_group_id)
                    .with_for_update(skip_locked=True)
                )
                if locked_group is None:
                    continue
            # Guild mutations also lock the Guild before the Character (§30.3).
            candidate_guild_id = await session.scalar(
                select(GuildMember.guild_id).where(
                    GuildMember.character_id == candidate_character_id
                )
            )
            if candidate_guild_id is not None:
                locked_guild = await session.scalar(
                    select(Guild)
                    .where(Guild.id == candidate_guild_id)
                    .with_for_update(skip_locked=True)
                )
                if locked_guild is None:
                    continue
            character = await session.scalar(
                select(Character)
                .where(
                    Character.id == candidate_character_id,
                    Character.server_id == server_id,
                )
                .with_for_update(skip_locked=True)
            )
            if character is None:
                character_exists = await session.scalar(
                    select(Character.id).where(
                        Character.id == candidate_character_id,
                        Character.server_id == server_id,
                    )
                )
                if character_exists is not None:
                    continue
                request = await session.scalar(
                    select(CharacterDeletionRequest)
                    .where(CharacterDeletionRequest.id == request_id)
                    .with_for_update()
                )
                if (
                    request is None
                    or request.status != "pending"
                    or request.due_at > now
                ):
                    continue
                request.status = "completed"
                request.revision += 1
                finalized += 1
                continue
            request = await session.scalar(
                select(CharacterDeletionRequest)
                .where(
                    CharacterDeletionRequest.id == request_id,
                    CharacterDeletionRequest.character_id == character.id,
                    CharacterDeletionRequest.server_id == server_id,
                )
                .with_for_update()
            )
            if (
                request is None
                or request.status != "pending"
                or request.due_at > now
            ):
                continue
            current_group_id = await session.scalar(
                select(SocialGroupMember.group_id).where(
                    SocialGroupMember.character_id == character.id
                )
            )
            if current_group_id != candidate_group_id:
                continue
            current_guild_id = await session.scalar(
                select(GuildMember.guild_id).where(GuildMember.character_id == character.id)
            )
            if current_guild_id != candidate_guild_id:
                continue
            # A due request must never delete a character still holding gameplay state.
            if await _has_foreground(session, character.id):
                continue
            if not await prepare_character_deletion(session, character.id):
                continue
            await prepare_guild_departure(session, character.id, now)
            old_name = character.name
            await lock_character_name(session, server_id, old_name)
            await _reserve_name(
                session,
                server_id=server_id,
                name=old_name,
                until=now + NAME_RESERVATION_PERIOD,
                source="deletion",
                character_id=character.id,
            )
            request.status = "completed"
            request.revision += 1
            await session.execute(
                delete(CreationDraft).where(
                    CreationDraft.telegram_id == character.telegram_id,
                    CreationDraft.server_id == server_id,
                )
            )
            await session.execute(
                delete(CreationInput).where(
                    CreationInput.telegram_id == character.telegram_id,
                    CreationInput.server_id == server_id,
                )
            )
            await delete_character_owned_data(session, character.id)
            finalized += 1
        return finalized


async def _reserve_name(
    session: AsyncSession,
    *,
    server_id: str,
    name: str,
    until: datetime,
    source: str,
    character_id: UUID,
) -> None:
    statement = pg_insert(CharacterNameReservation).values(
        server_id=server_id,
        normalized_name=name.casefold(),
        reserved_until=until,
        source=source,
        origin_character_id=character_id,
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[
                CharacterNameReservation.server_id,
                CharacterNameReservation.normalized_name,
            ],
            set_={
                "reserved_until": statement.excluded.reserved_until,
                "source": statement.excluded.source,
                "origin_character_id": statement.excluded.origin_character_id,
                "created_at": func.now(),
            },
        )
    )


async def _has_foreground(session: AsyncSession, character_id: UUID) -> bool:
    if await session.scalar(
        select(GameActivity.id).where(
            GameActivity.character_id == character_id,
            GameActivity.status == "active",
        )
    ):
        return True
    if await session.scalar(
        select(HuntRound.id).where(
            HuntRound.character_id == character_id,
            HuntRound.status.in_(("preparing", "active", "interrupted")),
        )
    ):
        return True
    if await session.scalar(
        select(DungeonRunMember.run_id)
        .join(DungeonRun, DungeonRun.id == DungeonRunMember.run_id)
        .where(
            DungeonRunMember.character_id == character_id,
            DungeonRunMember.status.in_(("active", "defeated")),
            DungeonRun.status == "active",
        )
    ):
        return True
    if await session.scalar(
        select(DungeonLobbyMember.lobby_id)
        .join(DungeonLobby, DungeonLobby.id == DungeonLobbyMember.lobby_id)
        .where(
            DungeonLobbyMember.character_id == character_id,
            DungeonLobbyMember.status.in_(ACTIVE_LOBBY_MEMBER_STATES),
            DungeonLobby.status.in_(("forming", "confirming")),
        )
    ):
        return True
    if await session.scalar(
        select(DungeonMatchQueue.character_id).where(
            DungeonMatchQueue.character_id == character_id,
            DungeonMatchQueue.status.in_(("queued", "matched")),
        )
    ):
        return True
    return bool(
        await session.scalar(
            select(ClassTrialState.character_id).where(
                ClassTrialState.character_id == character_id,
                ClassTrialState.status == "active",
            )
        )
    )


class AccountService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        name_policy: NamePolicy,
    ) -> None:
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id
        self.name_policy = name_policy

    async def notification(self, actor: int, category: str) -> NotificationPreferenceView | None:
        if category not in NOTIFICATION_CATEGORIES:
            raise ValueError("Unknown notification category")
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            row = await session.get(CharacterNotificationPreference, (character.id, category))
            if row is None:
                return NotificationPreferenceView(True, 0)
            return NotificationPreferenceView(row.enabled, row.revision)

    async def set_notification(
        self,
        actor: int,
        category: str,
        *,
        expected_revision: int,
        expected_enabled: bool,
        enabled: bool,
    ) -> NotificationPreferenceView | None:
        if category not in NOTIFICATION_CATEGORIES:
            raise ValueError("Unknown notification category")
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            row = await session.scalar(
                select(CharacterNotificationPreference)
                .where(
                    CharacterNotificationPreference.character_id == character.id,
                    CharacterNotificationPreference.category == category,
                )
                .with_for_update()
            )
            revision = row.revision if row else 0
            current = row.enabled if row else True
            if (
                revision != expected_revision
                or current != expected_enabled
                or current == enabled
            ):
                return NotificationPreferenceView(current, revision)
            if row is None:
                row = CharacterNotificationPreference(
                    character_id=character.id,
                    category=category,
                    enabled=enabled,
                    revision=revision + 1,
                )
                session.add(row)
            else:
                row.enabled = enabled
                row.revision += 1
                row.updated_at = utc_now()
            return NotificationPreferenceView(enabled, revision + 1)

    async def account(self, actor: int, *, now: datetime | None = None) -> AccountView | None:
        now = now or utc_now()
        async with self.sessions() as session:
            character_id = await session.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
            )
        if character_id is None:
            return None
        await finalize_due_character_deletions(
            self.sessions, self.server_id, now=now, character_id=character_id, limit=1
        )
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            last_rename = await session.scalar(
                select(CharacterRenameHistory.renamed_at)
                .where(CharacterRenameHistory.character_id == character.id)
                .order_by(CharacterRenameHistory.renamed_at.desc())
                .limit(1)
            )
            pending = await session.scalar(
                select(CharacterDeletionRequest).where(
                    CharacterDeletionRequest.character_id == character.id,
                    CharacterDeletionRequest.status == "pending",
                )
            )
            preview = await session.scalar(
                select(CharacterDeletionRequest).where(
                    CharacterDeletionRequest.character_id == character.id,
                    CharacterDeletionRequest.status == "preview",
                    CharacterDeletionRequest.due_at > now,
                )
            )
            due_rename = last_rename + RENAME_COOLDOWN if last_rename else None
            return AccountView(
                character.id,
                character.name,
                character.level,
                character.crowns,
                due_rename if due_rename and due_rename > now else None,
                pending.due_at if pending else None,
                pending.revision if pending else None,
                preview.id if preview else None,
            )

    async def begin_rename(
        self, actor: int, prompt_message_id: int, *, now=None
    ) -> RenameInputView:
        now = now or utc_now()
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                raise AccountRejected("missing_character")
            if await _has_foreground(session, character.id):
                raise AccountRejected("foreground")
            await self._ensure_not_deleting(session, character.id)
            await self._validate_rename_cooldown(session, character.id, now)
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(CharacterPendingInput.character_id == character.id)
                .with_for_update()
            )
            if lease is not None and lease.input_kind != "rename":
                raise AccountRejected("input_pending")
            row = await session.scalar(
                select(CharacterAccountInput)
                .where(CharacterAccountInput.character_id == character.id)
                .with_for_update()
            )
            if row is None:
                row = CharacterAccountInput(
                    character_id=character.id,
                    status="awaiting",
                    prompt_message_id=prompt_message_id,
                    current_name=character.name,
                    revision=0,
                )
                session.add(row)
            else:
                row.status = "awaiting"
                row.prompt_message_id = prompt_message_id
                row.current_name = character.name
                row.new_name = None
                row.error = None
                row.last_update_id = None
                row.revision += 1
                row.updated_at = now
            if lease is None:
                session.add(
                    CharacterPendingInput(
                        character_id=character.id,
                        input_kind="rename",
                        prompt_message_id=prompt_message_id,
                    )
                )
            else:
                lease.prompt_message_id = prompt_message_id
                lease.updated_at = now
            return _rename_view(row)

    async def preview_rename(
        self,
        actor: int,
        prompt_message_id: int,
        update_id: int,
        raw_name: str,
        *,
        now=None,
    ) -> RenameInputView:
        now = now or utc_now()
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                raise AccountRejected("missing_character")
            row = await session.scalar(
                select(CharacterAccountInput)
                .where(CharacterAccountInput.character_id == character.id)
                .with_for_update()
            )
            lease = await session.scalar(
                select(CharacterPendingInput)
                .where(
                    CharacterPendingInput.character_id == character.id,
                    CharacterPendingInput.input_kind == "rename",
                    CharacterPendingInput.prompt_message_id == prompt_message_id,
                )
                .with_for_update()
            )
            if row is None or row.prompt_message_id != prompt_message_id or lease is None:
                raise AccountRejected("stale_input")
            if row.last_update_id == update_id:
                return _rename_view(row)
            normalized = normalize_name(raw_name)
            row.last_update_id = update_id
            row.revision += 1
            row.current_name = character.name
            row.new_name = normalized
            row.error = None
            if normalized is None or not self.name_policy.accepts(normalized):
                row.status = "invalid"
                row.error = "format"
            elif normalized.casefold() == character.name.casefold():
                row.status = "invalid"
                row.error = "same"
                row.new_name = None
            else:
                await lock_character_name(session, self.server_id, normalized)
                if await name_available(
                    session,
                    server_id=self.server_id,
                    name=normalized,
                    now=now,
                    except_character_id=character.id,
                ):
                    row.status = "preview"
                else:
                    row.status = "unavailable"
                    row.error = "unavailable"
            row.updated_at = now
            return _rename_view(row)

    async def confirm_rename(
        self, actor: int, expected_revision: int, *, now=None
    ) -> str:
        now = now or utc_now()
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                raise AccountRejected("missing_character")
            row = await session.scalar(
                select(CharacterAccountInput)
                .where(CharacterAccountInput.character_id == character.id)
                .with_for_update()
            )
            if (
                row is None
                or row.revision != expected_revision
                or row.status != "preview"
                or not row.new_name
            ):
                raise AccountRejected("stale_preview")
            if await _has_foreground(session, character.id):
                raise AccountRejected("foreground")
            await self._ensure_not_deleting(session, character.id)
            await self._validate_rename_cooldown(session, character.id, now)
            new_name = normalize_name(row.new_name)
            if new_name is None or not self.name_policy.accepts(new_name):
                raise AccountRejected("invalid_name")
            for name in sorted((character.name, new_name), key=str.casefold):
                await lock_character_name(session, self.server_id, name)
            if not await name_available(
                session,
                server_id=self.server_id,
                name=new_name,
                now=now,
                except_character_id=character.id,
            ):
                raise AccountRejected("name_unavailable")
            if character.crowns < RENAME_COST:
                raise AccountRejected("insufficient_crowns")
            old_name = character.name
            character.crowns -= RENAME_COST
            character.name = new_name
            session.add(
                CharacterRenameHistory(
                    id=uuid4(),
                    character_id=character.id,
                    server_id=self.server_id,
                    old_name=old_name,
                    new_name=new_name,
                    renamed_at=now,
                    origin="player",
                )
            )
            await _reserve_name(
                session,
                server_id=self.server_id,
                name=old_name,
                until=now + NAME_RESERVATION_PERIOD,
                source="rename",
                character_id=character.id,
            )
            await session.delete(row)
            lease = await session.get(CharacterPendingInput, character.id)
            if lease and lease.input_kind == "rename":
                await session.delete(lease)
            return new_name

    async def cancel_rename(self, actor: int) -> bool:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return False
            row = await session.get(CharacterAccountInput, character.id)
            lease = await session.get(CharacterPendingInput, character.id)
            changed = row is not None or (lease is not None and lease.input_kind == "rename")
            if row is not None:
                await session.delete(row)
            if lease is not None and lease.input_kind == "rename":
                await session.delete(lease)
            return changed

    async def cancel_transient_inputs(self, actor: int) -> bool:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return False
            pending = await session.get(CharacterPendingInput, character.id)
            profile = await session.get(CharacterProfile, character.id)
            history_pending = profile is not None and profile.history_prompt_message_id is not None
            if profile is not None and history_pending:
                profile.history_prompt_message_id = None
                profile.updated_at = utc_now()
            doctrine_input = await session.get(CharacterDoctrineInput, character.id)
            account_input = await session.get(CharacterAccountInput, character.id)
            changed = (
                pending is not None
                or history_pending
                or doctrine_input is not None
                or account_input is not None
            )
            if doctrine_input is not None:
                await session.delete(doctrine_input)
            if account_input is not None:
                await session.delete(account_input)
            if pending is not None:
                await session.delete(pending)
            return changed

    async def start_deletion_confirmation(self, actor: int, *, now=None) -> AccountView:
        now = now or utc_now()
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                raise AccountRejected("missing_character")
            existing = await session.scalar(
                select(CharacterDeletionRequest)
                .where(
                    CharacterDeletionRequest.character_id == character.id,
                    CharacterDeletionRequest.status == "pending",
                )
                .with_for_update()
            )
            if existing is not None:
                raise AccountRejected("deletion_pending")
            if await _has_foreground(session, character.id):
                raise AccountRejected("foreground")
            stale_previews = list(
                (
                    await session.scalars(
                        select(CharacterDeletionRequest)
                        .where(
                            CharacterDeletionRequest.character_id == character.id,
                            CharacterDeletionRequest.status == "preview",
                        )
                        .with_for_update()
                    )
                ).all()
            )
            for stale in stale_previews:
                await session.delete(stale)
            request = CharacterDeletionRequest(
                id=uuid4(),
                character_id=character.id,
                telegram_id=actor,
                server_id=self.server_id,
                name_at_request=character.name,
                requested_at=now,
                due_at=now + timedelta(minutes=10),
                status="preview",
                revision=0,
            )
            session.add(request)
        view = await self.account(actor, now=now)
        if view is None:
            raise AccountRejected("missing_character")
        return view

    async def request_deletion(
        self,
        actor: int,
        expected_name: str,
        preview_id: UUID,
        *,
        now=None,
        period: timedelta = DELETION_PERIOD,
    ) -> DeletionResult:
        now = now or utc_now()
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                raise AccountRejected("missing_character")
            existing = await session.scalar(
                select(CharacterDeletionRequest)
                .where(
                    CharacterDeletionRequest.character_id == character.id,
                    CharacterDeletionRequest.status == "pending",
                )
                .with_for_update()
            )
            if existing is not None:
                return DeletionResult(True, existing.due_at, existing.revision, False)
            if character.name != expected_name:
                raise AccountRejected("stale_confirmation")
            request = await session.scalar(
                select(CharacterDeletionRequest)
                .where(
                    CharacterDeletionRequest.id == preview_id,
                    CharacterDeletionRequest.character_id == character.id,
                    CharacterDeletionRequest.status == "preview",
                )
                .with_for_update()
            )
            if (
                request is None
                or now >= request.due_at
                or request.name_at_request != expected_name
            ):
                raise AccountRejected("stale_confirmation")
            if await _has_foreground(session, character.id):
                raise AccountRejected("foreground")
            request.requested_at = now
            request.due_at = now + period
            request.status = "pending"
            request.revision += 1
            account_input = await session.get(CharacterAccountInput, character.id)
            pending_input = await session.get(CharacterPendingInput, character.id)
            if account_input is not None:
                await session.delete(account_input)
            if pending_input is not None:
                if pending_input.input_kind == "history":
                    profile = await session.get(CharacterProfile, character.id)
                    if profile is not None:
                        profile.history_prompt_message_id = None
                elif pending_input.input_kind == "doctrine_name":
                    doctrine_input = await session.get(CharacterDoctrineInput, character.id)
                    if doctrine_input is not None:
                        await session.delete(doctrine_input)
                await session.delete(pending_input)
            return DeletionResult(True, request.due_at, request.revision, True)

    async def delete_now(self, actor: int, typed_name: str, *, now=None) -> str:
        """Immediate deletion, confirmed by typing the character name.

        Needs a live preview (opened by start_deletion_confirmation). Returns the
        deleted name. The name stays reserved (NAME_RESERVATION_PERIOD) as before.
        """
        now = now or utc_now()
        view = await self.account(actor, now=now)
        if view is None:
            raise AccountRejected("missing_character")
        if not view.deletion_pending and view.deletion_preview_id is None:
            raise AccountRejected("stale_confirmation")
        if typed_name.strip().casefold() != view.name.casefold():
            raise AccountRejected("name_mismatch")
        if view.deletion_pending:
            # Old 7-day request: shorten it to now.
            async with self.sessions.begin() as session:
                request = await session.scalar(
                    select(CharacterDeletionRequest)
                    .where(
                        CharacterDeletionRequest.character_id == view.character_id,
                        CharacterDeletionRequest.status == "pending",
                    )
                    .with_for_update()
                )
                if request is not None:
                    request.due_at = max(request.requested_at + timedelta(seconds=1), now)
                    request.due_at = min(request.due_at, now + timedelta(seconds=1))
                    request.revision += 1
        else:
            await self.request_deletion(
                actor, view.name, view.deletion_preview_id, now=now, period=timedelta(seconds=1)
            )
        # DB check needs due_at > requested_at, so finalize one second later.
        finalized = await finalize_due_character_deletions(
            self.sessions,
            self.server_id,
            now=now + timedelta(seconds=1),
            character_id=view.character_id,
            limit=1,
        )
        if finalized == 0:
            # Could not delete now (group/guild/foreground busy): back out, keep the character.
            async with self.sessions.begin() as session:
                request = await session.scalar(
                    select(CharacterDeletionRequest)
                    .where(
                        CharacterDeletionRequest.character_id == view.character_id,
                        CharacterDeletionRequest.status == "pending",
                    )
                    .with_for_update()
                )
                if request is not None:
                    request.status = "cancelled"
                    request.cancelled_at = now
                    request.revision += 1
            raise AccountRejected("foreground")
        return view.name

    async def cancel_deletion(
        self, actor: int, expected_revision: int | None = None, *, now=None
    ) -> DeletionResult:
        now = now or utc_now()
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return DeletionResult(False, None, None, False)
            request = await session.scalar(
                select(CharacterDeletionRequest)
                .where(
                    CharacterDeletionRequest.character_id == character.id,
                    CharacterDeletionRequest.status == "pending",
                )
                .with_for_update()
            )
            if request is None:
                return DeletionResult(False, None, None, False)
            if expected_revision is not None and request.revision != expected_revision:
                raise AccountRejected("stale_deletion")
            if now >= request.due_at:
                raise AccountRejected("deletion_due")
            request.status = "cancelled"
            request.cancelled_at = now
            request.revision += 1
            return DeletionResult(False, None, request.revision, True)

    async def pending_deletion(self, actor: int, *, now=None) -> AccountView | None:
        return await self.account(actor, now=now)

    async def _validate_rename_cooldown(
        self, session: AsyncSession, character_id: UUID, now: datetime
    ) -> None:
        last = await session.scalar(
            select(CharacterRenameHistory.renamed_at)
            .where(CharacterRenameHistory.character_id == character_id)
            .order_by(CharacterRenameHistory.renamed_at.desc())
            .limit(1)
        )
        if last is not None and now < last + RENAME_COOLDOWN:
            raise AccountRejected("cooldown", due_at=last + RENAME_COOLDOWN)

    async def _ensure_not_deleting(self, session: AsyncSession, character_id: UUID) -> None:
        pending = await session.scalar(
            select(CharacterDeletionRequest.id).where(
                CharacterDeletionRequest.character_id == character_id,
                CharacterDeletionRequest.status == "pending",
            )
        )
        if pending is not None:
            raise AccountRejected("deletion_pending")

    async def _character(
        self, session: AsyncSession, actor: int, *, lock: bool = False
    ) -> Character | None:
        query = select(Character).where(
            Character.telegram_id == actor,
            Character.server_id == self.server_id,
        )
        if lock:
            query = query.with_for_update()
        return await session.scalar(query)


def _rename_view(row: CharacterAccountInput) -> RenameInputView:
    return RenameInputView(row.status, row.revision, row.current_name, row.new_name, row.error)
