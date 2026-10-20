"""Authoritative application flow for S2: Os Nomes Esquecidos."""

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
from asterion.application.road import CHARNECA_LOCATION, REFUGE, REGION, RoadService
from asterion.domain.combat import (
    Combat,
    CombatConsumableOption,
    act,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS, ConsumableFamily
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.road import (
    RULESET,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_combat,
    create_creature_party_combat,
    creature_for,
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
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    SocialGroupMember,
    WorldState,
)

S2_ID = "S2"
S2_TITLE = "Os Nomes Esquecidos"
S2_VERSION = "tdo-1.0.9"
S2_COMBAT_CONTENT_ID = "s2_scripted_peregrino_calcinado"
S2_REWARD_SOURCE = "s2.os_nomes_esquecidos"
S2_CODEX_ENTRY = "codex.mystery.peregrinos_do_ocaso"
S2_VESTIGE_IDS = (
    "s2.vestige.1",
    "s2.vestige.2",
    "s2.vestige.3",
)
S2_MATERIAL_REWARDS = (
    ("material.tdo.erva_cinzenta", 1),
    ("material.tdo.residuo_ocaso", 1),
)
P2_ID = "P2"
CHARNECA = "Charneca da Fuligem"
PEREGRINO = creature_for("peregrino_calcinado")


@dataclass(frozen=True)
class S2View:
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
    context: str = "s2"
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
    stage: str = "s2"
    xp: int = 0
    proposal_id: UUID | None = None
    proposal_status: str | None = None
    group_size: int = 1
    combat_actor_key: str = "player"


class S2Service:
    """Quest-specific flow composed from the shared Quest, combat and reward systems."""

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

    async def oren(self, actor: int) -> S2View | None:
        """Rebuild Oren's local mission options without creating a Quest."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "oren")

    async def offer(self, actor: int) -> S2View | None:
        """Return the offer or current authoritative state; no Quest is created."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is not None:
                if (
                    quest.status == "abandoned"
                    and self._at(world, REFUGE)
                    and not await self._foreground(session, character.id)
                ):
                    available = await self._eligible(session, character)
                    return await self._view(
                        session,
                        character,
                        quest,
                        world,
                        "offer" if available else "unavailable",
                    )
                return await self._view(session, character, quest, world)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world, "unavailable")
            available = await self._eligible(session, character)
            return await self._view(
                session,
                character,
                quest,
                world,
                "offer" if available else "unavailable",
            )

    async def resume(self, actor: int) -> S2View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def accept(
        self, actor: int, version: int = 0, *, reaccept: bool = False
    ) -> S2View | None:
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
                quest.progress = {}
                quest.content_version = S2_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world)
                quest = Quest(
                    character_id=character.id,
                    quest_id=S2_ID,
                    title=S2_TITLE,
                    status="active",
                    step=1,
                    content_version=S2_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world)

    async def objective(self, actor: int) -> S2View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            # Read-only objective callbacks must preserve the current foreground
            # combat/result state instead of replacing it with a narrative screen.
            return await self._view(session, character, quest, world)

    async def find_camp(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_coop_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=1) or not self._at(world, CHARNECA):
                return await self._view(session, character, quest, world)
            if await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            for member in await self._present_objective_members(
                session, character.id, step=1
            ):
                progress = dict(member.quest.progress or {})
                if progress.get("camp_found"):
                    continue
                progress["camp_found"] = True
                member.quest.progress = progress
                member.quest.step = 2
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=S2_ID,
                    objective_id="s2.camp",
                    source_key="s2.camp:found",
                    evidence={"location": CHARNECA},
                )
            return await self._view(session, character, quest, world)

    async def examine_vestige(self, actor: int, vestige_id: str, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_coop_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=2)
                or not self._at(world, CHARNECA)
                or vestige_id not in S2_VESTIGE_IDS
                or not (quest.progress or {}).get("camp_found")
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)

            members = await self._present_objective_members(
                session, character.id, step=2
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                vestiges = set(progress.get("vestiges", []))
                if vestige_id in vestiges:
                    continue
                vestiges.add(vestige_id)
                progress["vestiges"] = [
                    item for item in S2_VESTIGE_IDS if item in vestiges
                ]
                member.quest.progress = progress
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=S2_ID,
                    objective_id="s2.vestige",
                    source_key=f"s2.vestige:{vestige_id}",
                    evidence={"vestige_id": vestige_id, "location": CHARNECA},
                )
                if len(vestiges) == len(S2_VESTIGE_IDS):
                    member.quest.step = 3
                    progress.update(
                        encounter_result=None,
                        awaiting_retry=False,
                        combat_pending=True,
                    )
                    member.quest.progress = progress

            group_size = await self._group_size(session, character.id)
            if (
                quest.step == 3
                and not (quest.progress or {}).get("awaiting_retry")
                and group_size == 1
            ):
                activity = await self._materialize_combat(session, character, quest, world)
                if activity is None:
                    return await self._view(session, character, quest, world)
            return await self._view(session, character, quest, world)

    async def start_solo_combat(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or len(progress.get("vestiges", ())) != len(S2_VESTIGE_IDS)
                or not self._at(world, CHARNECA)
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
            activity = await self._materialize_combat(session, character, quest, world)
            if activity is None:
                quest.progress = {**progress, "combat_pending": True}
                return await self._view(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int) -> S2View | None:
        if self.groups is None:
            return await self.start_solo_combat(actor, version)
        initial = await self.resume(actor)
        if (
            initial is None
            or initial.status != "active"
            or initial.step != 3
            or initial.state_version != version
            or initial.location != CHARNECA
            or len(initial.progress.get("vestiges", ())) != len(S2_VESTIGE_IDS)
        ):
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_s2",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._s2_combat_eligibility,
            context_payload={
                "quest_id": S2_ID,
                "checkpoint": "s2.peregrino_calcinado",
                "title": f"{S2_TITLE} · Peregrino Calcinado",
                "reference_character_id": str(initial.character_id),
                "location": CHARNECA,
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
    ) -> S2View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._s2_combat_eligibility,
            create_activity=self._create_s2_group_combat,
        )
        return await self.resume(actor)

    async def _s2_combat_eligibility(self, session, character, payload):
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == S2_ID)
        )
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        progress = dict(quest.progress or {}) if quest else {}
        if (
            active is not None
            or not self._at(world, CHARNECA)
            or payload.get("location") != CHARNECA
            or quest is None
            or quest.content_version != S2_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and len(progress.get("vestiges", ())) == len(S2_VESTIGE_IDS)
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

    async def _create_s2_group_combat(self, session, proposal, characters):
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
                    checkpoint="s2.peregrino_calcinado",
                )
            )
        lead = characters[0]
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(PEREGRINO, 4, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor="As cinzas cedem sob os passos. Um Peregrino Calcinado se volta ao grupo.",
            opening_log="🧥 Peregrino Calcinado · Nv.4 surge junto ao acampamento.",
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
            quest_id=S2_ID,
            content_id=S2_COMBAT_CONTENT_ID,
            combat=combat,
            ruleset_version=RULESET,
            checkpoint="s2.peregrino_calcinado",
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
                quest = await self._locked_quest(session, member.character_id)
                if quest is not None:
                    quest.progress = {
                        **(quest.progress or {}),
                        "combat_activity_id": str(member.game_activity_id),
                    }
            await self.bestiary.record(
                session,
                member.character_id,
                PEREGRINO.creature_id,
                evidence_id=f"habitat:{CHARNECA_LOCATION}",
                evidence_category="habitat",
                evidence_points=3,
                grant_observation_xp=True,
                observation_level=4,
                observation_category="common",
            )
        await session.flush()
        return str(encounter.id)

    async def retry(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or not progress.get("awaiting_retry")
                or not self._at(world, CHARNECA)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            progress.update(awaiting_retry=False, combat_pending=False)
            quest.progress = progress
            activity = await self._materialize_combat(session, character, quest, world)
            if activity is None:
                progress["awaiting_retry"] = True
                quest.progress = progress
                return await self._view(session, character, quest, world)
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
    ) -> S2View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            shared, shared_member, _shared_combat = await campaign_combat_for_activity(
                session, activity_id, seed.id
            )
            if shared_member is not None:
                locked = await lock_campaign_encounter(session, activity_id, seed.id)
                if locked is None or locked.encounter.content_id != S2_COMBAT_CONTENT_ID:
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
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S2_COMBAT_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None or quest is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                quest.status != "active"
                or quest.content_version != S2_VERSION
                or quest.step != 3
                or activity.status != "active"
                or activity.state_version != version
                or foreground is None
                or foreground.id != activity.id
                or not self._at(world, CHARNECA)
                or (action is None) == (consumable_id is None)
            ):
                return current

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
                    return replace(
                        current,
                        consumable_notice="⚠️ Consumível · Não está mais disponível.",
                    )
                budget = ENCOUNTER_CONSUMABLE_LIMITS.get(PEREGRINO.category, 0)
                updated = use_combat_consumable(
                    combat,
                    consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=budget,
                )
                if updated.version == combat.version:
                    notice = self._consumable_rejection_notice(combat, budget)
                    return replace(
                        current,
                        consumable_notice=notice or "⚠️ Consumível · Não está mais disponível.",
                    )
                stack.quantity -= 1

            if updated.version == combat.version:
                return current
            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            character.hp = updated.fighters["player"].hp
            await self.bestiary.record_combat_events(
                session, character.id, PEREGRINO.creature_id, None, updated
            )

            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await self.bestiary.record(
                    session,
                    character.id,
                    PEREGRINO.creature_id,
                    victory=True,
                    observation_category="common",
                )
                await self._normalize_character_hp(session, character)
                # Step 4 is satisfied by this terminal Victory; step 5 is the next action.
                quest.step = 5
                progress.update(
                    encounter_result="victory",
                    awaiting_retry=False,
                    combat_pending=False,
                    fragment_recovered=False,
                )
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session,
                    character.id,
                    PEREGRINO.creature_id,
                    observation_category="common",
                )
                await self._normalize_character_hp(session, character)
                recovery_brazier, recovery_location = await self.road.recover_normal_pve_defeat(
                    session, character, CHARNECA_LOCATION, world
                )
                progress.update(
                    encounter_result="defeat",
                    awaiting_retry=True,
                    combat_pending=False,
                    defeat_activity_id=str(activity.id),
                    recovery_brazier=recovery_brazier,
                    recovery_location=recovery_location,
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def campaign_action(
        self, actor: int, activity_id: UUID, version: int, action: str
    ) -> S2View | None:
        return await self.action(actor, activity_id, version, action)

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
        quest = await self._locked_quest(session, character.id)
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
            consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(PEREGRINO.category, 0),
        )
        if updated.version == version:
            if consumable_id is not None:
                notice = self._consumable_rejection_notice(
                    locked.combat, ENCOUNTER_CONSUMABLE_LIMITS.get(PEREGRINO.category, 0)
                )
                return replace(
                    current,
                    consumable_notice=notice or "⚠️ Consumível · Não está mais disponível.",
                )
            return current
        if stack is not None:
            stack.quantity -= 1

        quests = list(
            (
                await session.scalars(
                    select(Quest)
                    .where(
                        Quest.character_id.in_(locked.characters),
                        Quest.quest_id == S2_ID,
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
        member_by_character = {row.character_id: row for row in locked.members}
        for character_id, participant in locked.characters.items():
            roster_member = member_by_character[character_id]
            participant_quest = quests_by_character.get(character_id)
            await self.bestiary.record_combat_events(
                session, character_id, PEREGRINO.creature_id, None, updated
            )
            if updated.result:
                await record_campaign_objective_credit(
                    session,
                    character_id=character_id,
                    quest_id=S2_ID,
                    objective_id="s2.peregrino_calcinado",
                    source_key=f"s2.peregrino_calcinado:{encounter.id}",
                    evidence={"result": updated.result, "encounter_id": str(encounter.id)},
                )
            if updated.result == "victory":
                await self.bestiary.record(
                    session,
                    character_id,
                    PEREGRINO.creature_id,
                    victory=True,
                    observation_category="common",
                )
                if (
                    roster_member.role == "eligible"
                    and participant_quest is not None
                    and participant_quest.status == "active"
                    and participant_quest.step == 3
                ):
                    await self._grant_enemy_xp(
                        session,
                        participant,
                        locked.activities[roster_member.game_activity_id],
                    )
                    progress = dict(participant_quest.progress or {})
                    progress.update(
                        encounter_result="victory",
                        awaiting_retry=False,
                        combat_pending=False,
                        fragment_recovered=False,
                    )
                    participant_quest.progress = progress
                    participant_quest.step = 5
                    participant_quest.state_version += 1
                await self._normalize_character_hp(session, participant)
            elif updated.result == "defeat":
                await self.bestiary.record(
                    session,
                    character_id,
                    PEREGRINO.creature_id,
                    observation_category="common",
                )
                await self._normalize_character_hp(session, participant)
                participant_world = worlds_by_character.get(character_id)
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, participant, CHARNECA_LOCATION, participant_world
                )
                if (
                    roster_member.role == "eligible"
                    and participant_quest is not None
                    and participant_quest.status == "active"
                    and participant_quest.step == 3
                ):
                    progress = dict(participant_quest.progress or {})
                    progress.update(
                        encounter_result="defeat",
                        awaiting_retry=True,
                        combat_pending=True,
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
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        screen: str = "items",
        item_id: str | None = None,
        target_id: str | None = None,
        parent: str = "items",
    ) -> S2View | None:
        """Rebuild shared combat Consumable selection from current persisted state."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S2_COMBAT_CONTENT_ID,
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
                option for option in current.consumable_options if option.item_id == item_id
            )
            if item is None or not item_options:
                return replace(
                    current,
                    consumable_screen=("items" if current.consumable_options else None),
                    consumable_notice="⚠️ Consumível · Não está mais disponível.",
                )
            if screen == "choose_item":
                if item.family == ConsumableFamily.DISPELLER:
                    target_ids = tuple(dict.fromkeys(option.target_id for option in item_options))
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
                    target_id, parent = "player", "items"
                selected = tuple(option for option in item_options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent=parent
                )
            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(option for option in item_options if option.target_id == target_id)
                if not selected:
                    return replace(
                        current,
                        consumable_screen=("items" if current.consumable_options else None),
                        consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
                    )
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )
            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                target_ids = tuple(dict.fromkeys(option.target_id for option in item_options))
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
                consumable_screen=("items" if current.consumable_options else None),
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

    async def recover_fragment(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=5)
                or not self._at(world, CHARNECA)
                or (quest.progress or {}).get("encounter_result") != "victory"
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            progress["fragment_recovered"] = True
            quest.progress = progress
            quest.step = 6
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def complete_with_oren(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if quest.status == "completed":
                return await self._view(session, character, quest, world)
            if (
                not self._valid(quest, version, step=6)
                or not self._at(world, REFUGE)
                or not (quest.progress or {}).get("fragment_recovered")
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)

            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == S2_REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                event = RewardEvent(
                    character_id=character.id,
                    source_id=S2_REWARD_SOURCE,
                )
                session.add(event)
                await session.flush()
                character.xp += 2695
                character.crowns += 120
                components = [
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        item_id=None,
                        quantity=2695,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        item_id=None,
                        quantity=120,
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
                    for material_id, quantity in S2_MATERIAL_REWARDS
                )
                session.add_all(components)
                for material_id, quantity in S2_MATERIAL_REWARDS:
                    await self.road.deliver_material(
                        session,
                        character,
                        material_id,
                        quantity,
                        f"{S2_REWARD_SOURCE}:material:{material_id}",
                        bound=True,
                    )
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=S2_CODEX_ENTRY,
            )
            await self._normalize_character_hp(session, character)
            quest.status = "completed"
            quest.progress = {
                **(quest.progress or {}),
                "completed": True,
                "codex_recorded": True,
            }
            quest.state_version += 1
            from asterion.application.tdo_feats import reconcile_tdo_feats

            await reconcile_tdo_feats(session, character)
            if character.tracked_secondary_quest_id == S2_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world)

    async def toggle_tracking(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S2_ID else S2_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def abandon_confirmation(self, actor: int) -> S2View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None or world is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            quest.status = "abandoned"
            quest.step = 1
            quest.progress = {}
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S2_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _materialize_combat(self, session, character, quest, world):
        if not self._at(world, CHARNECA):
            return None
        foreground = await self._foreground(session, character.id)
        if foreground is not None:
            if foreground.content_id == S2_COMBAT_CONTENT_ID and str(foreground.id) == (
                quest.progress or {}
            ).get("combat_activity_id"):
                return foreground
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
            PEREGRINO,
            4,
            None,
            player_level=character.level,
            equipment_configuration=configuration,
            ruleset_version=RULESET,
            flavor="As cinzas cedem sob os passos. Um Peregrino Calcinado se volta para você.",
            opening_log="🧥 Peregrino Calcinado · Nv.4 surge junto ao acampamento.",
            active_art_ids=active_art_configuration.art_ids,
        )
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | (
            active_art_configuration.to_data()
        )
        activity, encounter, record = await CombatRepository(session).create(
            character, S2_COMBAT_CONTENT_ID, combat
        )
        progress = dict(quest.progress or {})
        progress.update(
            combat_activity_id=str(activity.id),
            encounter_result=None,
            awaiting_retry=False,
            combat_pending=False,
        )
        quest.progress = progress
        await self.bestiary.record(
            session,
            character.id,
            PEREGRINO.creature_id,
            evidence_id=f"habitat:{CHARNECA_LOCATION}",
            evidence_category="habitat",
            evidence_points=3,
            grant_observation_xp=True,
            observation_level=4,
            observation_category="common",
        )
        await session.flush()
        return activity

    async def _grant_enemy_xp(self, session, character, activity) -> int:
        source_id = f"{S2_REWARD_SOURCE}:enemy-xp:{activity.id}"
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
        amount = enemy_xp(4, "common", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="enemy_xp",
                item_id=PEREGRINO.creature_id,
                quantity=amount,
                payload={
                    "enemy_level": 4,
                    "category": "common",
                    "observation_context": "S2",
                },
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
        group_size = await self._group_size(session, character.id)
        activity = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == S2_COMBAT_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        encounter_id = None
        combat_id = None
        combat = None
        activity_status = None
        activity_state_version = None
        combat_actor_key = "player"
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
                        GameActivity.content_id == S2_COMBAT_CONTENT_ID,
                    )
                )
        if activity is not None:
            activity_status = activity.status
            activity_state_version = activity.state_version
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity.id, character.id
            )
            if shared is not None and shared_member is not None:
                encounter_id = combat_id = shared.id
                combat_actor_key = shared_member.actor_key
                combat = shared_combat if activity.status == "active" else None
                group_size = shared.roster_size
            else:
                result = await session.execute(
                    select(Encounter, CombatRecord)
                    .join(CombatRecord)
                    .where(Encounter.game_activity_id == activity.id)
                )
                row = result.one_or_none()
                encounter, record = row if row is not None else (None, None)
                if encounter is not None and record is not None:
                    encounter_id = encounter.id
                    combat_id = record.id
                    if activity.status == "active":
                        combat = decode(
                            record.snapshot,
                            record.id,
                            activity.ruleset_version,
                            activity.state_version,
                        )

        if quest is None:
            status = "unaccepted"
            step = 1
            state_version = 0
        else:
            status, step, state_version = (
                quest.status,
                quest.step,
                quest.state_version,
            )

        available = await self._eligible(session, character) if quest is None else False
        reacceptable = bool(
            quest is not None
            and quest.status == "abandoned"
            and await self._eligible(session, character)
        )
        if requested_kind is not None:
            kind = requested_kind
        elif combat is not None:
            kind = "combat"
        elif quest is None:
            kind = "offer" if available else "unavailable"
        elif quest.status == "completed":
            kind = "completed"
        elif quest.status == "abandoned":
            kind = "abandoned"
        elif combat is not None:
            kind = "combat"
        elif step == 1:
            kind = "detail"
        elif step == 2:
            kind = "objective"
        elif step == 3 and progress.get("awaiting_retry"):
            kind = "recovery"
        elif step == 3:
            kind = "combat_pending"
        elif step == 5:
            kind = "fragment"
        else:
            kind = "return"

        quantities: tuple[tuple[str, int], ...] = ()
        options: tuple[CombatConsumableOption, ...] = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            budget = ENCOUNTER_CONSUMABLE_LIMITS.get(PEREGRINO.category, 0)
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
                    GroupActivityProposal.activity_type == "campaign_s2",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .order_by(GroupActivityProposal.created_at.desc(), GroupActivityProposal.id)
                .limit(1)
            )
            proposal_pair = proposal_rows.first()

        return S2View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=step,
            state_version=state_version,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=available,
            reacceptable=reacceptable,
            tracked=bool(
                quest and quest.status == "active" and character.tracked_secondary_quest_id == S2_ID
            ),
            combat=combat,
            activity_id=activity.id if activity is not None else None,
            activity_state_version=activity_state_version,
            activity_status=activity_status,
            encounter_id=encounter_id,
            combat_id=combat_id,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            stage=character.stage,
            xp=character.xp,
            proposal_id=proposal_pair[1].id if proposal_pair else None,
            proposal_status=proposal_pair[1].status if proposal_pair else None,
            group_size=group_size,
            combat_actor_key=combat_actor_key,
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

    async def _eligible(self, session, character):
        p2_completed = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == P2_ID,
                Quest.status == "completed",
            )
        )
        return bool(p2_completed and character.level >= 4)

    async def _locked_state(self, session, actor):
        character = await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
            .with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await self._locked_quest(session, character.id)
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id).with_for_update()
        )
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
            quest_id=S2_ID,
            content_version=S2_VERSION,
            step=step,
            region=REGION,
            location=CHARNECA,
        )

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
                Quest.quest_id == S2_ID,
            )
        )

    async def _locked_quest(self, session, character_id):
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id == S2_ID,
            )
            .with_for_update()
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

    async def _ensure(self, session, model, **values):
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return found
        row = model(**values)
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest is not None
            and quest.status == "active"
            and quest.content_version == S2_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world is not None and world.region == REGION and world.location == location)
