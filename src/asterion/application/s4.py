"""S4 mission flow, composed from persistent quests and scripted combat."""
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
from asterion.application.road import REFUGE, REGION, RUINS, RoadService
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
    CombatRecord,
    ConsumableStack,
    Encounter,
    GameActivity,
    GroupActivityParticipant,
    GroupActivityProposal,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    WorldState,
)

S4_ID = "S4"
S4_TITLE = "Vigília sem Voz"
S4_VERSION = "tdo-1.0.11"
S4_CONTENT_ID = "s4_scripted_vigia_rachado"
S4_REWARD_SOURCE = "s4.vigilia_sem_voz"
S4_WATCH_POINTS = ("s4.watch_point.1", "s4.watch_point.2", "s4.watch_point.3")
S4_MATERIALS = (
    ("material.tdo.ferro_de_fuligem", 2),
    ("material.tdo.couro_escoriado", 1),
    ("material.tdo.residuo_ocaso", 1),
)


@dataclass(frozen=True)
class S4View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    eligible: bool = False
    reacceptable: bool = False
    context: str = "s4"
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
    tracked: bool = False
    proposal_id: UUID | None = None
    proposal_status: str | None = None
    group_size: int = 1
    combat_actor_key: str = "player"


class S4Service:
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

    async def oren(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, await self._quest(session, character.id), world)

    async def offer(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            eligible = await self._eligible(session, character)
            available = bool(
                eligible and self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and (quest is None or quest.status == "abandoned")
            )
            return await self._view(
                session, character, quest, world,
                "offer" if available else "unavailable", available=available,
            )

    async def summary(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view(
                session, character, await self._quest(session, character.id),
                await self._world(session, character.id),
            )

    async def resume(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            return await self._view(session, character, quest, await self._world(session, character.id))

    async def detail(self, actor: int) -> S4View | None:
        view = await self.resume(actor)
        if (
            view is None
            or view.status != "active"
            or view.kind == "combat"
            or view.proposal_id is not None
        ):
            return view
        from dataclasses import replace

        return replace(view, kind="detail")

    async def accept(self, actor: int, version: int = 0, *, reaccept: bool = False) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                not self._at(world, REFUGE) or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            if reaccept:
                if quest is None or quest.status != "abandoned" or quest.state_version != version:
                    return await self._view(session, character, quest, world)
                quest.status = "active"
                quest.step = 1
                quest.content_version = S4_VERSION
                quest.progress = {"watch_points": []}
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world)
                quest = Quest(
                    character_id=character.id, quest_id=S4_ID, title=S4_TITLE,
                    status="active", step=1, content_version=S4_VERSION,
                    state_version=0, progress={"watch_points": []},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world)

    async def action(
        self, actor: int, version: int, operation: str, item: str | None = None,
    ) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_coop_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            if operation == "watch" and quest.step == 1 and self._at(world, RUINS):
                if item not in S4_WATCH_POINTS:
                    return await self._view(session, character, quest, world)
                for member in await self._present_objective_members(
                    session, character.id, step=1
                ):
                    progress = dict(member.quest.progress or {})
                    found = set(progress.get("watch_points", ()))
                    if item in found:
                        continue
                    found.add(item)
                    progress["watch_points"] = [
                        key for key in S4_WATCH_POINTS if key in found
                    ]
                    member.quest.progress = progress
                    if len(found) == len(S4_WATCH_POINTS):
                        member.quest.step = 2
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=S4_ID,
                        objective_id="s4.watch_point",
                        source_key=f"s4.watch_point:{item}",
                        evidence={"watch_point_id": item, "location": RUINS},
                    )
                return await self._view(session, character, quest, world)
            if operation == "orientation" and quest.step == 2 and self._at(world, RUINS):
                for member in await self._present_objective_members(
                    session, character.id, step=2
                ):
                    progress = dict(member.quest.progress or {})
                    if progress.get("patrol_orientation_recorded"):
                        continue
                    progress.update(
                        patrol_orientation_recorded=True,
                        combat_pending=True,
                        awaiting_retry=False,
                    )
                    member.quest.progress = progress
                    member.quest.step = 3
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=S4_ID,
                        objective_id="s4.patrol_orientation",
                        source_key="s4.patrol_orientation:recorded",
                        evidence={"location": RUINS},
                    )
                if quest.step == 3 and await self._group_size(session, character.id) == 1:
                    progress = dict(quest.progress or {})
                    progress["combat_pending"] = False
                    quest.progress = progress
                    await self._materialize(session, character, quest)
                return await self._view(session, character, quest, world)
            if operation == "turn_point" and quest.step == 4 and self._at(world, RUINS):
                for member in await self._present_objective_members(
                    session, character.id, step=4
                ):
                    progress = dict(member.quest.progress or {})
                    if progress.get("patrol_turn_point_found"):
                        continue
                    progress["patrol_turn_point_found"] = True
                    member.quest.progress = progress
                    member.quest.step = 5
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=S4_ID,
                        objective_id="s4.patrol_turn_point",
                        source_key="s4.patrol_turn_point:found",
                        evidence={"location": RUINS},
                    )
                return await self._view(session, character, quest, world)
            if operation == "examine" and quest.step == 5 and self._at(world, RUINS):
                for member in await self._present_objective_members(
                    session, character.id, step=5
                ):
                    progress = dict(member.quest.progress or {})
                    if progress.get("turn_point_examined"):
                        continue
                    progress["turn_point_examined"] = True
                    member.quest.progress = progress
                    member.quest.step = 6
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=S4_ID,
                        objective_id="s4.turn_point_examined",
                        source_key="s4.turn_point_examined:examined",
                        evidence={"location": RUINS},
                    )
                return await self._view(session, character, quest, world)
            if operation == "report" and quest.step == 6 and self._at(world, REFUGE):
                await self._complete(session, character, quest)
                return await self._view(session, character, quest, world)
            return await self._view(session, character, quest, world)

    async def start_solo_combat(self, actor: int, version: int) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or not progress.get("patrol_orientation_recorded")
                or not self._at(world, RUINS)
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
            else:
                quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int) -> S4View | None:
        if self.groups is None:
            return await self.start_solo_combat(actor, version)
        initial = await self.resume(actor)
        if (
            initial is None
            or initial.status != "active"
            or initial.step != 3
            or initial.state_version != version
            or initial.location != RUINS
        ):
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_s4",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._s4_combat_eligibility,
            context_payload={
                "quest_id": S4_ID,
                "checkpoint": "s4.vigia_rachado",
                "title": f"{S4_TITLE} · Vigia Rachado",
                "reference_character_id": str(initial.character_id),
                "location": RUINS,
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
    ) -> S4View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._s4_combat_eligibility,
            create_activity=self._create_s4_group_combat,
        )
        return await self.resume(actor)

    async def _s4_combat_eligibility(self, session, character, payload):
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == S4_ID)
        )
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        progress = dict(quest.progress or {}) if quest else {}
        if (
            active is not None
            or not self._at(world, RUINS)
            or payload.get("location") != RUINS
            or quest is None
            or quest.content_version != S4_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and progress.get("patrol_orientation_recorded")
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

    async def _create_s4_group_combat(self, session, proposal, characters):
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
                    checkpoint="s4.vigia_rachado",
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
            flavor="As marcas de patrulha terminam diante do Vigia Rachado.",
            opening_log="🛡️ Vigia Rachado · Nv.7 bloqueia a passagem.",
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
            quest_id=S4_ID,
            content_id=S4_CONTENT_ID,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint="s4.vigia_rachado",
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
                        Quest.character_id == member.character_id, Quest.quest_id == S4_ID
                    ).with_for_update()
                )
                if quest is not None:
                    quest.progress = {
                        **(quest.progress or {}),
                        "combat_activity_id": str(member.game_activity_id),
                    }
        await session.flush()
        return str(encounter.id)

    async def retry(self, actor: int, version: int) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3) or not progress.get("awaiting_retry")
                or not self._at(world, RUINS) or await self._foreground(session, character.id)
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
                progress.update(awaiting_retry=True, combat_pending=True)
                quest.progress = progress
                return await self._view(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def abandon_confirmation(self, actor: int) -> S4View | None:
        view = await self.resume(actor)
        if view is None or view.status != "active" or view.kind == "combat":
            return None
        if await self._has_foreground(actor):
            return None
        from dataclasses import replace

        return replace(view, kind="abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S4View | None:
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
            if character.tracked_secondary_quest_id == S4_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world)

    async def toggle_tracking(self, actor: int, version: int) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S4_ID else S4_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def action_combat(
        self, actor: int, activity_id: UUID, version: int, action: str | None = None, *,
        consumable_id: str | None = None, target_id: str | None = None, effect_id: str | None = None,
    ) -> S4View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _shared, shared_member, _combat = await campaign_combat_for_activity(
                session, activity_id, seed.id
            )
            if shared_member is not None:
                locked = await lock_campaign_encounter(session, activity_id, seed.id)
                if locked is None or locked.encounter.content_id != S4_CONTENT_ID:
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
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == activity_id, GameActivity.character_id == character.id,
                GameActivity.content_id == S4_CONTENT_ID,
            ).with_for_update())
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                not self._valid(quest, quest.state_version, step=3) or activity.status != "active"
                or activity.state_version != version or foreground is None or foreground.id != activity.id
                or (action is None) == (consumable_id is None)
            ):
                return current
            updated = await apply_action(
                session, character, activity, action=action, consumable_id=consumable_id,
                target_id=target_id, effect_id=effect_id, category=VIGIA.category,
            )
            if updated is None or updated.version == version:
                return current
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
            consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(VIGIA.category, 0),
        )
        if updated.version == version:
            return current
        if stack is not None:
            stack.quantity -= 1
        quests = list(
            (
                await session.scalars(
                    select(Quest)
                    .where(Quest.character_id.in_(locked.characters), Quest.quest_id == S4_ID)
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
                session, character_id, VIGIA.creature_id, None, updated
            )
            if updated.result:
                await record_campaign_objective_credit(
                    session,
                    character_id=character_id,
                    quest_id=S4_ID,
                    objective_id="s4.vigia_rachado",
                    source_key=f"s4.vigia_rachado:{encounter.id}",
                    evidence={"result": updated.result, "encounter_id": str(encounter.id)},
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

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, *, screen: str = "items",
        item_id: str | None = None, target_id: str | None = None, parent: str = "items",
    ) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == activity_id, GameActivity.character_id == character.id,
                GameActivity.content_id == S4_CONTENT_ID,
            ).with_for_update())
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
                from dataclasses import replace

                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    async def _materialize(self, session, character, quest):
        world = await self._world(session, character.id)
        if not self._at(world, RUINS) or await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session, character, S4_CONTENT_ID, VIGIA, 7,
            flavor="As marcas parecem ter conduzido o Vigia Rachado a este ponto.",
            opening_log="🛡️ Vigia Rachado · Nv.7 surge entre os antigos pontos de vigia.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{S4_REWARD_SOURCE}:enemy-xp:{activity.id}"
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
        event = await session.scalar(select(RewardEvent).where(
            RewardEvent.character_id == character.id,
            RewardEvent.source_id == S4_REWARD_SOURCE,
        ).with_for_update())
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S4_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 3990
            character.crowns += 150
            components = [
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=3990),
                RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=150),
                *[
                    RewardComponent(
                        reward_event_id=event.id, kind="material", item_id=material_id,
                        quantity=quantity, payload={"material_id": material_id, "bound": True},
                    )
                    for material_id, quantity in S4_MATERIALS
                ],
            ]
            session.add_all(components)
            for material_id, quantity in S4_MATERIALS:
                await self.road.deliver_material(
                    session, character, material_id, quantity,
                    f"{S4_REWARD_SOURCE}:material:{material_id}", bound=True,
                )
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        if character.tracked_secondary_quest_id == S4_ID:
            character.tracked_secondary_quest_id = None
        await consolidate_character_level(session, character)

    async def _view(self, session, character, quest, world, requested_kind=None, *, available=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        activity = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == S4_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        if activity is None:
            stored = progress.get("combat_activity_id")
            try:
                stored_id = UUID(stored) if stored else None
            except (TypeError, ValueError):
                stored_id = None
            if stored_id is not None:
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == stored_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == S4_CONTENT_ID,
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
        eligible = await self._eligible(session, character)
        can_offer = bool(eligible and (quest is None or status == "abandoned"))
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
                    GroupActivityProposal.activity_type == "campaign_s4",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .order_by(GroupActivityProposal.created_at.desc(), GroupActivityProposal.id)
                .limit(1)
            )
            proposal_pair = proposal_rows.first()
        if requested_kind:
            kind = requested_kind
        elif quest is None or status == "abandoned":
            kind = "offer" if can_offer and self._at(world, REFUGE) else "unavailable"
        elif status == "completed":
            kind = "completed"
        elif combat is not None:
            kind = "combat"
        elif quest.step == 3:
            kind = "recovery" if progress.get("awaiting_retry") else "combat_pending"
        elif quest.step == 6:
            kind = "report" if self._at(world, REFUGE) else "return"
        elif not self._at(world, RUINS):
            kind = "travel"
        elif quest.step == 1:
            kind = "watch_points"
        elif quest.step == 2:
            kind = "orientation"
        elif quest.step == 4:
            kind = "turn_point"
        else:
            kind = "examine"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(
                session, character, combat, VIGIA.category, actor_key=combat_actor_key
            )
        return S4View(
            character_id=character.id, kind=kind, status=status, step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0, progress=progress,
            location=world.location if world else "", level=character.level,
            available=bool(available if available is not None else can_offer), eligible=eligible,
            reacceptable=bool(quest and status == "abandoned" and eligible), combat=combat,
            activity_id=activity.id if activity else None,
            activity_state_version=activity_state_version,
            activity_status=activity_status,
            encounter_id=encounter_id,
            combat_id=combat_id,
            consumable_options=options, consumable_quantities=quantities,
            consumable_budget_limit=budget, xp=character.xp,
            tracked=bool(quest and status == "active" and character.tracked_secondary_quest_id == S4_ID),
            proposal_id=proposal_pair[1].id if proposal_pair else None,
            proposal_status=proposal_pair[1].status if proposal_pair else None,
            group_size=group_size,
            combat_actor_key=combat_actor_key,
        )

    async def _eligible(self, session, character):
        return bool(character.level >= 7 and await session.scalar(select(Quest.id).where(
            Quest.character_id == character.id, Quest.quest_id == "P4", Quest.status == "completed",
        )))

    async def _locked_state(self, session, actor):
        character = await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ).with_for_update())
        if character is None:
            return None, None, None
        quest = await session.scalar(select(Quest).where(
            Quest.character_id == character.id, Quest.quest_id == S4_ID
        ).with_for_update())
        world = await session.scalar(select(WorldState).where(
            WorldState.character_id == character.id
        ).with_for_update())
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
            quest_id=S4_ID,
            content_version=S4_VERSION,
            step=step,
            region=REGION,
            location=RUINS,
        )

    async def _group_size(self, session, character_id):
        """This encounter is not a Boss: missions stay Solo (Ação × Consequência §5)."""
        return 1
    async def _quest_for_update(self, session, character_id):
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S4_ID)
            .with_for_update()
        )

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ))

    async def _quest(self, session, character_id):
        return await session.scalar(select(Quest).where(
            Quest.character_id == character_id, Quest.quest_id == S4_ID
        ))

    async def _world(self, session, character_id):
        return await session.scalar(select(WorldState).where(WorldState.character_id == character_id))

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity).where(
            GameActivity.character_id == character_id, GameActivity.status == "active"
        ))

    async def _has_foreground(self, actor):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return bool(character and await self._foreground(session, character.id))

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest and quest.status == "active" and quest.content_version == S4_VERSION
            and quest.state_version == version and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
