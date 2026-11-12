"""Authoritative application service for P1: Vozes na Estrada."""

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.campaign_coop import (
    CampaignRosterMember,
    campaign_action_intent,
    create_campaign_encounter,
    lock_campaign_encounter,
    resolve_campaign_action,
)
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.groups import (
    ActivityEligibility,
    GroupError,
    GroupService,
)
from asterion.application.narrative_choices import (
    NarrativeNodeView,
    commit_mission_choice,
    narrative_node_view,
)
from asterion.domain.combat import Combat, act
from asterion.domain.creation import RULESET as CHARACTER_RULESET
from asterion.domain.prologue import (
    P1_CONTENT_ID,
    P1PartyMember,
    p1_combat_profile,
    p1_party_combat_profile,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Brazier,
    CampaignJourney,
    CampaignJourneyMember,
    CampaignObjectiveCredit,
    CampaignSharedEncounter,
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CombatRecord,
    Encounter,
    GameActivity,
    GroupActivityParticipant,
    GroupActivityProposal,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    SocialGroupMember,
    Unlock,
    WorldState,
)

P1_ID = "P1"
P1_VERSION = "tdo-1.0.2"
P1_TITLE = "Vozes na Estrada"
ROAD = "Estrada das Cinzas"
REGION = "Terras do Ocaso"
REFUGE = "Refúgio do Ocaso"
REFUGE_BRAZIER = "tdo.brazier.refugio_do_ocaso"
P1_CHECKPOINT = "p1.cao_cinereo"


@dataclass(frozen=True)
class P1View:
    character_id: UUID
    step: int
    state_version: int
    progress: dict
    combat: Combat | None = None
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    context: str = "p1"
    status: str = "active"
    known_locations: tuple[str, ...] = ()
    combat_actor_key: str | None = None
    group_size: int = 1
    proposal_id: UUID | None = None
    proposal_status: str | None = None
    narrative: NarrativeNodeView | None = None


