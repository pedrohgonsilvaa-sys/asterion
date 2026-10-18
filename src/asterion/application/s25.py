"""Persistent secondary quest S25: A Ponte que Espera."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.progression import consolidate_character_level
from asterion.application.road import ALTOS_ESCARPA_LABEL
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

S25_ID = "S25"
S25_MISSION_ID = "mission.altos.s25"
S25_TITLE = "A Ponte que Espera"
S25_CONTENT_VERSION = "altos-1.0.1"
S25_REWARD_SOURCE = S25_MISSION_ID
S25_CODEX_ENTRY = "codex.altos.infraestrutura_sustentacao"
S25_CODEX_FRAGMENT = "codex.fragment.altos.autorizacao_que_nunca_veio"
S25_XP_REWARD = 22_280
S25_CROWNS_REWARD = 370
P25_ID = "P25"
ALTOS_REGION = "Altos Cinéreos"

_STEP_ACTIONS = {
    1: ("inspect_bridge", "bridge_examined"),
    2: ("locate_seal", "authorization_seal_found"),
    3: ("compare_orders", "waiting_orders_compared"),
    4: ("verify_structure", "bridge_structure_verified"),
    5: ("return_to_doren", "returned_to_doren"),
}


@dataclass(frozen=True)
class S25View:
    character_id: UUID
    kind: str
    status: str
    step: int
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    reacceptable: bool = False
    tracked: bool = False
    fragment_owned: bool = False
    fragment_new_this_attempt: bool = False


class S25Service:
    """Per-character S25 state, evidence, one-time reward, and reacceptance."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id

    async def doren(self, actor: int) -> S25View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_escarpa(world) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S25View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_escarpa(world) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S25View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_escarpa(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S25View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "detail")

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S25View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            world = await self._locked_world(session, character.id)
            quest = await self._locked_quest(session, character.id)
            if (
                not self._at_escarpa(world)
                or await self._foreground(session, character.id)
                or character.level < 42
                or not await self._p25_completed(session, character.id)
            ):
                return await self._view(session, character, quest, world, "giver")

            if reaccept:
                if (
                    quest is None
                    or quest.status != "abandoned"
                    or quest.state_version != version
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest.status = "active"
                quest.step = 1
                quest.progress = {}
                quest.content_version = S25_CONTENT_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S25_ID,
                    title=S25_TITLE,
                    status="active",
                    step=1,
                    content_version=S25_CONTENT_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S25View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None:
                return None
            return await self._view(session, character, quest, world, "objective")

    async def advance(self, actor: int, version: int, action: str) -> S25View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if not self._valid_active(quest, version):
                return await self._view(session, character, quest, world, "detail")
            if (
                not self._at_escarpa(world)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "objective")

            if quest.step in _STEP_ACTIONS:
                expected_action, progress_key = _STEP_ACTIONS[quest.step]
                if action != expected_action:
                    return await self._view(session, character, quest, world, "objective")
                progress = dict(quest.progress or {})
                if progress.get(progress_key):
                    return await self._view(session, character, quest, world, "objective")
                progress[progress_key] = True
                quest.progress = progress
                quest.step += 1
                quest.state_version += 1
                return await self._view(session, character, quest, world, "detail")

            if quest.step != 6 or action != "record_codex":
                return await self._view(session, character, quest, world, "objective")

            progress = dict(quest.progress or {})
            if not progress.get("returned_to_doren"):
                return await self._view(session, character, quest, world, "objective")
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=S25_CODEX_ENTRY,
            )
            fragment_new = await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id=S25_CODEX_ENTRY,
                fragment_id=S25_CODEX_FRAGMENT,
            )
            progress["codex_recorded"] = True
            progress["fragment_new_this_attempt"] = fragment_new
            await self._complete(session, character, quest, progress)
            await consolidate_character_level(session, character)
            return await self._view(session, character, quest, world, "completed")

    async def toggle_tracking(self, actor: int, version: int) -> S25View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if (
                not self._valid_active(quest, version)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "detail")
            character.tracked_secondary_quest_id = (
                None
                if character.tracked_secondary_quest_id == S25_ID
                else S25_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S25View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S25View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if (
                not self._valid_active(quest, version)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "detail")
            quest.status = "abandoned"
            quest.step = 1
            quest.progress = {}
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S25_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character, quest, progress: dict) -> None:
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S25_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(
                character_id=character.id,
                source_id=S25_REWARD_SOURCE,
            )
            session.add(event)
            await session.flush()
            character.xp += S25_XP_REWARD
            character.crowns += S25_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        quantity=S25_XP_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        quantity=S25_CROWNS_REWARD,
                    ),
                )
            )
        quest.status = "completed"
        quest.state_version += 1
        progress["completed"] = True
        quest.progress = progress
        if character.tracked_secondary_quest_id == S25_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S25View:
        eligible = bool(
            self._at_escarpa(world)
            and character.level >= 42
            and await self._p25_completed(session, character.id)
        )
        status = quest.status if quest is not None else "unaccepted"
        available = bool(eligible and (quest is None or status == "abandoned"))
        reacceptable = bool(eligible and quest is not None and status == "abandoned")
        fragment_owned = bool(
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character.id,
                    CodexFragment.fragment_id == S25_CODEX_FRAGMENT,
                )
            )
        )
        progress = dict(quest.progress or {}) if quest is not None else {}
        return S25View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=available,
            reacceptable=reacceptable,
            tracked=bool(
                quest is not None
                and quest.status == "active"
                and character.tracked_secondary_quest_id == S25_ID
            ),
            fragment_owned=fragment_owned,
            fragment_new_this_attempt=bool(progress.get("fragment_new_this_attempt")),
        )

    async def _character(self, session, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _locked_character(self, session, actor: int) -> Character | None:
        return await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
            .with_for_update()
        )

    async def _quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == S25_ID,
            )
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id == S25_ID,
            )
            .with_for_update()
        )

    async def _world(self, session, character_id: UUID) -> WorldState | None:
        return await session.get(WorldState, character_id)

    async def _locked_world(self, session, character_id: UUID) -> WorldState | None:
        return await session.scalar(
            select(WorldState)
            .where(WorldState.character_id == character_id)
            .with_for_update()
        )

    async def _p25_completed(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P25_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _foreground(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == character_id,
                    GameActivity.status == "active",
                )
            )
        )

    @staticmethod
    def _at_escarpa(world: WorldState | None) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION
            and world.location == ALTOS_ESCARPA_LABEL
        )

    @staticmethod
    def _valid_active(quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S25_CONTENT_VERSION
            and quest.state_version == version
        )

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True
