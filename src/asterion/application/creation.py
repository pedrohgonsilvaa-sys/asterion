"""Transactional creation use cases; PostgreSQL is the sole state authority."""

from dataclasses import fields, replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.character_names import lock_character_name, name_available
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.creation import (
    PROLOGUE,
    RULESET,
    Creation,
    NamePolicy,
    navigate,
    normalize_name,
)
from asterion.infrastructure.db.models import Account, Character, CreationDraft, CreationInput


class CreationService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        policy: NamePolicy | None = None,
    ):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id
        self.policy = policy or NamePolicy()

    async def _load(
        self,
        session: AsyncSession,
        actor: int,
        *,
        create: bool = True,
    ) -> Character | CreationDraft | None:
        if actor <= 0:
            raise ValueError("Invalid Telegram actor")
        if create:
            await session.execute(
                insert(Account).values(telegram_id=actor).on_conflict_do_nothing()
            )
        # Also serializes first /start and multiple devices before a draft exists.
        account = await session.scalar(
            select(Account).where(Account.telegram_id == actor).with_for_update()
        )
        if account is None:
            return None
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )
        if character:
            return character
        draft = await session.scalar(
            select(CreationDraft).where(
                CreationDraft.telegram_id == actor,
                CreationDraft.server_id == self.server_id,
            )
        )
        if draft is None and create:
            draft = CreationDraft(telegram_id=actor, server_id=self.server_id)
            session.add(draft)
            await session.flush()
        return draft

    @staticmethod
    def snapshot(row: Character | CreationDraft) -> Creation:
        if isinstance(row, Character):
            return Creation(
                id=row.id,
                step=row.stage,
                name=row.name,
                race=row.race,
                character_class=row.character_class,
            )
        return Creation(**{field.name: getattr(row, field.name) for field in fields(Creation)})

    @staticmethod
    def _save(row: CreationDraft, state: Creation) -> None:
        for field in fields(Creation):
            if field.name not in ("id", "version"):
                setattr(row, field.name, getattr(state, field.name))
        row.version += 1

    async def start(self, actor: int) -> Creation:
        async with self.sessions.begin() as session:
            row = await self._load(session, actor)
            assert row is not None
            return self.snapshot(row)

    async def resume(self, actor: int) -> Creation | None:
        async with self.sessions.begin() as session:
            row = await self._load(session, actor, create=False)
            return self.snapshot(row) if row is not None else None

    async def _name_allowed(self, session: AsyncSession, name: str) -> bool:
        if not self.policy.accepts(name):
            return False
        await lock_character_name(session, self.server_id, name)
        return await name_available(session, server_id=self.server_id, name=name)

    async def name(self, actor: int, value: str, update_id: int) -> Creation:
        async with self.sessions.begin() as session:
            row = await self._load(session, actor)
            assert row is not None
            state = self.snapshot(row)
            if isinstance(row, Character):
                return state
            consumed = await session.scalar(
                insert(CreationInput)
                .values(
                    telegram_id=actor,
                    server_id=self.server_id,
                    update_id=update_id,
                )
                .on_conflict_do_nothing()
                .returning(CreationInput.update_id)
            )
            if consumed is None or state.step != "name":
                return state
            normalized = normalize_name(value)
            if normalized is None:
                updated = replace(state, error="format", rejected_name=None)
            elif not await self._name_allowed(session, normalized):
                updated = replace(state, error="unavailable", rejected_name=normalized)
            else:
                updated = replace(
                    state,
                    name=normalized,
                    error=None,
                    rejected_name=None,
                    step="confirm"
                    if state.editing and state.race and state.character_class
                    else "race",
                    editing=False,
                )
            self._save(row, updated)
            return self.snapshot(row)

    async def callback(
        self,
        actor: int,
        draft_id: UUID,
        version: int,
        action: str,
    ) -> Creation | None:
        async with self.sessions.begin() as session:
            row = await self._load(session, actor, create=False)
            if row is None:
                return None
            state = self.snapshot(row)
            if isinstance(row, Character):
                # Includes repeated confirmation after a successful commit/retry.
                return state
            if state.id != draft_id or state.version != version:
                return state
            if action == "confirm" and state.step == "confirm":
                return await self._confirm(session, row, state)
            updated = navigate(state, action)
            if updated is not None:
                self._save(row, updated)
            return self.snapshot(row)

    async def _confirm(
        self,
        session: AsyncSession,
        row: CreationDraft,
        state: Creation,
    ) -> Creation:
        if not (state.name and state.race and state.character_class):
            return state
        allowed = await self._name_allowed(session, state.name)
        character_id = None
        if allowed:
            stats = resolve_combat_stats(state.character_class, 1, state.race)
            # Unique index arbitrates players racing for the same name. DO NOTHING
            # keeps the transaction usable to persist the loser's editable name page.
            character_id = await session.scalar(
                insert(Character)
                .values(
                    telegram_id=row.telegram_id,
                    server_id=row.server_id,
                    name=state.name,
                    race=state.race,
                    character_class=state.character_class,
                    stage=PROLOGUE,
                    ruleset_version=RULESET,
                    hp=stats.hp,
                    max_hp=stats.hp,
                )
                .on_conflict_do_nothing()
                .returning(Character.id)
            )
        if character_id is None:
            self._save(
                row,
                replace(
                    state,
                    step="name",
                    editing=True,
                    error="unavailable",
                    rejected_name=state.name,
                ),
            )
            return self.snapshot(row)
        self._save(row, replace(state, step="completed", editing=False))
        return Creation(
            id=character_id,
            step=PROLOGUE,
            name=state.name,
            race=state.race,
            character_class=state.character_class,
        )