class P1Service:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        groups: GroupService | None = None,
    ):
        self.sessions, self.server_id, self.groups = sessions, server_id, groups

    async def resume(self, actor: int):
        async with self.sessions() as s:
            c = await self._character(s, actor)
            q = await self._quest(s, c.id) if c else None
            return await self._view(s, c, q) if q and q.content_version == P1_VERSION else None

    async def follow_road(self, actor: int, version: int):
        return await self._advance_shared_objective(
            actor, version, 1, ROAD, "p1.follow_road", self._follow
        )

    async def examine(self, actor: int, signal: str, version: int):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, 2):
                return await self._view(s, c, q)
            if signal not in {"pegadas", "sulcos"}:
                return await self._view(s, c, q)
            participants = await self._p1_present_participants(s, c, q, step=2, location=ROAD)
            changed = False
            for participant, quest in participants:
                progress = dict(quest.progress or {})
                if signal == "sulcos" and not progress.get("pegadas"):
                    continue
                if progress.get(signal):
                    continue
                progress[signal] = True
                quest.progress = progress
                if signal == "sulcos":
                    quest.step = 3
                quest.state_version += 1
                await self._record_objective_credit(
                    s,
                    participant.id,
                    quest,
                    f"p1.signal.{signal}",
                    {"location": ROAD, "shared_group": len(participants) > 1},
                )
                changed = True
            if not changed:
                return await self._view(s, c, q)
            group_size = await self._social_group_size(s, c.id)
            if signal == "sulcos" and group_size <= 1:
                return await self._start_solo_combat_locked(s, c, q)
            return await self._view(s, c, q)

    async def start_solo_combat(self, actor: int, version: int) -> P1View | None:
        async with self.sessions.begin() as session:
            character, quest = await self._locked(session, actor)
            if not self._valid(character, quest, version, 3):
                return await self._view(session, character, quest)
            return await self._start_solo_combat_locked(session, character, quest)

    async def propose_group_combat(self, actor: int, version: int) -> P1View | None:
        if self.groups is None:
            return await self.resume(actor)
        initial = await self.resume(actor)
        if initial is None or initial.status != "active" or initial.step != 3:
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_p1",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._p1_combat_eligibility,
            context_payload={
                "quest_id": P1_ID,
                "checkpoint": "p1.cao_cinereo",
                "title": f"{P1_TITLE} · Cão Cinéreo",
                "reference_character_id": str(initial.character_id),
                "location": ROAD,
            },
            journey_reference_character_id=initial.character_id,
        )
        view = await self.resume(actor)
        return replace(
            view,
            proposal_id=proposal.proposal_id,
            proposal_status=proposal.status,
        ) if view is not None else None

    async def start_group_combat(
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
    ) -> P1View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._p1_combat_eligibility,
            create_activity=self._create_p1_group_combat,
        )
        return await self.resume(actor)

    async def _p1_combat_eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == P1_ID)
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
            world and world.region == REGION and world.location == payload.get("location") == ROAD
        )
        if (
            active is not None
            or not same_location
            or quest is None
            or quest.content_version != P1_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and bool((quest.progress or {}).get("pegadas"))
            and bool((quest.progress or {}).get("sulcos"))
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

    async def _create_p1_group_combat(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
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
        party: list[P1PartyMember] = []
        roster: list[CampaignRosterMember] = []
        for index, character in enumerate(characters, start=1):
            participant = row_by_character.get(character.id)
            if participant is None or participant.eligibility not in {"eligible", "helper"}:
                raise GroupError("eligibility_changed")
            configuration = await load_equipment_configuration(session, character)
            reconcile_character_hp(character, configuration)
            actor_key = f"p{index}"
            party.append(
                P1PartyMember(
                    actor_key=actor_key,
                    character_id=character.id,
                    name=character.name,
                    character_class=character.character_class,
                    race=character.race,
                    level=character.level,
                    hp=character.hp,
                    equipment_configuration=configuration,
                )
            )
            roster.append(
                CampaignRosterMember(
                    character=character,
                    actor_key=actor_key,
                    role=participant.eligibility,
                    checkpoint=P1_CHECKPOINT,
                )
            )
        combat = p1_party_combat_profile(uuid4(), tuple(party))
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=P1_ID,
            content_id=P1_CONTENT_ID,
            combat=combat,
            ruleset_version=combat.ruleset,
            checkpoint=P1_CHECKPOINT,
        )
        return str(encounter.id)

    async def _start_solo_combat_locked(self, session, character, quest) -> P1View:
        active = await session.scalar(
            select(GameActivity)
            .where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
            .with_for_update()
        )
        if active is not None:
            return await self._view(session, character, quest)
        reservation = await session.scalar(
            select(GroupActivityParticipant).where(
                GroupActivityParticipant.character_id == character.id,
                GroupActivityParticipant.reservation_state == "active",
            )
        )
        if reservation is not None:
            return await self._view(session, character, quest)
        configuration = await load_equipment_configuration(session, character)
        reconcile_character_hp(character, configuration)
        await CombatRepository(session).create(
            character,
            P1_CONTENT_ID,
            p1_combat_profile(
                uuid4(),
                character.name,
                character.character_class,
                character.race,
                character.hp,
                configuration,
            ),
        )
        progress = dict(quest.progress or {})
        if progress.get("defeat") or progress.get("recovery"):
            progress.update(defeat=False, recovery=False)
            quest.progress = progress
            quest.state_version += 1
        return await self._view(session, character, quest)

    async def action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str,
        *,
        target_id: str | None = None,
    ):
        shared_view = await self._shared_action(
            actor, activity_id, version, action, target_id=target_id
        )
        if shared_view is not None:
            return shared_view
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            a = (
                await s.scalar(
                    select(GameActivity)
                    .where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == c.id if c else False,
                        GameActivity.content_id == P1_CONTENT_ID,
                    )
                    .with_for_update()
                )
                if c
                else None
            )
            if a is None:
                return None
            if (
                q is None
                or q.status != "active"
                or q.content_version != P1_VERSION
                or q.step != 3
                or a.status != "active"
                or a.state_version != version
            ):
                return await self._view(s, c, q)
            e, r = (
                await s.execute(
                    select(Encounter, CombatRecord)
                    .join(CombatRecord)
                    .where(Encounter.game_activity_id == a.id)
                )
            ).one()
            combat = decode(r.snapshot, r.id, a.ruleset_version, a.state_version)
            updated = act(combat, action, target_id=target_id)
            if updated.version == combat.version:
                return await self._view(s, c, q)
            a.state_version = updated.version
            r.snapshot = encode(updated)
            c.hp = updated.fighters["player"].hp
            p = dict(q.progress or {})
            if updated.result == "victory":
                a.status = "completed"
                q.step = 4
                p.update(arrival=True, defeat=False)
                c.ruleset_version = CHARACTER_RULESET
            elif updated.result == "defeat":
                a.status = "failed"
                q.step = 3
                c.hp = c.max_hp
                p.update(defeat=True, recovery=True)
                w = await s.scalar(
                    select(WorldState).where(WorldState.character_id == c.id).with_for_update()
                )
                if w:
                    w.region, w.location = REGION, ROAD
            q.progress, q.state_version = p, q.state_version + 1
            return await self._view(s, c, q)

    async def retry(self, actor: int, version: int):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, 3) or not (q.progress or {}).get("defeat"):
                return await self._view(s, c, q)
            equipment_configuration = await load_equipment_configuration(s, c)
            reconcile_character_hp(c, equipment_configuration)
            await CombatRepository(s).create(
                c,
                P1_CONTENT_ID,
                p1_combat_profile(
                    uuid4(),
                    c.name,
                    c.character_class,
                    c.race,
                    c.hp,
                    equipment_configuration,
                ),
            )
            p = dict(q.progress or {})
            p.update(defeat=False, recovery=False)
            q.progress, q.state_version = p, q.state_version + 1
            return await self._view(s, c, q)

    async def enter_refuge(self, actor: int, version: int):
        return await self._advance_shared_objective(
            actor, version, 4, ROAD, "p1.reach_refuge", self._enter_refuge
        )

    async def follow_alda(self, actor: int, version: int):
        """Etapa 5 now ends through the narrative node; a stale button only refreshes."""
        return await self.resume(actor)

    async def choose_posture(self, actor: int, version: int, option_id: str):
        """P1_choice_posture: first talk with Alda. Individual and commit once."""
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, 5):
                return await self._view(s, c, q)
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            if world is None or world.location != REFUGE:
                return await self._view(s, c, q)
            result = await commit_mission_choice(s, c, q, option_id)
            if result is None:
                return await self._view(s, c, q)
            await self._alda(s, c, q)
            q.state_version += 1
            await self._record_objective_credit(
                s, c.id, q, "p1.meet_alda", {"location": REFUGE, "shared_group": False}
            )
            return await self._view(s, c, q)

    async def go_brazier(self, actor: int, version: int):
        return await self._advance_shared_objective(
            actor, version, 6, REFUGE, "p1.meet_oren", self._oren
        )

    async def activate_brazier(self, actor: int, version: int):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, 7):
                return await self._view(s, c, q)
            participants = await self._p1_present_participants(
                s, c, q, step=7, location=REFUGE
            )
            if not participants:
                return await self._view(s, c, q)
            for participant, quest in participants:
                await self._complete_p1_for(s, participant, quest)
                await self._record_objective_credit(
                    s,
                    participant.id,
                    quest,
                    "p1.activate_refuge_brazier",
                    {"location": REFUGE, "shared_group": len(participants) > 1},
                )
            return await self._view(s, c, q)

    async def campaign_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
    ):
        """Resolve a compact Telegram intent against the current shared combat view."""
        from asterion.domain.combat import active_player_key

        view = await self.resume(actor)
        if view is not None and view.activity_id != activity_id:
            return None
        if (
            view is None
            or view.combat is None
            or view.combat.version != version
            or view.combat_actor_key != active_player_key(view.combat)
        ):
            return view
        actor_key = view.combat_actor_key
        intent = campaign_action_intent(view.combat, actor_key, action_index, target_code)
        if intent is None:
            return view
        action, target_id = intent
        return await self.action(actor, activity_id, version, action, target_id=target_id)

    async def _shared_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str,
        *,
        target_id: str | None = None,
    ) -> P1View | None:
        async with self.sessions.begin() as session:
            character_seed = await self._character(session, actor)
            if character_seed is None:
                return None
            shared_member = await session.scalar(
                select(CampaignSharedEncounterMember).where(
                    CampaignSharedEncounterMember.game_activity_id == activity_id,
                    CampaignSharedEncounterMember.character_id == character_seed.id,
                )
            )
            if shared_member is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, character_seed.id)
            if locked is None or locked.encounter.quest_id != P1_ID:
                return None
            member = next(
                (row for row in locked.members if row.game_activity_id == activity_id), None
            )
            character = locked.characters.get(character_seed.id)
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(
                            Quest.character_id.in_(locked.characters),
                            Quest.quest_id == P1_ID,
                        )
                        .order_by(Quest.character_id)
                        .with_for_update()
                    )
                ).all()
            )
            quest_by_character = {row.character_id: row for row in quest_rows}
            quest = quest_by_character.get(character_seed.id)
            activity = locked.activities.get(activity_id)
            if character is None or quest is None or activity is None:
                return None
            if (
                member is None
                or locked.encounter.content_id != P1_CONTENT_ID
                or activity.status != "active"
                or activity.state_version != version
                or locked.encounter.state_version != version
            ):
                return await self._view(session, character, quest)
            updated = resolve_campaign_action(
                locked,
                activity_id=activity_id,
                version=version,
                action=action,
                target_id=target_id,
            )
            if updated.version == version:
                return await self._view(session, character, quest)
            if updated.result:
                member_by_character = {row.character_id: row for row in locked.members}
                for character_id, participant in locked.characters.items():
                    roster_member = member_by_character[character_id]
                    participant_quest = quest_by_character.get(character_id)
                    if roster_member.role == "eligible" and participant_quest is not None:
                        progress = dict(participant_quest.progress or {})
                        if (
                            participant_quest.status == "active"
                            and participant_quest.content_version == P1_VERSION
                            and participant_quest.step == 3
                        ):
                            if updated.result == "victory":
                                participant_quest.step = 4
                                progress.update(arrival=True, defeat=False, recovery=False)
                                participant.ruleset_version = CHARACTER_RULESET
                            else:
                                participant.hp = participant.max_hp
                                progress.update(defeat=True, recovery=True)
                            participant_quest.progress = progress
                            participant_quest.state_version += 1
                    elif updated.result == "defeat":
                        # A helper is still subject to the encounter recovery, but its
                        # independently completed Quest state is never changed.
                        participant.hp = participant.max_hp
                await self._settle_campaign_activity(session, locked, updated.result)
            return await self._view(session, character, quest)

    async def _settle_campaign_activity(self, session, locked, result: str) -> None:
        now = datetime.now(UTC)
        encounter = locked.encounter
        for member in locked.members:
            member.settlement_state = "settled"
            member.result = result
            member.settled_at = now
        journey = await session.get(CampaignJourney, encounter.journey_id, with_for_update=True)
        if journey is not None:
            journey.status = "completed" if result == "victory" else "paused"
            journey.updated_at = now
            journey.revision += 1
            if result == "victory":
                journey_members = list(
                    (
                        await session.scalars(
                            select(CampaignJourneyMember)
                            .where(CampaignJourneyMember.journey_id == journey.id)
                            .with_for_update()
                        )
                    ).all()
                )
                for journey_member in journey_members:
                    journey_member.status = "completed"
        if encounter.proposal_id is not None:
            proposal = await session.get(
                GroupActivityProposal, encounter.proposal_id, with_for_update=True
            )
            if proposal is not None:
                proposal.status = "completed" if result == "victory" else "failed"
                proposal.finished_at = now
                proposal.revision += 1
            reservations = list(
                (
                    await session.scalars(
                        select(GroupActivityParticipant)
                        .where(GroupActivityParticipant.proposal_id == encounter.proposal_id)
                        .with_for_update()
                    )
                ).all()
            )
            for row in reservations:
                row.reservation_state = "released"

    async def _mutate(self, actor, version, step, fn):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, step):
                return await self._view(s, c, q)
            changed = await fn(s, c, q)
            if changed is not False:
                q.state_version += 1
            return await self._view(s, c, q)

    async def _follow(self, s, c, q):
        q.step = 2
        return True

    async def _enter_refuge(self, s, c, q):
        w = await s.scalar(
            select(WorldState).where(WorldState.character_id == c.id).with_for_update()
        )
        if w is None:
            return False
        await self._ensure(
            s, LocationDiscovery, character_id=c.id, location_id="tdo.location.refugio_do_ocaso"
        )
        w.region, w.location = REGION, REFUGE
        q.step = 5
        return True

    async def _alda(self, s, c, q):
        await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.figure.alda_veyr")
        q.step = 6
        return True

    async def _oren(self, s, c, q):
        await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.figure.oren_cal")
        q.step = 7
        return True

    async def _locked(self, s, actor):
        character_seed = await self._character(s, actor)
        if character_seed is None:
            return None, None
        membership = await s.get(SocialGroupMember, character_seed.id)
        if membership is not None:
            group = await s.scalar(
                select(SocialGroup)
                .where(SocialGroup.id == membership.group_id)
                .with_for_update()
            )
            if group is not None and group.status == "active":
                member_ids = list(
                    (
                        await s.scalars(
                            select(SocialGroupMember.character_id)
                            .where(SocialGroupMember.group_id == group.id)
                            .order_by(SocialGroupMember.character_id)
                        )
                    ).all()
                )
                locked_characters = list(
                    (
                        await s.scalars(
                            select(Character)
                            .where(Character.id.in_(member_ids))
                            .order_by(Character.id)
                            .with_for_update()
                        )
                    ).all()
                )
                c = next(
                    (item for item in locked_characters if item.id == character_seed.id), None
                )
            else:
                c = None
        else:
            c = await s.scalar(
                select(Character)
                .where(Character.id == character_seed.id)
                .with_for_update()
            )
        q = (
            await s.scalar(
                select(Quest)
                .where(Quest.character_id == c.id, Quest.quest_id == P1_ID)
                .with_for_update()
            )
            if c
            else None
        )
        return c, q

    async def _social_group_size(self, session, character_id: UUID) -> int:
        """This encounter is not a Boss: missions stay Solo (Ação × Consequência §5)."""
        return 1
    async def _p1_present_participants(
        self, session, actor_character, actor_quest, *, step, location
    ):
        # Missions are Solo for objectives (Ação × Consequência v1.0.0 §5).
        character_ids = [actor_character.id]
        active_ids = set(
            (
                await session.scalars(
                    select(GameActivity.character_id).where(
                        GameActivity.character_id.in_(character_ids),
                        GameActivity.status == "active",
                    )
                )
            ).all()
        )
        rows = list(
            (
                await session.execute(
                    select(Character, Quest, WorldState)
                    .join(Quest, Quest.character_id == Character.id)
                    .join(WorldState, WorldState.character_id == Character.id)
                    .where(
                        Character.id.in_(character_ids),
                        Quest.quest_id == P1_ID,
                        Quest.status == "active",
                        Quest.content_version == P1_VERSION,
                        Quest.step == step,
                        WorldState.location == location,
                        WorldState.region == REGION,
                    )
                    .order_by(Character.id)
                    .with_for_update(of=Quest)
                )
            ).all()
        )
        participants = [
            (character, quest)
            for character, quest, _world in rows
            if character.id not in active_ids
        ]
        if not any(character.id == actor_character.id for character, _ in participants):
            return []
        return participants

    async def _record_objective_credit(self, session, character_id, quest, objective_id, evidence):
        existing = await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == P1_ID,
                CampaignObjectiveCredit.objective_id == objective_id,
                CampaignObjectiveCredit.source_key == f"p1:{objective_id}",
            )
        )
        if existing is None:
            session.add(
                CampaignObjectiveCredit(
                    character_id=character_id,
                    quest_id=P1_ID,
                    objective_id=objective_id,
                    source_key=f"p1:{objective_id}",
                    evidence=evidence,
                )
            )

    async def _advance_shared_objective(
        self, actor, version, step, location, objective_id, operation
    ):
        async with self.sessions.begin() as session:
            character, quest = await self._locked(session, actor)
            if not self._valid(character, quest, version, step):
                return await self._view(session, character, quest)
            participants = await self._p1_present_participants(
                session, character, quest, step=step, location=location
            )
            if not participants:
                return await self._view(session, character, quest)
            for participant, participant_quest in participants:
                if await operation(session, participant, participant_quest) is False:
                    continue
                participant_quest.state_version += 1
                await self._record_objective_credit(
                    session,
                    participant.id,
                    participant_quest,
                    objective_id,
                    {"location": location, "shared_group": len(participants) > 1},
                )
            return await self._view(session, character, quest)

    async def _complete_p1_for(self, session, character, quest):
        await self._ensure(session, Brazier, character_id=character.id, brazier_id=REFUGE_BRAZIER)
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == "p1.vozes_na_estrada",
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id="p1.vozes_na_estrada")
            session.add(event)
            await session.flush()
            character.xp += 2400
            character.crowns += 120
            for kind, item, quantity in (
                ("xp", None, 2400),
                ("crowns", None, 120),
                ("material", "material.tdo.ferro_de_fuligem", 1),
                ("material", "material.tdo.couro_escoriado", 1),
            ):
                session.add(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind=kind,
                        item_id=item,
                        quantity=quantity,
                    )
                )
            for item in ("material.tdo.ferro_de_fuligem", "material.tdo.couro_escoriado"):
                stack = await session.scalar(
                    select(MaterialStack)
                    .where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.material_id == item,
                        MaterialStack.bound.is_(True),
                    )
                    .with_for_update()
                )
                if stack is None:
                    session.add(
                        MaterialStack(
                            character_id=character.id,
                            material_id=item,
                            quantity=1,
                            bound=True,
                        )
                    )
                else:
                    stack.quantity += 1
            for unlock_id in ("hunt_manual.estrada_das_cinzas", "explore.estrada_das_cinzas"):
                await self._ensure(
                    session, Unlock, character_id=character.id, unlock_id=unlock_id
                )
        quest.status = "completed"
        progress = dict(quest.progress or {})
        progress["completed"] = True
        quest.progress = progress
        quest.state_version += 1

    async def _character(self, s, actor):
        return await s.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _quest(self, s, cid):
        return await s.scalar(
            select(Quest).where(Quest.character_id == cid, Quest.quest_id == P1_ID)
        )

    def _valid(self, c, q, v, step=None):
        return bool(
            c
            and q
            and q.status == "active"
            and q.content_version == P1_VERSION
            and q.state_version == v
            and (step is None or q.step == step)
        )

    async def _view(self, s, c, q):
        if c is None or q is None:
            return None
        a = await s.scalar(
            select(GameActivity).where(
                GameActivity.character_id == c.id,
                GameActivity.content_id == P1_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        locations = tuple(
            (
                await s.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == c.id
                    )
                )
            ).all()
        )
        if a is None:
            proposal_rows = await s.execute(
                select(GroupActivityParticipant, GroupActivityProposal)
                .join(
                    GroupActivityProposal,
                    GroupActivityProposal.id == GroupActivityParticipant.proposal_id,
                )
                .where(
                    GroupActivityParticipant.character_id == c.id,
                    GroupActivityParticipant.reservation_state == "active",
                    GroupActivityProposal.activity_type == "campaign_p1",
                    GroupActivityProposal.status.in_(("pending", "ready")),
                )
                .order_by(GroupActivityProposal.created_at.desc(), GroupActivityProposal.id)
                .limit(1)
            )
            proposal_pair = proposal_rows.first()
            return P1View(
                c.id,
                q.step,
                q.state_version,
                q.progress or {},
                status=q.status,
                known_locations=locations,
                group_size=await self._social_group_size(s, c.id),
                proposal_id=proposal_pair[1].id if proposal_pair else None,
                proposal_status=proposal_pair[1].status if proposal_pair else None,
                narrative=(
                    await narrative_node_view(s, c, P1_ID)
                    if q.status == "active" and q.step in (5, 6)
                    else None
                ),
            )
        shared_member = await s.scalar(
            select(CampaignSharedEncounterMember).where(
                CampaignSharedEncounterMember.game_activity_id == a.id,
                CampaignSharedEncounterMember.character_id == c.id,
            )
        )
        if shared_member is not None:
            shared_encounter = await s.get(
                CampaignSharedEncounter, shared_member.shared_encounter_id
            )
            if shared_encounter is None or shared_encounter.combat_snapshot is None:
                return P1View(
                    c.id,
                    q.step,
                    q.state_version,
                    q.progress or {},
                    status=q.status,
                    known_locations=locations,
                )
            combat = decode(
                shared_encounter.combat_snapshot,
                shared_encounter.id,
                shared_encounter.ruleset_version,
                shared_encounter.state_version,
            )
            return P1View(
                c.id,
                q.step,
                q.state_version,
                q.progress or {},
                combat,
                a.id,
                shared_encounter.id,
                shared_encounter.id,
                status=q.status,
                known_locations=locations,
                combat_actor_key=shared_member.actor_key,
                group_size=shared_encounter.roster_size,
            )
        e, r = (
            await s.execute(
                select(Encounter, CombatRecord)
                .join(CombatRecord)
                .where(Encounter.game_activity_id == a.id)
            )
        ).one()
        combat = decode(r.snapshot, r.id, a.ruleset_version, a.state_version)
        return P1View(
            c.id,
            q.step,
            q.state_version,
            q.progress or {},
            combat,
            a.id,
            e.id,
            r.id,
            status=q.status,
            known_locations=locations,
        )

    async def _ensure(self, s, model, **values):
        obj = await s.scalar(select(model).filter_by(**values).with_for_update())
        if obj is None:
            s.add(model(**values))
        return obj
