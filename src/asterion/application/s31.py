"""Persistent secondary quest S31: Duas Vezes a Mesma Estrada."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import (
    P31_CONTENT_VERSION,
    P31_ID,
    S31_ID,
    AltosMissionService,
)
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import CONFINS_MARCHA_LABEL, CONFINS_REGION_LABEL
from asterion.infrastructure.db.models import (
    CampaignObjectiveCredit,
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

S31_MISSION_ID = "mission.confins.s31"
S31_TITLE = "Duas Vezes a Mesma Estrada"
S31_CONTENT_VERSION = "confins-1.0.0"
S31_REWARD_SOURCE = S31_MISSION_ID
S31_CODEX_ENTRY = "codex.confins.pegadas_incompativeis"
S31_CODEX_FRAGMENT = S31_CODEX_ENTRY
S31_COMPLETION_UNLOCK = "quest.confins.s31.completed"
S31_LEVEL = 52
S31_XP_REWARD = 31_860
S31_CROWNS_REWARD = 440
S31_TRAIL_POINTS = (
    "evidence.confins.s31.trail_point_a",
    "evidence.confins.s31.trail_point_b",
    "evidence.confins.s31.trail_point_c",
)
S31_IMPRESSIONS = (
    "evidence.confins.s31.impression_reading_a",
    "evidence.confins.s31.impression_reading_b",
)

_TRAIL_ACTIONS = {
    "observe_trail_point_a": S31_TRAIL_POINTS[0],
    "observe_trail_point_b": S31_TRAIL_POINTS[1],
    "observe_trail_point_c": S31_TRAIL_POINTS[2],
}
_IMPRESSION_ACTIONS = {
    "record_impression_reading_a": S31_IMPRESSIONS[0],
    "record_impression_reading_b": S31_IMPRESSIONS[1],
}


@dataclass(frozen=True, slots=True)
class S31View:
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
    action_available: bool = False
    gate_satisfied: bool = False
    trail_points: tuple[str, ...] = ()
    impressions: tuple[str, ...] = ()
    victory_recorded: bool = False
    codex_owned: bool = False


class S31Service:
    """Per-character mission state, shared physical evidence, and one-time reward."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        altos_missions: AltosMissionService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.altos_missions = altos_missions

    async def giver(self, actor: int) -> S31View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_marcha(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S31View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_marcha(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S31View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_marcha(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S31View | object | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            active_combat = await self._active_combat(session, character.id)
            world = await self._world(session, character.id)
            if active_combat is not None:
                return await self.altos_missions.resume(actor, S31_ID)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int) -> S31View | object | None:
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S31View | None:
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
            if (
                not await self._eligible_at_marcha(session, character, world)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "giver")
            if reaccept:
                if (
                    quest is None
                    or quest.status != "abandoned"
                    or quest.state_version != version
                    or quest.content_version != S31_CONTENT_VERSION
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest.status = "active"
                quest.step = await self._next_step(session, character.id)
                quest.content_version = S31_CONTENT_VERSION
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S31_ID,
                    title=S31_TITLE,
                    status="active",
                    step=2,
                    content_version=S31_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed_steps": [1], "survey_accepted": True},
                )
                session.add(quest)
                await session.flush()
                await self._credit(
                    session,
                    character.id,
                    "s31.survey_accepted",
                    "s31.survey_accepted",
                    {"giver": "Talen Nyr", "location_id": "location.confins.marcha_nebulosa"},
                )
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S31View | object | None:
        return await self.resume(actor)

    async def advance(self, actor: int, version: int, action: str):
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
            if await self._foreground(session, character.id):
                return await self._view(session, character, quest, world, "objective")
            if not await self._eligible_at_marcha(session, character, world):
                return await self._view(session, character, quest, world, "objective")

            if quest.step == 2 and action in _TRAIL_ACTIONS:
                await self._share_evidence(
                    session,
                    character_ids,
                    quest_step=2,
                    objective_id="s31.trail_point",
                    source_key=_TRAIL_ACTIONS[action],
                    evidence={"physical_trail_point": True, "shared_evidence": True},
                )
                return await self._refresh_actor_view(
                    session, character.id, world, "detail"
                )

            if quest.step == 3 and action in _IMPRESSION_ACTIONS:
                await self._share_evidence(
                    session,
                    character_ids,
                    quest_step=3,
                    objective_id="s31.incompatible_impression",
                    source_key=_IMPRESSION_ACTIONS[action],
                    evidence={
                        "physical_impression": True,
                        "pass_count_comparison": "different_counts",
                        "shared_evidence": True,
                        "does_not_prove_clones_or_time_travel": True,
                    },
                )
                return await self._refresh_actor_view(
                    session, character.id, world, "detail"
                )

            if quest.step == 5 and action == "compare_with_talen":
                if (
                    not set(S31_TRAIL_POINTS).issubset(
                        await self._trail_point_ids(session, character.id)
                    )
                    or not set(S31_IMPRESSIONS).issubset(
                        await self._impression_ids(session, character.id)
                    )
                    or not await self._has_credit(
                        session, character.id, "s31.gralha_defeated"
                    )
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=S31_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S31_CODEX_ENTRY,
                    fragment_id=S31_CODEX_FRAGMENT,
                )
                await self._credit(
                    session,
                    character.id,
                    "s31.codex_recorded",
                    "s31.codex_recorded",
                    {
                        "codex_entry": S31_CODEX_ENTRY,
                        "trail_point_ids": list(S31_TRAIL_POINTS),
                        "impression_ids": list(S31_IMPRESSIONS),
                        "preserves_both_readings": True,
                        "does_not_assert_conscious_duplicates": True,
                        "personal_evidence": True,
                    },
                )
                quest.step = 6
                quest.state_version += 1
                quest.progress = await self._progress_snapshot(session, character.id)
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 6 and action == "conclude_with_talen":
                if not await self._has_credit(session, character.id, "s31.codex_recorded"):
                    return await self._view(session, character, quest, world, "objective")
                await self._complete(session, character, quest)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "objective")

    async def start_solo_combat(self, actor: int, version: int):
        return await self.altos_missions.start_solo_combat(actor, version, S31_ID)

    async def propose_group_combat(self, actor: int, version: int):
        return await self.altos_missions.propose_group_combat(actor, version, S31_ID)

    async def retry_combat(self, actor: int, version: int):
        return await self.altos_missions.retry_combat(actor, version, S31_ID)

    async def toggle_tracking(self, actor: int, version: int) -> S31View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if not self._valid_active(quest, version) or await self._foreground(
                session, character.id
            ):
                return await self._view(session, character, quest, world, "detail")
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S31_ID else S31_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S31View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S31View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if not self._valid_active(quest, version) or await self._foreground(
                session, character.id
            ):
                return await self._view(session, character, quest, world, "detail")
            quest.status = "abandoned"
            quest.step = await self._next_step(session, character.id)
            quest.progress = await self._progress_snapshot(session, character.id)
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S31_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character: Character, quest: Quest) -> None:
        required = (
            "s31.survey_accepted",
            "s31.gralha_defeated",
            "s31.codex_recorded",
        )
        if not all(
            [await self._has_credit(session, character.id, item) for item in required]
        ):
            raise RuntimeError("S31 cannot complete before its persistent personal evidence")
        if not set(S31_TRAIL_POINTS).issubset(
            await self._trail_point_ids(session, character.id)
        ) or not set(S31_IMPRESSIONS).issubset(
            await self._impression_ids(session, character.id)
        ):
            raise RuntimeError("S31 cannot complete without its distinct shared trail evidence")

        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S31_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S31_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S31_XP_REWARD
            character.crowns += S31_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id, kind="xp", quantity=S31_XP_REWARD
                    ),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", quantity=S31_CROWNS_REWARD
                    ),
                )
            )
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=S31_COMPLETION_UNLOCK,
        )
        await self._credit(
            session,
            character.id,
            "s31.completed",
            "s31.completed",
            {"completion_unlock": S31_COMPLETION_UNLOCK, "personal_conclusion": True},
        )
        quest.status = "completed"
        quest.step = 6
        quest.state_version += 1
        quest.progress = await self._progress_snapshot(session, character.id)
        quest.progress = dict(quest.progress or {}) | {"completed": True}
        if character.tracked_secondary_quest_id == S31_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S31View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        progress.update(await self._progress_snapshot(session, character.id))
        gate_satisfied = await self._eligible_at_marcha(session, character, world)
        no_foreground = not await self._foreground(session, character.id)
        status = quest.status if quest is not None else "unaccepted"
        codex_owned = bool(
            await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character.id,
                    CodexEntry.entry_id == S31_CODEX_ENTRY,
                )
            )
        )
        return S31View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(
                gate_satisfied
                and quest is None
                and no_foreground
                and not await self._has_completion_unlock(session, character.id)
            ),
            reacceptable=bool(
                gate_satisfied
                and quest is not None
                and status == "abandoned"
                and no_foreground
            ),
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S31_ID
            ),
            action_available=bool(
                quest is not None
                and status == "active"
                and gate_satisfied
                and no_foreground
            ),
            gate_satisfied=gate_satisfied,
            trail_points=await self._trail_point_ids(session, character.id),
            impressions=await self._impression_ids(session, character.id),
            victory_recorded=await self._has_credit(
                session, character.id, "s31.gralha_defeated"
            ),
            codex_owned=codex_owned,
        )

    async def _share_evidence(
        self,
        session,
        character_ids: tuple[UUID, ...],
        *,
        quest_step: int,
        objective_id: str,
        source_key: str,
        evidence: dict,
    ) -> None:
        members = await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=S31_ID,
            content_version=S31_CONTENT_VERSION,
            step=quest_step,
            region=CONFINS_REGION_LABEL,
            location=CONFINS_MARCHA_LABEL,
        )
        for member in members:
            if not await self._eligible_at_marcha(session, member.character, member.world):
                continue
            created = await self._credit(
                session,
                member.character.id,
                objective_id,
                source_key,
                evidence | {"credited_by_character_id": str(member.character.id)},
            )
            if not created:
                continue
            progress = dict(member.quest.progress or {})
            if objective_id == "s31.trail_point":
                points = await self._trail_point_ids(session, member.character.id)
                progress["trail_point_ids"] = list(points)
                if set(S31_TRAIL_POINTS).issubset(points):
                    member.quest.step = 3
            else:
                impressions = await self._impression_ids(session, member.character.id)
                progress["impression_ids"] = list(impressions)
                if set(S31_IMPRESSIONS).issubset(impressions):
                    member.quest.step = 4
            progress["completed_steps"] = sorted(
                set(progress.get("completed_steps", ()))
                | (
                    {2}
                    if objective_id == "s31.trail_point" and member.quest.step == 3
                    else set()
                )
                | (
                    {3}
                    if objective_id == "s31.incompatible_impression"
                    and member.quest.step == 4
                    else set()
                )
            )
            member.quest.progress = progress
            member.quest.state_version += 1

    async def _refresh_actor_view(self, session, character_id: UUID, world, kind: str):
        character = await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        quest = await self._locked_quest(session, character_id)
        return (
            await self._view(session, character, quest, world, kind)
            if character is not None
            else None
        )

    async def _progress_snapshot(self, session, character_id: UUID) -> dict:
        return {
            "survey_accepted": await self._has_credit(
                session, character_id, "s31.survey_accepted"
            ),
            "trail_point_ids": list(await self._trail_point_ids(session, character_id)),
            "impression_ids": list(await self._impression_ids(session, character_id)),
            "gralha_defeated": await self._has_credit(
                session, character_id, "s31.gralha_defeated"
            ),
            "codex_recorded": await self._has_credit(
                session, character_id, "s31.codex_recorded"
            ),
            "completed": await self._has_credit(session, character_id, "s31.completed"),
        }

    async def _next_step(self, session, character_id: UUID) -> int:
        if await self._has_credit(session, character_id, "s31.completed"):
            return 6
        if await self._has_credit(session, character_id, "s31.codex_recorded"):
            return 6
        if await self._has_credit(session, character_id, "s31.gralha_defeated"):
            return 5
        if set(S31_IMPRESSIONS).issubset(await self._impression_ids(session, character_id)):
            return 4
        if set(S31_TRAIL_POINTS).issubset(await self._trail_point_ids(session, character_id)):
            return 3
        if await self._has_credit(session, character_id, "s31.survey_accepted"):
            return 2
        return 1

    async def _trail_point_ids(self, session, character_id: UUID) -> tuple[str, ...]:
        return await self._source_keys(
            session, character_id, "s31.trail_point", S31_TRAIL_POINTS
        )

    async def _impression_ids(self, session, character_id: UUID) -> tuple[str, ...]:
        return await self._source_keys(
            session, character_id, "s31.incompatible_impression", S31_IMPRESSIONS
        )

    async def _source_keys(
        self, session, character_id: UUID, objective_id: str, allowed: tuple[str, ...]
    ) -> tuple[str, ...]:
        rows = (
            await session.scalars(
                select(CampaignObjectiveCredit.source_key).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S31_ID,
                    CampaignObjectiveCredit.objective_id == objective_id,
                    CampaignObjectiveCredit.source_key.in_(allowed),
                )
            )
        ).all()
        return tuple(sorted(set(rows).intersection(allowed)))

    async def _has_credit(self, session, character_id: UUID, objective_id: str) -> bool:
        return bool(
            await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S31_ID,
                    CampaignObjectiveCredit.objective_id == objective_id,
                )
            )
        )

    async def _credit(
        self, session, character_id, objective_id: str, source_key: str, evidence: dict
    ) -> bool:
        existing = await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == S31_ID,
                CampaignObjectiveCredit.objective_id == objective_id,
                CampaignObjectiveCredit.source_key == source_key,
            )
        )
        if existing is not None:
            return False
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S31_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )
        return True

    async def _has_p31_completed(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P31_ID,
                    Quest.status == "completed",
                    Quest.content_version == P31_CONTENT_VERSION,
                )
            )
        )

    async def _eligible_at_marcha(self, session, character, world) -> bool:
        return bool(
            character is not None
            and character.level >= S31_LEVEL
            and self._at_marcha(world)
            and await self._has_p31_completed(session, character.id)
        )

    async def _has_completion_unlock(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == S31_COMPLETION_UNLOCK,
                )
            )
        )

    async def _active_combat(self, session, character_id: UUID):
        return await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == S31_MISSION_ID,
                GameActivity.status == "active",
            )
        )

    async def _ensure(self, session, model, **values) -> bool:
        existing = await session.scalar(select(model).filter_by(**values).with_for_update())
        if existing is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True

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
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S31_ID)
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S31_ID)
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
    def _at_marcha(world) -> bool:
        return bool(
            world is not None
            and world.region == CONFINS_REGION_LABEL
            and world.location == CONFINS_MARCHA_LABEL
        )

    @staticmethod
    def _valid_active(quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S31_CONTENT_VERSION
            and quest.state_version == version
        )
