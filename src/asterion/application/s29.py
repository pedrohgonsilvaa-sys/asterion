"""Persistent secondary quest S29: Os que Disseram Não."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import P28_ID
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_BASTILHA_LABEL,
    ALTOS_REGION_LABEL,
    RoadService,
)
from asterion.domain.road import (
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_CINZA_BASALTO,
    ALTOS_FERRO_CONTRAPESO,
    ALTOS_LIQUEN_PEDREIRA,
)
from asterion.infrastructure.db.models import (
    Achievement,
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

S29_ID = "S29"
S29_MISSION_ID = "mission.altos.s29"
S29_TITLE = "Os que Disseram Não"
S29_CONTENT_VERSION = "altos-1.0.1"
S29_REWARD_SOURCE = S29_MISSION_ID
S29_CODEX_ENTRY = "codex.altos.dissidencia_sem_sabotagem"
S29_CODEX_FRAGMENT = "codex.altos.dissidencia_sem_sabotagem"
S29_ACHIEVEMENT = "achievement.altos.dissidencia"
S29_XP_REWARD = 48_685
S29_CROWNS_REWARD = 620
S29_LEVEL = 48
S29_FERRO_CONTRAPESO = ALTOS_FERRO_CONTRAPESO
S29_LIQUEN_PEDREIRA = ALTOS_LIQUEN_PEDREIRA
S29_CINZA_BASALTO = ALTOS_CINZA_BASALTO
ALTOS_REGION = ALTOS_REGION_LABEL

# The source publishes three distinct refusal records but does not name their
# authors. Stable evidence IDs keep the anonymous records distinct without
# adding names or further narrative claims. Two records carry the published
# continuation-in-civil-maintenance evidence.
S29_REFUSAL_RECORDS = (
    "evidence.altos.s29.refusal_record_a",
    "evidence.altos.s29.refusal_record_b",
    "evidence.altos.s29.refusal_record_c",
)
S29_RECORDS = S29_REFUSAL_RECORDS
S29_CIVIL_MAINTENANCE_RECORDS = frozenset(S29_REFUSAL_RECORDS[:2])
_RECORD_ACTION_IDS = {
    "locate_record_a": S29_REFUSAL_RECORDS[0],
    "locate_record_b": S29_REFUSAL_RECORDS[1],
    "locate_record_c": S29_REFUSAL_RECORDS[2],
}
S29_LOCATIONS = frozenset((ALTOS_ABRIGO_LABEL, ALTOS_BASTILHA_LABEL))
_LOCATION_UNLOCKS = {
    ALTOS_ABRIGO_LABEL: ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_BASTILHA_LABEL: ALTOS_BASTILHA_ACCESS_UNLOCK,
}


@dataclass(frozen=True, slots=True)
class S29View:
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
    refusal_records: tuple[str, ...] = ()
    civil_maintenance_verified: bool = False
    no_material_sabotage_verified: bool = False
    codex_owned: bool = False
    achievement_owned: bool = False


class S29Service:
    """Per-character evidence, corroboration, Codex, and one-time settlement."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        road: RoadService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.road = road

    async def giver(self, actor: int) -> S29View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not await self._at_contact_with_access(session, character, world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S29View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not await self._at_contact_with_access(session, character, world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S29View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_mission_location(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S29View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int) -> S29View | None:
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S29View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            world = await self._locked_world(session, character.id)
            quest = await self._locked_quest(session, character.id)
            eligible = bool(
                await self._eligible_giver(session, character, world)
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
                records = await self._record_ids(session, character.id)
                quest.status = "active"
                quest.step = 1 if len(records) < len(S29_REFUSAL_RECORDS) else 2
                quest.progress = {"refusal_record_ids": list(records)}
                quest.content_version = S29_CONTENT_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S29_ID,
                    title=S29_TITLE,
                    status="active",
                    step=1,
                    content_version=S29_CONTENT_VERSION,
                    state_version=0,
                    progress={"refusal_record_ids": []},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S29View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "objective")

    async def advance(self, actor: int, version: int, action: str) -> S29View | None:
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

            record_id = self._record_action_id(action)
            if quest.step == 1 and record_id is not None:
                if (
                    world is None
                    or world.location != ALTOS_BASTILHA_LABEL
                    or not await self._eligible_at_location(
                        session, character, world, ALTOS_BASTILHA_LABEL
                    )
                ):
                    return await self._view(session, character, quest, world, "objective")
                members = await present_campaign_members(
                    session,
                    character_ids=character_ids,
                    quest_id=S29_ID,
                    content_version=S29_CONTENT_VERSION,
                    step=1,
                    region=ALTOS_REGION,
                    location=ALTOS_BASTILHA_LABEL,
                )
                eligible_members = []
                for member in members:
                    if await self._eligible_at_location(
                        session, member.character, member.world, ALTOS_BASTILHA_LABEL
                    ):
                        eligible_members.append(member)
                if not any(member.character.id == character.id for member in eligible_members):
                    return await self._view(session, character, quest, world, "objective")

                for member in eligible_members:
                    records = set(await self._record_ids(session, member.character.id))
                    if record_id in records:
                        continue
                    await self._credit(
                        session,
                        member.character.id,
                        "s29.refusal_record",
                        record_id,
                        {
                            "record_id": record_id,
                            "evidence_type": "distinct_emergency_order_refusal_record",
                            "shared_physical_evidence": True,
                        },
                    )
                    records.add(record_id)
                    member_progress = dict(member.quest.progress or {})
                    member_progress["refusal_record_ids"] = sorted(records)
                    member.quest.progress = member_progress
                    if set(S29_REFUSAL_RECORDS).issubset(records):
                        member.quest.step = 2
                    member.quest.state_version += 1
                quest = await self._locked_quest(session, character.id)
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 2 and action == "verify_civil_maintenance":
                records = await self._record_ids(session, character.id)
                continued = sorted(set(records).intersection(S29_CIVIL_MAINTENANCE_RECORDS))
                if (
                    world is None
                    or world.location != ALTOS_BASTILHA_LABEL
                    or not await self._eligible_at_location(
                        session, character, world, ALTOS_BASTILHA_LABEL
                    )
                    or not set(S29_REFUSAL_RECORDS).issubset(records)
                    or len(continued) < 2
                ):
                    return await self._view(session, character, quest, world, "objective")
                progress = dict(quest.progress or {})
                progress["civil_maintenance_record_ids"] = continued
                progress["civil_maintenance_verified"] = True
                quest.progress = progress
                quest.step = 3
                quest.state_version += 1
                await self._credit(
                    session,
                    character.id,
                    "s29.civil_maintenance_verified",
                    "s29.civil_maintenance_verified",
                    {
                        "refusal_record_ids": list(records),
                        "continued_civil_maintenance_record_ids": continued,
                        "minimum_distinct_refusants": 2,
                        "personal_evidence": True,
                    },
                )
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 3 and action == "verify_no_material_sabotage":
                records = await self._record_ids(session, character.id)
                if (
                    world is None
                    or world.location != ALTOS_BASTILHA_LABEL
                    or not await self._eligible_at_location(
                        session, character, world, ALTOS_BASTILHA_LABEL
                    )
                    or not set(S29_REFUSAL_RECORDS).issubset(records)
                    or not (quest.progress or {}).get("civil_maintenance_verified")
                ):
                    return await self._view(session, character, quest, world, "objective")
                progress = dict(quest.progress or {})
                progress["no_material_sabotage_verified"] = True
                quest.progress = progress
                quest.step = 4
                quest.state_version += 1
                await self._credit(
                    session,
                    character.id,
                    "s29.no_material_sabotage_verified",
                    "s29.no_material_sabotage_verified",
                    {
                        "refusal_record_ids": list(records),
                        "material_sabotage": False,
                        "personal_evidence": True,
                        "does_not_absolve_all_dissidents": True,
                        "does_not_reverse_p30_confirmation": True,
                    },
                )
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 4 and action == "compare_with_maro_and_sel":
                if not await self._eligible_at_contact(session, character, world):
                    return await self._view(session, character, quest, world, "objective")
                progress = dict(quest.progress or {})
                progress["compared_with_maro_and_sel"] = True
                quest.progress = progress
                quest.step = 5
                quest.state_version += 1
                await self._credit(
                    session,
                    character.id,
                    "s29.compared_with_maro_and_sel",
                    "s29.compared_with_maro_and_sel",
                    {
                        "location": world.location,
                        "refusal_record_ids": list(await self._record_ids(session, character.id)),
                        "personal_evidence": True,
                    },
                )
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 5 and action == "record_codex":
                if (
                    not await self._eligible_at_contact(session, character, world)
                    or not (quest.progress or {}).get("compared_with_maro_and_sel")
                    or not (quest.progress or {}).get("civil_maintenance_verified")
                    or not (quest.progress or {}).get("no_material_sabotage_verified")
                    or not set(S29_REFUSAL_RECORDS).issubset(
                        await self._record_ids(session, character.id)
                    )
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=S29_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S29_CODEX_ENTRY,
                    fragment_id=S29_CODEX_FRAGMENT,
                )
                progress = dict(quest.progress or {})
                progress["codex_registered"] = True
                await self._credit(
                    session,
                    character.id,
                    "s29.codex_recorded",
                    "s29.codex_recorded",
                    {
                        "codex_entry": S29_CODEX_ENTRY,
                        "refusal_record_ids": list(await self._record_ids(session, character.id)),
                        "refusal_is_not_material_sabotage": True,
                        "not_collective_absolution": True,
                        "p30_confirmation_remains_valid": True,
                        "personal_evidence": True,
                    },
                )
                await self._complete(session, character, quest, progress)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "objective")

    async def toggle_tracking(self, actor: int, version: int) -> S29View | None:
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
                None if character.tracked_secondary_quest_id == S29_ID else S29_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S29View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S29View | None:
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
            quest.step = 1
            quest.progress = {}
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S29_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character, quest, progress: dict) -> None:
        records = await self._record_ids(session, character.id)
        if not set(S29_REFUSAL_RECORDS).issubset(records):
            raise RuntimeError("S29 cannot complete without its three distinct refusal records")
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S29_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S29_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S29_XP_REWARD
            character.crowns += S29_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(reward_event_id=event.id, kind="xp", quantity=S29_XP_REWARD),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", quantity=S29_CROWNS_REWARD
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S29_FERRO_CONTRAPESO,
                        quantity=1,
                        payload={"material_id": S29_FERRO_CONTRAPESO, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S29_LIQUEN_PEDREIRA,
                        quantity=1,
                        payload={"material_id": S29_LIQUEN_PEDREIRA, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S29_CINZA_BASALTO,
                        quantity=2,
                        payload={"material_id": S29_CINZA_BASALTO, "bound": True},
                    ),
                )
            )
            await self.road.deliver_material(
                session,
                character,
                S29_FERRO_CONTRAPESO,
                1,
                f"{S29_REWARD_SOURCE}:material:ferro_contrapeso",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                S29_LIQUEN_PEDREIRA,
                1,
                f"{S29_REWARD_SOURCE}:material:liquen_pedreira",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                S29_CINZA_BASALTO,
                2,
                f"{S29_REWARD_SOURCE}:material:cinza_basalto",
                bound=True,
            )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=S29_ACHIEVEMENT,
        )
        quest.status = "completed"
        quest.state_version += 1
        progress["completed"] = True
        progress["codex_registered"] = True
        progress["refusal_record_ids"] = list(records)
        quest.progress = progress
        if character.tracked_secondary_quest_id == S29_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S29View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        records = await self._record_ids(session, character.id)
        contact_eligible = await self._eligible_giver(session, character, world)
        action_available = False
        if quest is not None and quest.status == "active" and world is not None:
            if quest.step == 1:
                action_available = bool(
                    world.location == ALTOS_BASTILHA_LABEL
                    and await self._eligible_at_location(
                        session, character, world, ALTOS_BASTILHA_LABEL
                    )
                    and set(records) != set(S29_REFUSAL_RECORDS)
                )
            elif quest.step in {2, 3}:
                action_available = bool(
                    world.location == ALTOS_BASTILHA_LABEL
                    and await self._eligible_at_location(
                        session, character, world, ALTOS_BASTILHA_LABEL
                    )
                )
            elif quest.step in {4, 5}:
                action_available = await self._eligible_at_contact(
                    session, character, world
                )
        codex_owned = bool(
            await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character.id,
                    CodexEntry.entry_id == S29_CODEX_ENTRY,
                )
            )
        )
        achievement_owned = bool(
            await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character.id,
                    Achievement.achievement_id == S29_ACHIEVEMENT,
                )
            )
        )
        status = quest.status if quest is not None else "unaccepted"
        return S29View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(
                contact_eligible
                and quest is None
                and not await self._foreground(session, character.id)
            ),
            reacceptable=bool(
                contact_eligible
                and quest is not None
                and status == "abandoned"
                and not await self._foreground(session, character.id)
            ),
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S29_ID
            ),
            action_available=action_available,
            refusal_records=records,
            civil_maintenance_verified=bool(progress.get("civil_maintenance_verified")),
            no_material_sabotage_verified=bool(
                progress.get("no_material_sabotage_verified")
            ),
            codex_owned=codex_owned,
            achievement_owned=achievement_owned,
        )

    async def _eligible_giver(self, session, character, world) -> bool:
        if (
            character.level < S29_LEVEL
            or world is None
            or world.region != ALTOS_REGION
            or world.location not in S29_LOCATIONS
            or not await self._has_location_access(session, character.id, world.location)
        ):
            return False
        return await self._has_p28_completed(session, character.id)

    async def _eligible_at_location(self, session, character, world, location: str) -> bool:
        if (
            character.level < S29_LEVEL
            or world is None
            or world.region != ALTOS_REGION
            or world.location != location
            or location not in S29_LOCATIONS
            or not await self._has_location_access(session, character.id, location)
        ):
            return False
        return await self._has_p28_completed(session, character.id)

    async def _eligible_at_contact(self, session, character, world) -> bool:
        return bool(
            world is not None
            and world.location in S29_LOCATIONS
            and await self._eligible_at_location(
                session, character, world, world.location
            )
        )

    async def _has_location_access(self, session, character_id: UUID, location: str) -> bool:
        unlock_id = _LOCATION_UNLOCKS.get(location)
        if unlock_id is None:
            return False
        return bool(
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == unlock_id,
                )
            )
        )

    async def _has_p28_completed(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P28_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _at_contact_with_access(self, session, character, world) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION
            and world.location in S29_LOCATIONS
            and await self._has_location_access(session, character.id, world.location)
            and not await self._foreground(session, character.id)
        )

    @staticmethod
    def _at_mission_location(world) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION
            and world.location in S29_LOCATIONS
        )

    @staticmethod
    def _record_action_id(action: str) -> str | None:
        return _RECORD_ACTION_IDS.get(action)

    async def _record_ids(self, session, character_id: UUID) -> tuple[str, ...]:
        rows = (
            await session.scalars(
                select(CampaignObjectiveCredit.source_key).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S29_ID,
                    CampaignObjectiveCredit.objective_id == "s29.refusal_record",
                    CampaignObjectiveCredit.source_key.in_(S29_REFUSAL_RECORDS),
                )
            )
        ).all()
        return tuple(sorted(set(rows).intersection(S29_REFUSAL_RECORDS)))

    async def _credit(self, session, character_id, objective_id, source_key, evidence):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S29_ID,
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
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S29_ID)
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S29_ID)
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
    def _valid_active(quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S29_CONTENT_VERSION
            and quest.state_version == version
        )

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True
