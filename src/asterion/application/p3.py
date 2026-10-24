"""Authoritative P3 mission flow composed from the shared Quest/combat/reward systems."""

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
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
    BOSQUE_ROUTE_UNLOCK,
    CHARNECA,
    P2_QUEST_ID,
    REFUGE,
    REGION,
    RoadService,
)
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
from asterion.domain.road import (
    BOSQUE_LOCATION,
    CERVO,
    RULESET,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_combat,
    create_creature_party_combat,
    enemy_xp,
    materialize_equipment,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    ConsumableStack,
    Encounter,
    EquipmentItem,
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

P3_ID = "P3"
P3_TITLE = "Sob Galhos Calcinados"
P3_VERSION = "tdo-1.0.10"
P3_COMBAT_CONTENT_ID = "p3_scripted_cervo_escoriado"
P3_REWARD_SOURCE = "p3.sob_galhos_calcinados"
P3_FRAGMENTS = ("p3.fragment.1", "p3.fragment.2", "p3.fragment.3")
P3_LOCATION_ID = BOSQUE_LOCATION
P3_ROUTE_UNLOCK = BOSQUE_ROUTE_UNLOCK
P3_CODEX_OLD_ASTERIANS = "codex.history.antigos_asterianos"
P3_CODEX_FRAGMENT = "p3.bosque.fragmento_entalhado"
P3_MARKS_FRAGMENT = "p3.bosque.associacao_arquitetonica"
S3_ID = "S3"
CHARNECA_LOCATION = "tdo.location.charneca_da_fuligem"
CHARNECA_ROUTE_UNLOCK = "route.tdo.refugio_charneca"

P3_REWARD_CHOICES = {
    "veil": ("Véu do Bosque", "Cabeça"),
    "seal": ("Selo do Galho Morto", "Acessório"),
    "reliquary": ("Relicário da Cinza Verde", "Artefato"),
}


@dataclass(frozen=True)
class P3View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p3"
    combat: Combat | None = None
    activity_id: UUID | None = None
    activity_state_version: int | None = None
    activity_status: str | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: CombatConsumableOption | None = None
    xp: int = 0
    combat_actor_key: str = "player"
    group_size: int = 1
    proposal_id: UUID | None = None
    proposal_status: str | None = None


class P3Service:
    """Quest-specific P3 flow; combat, delivery, bestiary and progression stay shared."""

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

    async def oren(self, actor: int) -> P3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "oren")

    async def offer(self, actor: int) -> P3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is not None:
                return await self._view(session, character, quest, world)
            available = (
                self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and await self._eligible(session, character)
            )
            return await self._view(
                session, character, None, world, "offer" if available else "unavailable"
            )

    async def resume(self, actor: int) -> P3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def objective(self, actor: int) -> P3View | None:
        return await self.resume(actor)

    async def accept(self, actor: int, version: int = 0) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if quest is not None or version != 0 or not self._at(world, REFUGE):
                return await self._view(session, character, quest, world)
            if await self._foreground(session, character.id) or not await self._eligible(
                session, character
            ):
                return await self._view(session, character, quest, world)
            quest = Quest(
                character_id=character.id,
                quest_id=P3_ID,
                title=P3_TITLE,
                status="active",
                step=1,
                content_version=P3_VERSION,
                state_version=0,
                progress={"fragments": []},
            )
            session.add(quest)
            await session.flush()
            return await self._view(session, character, quest, world)

    async def mission_route(self, actor: int, version: int, destination: str) -> P3View | None:
        """Move present, eligible P3 members together along the explicit mission path."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None or world is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            if not await self._destination_allowed(session, character, quest, world, destination):
                return await self._view(session, character, quest, world)
            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P3_ID,
                content_version=P3_VERSION,
                step=quest.step,
                region=REGION,
                location=world.location,
            )
            for member in present:
                if not await self._destination_allowed(
                    session, member.character, member.quest, member.world, destination
                ):
                    continue
                from_location = member.world.location
                member.world.region = REGION
                member.world.location = destination
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P3_ID,
                    objective_id="p3.route",
                    source_key=(
                        f"p3.route:{member.quest.step}:{from_location}:{destination}:"
                        f"{member.quest.state_version - 1}"
                    ),
                    evidence={"from": from_location, "to": destination},
                )
            return await self._view(session, character, quest, world)

    async def s3_campaign_route(self, actor: int, s3_version: int, destination: str) -> bool:
        """Move one adjacent step on the existing campaign route for an active S3 retry."""
        async with self.sessions.begin() as session:
            character, p3, world = await self._locked_state(session, actor)
            if character is None or p3 is None or world is None:
                return False
            s3 = await session.scalar(
                select(Quest)
                .where(Quest.character_id == character.id, Quest.quest_id == S3_ID)
                .with_for_update()
            )
            if (
                p3.status != "active" or s3 is None or s3.status != "active"
                or s3.content_version != "tdo-1.0.11"
                or s3.state_version != s3_version
                or await self._foreground(session, character.id)
            ):
                return False
            allowed = False
            if {world.location, destination} == {REFUGE, CHARNECA}:
                allowed = await self._has_unlock(session, character.id, CHARNECA_ROUTE_UNLOCK)
            elif {world.location, destination} == {CHARNECA, BOSQUE}:
                allowed = await self._has_unlock(session, character.id, P3_ROUTE_UNLOCK)
            if not allowed:
                return False
            world.region = REGION
            world.location = destination
            s3.state_version += 1
            return True

    async def enter_bosque(self, actor: int, version: int) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None or world is None:
                return None
            progress = dict(quest.progress or {})
            first_entry = quest.step == 1 and not progress.get("bosque_entered")
            retry_return = quest.step == 3 and progress.get("awaiting_retry")
            if (
                not self._valid(quest, version)
                or not self._at(world, CHARNECA)
                or not (first_entry or retry_return)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            if first_entry:
                roster_ids = await campaign_roster_ids(session, character.id)
                present = await present_campaign_members(
                    session,
                    character_ids=roster_ids,
                    quest_id=P3_ID,
                    content_version=P3_VERSION,
                    step=1,
                    region=REGION,
                    location=CHARNECA,
                )
                for member in present:
                    member_progress = dict(member.quest.progress or {})
                    if member_progress.get("bosque_entered"):
                        continue
                    await self._ensure(
                        session,
                        LocationDiscovery,
                        character_id=member.character.id,
                        location_id=P3_LOCATION_ID,
                    )
                    await self._ensure(
                        session,
                        Unlock,
                        character_id=member.character.id,
                        unlock_id=P3_ROUTE_UNLOCK,
                    )
                    member.world.region = REGION
                    member.world.location = BOSQUE
                    member_progress.update(bosque_entered=True, fragments=[])
                    member.quest.progress = member_progress
                    member.quest.step = 2
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=P3_ID,
                        objective_id="p3.enter_bosque",
                        source_key="p3.enter_bosque:first-entry",
                        evidence={"location_id": P3_LOCATION_ID},
                    )
            else:
                if not await self._has_unlock(session, character.id, P3_ROUTE_UNLOCK):
                    return await self._view(session, character, quest, world)
                roster_ids = await campaign_roster_ids(session, character.id)
                present = await present_campaign_members(
                    session,
                    character_ids=roster_ids,
                    quest_id=P3_ID,
                    content_version=P3_VERSION,
                    step=3,
                    region=REGION,
                    location=CHARNECA,
                )
                for member in present:
                    member_progress = dict(member.quest.progress or {})
                    if not member_progress.get("awaiting_retry") or not await self._has_unlock(
                        session, member.character.id, P3_ROUTE_UNLOCK
                    ):
                        continue
                    member.world.region = REGION
                    member.world.location = BOSQUE
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=P3_ID,
                        objective_id="p3.retry_route",
                        source_key=f"p3.retry_route:{member.quest.state_version - 1}",
                        evidence={"from": CHARNECA, "to": BOSQUE},
                    )
            return await self._view(session, character, quest, world)

    async def examine_fragment(self, actor: int, fragment_id: str, version: int) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=2)
                or not self._at(world, BOSQUE)
                or fragment_id not in P3_FRAGMENTS
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P3_ID,
                content_version=P3_VERSION,
                step=2,
                region=REGION,
                location=BOSQUE,
            )
            for member in present:
                member_progress = dict(member.quest.progress or {})
                found = set(member_progress.get("fragments", ()))
                if fragment_id in found:
                    continue
                found.add(fragment_id)
                member_progress["fragments"] = [item for item in P3_FRAGMENTS if item in found]
                member.quest.progress = member_progress
                if len(found) == len(P3_FRAGMENTS):
                    member.quest.step = 3
                    member_progress.update(awaiting_retry=False, combat_result=None)
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P3_ID,
                    objective_id="p3.fragment",
                    source_key=f"p3.fragment:{fragment_id}",
                    evidence={"fragment_id": fragment_id, "location": BOSQUE},
                )
            if quest.step == 3 and await self._social_group_size(session, character.id) == 1:
                await self._materialize_combat(session, character, quest)
            return await self._view(session, character, quest, world)

    async def retry(self, actor: int, version: int) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or not progress.get("awaiting_retry")
                or not self._at(world, BOSQUE)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P3_ID,
                content_version=P3_VERSION,
                step=3,
                region=REGION,
                location=BOSQUE,
            )
            for member in present:
                member_progress = dict(member.quest.progress or {})
                if not member_progress.get("awaiting_retry"):
                    continue
                member_progress.update(awaiting_retry=False, combat_pending=False)
                member.quest.progress = member_progress
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P3_ID,
                    objective_id="p3.retry",
                    source_key=f"p3.retry:{member.quest.state_version - 1}",
                    evidence={"location": BOSQUE},
                )
            if await self._social_group_size(session, character.id) == 1:
                activity = await self._materialize_combat(session, character, quest)
                if activity is None:
                    progress["awaiting_retry"] = True
                    quest.progress = progress
                    return await self._view(session, character, quest, world)
            return await self._view(session, character, quest, world)

    async def start_solo_combat(self, actor: int, version: int) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None or world is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or progress.get("awaiting_retry")
                or len(progress.get("fragments", ())) != len(P3_FRAGMENTS)
                or not self._at(world, BOSQUE)
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
            await self._materialize_combat(session, character, quest)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int) -> P3View | None:
        if self.groups is None:
            return await self.resume(actor)
        initial = await self.resume(actor)
        if (
            initial is None
            or initial.status != "active"
            or initial.step != 3
            or initial.state_version != version
            or initial.location != BOSQUE
            or len(initial.progress.get("fragments", ())) != len(P3_FRAGMENTS)
            or initial.progress.get("awaiting_retry")
        ):
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_p3",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._p3_combat_eligibility,
            context_payload={
                "quest_id": P3_ID,
                "checkpoint": "p3.cervo_escoriado",
                "title": f"{P3_TITLE} · Cervo Escoriado",
                "reference_character_id": str(initial.character_id),
                "location": BOSQUE,
            },
            journey_reference_character_id=initial.character_id,
        )
        view = await self.resume(actor)
        return (
            replace(view, proposal_id=proposal.proposal_id, proposal_status=proposal.status)
            if view is not None
            else None
        )

    async def start_group_combat(
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
    ) -> P3View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._p3_combat_eligibility,
            create_activity=self._create_p3_group_combat,
        )
        return await self.resume(actor)

    async def campaign_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
    ) -> P3View | None:
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
                or encounter.quest_id != P3_ID
                or encounter.content_id != P3_COMBAT_CONTENT_ID
                or combat is None
            ):
                return None
            intent = campaign_action_intent(
                combat, member.actor_key, action_index, target_code
            )
            if intent is None:
                return await self.resume(actor)
            action, target_id = intent
        return await self.action(
            actor, activity_id, version, action, target_id=target_id
        )

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
    ) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P3_COMBAT_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None or quest is None:
                return None
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
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                quest.status != "active"
                or quest.content_version != P3_VERSION
                or quest.step != 3
                or activity.status != "active"
                or activity.state_version != version
                or foreground is None
                or foreground.id != activity.id
                or not self._at(world, BOSQUE)
                or (action is None) == (consumable_id is None)
            ):
                return current
            _, record = await CombatRepository(session).combat(activity)
            combat = decode(
                record.snapshot, record.id, activity.ruleset_version, activity.state_version
            )
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
                    return replace(
                        current, consumable_notice="⚠️ Consumível · Não está mais disponível."
                    )
                updated = use_combat_consumable(
                    combat,
                    consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=ENCOUNTER_CONSUMABLE_LIMITS.get(CERVO.category, 0),
                )
                if updated.version == combat.version:
                    return replace(
                        current, consumable_notice="⚠️ Consumível · Não está mais disponível."
                    )
                stack.quantity -= 1
            if updated.version == combat.version:
                return current
            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            character.hp = updated.fighters["player"].hp
            await self.bestiary.record_combat_events(
                session, character.id, CERVO.creature_id, None, updated
            )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await self.bestiary.record(
                    session,
                    character.id,
                    CERVO.creature_id,
                    victory=True,
                    observation_category="common",
                )
                await self._normalize_character_hp(session, character)
                quest.step = 4
                progress.update(combat_result="victory", awaiting_retry=False)
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session, character.id, CERVO.creature_id, observation_category="common"
                )
                recovery_brazier, recovery_location = await self.road.recover_normal_pve_defeat(
                    session, character, BOSQUE_LOCATION, world
                )
                progress.update(
                    combat_result="defeat",
                    awaiting_retry=True,
                    defeat_activity_id=str(activity.id),
                    recovery_brazier=recovery_brazier,
                    recovery_location=recovery_location,
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _shared_action(
        self,
        session: AsyncSession,
        character: Character,
        quest: Quest,
        world: WorldState | None,
        activity_id: UUID,
        version: int,
        action: str | None,
        *,
        consumable_id: str | None,
        target_id: str | None,
        effect_id: str | None,
    ) -> P3View:
        locked = await lock_campaign_encounter(session, activity_id, character.id)
        if locked is None or locked.encounter.content_id != P3_COMBAT_CONTENT_ID:
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
            consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(CERVO.category, 0),
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
                        Quest.quest_id == P3_ID,
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
            if updated.result:
                await record_campaign_objective_credit(
                    session,
                    character_id=character_id,
                    quest_id=P3_ID,
                    objective_id="p3.cervo_escoriado",
                    source_key=f"p3.cervo_escoriado:{locked.encounter.id}",
                    evidence={"result": updated.result, "encounter_id": str(locked.encounter.id)},
                )
            await self.bestiary.record_combat_events(
                session, character_id, CERVO.creature_id, None, updated
            )
            if updated.result == "victory":
                await self.bestiary.record(
                    session,
                    character_id,
                    CERVO.creature_id,
                    victory=True,
                    observation_category="common",
                )
                if roster_member.role == "eligible":
                    await self._grant_enemy_xp(
                        session,
                        participant,
                        locked.activities[roster_member.game_activity_id],
                    )
                    configuration = await load_equipment_configuration(session, participant)
                    reconcile_character_hp(participant, configuration)
                    await consolidate_character_level(session, participant, configuration)
                    reconcile_character_hp(participant, configuration)
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
                    session, character_id, CERVO.creature_id, observation_category="common"
                )
                participant_world = worlds_by_character.get(character_id)
                recovery_brazier, recovery_location = await self.road.recover_normal_pve_defeat(
                    session, participant, BOSQUE_LOCATION, participant_world
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
                        recovery_brazier=recovery_brazier,
                        recovery_location=recovery_location,
                    )
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
    ) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P3_COMBAT_CONTENT_ID,
                )
                .with_for_update()
            )
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
                or foreground is None
                or foreground.id != activity.id
            ):
                return current
            if activity.state_version != version:
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            if screen == "combat":
                return current
            if screen == "items":
                return (
                    replace(current, consumable_screen="items")
                    if current.consumable_options
                    else current
                )
            item = consumable_definition(item_id or "")
            options = tuple(
                option for option in current.consumable_options if option.item_id == item_id
            )
            if item is None or not options:
                return replace(
                    current,
                    consumable_screen=None,
                    consumable_notice="⚠️ Consumível · Não está mais disponível.",
                )
            if screen == "choose_item":
                targets = tuple(dict.fromkeys(option.target_id for option in options))
                if item.family == ConsumableFamily.DISPELLER and len(targets) > 1:
                    return replace(
                        current, consumable_screen="targets", selected_consumable_id=item.id
                    )
                target_id = (
                    targets[0]
                    if item.family == ConsumableFamily.DISPELLER and targets
                    else "player"
                )
                selected = tuple(option for option in options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent="items"
                )
            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(option for option in options if option.target_id == target_id)
                if not selected:
                    return replace(
                        current,
                        consumable_screen="items",
                        consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
                    )
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )
            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                targets = tuple(dict.fromkeys(option.target_id for option in options))
                return replace(
                    current,
                    consumable_screen="targets" if len(targets) > 1 else "items",
                    selected_consumable_id=item.id if len(targets) > 1 else None,
                )
            if screen == "effects" and target_id is not None:
                selected = tuple(
                    option
                    for option in options
                    if option.target_id == target_id and option.effect_id is not None
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
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
            )

    @staticmethod
    def _selection_after_target(current, item, target_id, selected, *, parent):
        if len(selected) == 1:
            return replace(current, ready_consumable_option=selected[0])
        if not selected:
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
            )
        return replace(
            current,
            consumable_screen="effects",
            selected_consumable_id=item.id,
            selected_target_id=target_id,
            selection_parent=parent,
        )

    async def examine_carved_fragment(self, actor: int, version: int) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=4)
                or not self._at(world, BOSQUE)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P3_ID,
                content_version=P3_VERSION,
                step=4,
                region=REGION,
                location=BOSQUE,
            )
            for member in present:
                member_progress = dict(member.quest.progress or {})
                if (
                    member_progress.get("combat_result") != "victory"
                    or member_progress.get("carved_fragment_examined")
                ):
                    continue
                member_progress["carved_fragment_examined"] = True
                member.quest.progress = member_progress
                member.quest.step = 5
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P3_ID,
                    objective_id="p3.carved_fragment",
                    source_key="p3.carved_fragment:bosque",
                    evidence={"location": BOSQUE},
                )
            return await self._view(session, character, quest, world)

    async def talk_to_oren(self, actor: int, version: int) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=5)
                or not self._at(world, REFUGE)
                or not (quest.progress or {}).get("carved_fragment_examined")
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            roster_ids = await campaign_roster_ids(session, character.id)
            present = await present_campaign_members(
                session,
                character_ids=roster_ids,
                quest_id=P3_ID,
                content_version=P3_VERSION,
                step=5,
                region=REGION,
                location=REFUGE,
            )
            for member in present:
                if not (member.quest.progress or {}).get("carved_fragment_examined"):
                    continue
                member.quest.step = 6
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P3_ID,
                    objective_id="p3.return_to_oren",
                    source_key=f"p3.return_to_oren:{member.quest.state_version - 1}",
                    evidence={"location": REFUGE},
                )
            return await self._view(session, character, quest, world)

    async def choose_reward(self, actor: int, version: int, choice: str) -> P3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if quest.status == "completed":
                return await self._view(session, character, quest, world)
            if (
                not self._valid(quest, version, step=6)
                or not self._at(world, REFUGE)
                or choice not in P3_REWARD_CHOICES
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            source = P3_REWARD_SOURCE
            event = await session.scalar(
                select(RewardEvent)
                .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source)
                .with_for_update()
            )
            if event is None:
                name, slot = P3_REWARD_CHOICES[choice]
                seed = f"{P3_REWARD_SOURCE}:{character.id}:{choice}"
                payload = materialize_equipment(
                    seed,
                    "Raro",
                    5,
                    forced_name=name,
                    forced_slot=slot,
                    bound=True,
                )
                event = RewardEvent(character_id=character.id, source_id=source)
                session.add(event)
                await session.flush()
                character.xp += 4400
                character.crowns += 180
                session.add_all(
                    (
                        RewardComponent(
                            reward_event_id=event.id, kind="xp", item_id=None, quantity=4400
                        ),
                        RewardComponent(
                            reward_event_id=event.id, kind="crowns", item_id=None, quantity=180
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="equipment",
                            item_id=None,
                            quantity=1,
                            payload=payload,
                        ),
                    )
                )
                source_key = f"{source}:equipment:{choice}"
                if await self.road._inventory_slots(session, character.id) < 60:
                    from asterion.application.equipment import equipment_instance_payload

                    item_id, payload = equipment_instance_payload(payload)
                    session.add(
                        EquipmentItem(
                            id=item_id,
                            character_id=character.id,
                            source_key=source_key,
                            item_name=payload["item_name"],
                            rarity=payload["rarity"],
                            slot=payload["slot"],
                            item_level=payload["item_level"],
                            bound=True,
                            payload=payload,
                        )
                    )
                else:
                    await self.road._pending(
                        session, character.id, source_key, "equipment", payload
                    )
            await self._ensure(
                session, CodexEntry, character_id=character.id, entry_id=P3_CODEX_OLD_ASTERIANS
            )
            await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id=P3_CODEX_OLD_ASTERIANS,
                fragment_id=P3_CODEX_FRAGMENT,
            )
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id="codex.mystery.marcas_na_fuligem",
            )
            await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id="codex.mystery.marcas_na_fuligem",
                fragment_id=P3_MARKS_FRAGMENT,
            )
            await self._ensure(
                session, LocationDiscovery, character_id=character.id, location_id=P3_LOCATION_ID
            )
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id=P3_ROUTE_UNLOCK
            )
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id="hunt_manual.bosque_calcinado"
            )
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id="explore.bosque_calcinado"
            )
            await self._normalize_character_hp(session, character)
            progress = dict(quest.progress or {})
            progress.update(completed=True, selected_reward=choice)
            quest.progress = progress
            quest.status = "completed"
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _materialize_combat(self, session, character, quest):
        if not self._at(await self._world(session, character.id), BOSQUE):
            return None
        foreground = await self._foreground(session, character.id)
        if foreground is not None:
            progress = quest.progress or {}
            if foreground.content_id == P3_COMBAT_CONTENT_ID and str(foreground.id) == progress.get(
                "combat_activity_id"
            ):
                return foreground
            return None
        configuration = await load_equipment_configuration(session, character)
        active_art_configuration = await load_active_art_configuration(session, character)
        reconcile_character_hp(character, configuration)
        mission_cervo = replace(CERVO, ai=("ocaso_charge", "antler_gore"))
        combat = create_creature_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            character.hp,
            mission_cervo,
            5,
            None,
            player_level=character.level,
            equipment_configuration=configuration,
            ruleset_version=RULESET,
            flavor="Entre as raízes, um Cervo Escoriado prepara uma investida.",
            opening_log="🦌 Cervo Escoriado · Nv.5 bloqueia o caminho entre os galhos.",
            active_art_ids=active_art_configuration.art_ids,
        )
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | (
            active_art_configuration.to_data()
        )
        activity, _, _ = await CombatRepository(session).create(
            character, P3_COMBAT_CONTENT_ID, combat
        )
        progress = dict(quest.progress or {})
        progress.update(
            combat_activity_id=str(activity.id), combat_result=None, awaiting_retry=False
        )
        quest.progress = progress
        await session.flush()
        return activity

    async def _p3_combat_eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == P3_ID)
        )
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        progress = dict(quest.progress or {}) if quest else {}
        if (
            active is not None
            or not self._at(world, BOSQUE)
            or payload.get("location") != BOSQUE
            or quest is None
            or quest.content_version != P3_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and len(progress.get("fragments", ())) == len(P3_FRAGMENTS)
            and not progress.get("awaiting_retry")
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
            "fragments": sorted(progress.get("fragments", ())),
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

    async def _create_p3_group_combat(
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
                    checkpoint="p3.cervo_escoriado",
                )
            )
        lead = characters[0]
        mission_cervo = replace(CERVO, ai=("ocaso_charge", "antler_gore"))
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(mission_cervo, 5, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor="Entre as raízes, um Cervo Escoriado prepara uma investida.",
            opening_log="🦌 Cervo Escoriado · Nv.5 bloqueia o caminho entre os galhos.",
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
            quest_id=P3_ID,
            content_id=P3_COMBAT_CONTENT_ID,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint="p3.cervo_escoriado",
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
                .where(Quest.character_id == member.character_id, Quest.quest_id == P3_ID)
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
                CERVO.creature_id,
                evidence_id=f"habitat:{P3_LOCATION_ID}",
                evidence_category="habitat",
                evidence_points=3,
                grant_observation_xp=True,
                observation_level=5,
                observation_category="common",
            )
        await session.flush()
        return str(encounter.id)

    async def _grant_enemy_xp(self, session, character, activity) -> int:
        source_id = f"{P3_REWARD_SOURCE}:enemy-xp:{activity.id}"
        existing = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source_id)
            .with_for_update()
        )
        if existing is not None:
            return 0
        amount = enemy_xp(
            5,
            "common",
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
                item_id=CERVO.creature_id,
                quantity=amount,
                payload={"enemy_level": 5, "category": "common", "observation_context": "P3"},
            )
        )
        character.xp += amount
        return amount

    async def _normalize_character_hp(self, session, character):
        configuration = await load_equipment_configuration(session, character)
        reconcile_character_hp(character, configuration)
        await consolidate_character_level(session, character, configuration)
        reconcile_character_hp(character, configuration)

    async def _view(self, session, character, quest, world, requested_kind=None):
        progress = dict(quest.progress or {}) if quest else {}
        group_size = await self._social_group_size(session, character.id)
        activity = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == P3_COMBAT_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        encounter_id = combat_id = None
        combat = None
        activity_status = activity_version = None
        combat_actor_key = "player"
        stored = progress.get("combat_activity_id")
        try:
            stored_id = UUID(stored) if stored else None
        except (TypeError, ValueError):
            stored_id = None
        if activity is None and stored_id is not None:
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == stored_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P3_COMBAT_CONTENT_ID,
                )
            )
        if activity is not None:
            activity_status = activity.status
            activity_version = activity.state_version
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity.id, character.id
            )
            if shared is not None and shared_member is not None:
                encounter_id = combat_id = shared.id
                combat_actor_key = shared_member.actor_key
                combat = shared_combat if activity.status == "active" else None
                group_size = shared.roster_size
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
                    encounter_id, combat_id = encounter.id, record.id
                    if activity.status == "active":
                        combat = decode(
                            record.snapshot,
                            record.id,
                            activity.ruleset_version,
                            activity.state_version,
                        )
        status = quest.status if quest else "unaccepted"
        step = quest.step if quest else 1
        state_version = quest.state_version if quest else 0
        available = quest is None and await self._eligible(session, character)
        if requested_kind is not None:
            kind = requested_kind
        elif quest is None:
            kind = "offer" if available else "unavailable"
        elif combat is not None:
            kind = "combat"
        elif quest.status == "completed":
            kind = "completed"
        elif step == 1:
            kind = "travel"
        elif step == 2:
            kind = "fragments"
        elif step == 3 and progress.get("awaiting_retry"):
            kind = "recovery"
        elif step == 3:
            kind = "combat_pending"
        elif step == 4:
            kind = "carved"
        elif step == 5:
            kind = "return"
        else:
            kind = "choice"
        options: tuple[CombatConsumableOption, ...] = ()
        quantities: tuple[tuple[str, int], ...] = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            budget = ENCOUNTER_CONSUMABLE_LIMITS.get(CERVO.category, 0)
            stock = (
                await session.scalars(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character.id, ConsumableStack.quantity > 0
                    )
                    .order_by(ConsumableStack.consumable_id)
                )
            ).all()
            quantities = tuple((row.consumable_id, row.quantity) for row in stock)
            options = combat_consumable_options(
                combat,
                tuple(row.consumable_id for row in stock),
                budget_limit=budget,
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
                    GroupActivityProposal.activity_type == "campaign_p3",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .order_by(GroupActivityProposal.created_at.desc(), GroupActivityProposal.id)
                .limit(1)
            )
            proposal_pair = proposal_rows.first()
        return P3View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=step,
            state_version=state_version,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=available,
            combat=combat,
            activity_id=activity.id if activity else None,
            activity_state_version=activity_version,
            activity_status=activity_status,
            encounter_id=encounter_id,
            combat_id=combat_id,
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
        completed = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == P2_QUEST_ID,
                Quest.status == "completed",
            )
        )
        return bool(completed and character.level >= 5)

    async def _destination_allowed(self, session, character, quest, world, destination):
        if quest is None or world is None or world.region != REGION:
            return False
        progress = dict(quest.progress or {})
        if quest.step == 1 and world.location == REFUGE and destination == CHARNECA:
            return await self._has_unlock(session, character.id, CHARNECA_ROUTE_UNLOCK)
        if quest.step == 3 and progress.get("awaiting_retry"):
            if world.location == REFUGE and destination == CHARNECA:
                return await self._has_unlock(session, character.id, CHARNECA_ROUTE_UNLOCK)
            if {world.location, destination} == {CHARNECA, BOSQUE}:
                return await self._has_unlock(session, character.id, P3_ROUTE_UNLOCK)
        if quest.step == 5:
            if {world.location, destination} == {BOSQUE, CHARNECA}:
                return await self._has_unlock(session, character.id, P3_ROUTE_UNLOCK)
            if {world.location, destination} == {CHARNECA, REFUGE}:
                return await self._has_unlock(session, character.id, CHARNECA_ROUTE_UNLOCK)
        return False

    async def _social_group_size(self, session, character_id: UUID) -> int:
        membership = await session.get(SocialGroupMember, character_id)
        if membership is None:
            return 1
        group = await session.get(SocialGroup, membership.group_id)
        if group is None or group.status != "active":
            return 1
        return int(
            await session.scalar(
                select(func.count())
                .select_from(SocialGroupMember)
                .where(SocialGroupMember.group_id == group.id)
            )
            or 1
        )

    async def _locked_state(self, session, actor):
        seed = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
        )
        if seed is None:
            return None, None, None
        await lock_campaign_roster(session, seed.id)
        character = await session.scalar(
            select(Character).where(Character.id == seed.id).with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(
            select(Quest)
            .where(Quest.character_id == character.id, Quest.quest_id == P3_ID)
            .with_for_update()
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id).with_for_update()
        )
        return character, quest, world

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _quest(self, session, character_id):
        return await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P3_ID)
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id, GameActivity.status == "active"
            )
        )

    async def _has_unlock(self, session, character_id, unlock_id):
        return bool(
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id, Unlock.unlock_id == unlock_id
                )
            )
        )

    async def _ensure(self, session, model, **values):
        row = await session.scalar(select(model).filter_by(**values).with_for_update())
        if row is not None:
            return row
        row = model(**values)
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest is not None
            and quest.status == "active"
            and quest.content_version == P3_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world is not None and world.region == REGION and world.location == location)
