"""Authoritative P2 quest flow and scripted encounter settlement."""

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
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
from asterion.application.narrative_choices import (
    NarrativeNodeView,
    commit_mission_choice,
    narrative_node_view,
    resolve_future_hook,
)
from asterion.application.narrative_identity import resolve_character_scene
from asterion.application.progression import consolidate_character_level
from asterion.application.road import REFUGE, REGION, RoadService
from asterion.domain.combat import (
    Combat,
    CombatConsumableOption,
    act,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import (
    ENCOUNTER_CONSUMABLE_LIMITS,
    ConsumableFamily,
)
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.legacy import legacy_xp_factor
from asterion.domain.narrative_identity import P2_ALDA_OFFER_SCENE
from asterion.domain.road import (
    RULESET,
    SPIDER,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_combat,
    create_creature_party_combat,
    enemy_xp,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
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
    Unlock,
    WorldState,
)

P2_ID = "P2"
P2_TITLE = "Fuligem sem Fogo"
P2_VERSION = "tdo-1.0.7"
P2_COMBAT_CONTENT_ID = "p2_step3_scripted_spider"
P2_REWARD_SOURCE = "p2.fuligem_sem_fogo"

CHARNECA = "Charneca da Fuligem"
CHARNECA_LOCATION_ID = "tdo.location.charneca_da_fuligem"
ROUTE_UNLOCK = "route.tdo.refugio_charneca"
HUNT_UNLOCK = "hunt_manual.charneca_da_fuligem"
EXPLORE_UNLOCK = "explore.charneca_da_fuligem"
CODEX_MARKS_ENTRY = "codex.mystery.marcas_na_fuligem"
CODEX_OREN_ENTRY = "codex.figure.oren_cal"

ASH_POINT_IDS = (
    "p2.ash_point.1",
    "p2.ash_point.2",
    "p2.ash_point.3",
)
P2_MATERIAL_REWARDS = (
    ("material.tdo.ferro_de_fuligem", 1),
    ("material.tdo.erva_cinzenta", 2),
    ("material.tdo.residuo_ocaso", 1),
)


@dataclass(frozen=True)
class P2View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p2"
    combat: Combat | None = None
    activity_id: UUID | None = None
    activity_state_version: int | None = None
    activity_status: str | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    result_state: str | None = None
    rewarded: bool = False
    blocked_by_foreground: bool = False
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: CombatConsumableOption | None = None
    combat_actor_key: str | None = None
    group_size: int = 1
    proposal_id: UUID | None = None
    proposal_status: str | None = None
    # Identity-aware lines of the offer, resolved for this character only.
    identity_lines: tuple[str, ...] = ()
    identity_options: tuple[tuple[str, str], ...] = ()
    identity_reply: str | None = None
    narrative: NarrativeNodeView | None = None
    # (hook_id, option_id) a scene may react to; resolved only from legitimate memory.
    future_reactions: tuple[tuple[str, str], ...] = ()


P1_POSTURE_HOOK = "P1_choice_posture->P2"


class P2Service:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        groups: GroupService | None = None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.groups = groups
        # Share Bestiary rules and the established material-delivery policy.
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def alda(self, actor: int) -> P2View | None:
        """Return Alda's offer or the authoritative state without creating P2."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def resume(self, actor: int) -> P2View | None:
        """Rebuild an already-created P2 state; never pre-create the Quest."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def accept(self, actor: int, version: int = 0) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if quest is not None:
                return await self._view(session, character, quest, world)
            if version != 0 or not await self._eligible(
                session, character, world, quest
            ):
                return await self._view(session, character, quest, world)
            quest = Quest(
                character_id=character.id,
                quest_id=P2_ID,
                title=P2_TITLE,
                status="active",
                step=1,
                content_version=P2_VERSION,
                state_version=0,
                progress={"ash_points": []},
            )
            session.add(quest)
            await session.flush()
            return await self._view(session, character, quest, world)

    async def travel_to_charneca(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=1):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, REFUGE)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P2_ID,
                content_version=P2_VERSION,
                step=1,
                region=REGION,
                location=REFUGE,
            )
            for member in present:
                await self._ensure(
                    session,
                    LocationDiscovery,
                    character_id=member.character.id,
                    location_id=CHARNECA_LOCATION_ID,
                )
                await self._ensure(
                    session,
                    Unlock,
                    character_id=member.character.id,
                    unlock_id=ROUTE_UNLOCK,
                )
                member.world.region, member.world.location = REGION, CHARNECA
                member.quest.step = 2
                member.quest.state_version += 1
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "ash_points": [],
                }
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P2_ID,
                    objective_id="p2.travel.charneca",
                    source_key=f"p2.travel.charneca:{member.quest.state_version - 1}",
                    evidence={"from": REFUGE, "to": CHARNECA},
                )
            return await self._view(session, character, quest, world)

    async def examine_ash_point(
        self, actor: int, point_id: str, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=2):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, CHARNECA)
                or point_id not in ASH_POINT_IDS
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P2_ID,
                content_version=P2_VERSION,
                step=2,
                region=REGION,
                location=CHARNECA,
            )
            for member in present:
                progress = dict(member.quest.progress or {})
                points = list(progress.get("ash_points", []))
                if point_id in points:
                    continue
                points.append(point_id)
                progress["ash_points"] = points
                member.quest.progress = progress
                if len(points) == len(ASH_POINT_IDS):
                    member.quest.step = 3
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P2_ID,
                    objective_id="p2.ash_point",
                    source_key=f"p2.ash_point:{point_id}",
                    evidence={"point_id": point_id, "location": CHARNECA},
                )
            if len(roster_ids) == 1 and quest.step == 3:
                await self._materialize_combat(session, character, quest, world)
            return await self._view(session, character, quest, world)

    async def start_solo_combat(self, actor: int, version: int) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=3)
                or (quest.progress or {}).get("awaiting_retry")
                or len((quest.progress or {}).get("ash_points", [])) != len(ASH_POINT_IDS)
                or not self._at(world, CHARNECA)
                or await self._foreground(session, character.id) is not None
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
            await self._materialize_combat(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int) -> P2View | None:
        if self.groups is None:
            return await self.resume(actor)
        initial = await self.resume(actor)
        if (
            initial is None
            or initial.status != "active"
            or initial.step != 3
            or initial.state_version != version
            or initial.location != CHARNECA
            or len(initial.progress.get("ash_points", [])) != len(ASH_POINT_IDS)
        ):
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_p2",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._p2_combat_eligibility,
            context_payload={
                "quest_id": P2_ID,
                "checkpoint": "p2.aranha_cinza",
                "title": f"{P2_TITLE} · Aranha de Cinza",
                "reference_character_id": str(initial.character_id),
                "location": CHARNECA,
            },
            journey_reference_character_id=initial.character_id,
        )
        view = await self.resume(actor)
        return (
            replace(
                view,
                proposal_id=proposal.proposal_id,
                proposal_status=proposal.status,
            )
            if view is not None
            else None
        )

    async def start_group_combat(
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
    ) -> P2View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._p2_combat_eligibility,
            create_activity=self._create_p2_group_combat,
        )
        return await self.resume(actor)

    async def _p2_combat_eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == P2_ID,
            )
        )
        world = await self._world(session, character.id)
        active = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        )
        points = set((quest.progress or {}).get("ash_points", [])) if quest else set()
        if (
            active is not None
            or not self._at(world, CHARNECA)
            or payload.get("location") != CHARNECA
            or quest is None
            or quest.content_version != P2_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and points == set(ASH_POINT_IDS)
            and not (quest.progress or {}).get("awaiting_retry")
        ):
            role = "eligible"
        elif quest.status == "completed" or quest.step > 3:
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
            "ash_points": sorted(points),
            "location": world.location if world else None,
            "region": world.region if world else None,
            "active_activity": str(active.id) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
            "level": character.level,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_p2_group_combat(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
        characters: tuple[Character, ...],
    ) -> str:
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
        if any(roles.get(character.id) not in {"eligible", "helper"} for character in characters):
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
                    checkpoint="p2.aranha_cinza",
                )
            )
        lead = characters[0]
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(SPIDER, 3, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor="A fuligem se move sobre a pedra; a Aranha de Cinza avança.",
            opening_log="🕷️ Aranha de Cinza · Nv.3 surge entre a fuligem.",
            active_art_ids=party[0].active_art_ids,
            party=tuple(party),
        )
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=P2_ID,
            content_id=P2_COMBAT_CONTENT_ID,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint="p2.aranha_cinza",
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
            participant_quest = await session.scalar(
                select(Quest)
                .where(
                    Quest.character_id == member.character_id,
                    Quest.quest_id == P2_ID,
                )
                .with_for_update()
            )
            if participant_quest is not None and member.role == "eligible":
                participant_quest.progress = {
                    **(participant_quest.progress or {}),
                    "combat_activity_id": str(member.game_activity_id),
                }
            await self.bestiary.record(
                session,
                member.character_id,
                SPIDER.creature_id,
                evidence_id=f"habitat:{CHARNECA_LOCATION_ID}",
                evidence_category="habitat",
                evidence_points=3,
                grant_observation_xp=True,
                observation_level=3,
                observation_category="uncommon",
            )
        await session.flush()
        return str(encounter.id)

    async def action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ) -> P2View | None:
        async with self.sessions() as session:
            seed = await self._character(session, actor)
            shared = (
                await session.scalar(
                    select(CampaignSharedEncounterMember).where(
                        CampaignSharedEncounterMember.game_activity_id == activity_id,
                        CampaignSharedEncounterMember.character_id == seed.id,
                    )
                )
                if seed is not None
                else None
            )
        if shared is not None:
            return await self._shared_action(
                actor,
                activity_id,
                version,
                action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
            )
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None or quest is None:
                return await self._view(session, character, quest, world)
            if (
                quest.status != "active"
                or quest.content_version != P2_VERSION
                or quest.step != 3
                or activity.status != "active"
                or activity.state_version != version
                or not self._at(world, CHARNECA)
            ):
                return await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if foreground is None or foreground.id != activity.id:
                return await self._view(session, character, quest, world)
            if (action is None) == (consumable_id is None):
                return await self._view(session, character, quest, world)

            _, record = await CombatRepository(session).combat(activity)
            combat = decode(
                record.snapshot,
                record.id,
                activity.ruleset_version,
                activity.state_version,
            )
            stack = None
            if consumable_id is None:
                updated = act(
                    combat,
                    action,
                    target_id=target_id,
                    effect_id=effect_id,
                )
            else:
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
                budget_limit = ENCOUNTER_CONSUMABLE_LIMITS.get(
                    SPIDER.category, 0
                )
                updated = use_combat_consumable(
                    combat,
                    consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=budget_limit,
                )
            if updated.version == combat.version:
                return await self._view(session, character, quest, world)
            if stack is not None:
                stack.quantity -= 1

            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            character.hp = updated.fighters["player"].hp
            await self.bestiary.record_combat_events(
                session, character.id, SPIDER.creature_id, None, updated
            )

            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await self.bestiary.record(
                    session,
                    character.id,
                    SPIDER.creature_id,
                    victory=True,
                    observation_category="uncommon",
                )
                configuration = await load_equipment_configuration(
                    session, character
                )
                reconcile_character_hp(character, configuration)
                await consolidate_character_level(
                    session, character, configuration
                )
                reconcile_character_hp(character, configuration)
                progress.update(
                    combat_result="victory",
                    awaiting_retry=False,
                )
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session,
                    character.id,
                    SPIDER.creature_id,
                    observation_category="uncommon",
                )
                configuration = await load_equipment_configuration(
                    session, character
                )
                reconcile_character_hp(character, configuration)
                await consolidate_character_level(
                    session, character, configuration
                )
                reconcile_character_hp(character, configuration)
                character.hp = character.max_hp
                world.region, world.location = REGION, REFUGE
                progress.update(
                    combat_result="defeat",
                    awaiting_retry=True,
                    defeat_activity_id=str(activity.id),
                )

            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def campaign_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
    ) -> P2View | None:
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
        action, target_id = intent
        return await self._shared_action(
            actor, activity_id, version, action, target_id=target_id
        )

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
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _encounter_seed, member_seed, _combat_seed = await campaign_combat_for_activity(
                session, activity_id, seed.id
            )
            if member_seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id != P2_ID:
                return None
            character = locked.characters.get(seed.id)
            member = next(
                (row for row in locked.members if row.game_activity_id == activity_id),
                None,
            )
            activity = locked.activities.get(activity_id)
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(
                            Quest.character_id.in_(locked.characters),
                            Quest.quest_id == P2_ID,
                        )
                        .order_by(Quest.character_id)
                        .with_for_update()
                    )
                ).all()
            )
            quests = {row.character_id: row for row in quest_rows}
            quest = quests.get(seed.id)
            world = await self._world(session, seed.id)
            if character is None or quest is None or activity is None:
                return None
            if (
                member is None
                or locked.encounter.content_id != P2_COMBAT_CONTENT_ID
                or locked.encounter.state_version != version
                or activity.state_version != version
                or activity.status != "active"
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
                    return await self._view(session, character, quest, world)
            updated = resolve_campaign_action(
                locked,
                activity_id=activity_id,
                version=version,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(
                    SPIDER.category, 0
                ),
            )
            if updated.version == version:
                return await self._view(session, character, quest, world)
            if stack is not None:
                stack.quantity -= 1

            member_by_character = {row.character_id: row for row in locked.members}
            for character_id, participant in locked.characters.items():
                roster_member = member_by_character[character_id]
                participant_quest = quests.get(character_id)
                if updated.result:
                    await record_campaign_objective_credit(
                        session,
                        character_id=character_id,
                        quest_id=P2_ID,
                        objective_id="p2.aranha_cinza",
                        source_key=f"p2.aranha_cinza:{locked.encounter.id}",
                        evidence={
                            "result": updated.result,
                            "encounter_id": str(locked.encounter.id),
                        },
                    )
                await self.bestiary.record_combat_events(
                    session, character_id, SPIDER.creature_id, None, updated
                )
                if updated.result == "victory":
                    await self.bestiary.record(
                        session,
                        character_id,
                        SPIDER.creature_id,
                        victory=True,
                        observation_category="uncommon",
                    )
                    await self._grant_enemy_xp(
                        session,
                        participant,
                        locked.activities[roster_member.game_activity_id],
                    )
                    configuration = await load_equipment_configuration(
                        session, participant
                    )
                    reconcile_character_hp(participant, configuration)
                    await consolidate_character_level(
                        session, participant, configuration
                    )
                    reconcile_character_hp(participant, configuration)
                elif updated.result == "defeat":
                    await self.bestiary.record(
                        session,
                        character_id,
                        SPIDER.creature_id,
                        observation_category="uncommon",
                    )
                    participant.hp = participant.max_hp
                    participant_world = await self._world(session, character_id)
                    if participant_world is not None:
                        participant_world.region, participant_world.location = REGION, REFUGE
                if roster_member.role == "eligible" and participant_quest is not None:
                    progress = dict(participant_quest.progress or {})
                    if updated.result == "victory":
                        participant_quest.step = 4
                        progress.update(combat_result="victory", awaiting_retry=False)
                    elif updated.result == "defeat":
                        progress.update(
                            combat_result="defeat",
                            awaiting_retry=True,
                            defeat_activity_id=str(roster_member.game_activity_id),
                        )
                    if updated.result:
                        participant_quest.progress = progress
                        participant_quest.state_version += 1
            if updated.result:
                await settle_campaign_encounter(session, locked, updated.result)
            return await self._view(session, character, quest, world)

    async def consumable_selection(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        screen: str = "items",
        item_id: str | None = None,
        target_id: str | None = None,
        parent: str = "items",
    ) -> P2View | None:
        """Rebuild the shared combat Consumable chooser without persisting UI state."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                quest.status != "active"
                or quest.step != 3
                or activity.status != "active"
                or foreground is None
                or foreground.id != activity.id
            ):
                return current
            if activity.state_version != version:
                return replace(
                    current,
                    consumable_notice=self._consumable_rejection_notice(
                        current.combat, current.consumable_budget_limit
                    ),
                )
            if screen == "combat":
                return current
            if screen == "items":
                return (
                    replace(current, consumable_screen="items")
                    if current.consumable_options
                    else current
                )

            item = consumable_definition(item_id or "")
            item_options = tuple(
                option
                for option in current.consumable_options
                if option.item_id == item_id
            )
            if item is None or not item_options:
                if current.consumable_options:
                    return replace(
                        current,
                        consumable_screen="items",
                        consumable_notice="⚠️ Consumível · Não está mais disponível.",
                    )
                return current

            if screen == "choose_item":
                if item.family == ConsumableFamily.DISPELLER:
                    target_ids = tuple(
                        dict.fromkeys(option.target_id for option in item_options)
                    )
                    if len(target_ids) > 1:
                        return replace(
                            current,
                            consumable_screen="targets",
                            selected_consumable_id=item.id,
                            selection_parent="items",
                        )
                    target_id = target_ids[0] if target_ids else None
                    parent = "items"
                else:
                    target_id = "player"
                    parent = "items"
                selected = tuple(
                    option for option in item_options if option.target_id == target_id
                )
                return self._selection_after_target(
                    current, item, target_id, selected, parent=parent
                )

            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(
                    option for option in item_options if option.target_id == target_id
                )
                if not selected:
                    return replace(
                        current,
                        consumable_screen=(
                            "items" if current.consumable_options else None
                        ),
                        consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
                    )
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )

            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                target_ids = tuple(
                    dict.fromkeys(option.target_id for option in item_options)
                )
                if len(target_ids) > 1:
                    return replace(
                        current,
                        consumable_screen="targets",
                        selected_consumable_id=item.id,
                        selection_parent="items",
                    )
                return replace(
                    current,
                    consumable_screen="items",
                    consumable_notice=(
                        "⚠️ Dissipador · Sem Alvo Válido" if not target_ids else None
                    ),
                )

            if screen == "effects" and target_id is not None:
                selected = tuple(
                    option
                    for option in item_options
                    if option.target_id == target_id and option.effect_id is not None
                )
                if len(selected) > 1:
                    return replace(
                        current,
                        consumable_screen="effects",
                        selected_consumable_id=item.id,
                        selected_target_id=target_id,
                        selection_parent=parent,
                    )
                return replace(
                    current,
                    consumable_screen="items",
                    consumable_notice=(
                        "⚠️ Dissipador · Sem Efeito Removível"
                        if item.family == ConsumableFamily.DISPELLER and not selected
                        else "⚠️ Consumível · Não está mais disponível."
                        if not selected
                        else None
                    ),
                )

            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
            )

    @staticmethod
    def _selection_after_target(current, item, target_id, selected, *, parent):
        if not selected:
            return replace(
                current,
                consumable_screen=("items" if current.consumable_options else None),
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
            )
        if len(selected) == 1:
            return replace(current, ready_consumable_option=selected[0])
        return replace(
            current,
            consumable_screen="effects",
            selected_consumable_id=item.id,
            selected_target_id=target_id,
            selection_parent=parent,
        )

    @staticmethod
    def _consumable_rejection_notice(combat, budget_limit):
        if combat is None:
            return None
        player = combat.fighters["player"]
        if player.cooldowns.get("consumable", 0) > player.opportunity:
            return "⏳ Consumíveis · Em Recarga"
        if budget_limit and combat.consumable_uses >= budget_limit:
            return "🔒 Consumíveis · Limite Atingido"
        return None

    async def return_to_charneca(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            foreground = await self._foreground(session, character.id)
            if foreground is not None:
                return await self._view(session, character, quest, world)
            if (
                not self._valid(quest, version, step=3)
                or not (quest.progress or {}).get("awaiting_retry")
                or not self._at(world, REFUGE)
            ):
                return await self._view(session, character, quest, world)

            route = await session.scalar(
                select(Unlock).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == ROUTE_UNLOCK,
                )
            )
            if route is None:
                return await self._view(session, character, quest, world)
            world.region, world.location = REGION, CHARNECA
            progress = dict(quest.progress or {})
            progress["awaiting_retry"] = False
            quest.progress = progress
            await self._materialize_combat(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def examine_pedra_marcada(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=4):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, CHARNECA)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P2_ID,
                content_version=P2_VERSION,
                step=4,
                region=REGION,
                location=CHARNECA,
            )
            for member in present:
                progress = dict(member.quest.progress or {})
                if progress.get("stone_examined"):
                    continue
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=member.character.id,
                    entry_id=CODEX_MARKS_ENTRY,
                )
                progress["stone_examined"] = True
                progress["stone_evidence"] = (
                    "recurrent marks associated with ash and the route; authorship unknown"
                )
                member.quest.progress = progress
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P2_ID,
                    objective_id="p2.marked_stone",
                    source_key="p2.marked_stone:charneca",
                    evidence={"location": CHARNECA},
                )
            return await self._view(session, character, quest, world)

    async def return_to_refuge(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=4):
                return await self._view(session, character, quest, world)
            if (
                not (quest.progress or {}).get("stone_examined")
                or not self._at(world, CHARNECA)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)
            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P2_ID,
                content_version=P2_VERSION,
                step=4,
                region=REGION,
                location=CHARNECA,
            )
            for member in present:
                if not (member.quest.progress or {}).get("stone_examined"):
                    continue
                member.world.region, member.world.location = REGION, REFUGE
                member.quest.step = 5
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P2_ID,
                    objective_id="p2.return_refuge",
                    source_key=f"p2.return_refuge:{member.quest.state_version - 1}",
                    evidence={"from": CHARNECA, "to": REFUGE},
                )
            return await self._view(session, character, quest, world)

    async def oren(
        self, actor: int, version: int, option_id: str | None = None
    ) -> P2View | None:
        """Etapa 5 ends through P2_evidentiary_posture (individual, commit once)."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=5):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, REFUGE)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)
            node = await narrative_node_view(session, character, P2_ID)
            if node is not None and node.pending:
                if option_id is None or (
                    await commit_mission_choice(session, character, quest, option_id)
                ) is None:
                    return await self._view(session, character, quest, world)
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=CODEX_OREN_ENTRY,
            )
            progress = dict(quest.progress or {})
            progress["oren_spoken"] = True
            quest.progress = progress
            quest.step = 6
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def report_to_alda(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if quest.status == "completed":
                return await self._view(session, character, quest, world)
            if not self._valid(quest, version, step=6):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, REFUGE)
                or not (quest.progress or {}).get("oren_spoken")
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P2_REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                event = RewardEvent(
                    character_id=character.id,
                    source_id=P2_REWARD_SOURCE,
                )
                session.add(event)
                await session.flush()
                character.xp += 3300
                character.crowns += 140
                components = [
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        item_id=None,
                        quantity=3300,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        item_id=None,
                        quantity=140,
                    ),
                ]
                components.extend(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=material_id,
                        quantity=quantity,
                        payload={"material_id": material_id, "bound": True},
                    )
                    for material_id, quantity in P2_MATERIAL_REWARDS
                )
                session.add_all(components)
                for material_id, quantity in P2_MATERIAL_REWARDS:
                    await self.road.deliver_material(
                        session,
                        character,
                        material_id,
                        quantity,
                        f"{P2_REWARD_SOURCE}:material:{material_id}",
                        bound=True,
                    )

            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=HUNT_UNLOCK,
            )
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=EXPLORE_UNLOCK,
            )
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=ROUTE_UNLOCK,
            )
            configuration = await load_equipment_configuration(
                session, character
            )
            reconcile_character_hp(character, configuration)
            await consolidate_character_level(
                session, character, configuration
            )
            reconcile_character_hp(character, configuration)
            quest.status = "completed"
            quest.progress = {
                **(quest.progress or {}),
                "completed": True,
                "awaiting_retry": False,
            }
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _materialize_combat(
        self, session, character, quest, world
    ) -> GameActivity | None:
        if not self._at(world, CHARNECA):
            return None
        foreground = await self._foreground(session, character.id)
        if foreground is not None:
            return (
                foreground
                if foreground.content_id == P2_COMBAT_CONTENT_ID
                else None
            )
        reservation = await session.scalar(
            select(GroupActivityParticipant).where(
                GroupActivityParticipant.character_id == character.id,
                GroupActivityParticipant.reservation_state == "active",
            )
        )
        if reservation is not None:
            return None
        configuration = await load_equipment_configuration(session, character)
        active_art_configuration = await load_active_art_configuration(session, character)
        reconcile_character_hp(character, configuration)
        combat = create_creature_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            character.hp,
            SPIDER,
            3,
            None,
            player_level=character.level,
            equipment_configuration=configuration,
            ruleset_version=RULESET,
            flavor="A fuligem se move sobre a pedra; a Aranha de Cinza avança.",
            opening_log="🕷️ Aranha de Cinza · Nv.3 surge entre a fuligem.",
            active_art_ids=active_art_configuration.art_ids,
        )
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | (
            active_art_configuration.to_data()
        )
        activity, _, _ = await CombatRepository(session).create(
            character, P2_COMBAT_CONTENT_ID, combat
        )
        progress = dict(quest.progress or {})
        progress.update(
            combat_activity_id=str(activity.id),
            combat_result=None,
            awaiting_retry=False,
        )
        quest.progress = progress
        await self.bestiary.record(
            session,
            character.id,
            SPIDER.creature_id,
            evidence_id=f"habitat:{CHARNECA_LOCATION_ID}",
            evidence_category="habitat",
            evidence_points=3,
            grant_observation_xp=True,
            observation_level=3,
            observation_category="uncommon",
        )
        await session.flush()
        return activity

    async def _grant_enemy_xp(
        self, session, character: Character, activity: GameActivity
    ) -> int:
        source_id = f"{P2_REWARD_SOURCE}:enemy-xp:{activity.id}"
        existing = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return 0
        xp = enemy_xp(
            3,
            "uncommon",
            player_level=character.level,
            legacy_factor=legacy_xp_factor(character.legacy_level),
        )
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="enemy_xp",
                item_id=SPIDER.creature_id,
                quantity=xp,
                payload={
                    "enemy_level": 3,
                    "category": "uncommon",
                    "observation_context": "P2",
                },
            )
        )
        character.xp += xp
        return xp

    async def _locked_state(self, session, actor):
        seed = await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )
        if seed is None:
            return None, None, None
        await lock_campaign_roster(session, seed.id)
        character = await session.scalar(
            select(Character)
            .where(Character.id == seed.id)
            .with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character.id,
                Quest.quest_id == P2_ID,
            )
            .with_for_update()
        )
        world = await session.scalar(
            select(WorldState)
            .where(WorldState.character_id == character.id)
            .with_for_update()
        )
        return character, quest, world

    async def _social_group_size(self, session, character_id):
        """This encounter is not a Boss: missions stay Solo (Ação × Consequência §5)."""
        return 1
    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _quest(self, session, character_id):
        return await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P2_ID,
            )
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(
                WorldState.character_id == character_id
            )
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity)
            .where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
            .with_for_update()
        )

    async def _eligible(self, session, character, world, quest):
        if (
            quest is not None
            or character.level < 3
            or world is None
            or world.region != REGION
            or world.location != REFUGE
        ):
            return False
        p1_completed = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == "P1",
                Quest.status == "completed",
            )
        )
        if p1_completed is None:
            return False
        return await self._foreground(session, character.id) is None

    async def _view(self, session, character, quest, world):
        if character is None:
            return None
        world = world or await self._world(session, character.id)
        progress = dict(quest.progress or {}) if quest is not None else {}
        active = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        activity = active
        if activity is None and progress.get("combat_activity_id"):
            try:
                stored_activity_id = UUID(progress["combat_activity_id"])
            except (TypeError, ValueError):
                stored_activity_id = None
            if stored_activity_id is not None:
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == stored_activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                    )
                )

        encounter_id = None
        combat_id = None
        combat = None
        combat_actor_key = None
        group_size = await self._social_group_size(session, character.id)
        if activity is not None:
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity.id, character.id
            )
            if shared is not None and shared_member is not None:
                encounter_id, combat_id = shared.id, shared.id
                combat = shared_combat if activity.status == "active" else None
                combat_actor_key = shared_member.actor_key
                group_size = shared.roster_size
            else:
                pair = await session.execute(
                    select(Encounter, CombatRecord)
                    .join(CombatRecord)
                    .where(Encounter.game_activity_id == activity.id)
                )
                row = pair.first()
                if row is not None:
                    encounter, record = row
                    encounter_id, combat_id = encounter.id, record.id
                    combat = decode(
                        record.snapshot,
                        record.id,
                        activity.ruleset_version,
                        activity.state_version,
                    )

        consumable_options = ()
        consumable_quantities = ()
        consumable_budget_limit = 0
        if (
            activity is not None
            and activity.status == "active"
            and combat is not None
        ):
            consumable_budget_limit = ENCOUNTER_CONSUMABLE_LIMITS.get(
                SPIDER.category, 0
            )
            stock = (
                await session.scalars(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character.id,
                        ConsumableStack.quantity > 0,
                    )
                    .order_by(ConsumableStack.consumable_id)
                )
            ).all()
            stock_ids = tuple(row.consumable_id for row in stock)
            consumable_quantities = tuple(
                (row.consumable_id, row.quantity) for row in stock
            )
            consumable_options = combat_consumable_options(
                combat,
                stock_ids,
                budget_limit=consumable_budget_limit,
                actor_key=combat_actor_key,
            )

        foreground = await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        )
        blocked_by_foreground = bool(
            foreground is not None and (activity is None or foreground != activity.id)
        )
        available = (
            await self._eligible(session, character, world, quest)
            if quest is None
            else False
        )
        if quest is None:
            kind = "offer" if available else "unavailable"
            status = None
            step = None
            state_version = 0
        else:
            status = quest.status
            step = quest.step
            state_version = quest.state_version
            if active is not None:
                kind = "combat"
            elif quest.status == "completed":
                kind = "completed"
            elif step == 1:
                kind = "travel"
            elif step == 2:
                kind = "ash_points"
            elif step == 3 and progress.get("awaiting_retry"):
                kind = "recovery"
            elif step == 3:
                kind = "combat_pending"
            elif step == 4:
                kind = "stone"
            elif step == 5:
                kind = "oren"
            else:
                kind = "alda"

        rewarded = bool(
            await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P2_REWARD_SOURCE,
                )
            )
        )
        result_state = progress.get("combat_result")
        if progress.get("awaiting_retry"):
            result_state = "awaiting_retry"
        proposal_pair = None
        if active is None:
            proposal_rows = await session.execute(
                select(GroupActivityParticipant, GroupActivityProposal)
                .join(
                    GroupActivityProposal,
                    GroupActivityProposal.id == GroupActivityParticipant.proposal_id,
                )
                .where(
                    GroupActivityParticipant.character_id == character.id,
                    GroupActivityParticipant.reservation_state == "active",
                    GroupActivityProposal.activity_type == "campaign_p2",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .order_by(
                    GroupActivityProposal.created_at.desc(),
                    GroupActivityProposal.id,
                )
                .limit(1)
            )
            proposal_pair = proposal_rows.first()
        identity_lines: tuple[str, ...] = ()
        identity_options: tuple[tuple[str, str], ...] = ()
        future_reactions: tuple[tuple[str, str], ...] = ()
        narrative = (
            await narrative_node_view(session, character, P2_ID)
            if kind in {"oren", "alda"}
            else None
        )
        if kind == "offer":
            posture = await resolve_future_hook(session, character.id, P1_POSTURE_HOOK)
            if posture is not None:
                future_reactions = ((P1_POSTURE_HOOK, posture),)
            offer = await resolve_character_scene(session, character.id, P2_ALDA_OFFER_SCENE)
            if offer is not None:
                identity_lines = offer.spoken_lines
                identity_options = tuple(
                    (option.option_id, option.label) for option in offer.options
                )
        return P2View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=step,
            state_version=state_version,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=available,
            combat=combat,
            activity_id=activity.id if activity is not None else None,
            activity_state_version=(
                activity.state_version if activity is not None else None
            ),
            activity_status=activity.status if activity is not None else None,
            encounter_id=encounter_id,
            combat_id=combat_id,
            result_state=result_state,
            rewarded=rewarded,
            blocked_by_foreground=blocked_by_foreground,
            consumable_options=consumable_options,
            consumable_quantities=consumable_quantities,
            consumable_budget_limit=consumable_budget_limit,
            combat_actor_key=combat_actor_key,
            group_size=group_size,
narrative=narrative,
            future_reactions=future_reactions,
                        proposal_id=proposal_pair[1].id if proposal_pair else None,
            proposal_status=proposal_pair[1].status if proposal_pair else None,
            identity_lines=identity_lines,
            identity_options=identity_options,
        )

    async def ask_alda(self, actor: int, option_id: str) -> P2View | None:
        """Answer an identity option of the offer; read-only, records nothing."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            view = await self._view(session, character, quest, world)
            if view.kind != "offer":
                return view
            offer = await resolve_character_scene(session, character.id, P2_ALDA_OFFER_SCENE)
            option = offer.option(option_id) if offer is not None else None
            if option is None:
                return view
            return replace(view, identity_reply=option.reply)

    def _valid(self, quest, version, *, step=None):
        return bool(
            quest is not None
            and quest.status == "active"
            and quest.content_version == P2_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(
            world is not None
            and world.region == REGION
            and world.location == location
        )

    async def _ensure(self, session, model, **values):
        existing = await session.scalar(
            select(model).filter_by(**values).with_for_update()
        )
        if existing is not None:
            return existing
        row = model(**values)
        session.add(row)
        await session.flush()
        return row
