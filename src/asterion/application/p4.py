"""P4 mission-specific campaign flow for the Ruínas do Vigia."""
# ruff: noqa: E501

import hashlib
import json
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BestiaryRecorder
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
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.groups import ActivityEligibility, GroupError, GroupService
from asterion.application.progression import consolidate_character_level
from asterion.application.road import (
    BOSQUE,
    CHARNECA,
    CHARNECA_ROUTE_UNLOCK,
    P3_QUEST_ID,
    REFUGE,
    REGION,
    RUINS,
    RoadService,
)
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    derive_consumable_selection,
    materialize,
    normalize_character_hp,
)
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.legacy import legacy_xp_factor
from asterion.domain.road import (
    RUINS_LOCATION,
    RULESET,
    VIGIA,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    enemy_xp,
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
    GroupActivityProposal,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    SocialGroupMember,
    Unlock,
    WorldState,
)

P4_ID = "P4"
P4_TITLE = "Pedras que Ainda Vigiam"
P4_VERSION = "tdo-1.0.11"
P4_CONTENT_ID = "p4_scripted_vigia_rachado"
P4_REWARD_SOURCE = "p4.pedras_que_ainda_vigiam"
P4_STRUCTURES = ("p4.guard_structure.1", "p4.guard_structure.2")
P4_ROUTE_UNLOCK = "route.tdo.bosque_ruinas"
P4_HUNT_UNLOCK = "hunt_manual.ruinas_do_vigia"
P4_EXPLORE_UNLOCK = "explore.ruinas_do_vigia"
P4_CODEX_ENTRY = "codex.history.antigos_asterianos"
P4_CODEX_FRAGMENT = "p4.ruinas.funcao_de_guarda"
P4_IRON = "material.tdo.ferro_de_fuligem"
P4_RESIDUE = "material.tdo.residuo_ocaso"


@dataclass(frozen=True)
class P4View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p4"
    combat: object | None = None
    activity_id: UUID | None = None
    activity_state_version: int | None = None
    activity_status: str | None = None
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
    combat_actor_key: str = "player"
    group_size: int = 1
    proposal_id: UUID | None = None
    proposal_status: str | None = None


