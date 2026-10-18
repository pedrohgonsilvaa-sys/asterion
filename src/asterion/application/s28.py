"""Persistent secondary quest S28: Cartas de Emergência."""

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
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_PONTES_LABEL,
    ALTOS_REGION_LABEL,
    RoadService,
)
from asterion.domain.road import (
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_CINZA_BASALTO,
    ALTOS_FERRO_CONTRAPESO,
    ALTOS_LIQUEN_PEDREIRA,
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_PONTES_ACCESS_UNLOCK,
)
from asterion.infrastructure.db.models import (
    Achievement,
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

S28_ID = "S28"
S28_MISSION_ID = "mission.altos.s28"
S28_TITLE = "Cartas de Emergência"
S28_CONTENT_VERSION = "altos-1.0.1"
S28_REWARD_SOURCE = S28_MISSION_ID
S28_CODEX_ENTRY = "codex.altos.cartas_emergencia"
S28_ACHIEVEMENT = "achievement.altos.cartas_emergencia"
S28_XP_REWARD = 46_970
S28_CROWNS_REWARD = 610
S28_LEVEL = 47
S28_FERRO_CONTRAPESO = ALTOS_FERRO_CONTRAPESO
S28_LIQUEN_PEDREIRA = ALTOS_LIQUEN_PEDREIRA
S28_CINZA_BASALTO = ALTOS_CINZA_BASALTO
ALTOS_REGION = ALTOS_REGION_LABEL

S28_CIVIL_LETTER = "codex.fragment.altos.cartas_emergencia.civil"
S28_WORKERS_LETTER = "codex.fragment.altos.cartas_emergencia.trabalhadores"
S28_ARCHIVE_LETTER = "codex.fragment.altos.cartas_emergencia.fora_arquivo"
S28_LETTER_FRAGMENTS = (S28_CIVIL_LETTER, S28_WORKERS_LETTER, S28_ARCHIVE_LETTER)

_LETTER_STEPS = {
    1: (
        "recover_civil_letter",
        "civil_letter_recovered",
        "letter.civil",
        ALTOS_PONTES_LABEL,
        ALTOS_PONTES_ACCESS_UNLOCK,
        S28_CIVIL_LETTER,
    ),
    2: (
        "recover_workers_letter",
        "workers_letter_recovered",
        "letter.workers",
        ALTOS_PEDREIRAS_LABEL,
        ALTOS_PEDREIRAS_ACCESS_UNLOCK,
        S28_WORKERS_LETTER,
    ),
    3: (
        "recover_archive_letter",
        "archive_letter_recovered",
        "letter.archive",
        ALTOS_BASTILHA_LABEL,
        ALTOS_BASTILHA_ACCESS_UNLOCK,
        S28_ARCHIVE_LETTER,
    ),
}
_CONTACT_LOCATIONS = frozenset((ALTOS_ABRIGO_LABEL, ALTOS_BASTILHA_LABEL))
_LOCATION_UNLOCKS = {
    ALTOS_ABRIGO_LABEL: ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_PONTES_LABEL: ALTOS_PONTES_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_LABEL: ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_BASTILHA_LABEL: ALTOS_BASTILHA_ACCESS_UNLOCK,
}


@dataclass(frozen=True, slots=True)
class S28View:
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
    codex_fragments: tuple[str, ...] = ()
    codex_corroborated: bool = False
    achievement_owned: bool = False


class S28Service:
    """Tracks per-character letters, their durable Codex fragments, and settlement."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        road: RoadService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.road = road

    async def giver(self, actor: int) -> S28View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not await self._at_contact_with_access(session, character, world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S28View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not await self._at_contact_with_access(session, character, world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S28View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_mission_location(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S28View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int) -> S28View | None:
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S28View | None:
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
                quest.status = "active"
                quest.step = 1
                quest.progress = {}
                quest.content_version = S28_CONTENT_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S28_ID,
                    title=S28_TITLE,
                    status="active",
                    step=1,
                    content_version=S28_CONTENT_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S28View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "objective")

    async def advance(self, actor: int, version: int, action: str) -> S28View | None:
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

            letter_step = _LETTER_STEPS.get(quest.step)
            if letter_step is not None:
                (
                    expected_action,
                    progress_key,
                    objective,
                    location,
                    unlock_id,
                    fragment_id,
                ) = letter_step
                if action != expected_action or world is None or world.location != location:
                    return await self._view(session, character, quest, world, "objective")
                members = await present_campaign_members(
                    session,
                    character_ids=character_ids,
                    quest_id=S28_ID,
                    content_version=S28_CONTENT_VERSION,
                    step=quest.step,
                    region=ALTOS_REGION,
                    location=location,
                )
                eligible_members = []
                for member in members:
                    if await self._eligible_at_location(
                        session, member.character, member.world, location
                    ):
                        eligible_members.append(member)
                if not any(member.character.id == character.id for member in eligible_members):
                    return await self._view(session, character, quest, world, "objective")
                for member in eligible_members:
                    member_progress = dict(member.quest.progress or {})
                    member_progress[progress_key] = True
                    member.quest.progress = member_progress
                    member.quest.step += 1
                    member.quest.state_version += 1
                    await self._record_letter(
                        session, member.character.id, fragment_id
                    )
                    await self._credit(
                        session,
                        member.character.id,
                        f"s28.{objective}",
                        f"s28.{objective}:{fragment_id}",
                        {
                            "location": location,
                            "codex_entry": S28_CODEX_ENTRY,
                            "codex_fragment": fragment_id,
                            "shared_physical_evidence": True,
                        },
                    )
                quest = await self._locked_quest(session, character.id)
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 4 and action == "compare_with_maro":
                if (
                    world is None
                    or world.location not in _CONTACT_LOCATIONS
                    or not await self._eligible_at_location(
                        session, character, world, world.location
                    )
                    or not await self._has_all_letters(session, character.id)
                ):
                    return await self._view(session, character, quest, world, "objective")
                progress = dict(quest.progress or {})
                progress["compared_with_maro"] = True
                quest.progress = progress
                quest.step += 1
                quest.state_version += 1
                await self._credit(
                    session,
                    character.id,
                    "s28.compared_with_maro",
                    f"s28.compared_with_maro:{quest.state_version}",
                    {
                        "location": world.location,
                        "codex_entry": S28_CODEX_ENTRY,
                        "codex_fragments": list(S28_LETTER_FRAGMENTS),
                        "personal_evidence": True,
                    },
                )
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 5 and action == "corroborate_codex":
                if (
                    world is None
                    or world.location not in _CONTACT_LOCATIONS
                    or not await self._eligible_at_location(
                        session, character, world, world.location
                    )
                    or not (quest.progress or {}).get("compared_with_maro")
                    or not await self._has_all_letters(session, character.id)
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=S28_CODEX_ENTRY,
                )
                progress = dict(quest.progress or {})
                progress["codex_corroborated"] = True
                await self._credit(
                    session,
                    character.id,
                    "s28.codex_corroborated",
                    f"s28.codex_corroborated:{quest.state_version + 1}",
                    {
                        "codex_entry": S28_CODEX_ENTRY,
                        "codex_fragments": list(S28_LETTER_FRAGMENTS),
                        "personal_evidence": True,
                        "civil_testimony_supplements_official_records": True,
                    },
                )
                await self._complete(session, character, quest, progress)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "objective")

    async def toggle_tracking(self, actor: int, version: int) -> S28View | None:
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
                None if character.tracked_secondary_quest_id == S28_ID else S28_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S28View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S28View | None:
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
            if character.tracked_secondary_quest_id == S28_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _record_letter(self, session, character_id: UUID, fragment_id: str) -> None:
        await self._ensure(
            session,
            CodexEntry,
            character_id=character_id,
            entry_id=S28_CODEX_ENTRY,
        )
        await self._ensure(
            session,
            CodexFragment,
            character_id=character_id,
            entry_id=S28_CODEX_ENTRY,
            fragment_id=fragment_id,
        )

    async def _has_all_letters(self, session, character_id: UUID) -> bool:
        owned = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id,
                        CodexFragment.entry_id == S28_CODEX_ENTRY,
                        CodexFragment.fragment_id.in_(S28_LETTER_FRAGMENTS),
                    )
                )
            ).all()
        )
        return set(S28_LETTER_FRAGMENTS).issubset(owned)

    async def _complete(self, session, character, quest, progress: dict) -> None:
        if not await self._has_all_letters(session, character.id):
            raise RuntimeError("S28 cannot complete without its three persistent letter fragments")
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S28_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S28_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S28_XP_REWARD
            character.crowns += S28_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        quantity=S28_XP_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        quantity=S28_CROWNS_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S28_FERRO_CONTRAPESO,
                        quantity=1,
                        payload={"material_id": S28_FERRO_CONTRAPESO, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S28_LIQUEN_PEDREIRA,
                        quantity=1,
                        payload={"material_id": S28_LIQUEN_PEDREIRA, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S28_CINZA_BASALTO,
                        quantity=2,
                        payload={"material_id": S28_CINZA_BASALTO, "bound": True},
                    ),
                )
            )
            await self.road.deliver_material(
                session,
                character,
                S28_FERRO_CONTRAPESO,
                1,
                f"{S28_REWARD_SOURCE}:material:ferro_contrapeso",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                S28_LIQUEN_PEDREIRA,
                1,
                f"{S28_REWARD_SOURCE}:material:liquen_pedreira",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                S28_CINZA_BASALTO,
                2,
                f"{S28_REWARD_SOURCE}:material:cinza_basalto",
                bound=True,
            )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=S28_ACHIEVEMENT,
        )
        quest.status = "completed"
        quest.state_version += 1
        progress["completed"] = True
        progress["codex_corroborated"] = True
        quest.progress = progress
        if character.tracked_secondary_quest_id == S28_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S28View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        fragments = tuple(
            sorted(
                set(
                    (
                        await session.scalars(
                            select(CodexFragment.fragment_id).where(
                                CodexFragment.character_id == character.id,
                                CodexFragment.entry_id == S28_CODEX_ENTRY,
                                CodexFragment.fragment_id.in_(S28_LETTER_FRAGMENTS),
                            )
                        )
                    ).all()
                )
            )
        )
        contact_eligible = await self._eligible_giver(session, character, world)
        action_available = False
        if quest is not None and quest.status == "active" and world is not None:
            letter = _LETTER_STEPS.get(quest.step)
            if letter is not None:
                action_available = bool(
                    world.location == letter[3]
                    and await self._eligible_at_location(
                        session, character, world, letter[3]
                    )
                )
            elif quest.step in {4, 5}:
                action_available = bool(
                    world.location in _CONTACT_LOCATIONS
                    and await self._eligible_at_location(
                        session, character, world, world.location
                    )
                )
        achievement_owned = bool(
            await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character.id,
                    Achievement.achievement_id == S28_ACHIEVEMENT,
                )
            )
        )
        status = quest.status if quest is not None else "unaccepted"
        return S28View(
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
                and (quest is None or status == "abandoned")
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
                and character.tracked_secondary_quest_id == S28_ID
            ),
            action_available=action_available,
            codex_fragments=fragments,
            codex_corroborated=bool(progress.get("codex_corroborated")),
            achievement_owned=achievement_owned,
        )

    async def _eligible_giver(self, session, character, world) -> bool:
        if (
            character.level < S28_LEVEL
            or world is None
            or world.region != ALTOS_REGION
            or world.location not in _CONTACT_LOCATIONS
            or not await self._has_location_access(session, character.id, world.location)
        ):
            return False
        return await self._has_p28(session, character.id)

    async def _eligible_at_location(self, session, character, world, location: str) -> bool:
        if (
            character.level < S28_LEVEL
            or world is None
            or world.region != ALTOS_REGION
            or world.location != location
            or location not in _LOCATION_UNLOCKS
            or not await self._has_location_access(session, character.id, location)
        ):
            return False
        return await self._has_p28(session, character.id)

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

    async def _has_p28(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P28_ID,
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    async def _at_contact_with_access(self, session, character, world) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION
            and world.location in _CONTACT_LOCATIONS
            and await self._has_location_access(session, character.id, world.location)
            and not await self._foreground(session, character.id)
        )

    @staticmethod
    def _at_mission_location(world) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION
            and world.location in _LOCATION_UNLOCKS
        )

    async def _credit(self, session, character_id, objective_id, source_key, evidence):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S28_ID,
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
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S28_ID)
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S28_ID)
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
            and quest.content_version == S28_CONTENT_VERSION
            and quest.state_version == version
        )

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True
