"""Persistent secondary quest S30: A Ordem que Restou."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import P29_ID, S30_ID, AltosMissionService
from asterion.application.campaign_objectives import record_campaign_objective_credit
from asterion.application.progression import consolidate_character_level
from asterion.application.road import ALTOS_BASTILHA_LABEL, ALTOS_REGION_LABEL, RoadService
from asterion.application.s28 import S28_ID, S28_LETTER_FRAGMENTS
from asterion.domain.road import (
    ALTOS_ABRIGO_BRAZIER,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_CINZA_BASALTO,
    ALTOS_COURO_ESCARPA,
    ALTOS_CUSTODIO_ULTIMO_TURNO,
    ALTOS_FERRO_CONTRAPESO,
    ALTOS_LIQUEN_PEDREIRA,
)
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEvidence,
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

S30_MISSION_ID = "mission.altos.s30"
S30_TITLE = "A Ordem que Restou"
S30_CONTENT_VERSION = "altos-1.0.1"
S30_REWARD_SOURCE = S30_MISSION_ID
S30_CODEX_ENTRY = "codex.altos.ordem_que_restou"
S30_CODEX_FRAGMENT = S30_CODEX_ENTRY
S30_ACHIEVEMENT = "achievement.altos.ordem_restou"
S30_LEVEL = 50
S30_XP_REWARD = 74_500
S30_CROWNS_REWARD = 1_060

# The source identifies three physical seals but does not give them names.
# These stable IDs distinguish their evidence without adding narrative lore.
S30_PHYSICAL_SEALS = (
    "evidence.altos.s30.validity_seal_a",
    "evidence.altos.s30.validity_seal_b",
    "evidence.altos.s30.validity_seal_c",
)
_SEAL_ACTIONS = {
    "locate_seal_a": S30_PHYSICAL_SEALS[0],
    "locate_seal_b": S30_PHYSICAL_SEALS[1],
    "locate_seal_c": S30_PHYSICAL_SEALS[2],
}
_MATERIAL_REWARDS = (
    (ALTOS_FERRO_CONTRAPESO, 2, "ferro_contrapeso"),
    (ALTOS_COURO_ESCARPA, 2, "couro_escarpa"),
    (ALTOS_LIQUEN_PEDREIRA, 2, "liquen_pedreira"),
    (ALTOS_CINZA_BASALTO, 2, "cinza_basalto"),
)


@dataclass(frozen=True, slots=True)
class S30View:
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
    physical_seals: tuple[str, ...] = ()
    codex_owned: bool = False
    achievement_owned: bool = False
    boss_victory_recorded: bool = False
    bestiary_observations: tuple[str, ...] = ()
    brazier: str = ALTOS_ABRIGO_BRAZIER


class S30Service:
    """Personal mission state backed by durable objective credits and rewards."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        road: RoadService,
        altos_missions: AltosMissionService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.road = road
        self.altos_missions = altos_missions

    async def giver(self, actor: int) -> S30View | object | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not await self._at_contact(session, character, world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S30View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not await self._at_contact(session, character, world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S30View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_bastilha(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S30View | object | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            active = await self._active_combat(session, character.id)
            if active is not None:
                return await self.altos_missions.resume(actor, S30_ID)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int) -> S30View | object | None:
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(
        self, actor: int, version: int = 0, *, reaccept: bool = False
    ) -> S30View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            world = await self._locked_world(session, character.id)
            quest = await self._locked_quest(session, character.id)
            eligible = bool(
                await self._eligible_contact(session, character, world)
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
                quest.step = await self._next_step(session, character.id)
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.content_version = S30_CONTENT_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S30_ID,
                    title=S30_TITLE,
                    status="active",
                    step=1,
                    content_version=S30_CONTENT_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S30View | object | None:
        return await self.resume(actor)

    async def advance(self, actor: int, version: int, action: str):
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
            if not await self._eligible_contact(session, character, world):
                return await self._view(session, character, quest, world, "objective")

            if quest.step == 1 and action == "reconstruct_from_letters":
                if not await self._has_emergency_letters(session, character.id):
                    return await self._view(session, character, quest, world, "objective")
                await self._credit(
                    session,
                    character.id,
                    "s30.letters_reconstructed",
                    "s30.letters_reconstructed",
                    {"s28_fragments": list(S28_LETTER_FRAGMENTS), "personal_evidence": True},
                )
                await self._set_step(session, quest, character.id, 2)

            elif quest.step == 2 and action in _SEAL_ACTIONS:
                seal = _SEAL_ACTIONS[action]
                await self._credit(
                    session,
                    character.id,
                    "s30.physical_seal",
                    seal,
                    {"seal_id": seal, "physical_evidence": True, "personal_evidence": True},
                )
                seals = await self._seals(session, character.id)
                if set(S30_PHYSICAL_SEALS).issubset(seals):
                    await self._set_step(session, quest, character.id, 3)
                else:
                    quest.state_version += 1
                    quest.progress = await self._progress_snapshot(session, character.id)

            elif quest.step == 3 and action == "authorize_service_post":
                await self._credit(
                    session,
                    character.id,
                    "s30.service_post_opened",
                    "s30.service_post_opened",
                    {"authorization": "mission_narrative", "global_world_state_changed": False},
                )
                await self._set_step(session, quest, character.id, 4)

            elif quest.step == 4 and action == "verify_no_current_civil_function":
                if not await self._has_credit(session, character.id, "s30.service_post_opened"):
                    return await self._view(session, character, quest, world, "objective")
                await self._credit(
                    session,
                    character.id,
                    "s30.protocol_verified",
                    "s30.protocol_verified",
                    {"current_civil_function": False, "personal_evidence": True},
                )
                await self._set_step(session, quest, character.id, 5)

            elif quest.step == 7 and action == "record_bestiary_facts":
                if not await self._has_credit(session, character.id, "s30.custodian_defeated"):
                    return await self._view(session, character, quest, world, "objective")
                bestiary_entry = await self._bestiary_entry(session, character.id)
                if bestiary_entry is None:
                    return await self._view(session, character, quest, world, "objective")
                await self.road.bestiary.add_evidence(
                    session,
                    bestiary_entry,
                    character.id,
                    ALTOS_CUSTODIO_ULTIMO_TURNO,
                    "mission:s30_bestiary_observed",
                    "mission",
                    10,
                )
                await self.road.bestiary.refresh_boss_mastery(
                    session, character.id, ALTOS_CUSTODIO_ULTIMO_TURNO
                )
                await self._credit(
                    session,
                    character.id,
                    "s30.bestiary_recorded",
                    "s30.bestiary_recorded",
                    {"observed_facts_only": True, "creature_id": ALTOS_CUSTODIO_ULTIMO_TURNO},
                )
                await self._set_step(session, quest, character.id, 8)

            elif quest.step == 8 and action == "record_codex":
                if not await self._has_credit(session, character.id, "s30.bestiary_recorded"):
                    return await self._view(session, character, quest, world, "objective")
                await self._ensure(
                    session, CodexEntry, character_id=character.id, entry_id=S30_CODEX_ENTRY
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S30_CODEX_ENTRY,
                    fragment_id=S30_CODEX_FRAGMENT,
                )
                await self._credit(
                    session,
                    character.id,
                    "s30.codex_recorded",
                    "s30.codex_recorded",
                    {"codex_entry": S30_CODEX_ENTRY, "personal_evidence": True},
                )
                await self._set_step(session, quest, character.id, 9)

            elif quest.step == 9 and action == "conclude_with_sel":
                if not await self._has_credit(session, character.id, "s30.codex_recorded"):
                    return await self._view(session, character, quest, world, "objective")
                await self._complete(session, character, quest)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")
            else:
                return await self._view(session, character, quest, world, "objective")
            return await self._view(session, character, quest, world, "detail")

    async def toggle_tracking(self, actor: int, version: int) -> S30View | None:
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
                None if character.tracked_secondary_quest_id == S30_ID else S30_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S30View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S30View | None:
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
            if character.tracked_secondary_quest_id == S30_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character, quest) -> None:
        required = (
            "s30.letters_reconstructed",
            "s30.service_post_opened",
            "s30.protocol_verified",
            "s30.custodian_faced",
            "s30.custodian_defeated",
            "s30.bestiary_recorded",
            "s30.codex_recorded",
        )
        if not all([await self._has_credit(session, character.id, item) for item in required]):
            raise RuntimeError("S30 cannot complete before its persistent mission evidence")
        if not set(S30_PHYSICAL_SEALS).issubset(await self._seals(session, character.id)):
            raise RuntimeError("S30 cannot complete without its three distinct physical seals")
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S30_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S30_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S30_XP_REWARD
            character.crowns += S30_CROWNS_REWARD
            components = [
                RewardComponent(reward_event_id=event.id, kind="xp", quantity=S30_XP_REWARD),
                RewardComponent(
                    reward_event_id=event.id, kind="crowns", quantity=S30_CROWNS_REWARD
                ),
            ]
            for item_id, quantity, _slug in _MATERIAL_REWARDS:
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=item_id,
                        quantity=quantity,
                        payload={"material_id": item_id, "bound": True},
                    )
                )
            session.add_all(components)
            for item_id, quantity, slug in _MATERIAL_REWARDS:
                await self.road.deliver_material(
                    session,
                    character,
                    item_id,
                    quantity,
                    f"{S30_REWARD_SOURCE}:material:{slug}",
                    bound=True,
                )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=S30_ACHIEVEMENT,
        )
        quest.status = "completed"
        quest.step = 9
        quest.state_version += 1
        progress = dict(quest.progress or {}) if quest is not None else {}
        progress.update(await self._progress_snapshot(session, character.id))
        progress.update(completed=True, codex_registered=True)
        quest.progress = progress
        if character.tracked_secondary_quest_id == S30_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S30View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        progress.update(await self._progress_snapshot(session, character.id))
        seals = await self._seals(session, character.id)
        eligible = await self._eligible_contact(session, character, world)
        action_available = bool(
            quest is not None
            and quest.status == "active"
            and await self._eligible_location(session, character, world)
            and not await self._foreground(session, character.id)
        )
        codex_owned = bool(
            await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character.id,
                    CodexEntry.entry_id == S30_CODEX_ENTRY,
                )
            )
        )
        achievement_owned = bool(
            await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character.id,
                    Achievement.achievement_id == S30_ACHIEVEMENT,
                )
            )
        )
        observations = tuple(
            sorted(
                (
                    await session.scalars(
                        select(BestiaryEvidence.evidence_id).where(
                            BestiaryEvidence.character_id == character.id,
                            BestiaryEvidence.creature_id == ALTOS_CUSTODIO_ULTIMO_TURNO,
                        )
                    )
                ).all()
            )
        )
        status = quest.status if quest is not None else "unaccepted"
        return S30View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(
                eligible and quest is None and not await self._foreground(session, character.id)
            ),
            reacceptable=bool(
                eligible
                and quest is not None
                and status == "abandoned"
                and not await self._foreground(session, character.id)
            ),
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S30_ID
            ),
            action_available=action_available,
            physical_seals=seals,
            codex_owned=codex_owned,
            achievement_owned=achievement_owned,
            boss_victory_recorded=await self._has_credit(
                session, character.id, "s30.custodian_defeated"
            ),
            bestiary_observations=observations,
        )

    async def _eligible_contact(self, session, character, world) -> bool:
        return bool(
            await self._eligible_location(session, character, world)
            and not await self._foreground(session, character.id)
        )

    async def _eligible_location(self, session, character, world) -> bool:
        if (
            character.level < S30_LEVEL
            or world is None
            or world.region != ALTOS_REGION_LABEL
            or world.location != ALTOS_BASTILHA_LABEL
        ):
            return False
        has_access = await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_BASTILHA_ACCESS_UNLOCK,
            )
        )
        if has_access is None:
            return False
        return bool(
            await self._has_quest_completed(session, character.id, S28_ID)
            and await self._has_quest_completed(session, character.id, P29_ID)
        )

    async def _has_emergency_letters(self, session, character_id: UUID) -> bool:
        if not await self._has_quest_completed(session, character_id, S28_ID):
            return False
        owned = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id,
                        CodexFragment.entry_id == "codex.altos.cartas_emergencia",
                    )
                )
            ).all()
        )
        return set(S28_LETTER_FRAGMENTS).issubset(owned)

    async def _has_quest_completed(self, session, character_id: UUID, quest_id: str) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == quest_id,
                    Quest.status == "completed",
                )
            )
        )

    async def _seals(self, session, character_id: UUID) -> tuple[str, ...]:
        rows = (
            await session.scalars(
                select(CampaignObjectiveCredit.source_key).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S30_ID,
                    CampaignObjectiveCredit.objective_id == "s30.physical_seal",
                    CampaignObjectiveCredit.source_key.in_(S30_PHYSICAL_SEALS),
                )
            )
        ).all()
        return tuple(sorted(set(rows).intersection(S30_PHYSICAL_SEALS)))

    async def _has_credit(self, session, character_id: UUID, objective_id: str) -> bool:
        return bool(
            await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S30_ID,
                    CampaignObjectiveCredit.objective_id == objective_id,
                )
            )
        )

    async def _next_step(self, session, character_id: UUID) -> int:
        if await self._has_credit(session, character_id, "s30.codex_recorded"):
            return 9
        if await self._has_credit(session, character_id, "s30.bestiary_recorded"):
            return 8
        if await self._has_credit(session, character_id, "s30.custodian_defeated"):
            return 7
        if await self._has_credit(session, character_id, "s30.protocol_verified"):
            return 5
        if await self._has_credit(session, character_id, "s30.service_post_opened"):
            return 4
        if set(S30_PHYSICAL_SEALS).issubset(await self._seals(session, character_id)):
            return 3
        if await self._has_credit(session, character_id, "s30.letters_reconstructed"):
            return 2
        return 1

    async def _progress_snapshot(self, session, character_id: UUID) -> dict:
        seals = await self._seals(session, character_id)
        return {
            "physical_seal_ids": list(seals),
            "letters_reconstructed": await self._has_credit(
                session, character_id, "s30.letters_reconstructed"
            ),
            "service_post_opened": await self._has_credit(
                session, character_id, "s30.service_post_opened"
            ),
            "protocol_verified": await self._has_credit(
                session, character_id, "s30.protocol_verified"
            ),
            "custodian_defeated": await self._has_credit(
                session, character_id, "s30.custodian_defeated"
            ),
            "bestiary_recorded": await self._has_credit(
                session, character_id, "s30.bestiary_recorded"
            ),
            "codex_registered": await self._has_credit(
                session, character_id, "s30.codex_recorded"
            ),
        }

    async def _set_step(self, session, quest, character_id: UUID, step: int) -> None:
        quest.step = step
        quest.state_version += 1
        quest.progress = await self._progress_snapshot(session, character_id)

    async def _credit(
        self, session, character_id, objective_id: str, source_key: str, evidence: dict
    ) -> bool:
        return await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S30_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _bestiary_entry(self, session, character_id):
        from asterion.infrastructure.db.models import BestiaryEntry

        return await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == ALTOS_CUSTODIO_ULTIMO_TURNO,
            )
            .with_for_update()
        )

    async def _active_combat(self, session, character_id):
        return await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == S30_MISSION_ID,
                GameActivity.status == "active",
            )
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
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S30_ID)
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S30_ID)
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
    def _at_bastilha(world) -> bool:
        return bool(
            world is not None
            and world.region == ALTOS_REGION_LABEL
            and world.location == ALTOS_BASTILHA_LABEL
        )

    @staticmethod
    def _valid_active(quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S30_CONTENT_VERSION
            and quest.state_version == version
        )

    async def _at_contact(self, session, character, world) -> bool:
        return bool(
            self._at_bastilha(world)
            and await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == ALTOS_BASTILHA_ACCESS_UNLOCK,
                )
            )
        )

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True
