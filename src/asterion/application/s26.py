"""Persistent secondary quest S26: Turno sem Fim."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import (
    S26_CODEX_ENTRY,
    S26_CONTENT_VERSION,
    S26_ID,
    S26_REWARD_SOURCE,
    S26_TITLE,
)
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import ALTOS_ABRIGO_LABEL, ALTOS_PONTES_LABEL
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

if TYPE_CHECKING:
    from asterion.application.altos_missions import AltosMissionService

ALTOS_REGION = "Altos Cinéreos"
P26_ID = "P26"
S26_XP_REWARD = 42_070
S26_CROWNS_REWARD = 570
S26_COURO_ESCARPA = "material.altos.couro_escarpa"
S26_LIQUEN_PEDREIRA = "material.altos.liquen_pedreira"
S26_LOCATIONS = (ALTOS_ABRIGO_LABEL, ALTOS_PONTES_LABEL)
S26_SHIFT_MARKER_COUNT = 3


@dataclass(frozen=True)
class S26View:
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


class S26Service:
    """Per-character S26 progress and rewards, using Altos' shared combat engine."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        combat: AltosMissionService,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.combat = combat

    async def giver(self, actor: int) -> S26View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_s26_location(world) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S26View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_s26_location(world) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S26View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_s26_location(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S26View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None or quest.status != "active":
                return None
        combat_view = await self.combat.resume(actor, S26_ID)
        if combat_view is not None and combat_view.kind == "combat":
            return combat_view
        return await self.resume(actor)

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S26View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            await lock_campaign_roster(session, seed.id)
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            world = await self._locked_world(session, character.id)
            quest = await self._locked_quest(session, character.id)
            eligible = bool(
                self._at_s26_location(world)
                and not await self._foreground(session, character.id)
                and character.level >= 44
                and await self._p26_completed(session, character.id)
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
                quest.content_version = S26_CONTENT_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S26_ID,
                    title=S26_TITLE,
                    status="active",
                    step=1,
                    content_version=S26_CONTENT_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S26View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "objective")

    async def advance(self, actor: int, version: int, action: str) -> S26View | None:
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
                not self._at_s26_location(world)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "objective")

            if quest.step == 1 and action == "receive_shift_marks":
                progress = dict(quest.progress or {})
                progress["shift_markers_received"] = S26_SHIFT_MARKER_COUNT
                quest.progress = progress
                quest.step = 2
                quest.state_version += 1
                await self._credit(
                    session,
                    character.id,
                    "s26.received_shift_markers",
                    f"s26.received_shift_markers:{character.id}",
                    {"giver": "Hesa Tor", "marker_count": S26_SHIFT_MARKER_COUNT},
                )
            elif quest.step == 2 and action == "accompany_rescue_team":
                members = await self._present(session, character_ids, 2, world.location)
                for member in members:
                    member_progress = dict(member.quest.progress or {})
                    if member_progress.get("rescue_team_accompanied"):
                        continue
                    member_progress["rescue_team_accompanied"] = True
                    member.quest.progress = member_progress
                    member.quest.step = 3
                    member.quest.state_version += 1
                    await self._credit(
                        session,
                        member.character.id,
                        "s26.accompanied_rescue_team",
                        f"s26.accompanied_rescue_team:{member.character.id}",
                        {"location": world.location, "persistent_npc_created": False},
                    )
                quest = await self._locked_quest(session, character.id)
            elif quest.step == 4 and action == "find_old_shift_record":
                members = await self._present(session, character_ids, 4, world.location)
                for member in members:
                    member_progress = dict(member.quest.progress or {})
                    if member_progress.get("old_shift_record_found"):
                        continue
                    member_progress["old_shift_record_found"] = True
                    member.quest.progress = member_progress
                    member.quest.step = 5
                    member.quest.state_version += 1
                    await self._credit(
                        session,
                        member.character.id,
                        "s26.found_old_shift_record",
                        f"s26.found_old_shift_record:{member.character.id}",
                        {"location": world.location},
                    )
                quest = await self._locked_quest(session, character.id)
            elif quest.step == 5 and action == "discuss_heroism_and_exploitation":
                progress = dict(quest.progress or {})
                progress["discussed_with_hesa"] = True
                progress["conclusion"] = "heroism_and_institutional_exploitation_coexist"
                quest.progress = progress
                quest.step = 6
                quest.state_version += 1
                await self._credit(
                    session,
                    character.id,
                    "s26.concluded_with_hesa",
                    f"s26.concluded_with_hesa:{character.id}",
                    {"conclusion": "heroism_and_institutional_exploitation_coexist"},
                )
            elif (
                quest.step == 6
                and action == "record_codex"
                and (quest.progress or {}).get("discussed_with_hesa")
            ):
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=S26_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S26_CODEX_ENTRY,
                    fragment_id=S26_CODEX_ENTRY,
                )
                progress = dict(quest.progress or {})
                progress["codex_recorded"] = True
                await self._complete(session, character, quest, progress)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "detail")

    async def toggle_tracking(self, actor: int, version: int) -> S26View | None:
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
                None if character.tracked_secondary_quest_id == S26_ID else S26_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S26View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S26View | None:
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
            if character.tracked_secondary_quest_id == S26_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character, quest, progress: dict) -> None:
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S26_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S26_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S26_XP_REWARD
            character.crowns += S26_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        quantity=S26_XP_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        quantity=S26_CROWNS_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S26_COURO_ESCARPA,
                        quantity=1,
                        payload={"material_id": S26_COURO_ESCARPA, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S26_LIQUEN_PEDREIRA,
                        quantity=1,
                        payload={"material_id": S26_LIQUEN_PEDREIRA, "bound": True},
                    ),
                )
            )
            await self.combat.road.deliver_material(
                session,
                character,
                S26_COURO_ESCARPA,
                1,
                f"{S26_REWARD_SOURCE}:material:couro_escarpa",
                bound=True,
            )
            await self.combat.road.deliver_material(
                session,
                character,
                S26_LIQUEN_PEDREIRA,
                1,
                f"{S26_REWARD_SOURCE}:material:liquen_pedreira",
                bound=True,
            )
        quest.status = "completed"
        quest.state_version += 1
        progress["completed"] = True
        quest.progress = progress
        if character.tracked_secondary_quest_id == S26_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S26View:
        eligible = bool(
            self._at_s26_location(world)
            and character.level >= 44
            and await self._p26_completed(session, character.id)
        )
        status = quest.status if quest is not None else "unaccepted"
        progress = dict(quest.progress or {}) if quest is not None else {}
        codex_owned = bool(
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character.id,
                    CodexFragment.fragment_id == S26_CODEX_ENTRY,
                )
            )
        )
        return S26View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(eligible and (quest is None or status == "abandoned")),
            reacceptable=bool(
                eligible and quest is not None and status == "abandoned"
            ),
            tracked=bool(
                quest is not None
                and quest.status == "active"
                and character.tracked_secondary_quest_id == S26_ID
            ),
            codex_owned=codex_owned,
        )

    async def _present(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=S26_ID,
            content_version=S26_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _credit(self, session, character_id, objective_id, source_key, evidence):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S26_ID,
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
                Quest.quest_id == S26_ID,
            )
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id == S26_ID,
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

    async def _p26_completed(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P26_ID,
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
    def _at_s26_location(world: WorldState | None) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION
            and world.location in S26_LOCATIONS
        )

    @staticmethod
    def _valid_active(quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S26_CONTENT_VERSION
            and quest.state_version == version
        )

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True
