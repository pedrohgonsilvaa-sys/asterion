"""S3-specific quest flow built on the shared combat, bestiary, and delivery systems."""
# ruff: noqa: E501

import hashlib
import json
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BestiaryRecorder
from asterion.application.campaign_coop import (
    CampaignRosterMember,
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
from asterion.application.road import BOSQUE, P3_QUEST_ID, REFUGE, REGION, RoadService
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    derive_consumable_selection,
    materialize,
    normalize_character_hp,
)
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.road import (
    BOSQUE_LOCATION,
    CERVO,
    RULESET,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    enemy_xp,
)
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    CampaignSharedEncounterMember,
    Character,
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
    WorldState,
)

S3_ID = "S3"
S3_TITLE = "Rastros sob os Galhos"
S3_VERSION = "tdo-1.0.11"
S3_CONTENT_ID = "s3_scripted_cervo_escoriado"
S3_REWARD_SOURCE = "s3.rastros_sob_os_galhos"
S3_TRACKS = ("s3.track.1", "s3.track.2", "s3.track.3")
S3_MATERIAL = "material.tdo.couro_escoriado"


@dataclass(frozen=True)
class S3View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    reacceptable: bool = False
    context: str = "s3"
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
    campaign_active: bool = False
    tracked: bool = False
    proposal_id: UUID | None = None
    proposal_status: str | None = None
    group_size: int = 1
    combat_actor_key: str = "player"


