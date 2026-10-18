"""Persistent secondary quest S27: Cabo Partido."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import P27_ID
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import ALTOS_PEDREIRAS_LABEL, RoadService
from asterion.domain.road import ALTOS_PEDREIRAS_ACCESS_UNLOCK
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

S27_ID = "S27"
S27_MISSION_ID = "mission.altos.s27"
S27_TITLE = "Cabo Partido"
S27_CONTENT_VERSION = "altos-1.0.1"
S27_REWARD_SOURCE = S27_MISSION_ID
S27_CODEX_ENTRY = "codex.altos.reparo_redundante"
S27_XP_REWARD = 24_960
S27_CROWNS_REWARD = 390
S27_FERRO_CONTRAPESO = "material.altos.ferro_contrapeso"
S27_COURO_ESCARPA = "material.altos.couro_escarpa"
ALTOS_REGION = "Altos Cinéreos"

_ACTIONS = {
    1: ("inspect_broken_cable", "old_cable_inspected"),
    2: ("confirm_full_rebuild_unneeded", "full_rebuild_not_needed"),
    3: ("validate_redundant_repair", "modern_redundant_repair_validated"),
    4: ("cross_repaired_route", "repaired_route_crossed"),
    5: ("return_to_doren", "returned_to_doren"),
}
_SHARED_STEPS = frozenset({1, 3, 4})


@dataclass(frozen=True)
class S27View:
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
    codex_owned: bool = False


class S27Service:
    """Per-character S27 progress, physical evidence, Codex, and reward."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        road: RoadService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.road = road

    async def giver(self, actor: int) -> S27View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_pedreiras(world) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S27View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_pedreiras(world) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S27View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_pedreiras(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S27View | None:
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
    ) -> S27View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            world = await self._locked_world(session, character.id)
            quest = await self._locked_quest(session, character.id)
            eligible = bool(
                await self._eligible(session, character, world)
                and not await self._foreground(session, character.id)
            )
            if not eligible:
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
                quest.content_version = S27_CONTENT_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S27_ID,
                    title=S27_TITLE,
                    status="active",
                    step=1,
                    content_version=S27_CONTENT_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S27View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "objective")

    async def advance(self, actor: int, version: int, action: str) -> S27View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _group_id, character_ids = await lock_campaign_roster(session, seed.id)
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
                not self._at_pedreiras(world)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "objective")

            if quest.step in _ACTIONS:
                expected_action, progress_key = _ACTIONS[quest.step]
                if action != expected_action:
                    return await self._view(session, character, quest, world, "objective")
                if quest.step in _SHARED_STEPS:
                    members = await self._present(
                        session, character_ids, quest.step, world.location
                    )
                    if not any(member.character.id == character.id for member in members):
                        return await self._view(
                            session, character, quest, world, "objective"
                        )
                    for member in members:
                        member_progress = dict(member.quest.progress or {})
                        if member_progress.get(progress_key):
                            continue
                        member_progress[progress_key] = True
                        if quest.step == 3:
                            # Mission presentation only; no inventory or world state changes.
                            member_progress["narrative_material_cost"] = 0
                            member_progress["public_route_unlocked"] = False
                        member.quest.progress = member_progress
                        member.quest.step += 1
                        member.quest.state_version += 1
                        await self._credit(
                            session,
                            member.character.id,
                            f"s27.{progress_key}",
                            f"s27.{progress_key}:{member.quest.state_version}",
                            {
                                "location": world.location,
                                "personal_world_state_changed": False,
                                "shared_physical_evidence": True,
                            },
                        )
                    quest = await self._locked_quest(session, character.id)
                else:
                    progress = dict(quest.progress or {})
                    progress[progress_key] = True
                    quest.progress = progress
                    quest.step += 1
                    quest.state_version += 1
                    await self._credit(
                        session,
                        character.id,
                        f"s27.{progress_key}",
                        f"s27.{progress_key}:{quest.state_version}",
                        {"location": world.location, "personal_evidence": True},
                    )
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
                entry_id=S27_CODEX_ENTRY,
            )
            await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id=S27_CODEX_ENTRY,
                fragment_id=S27_CODEX_ENTRY,
            )
            progress["codex_recorded"] = True
            await self._credit(
                session,
                character.id,
                "s27.recorded_codex",
                f"s27.recorded_codex:{quest.state_version + 1}",
                {"codex_entry": S27_CODEX_ENTRY, "personal_evidence": True},
            )
            await self._complete(session, character, quest, progress)
            await consolidate_character_level(session, character)
            return await self._view(session, character, quest, world, "completed")

    async def toggle_tracking(self, actor: int, version: int) -> S27View | None:
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
                None if character.tracked_secondary_quest_id == S27_ID else S27_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S27View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S27View | None:
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
            if character.tracked_secondary_quest_id == S27_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character, quest, progress: dict) -> None:
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S27_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S27_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S27_XP_REWARD
            character.crowns += S27_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        quantity=S27_XP_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        quantity=S27_CROWNS_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S27_FERRO_CONTRAPESO,
                        quantity=1,
                        payload={"material_id": S27_FERRO_CONTRAPESO, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S27_COURO_ESCARPA,
                        quantity=1,
                        payload={"material_id": S27_COURO_ESCARPA, "bound": True},
                    ),
                )
            )
            await self.road.deliver_material(
                session,
                character,
                S27_FERRO_CONTRAPESO,
                1,
                f"{S27_REWARD_SOURCE}:material:ferro_contrapeso",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                S27_COURO_ESCARPA,
                1,
                f"{S27_REWARD_SOURCE}:material:couro_escarpa",
                bound=True,
            )
        quest.status = "completed"
        quest.state_version += 1
        progress["completed"] = True
        quest.progress = progress
        if character.tracked_secondary_quest_id == S27_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S27View:
        eligible = await self._eligible(session, character, world)
        status = quest.status if quest is not None else "unaccepted"
        progress = dict(quest.progress or {}) if quest is not None else {}
        codex_owned = bool(
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character.id,
                    CodexFragment.fragment_id == S27_CODEX_ENTRY,
                )
            )
        )
        return S27View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(eligible and (quest is None or status == "abandoned")),
            reacceptable=bool(eligible and quest is not None and status == "abandoned"),
            tracked=bool(
                quest is not None
                and quest.status == "active"
                and character.tracked_secondary_quest_id == S27_ID
            ),
            codex_owned=codex_owned,
        )

    async def _eligible(self, session, character, world) -> bool:
        if (
            character.level < 45
            or not self._at_pedreiras(world)
            or not await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == ALTOS_PEDREIRAS_ACCESS_UNLOCK,
                )
            )
        ):
            return False
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == P27_ID,
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    async def _present(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=S27_ID,
            content_version=S27_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _credit(self, session, character_id, objective_id, source_key, evidence):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S27_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
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
                Quest.quest_id == S27_ID,
            )
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id == S27_ID,
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
    def _at_pedreiras(world: WorldState | None) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION
            and world.location == ALTOS_PEDREIRAS_LABEL
        )

    @staticmethod
    def _valid_active(quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S27_CONTENT_VERSION
            and quest.state_version == version
        )

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True
