"""Authoritative application service for S1: Luzes sob as Cinzas."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.campaign_objectives import (
    campaign_roster_ids,
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

S1_ID = "S1"
S1_TITLE = "Luzes sob as Cinzas"
S1_VERSION = "tdo-1.0.3"
P1_ID = "P1"
ROAD = "Estrada das Cinzas"
REFUGE = "Refúgio do Ocaso"
REGION = "Terras do Ocaso"
CODEX_ROAD = "codex.location.estrada_das_cinzas"
LIGHTS_FRAGMENT = "codex.fragment.estrada.luzes_na_estrada"
REWARD_SOURCE = "s1.luzes_sob_as_cinzas"


@dataclass(frozen=True)
class S1View:
    kind: str
    character_id: UUID
    status: str
    step: int
    state_version: int
    progress: dict
    tracked: bool
    location: str
    level: int
    available: bool = False
    reacceptable: bool = False
    fragment_owned: bool = False
    fragment_new_this_attempt: bool = False


class S1Service:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id

    async def resume(self, actor: int) -> S1View | None:
        async with self.sessions() as session:
            c = await self._character(session, actor)
            if c is None:
                return None
            q = await self._quest(session, c.id)
            world = await self._world(session, c.id)
            if world is None or q is None or q.status != "active":
                return None
            return await self._view(session, c, q, world, "detail")

    async def oren(self, actor: int) -> S1View | None:
        async with self.sessions() as session:
            c = await self._character(session, actor)
            if c is None or await self._foreground(session, c.id):
                return None
            world = await self._world(session, c.id)
            if world is None or world.location != REFUGE:
                return None
            if not await self._p1_completed(session, c.id):
                return None
            q = await self._quest(session, c.id)
            return await self._view(session, c, q, world, "oren")

    async def offer(self, actor: int) -> S1View | None:
        async with self.sessions() as session:
            c = await self._character(session, actor)
            if c is None or await self._foreground(session, c.id):
                return None
            world = await self._world(session, c.id)
            if (
                world is None
                or world.location != REFUGE
                or not await self._p1_completed(session, c.id)
            ):
                return None
            q = await self._quest(session, c.id)
            available = c.level >= 2 and q is None
            reacceptable = bool(q and q.status == "abandoned" and c.level >= 2)
            if not (available or reacceptable):
                return await self._view(session, c, q, world, "oren")
            return await self._view(session, c, q, world, "offer")

    async def accept(self, actor: int, *, reaccept: bool = False) -> S1View | None:
        async with self.sessions.begin() as session:
            c = await self._locked_character(session, actor)
            if c is None or await self._foreground(session, c.id):
                return None
            world = await self._locked_world(session, c.id)
            if (
                world is None
                or world.location != REFUGE
                or c.level < 2
                or not await self._p1_completed(session, c.id)
            ):
                q = await self._quest(session, c.id)
                return await self._view(session, c, q, world, "oren") if world else None

            q = await self._locked_quest(session, c.id)
            if reaccept:
                if q is None or q.status != "abandoned":
                    return await self._view(session, c, q, world, "detail")
                q.status = "active"
                q.step = 1
                q.progress = {"points": []}
                q.state_version += 1
            else:
                if q is not None:
                    return await self._view(session, c, q, world, "detail")
                q = Quest(
                    character_id=c.id,
                    quest_id=S1_ID,
                    title=S1_TITLE,
                    status="active",
                    step=1,
                    content_version=S1_VERSION,
                    progress={"points": []},
                )
                session.add(q)
                await session.flush()
            return await self._view(session, c, q, world, "detail")

    async def toggle_tracking(self, actor: int, version: int) -> S1View | None:
        async with self.sessions.begin() as session:
            c, q, world = await self._locked_state(session, actor)
            if c is None or q is None or world is None:
                return None
            if not self._valid_active(q, version) or await self._foreground(session, c.id):
                return await self._view(session, c, q, world, "detail")
            c.tracked_secondary_quest_id = (
                None if c.tracked_secondary_quest_id == S1_ID else S1_ID
            )
            q.state_version += 1
            return await self._view(session, c, q, world, "detail")

    async def objective(self, actor: int) -> S1View | None:
        async with self.sessions() as session:
            c = await self._character(session, actor)
            if c is None or await self._foreground(session, c.id):
                return None
            q = await self._quest(session, c.id)
            world = await self._world(session, c.id)
            if q is None or q.status != "active" or world is None:
                return None
            return await self._view(session, c, q, world, "objective")

    async def investigate_point(self, actor: int, point: int, version: int) -> S1View | None:
        async with self.sessions.begin() as session:
            c, q, world = await self._locked_coop_state(session, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid_active(q, version, 1)
                or world.location != ROAD
                or point not in {1, 2, 3}
                or await self._foreground(session, c.id)
            ):
                return await self._view(session, c, q, world, "objective")
            members = await self._present_objective_members(
                session, c.id, step=1, location=ROAD
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                points = {
                    int(value)
                    for value in progress.get("points", [])
                    if int(value) in {1, 2, 3}
                }
                if point in points:
                    continue
                points.add(point)
                progress["points"] = sorted(points)
                if len(points) == 3:
                    member.quest.step = 2
                member.quest.progress = progress
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=S1_ID,
                    objective_id="s1.signal",
                    source_key=f"s1.signal:{point}",
                    evidence={"point": point, "location": ROAD},
                )
            return await self._view(session, c, q, world, "objective")

    async def examine_ashes(self, actor: int, version: int) -> S1View | None:
        async with self.sessions.begin() as session:
            c, q, world = await self._locked_coop_state(session, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid_active(q, version, 2)
                or world.location != ROAD
                or await self._foreground(session, c.id)
            ):
                return await self._view(session, c, q, world, "objective")
            for member in await self._present_objective_members(
                session, c.id, step=2, location=ROAD
            ):
                progress = dict(member.quest.progress or {})
                if progress.get("ashes_examined"):
                    continue
                progress["ashes_examined"] = True
                member.quest.progress = progress
                member.quest.step = 3
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=S1_ID,
                    objective_id="s1.ashes",
                    source_key="s1.ashes:examined",
                    evidence={"location": ROAD},
                )
            return await self._view(session, c, q, world, "objective")

    async def observe_light(self, actor: int, version: int) -> S1View | None:
        async with self.sessions.begin() as session:
            c, q, world = await self._locked_coop_state(session, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid_active(q, version, 3)
                or world.location != ROAD
                or await self._foreground(session, c.id)
            ):
                return await self._view(session, c, q, world, "objective")
            for member in await self._present_objective_members(
                session, c.id, step=3, location=ROAD
            ):
                progress = dict(member.quest.progress or {})
                if progress.get("light_observed"):
                    continue
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=member.character.id,
                    entry_id=CODEX_ROAD,
                )
                fragment_new = await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=CODEX_ROAD,
                    fragment_id=LIGHTS_FRAGMENT,
                )
                progress["light_observed"] = True
                progress["fragment_new_this_attempt"] = bool(fragment_new)
                member.quest.progress = progress
                member.quest.step = 4
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=S1_ID,
                    objective_id="s1.light",
                    source_key="s1.light:observed",
                    evidence={"location": ROAD, "codex_entry": CODEX_ROAD},
                )
            return await self._view(session, c, q, world, "objective")

    async def complete_with_oren(self, actor: int, version: int) -> S1View | None:
        async with self.sessions.begin() as session:
            c, q, world = await self._locked_state(session, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid_active(q, version, 4)
                or world.location != REFUGE
                or await self._foreground(session, c.id)
            ):
                return await self._view(session, c, q, world, "oren")
            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == c.id,
                    RewardEvent.source_id == REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                event = RewardEvent(character_id=c.id, source_id=REWARD_SOURCE)
                session.add(event)
                await session.flush()
                c.xp += 1140
                c.crowns += 60
                session.add_all(
                    [
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="xp",
                            item_id=None,
                            quantity=1140,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="crowns",
                            item_id=None,
                            quantity=60,
                        ),
                    ]
                )
            await self._ensure(
                session,
                CodexEntry,
                character_id=c.id,
                entry_id=CODEX_ROAD,
            )
            q.status = "completed"
            q.state_version += 1
            progress = dict(q.progress or {})
            progress["completed"] = True
            q.progress = progress
            if c.tracked_secondary_quest_id == S1_ID:
                c.tracked_secondary_quest_id = None
            await consolidate_character_level(session, c)
            return await self._view(session, c, q, world, "completed")

    async def abandon(self, actor: int, version: int) -> S1View | None:
        async with self.sessions.begin() as session:
            c, q, world = await self._locked_state(session, actor)
            if c is None or q is None or world is None:
                return None
            if not self._valid_active(q, version) or await self._foreground(session, c.id):
                return await self._view(session, c, q, world, "detail")
            q.status = "abandoned"
            q.step = 1
            q.progress = {}
            q.state_version += 1
            if c.tracked_secondary_quest_id == S1_ID:
                c.tracked_secondary_quest_id = None
            return await self._view(session, c, q, world, "abandoned")

    async def abandon_confirmation(self, actor: int) -> S1View | None:
        async with self.sessions() as session:
            c = await self._character(session, actor)
            if c is None or await self._foreground(session, c.id):
                return None
            q = await self._quest(session, c.id)
            world = await self._world(session, c.id)
            if q is None or q.status != "active" or world is None:
                return None
            return await self._view(session, c, q, world, "abandon_confirm")

    async def _view(
        self,
        session: AsyncSession,
        c: Character,
        q: Quest | None,
        world: WorldState,
        kind: str,
    ) -> S1View:
        p1_completed = await self._p1_completed(session, c.id)
        available = bool(p1_completed and c.level >= 2 and q is None)
        reacceptable = bool(p1_completed and c.level >= 2 and q and q.status == "abandoned")
        fragment_owned = bool(
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == c.id,
                    CodexFragment.fragment_id == LIGHTS_FRAGMENT,
                )
            )
        )
        status = q.status if q else "unaccepted"
        step = q.step if q else 1
        version = q.state_version if q else 0
        progress = dict(q.progress or {}) if q else {}
        tracked = bool(q and q.status == "active" and c.tracked_secondary_quest_id == S1_ID)
        return S1View(
            kind=kind,
            character_id=c.id,
            status=status,
            step=step,
            state_version=version,
            progress=progress,
            tracked=tracked,
            location=world.location,
            level=c.level,
            available=available,
            reacceptable=reacceptable,
            fragment_owned=fragment_owned,
            fragment_new_this_attempt=bool(progress.get("fragment_new_this_attempt")),
        )

    async def _locked_state(self, session: AsyncSession, actor: int):
        c = await self._locked_character(session, actor)
        if c is None:
            return None, None, None
        q = await self._locked_quest(session, c.id)
        world = await self._locked_world(session, c.id)
        return c, q, world

    async def _locked_coop_state(self, session: AsyncSession, actor: int):
        seed = await self._character(session, actor)
        if seed is None:
            return None, None, None
        await lock_campaign_roster(session, seed.id)
        return await self._locked_state(session, actor)

    async def _present_objective_members(
        self,
        session: AsyncSession,
        character_id: UUID,
        *,
        step: int,
        location: str,
    ):
        roster_ids = await campaign_roster_ids(session, character_id)
        return await present_campaign_members(
            session,
            character_ids=roster_ids,
            quest_id=S1_ID,
            content_version=S1_VERSION,
            step=step,
            region=REGION,
            location=location,
        )

    async def _character(self, session: AsyncSession, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _locked_character(self, session: AsyncSession, actor: int) -> Character | None:
        return await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
            .with_for_update()
        )

    async def _quest(self, session: AsyncSession, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == S1_ID,
            )
        )

    async def _locked_quest(self, session: AsyncSession, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id == S1_ID,
            )
            .with_for_update()
        )

    async def _world(self, session: AsyncSession, character_id: UUID) -> WorldState | None:
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )

    async def _locked_world(self, session: AsyncSession, character_id: UUID) -> WorldState | None:
        return await session.scalar(
            select(WorldState)
            .where(WorldState.character_id == character_id)
            .with_for_update()
        )

    async def _p1_completed(self, session: AsyncSession, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P1_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _foreground(self, session: AsyncSession, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == character_id,
                    GameActivity.status == "active",
                )
            )
        )

    @staticmethod
    def _valid_active(q: Quest, version: int, step: int | None = None) -> bool:
        return bool(
            q.status == "active"
            and q.content_version == S1_VERSION
            and q.state_version == version
            and (step is None or q.step == step)
        )

    async def _ensure(self, session: AsyncSession, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        return True
