"""Authoritative P7 flow for Vales dos Enforcados: A Estrada Estrangulada."""
# ruff: noqa: E501

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
    Achievement,
    Brazier,
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

P7_ID = "P7"
P7_TITLE = "A Estrada Estrangulada"
P7_VERSION = "vales-1.0.3"
P7_CONTENT_ID = "p7_scripted_regional_fauna"
P7_CHECKPOINT = "p7.fauna_regional"
P7_REWARD_SOURCE = "p7.a_estrada_estrangulada"

REGION = "Vales dos Enforcados"
GARGANTA = "Garganta dos Laços"
VIGILIA = "Vigília do Vale"
GARGANTA_LOCATION_ID = "vde.location.garganta_dos_lacos"
VIGILIA_LOCATION_ID = "vde.location.vigilia_do_vale"
VIGILIA_BRAZIER = "vde.brazier.vigilia_do_vale"
GARGANTA_BRAZIER = "vde.brazier.garganta_dos_lacos"
GARGANTA_HUNT_UNLOCK = "hunt.manual.vde.garganta_dos_lacos"
GARGANTA_EXPLORE_UNLOCK = "explore.vde.garganta_dos_lacos"
GARGANTA_VIGILIA_ROUTE = "route.vde.garganta_vigilia"
P7_FEAT = "feat.vde.estrada_estrangulada"
P7_ROUTES_CODEX = "codex.route.rotas_dos_vales"
FERRO_ENREDADO = "material.vde.ferro_enredado"
COURO_MUSGOSO = "material.vde.couro_musgoso"

# P7 deliberately does not name the scripted fauna. This internal combatant is
# not part of the regional Bestiary/catalog and carries no independent economy.
P7_FAUNA = Creature(
    "p7_fauna_regional",
    "Fauna Regional",
    "common",
    "balanced",
    11,
    11,
    0,
    ("investida_instintiva",),
    (("investida_instintiva", "Investida Instintiva", Decimal("1.00"), 0, Decimal(0), 0),),
)


@dataclass(frozen=True)
class P7View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p7"
    combat: object | None = None
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    consumable_options: tuple = ()
    consumable_quantities: tuple = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: object | None = None
    xp: int = 0
    combat_actor_key: str | None = None
    group_size: int = 1
    proposal_id: UUID | None = None
    proposal_status: str | None = None