class P4Service:
    """Owns only P4 state transitions; movement and combat rules stay shared."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        *,
        groups: GroupService | None = None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.groups = groups
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def alda(self, actor: int) -> P4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "alda")

    async def offer(self, actor: int) -> P4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            available = quest is None and self._at(world, REFUGE) and not await self._foreground(
                session, character.id
            ) and await self._eligible(session, character)
            return await self._view(
                session, character, quest, world,
                "offer" if available else "unavailable", available=available,
            )

    async def resume(self, actor: int) -> P4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def accept(self, actor: int, version: int = 0) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                quest is not None or version != 0 or not self._at(world, REFUGE)
                or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            quest = Quest(
                character_id=character.id, quest_id=P4_ID, title=P4_TITLE,
                status="active", step=1, content_version=P4_VERSION,
                state_version=0, progress={},
            )
            session.add(quest)
            await session.flush()
            return await self._view(session, character, quest, world)

    async def action(
        self, actor: int, version: int, operation: str, item: str | None = None
    ) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            if operation == "path" and quest.step == 1 and self._at(world, BOSQUE):
                await self._share_path(session, character, quest, world)
                return await self._view(session, character, quest, world)
            elif (
                operation == "enter" and quest.step == 2
                and (quest.progress or {}).get("western_path_followed")
                and self._at(world, BOSQUE)
            ):
                await self._share_ruins_entry(session, character, quest, world)
                if await self._social_group_size(session, character.id) == 1:
                    await self._materialize(session, character, quest)
                return await self._view(session, character, quest, world)
            elif (
                operation == "enter" and quest.step == 3
                and (quest.progress or {}).get("awaiting_retry")
                and self._at(world, BOSQUE)
                and await self._has_unlock(session, character.id, P4_ROUTE_UNLOCK)
            ):
                await self._share_retry_route(session, character, quest, world)
                return await self._view(session, character, quest, world)
            elif (
                operation == "retry"
                and quest.step == 3
                and (quest.progress or {}).get("awaiting_retry")
            ):
                await self._share_retry(session, character, quest, world)
                if await self._social_group_size(session, character.id) == 1:
                    await self._materialize(session, character, quest)
                return await self._view(session, character, quest, world)
            elif operation == "structure" and quest.step == 4 and self._at(world, RUINS):
                if item not in P4_STRUCTURES:
                    return await self._view(session, character, quest, world)
                await self._share_structure(session, character, quest, world, item)
                return await self._view(session, character, quest, world)
            elif operation == "safe_route" and quest.step == 5 and self._at(world, RUINS):
                await self._share_safe_route(session, character, quest, world)
                return await self._view(session, character, quest, world)
            elif operation == "return" and quest.step == 6 and self._at(world, RUINS):
                if not await self._has_unlock(session, character.id, P4_ROUTE_UNLOCK):
                    return await self._view(session, character, quest, world)
                await self._share_return_to_bosque(session, character, quest, world)
                return await self._view(session, character, quest, world)
            elif operation in {"report_alda", "report_oren"} and quest.step == 6 and self._at(world, REFUGE):
                progress = dict(quest.progress or {})
                progress["reports"] = list(progress.get("reports", ()))
                person = "alda" if operation.endswith("alda") else "oren"
                if person not in progress["reports"]:
                    progress["reports"].append(person)
                if set(progress["reports"]) == {"alda", "oren"}:
                    quest.progress = progress
                    await self._complete(session, character, quest)
                    return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _present(self, session, character, quest, world, *, step, location):
        roster_ids = await campaign_roster_ids(session, character.id)
        return await present_campaign_members(
            session,
            character_ids=roster_ids,
            quest_id=P4_ID,
            content_version=P4_VERSION,
            step=step,
            region=REGION,
            location=location,
        )

    async def _share_path(self, session, character, quest, world):
        for member in await self._present(
            session, character, quest, world, step=1, location=BOSQUE
        ):
            progress = dict(member.quest.progress or {})
            if progress.get("western_path_followed"):
                continue
            progress["western_path_followed"] = True
            member.quest.progress = progress
            member.quest.step = 2
            member.quest.state_version += 1
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id=P4_ID,
                objective_id="p4.western_path",
                source_key="p4.western_path:followed",
                evidence={"location": BOSQUE},
            )

    async def _share_ruins_entry(self, session, character, quest, world):
        for member in await self._present(
            session, character, quest, world, step=2, location=BOSQUE
        ):
            progress = dict(member.quest.progress or {})
            if not progress.get("western_path_followed"):
                continue
            await self._ensure(
                session,
                LocationDiscovery,
                character_id=member.character.id,
                location_id=RUINS_LOCATION,
            )
            await self._ensure(
                session,
                Unlock,
                character_id=member.character.id,
                unlock_id=P4_ROUTE_UNLOCK,
            )
            member.world.region = REGION
            member.world.location = RUINS
            progress.update(ruins_discovered=True, awaiting_retry=False)
            member.quest.progress = progress
            member.quest.step = 3
            member.quest.state_version += 1
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id=P4_ID,
                objective_id="p4.reach_ruins",
                source_key="p4.reach_ruins:first-entry",
                evidence={"location_id": RUINS_LOCATION},
            )

    async def _share_retry_route(self, session, character, quest, world):
        for member in await self._present(
            session, character, quest, world, step=3, location=BOSQUE
        ):
            progress = dict(member.quest.progress or {})
            if not progress.get("awaiting_retry") or not await self._has_unlock(
                session, member.character.id, P4_ROUTE_UNLOCK
            ):
                continue
            member.world.region = REGION
            member.world.location = RUINS
            progress["returned_for_retry"] = True
            member.quest.progress = progress
            member.quest.state_version += 1
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id=P4_ID,
                objective_id="p4.retry_route",
                source_key=f"p4.retry_route:{member.quest.state_version - 1}",
                evidence={"from": BOSQUE, "to": RUINS},
            )

    async def _share_retry(self, session, character, quest, world):
        if not self._at(world, RUINS):
            return
        for member in await self._present(
            session, character, quest, world, step=3, location=RUINS
        ):
            progress = dict(member.quest.progress or {})
            if not progress.get("awaiting_retry"):
                continue
            progress["awaiting_retry"] = False
            member.quest.progress = progress
            member.quest.state_version += 1
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id=P4_ID,
                objective_id="p4.retry",
                source_key=f"p4.retry:{member.quest.state_version - 1}",
                evidence={"location": RUINS},
            )

    async def _share_structure(self, session, character, quest, world, item):
        for member in await self._present(
            session, character, quest, world, step=4, location=RUINS
        ):
            progress = dict(member.quest.progress or {})
            found = set(progress.get("structures", ()))
            if item in found:
                continue
            found.add(item)
            progress["structures"] = [key for key in P4_STRUCTURES if key in found]
            member.quest.progress = progress
            if len(found) == len(P4_STRUCTURES):
                member.quest.step = 5
            member.quest.state_version += 1
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id=P4_ID,
                objective_id="p4.guard_structure",
                source_key=f"p4.guard_structure:{item}",
                evidence={"structure_id": item, "location": RUINS},
            )

    async def _share_safe_route(self, session, character, quest, world):
        for member in await self._present(
            session, character, quest, world, step=5, location=RUINS
        ):
            progress = dict(member.quest.progress or {})
            if progress.get("safe_route_identified"):
                continue
            progress["safe_route_identified"] = True
            member.quest.progress = progress
            member.quest.step = 6
            member.quest.state_version += 1
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id=P4_ID,
                objective_id="p4.safe_route",
                source_key="p4.safe_route:identified",
                evidence={"location": RUINS},
            )

    async def _share_return_to_bosque(self, session, character, quest, world):
        for member in await self._present(
            session, character, quest, world, step=6, location=RUINS
        ):
            if not await self._has_unlock(session, member.character.id, P4_ROUTE_UNLOCK):
                continue
            member.world.region = REGION
            member.world.location = BOSQUE
            progress = dict(member.quest.progress or {})
            progress["returned_to_bosque"] = True
            member.quest.progress = progress
            member.quest.state_version += 1
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id=P4_ID,
                objective_id="p4.return_to_bosque",
                source_key=f"p4.return_to_bosque:{member.quest.state_version - 1}",
                evidence={"from": RUINS, "to": BOSQUE},
            )

    async def mission_route(self, actor: int, version: int, destination: str) -> P4View | None:
        """Share the P4 return route with eligible members at the same checkpoint."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None or world is None:
                return None
            if (
                not self._valid(quest, version, step=6)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            current = world.location
            allowed = {current, destination} in (
                {BOSQUE, CHARNECA},
                {CHARNECA, REFUGE},
            )
            if not allowed:
                return await self._view(session, character, quest, world)
            route_unlock = CHARNECA_ROUTE_UNLOCK
            if not await self._has_unlock(session, character.id, route_unlock):
                return await self._view(session, character, quest, world)
            for member in await self._present(
                session, character, quest, world, step=6, location=current
            ):
                if not await self._has_unlock(
                    session, member.character.id, route_unlock
                ):
                    continue
                member.world.region = REGION
                member.world.location = destination
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P4_ID,
                    objective_id="p4.return_route",
                    source_key=(
                        f"p4.return_route:{current}:{destination}:"
                        f"{member.quest.state_version - 1}"
                    ),
                    evidence={"from": current, "to": destination},
                )
            return await self._view(session, character, quest, world)

    async def start_solo_combat(self, actor: int, version: int) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None or world is None:
                return None
            if (
                not self._valid(quest, version, step=3)
                or not self._at(world, RUINS)
                or (quest.progress or {}).get("awaiting_retry")
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            reservation = await session.scalar(
                select(GroupActivityParticipant).where(
                    GroupActivityParticipant.character_id == character.id,
                    GroupActivityParticipant.reservation_state == "active",
                )
            )
            if reservation is not None:
                return await self._view(session, character, quest, world)
            activity = await self._materialize(session, character, quest)
            if activity is not None:
                quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int) -> P4View | None:
        if self.groups is None:
            return await self.resume(actor)
        initial = await self.resume(actor)
        if (
            initial is None
            or initial.status != "active"
            or initial.step != 3
            or initial.state_version != version
            or initial.location != RUINS
            or initial.progress.get("awaiting_retry")
        ):
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_p4",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._p4_combat_eligibility,
            context_payload={
                "quest_id": P4_ID,
                "checkpoint": "p4.vigia_rachado",
                "title": f"{P4_TITLE} · Vigia Rachado",
                "reference_character_id": str(initial.character_id),
                "location": RUINS,
            },
            journey_reference_character_id=initial.character_id,
        )
        view = await self.resume(actor)
        return replace(view, proposal_id=proposal.proposal_id) if view is not None else None

    async def start_group_combat(
        self, actor: int, proposal_id: UUID, *, expected_revision: int
    ) -> P4View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._p4_combat_eligibility,
            create_activity=self._create_p4_group_combat,
        )
        return await self.resume(actor)

    async def campaign_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
    ) -> P4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            encounter, member, combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if (
                encounter is None
                or member is None
                or encounter.content_id != P4_CONTENT_ID
                or combat is None
            ):
                return None
            intent = campaign_action_intent(
                combat, member.actor_key, action_index, target_code
            )
            if intent is None:
                return await self.resume(actor)
            action, target_id = intent
        return await self.action_combat(
            actor, activity_id, version, action, target_id=target_id
        )

    async def _p4_combat_eligibility(self, session, character, payload):
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == P4_ID)
        )
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        progress = dict(quest.progress or {}) if quest else {}
        if (
            active is not None
            or not self._at(world, RUINS)
            or payload.get("location") != RUINS
            or quest is None
            or quest.content_version != P4_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and progress.get("ruins_discovered")
            and not progress.get("awaiting_retry")
        ):
            role = "eligible"
        elif quest.status == "completed" or quest.step > 3:
            role = "helper"
        else:
            role = "ineligible"
        reward_event = await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P4_REWARD_SOURCE,
            )
        )
        snapshot = {
            "character_id": str(character.id),
            "role": role,
            "quest_status": quest.status if quest else None,
            "quest_step": quest.step if quest else None,
            "quest_version": quest.state_version if quest else None,
            "quest_content_version": quest.content_version if quest else None,
            "location": world.location if world else None,
            "region": world.region if world else None,
            "active_activity": str(active.id) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
            "level": character.level,
            "mission_reward_eligible": role == "eligible" and reward_event is None,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_p4_group_combat(self, session, proposal, characters):
        participants = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal.id)
                    .order_by(GroupActivityParticipant.ordinal)
                )
            ).all()
        )
        roles = {row.character_id: row.eligibility for row in participants}
        if any(roles.get(row.id) not in {"eligible", "helper"} for row in characters):
            raise GroupError("eligibility_changed")
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        party = []
        roster = []
        for index, character in enumerate(characters, start=1):
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
                    role=roles[character.id],
                    checkpoint="p4.vigia_rachado",
                )
            )
        lead = characters[0]
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(VIGIA, 7, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor="Um Vigia Rachado se ergue entre as estruturas de guarda.",
            opening_log="🛡️ Vigia Rachado · Nv.7 protege os limites das Ruínas.",
            active_art_ids=party[0].active_art_ids,
            party=tuple(party),
        )
        arts = await load_active_art_configuration(session, lead)
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | arts.to_data()
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=P4_ID,
            content_id=P4_CONTENT_ID,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint="p4.vigia_rachado",
        )
        encounter_members = list(
            (
                await session.scalars(
                    select(CampaignSharedEncounterMember).where(
                        CampaignSharedEncounterMember.shared_encounter_id == encounter.id
                    )
                )
            ).all()
        )
        for member in encounter_members:
            if member.role == "eligible":
                participant_quest = await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == member.character_id, Quest.quest_id == P4_ID)
                    .with_for_update()
                )
                if participant_quest is not None:
                    participant_quest.progress = {
                        **(participant_quest.progress or {}),
                        "combat_activity_id": str(member.game_activity_id),
                    }
        await session.flush()
        return str(encounter.id)

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, *,
        screen: str = "items", item_id: str | None = None,
        target_id: str | None = None, parent: str = "items",
    ) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == activity_id, GameActivity.character_id == character.id,
                GameActivity.content_id == P4_CONTENT_ID,
            ).with_for_update())
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            shared, shared_member, _combat = await campaign_combat_for_activity(
                session, activity.id, character.id
            )
            shared_allowed = bool(
                shared is not None
                and shared_member is not None
                and shared_member.role in {"eligible", "helper"}
            )
            if (
                (not shared_allowed and (quest.status != "active" or quest.step != 3))
                or activity.status != "active"
                or foreground is None or foreground.id != activity.id
            ):
                return current
            if activity.state_version != version:
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    async def action_combat(
        self, actor: int, activity_id: UUID, version: int, action: str | None = None,
        *, consumable_id: str | None = None, target_id: str | None = None,
        effect_id: str | None = None,
    ) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P4_CONTENT_ID,
                ).with_for_update()
            )
            if activity is None:
                return None
            current_view = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            _shared, shared_member, _combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if shared_member is not None:
                return await self._shared_action(
                    session,
                    character,
                    quest,
                    world,
                    activity_id,
                    version,
                    action,
                    consumable_id=consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                )
            if (
                not self._valid(quest, quest.state_version, step=3)
                or activity.status != "active" or activity.state_version != version
                or foreground is None or foreground.id != activity.id
                or (action is None) == (consumable_id is None)
            ):
                return current_view
            updated = await apply_action(
                session, character, activity, action=action, consumable_id=consumable_id,
                target_id=target_id, effect_id=effect_id, category=VIGIA.category,
            )
            if updated is None:
                return current_view
            await self.bestiary.record_combat_events(
                session, character.id, VIGIA.creature_id, None, updated
            )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session, character.id, VIGIA.creature_id, victory=True,
                    observation_category="common",
                )
                progress.update(combat_result="victory", awaiting_retry=False)
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session, character.id, VIGIA.creature_id, observation_category="common"
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, RUINS_LOCATION, world
                )
                progress.update(
                    combat_result="defeat", awaiting_retry=True,
                    defeat_activity_id=str(activity.id), recovery_brazier=brazier,
                    recovery_location=location,
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _shared_action(
        self,
        session,
        character,
        quest,
        world,
        activity_id,
        version,
        action,
        *,
        consumable_id,
        target_id,
        effect_id,
    ):
        locked = await lock_campaign_encounter(session, activity_id, character.id)
        if locked is None or locked.encounter.content_id != P4_CONTENT_ID:
            return await self._view(session, character, quest, world)
        member = next(
            (row for row in locked.members if row.game_activity_id == activity_id), None
        )
        activity = locked.activities.get(activity_id)
        if (
            member is None
            or activity is None
            or activity.state_version != version
            or activity.status != "active"
            or locked.encounter.state_version != version
            or (action is None) == (consumable_id is None)
        ):
            return await self._view(session, character, quest, world)
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
                return replace(
                    await self._view(session, character, quest, world),
                    consumable_notice="⚠️ Consumível · Não está mais disponível.",
                )
        updated = resolve_campaign_action(
            locked,
            activity_id=activity_id,
            version=version,
            action=action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
            consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(VIGIA.category, 0),
        )
        if updated.version == version:
            return await self._view(session, character, quest, world)
        if stack is not None:
            stack.quantity -= 1
        member_by_character = {row.character_id: row for row in locked.members}
        quests = list(
            (
                await session.scalars(
                    select(Quest)
                    .where(
                        Quest.character_id.in_(locked.characters),
                        Quest.quest_id == P4_ID,
                    )
                    .order_by(Quest.character_id)
                    .with_for_update()
                )
            ).all()
        )
        quests_by_character = {row.character_id: row for row in quests}
        worlds = list(
            (
                await session.scalars(
                    select(WorldState)
                    .where(WorldState.character_id.in_(locked.characters))
                    .order_by(WorldState.character_id)
                    .with_for_update()
                )
            ).all()
        )
        worlds_by_character = {row.character_id: row for row in worlds}
        for character_id, participant in locked.characters.items():
            roster_member = member_by_character[character_id]
            participant_quest = quests_by_character.get(character_id)
            await self.bestiary.record_combat_events(
                session, character_id, VIGIA.creature_id, None, updated
            )
            if updated.result and roster_member.role == "eligible":
                await record_campaign_objective_credit(
                    session,
                    character_id=character_id,
                    quest_id=P4_ID,
                    objective_id="p4.vigia_rachado",
                    source_key=f"p4.vigia_rachado:{locked.encounter.id}",
                    evidence={
                        "result": updated.result,
                        "encounter_id": str(locked.encounter.id),
                    },
                )
            if updated.result == "victory":
                await self.bestiary.record(
                    session,
                    character_id,
                    VIGIA.creature_id,
                    victory=True,
                    observation_category="common",
                )
                if roster_member.role == "eligible":
                    await self._grant_enemy_xp(
                        session,
                        participant,
                        locked.activities[roster_member.game_activity_id],
                    )
                    await normalize_character_hp(session, participant)
                if (
                    roster_member.role == "eligible"
                    and participant_quest is not None
                    and participant_quest.status == "active"
                    and participant_quest.step == 3
                ):
                    progress = dict(participant_quest.progress or {})
                    progress.update(combat_result="victory", awaiting_retry=False)
                    participant_quest.progress = progress
                    participant_quest.step = 4
                    participant_quest.state_version += 1
            elif updated.result == "defeat":
                await self.bestiary.record(
                    session,
                    character_id,
                    VIGIA.creature_id,
                    observation_category="common",
                )
                participant_world = worlds_by_character.get(character_id)
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, participant, RUINS_LOCATION, participant_world
                )
                if (
                    roster_member.role == "eligible"
                    and participant_quest is not None
                    and participant_quest.status == "active"
                    and participant_quest.step == 3
                ):
                    progress = dict(participant_quest.progress or {})
                    progress.update(
                        combat_result="defeat",
                        awaiting_retry=True,
                        defeat_activity_id=str(roster_member.game_activity_id),
                        recovery_brazier=brazier,
                        recovery_location=location,
                    )
                    participant_quest.progress = progress
                    participant_quest.state_version += 1
        if updated.result:
            await settle_campaign_encounter(session, locked, updated.result)
        return await self._view(session, character, quest, world)

    async def _materialize(self, session, character, quest):
        if await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session, character, P4_CONTENT_ID, VIGIA, 7,
            flavor="Um Vigia Rachado se ergue entre as estruturas de guarda.",
            opening_log="🛡️ Vigia Rachado · Nv.7 protege os limites das Ruínas.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{P4_REWARD_SOURCE}:enemy-xp:{activity.id}"
        if await session.scalar(select(RewardEvent.id).where(
            RewardEvent.character_id == character.id, RewardEvent.source_id == source
        ).with_for_update()):
            return
        amount = enemy_xp(
            7,
            "common",
            player_level=character.level,
            legacy_factor=legacy_xp_factor(character.legacy_level),
        )
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        session.add(RewardComponent(
            reward_event_id=event.id, kind="enemy_xp", item_id=VIGIA.creature_id,
            quantity=amount, payload={"enemy_level": 7, "category": "common"},
        ))
        character.xp += amount

    async def _complete(self, session, character, quest):
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P4_REWARD_SOURCE,
            ).with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P4_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 5700
            character.crowns += 250
            components = [
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=5700),
                RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=250),
                RewardComponent(reward_event_id=event.id, kind="material", item_id=P4_IRON, quantity=2,
                                payload={"material_id": P4_IRON, "bound": True}),
                RewardComponent(reward_event_id=event.id, kind="material", item_id=P4_RESIDUE, quantity=2,
                                payload={"material_id": P4_RESIDUE, "bound": True}),
            ]
            session.add_all(components)
            await self.road.deliver_material(session, character, P4_IRON, 2,
                                             f"{P4_REWARD_SOURCE}:material:{P4_IRON}", bound=True)
            await self.road.deliver_material(session, character, P4_RESIDUE, 2,
                                             f"{P4_REWARD_SOURCE}:material:{P4_RESIDUE}", bound=True)
        await self._ensure(session, CodexEntry, character_id=character.id, entry_id=P4_CODEX_ENTRY)
        await self._ensure(session, CodexFragment, character_id=character.id,
                           entry_id=P4_CODEX_ENTRY, fragment_id=P4_CODEX_FRAGMENT)
        await self._ensure(session, Unlock, character_id=character.id, unlock_id=P4_HUNT_UNLOCK)
        await self._ensure(session, Unlock, character_id=character.id, unlock_id=P4_EXPLORE_UNLOCK)
        await self._ensure(session, Unlock, character_id=character.id, unlock_id=P4_ROUTE_UNLOCK)
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _view(self, session, character, quest, world, requested_kind=None, *, available=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        combat_actor_key = "player"
        group_size = await self._social_group_size(session, character.id)
        stored = progress.get("combat_activity_id")
        try:
            stored_id = UUID(stored) if stored else None
        except (TypeError, ValueError):
            stored_id = None
        activity = await session.scalar(
            select(GameActivity)
            .where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == P4_CONTENT_ID,
                GameActivity.status == "active",
            )
            .order_by(GameActivity.last_valid_action_at.desc(), GameActivity.id.desc())
        )
        if stored_id:
            if activity is None:
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == stored_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == P4_CONTENT_ID,
                    )
                )
        if activity is not None:
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity.id, character.id
            )
            if shared is not None and shared_member is not None:
                encounter = shared
                record = None
                combat_actor_key = shared_member.actor_key
                group_size = shared.roster_size
                if activity.status == "active":
                    combat = shared_combat
            else:
                row = (
                    await session.execute(
                        select(Encounter, CombatRecord)
                        .join(CombatRecord)
                        .where(Encounter.game_activity_id == activity.id)
                    )
                ).one_or_none()
                if row is not None:
                    encounter, record = row
                    if activity.status == "active":
                        combat = decode(
                            record.snapshot,
                            record.id,
                            activity.ruleset_version,
                            activity.state_version,
                        )
        status = quest.status if quest else "unaccepted"
        available = (
            quest is None and await self._eligible(session, character)
            if available is None else available
        )
        if requested_kind:
            kind = requested_kind
        elif quest is None:
            kind = "offer" if available else "unavailable"
        elif combat is not None:
            kind = "combat"
        elif status == "completed":
            kind = "completed"
        elif quest.step == 1:
            kind = "path"
        elif quest.step == 2:
            kind = "enter_ruins" if self._at(world, BOSQUE) else "path"
        elif quest.step == 3:
            kind = "recovery" if progress.get("awaiting_retry") else "combat_pending"
        elif quest.step == 4:
            kind = "structures"
        elif quest.step == 5:
            kind = "safe_route"
        else:
            kind = "reports" if self._at(world, REFUGE) else "return"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(
                session,
                character,
                combat,
                VIGIA.category,
                actor_key=combat_actor_key,
            )
        proposal_pair = None
        if activity is None:
            proposal_rows = await session.execute(
                select(GroupActivityParticipant, GroupActivityProposal)
                .join(
                    GroupActivityProposal,
                    GroupActivityProposal.id == GroupActivityParticipant.proposal_id,
                )
                .where(
                    GroupActivityParticipant.character_id == character.id,
                    GroupActivityParticipant.reservation_state == "active",
                    GroupActivityProposal.activity_type == "campaign_p4",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .order_by(GroupActivityProposal.created_at.desc(), GroupActivityProposal.id)
                .limit(1)
            )
            proposal_pair = proposal_rows.first()
        return P4View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=bool(available and quest is None),
            combat=combat,
            activity_id=activity.id if activity else None,
            activity_state_version=activity.state_version if activity else None,
            activity_status=activity.status if activity else None,
            encounter_id=encounter.id if encounter else None,
            combat_id=record.id if record else None,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            xp=character.xp,
            combat_actor_key=combat_actor_key,
            group_size=group_size,
            proposal_id=proposal_pair[1].id if proposal_pair else None,
            proposal_status=proposal_pair[1].status if proposal_pair else None,
        )

    async def _eligible(self, session, character):
        return bool(
            character.level >= 7 and await session.scalar(select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P3_QUEST_ID,
                Quest.status == "completed",
            ))
        )

    async def _ensure(self, session, model, **values):
        row = await session.scalar(select(model).filter_by(**values).with_for_update())
        if row is None:
            row = model(**values)
            session.add(row)
            await session.flush()
        return row

    async def _has_unlock(self, session, character_id, unlock_id):
        return bool(await session.scalar(select(Unlock.id).where(
            Unlock.character_id == character_id, Unlock.unlock_id == unlock_id
        )))

    async def _locked_state(self, session, actor):
        seed = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )
        if seed is None:
            return None, None, None
        await lock_campaign_roster(session, seed.id)
        character = await session.scalar(
            select(Character).where(Character.id == seed.id).with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(select(Quest).where(
            Quest.character_id == character.id, Quest.quest_id == P4_ID
        ).with_for_update())
        world = await session.scalar(select(WorldState).where(
            WorldState.character_id == character.id
        ).with_for_update())
        return character, quest, world

    async def _social_group_size(self, session, character_id):
        membership = await session.scalar(
            select(SocialGroupMember).where(
                SocialGroupMember.character_id == character_id
            )
        )
        if membership is None:
            return 1
        group = await session.get(SocialGroup, membership.group_id)
        if group is None or group.status != "active":
            return 1
        members = (
            await session.scalars(
                select(SocialGroupMember.character_id).where(
                    SocialGroupMember.group_id == group.id
                )
            )
        ).all()
        return max(1, len(members))

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ))

    async def _quest(self, session, character_id):
        return await session.scalar(select(Quest).where(
            Quest.character_id == character_id, Quest.quest_id == P4_ID
        ))

    async def _world(self, session, character_id):
        return await session.scalar(select(WorldState).where(WorldState.character_id == character_id))

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity).where(
            GameActivity.character_id == character_id, GameActivity.status == "active"
        ))

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(quest and quest.status == "active" and quest.content_version == P4_VERSION
                    and quest.state_version == version and (step is None or quest.step == step))

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
