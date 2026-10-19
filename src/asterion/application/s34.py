"""Persistent secondary quest S34: A Testemunha de Ontem."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import (
    P34_CONTENT_VERSION,
    P34_ID,
    S34_CONTENT_VERSION,
    S34_ID,
    S34_MISSION_ID,
    S34_TITLE,
    AltosMissionService,
    AltosMissionView,
)
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import (
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
)
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

S34_REWARD_SOURCE = S34_MISSION_ID
S34_CODEX_ENTRY = "codex.confins.testemunha_ontem"
S34_CODEX_FRAGMENT = S34_CODEX_ENTRY
S34_COMPLETION_UNLOCK = "quest.confins.s34.completed"
S34_LEVEL = 57
S34_XP_REWARD = 65_275
S34_CROWNS_REWARD = 720
S34_MATERIAL_REWARDS = (
    ("material.confins.ferro_baliza", "ferro_baliza"),
    ("material.confins.couro_marcha", "couro_marcha"),
    ("material.confins.musgo_limiar", "musgo_limiar"),
    ("material.confins.po_referencia", "po_referencia"),
)
S34_EVIDENCE = (
    "evidence.confins.s34.marca_fisica_a",
    "evidence.confins.s34.marca_fisica_b",
    "evidence.confins.s34.ficha_custodia",
)

_EVIDENCE_ACTIONS = {
    "inspect_mark_a": S34_EVIDENCE[0],
    "inspect_mark_b": S34_EVIDENCE[1],
    "inspect_chain_of_custody": S34_EVIDENCE[2],
}
_EVIDENCE_LOCATIONS = {
    S34_EVIDENCE[0]: CONFINS_FRATURAS_LIMIAR_LABEL,
    S34_EVIDENCE[1]: CONFINS_NO_CENTRAL_LABEL,
    S34_EVIDENCE[2]: CONFINS_NO_CENTRAL_LABEL,
}
_S34_SITES = (CONFINS_FRATURAS_LIMIAR_LABEL, CONFINS_NO_CENTRAL_LABEL)


@dataclass(frozen=True, slots=True)
class S34View:
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
    evidence: tuple[str, ...] = ()
    testimony_received: bool = False
    andarilho_victory: bool = False
    reconciliation_recorded: bool = False
    codex_recorded: bool = False
    codex_owned: bool = False


class S34Service:
    """Per-character S34 state with shared field evidence and scripted combat."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        altos_missions: AltosMissionService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.altos_missions = altos_missions

    async def giver(self, actor: int) -> S34View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_site(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S34View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_site(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S34View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_site(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S34View | AltosMissionView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S34_MISSION_ID,
                    GameActivity.status == "active",
                )
            )
            if activity is not None:
                return await self.altos_missions.resume(actor, S34_ID)
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int) -> S34View | AltosMissionView | None:
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S34View | None:
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
                not await self._eligible(session, character)
                or not self._at_site(world)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "giver")
            if reaccept:
                if (
                    quest is None
                    or quest.status != "abandoned"
                    or quest.state_version != version
                    or quest.content_version != S34_CONTENT_VERSION
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest.status = "active"
                quest.step = await self._next_step(session, character.id)
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
            else:
                if quest is not None or version != 0 or await self._has_completion(
                    session, character.id
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S34_ID,
                    title=S34_TITLE,
                    status="active",
                    step=2,
                    content_version=S34_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed_steps": [1], "testimony_received": True},
                )
                session.add(quest)
                await session.flush()
                await self._credit(
                    session,
                    character.id,
                    "s34.testimony_received",
                    "s34.testimony_received",
                    {
                        "document_date_precedes_apparent_emission": True,
                        "custody_chain_to_verify": True,
                        "apparent_inversion_not_proof_of_prophecy": True,
                        "personal_acceptance": True,
                    },
                )
            return await self._view(session, character, quest, world, "detail")

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
            if not await self._eligible(session, character) or not self._at_site(world):
                return await self._view(session, character, quest, world, "objective")

            if quest.step == 2 and action in _EVIDENCE_ACTIONS:
                evidence_id = _EVIDENCE_ACTIONS[action]
                if world.location != _EVIDENCE_LOCATIONS[evidence_id]:
                    return await self._view(session, character, quest, world, "objective")
                await self._share_evidence(
                    session,
                    character_ids,
                    world.location,
                    evidence_id,
                )
                return await self._refresh_actor_view(
                    session, character.id, world, "detail"
                )

            if quest.step == 4 and action == "reconcile_testimony":
                evidence = await self._evidence_ids(session, character.id)
                if (
                    not set(S34_EVIDENCE).issubset(evidence)
                    or not await self._has_credit(
                        session, character.id, "s34.andarilho_defeated"
                    )
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._credit(
                    session,
                    character.id,
                    "s34.testimony_reconciled",
                    "s34.testimony_reconciled",
                    {
                        "document_date_preserved": True,
                        "physical_marks_preserved": True,
                        "custody_chain_verified": True,
                        "apparent_event_order_preserved": True,
                        "complete_explanation_absent": True,
                        "no_prophecy_or_controlled_time_travel_claim": True,
                        "personal_interpretation": True,
                    },
                )
                quest.step = 5
                quest.state_version += 1
                quest.progress = await self._progress_snapshot(session, character.id)
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 5 and action == "record_codex":
                if not await self._has_credit(
                    session, character.id, "s34.testimony_reconciled"
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=S34_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S34_CODEX_ENTRY,
                    fragment_id=S34_CODEX_FRAGMENT,
                )
                await self._credit(
                    session,
                    character.id,
                    "s34.codex_recorded",
                    "s34.codex_recorded",
                    {
                        "codex_entry": S34_CODEX_ENTRY,
                        "evidence_ids": list(S34_EVIDENCE),
                        "documents_and_observations_preserved": True,
                        "chronology_limits_preserved": True,
                        "personal_knowledge": True,
                    },
                )
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 5 and action == "conclude_with_talen":
                if not await self._has_credit(session, character.id, "s34.codex_recorded"):
                    return await self._view(session, character, quest, world, "objective")
                await self._complete(session, character, quest)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "objective")

    async def start_solo_combat(self, actor: int, version: int):
        return await self.altos_missions.start_solo_combat(actor, version, S34_ID)

    async def propose_group_combat(self, actor: int, version: int):
        return await self.altos_missions.propose_group_combat(actor, version, S34_ID)

    async def retry_combat(self, actor: int, version: int):
        return await self.altos_missions.retry_combat(actor, version, S34_ID)

    async def toggle_tracking(self, actor: int, version: int) -> S34View | None:
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
                None if character.tracked_secondary_quest_id == S34_ID else S34_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S34View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S34View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            await lock_campaign_roster(session, seed.id)
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
            if character.tracked_secondary_quest_id == S34_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character: Character, quest: Quest) -> None:
        if (
            not await self._has_credit(session, character.id, "s34.testimony_received")
            or not await self._has_credit(session, character.id, "s34.testimony_reconciled")
            or not await self._has_credit(session, character.id, "s34.andarilho_defeated")
            or not await self._has_credit(session, character.id, "s34.codex_recorded")
            or not set(S34_EVIDENCE).issubset(
                await self._evidence_ids(session, character.id)
            )
        ):
            raise RuntimeError("S34 cannot complete before its distinct evidence and victory")

        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S34_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S34_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S34_XP_REWARD
            character.crowns += S34_CROWNS_REWARD
            components = [
                RewardComponent(
                    reward_event_id=event.id,
                    kind="xp",
                    quantity=S34_XP_REWARD,
                ),
                RewardComponent(
                    reward_event_id=event.id,
                    kind="crowns",
                    quantity=S34_CROWNS_REWARD,
                ),
            ]
            for material_id, reward_key in S34_MATERIAL_REWARDS:
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=material_id,
                        quantity=1,
                        payload={"material_id": material_id, "bound": True},
                    )
                )
                await self.altos_missions.road.deliver_material(
                    session,
                    character,
                    material_id,
                    1,
                    f"{S34_REWARD_SOURCE}:material:{reward_key}",
                    bound=True,
                )
            session.add_all(components)

        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=S34_COMPLETION_UNLOCK,
        )
        await self._credit(
            session,
            character.id,
            "s34.completed",
            "s34.completed",
            {"completion_unlock": S34_COMPLETION_UNLOCK, "personal_conclusion": True},
        )
        quest.status = "completed"
        quest.step = 5
        quest.state_version += 1
        quest.progress = dict(await self._progress_snapshot(session, character.id)) | {
            "completed": True,
            "completed_steps": [1, 2, 3, 4, 5],
        }
        if character.tracked_secondary_quest_id == S34_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S34View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        progress.update(await self._progress_snapshot(session, character.id))
        gate_satisfied = await self._eligible(session, character)
        no_foreground = not await self._foreground(session, character.id)
        status = quest.status if quest is not None else "unaccepted"
        at_site = self._at_site(world)
        evidence = await self._evidence_ids(session, character.id)
        step_site = at_site
        if quest is not None and quest.step == 2:
            step_site = step_site and world.location in set(_EVIDENCE_LOCATIONS.values())
        return S34View(
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
                and at_site
                and quest is None
                and no_foreground
                and not await self._has_completion(session, character.id)
            ),
            reacceptable=bool(
                gate_satisfied
                and at_site
                and quest is not None
                and status == "abandoned"
                and no_foreground
            ),
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S34_ID
            ),
            action_available=bool(
                quest is not None
                and status == "active"
                and gate_satisfied
                and no_foreground
                and step_site
            ),
            gate_satisfied=gate_satisfied,
            evidence=evidence,
            testimony_received=await self._has_credit(
                session, character.id, "s34.testimony_received"
            ),
            andarilho_victory=await self._has_credit(
                session, character.id, "s34.andarilho_defeated"
            ),
            reconciliation_recorded=await self._has_credit(
                session, character.id, "s34.testimony_reconciled"
            ),
            codex_recorded=await self._has_credit(
                session, character.id, "s34.codex_recorded"
            ),
            codex_owned=bool(
                await session.scalar(
                    select(CodexEntry.id).where(
                        CodexEntry.character_id == character.id,
                        CodexEntry.entry_id == S34_CODEX_ENTRY,
                    )
                )
            ),
        )

    async def _share_evidence(
        self,
        session,
        character_ids: tuple[UUID, ...],
        location: str,
        evidence_id: str,
    ) -> None:
        members = await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=S34_ID,
            content_version=S34_CONTENT_VERSION,
            step=2,
            region=CONFINS_REGION_LABEL,
            location=location,
        )
        for member in members:
            if not await self._eligible(session, member.character):
                continue
            created = await self._credit(
                session,
                member.character.id,
                "s34.field_evidence",
                evidence_id,
                {
                    "evidence_id": evidence_id,
                    "evidence_location": location,
                    "shared_evidence": True,
                    "participant_present_and_eligible": True,
                },
            )
            if not created:
                continue
            evidence = await self._evidence_ids(session, member.character.id)
            progress = dict(member.quest.progress or {})
            progress["evidence_ids"] = list(evidence)
            if set(S34_EVIDENCE).issubset(evidence):
                member.quest.step = 3
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {2}
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
        testimony = await self._has_credit(session, character_id, "s34.testimony_received")
        evidence = await self._evidence_ids(session, character_id)
        victory = await self._has_credit(session, character_id, "s34.andarilho_defeated")
        reconciled = await self._has_credit(
            session, character_id, "s34.testimony_reconciled"
        )
        codex = await self._has_credit(session, character_id, "s34.codex_recorded")
        completed = await self._has_credit(session, character_id, "s34.completed")
        steps: list[int] = []
        if testimony:
            steps.append(1)
        if set(S34_EVIDENCE).issubset(evidence):
            steps.append(2)
        if victory:
            steps.append(3)
        if reconciled:
            steps.append(4)
        if completed:
            steps.append(5)
        return {
            "testimony_received": testimony,
            "field_evidence_ids": list(evidence),
            "andarilho_victory": victory,
            "testimony_reconciled": reconciled,
            "codex_recorded": codex,
            "completed": completed,
            "completed_steps": steps,
        }

    async def _next_step(self, session, character_id: UUID) -> int:
        if await self._has_credit(session, character_id, "s34.completed"):
            return 5
        if await self._has_credit(session, character_id, "s34.codex_recorded"):
            return 5
        if await self._has_credit(session, character_id, "s34.testimony_reconciled"):
            return 5
        if await self._has_credit(session, character_id, "s34.andarilho_defeated"):
            return 4
        if set(S34_EVIDENCE).issubset(await self._evidence_ids(session, character_id)):
            return 3
        if await self._has_credit(session, character_id, "s34.testimony_received"):
            return 2
        return 1

    async def _evidence_ids(self, session, character_id: UUID) -> tuple[str, ...]:
        rows = (
            await session.scalars(
                select(CampaignObjectiveCredit.source_key).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S34_ID,
                    CampaignObjectiveCredit.objective_id == "s34.field_evidence",
                    CampaignObjectiveCredit.source_key.in_(S34_EVIDENCE),
                )
            )
        ).all()
        return tuple(sorted(set(rows).intersection(S34_EVIDENCE)))

    async def _has_credit(self, session, character_id: UUID, objective_id: str) -> bool:
        return bool(
            await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S34_ID,
                    CampaignObjectiveCredit.objective_id == objective_id,
                )
            )
        )

    async def _credit(
        self,
        session,
        character_id: UUID,
        objective_id: str,
        source_key: str,
        evidence: dict,
    ) -> bool:
        existing = await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == S34_ID,
                CampaignObjectiveCredit.objective_id == objective_id,
                CampaignObjectiveCredit.source_key == source_key,
            )
        )
        if existing is not None:
            return False
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S34_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )
        return True

    async def _eligible(self, session, character: Character | None) -> bool:
        return bool(
            character is not None
            and character.level >= S34_LEVEL
            and await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == P34_ID,
                    Quest.status == "completed",
                    Quest.content_version == P34_CONTENT_VERSION,
                )
            )
        )

    async def _has_completion(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == S34_COMPLETION_UNLOCK,
                )
            )
        )

    async def _ensure(self, session, model, **values):
        existing = await session.scalar(select(model).filter_by(**values).with_for_update())
        if existing is None:
            session.add(model(**values))
        return existing

    def _valid_active(self, quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S34_CONTENT_VERSION
            and quest.state_version == version
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
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S34_ID)
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S34_ID)
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
    def _at_site(world) -> bool:
        return bool(
            world is not None
            and world.region == CONFINS_REGION_LABEL
            and world.location in _S34_SITES
        )