class P7Service:
    """Owns P7 without creating a second regional progression framework."""

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

    async def resume(self, actor: int) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            return await self._view(session, character, quest, world)

    async def enter_vales(self, actor: int) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or world is None:
                return None
            if quest is not None:
                if (quest.progress or {}).get("entered_garganta"):
                    await self._ensure_location(session, character.id, GARGANTA_LOCATION_ID)
                    await self._ensure_brazier(session, character.id, GARGANTA_BRAZIER)
                return await self._view(session, character, quest, world)
            p6 = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == "P6",
                    Quest.status == "completed",
                )
            )
            foreground = await self._foreground(session, character.id)
            if p6 is None or character.level < 11 or foreground is not None:
                return await self._view(session, character, None, world)
            world.region, world.location = REGION, GARGANTA
            await self._ensure_location(session, character.id, GARGANTA_LOCATION_ID)
            await self._ensure_brazier(session, character.id, GARGANTA_BRAZIER)
            quest = Quest(
                character_id=character.id,
                quest_id=P7_ID,
                title=P7_TITLE,
                status="active",
                step=2,
                content_version=P7_VERSION,
                state_version=0,
                progress={"entered_garganta": True, "road_points": []},
            )
            session.add(quest)
            await session.flush()
            await record_campaign_objective_credit(
                session,
                character_id=character.id,
                quest_id=P7_ID,
                objective_id="p7.enter_garganta",
                source_key="p7.enter_garganta:first_entry",
                evidence={"region": REGION, "location": GARGANTA},
            )
            return await self._view(session, character, quest, world)

    async def examine_road_point(self, actor: int, version: int, point: str) -> P7View | None:
        if point not in {"a", "b"}:
            return await self.resume(actor)
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if not self._valid(quest, version, step=2) or character is None:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, step=2, location=GARGANTA)
            for member in members:
                progress = dict(member.quest.progress or {})
                points = list(progress.get("road_points", ()))
                if point not in points:
                    points.append(point)
                    progress["road_points"] = sorted(points)
                    member.quest.progress = progress
                    if len(points) >= 2:
                        member.quest.step = 3
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=P7_ID,
                        objective_id=f"p7.old_road.{point}",
                        source_key=f"p7.old_road.{point}:garganta",
                        evidence={"location": GARGANTA, "shared": len(members) > 1},
                    )
            return await self._view(session, character, quest, world)

    async def inspect_recent_passage(self, actor: int, version: int) -> P7View | None:
        return await self._advance_shared(
            actor,
            version,
            step=3,
            location=GARGANTA,
            objective_id="p7.recent_passage",
            source_key="p7.recent_passage:garganta",
            progress_key="recent_passage",
            next_step=4,
        )

    async def inspect_worked_stone(self, actor: int, version: int) -> P7View | None:
        return await self._advance_shared(
            actor,
            version,
            step=5,
            location=GARGANTA,
            objective_id="p7.worked_stone",
            source_key="p7.worked_stone:garganta",
            progress_key="worked_stone",
            next_step=6,
            evidence={"confirmed": "raízes seguem estruturas enterradas", "cause": "unknown"},
        )

    async def proceed_to_vigilia(self, actor: int, version: int) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if not self._valid(quest, version, step=6) or character is None:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, step=6, location=GARGANTA)
            for member in members:
                member.world.region, member.world.location = REGION, VIGILIA
                progress = dict(member.quest.progress or {})
                progress["reached_vigilia"] = True
                member.quest.progress = progress
                member.quest.step = 7
                member.quest.state_version += 1
                await self._ensure_location(session, member.character.id, VIGILIA_LOCATION_ID)
                await self._ensure_unlock(session, member.character.id, GARGANTA_VIGILIA_ROUTE)
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P7_ID,
                    objective_id="p7.reach_vigilia",
                    source_key="p7.reach_vigilia:first_arrival",
                    evidence={"location": VIGILIA, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def activate_brazier(self, actor: int, version: int) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if not self._valid(quest, version, step=7) or character is None:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, step=7, location=VIGILIA)
            for member in members:
                progress = dict(member.quest.progress or {})
                if progress.get("brazier_activated"):
                    continue
                await self._ensure_brazier(session, member.character.id)
                progress["brazier_activated"] = True
                member.quest.progress = progress
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P7_ID,
                    objective_id="p7.activate_vigilia_brazier",
                    source_key="p7.brazier.vigilia:first_activation",
                    evidence={"location": VIGILIA, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def report_dara(self, actor: int, version: int) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if not self._valid(quest, version, step=7) or character is None:
                return await self._view(session, character, quest, world)
            if not (quest.progress or {}).get("brazier_activated"):
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, step=7, location=VIGILIA)
            for member in members:
                if not (member.quest.progress or {}).get("brazier_activated"):
                    continue
                await self._complete(session, member.character, member.quest)
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P7_ID,
                    objective_id="p7.report_dara",
                    source_key="p7.report_dara:vigilia",
                    evidence={"location": VIGILIA, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def start_solo_combat(self, actor: int, version: int) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or not self._valid(quest, version, step=4):
                return await self._view(session, character, quest, world)
            if not self._at(world, GARGANTA) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            activity = await materialize(
                session,
                character,
                P7_CONTENT_ID,
                P7_FAUNA,
                11,
                flavor="Movimento brusco corta a névoa entre as raízes.",
                opening_log="⚔️ Fauna regional bloqueia a antiga estrada.",
            )
            progress = dict(quest.progress or {})
            progress.update(
                fauna_activity_id=str(activity.id),
                fauna_result=None,
                awaiting_retry=False,
            )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int) -> P7View | None:
        if self.groups is None:
            return await self.start_solo_combat(actor, version)
        initial = await self.resume(actor)
        if initial is None or initial.status != "active" or initial.step != 4:
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_p7",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._combat_eligibility,
            context_payload={
                "quest_id": P7_ID,
                "checkpoint": P7_CHECKPOINT,
                "title": f"{P7_TITLE} · Fauna Regional",
                "reference_character_id": str(initial.character_id),
                "location": GARGANTA,
            },
            journey_reference_character_id=initial.character_id,
        )
        return replace(initial, proposal_id=proposal.proposal_id, proposal_status=proposal.status)

    async def start_group_combat(
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
    ) -> P7View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._combat_eligibility,
            create_activity=self._create_group_combat,
        )
        return await self.resume(actor)

    async def action_combat(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ) -> P7View | None:
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
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P7_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            if (
                quest.status != "active"
                or quest.step != 4
                or activity.status != "active"
                or activity.state_version != version
            ):
                return current
            updated = await apply_action(
                session,
                character,
                activity,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                category=P7_FAUNA.category,
            )
            if updated is None or updated.version == version:
                return current
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await normalize_character_hp(session, character)
                progress.update(fauna_result="victory", awaiting_retry=False)
                quest.step = 5
                await record_campaign_objective_credit(
                    session,
                    character_id=character.id,
                    quest_id=P7_ID,
                    objective_id="p7.survive_fauna",
                    source_key=f"p7.survive_fauna:{activity.id}",
                    evidence={"result": "victory", "location": GARGANTA},
                )
            elif updated.result == "defeat":
                activity.status = "failed"
                character.hp = character.max_hp
                progress.update(
                    fauna_result="defeat",
                    awaiting_retry=True,
                    defeat_activity_id=str(activity.id),
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def retry(self, actor: int, version: int) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if (
                character is None
                or not self._valid(quest, version, step=4)
                or not (quest.progress or {}).get("awaiting_retry")
            ):
                return await self._view(session, character, quest, world)
            return await self._start_solo_locked(session, character, quest, world)

    async def campaign_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
    ) -> P7View | None:
        view = await self.resume(actor)
        if (
            view is None
            or view.activity_id != activity_id
            or view.combat is None
            or view.combat.version != version
            or view.combat_actor_key is None
        ):
            return None
        intent = campaign_action_intent(
            view.combat, view.combat_actor_key, action_index, target_code
        )
        if intent is None:
            return view
        action, target = intent
        return await self.action_combat(actor, activity_id, version, action, target_id=target)

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, **kwargs
    ) -> P7View | None:
        current = await self.resume(actor)
        if current is None or current.activity_id != activity_id or current.combat is None:
            return None
        if current.combat.version != version:
            return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
        return derive_consumable_selection(current, **kwargs)

    async def _start_solo_locked(self, session, character, quest, world):
        if not self._at(world, GARGANTA) or await self._foreground(session, character.id):
            return await self._view(session, character, quest, world)
        activity = await materialize(
            session,
            character,
            P7_CONTENT_ID,
            P7_FAUNA,
            11,
            flavor="Movimento brusco corta a névoa entre as raízes.",
            opening_log="⚔️ Fauna regional bloqueia a antiga estrada.",
        )
        progress = dict(quest.progress or {})
        progress.update(
            fauna_activity_id=str(activity.id),
            fauna_result=None,
            awaiting_retry=False,
        )
        quest.progress = progress
        quest.state_version += 1
        return await self._view(session, character, quest, world)

    async def _shared_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ) -> P7View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _, member_seed, _ = await campaign_combat_for_activity(session, activity_id, seed.id)
            if member_seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id != P7_ID:
                return None
            character = locked.characters.get(seed.id)
            member = next((row for row in locked.members if row.game_activity_id == activity_id), None)
            activity = locked.activities.get(activity_id)
            if character is None or member is None or activity is None:
                return None
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(Quest.character_id.in_(locked.characters), Quest.quest_id == P7_ID)
                        .order_by(Quest.character_id)
                        .with_for_update()
                    )
                ).all()
            )
            quests = {row.character_id: row for row in quest_rows}
            quest = quests.get(character.id)
            world = await self._world(session, character.id)
            if quest is None or (action is None) == (consumable_id is None):
                return None if quest is None else await self._view(session, character, quest, world)
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
                    return await self._view(session, character, quest, world)
            updated = resolve_campaign_action(
                locked,
                activity_id=activity_id,
                version=version,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(P7_FAUNA.category, 0),
            )
            if updated.version == version:
                return await self._view(session, character, quest, world)
            if stack is not None:
                stack.quantity -= 1
            member_by_character = {row.character_id: row for row in locked.members}
            for character_id, participant in locked.characters.items():
                roster_member = member_by_character[character_id]
                participant_quest = quests.get(character_id)
                if updated.result == "victory":
                    await normalize_character_hp(session, participant)
                    if roster_member.role == "eligible" and participant_quest is not None:
                        progress = dict(participant_quest.progress or {})
                        progress.update(fauna_result="victory", awaiting_retry=False)
                        participant_quest.progress = progress
                        participant_quest.step = 5
                        participant_quest.state_version += 1
                        await record_campaign_objective_credit(
                            session,
                            character_id=character_id,
                            quest_id=P7_ID,
                            objective_id="p7.survive_fauna",
                            source_key=f"p7.survive_fauna:{locked.encounter.id}",
                            evidence={"result": "victory", "location": GARGANTA},
                        )
                elif updated.result == "defeat":
                    participant.hp = participant.max_hp
                    if roster_member.role == "eligible" and participant_quest is not None:
                        progress = dict(participant_quest.progress or {})
                        progress.update(
                            fauna_result="defeat",
                            awaiting_retry=True,
                            defeat_activity_id=str(roster_member.game_activity_id),
                        )
                        participant_quest.progress = progress
                        participant_quest.state_version += 1
            if updated.result:
                await settle_campaign_encounter(session, locked, updated.result)
            return await self._view(session, character, quest, world)

    async def _combat_eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == P7_ID)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        active = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        )
        same_location = bool(
            world
            and world.region == REGION
            and world.location == payload.get("location") == GARGANTA
        )
        if active is not None or not same_location or quest is None or quest.content_version != P7_VERSION:
            role = "ineligible"
        elif quest.status == "active" and quest.step == 4:
            role = "eligible"
        elif quest.status == "completed" or quest.step > 4:
            role = "helper"
        else:
            role = "ineligible"
        snapshot = {
            "character_id": str(character.id),
            "role": role,
            "quest_status": quest.status if quest else None,
            "quest_step": quest.step if quest else None,
            "quest_version": quest.state_version if quest else None,
            "quest_content_version": quest.content_version if quest else None,
            "region": world.region if world else None,
            "location": world.location if world else None,
            "active_activity": str(active.id) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
            "level": character.level,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_group_combat(
        self,
        session: AsyncSession,
        proposal,
        characters: tuple[Character, ...],
    ) -> str:
        participant_rows = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal.id)
                    .order_by(GroupActivityParticipant.ordinal)
                )
            ).all()
        )
        row_by_character = {row.character_id: row for row in participant_rows}
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        party: list[PlayerCombatantSpec] = []
        roster: list[CampaignRosterMember] = []
        roster_size = len(characters)
        for index, character in enumerate(characters, start=1):
            participant = row_by_character.get(character.id)
            if participant is None or participant.eligibility not in {"eligible", "helper"}:
                raise GroupError("eligibility_changed")
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment)
            actor_key = campaign_actor_key(index, roster_size)
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
                    checkpoint=P7_CHECKPOINT,
                )
            )
        lead = characters[0]
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(P7_FAUNA, 11, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor="Movimento brusco corta a névoa entre as raízes.",
            opening_log="⚔️ Fauna regional bloqueia a antiga estrada.",
            active_art_ids=party[0].active_art_ids,
            party=tuple(party),
        )
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=P7_ID,
            content_id=P7_CONTENT_ID,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint=P7_CHECKPOINT,
            campaign_boss=False,
        )
        for member in roster:
            if member.role == "eligible":
                quest = await session.scalar(
                    select(Quest).where(
                        Quest.character_id == member.character.id,
                        Quest.quest_id == P7_ID,
                    )
                )
                if quest is not None:
                    progress = dict(quest.progress or {})
                    roster_member = await session.scalar(
                        select(CampaignSharedEncounterMember).where(
                            CampaignSharedEncounterMember.shared_encounter_id == encounter.id,
                            CampaignSharedEncounterMember.character_id == member.character.id,
                        )
                    )
                    if roster_member is not None:
                        progress["fauna_activity_id"] = str(roster_member.game_activity_id)
                    progress.update(fauna_result=None, awaiting_retry=False)
                    quest.progress = progress
                    quest.state_version += 1
        return str(encounter.id)

    async def _advance_shared(
        self,
        actor: int,
        version: int,
        *,
        step: int,
        location: str,
        objective_id: str,
        source_key: str,
        progress_key: str,
        next_step: int,
        evidence: dict | None = None,
    ) -> P7View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or not self._valid(quest, version, step=step):
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, step=step, location=location)
            for member in members:
                progress = dict(member.quest.progress or {})
                if progress.get(progress_key):
                    continue
                progress[progress_key] = True
                member.quest.progress = progress
                member.quest.step = next_step
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P7_ID,
                    objective_id=objective_id,
                    source_key=source_key,
                    evidence=(evidence or {}) | {"location": location, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def _complete(self, session, character: Character, quest: Quest) -> None:
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P7_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P7_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 8750
            character.crowns += 270
            session.add_all(
                [
                    RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=8750),
                    RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=270),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=FERRO_ENREDADO,
                        quantity=1,
                        payload={"material_id": FERRO_ENREDADO, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=COURO_MUSGOSO,
                        quantity=1,
                        payload={"material_id": COURO_MUSGOSO, "bound": True},
                    ),
                ]
            )
            await self.road.deliver_material(
                session,
                character,
                FERRO_ENREDADO,
                1,
                f"{P7_REWARD_SOURCE}:material:{FERRO_ENREDADO}",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                COURO_MUSGOSO,
                1,
                f"{P7_REWARD_SOURCE}:material:{COURO_MUSGOSO}",
                bound=True,
            )
        await self._ensure_achievement(session, character.id, P7_FEAT)
        await self._ensure_unlock(session, character.id, GARGANTA_HUNT_UNLOCK)
        await self._ensure_unlock(session, character.id, GARGANTA_EXPLORE_UNLOCK)
        await self._ensure_codex(session, character.id, P7_ROUTES_CODEX)
        await self._ensure_codex_fragment(
            session,
            character.id,
            P7_ROUTES_CODEX,
            "codex.fragment.vales.routes.garganta_vigilia",
        )
        quest.status = "completed"
        quest.step = 7
        quest.progress = {**(quest.progress or {}), "reported_dara": True, "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _view(self, session, character, quest, world) -> P7View:
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        actor_key = None
        group_size = 1
        try:
            activity_id = UUID(progress["fauna_activity_id"]) if progress.get("fauna_activity_id") else None
        except (TypeError, ValueError):
            activity_id = None
        if activity_id is not None and character is not None:
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if shared is not None:
                activity = await session.get(GameActivity, activity_id)
                combat = shared_combat if shared.status == "active" else None
                encounter = shared
                actor_key = shared_member.actor_key if shared_member else None
                group_size = shared.roster_size
            else:
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == P7_CONTENT_ID,
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
        if quest is None:
            kind = "unavailable"
        elif combat is not None:
            kind = "combat"
        elif quest.status == "completed":
            kind = "completed"
        elif quest.step == 2:
            kind = "road_points"
        elif quest.step == 3:
            kind = "recent_passage"
        elif quest.step == 4 and progress.get("awaiting_retry"):
            kind = "retry"
        elif quest.step == 4:
            kind = "start_fauna"
        elif quest.step == 5:
            kind = "worked_stone"
        elif quest.step == 6:
            kind = "proceed_vigilia"
        elif quest.step == 7 and not progress.get("brazier_activated"):
            kind = "activate_brazier"
        elif quest.step == 7:
            kind = "report_dara"
        else:
            kind = "unavailable"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None and character is not None:
            options, quantities, budget = await consumable_state(
                session, character, combat, P7_FAUNA.category, actor_key=actor_key
            )
        return P7View(
            character_id=character.id if character else UUID(int=0),
            kind=kind,
            status=quest.status if quest else None,
            step=quest.step if quest else None,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level if character else 0,
            available=quest is not None and quest.status == "active",
            combat=combat,
            activity_id=activity.id if activity else None,
            encounter_id=encounter.id if encounter else None,
            combat_id=record.id if record else None,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            xp=character.xp if character else 0,
            combat_actor_key=actor_key,
            group_size=group_size,
        )

    async def _present(self, session, character_id, *, step, location):
        roster = await campaign_roster_ids(session, character_id)
        return await present_campaign_members(
            session,
            character_ids=roster,
            quest_id=P7_ID,
            content_version=P7_VERSION,
            step=step,
            region=REGION,
            location=location,
        )

    async def _locked_state(self, session, actor):
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(
            select(Quest)
            .where(Quest.character_id == character.id, Quest.quest_id == P7_ID)
            .with_for_update()
        )
        world = await session.scalar(
            select(WorldState)
            .where(WorldState.character_id == character.id)
            .with_for_update()
        )
        return character, quest, world

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        )

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == P7_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)

    async def _ensure_location(self, session, character_id, location_id):
        found = await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == location_id,
            )
        )
        if found is None:
            session.add(LocationDiscovery(character_id=character_id, location_id=location_id))

    async def _ensure_brazier(self, session, character_id, brazier_id=VIGILIA_BRAZIER):
        found = await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == brazier_id,
            )
        )
        if found is None:
            session.add(Brazier(character_id=character_id, brazier_id=brazier_id))

    async def _ensure_unlock(self, session, character_id, unlock_id):
        found = await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == unlock_id,
            )
        )
        if found is None:
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))

    async def _ensure_achievement(self, session, character_id, achievement_id):
        found = await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == achievement_id,
            )
        )
        if found is None:
            session.add(Achievement(character_id=character_id, achievement_id=achievement_id))

    async def _ensure_codex(self, session, character_id, entry_id):
        found = await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == entry_id,
            )
        )
        if found is None:
            session.add(CodexEntry(character_id=character_id, entry_id=entry_id))

    async def _ensure_codex_fragment(self, session, character_id, entry_id, fragment_id):
        found = await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == fragment_id,
            )
        )
        if found is None:
            await self._ensure_codex(session, character_id, entry_id)
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
            )
