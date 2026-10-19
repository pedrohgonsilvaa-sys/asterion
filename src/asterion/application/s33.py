"""Persistent secondary quest S33: Nomes em Ordem Errada."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import P33_CONTENT_VERSION, P33_ID, AltosMissionService
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import (
    CONFINS_FRATURAS_ACCESS_UNLOCK,
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
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

S33_ID = "S33"
S33_MISSION_ID = "mission.confins.s33"
S33_TITLE = "Nomes em Ordem Errada"
S33_CONTENT_VERSION = "confins-1.0.0"
S33_REWARD_SOURCE = S33_MISSION_ID
S33_CODEX_ENTRY = "codex.confins.nomes_ordem_errada"
S33_CODEX_FRAGMENT = "mission.confins.s33.nomes_ordem_errada"
S33_COMPLETION_UNLOCK = "quest.confins.s33.completed"
S33_LEVEL = 55
S33_XP_REWARD = 35_060
S33_CROWNS_REWARD = 460
S33_FERRO_BALIZA = "material.confins.ferro_baliza"
S33_MUSGO_LIMIAR = "material.confins.musgo_limiar"
S33_DOCUMENT_LISTS = (
    "evidence.confins.s33.document_list_a",
    "evidence.confins.s33.document_list_b",
)
S33_FIELD_INSCRIPTIONS = (
    "evidence.confins.s33.field_inscription_a",
    "evidence.confins.s33.field_inscription_b",
)

_INSCRIPTION_ACTIONS = {
    "inspect_inscription_a": S33_FIELD_INSCRIPTIONS[0],
    "inspect_inscription_b": S33_FIELD_INSCRIPTIONS[1],
}


@dataclass(frozen=True, slots=True)
class S33View:
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
    field_inscriptions: tuple[str, ...] = ()
    lists_received: bool = False
    analysis_recorded: bool = False
    codex_recorded: bool = False
    codex_owned: bool = False


class S33Service:
    """Per-character S33 state, distinct shared evidence, and one-time reward."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        altos_missions: AltosMissionService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.altos_missions = altos_missions

    async def giver(self, actor: int) -> S33View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_refuge(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S33View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_refuge(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S33View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_refuge(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S33View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int) -> S33View | None:
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S33View | None:
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
                or not self._at_refuge(world)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "giver")
            if reaccept:
                if (
                    quest is None
                    or quest.status != "abandoned"
                    or quest.state_version != version
                    or quest.content_version != S33_CONTENT_VERSION
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest.status = "active"
                quest.step = await self._next_step(session, character.id)
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
            else:
                if quest is not None or version != 0 or await self._has_completion_unlock(
                    session, character.id
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S33_ID,
                    title=S33_TITLE,
                    status="active",
                    step=2,
                    content_version=S33_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed_steps": [1], "lists_received": True},
                )
                session.add(quest)
                await session.flush()
                await self._credit(
                    session,
                    character.id,
                    "s33.lists_received",
                    "s33.lists_received",
                    {
                        "giver_id": "npc.confins.roven_pell",
                        "document_list_ids": list(S33_DOCUMENT_LISTS),
                        "personal_acceptance": True,
                    },
                )
            return await self._view(session, character, quest, world, "detail")

    async def advance(self, actor: int, version: int, action: str) -> S33View | None:
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
            if not await self._eligible(session, character):
                return await self._view(session, character, quest, world, "objective")

            if quest.step == 2 and action in _INSCRIPTION_ACTIONS:
                if not await self._eligible_at_fraturas(session, character, world):
                    return await self._view(session, character, quest, world, "objective")
                await self._share_inscription(
                    session,
                    character_ids,
                    _INSCRIPTION_ACTIONS[action],
                )
                return await self._refresh_actor_view(
                    session, character.id, world, "detail"
                )

            if quest.step == 3 and action == "analyze_documents":
                inscriptions = await self._inscription_ids(session, character.id)
                if (
                    not self._at_refuge(world)
                    or not set(S33_FIELD_INSCRIPTIONS).issubset(inscriptions)
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._credit(
                    session,
                    character.id,
                    "s33.documents_analyzed",
                    "s33.documents_analyzed",
                    {
                        "analyst_id": "npc.confins.roven_pell",
                        "document_list_ids": list(S33_DOCUMENT_LISTS),
                        "field_inscription_ids": list(inscriptions),
                        "proven_copy_error": True,
                        "material_discrepancy_unresolved": True,
                        "both_evidences_preserved": True,
                        "does_not_explain_every_difference_as_avesso": True,
                        "personal_analysis": True,
                    },
                )
                quest.step = 4
                quest.state_version += 1
                quest.progress = await self._progress_snapshot(session, character.id)
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 4 and action == "record_codex":
                if (
                    not self._at_refuge(world)
                    or not await self._has_credit(
                        session, character.id, "s33.documents_analyzed"
                    )
                ):
                    return await self._view(session, character, quest, world, "objective")
                inscription_ids = await self._inscription_ids(session, character.id)
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=S33_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S33_CODEX_ENTRY,
                    fragment_id=S33_CODEX_FRAGMENT,
                )
                await self._credit(
                    session,
                    character.id,
                    "s33.codex_recorded",
                    "s33.codex_recorded",
                    {
                        "codex_entry": S33_CODEX_ENTRY,
                        "mission_fragment": S33_CODEX_FRAGMENT,
                        "document_list_ids": list(S33_DOCUMENT_LISTS),
                        "field_inscription_ids": list(inscription_ids),
                        "proven_copy_error": True,
                        "material_discrepancy_unresolved": True,
                        "preserves_both_evidences": True,
                        "personal_knowledge": True,
                    },
                )
                quest.step = 5
                quest.state_version += 1
                quest.progress = await self._progress_snapshot(session, character.id)
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 5 and action == "conclude_with_roven":
                if (
                    not self._at_refuge(world)
                    or not await self._has_credit(
                        session, character.id, "s33.codex_recorded"
                    )
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._complete(session, character, quest)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "objective")

    async def toggle_tracking(self, actor: int, version: int) -> S33View | None:
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
                None if character.tracked_secondary_quest_id == S33_ID else S33_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S33View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S33View | None:
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
            if character.tracked_secondary_quest_id == S33_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character: Character, quest: Quest) -> None:
        required = (
            "s33.lists_received",
            "s33.documents_analyzed",
            "s33.codex_recorded",
        )
        if not all(
            [await self._has_credit(session, character.id, objective) for objective in required]
        ) or not set(S33_FIELD_INSCRIPTIONS).issubset(
            await self._inscription_ids(session, character.id)
        ):
            raise RuntimeError("S33 cannot complete before its distinct persistent evidence")

        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S33_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S33_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S33_XP_REWARD
            character.crowns += S33_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        quantity=S33_XP_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        quantity=S33_CROWNS_REWARD,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S33_FERRO_BALIZA,
                        quantity=1,
                        payload={"material_id": S33_FERRO_BALIZA, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S33_MUSGO_LIMIAR,
                        quantity=1,
                        payload={"material_id": S33_MUSGO_LIMIAR, "bound": True},
                    ),
                )
            )
            await self.altos_missions.road.deliver_material(
                session,
                character,
                S33_FERRO_BALIZA,
                1,
                f"{S33_REWARD_SOURCE}:material:ferro_baliza",
                bound=True,
            )
            await self.altos_missions.road.deliver_material(
                session,
                character,
                S33_MUSGO_LIMIAR,
                1,
                f"{S33_REWARD_SOURCE}:material:musgo_limiar",
                bound=True,
            )
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=S33_COMPLETION_UNLOCK,
        )
        await self._credit(
            session,
            character.id,
            "s33.completed",
            "s33.completed",
            {"completion_unlock": S33_COMPLETION_UNLOCK, "personal_conclusion": True},
        )
        quest.status = "completed"
        quest.step = 5
        quest.state_version += 1
        quest.progress = dict(await self._progress_snapshot(session, character.id)) | {
            "completed": True,
            "completed_steps": [1, 2, 3, 4, 5],
        }
        if character.tracked_secondary_quest_id == S33_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S33View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        progress.update(await self._progress_snapshot(session, character.id))
        gate_satisfied = await self._eligible(session, character)
        no_foreground = not await self._foreground(session, character.id)
        status = quest.status if quest is not None else "unaccepted"
        at_refuge = self._at_refuge(world)
        at_fraturas = await self._eligible_at_fraturas(session, character, world)
        step = quest.step if quest is not None else 1
        action_location = at_fraturas if step == 2 else at_refuge
        return S33View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=step,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(
                gate_satisfied
                and at_refuge
                and quest is None
                and no_foreground
                and not await self._has_completion_unlock(session, character.id)
            ),
            reacceptable=bool(
                gate_satisfied
                and at_refuge
                and quest is not None
                and status == "abandoned"
                and no_foreground
            ),
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S33_ID
            ),
            action_available=bool(
                quest is not None
                and status == "active"
                and gate_satisfied
                and no_foreground
                and action_location
            ),
            gate_satisfied=gate_satisfied,
            field_inscriptions=await self._inscription_ids(session, character.id),
            lists_received=await self._has_credit(
                session, character.id, "s33.lists_received"
            ),
            analysis_recorded=await self._has_credit(
                session, character.id, "s33.documents_analyzed"
            ),
            codex_recorded=await self._has_credit(
                session, character.id, "s33.codex_recorded"
            ),
            codex_owned=bool(
                await session.scalar(
                    select(CodexEntry.id).where(
                        CodexEntry.character_id == character.id,
                        CodexEntry.entry_id == S33_CODEX_ENTRY,
                    )
                )
            ),
        )

    async def _share_inscription(
        self,
        session,
        character_ids: tuple[UUID, ...],
        inscription_id: str,
    ) -> None:
        members = await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=S33_ID,
            content_version=S33_CONTENT_VERSION,
            step=2,
            region=CONFINS_REGION_LABEL,
            location=CONFINS_FRATURAS_LIMIAR_LABEL,
        )
        for member in members:
            if not await self._eligible_at_fraturas(
                session, member.character, member.world
            ):
                continue
            created = await self._credit(
                session,
                member.character.id,
                "s33.field_inscription",
                inscription_id,
                {
                    "physical_inscription_id": inscription_id,
                    "shared_evidence": True,
                    "credited_by_character_id": str(member.character.id),
                },
            )
            if not created:
                continue
            inscriptions = await self._inscription_ids(session, member.character.id)
            progress = dict(member.quest.progress or {})
            progress["field_inscription_ids"] = list(inscriptions)
            if set(S33_FIELD_INSCRIPTIONS).issubset(inscriptions):
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
        accepted = await self._has_credit(session, character_id, "s33.lists_received")
        inscriptions = await self._inscription_ids(session, character_id)
        analyzed = await self._has_credit(session, character_id, "s33.documents_analyzed")
        codex = await self._has_credit(session, character_id, "s33.codex_recorded")
        completed = await self._has_credit(session, character_id, "s33.completed")
        completed_steps = []
        if accepted:
            completed_steps.append(1)
        if set(S33_FIELD_INSCRIPTIONS).issubset(inscriptions):
            completed_steps.append(2)
        if analyzed:
            completed_steps.append(3)
        if codex:
            completed_steps.append(4)
        if completed:
            completed_steps.append(5)
        return {
            "lists_received": accepted,
            "document_list_ids": list(S33_DOCUMENT_LISTS) if accepted else [],
            "field_inscription_ids": list(inscriptions),
            "documents_analyzed": analyzed,
            "proven_copy_error": analyzed,
            "material_discrepancy_unresolved": analyzed,
            "codex_recorded": codex,
            "completed": completed,
            "completed_steps": completed_steps,
        }

    async def _next_step(self, session, character_id: UUID) -> int:
        if await self._has_credit(session, character_id, "s33.completed"):
            return 5
        if await self._has_credit(session, character_id, "s33.codex_recorded"):
            return 5
        if await self._has_credit(session, character_id, "s33.documents_analyzed"):
            return 4
        if set(S33_FIELD_INSCRIPTIONS).issubset(
            await self._inscription_ids(session, character_id)
        ):
            return 3
        if await self._has_credit(session, character_id, "s33.lists_received"):
            return 2
        return 1

    async def _inscription_ids(self, session, character_id: UUID) -> tuple[str, ...]:
        rows = (
            await session.scalars(
                select(CampaignObjectiveCredit.source_key).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S33_ID,
                    CampaignObjectiveCredit.objective_id == "s33.field_inscription",
                    CampaignObjectiveCredit.source_key.in_(S33_FIELD_INSCRIPTIONS),
                )
            )
        ).all()
        return tuple(sorted(set(rows).intersection(S33_FIELD_INSCRIPTIONS)))

    async def _has_credit(
        self, session, character_id: UUID, objective_id: str
    ) -> bool:
        return bool(
            await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S33_ID,
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
                CampaignObjectiveCredit.quest_id == S33_ID,
                CampaignObjectiveCredit.objective_id == objective_id,
                CampaignObjectiveCredit.source_key == source_key,
            )
        )
        if existing is not None:
            return False
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S33_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )
        return True

    async def _eligible(self, session, character: Character | None) -> bool:
        return bool(
            character is not None
            and character.level >= S33_LEVEL
            and await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == P33_ID,
                    Quest.status == "completed",
                    Quest.content_version == P33_CONTENT_VERSION,
                )
            )
        )

    async def _eligible_at_fraturas(self, session, character, world) -> bool:
        return bool(
            self._at_fraturas(world)
            and await self._eligible(session, character)
            and await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == CONFINS_FRATURAS_ACCESS_UNLOCK,
                )
            )
        )

    async def _has_completion_unlock(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == S33_COMPLETION_UNLOCK,
                )
            )
        )

    async def _ensure(self, session, model, **values) -> bool:
        existing = await session.scalar(
            select(model).filter_by(**values).with_for_update()
        )
        if existing is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True

    def _valid_active(self, quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S33_CONTENT_VERSION
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
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S33_ID)
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S33_ID)
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
    def _at_refuge(world) -> bool:
        return bool(
            world is not None
            and world.region == CONFINS_REGION_LABEL
            and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
        )

    @staticmethod
    def _at_fraturas(world) -> bool:
        return bool(
            world is not None
            and world.region == CONFINS_REGION_LABEL
            and world.location == CONFINS_FRATURAS_LIMIAR_LABEL
        )
