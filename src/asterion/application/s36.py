"""Persistent post-campaign secondary quest S36: Depois da Última Ordem."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import (
    P36_CONTENT_VERSION,
    P36_ID,
    S36_CONTENT_VERSION,
    S36_ID,
    S36_MISSION_ID,
    S36_TITLE,
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
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
)
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEvidence,
    CampaignObjectiveCredit,
    Character,
    CharacterCosmetic,
    CodexEntry,
    CodexFragment,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

S36_REWARD_SOURCE = S36_MISSION_ID
S36_CODEX_ENTRY = "codex.confins.depois_ultima_ordem"
S36_COMPLETION_UNLOCK = "quest.confins.s36.completed"
S36_ACHIEVEMENT = "achievement.confins.s36"
S36_TITLE_COSMETIC = "cosmetic.title.confins.guardiao_testemunhas"
S36_BOSS_ID = "boss.confins.s36.verificador_sem_testemunhas"
S36_LEVEL = 60
S36_XP_REWARD = 101_900
S36_CROWNS_REWARD = 1_250
S36_MATERIAL_REWARDS = (
    ("material.confins.ferro_baliza", "ferro_baliza_a"),
    ("material.confins.ferro_baliza", "ferro_baliza_b"),
    ("material.confins.couro_marcha", "couro_marcha_a"),
    ("material.confins.couro_marcha", "couro_marcha_b"),
    ("material.confins.musgo_limiar", "musgo_limiar_a"),
    ("material.confins.musgo_limiar", "musgo_limiar_b"),
    ("material.confins.po_referencia", "po_referencia_a"),
    ("material.confins.po_referencia", "po_referencia_b"),
)
S36_CONTROL_POINTS = (
    "evidence.confins.s36.controle_seguranca",
    "evidence.confins.s36.ordem_sem_funcao",
    "evidence.confins.s36.verificacao_necessaria",
)
S36_MATERIAL_PROOFS = (
    "evidence.confins.s36.retorno_bloqueado_a",
    "evidence.confins.s36.retorno_bloqueado_b",
)
S36_SHARED_EVIDENCE = (*S36_CONTROL_POINTS, *S36_MATERIAL_PROOFS)
_EVIDENCE_ACTIONS = {
    "inspect_control_safety": S36_CONTROL_POINTS[0],
    "inspect_control_obsolete_order": S36_CONTROL_POINTS[1],
    "inspect_control_verification": S36_CONTROL_POINTS[2],
    "collect_return_proof_a": S36_MATERIAL_PROOFS[0],
    "collect_return_proof_b": S36_MATERIAL_PROOFS[1],
}
_S36_SITES = (CONFINS_ULTIMO_REFUGIO_LABEL, CONFINS_NO_CENTRAL_LABEL)


@dataclass(frozen=True, slots=True)
class S36View:
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
    routines_examined: bool = False
    verifier_victory: bool = False
    bestiary_recorded: bool = False
    codex_recorded: bool = False
    codex_owned: bool = False


class S36Service:
    """Per-character S36 state, sharing only present, eligible field evidence."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        altos_missions: AltosMissionService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.altos_missions = altos_missions

    async def giver(self, actor: int) -> S36View | None:
        return await self._screen(actor, "giver", require_site=True)

    async def offer(self, actor: int) -> S36View | None:
        return await self._screen(actor, "offer", require_site=True)

    async def summary(self, actor: int) -> S36View | None:
        return await self._screen(actor, "summary", require_site=False)

    async def _screen(self, actor: int, kind: str, *, require_site: bool):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if require_site and not self._at_site(world):
                return None
            if quest is None and not self._at_site(world):
                return None
            return await self._view(session, character, quest, world, kind)

    async def resume(self, actor: int) -> S36View | AltosMissionView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            activity_id = await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S36_MISSION_ID,
                    GameActivity.status == "active",
                )
            )
            if activity_id is not None:
                return await self.altos_missions.resume(actor, S36_ID)
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int):
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(self, actor: int, version: int = 0, *, reaccept: bool = False):
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
                or world is None
                or world.region != CONFINS_REGION_LABEL
                or world.location != CONFINS_ULTIMO_REFUGIO_LABEL
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "giver")
            if reaccept:
                if (
                    quest is None
                    or quest.status != "abandoned"
                    or quest.state_version != version
                    or quest.content_version != S36_CONTENT_VERSION
                    or await self._has_completion(session, character.id)
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest.status = "active"
                quest.step = await self._next_step(session, character.id)
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
            else:
                if (
                    quest is not None
                    or version != 0
                    or await self._has_completion(session, character.id)
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S36_ID,
                    title=S36_TITLE,
                    status="active",
                    step=1,
                    content_version=S36_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed_steps": []},
                )
                session.add(quest)
                await session.flush()
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
            if (
                await self._foreground(session, character.id)
                or not await self._eligible(session, character)
                or not self._at_site(world)
            ):
                return await self._view(session, character, quest, world, "objective")

            if quest.step == 1 and action == "examine_civil_routines":
                if world.location != CONFINS_ULTIMO_REFUGIO_LABEL:
                    return await self._view(session, character, quest, world, "objective")
                await self._credit(
                    session,
                    character.id,
                    "s36.routines_examined",
                    "s36.routines_examined",
                    {
                        "useful_safety_routines_preserved": True,
                        "obsolete_order_not_generalized": True,
                        "personal_observation": True,
                    },
                )
                quest.step = 2
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
                return await self._view(session, character, quest, world, "detail")

            if quest.step in {2, 3} and action in _EVIDENCE_ACTIONS:
                if world.location != CONFINS_NO_CENTRAL_LABEL:
                    return await self._view(session, character, quest, world, "objective")
                evidence_id = _EVIDENCE_ACTIONS[action]
                expected_step = 2 if evidence_id in S36_CONTROL_POINTS else 3
                if quest.step != expected_step:
                    return await self._view(session, character, quest, world, "objective")
                await self._share_evidence(
                    session, character_ids, world.location, evidence_id, expected_step
                )
                return await self._refresh_actor_view(session, character.id, world)

            if quest.step == 5 and action == "record_bestiary":
                if world.location != CONFINS_NO_CENTRAL_LABEL or not await self._has_credit(
                    session, character.id, "s36.verifier_defeated"
                ):
                    return await self._view(session, character, quest, world, "objective")
                observed_victory = await session.scalar(
                    select(BestiaryEvidence.id).where(
                        BestiaryEvidence.character_id == character.id,
                        BestiaryEvidence.creature_id == S36_BOSS_ID,
                        BestiaryEvidence.evidence_id == "first_victory",
                    )
                )
                if observed_victory is None:
                    return await self._view(session, character, quest, world, "objective")
                await self._credit(
                    session,
                    character.id,
                    "s36.bestiary_recorded",
                    "s36.bestiary_recorded",
                    {
                        "creature_id": S36_BOSS_ID,
                        "observed_facts_only": True,
                        "automatic_procedure_not_consciousness": True,
                        "personal_observation": True,
                    },
                )
                quest.step = 6
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 6 and action in {
                "narrate_civil_continuity",
                "narrate_verification_needed",
            }:
                if world.location != CONFINS_NO_CENTRAL_LABEL or not await self._has_credit(
                    session, character.id, "s36.bestiary_recorded"
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._ensure(
                    session, CodexEntry, character_id=character.id, entry_id=S36_CODEX_ENTRY
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S36_CODEX_ENTRY,
                    fragment_id=S36_CODEX_ENTRY,
                )
                await self._credit(
                    session,
                    character.id,
                    "s36.codex_recorded",
                    "s36.codex_recorded",
                    {
                        "codex_entry": S36_CODEX_ENTRY,
                        "interpretation": action,
                        "routine_continues_without_global_change": True,
                        "risks_remain": True,
                        "personal_knowledge": True,
                    },
                )
                quest.step = 7
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 7 and action == "conclude_with_haro_sera":
                if (
                    world.location != CONFINS_NO_CENTRAL_LABEL
                    or not await self._has_credit(session, character.id, "s36.codex_recorded")
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._complete(session, character, quest)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "objective")

    async def start_solo_combat(self, actor: int, version: int):
        return await self.altos_missions.start_solo_combat(actor, version, S36_ID)

    async def propose_group_combat(self, actor: int, version: int):
        return await self.altos_missions.propose_group_combat(actor, version, S36_ID)

    async def retry_combat(self, actor: int, version: int):
        return await self.altos_missions.retry_combat(actor, version, S36_ID)

    async def toggle_tracking(self, actor: int, version: int):
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
                None if character.tracked_secondary_quest_id == S36_ID else S36_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int):
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
            if character.tracked_secondary_quest_id == S36_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character: Character, quest: Quest) -> None:
        if (
            not await self._has_credit(session, character.id, "s36.routines_examined")
            or not set(S36_CONTROL_POINTS).issubset(await self._evidence_ids(session, character.id))
            or not set(S36_MATERIAL_PROOFS).issubset(
                await self._evidence_ids(session, character.id)
            )
            or not await self._has_credit(session, character.id, "s36.verifier_defeated")
            or not await self._has_credit(session, character.id, "s36.bestiary_recorded")
            or not await self._has_credit(session, character.id, "s36.codex_recorded")
        ):
            raise RuntimeError(
                "S36 cannot complete before its seven personal and shared objectives"
            )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S36_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S36_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S36_XP_REWARD
            character.crowns += S36_CROWNS_REWARD
            components = [
                RewardComponent(reward_event_id=event.id, kind="xp", quantity=S36_XP_REWARD),
                RewardComponent(
                    reward_event_id=event.id,
                    kind="crowns",
                    quantity=S36_CROWNS_REWARD,
                ),
            ]
            for material_id, reward_key in S36_MATERIAL_REWARDS:
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
                    f"{S36_REWARD_SOURCE}:material:{reward_key}",
                    bound=True,
                )
            session.add_all(components)
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=S36_COMPLETION_UNLOCK,
        )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=S36_ACHIEVEMENT,
        )
        await self._ensure(
            session,
            CharacterCosmetic,
            character_id=character.id,
            cosmetic_id=S36_TITLE_COSMETIC,
            cosmetic_type="title",
            source_achievement_id=S36_ACHIEVEMENT,
        )
        await self._credit(
            session,
            character.id,
            "s36.completed",
            "s36.completed",
            {"completion_unlock": S36_COMPLETION_UNLOCK, "personal_conclusion": True},
        )
        quest.status = "completed"
        quest.step = 7
        quest.state_version += 1
        quest.progress = dict(await self._progress_snapshot(session, character.id)) | {
            "completed": True,
            "completed_steps": [1, 2, 3, 4, 5, 6, 7],
        }
        if character.tracked_secondary_quest_id == S36_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S36View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        progress.update(await self._progress_snapshot(session, character.id))
        gate = await self._eligible(session, character)
        no_foreground = not await self._foreground(session, character.id)
        status = quest.status if quest is not None else "unaccepted"
        at_site = self._at_site(world)
        step_location = (
            CONFINS_ULTIMO_REFUGIO_LABEL
            if quest and quest.step == 1
            else CONFINS_NO_CENTRAL_LABEL
        )
        return S36View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(
                gate and world is not None and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
                and quest is None and no_foreground
                and not await self._has_completion(session, character.id)
            ),
            reacceptable=bool(
                gate and world is not None and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
                and quest is not None and status == "abandoned" and no_foreground
                and not await self._has_completion(session, character.id)
            ),
            tracked=bool(
                quest is not None and status == "active"
                and character.tracked_secondary_quest_id == S36_ID
            ),
            action_available=bool(
                quest is not None and status == "active" and gate and no_foreground
                and at_site and world.location == step_location
            ),
            gate_satisfied=gate,
            evidence=await self._evidence_ids(session, character.id),
            routines_examined=await self._has_credit(
                session, character.id, "s36.routines_examined"
            ),
            verifier_victory=await self._has_credit(session, character.id, "s36.verifier_defeated"),
            bestiary_recorded=await self._has_credit(
                session, character.id, "s36.bestiary_recorded"
            ),
            codex_recorded=await self._has_credit(session, character.id, "s36.codex_recorded"),
            codex_owned=bool(await session.scalar(select(CodexEntry.id).where(
                CodexEntry.character_id == character.id, CodexEntry.entry_id == S36_CODEX_ENTRY
            ))),
        )

    async def _share_evidence(self, session, character_ids, location, evidence_id, step):
        members = await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=S36_ID,
            content_version=S36_CONTENT_VERSION,
            step=step,
            region=CONFINS_REGION_LABEL,
            location=location,
        )
        expected = S36_CONTROL_POINTS if step == 2 else S36_MATERIAL_PROOFS
        objective = "s36.control_point" if step == 2 else "s36.material_proof"
        for member in members:
            if not await self._eligible(session, member.character):
                continue
            if not await self._credit(
                session,
                member.character.id,
                objective,
                evidence_id,
                {"evidence_id": evidence_id, "location": location, "present_and_eligible": True},
            ):
                continue
            evidence = await self._evidence_ids(session, member.character.id)
            progress = dict(member.quest.progress or {})
            progress["field_evidence_ids"] = list(evidence)
            if set(expected).issubset(evidence):
                member.quest.step = step + 1
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {step}
                )
            member.quest.progress = progress
            member.quest.state_version += 1

    async def _refresh_actor_view(self, session, character_id, world):
        character = await session.scalar(
            select(Character)
            .where(Character.id == character_id)
            .with_for_update()
        )
        quest = await self._locked_quest(session, character_id)
        return await self._view(session, character, quest, world, "detail") if character else None

    async def _progress_snapshot(self, session, character_id: UUID) -> dict:
        routines = await self._has_credit(session, character_id, "s36.routines_examined")
        evidence = await self._evidence_ids(session, character_id)
        victory = await self._has_credit(session, character_id, "s36.verifier_defeated")
        bestiary = await self._has_credit(session, character_id, "s36.bestiary_recorded")
        codex = await self._has_credit(session, character_id, "s36.codex_recorded")
        completed = await self._has_credit(session, character_id, "s36.completed")
        steps = []
        if routines:
            steps.append(1)
        if set(S36_CONTROL_POINTS).issubset(evidence):
            steps.append(2)
        if set(S36_MATERIAL_PROOFS).issubset(evidence):
            steps.append(3)
        if victory:
            steps.append(4)
        if bestiary:
            steps.append(5)
        if codex:
            steps.append(6)
        if completed:
            steps.append(7)
        return {
            "routines_examined": routines,
            "field_evidence_ids": list(evidence),
            "verifier_victory": victory,
            "bestiary_recorded": bestiary,
            "codex_recorded": codex,
            "completed": completed,
            "completed_steps": steps,
        }

    async def _next_step(self, session, character_id: UUID) -> int:
        if await self._has_credit(session, character_id, "s36.completed"):
            return 7
        if await self._has_credit(session, character_id, "s36.codex_recorded"):
            return 7
        if await self._has_credit(session, character_id, "s36.bestiary_recorded"):
            return 6
        if await self._has_credit(session, character_id, "s36.verifier_defeated"):
            return 5
        evidence = await self._evidence_ids(session, character_id)
        if set(S36_CONTROL_POINTS).issubset(evidence) and set(
            S36_MATERIAL_PROOFS
        ).issubset(evidence):
            return 4
        if set(S36_CONTROL_POINTS).issubset(evidence):
            return 3
        if await self._has_credit(session, character_id, "s36.routines_examined"):
            return 2
        return 1

    async def _evidence_ids(self, session, character_id: UUID) -> tuple[str, ...]:
        rows = (
            await session.scalars(
                select(CampaignObjectiveCredit.source_key).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S36_ID,
                    CampaignObjectiveCredit.objective_id.in_(
                        ("s36.control_point", "s36.material_proof")
                    ),
                    CampaignObjectiveCredit.source_key.in_(S36_SHARED_EVIDENCE),
                )
            )
        ).all()
        return tuple(sorted(set(rows).intersection(S36_SHARED_EVIDENCE)))

    async def _has_credit(self, session, character_id: UUID, objective_id: str) -> bool:
        return bool(await session.scalar(select(CampaignObjectiveCredit.id).where(
            CampaignObjectiveCredit.character_id == character_id,
            CampaignObjectiveCredit.quest_id == S36_ID,
            CampaignObjectiveCredit.objective_id == objective_id,
        )))

    async def _credit(self, session, character_id, objective_id, source_key, evidence) -> bool:
        exists = await session.scalar(select(CampaignObjectiveCredit.id).where(
            CampaignObjectiveCredit.character_id == character_id,
            CampaignObjectiveCredit.quest_id == S36_ID,
            CampaignObjectiveCredit.objective_id == objective_id,
            CampaignObjectiveCredit.source_key == source_key,
        ))
        if exists is not None:
            return False
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S36_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )
        return True

    async def _eligible(self, session, character: Character | None) -> bool:
        return bool(
            character is not None
            and character.level >= S36_LEVEL
            and await session.scalar(select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == P36_ID,
                Quest.status == "completed",
                Quest.content_version == P36_CONTENT_VERSION,
            ))
        )

    async def _has_completion(self, session, character_id: UUID) -> bool:
        return bool(await session.scalar(select(Unlock.id).where(
            Unlock.character_id == character_id,
            Unlock.unlock_id == S36_COMPLETION_UNLOCK,
        )))

    async def _ensure(self, session, model, **values):
        existing = await session.scalar(select(model).filter_by(**values).with_for_update())
        if existing is None:
            session.add(model(**values))
        return existing

    def _valid_active(self, quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S36_CONTENT_VERSION
            and quest.state_version == version
        )

    async def _character(self, session, actor: int):
        return await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ))

    async def _locked_character(self, session, actor: int):
        return await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ).with_for_update())

    async def _quest(self, session, character_id: UUID):
        return await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == S36_ID,
            )
        )

    async def _locked_quest(self, session, character_id: UUID):
        return await session.scalar(select(Quest).where(
            Quest.character_id == character_id, Quest.quest_id == S36_ID
        ).with_for_update())

    async def _world(self, session, character_id: UUID):
        return await session.get(WorldState, character_id)

    async def _locked_world(self, session, character_id: UUID):
        return await session.scalar(
            select(WorldState)
            .where(WorldState.character_id == character_id)
            .with_for_update()
        )

    async def _foreground(self, session, character_id: UUID) -> bool:
        return bool(await session.scalar(select(GameActivity.id).where(
            GameActivity.character_id == character_id, GameActivity.status == "active"
        )))

    @staticmethod
    def _at_site(world) -> bool:
        return bool(
            world is not None
            and world.region == CONFINS_REGION_LABEL
            and world.location in _S36_SITES
        )