class S3Service:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        *,
        groups: GroupService | None = None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)
        self.groups = groups

    async def alda(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "alda")

    async def offer(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            available = (
                (quest is None or quest.status == "abandoned")
                and self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and await self._eligible(session, character)
            )
            return await self._view(
                session,
                character,
                quest,
                world,
                "offer" if available else "unavailable",
                available=available,
            )

    async def resume(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            return await self._view(
                session, character, quest, await self._world(session, character.id)
            )

    async def detail(self, actor: int) -> S3View | None:
        view = await self.resume(actor)
        if view is None or view.status != "active" or view.kind == "combat":
            return view
        return replace(view, kind="detail")

    async def accept(self, actor: int, version: int = 0, *, reaccept: bool = False) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                not self._at(world, REFUGE)
                or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            if reaccept:
                if quest is None or quest.status != "abandoned" or quest.state_version != version:
                    return await self._view(session, character, quest, world)
                quest.status = "active"
                quest.step = 1
                quest.progress = {"tracks": []}
                quest.content_version = S3_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world)
                quest = Quest(
                    character_id=character.id,
                    quest_id=S3_ID,
                    title=S3_TITLE,
                    status="active",
                    step=1,
                    content_version=S3_VERSION,
                    state_version=0,
                    progress={"tracks": []},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world)

    async def interact(self, actor: int, version: int, action: str, item: str | None = None) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_coop_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            if action == "route" and quest.step == 1 and self._at(world, BOSQUE):
                for member in await self._present_objective_members(
                    session, character.id, step=1
                ):
                    progress = dict(member.quest.progress or {})
                    if progress.get("supply_route_examined"):
                        continue
                    progress["supply_route_examined"] = True
                    progress["tracks"] = []
                    member.quest.progress = progress
                    member.quest.step = 2
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=S3_ID,
                        objective_id="s3.supply_route",
                        source_key="s3.supply_route:examined",
                        evidence={"location": BOSQUE},
                    )
                return await self._view(session, character, quest, world)
            elif action == "track" and quest.step == 2 and self._at(world, BOSQUE):
                if item not in S3_TRACKS:
                    return await self._view(session, character, quest, world)
                for member in await self._present_objective_members(
                    session, character.id, step=2
                ):
                    progress = dict(member.quest.progress or {})
                    tracks = set(progress.get("tracks", ()))
                    if item in tracks:
                        continue
                    tracks.add(item)
                    progress["tracks"] = [track for track in S3_TRACKS if track in tracks]
                    member.quest.progress = progress
                    if len(tracks) == len(S3_TRACKS):
                        member.quest.step = 3
                        progress.update(
                            awaiting_retry=False,
                            combat_result=None,
                            combat_pending=True,
                        )
                        member.quest.progress = progress
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=S3_ID,
                        objective_id="s3.track",
                        source_key=f"s3.track:{item}",
                        evidence={"track_id": item, "location": BOSQUE},
                    )
                if quest.step == 3 and await self._group_size(session, character.id) == 1:
                    await self._materialize(session, character, quest)
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            if action == "cargo" and quest.step == 4 and self._at(world, BOSQUE):
                progress["cargo_checked"] = True
                quest.step = 5
            elif action == "report" and quest.step == 5 and self._at(world, REFUGE):
                await self._complete(session, character, quest)
                return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def start_solo_combat(self, actor: int, version: int) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or len(progress.get("tracks", ())) != len(S3_TRACKS)
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
            progress.update(awaiting_retry=False, combat_pending=False)
            quest.progress = progress
            if await self._materialize(session, character, quest) is None:
                quest.progress = {**progress, "combat_pending": True}
                return await self._view(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int) -> S3View | None:
        if self.groups is None:
            return await self.start_solo_combat(actor, version)
        initial = await self.resume(actor)
        if (
            initial is None
            or initial.status != "active"
            or initial.step != 3
            or initial.state_version != version
            or initial.location != BOSQUE
            or len(initial.progress.get("tracks", ())) != len(S3_TRACKS)
        ):
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_s3",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._s3_combat_eligibility,
            context_payload={
                "quest_id": S3_ID,
                "checkpoint": "s3.cervo_escoriado",
                "title": f"{S3_TITLE} · Cervo Escoriado",
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
        self, actor: int, proposal_id: UUID, *, expected_revision: int
    ) -> S3View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._s3_combat_eligibility,
            create_activity=self._create_s3_group_combat,
        )
        return await self.resume(actor)

    async def _s3_combat_eligibility(self, session, character, payload):
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == S3_ID)
        )
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        progress = dict(quest.progress or {}) if quest else {}
        if (
            active is not None
            or not self._at(world, BOSQUE)
            or payload.get("location") != BOSQUE
            or quest is None
            or quest.content_version != S3_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and len(progress.get("tracks", ())) == len(S3_TRACKS)
        ):
            role = "eligible"
        elif quest.status == "completed":
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
            "location": world.location if world else None,
            "active_activity": str(active.id) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
            "level": character.level,
            "mission_reward_eligible": role == "eligible",
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_s3_group_combat(self, session, proposal, characters):
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
        creature = replace(CERVO, ai=("ocaso_charge", "antler_gore"))
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
                    checkpoint="s3.cervo_escoriado",
                )
            )
        lead = characters[0]
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(creature, 5, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor="Rastros recentes terminam diante de um Cervo Escoriado.",
            opening_log="🦌 Cervo Escoriado · Nv.5 surge entre os galhos.",
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
            quest_id=S3_ID,
            content_id=S3_CONTENT_ID,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint="s3.cervo_escoriado",
        )
        members = list(
            (
                await session.scalars(
                    select(CampaignSharedEncounterMember).where(
                        CampaignSharedEncounterMember.shared_encounter_id == encounter.id
                    )
                )
            ).all()
        )
        for member in members:
            if member.role == "eligible":
                quest = await session.scalar(
                    select(Quest).where(
                        Quest.character_id == member.character_id, Quest.quest_id == S3_ID
                    ).with_for_update()
                )
                if quest is not None:
                    quest.progress = {
                        **(quest.progress or {}),
                        "combat_activity_id": str(member.game_activity_id),
                    }
        await session.flush()
        return str(encounter.id)

    async def retry(self, actor: int, version: int) -> S3View | None:
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
            progress["awaiting_retry"] = False
            quest.progress = progress
            if await self._materialize(session, character, quest) is None:
                progress["awaiting_retry"] = True
                quest.progress = progress
                return await self._view(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def abandon(self, actor: int, version: int) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            quest.status = "abandoned"
            quest.step = 1
            quest.progress = {}
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S3_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world)

    async def abandon_confirmation(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active" or world is None:
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def toggle_tracking(self, actor: int, version: int) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S3_ID else S3_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world)

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
    ) -> S3View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _shared, shared_member, _combat = await campaign_combat_for_activity(
                session, activity_id, seed.id
            )
            if shared_member is not None:
                locked = await lock_campaign_encounter(session, activity_id, seed.id)
                if locked is None or locked.encounter.content_id != S3_CONTENT_ID:
                    return None
                return await self._shared_action(
                    session,
                    locked,
                    activity_id,
                    version,
                    action,
                    consumable_id=consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                )
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S3_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                not self._valid(quest, quest.state_version, step=3)
                or activity.status != "active"
                or activity.state_version != version
                or foreground is None
                or foreground.id != activity.id
                or (action is None) == (consumable_id is None)
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
                category=CERVO.category,
            )
            if updated is None:
                return current
            await self.bestiary.record_combat_events(
                session, character.id, CERVO.creature_id, None, updated
            )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session, character.id, CERVO.creature_id, victory=True,
                    observation_category="common",
                )
                progress.update(combat_result="victory", awaiting_retry=False)
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session, character.id, CERVO.creature_id, observation_category="common"
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, BOSQUE_LOCATION, world
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
        locked,
        activity_id,
        version,
        action,
        *,
        consumable_id,
        target_id,
        effect_id,
    ):
        encounter = locked.encounter
        member = next(
            (row for row in locked.members if row.game_activity_id == activity_id), None
        )
        activity = locked.activities.get(activity_id)
        character = next(
            (
                locked.characters[row.character_id]
                for row in locked.members
                if row.game_activity_id == activity_id
            ),
            None,
        )
        if character is None:
            return None
        quest = await self._quest_for_update(session, character.id)
        world = await session.scalar(
            select(WorldState)
            .where(WorldState.character_id == character.id)
            .with_for_update()
        )
        current = await self._view(session, character, quest, world)
        if (
            member is None
            or activity is None
            or activity.status != "active"
            or activity.state_version != version
            or encounter.state_version != version
            or (action is None) == (consumable_id is None)
        ):
            return current

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
                    current,
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
            return current
        if stack is not None:
            stack.quantity -= 1

        quests = list(
            (
                await session.scalars(
                    select(Quest)
                    .where(
                        Quest.character_id.in_(locked.characters), Quest.quest_id == S3_ID
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
        members_by_character = {row.character_id: row for row in locked.members}
        for character_id, participant in locked.characters.items():
            roster_member = members_by_character[character_id]
            participant_quest = quests_by_character.get(character_id)
            await self.bestiary.record_combat_events(
                session, character_id, CERVO.creature_id, None, updated
            )
            if updated.result:
                await record_campaign_objective_credit(
                    session,
                    character_id=character_id,
                    quest_id=S3_ID,
                    objective_id="s3.cervo_escoriado",
                    source_key=f"s3.cervo_escoriado:{encounter.id}",
                    evidence={"result": updated.result, "encounter_id": str(encounter.id)},
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
                        session, participant, locked.activities[roster_member.game_activity_id]
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
                    CERVO.creature_id,
                    observation_category="common",
                )
                participant_world = worlds_by_character.get(character_id)
                brazier, location = await self.road.recover_normal_pve_defeat(
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
                        recovery_brazier=brazier,
                        recovery_location=location,
                    )
                    participant_quest.progress = progress
                    participant_quest.state_version += 1
        if updated.result:
            await settle_campaign_encounter(session, locked, updated.result)
        return await self._view(session, character, quest, world)

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, *,
        screen: str = "items", item_id: str | None = None,
        target_id: str | None = None, parent: str = "items",
    ) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S3_CONTENT_ID,
                ).with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                quest.status != "active" or quest.step != 3 or activity.status != "active"
                or foreground is None or foreground.id != activity.id
            ):
                return current
            if activity.state_version != version:
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    async def _materialize(self, session, character, quest):
        world = await self._world(session, character.id)
        if not self._at(world, BOSQUE) or await self._foreground(session, character.id):
            return None
        from dataclasses import replace

        creature = replace(CERVO, ai=("ocaso_charge", "antler_gore"))
        activity = await materialize(
            session, character, S3_CONTENT_ID, creature, 5,
            flavor="Rastros recentes terminam diante de um Cervo Escoriado.",
            opening_log="🦌 Cervo Escoriado · Nv.5 surge entre os galhos.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{S3_REWARD_SOURCE}:enemy-xp:{activity.id}"
        if await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id, RewardEvent.source_id == source
            ).with_for_update()
        ):
            return
        amount = enemy_xp(5, "common", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id, kind="enemy_xp", item_id=CERVO.creature_id,
                quantity=amount, payload={"enemy_level": 5, "category": "common"},
            )
        )
        character.xp += amount

    async def _complete(self, session, character, quest):
        source = S3_REWARD_SOURCE
        event = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source)
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=source)
            session.add(event)
            await session.flush()
            character.xp += 1760
            character.crowns += 90
            session.add_all(
                [
                    RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=1760),
                    RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=90),
                    RewardComponent(reward_event_id=event.id, kind="material", item_id=S3_MATERIAL, quantity=2,
                                    payload={"material_id": S3_MATERIAL, "bound": True}),
                ]
            )
            await self.road.deliver_material(
                session, character, S3_MATERIAL, 2, f"{S3_REWARD_SOURCE}:material:{S3_MATERIAL}", bound=True
            )
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        if character.tracked_secondary_quest_id == S3_ID:
            character.tracked_secondary_quest_id = None
        await consolidate_character_level(session, character)

    async def _view(self, session, character, quest, world, requested_kind=None, *, available=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        activity = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == S3_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        if activity is None:
            stored = progress.get("combat_activity_id")
            try:
                activity_id = UUID(stored)
            except (TypeError, ValueError):
                activity_id = None
            if activity_id:
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == S3_CONTENT_ID,
                    )
                )
        activity_state_version = None
        activity_status = None
        encounter_id = None
        combat_id = None
        combat_actor_key = "player"
        group_size = await self._group_size(session, character.id)
        if activity is not None:
            activity_state_version = activity.state_version
            activity_status = activity.status
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
                        select(Encounter, CombatRecord).join(CombatRecord)
                        .where(Encounter.game_activity_id == activity.id)
                    )
                ).one_or_none()
                if row:
                    encounter, record = row
                    encounter_id = encounter.id
                    combat_id = record.id
                    if activity.status == "active":
                        combat = decode(
                            record.snapshot,
                            record.id,
                            activity.ruleset_version,
                            activity.state_version,
                        )
        status = quest.status if quest else "unaccepted"
        available = (
            (quest is None or quest.status == "abandoned")
            and await self._eligible(session, character)
            if available is None else available
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
                    GroupActivityProposal.activity_type == "campaign_s3",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .order_by(GroupActivityProposal.created_at.desc(), GroupActivityProposal.id)
                .limit(1)
            )
            proposal_pair = proposal_rows.first()

        if requested_kind:
            kind = requested_kind
        elif quest is None or status == "abandoned":
            kind = "offer" if available else "unavailable"
        elif status == "completed":
            kind = "completed"
        elif combat is not None:
            kind = "combat"
        elif quest.step == 1:
            kind = "route"
        elif quest.step == 2:
            kind = "tracks"
        elif quest.step == 3:
            kind = "recovery" if progress.get("awaiting_retry") else "combat_pending"
        elif quest.step == 4:
            kind = "cargo"
        else:
            kind = "report"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(
                session,
                character,
                combat,
                CERVO.category,
                actor_key=combat_actor_key,
            )
        campaign_active = bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == P3_QUEST_ID,
                    Quest.status == "active",
                )
            )
        )
        return S3View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=bool(available and (quest is None or status == "abandoned")),
            reacceptable=bool(quest and status == "abandoned" and available),
            combat=combat,
            activity_id=activity.id if activity else None,
            activity_state_version=activity_state_version,
            activity_status=activity_status,
            encounter_id=encounter_id,
            combat_id=combat_id,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            xp=character.xp,
            campaign_active=campaign_active,
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S3_ID
            ),
            proposal_id=proposal_pair[1].id if proposal_pair else None,
            proposal_status=proposal_pair[1].status if proposal_pair else None,
            group_size=group_size,
            combat_actor_key=combat_actor_key,
        )

    async def _eligible(self, session, character):
        p3 = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P3_QUEST_ID,
                Quest.status.in_(("active", "completed")),
            )
        )
        known = await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id, LocationDiscovery.location_id == BOSQUE_LOCATION
            )
        )
        return bool(p3 and known and character.level >= 5)

    async def _locked_state(self, session, actor):
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor, Character.server_id == self.server_id).with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == S3_ID).with_for_update()
        )
        world = await session.scalar(select(WorldState).where(WorldState.character_id == character.id).with_for_update())
        return character, quest, world

    async def _locked_coop_state(self, session, actor):
        seed = await self._character(session, actor)
        if seed is None:
            return None, None, None
        await lock_campaign_roster(session, seed.id)
        return await self._locked_state(session, actor)

    async def _present_objective_members(self, session, character_id, *, step):
        roster_ids = await campaign_roster_ids(session, character_id)
        return await present_campaign_members(
            session,
            character_ids=roster_ids,
            quest_id=S3_ID,
            content_version=S3_VERSION,
            step=step,
            region=REGION,
            location=BOSQUE,
        )

    async def _group_size(self, session, character_id):
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
        return int(
            await session.scalar(
                select(func.count())
                .select_from(SocialGroupMember)
                .where(SocialGroupMember.group_id == group.id)
            )
            or 1
        )

    async def _quest_for_update(self, session, character_id):
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S3_ID)
            .with_for_update()
        )

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(Character.telegram_id == actor, Character.server_id == self.server_id))

    async def _quest(self, session, character_id):
        return await session.scalar(select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S3_ID))

    async def _world(self, session, character_id):
        return await session.scalar(select(WorldState).where(WorldState.character_id == character_id))

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity).where(GameActivity.character_id == character_id, GameActivity.status == "active"))

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(quest and quest.status == "active" and quest.content_version == S3_VERSION and quest.state_version == version and (step is None or quest.step == step))

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
