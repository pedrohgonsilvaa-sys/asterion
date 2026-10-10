"""Shared, idempotent S7/P8 mission progression for Vales dos Enforcados."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import (
    CampaignRosterMember,
    campaign_action_intent,
    campaign_actor_key,
    campaign_combat_for_activity,
    create_campaign_encounter,
    lock_campaign_encounter,
    resolve_campaign_action,
    settle_campaign_encounter,
)
from asterion.application.campaign_objectives import (
    campaign_roster_ids,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.groups import ActivityEligibility, GroupError, GroupService
from asterion.application.progression import consolidate_character_level
from asterion.application.road import RoadService
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    derive_consumable_selection,
    materialize,
    normalize_character_hp,
)
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.road import (
    RULESET,
    Creature,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    ConsumableStack,
    Encounter,
    GameActivity,
    GroupActivityParticipant,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    Unlock,
    WorldState,
)

REGION = "Vales dos Enforcados"
GARGANTA = "Garganta dos Laços"
VIGILIA = "Vigília do Vale"
MATA = "Mata Suspensa"
P7_ID = "P7"
S7_ID = "S7"
P8_ID = "P8"
CONTENT_VERSION = "vales-1.0.3"
S7_TITLE = "Cordas na Névoa"
P8_TITLE = "Entre Galhos Suspensos"
S7_CHECKPOINT = "vde.s7.cordas_na_nevoa"
P8_CHECKPOINT = "vde.p8.entre_galhos_suspensos"
S7_CONTENT = "vde_s7_scripted_combat"
P8_CONTENT = "vde_p8_scripted_combat"
S7_REWARD_SOURCE = "s7.cordas_na_nevoa"
P8_REWARD_SOURCE = "p8.entre_galhos_suspensos"
MATA_LOCATION_ID = "vde.location.mata_suspensa"
MATA_ROUTE_UNLOCK = "route.vde.vigilia_mata"
MATA_HUNT_UNLOCK = "hunt.manual.vde.mata_suspensa"
MATA_EXPLORE_UNLOCK = "explore.vde.mata_suspensa"

# The regional text leaves the scripted species unnamed. This internal common
# combatant uses the global common/balanced level curve and never enters the
# Bestiary or repeatable reward settlement.
_SCRIPTED_FAUNA = Creature(
    "vde_scripted_fauna",
    "Criatura entre as raízes",
    "common",
    "balanced",
    1,
    60,
    0,
    ("investida_instintiva",),
    (("investida_instintiva", "Investida Instintiva", Decimal("1.00"), 0, Decimal(0), 0),),
)


@dataclass(frozen=True, slots=True)
class VDEMissionView:
    character_id: UUID
    quest_id: str
    title: str
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    combat: object | None = None
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    combat_actor_key: str | None = None
    group_size: int = 1
    consumable_options: tuple = ()
    consumable_quantities: tuple = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: object | None = None
    proposal_id: UUID | None = None
    proposal_status: str | None = None


class VDEMissionService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        groups: GroupService | None = None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.groups = groups
        self.road = RoadService(sessions, server_id)

    async def resume(self, actor: int, quest_id: str) -> VDEMissionView | None:
        if quest_id not in {S7_ID, P8_ID}:
            return None
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None:
                return None
            return await self._view(session, character, quest, world, requested_quest_id=quest_id)

    async def resume_active(self, actor: int) -> VDEMissionView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.character_id == character.id,
                    GameActivity.status == "active",
                    GameActivity.content_id.in_((S7_CONTENT, P8_CONTENT)),
                )
                .with_for_update()
            )
            if activity is not None:
                shared, member, _combat = await campaign_combat_for_activity(
                    session, activity.id, character.id
                )
                if shared is not None and member is not None:
                    return await self._view_for_character_activity(session, character, activity.id)
                quest = await self._active_quest_for_character(session, character.id)
                if quest is not None:
                    return await self._view(
                        session, character, quest, await self._world(session, character.id)
                    )
        s7 = await self.resume(actor, S7_ID)
        if s7 is not None and s7.status == "active":
            return s7
        p8 = await self.resume(actor, P8_ID)
        return p8 if p8 is not None and p8.status == "active" else None

    async def board(self, actor: int) -> tuple[VDEMissionView | None, VDEMissionView | None]:
        return await self.resume(actor, S7_ID), await self.resume(actor, P8_ID)

    async def region_access(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return False
            return bool(
                await session.scalar(
                    select(Quest.id).where(
                        Quest.character_id == character.id,
                        Quest.quest_id == P7_ID,
                        Quest.status == "completed",
                    )
                )
            )

    async def start(self, actor: int, quest_id: str) -> VDEMissionView | None:
        if quest_id not in {S7_ID, P8_ID}:
            return None
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None or world is None:
                return None
            if quest is not None:
                return await self._view(
                    session, character, quest, world, requested_quest_id=quest_id
                )
            p7 = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == P7_ID,
                    Quest.status == "completed",
                )
            )
            required_level = 12 if quest_id == S7_ID else 13
            required_location = GARGANTA if quest_id == S7_ID else VIGILIA
            if (
                p7 is None
                or character.level < required_level
                or world.region != REGION
                or world.location != required_location
                or await self._foreground(session, character.id)
            ):
                return await self._view(
                    session, character, None, world, requested_quest_id=quest_id
                )
            progress = {"markers": []} if quest_id == S7_ID else {"roots": []}
            quest = Quest(
                character_id=character.id,
                quest_id=quest_id,
                title=S7_TITLE if quest_id == S7_ID else P8_TITLE,
                status="active",
                step=1,
                content_version=CONTENT_VERSION,
                state_version=0,
                progress=progress,
            )
            session.add(quest)
            await session.flush()
            if quest_id == P8_ID:
                await self._ensure_unlock(session, character.id, MATA_ROUTE_UNLOCK)
            await record_campaign_objective_credit(
                session,
                character_id=character.id,
                quest_id=quest_id,
                objective_id=f"{quest_id.lower()}.started",
                source_key=f"{quest_id.lower()}:start:{character.id}",
                evidence={"location": world.location, "level": character.level},
            )
            return await self._view(session, character, quest, world)

    async def enter_mata(self, actor: int, version: int) -> VDEMissionView | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P8_ID)
            if not self._valid(quest, version, step=1) or character is None or world is None:
                return await self._view(session, character, quest, world)
            if world.region != REGION or world.location != MATA:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, P8_ID, step=1, location=MATA)
            for member in members:
                await self._ensure_location(session, member.character.id, MATA_LOCATION_ID)
                await self._ensure_unlock(session, member.character.id, MATA_EXPLORE_UNLOCK)
                member.quest.step = 2
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "entered_mata": True,
                    "roots": [],
                }
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P8_ID,
                    objective_id="p8.enter_mata",
                    source_key="p8.enter_mata:first_entry",
                    evidence={"region": REGION, "location": MATA, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def examine(
        self, actor: int, quest_id: str, version: int, point: str
    ) -> VDEMissionView | None:
        if quest_id not in {S7_ID, P8_ID}:
            return None
        if point not in {"a", "b", "c"}:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            quest_step = 1 if quest_id == S7_ID else 2
            if character is None or not self._valid(quest, version, step=quest_step):
                return await self._view(session, character, quest, world)
            location = GARGANTA if quest_id == S7_ID else MATA
            key = "markers" if quest_id == S7_ID else "roots"
            members = await self._present(
                session,
                character.id,
                quest_id,
                step=quest_step,
                location=location,
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                points = list(progress.get(key, ()))
                if point in points:
                    continue
                points.append(point)
                progress[key] = sorted(points)
                member.quest.progress = progress
                if len(points) >= 3:
                    member.quest.step = 2 if quest_id == S7_ID else 3
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=quest_id,
                    objective_id=f"{quest_id.lower()}.{key}.{point}",
                    source_key=f"{quest_id.lower()}.{key}.{point}:{location}",
                    evidence={"location": location, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def advance(
        self, actor: int, quest_id: str, version: int, action: str
    ) -> VDEMissionView | None:
        steps = {
            (S7_ID, "rope"): (3, GARGANTA, 4, "s7.find_rope"),
            (S7_ID, "report"): (4, VIGILIA, 5, "s7.report_dara"),
            (P8_ID, "compare"): (4, MATA, 5, "p8.compare_roots"),
            (P8_ID, "masonry"): (5, MATA, 6, "p8.find_masonry"),
            (P8_ID, "record"): (6, MATA, 7, "p8.record_find"),
        }
        config = steps.get((quest_id, action))
        if config is None:
            return await self.resume(actor, quest_id)
        expected_step, location, next_step, objective_id = config
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None or not self._valid(quest, version, step=expected_step):
                return await self._view(session, character, quest, world)
            if world is None or world.region != REGION or world.location != location:
                return await self._view(session, character, quest, world)
            members = await self._present(
                session, character.id, quest_id, step=expected_step, location=location
            )
            for member in members:
                if quest_id == S7_ID and action == "report":
                    await self._complete_s7(session, member.character, member.quest)
                    continue
                progress = dict(member.quest.progress or {})
                progress[action] = True
                member.quest.progress = progress
                member.quest.step = next_step
                member.quest.state_version += 1
                if quest_id == P8_ID and action == "record":
                    await self._ensure_codex(
                        session, member.character.id, "codex.location.mata_suspensa"
                    )
                    await self._ensure_codex(
                        session, member.character.id, "codex.mystery.raizes_que_seguem_pedra"
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.location.mata_suspensa",
                        "codex.fragment.mata.entrada_registrada",
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.mystery.raizes_que_seguem_pedra",
                        "codex.fragment.mata.raizes_sob_a_pedra",
                    )
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=quest_id,
                    objective_id=objective_id,
                    source_key=f"{objective_id}:{location}",
                    evidence={"location": location, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def return_vigilia(self, actor: int, version: int) -> VDEMissionView | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P8_ID)
            if character is None or world is None or not self._valid(quest, version, step=7):
                return await self._view(session, character, quest, world)
            if world.region != REGION or world.location != VIGILIA:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, P8_ID, step=7, location=VIGILIA)
            for member in members:
                await self._complete_p8(session, member.character, member.quest)
            return await self._view(session, character, quest, world)

    async def start_solo_combat(
        self, actor: int, quest_id: str, version: int
    ) -> VDEMissionView | None:
        step = 2 if quest_id == S7_ID else 3
        location = GARGANTA if quest_id == S7_ID else MATA
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None or world is None or not self._valid(quest, version, step=step):
                return await self._view(session, character, quest, world)
            if (
                world.region != REGION
                or world.location != location
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            level = 12 if quest_id == S7_ID else 13
            content_id = S7_CONTENT if quest_id == S7_ID else P8_CONTENT
            activity = await materialize(
                session,
                character,
                content_id,
                _SCRIPTED_FAUNA,
                level,
                flavor="A criatura bloqueia o ponto examinado entre as raízes.",
                opening_log=(
                    "⚔️ Uma criatura se move entre as raízes; "
                    "a missão não identifica uma espécie."
                ),
            )
            progress = dict(quest.progress or {})
            progress.update(activity_id=str(activity.id), awaiting_retry=False)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, quest_id: str, version: int):
        initial = await self.resume(actor, quest_id)
        step = 2 if quest_id == S7_ID else 3
        if initial is None or initial.status != "active" or initial.step != step:
            return initial
        if self.groups is None:
            return await self.start_solo_combat(actor, quest_id, version)
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, quest_id, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_vde",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._combat_eligibility,
            context_payload={
                "quest_id": quest_id,
                "checkpoint": S7_CHECKPOINT if quest_id == S7_ID else P8_CHECKPOINT,
                "title": f"{initial.title} · Encontro Roteirizado",
                "reference_character_id": str(initial.character_id),
                "location": GARGANTA if quest_id == S7_ID else MATA,
            },
            journey_reference_character_id=initial.character_id,
        )
        return replace(initial, proposal_id=proposal.proposal_id, proposal_status=proposal.status)

    async def start_group_combat(self, actor: int, proposal_id: UUID, *, expected_revision: int):
        if self.groups is None:
            return await self.resume_active(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._combat_eligibility,
            create_activity=self._create_group_combat,
        )
        return await self.resume_active(actor)

    async def action_combat(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id=None,
        target_id=None,
        effect_id=None,
    ):
        shared = await self._shared_action(
            actor,
            activity_id,
            version,
            action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
        )
        if shared is not None:
            return shared
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._active_quest_for_character(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id.in_((S7_CONTENT, P8_CONTENT)),
                )
                .with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            if activity.status != "active" or activity.state_version != version:
                return current
            updated = await apply_action(
                session,
                character,
                activity,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                category=_SCRIPTED_FAUNA.category,
            )
            if updated is None or updated.version == version:
                return current
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await normalize_character_hp(session, character)
                quest.step += 1
                progress.update(activity_id=None, awaiting_retry=False, combat_victory=True)
                await record_campaign_objective_credit(
                    session,
                    character_id=character.id,
                    quest_id=quest.quest_id,
                    objective_id=f"{quest.quest_id.lower()}.scripted_encounter_victory",
                    source_key=f"{quest.quest_id.lower()}.combat:{activity.id}",
                    evidence={"result": "victory", "location": world.location if world else None},
                )
            elif updated.result == "defeat":
                activity.status = "failed"
                character.hp = character.max_hp
                progress.update(activity_id=None, awaiting_retry=True)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def campaign_action(
        self, actor: int, activity_id: UUID, version: int, action_index: int, target_code: str
    ):
        view = await self.resume_active(actor)
        if view is None or view.activity_id != activity_id:
            return None
        if view.combat is None or view.combat_actor_key is None:
            return view
        intent = campaign_action_intent(
            view.combat, view.combat_actor_key, action_index, target_code
        )
        if intent is None:
            return view
        action, target = intent
        return await self.action_combat(actor, activity_id, version, action, target_id=target)

    async def consumable_selection(self, actor: int, activity_id: UUID, version: int, **kwargs):
        current = await self.resume_active(actor)
        if current is None or current.activity_id != activity_id or current.combat is None:
            return None
        if current.combat.version != version:
            return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
        return derive_consumable_selection(current, **kwargs)

    async def _shared_action(
        self,
        actor,
        activity_id,
        version,
        action,
        *,
        consumable_id=None,
        target_id=None,
        effect_id=None,
    ):
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _, member_seed, _ = await campaign_combat_for_activity(session, activity_id, seed.id)
            if member_seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id not in {S7_ID, P8_ID}:
                return None
            character = locked.characters.get(seed.id)
            member = next(
                (row for row in locked.members if row.game_activity_id == activity_id), None
            )
            activity = locked.activities.get(activity_id)
            if character is None or member is None or activity is None:
                return None
            stack = None
            if consumable_id is not None:
                stack = await session.scalar(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character.id,
                        ConsumableStack.consumable_id == consumable_id,
                        ConsumableStack.quantity > 0,
                    )
                    .with_for_update()
                )
                if stack is None:
                    return await self._view_for_character_activity(session, character, activity_id)
            updated = resolve_campaign_action(
                locked,
                activity_id=activity_id,
                version=version,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(_SCRIPTED_FAUNA.category, 0),
            )
            if updated.version == version:
                return await self._view_for_character_activity(session, character, activity_id)
            if stack is not None:
                stack.quantity -= 1
            roster_by_id = {row.character_id: row for row in locked.members}
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(
                            Quest.character_id.in_(locked.characters),
                            Quest.quest_id == locked.encounter.quest_id,
                        )
                        .with_for_update()
                    )
                ).all()
            )
            quests = {row.character_id: row for row in quest_rows}
            for character_id, participant in locked.characters.items():
                roster_row = roster_by_id[character_id]
                participant_quest = quests.get(character_id)
                if updated.result == "victory":
                    await normalize_character_hp(session, participant)
                    if roster_row.role == "eligible" and participant_quest is not None:
                        participant_quest.step += 1
                        participant_quest.state_version += 1
                        participant_quest.progress = {
                            **(participant_quest.progress or {}),
                            "activity_id": None,
                            "awaiting_retry": False,
                            "combat_victory": True,
                        }
                        await record_campaign_objective_credit(
                            session,
                            character_id=character_id,
                            quest_id=participant_quest.quest_id,
                            objective_id=f"{participant_quest.quest_id.lower()}.scripted_encounter_victory",
                            source_key=f"{participant_quest.quest_id.lower()}.combat:{locked.encounter.id}",
                            evidence={"result": "victory", "shared": True},
                        )
                elif updated.result == "defeat":
                    participant.hp = participant.max_hp
                    if roster_row.role == "eligible" and participant_quest is not None:
                        participant_quest.state_version += 1
                        participant_quest.progress = {
                            **(participant_quest.progress or {}),
                            "activity_id": None,
                            "awaiting_retry": True,
                        }
            if updated.result:
                await settle_campaign_encounter(session, locked, updated.result)
            return await self._view_for_character_activity(session, character, activity_id)

    async def _combat_eligibility(self, session, character, payload) -> ActivityEligibility:
        quest_id = payload.get("quest_id")
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == quest_id)
        )
        world = await self._world(session, character.id)
        active = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id, GameActivity.status == "active"
            )
        )
        quest_step = 2 if quest_id == S7_ID else 3
        same_location = bool(
            world and world.region == REGION and world.location == payload.get("location")
        )
        if active is not None or not same_location:
            role = "ineligible"
        elif quest is not None and quest.status == "active" and quest.step == quest_step:
            role = "eligible"
        elif quest is None or quest.status == "completed" or (quest and quest.step > quest_step):
            role = "helper"
        else:
            role = "ineligible"
        snapshot = {
            "character_id": str(character.id),
            "role": role,
            "quest_status": quest.status if quest else None,
            "quest_step": quest.step if quest else None,
            "quest_version": quest.state_version if quest else None,
            "location": world.location if world else None,
            "region": world.region if world else None,
            "active_activity": str(active.id) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_group_combat(self, session, proposal, characters) -> str:
        quest_id = proposal.context_payload.get("quest_id")
        content_id = S7_CONTENT if quest_id == S7_ID else P8_CONTENT
        checkpoint = S7_CHECKPOINT if quest_id == S7_ID else P8_CHECKPOINT
        level = 12 if quest_id == S7_ID else 13
        participant_rows = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal.id)
                    .order_by(GroupActivityParticipant.ordinal)
                )
            ).all()
        )
        by_character = {row.character_id: row for row in participant_rows}
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        party = []
        roster = []
        for index, character in enumerate(characters, start=1):
            participant = by_character.get(character.id)
            if participant is None or participant.eligibility not in {"eligible", "helper"}:
                raise GroupError("eligibility_changed")
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment)
            actor_key = campaign_actor_key(index, len(characters))
            party.append(
                PlayerCombatantSpec(
                    fighter_key=actor_key,
                    character_id=str(character.id),
                    name=character.name,
                    character_class=character.character_class,
                    race=character.race,
                    level=character.level,
                    hp=character.hp,
                    equipment_configuration=equipment,
                    active_art_ids=arts.art_ids,
                    active_art_snapshots=tuple(slot.to_data() for slot in arts.slots),
                )
            )
            roster.append(
                CampaignRosterMember(
                    character=character,
                    actor_key=actor_key,
                    role=participant.eligibility,
                    checkpoint=checkpoint,
                )
            )
        lead = characters[0]
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(_SCRIPTED_FAUNA, level, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor="Uma criatura bloqueia o ponto examinado entre as raízes.",
            opening_log=(
                "⚔️ Uma criatura se move entre as raízes; "
                "a missão não identifica uma espécie."
            ),
            active_art_ids=party[0].active_art_ids,
            party=tuple(party),
        )
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=quest_id,
            content_id=content_id,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint=checkpoint,
            campaign_boss=False,
        )
        for member in roster:
            if member.role == "eligible":
                quest = await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == member.character.id, Quest.quest_id == quest_id)
                    .with_for_update()
                )
                shared_member = await session.scalar(
                    select(CampaignSharedEncounterMember).where(
                        CampaignSharedEncounterMember.shared_encounter_id == encounter.id,
                        CampaignSharedEncounterMember.character_id == member.character.id,
                    )
                )
                if quest is not None and shared_member is not None:
                    quest.progress = {
                        **(quest.progress or {}),
                        "activity_id": str(shared_member.game_activity_id),
                        "awaiting_retry": False,
                    }
                    quest.state_version += 1
        return str(encounter.id)

    async def _complete_s7(self, session, character, quest):
        await self._reward(session, character, quest, S7_REWARD_SOURCE, 3840, 140, ())
        await self._ensure_codex(session, character.id, "codex.route.rotas_dos_vales")
        await self._ensure_codex_fragment(
            session,
            character.id,
            "codex.route.rotas_dos_vales",
            "codex.fragment.vales.routes.s7_marker_shift",
        )
        quest.status = "completed"
        quest.step = 5
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _complete_p8(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 1),
            ("material.vde.erva_de_turfa", 2),
            ("material.vde.resina_enredada", 1),
        )
        await self._reward(session, character, quest, P8_REWARD_SOURCE, 10500, 300, materials)
        for unlock_id in (MATA_HUNT_UNLOCK, MATA_EXPLORE_UNLOCK):
            await self._ensure_unlock(session, character.id, unlock_id)
        quest.status = "completed"
        quest.step = 7
        quest.progress = {**(quest.progress or {}), "completed": True, "returned_vigilia": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _reward(self, session, character, quest, source_id, xp, crowns, materials):
        event = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source_id)
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        character.xp += xp
        character.crowns += crowns
        session.add_all(
            [
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=xp),
                RewardComponent(
                    reward_event_id=event.id, kind="crowns", item_id=None, quantity=crowns
                ),
            ]
        )
        for material_id, quantity in materials:
            session.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind="material",
                    item_id=material_id,
                    quantity=quantity,
                    payload={"material_id": material_id, "bound": True},
                )
            )
            await self.road.deliver_material(
                session,
                character,
                material_id,
                quantity,
                f"{source_id}:material:{material_id}",
                bound=True,
            )

    async def _present(self, session, character_id, quest_id, *, step, location):
        return await present_campaign_members(
            session,
            character_ids=await campaign_roster_ids(session, character_id),
            quest_id=quest_id,
            content_version=CONTENT_VERSION,
            step=step,
            region=REGION,
            location=location,
        )

    async def _view(self, session, character, quest, world, *, requested_quest_id=None):
        progress = dict(quest.progress or {}) if quest else {}
        quest_id = quest.quest_id if quest else (requested_quest_id or S7_ID)
        title = S7_TITLE if quest_id == S7_ID else P8_TITLE
        activity = combat = encounter = record = None
        actor_key = None
        group_size = 1
        try:
            activity_id = UUID(progress["activity_id"]) if progress.get("activity_id") else None
        except (TypeError, ValueError):
            activity_id = None
        if activity_id is not None and character is not None:
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if shared is not None:
                activity = await session.get(GameActivity, activity_id)
                encounter = shared
                combat = shared_combat if shared.status == "active" else None
                actor_key = shared_member.actor_key if shared_member else None
                group_size = shared.roster_size
            else:
                content_id = S7_CONTENT if quest_id == S7_ID else P8_CONTENT
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == content_id,
                    )
                )
                if activity is not None:
                    row = (
                        await session.execute(
                            select(Encounter, CombatRecord)
                            .join(CombatRecord)
                            .where(Encounter.game_activity_id == activity.id)
                        )
                    ).one_or_none()
                    if row:
                        encounter, record = row
                        if activity.status == "active":
                            combat = decode(
                                record.snapshot,
                                record.id,
                                activity.ruleset_version,
                                activity.state_version,
                            )
        available = False
        if quest is None:
            required_level = 12 if quest_id == S7_ID else 13
            required_location = GARGANTA if quest_id == S7_ID else VIGILIA
            p7 = (
                await session.scalar(
                    select(Quest.id).where(
                        Quest.character_id == character.id,
                        Quest.quest_id == P7_ID,
                        Quest.status == "completed",
                    )
                )
                if character is not None
                else None
            )
            available = bool(
                character is not None
                and world is not None
                and p7 is not None
                and character.level >= required_level
                and world.region == REGION
                and world.location == required_location
                and await self._foreground(session, character.id) is None
            )
            kind = "offer" if available else "unavailable"
        elif combat is not None:
            kind = "combat"
        elif quest.status == "completed":
            kind = "completed"
        elif quest_id == S7_ID:
            if quest.step == 1:
                kind = "markers"
            elif quest.step == 2:
                kind = "retry" if progress.get("awaiting_retry") else "combat_start"
            elif quest.step == 3:
                kind = "rope"
            else:
                kind = "report"
        else:
            kind = {
                1: "enter_mata",
                2: "roots",
                3: "retry" if progress.get("awaiting_retry") else "combat_start",
                4: "compare",
                5: "masonry",
                6: "record",
                7: "return_vigilia",
            }.get(quest.step, "unavailable")
        options = quantities = ()
        budget = 0
        if (
            activity is not None
            and activity.status == "active"
            and combat is not None
            and character is not None
        ):
            options, quantities, budget = await consumable_state(
                session, character, combat, _SCRIPTED_FAUNA.category, actor_key=actor_key
            )
        return VDEMissionView(
            character_id=character.id if character else UUID(int=0),
            quest_id=quest_id,
            title=title,
            kind=kind,
            status=quest.status if quest else None,
            step=quest.step if quest else None,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level if character else 0,
            available=(quest.status == "active" if quest is not None else available),
            combat=combat,
            activity_id=activity.id if activity else None,
            encounter_id=encounter.id if encounter else None,
            combat_id=record.id if record else None,
            combat_actor_key=actor_key,
            group_size=group_size,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
        )

    async def _view_for_character_activity(self, session, character, activity_id):
        shared, member, combat = await campaign_combat_for_activity(
            session, activity_id, character.id
        )
        activity = await session.get(GameActivity, activity_id)
        if shared is None or member is None or activity is None:
            return None
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == shared.quest_id,
            )
        )
        world = await self._world(session, character.id)
        if quest is None:
            title = S7_TITLE if shared.quest_id == S7_ID else P8_TITLE
            base = VDEMissionView(
                character_id=character.id,
                quest_id=shared.quest_id,
                title=title,
                kind="combat",
                status="helper",
                step=None,
                state_version=0,
                progress={"helper": True, "result": shared.status},
                location=world.location if world else "",
                level=character.level,
                available=False,
            )
        else:
            base = await self._view(session, character, quest, world)
        consumables = ((), (), 0)
        if shared.status == "active" and combat is not None:
            consumables = await consumable_state(
                session,
                character,
                combat,
                _SCRIPTED_FAUNA.category,
                actor_key=member.actor_key,
            )
        if shared.status != "active":
            if quest is not None and member.eligibility == "eligible":
                # Eligible participants now see their own next mission objective.
                # Helpers without quest credit receive a result-only view below.
                return replace(
                    base,
                    activity_id=None,
                    encounter_id=shared.id,
                    combat=None,
                    group_size=shared.roster_size,
                )
            return replace(
                base,
                kind="combat_result",
                progress={"helper": True, "result": shared.status},
                activity_id=None,
                encounter_id=shared.id,
                combat=None,
                combat_actor_key=member.actor_key,
                group_size=shared.roster_size,
            )
        return replace(
            base,
            kind="combat",
            combat=combat,
            activity_id=activity.id,
            encounter_id=shared.id,
            combat_id=None,
            combat_actor_key=member.actor_key,
            group_size=shared.roster_size,
            consumable_options=consumables[0],
            consumable_quantities=consumables[1],
            consumable_budget_limit=consumables[2],
        )

    async def _locked_state(self, session, actor, quest_id):
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(
            select(Quest)
            .where(Quest.character_id == character.id, Quest.quest_id == quest_id)
            .with_for_update()
        )
        world = await self._world(session, character.id)
        return character, quest, world

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id).with_for_update()
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id, GameActivity.status == "active"
            )
        )

    async def _active_quest_for_character(self, session, character_id):
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id.in_((S7_ID, P8_ID)),
                Quest.status == "active",
            )
            .with_for_update()
        )

    @staticmethod
    def _valid(quest, version, *, step):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == CONTENT_VERSION
            and quest.state_version == version
            and quest.step == step
        )

    async def _ensure_location(self, session, character_id, location_id):
        if (
            await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id == location_id,
                )
            )
            is None
        ):
            session.add(LocationDiscovery(character_id=character_id, location_id=location_id))

    async def _ensure_unlock(self, session, character_id, unlock_id):
        if (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id, Unlock.unlock_id == unlock_id
                )
            )
            is None
        ):
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))

    async def _ensure_codex(self, session, character_id, entry_id):
        if (
            await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character_id, CodexEntry.entry_id == entry_id
                )
            )
            is None
        ):
            session.add(CodexEntry(character_id=character_id, entry_id=entry_id))

    async def _ensure_codex_fragment(self, session, character_id, entry_id, fragment_id):
        if (
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.fragment_id == fragment_id,
                )
            )
            is None
        ):
            await self._ensure_codex(session, character_id, entry_id)
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
            )
