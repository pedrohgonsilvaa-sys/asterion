"""Authoritative state transitions for P1's first three stages."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.domain.combat import Combat
from asterion.domain.prologue import P1_CONTENT_ID, p1_combat_profile
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    Encounter,
    GameActivity,
    Quest,
)

P1_ID = "P1"
P1_VERSION = "tdo-1.0.2"


@dataclass(frozen=True)
class P1View:
    character_id: UUID
    step: int
    state_version: int
    progress: dict
    combat: Combat | None = None


class P1Service:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id

    async def resume(self, actor: int) -> P1View | None:
        async with self.sessions() as session:
            c = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if c is None:
                return None
            q = await session.scalar(
                select(Quest).where(Quest.character_id == c.id, Quest.quest_id == P1_ID)
            )
            if q is None or q.content_version != P1_VERSION:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id,
                    GameActivity.content_id == P1_CONTENT_ID,
                    GameActivity.status == "active",
                )
            )
            combat = None
            if activity is not None:
                encounter, record = (
                    await session.execute(
                        select(Encounter, CombatRecord)
                        .join(CombatRecord)
                        .where(Encounter.game_activity_id == activity.id)
                    )
                ).one()
                combat = decode(
                    record.snapshot, record.id, activity.ruleset_version, activity.state_version
                )
            return P1View(c.id, q.step, q.state_version, q.progress or {}, combat)

    async def follow_road(self, actor: int, version: int) -> P1View | None:
        return await self._advance(actor, version, lambda q: (q.step == 1, setattr(q, "step", 2)))

    async def examine(self, actor: int, signal: str, version: int) -> P1View | None:
        async with self.sessions.begin() as session:
            c = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            q = (
                await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == c.id, Quest.quest_id == P1_ID)
                    .with_for_update()
                )
                if c
                else None
            )
            if (
                c is None
                or q is None
                or q.content_version != P1_VERSION
                or q.step != 2
                or q.state_version != version
            ):
                return await self._view_in_session(session, c, q)
            progress = dict(q.progress or {})
            if signal == "pegadas":
                progress["pegadas"] = True
            elif signal == "sulcos" and progress.get("pegadas"):
                progress["sulcos"] = True
                q.step = 3
                state = p1_combat_profile(uuid4(), c.name, c.character_class, c.race, c.hp)
                repo = CombatRepository(session)
                await repo.create(c, P1_CONTENT_ID, state)
            else:
                return await self._view_in_session(session, c, q)
            q.progress, q.state_version = progress, q.state_version + 1
            return await self._view_in_session(session, c, q)

    async def _advance(self, actor, version, operation):
        async with self.sessions.begin() as session:
            c = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            q = (
                await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == c.id, Quest.quest_id == P1_ID)
                    .with_for_update()
                )
                if c
                else None
            )
            if (
                c is None
                or q is None
                or q.content_version != P1_VERSION
                or q.state_version != version
            ):
                return await self._view_in_session(session, c, q)
            valid, _ = operation(q)
            if valid:
                q.step += 1
                q.state_version += 1
            return await self._view_in_session(session, c, q)

    async def _view_in_session(self, session, c, q):
        if c is None or q is None:
            return None
        return P1View(c.id, q.step, q.state_version, q.progress or {})
