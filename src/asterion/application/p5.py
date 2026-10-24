"""P5 campaign mission composed from persistent quests and shared combat."""
# ruff: noqa: E501

import hashlib
import json
from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.campaign_coop import (
    CampaignRosterMember,
    campaign_action_intent,
    campaign_actor_key,
    campaign_combat_for_activity,
    create_campaign_boss_profile,
    create_campaign_encounter,
    lock_campaign_encounter,
    resolve_campaign_action,
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
from asterion.domain.road import RUINS_LOCATION, SUNSET_CUSTODIAN, enemy_xp
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    ConsumableStack,
    Encounter,
    GameActivity,
    GroupActivityParticipant,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    SocialGroupMember,
    WorldState,
)

P5_ID = "P5"
P5_TITLE = "A Porta do Poente"
P5_VERSION = "tdo-1.0.11"
P5_CONTENT_ID = "p5_scripted_custodio_poente"
P5_REWARD_SOURCE = "p5.a_porta_do_poente"
P5_ELEMENTS = (
    "p5.door_element.1",
    "p5.door_element.2",
    "p5.door_element.3",
)
P5_CODEX_ENTRY = "codex.history.antigos_asterianos"
P5_DOOR_FRAGMENT = "codex.fragment.ruinas.porta_do_poente"
P5_SYMBOL_FRAGMENT = "codex.fragment.ruinas.simbolo_recorrente"
P5_IRON = "material.tdo.ferro_de_fuligem"
P5_RESIDUE = "material.tdo.residuo_ocaso"


@dataclass(frozen=True)
class P5View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p5"
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
    combat_actor_key: str | None = None
    group_size: int = 1
    proposal_id: UUID | None = None
    proposal_status: str | None = None


class P5Service:
    """Owns P5 transitions; movement and combat remain shared services."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        groups: GroupService | None = None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.groups = groups
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def offer(self, actor: int) -> P5View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            available = bool(
                quest is None
                and self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and await self._eligible(session, character)
            )
            return await self._view(
                session,
                character,
                quest,
                world,
                "offer" if available else "unavailable" if quest is None else None,
                available=available,
            )

    async def alda(self, actor: int) -> P5View | None:
        return await self._npc(actor, "alda")

    async def oren(self, actor: int) -> P5View | None:
        return await self._npc(actor, "oren")

    async def _npc(self, actor: int, npc: str) -> P5View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            available = bool(
                quest is None and await self._eligible(session, character)
            )
            return await self._view(
                session, character, quest, world, npc, available=available
            )

    async def resume(self, actor: int) -> P5View | None:
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

    async def accept(self, actor: int, version: int = 0) -> P5View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                quest is not None
                or version != 0
                or not self._at(world, REFUGE)
                or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            quest = Quest(
                character_id=character.id,
                quest_id=P5_ID,
                title=P5_TITLE,
                status="active",
                step=1,
                content_version=P5_VERSION,
                state_version=0,
                progress={},
            )
            session.add(quest)
            await session.flush()
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int):
        if self.groups is None:
            return await self.resume(actor)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            quest = await self._quest(session, character.id) if character else None
            world = await self._world(session, character.id) if character else None
            if (
                character is None
                or not self._valid(quest, version, step=3)
                or not self._at(world, RUINS)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            membership = await session.get(SocialGroupMember, character.id)
            if membership is None:
                return await self._view(session, character, quest, world)
            participants = tuple(
                (
                    await session.scalars(
                        select(SocialGroupMember.character_id)
                        .where(SocialGroupMember.group_id == membership.group_id)
                        .order_by(SocialGroupMember.joined_at, SocialGroupMember.character_id)
                    )
                ).all()
            )
        await self.groups.propose_activity(
            actor,
            activity_type="campaign_p5",
            participant_character_ids=participants,
            eligibility_resolver=self._p5_combat_eligibility,
            journey_reference_character_id=character.id,
            context_payload={
                "title": P5_TITLE,
                "quest_id": P5_ID,
                "checkpoint": "p5.custodio_poente",
                "location": RUINS,
            },
        )
        return await self.resume(actor)

    async def start_group_combat(
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
    ) -> P5View | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._p5_combat_eligibility,
            create_activity=self._create_p5_group_combat,
        )
        return await self.resume(actor)

    async def _p5_combat_eligibility(self, session, character, payload):
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == P5_ID,
            )
        )
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        same_location = self._at(world, payload.get("location")) and payload.get(
            "location"
        ) == RUINS
        if (
            active is not None
            or not same_location
            or quest is None
            or quest.content_version != P5_VERSION
        ):
            role = "ineligible"
        elif (
            quest.status == "active"
            and quest.step == 3
            and bool((quest.progress or {}).get("door_known"))
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

    async def _create_p5_group_combat(self, session, proposal, characters):
        participant_rows = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal.id)
                    .order_by(GroupActivityParticipant.ordinal)
                )
            ).all()
        )
        roles = {row.character_id: row.eligibility for row in participant_rows}
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        combat = await create_campaign_boss_profile(
            session,
            characters,
            SUNSET_CUSTODIAN,
            9,
            flavor="Uma figura blindada se ergue diante da Porta do Poente.",
            opening_log="🛡️ Custódio do Poente · Nv.9 guarda a estrutura deliberadamente protegida.",
        )
        roster = tuple(
            CampaignRosterMember(
                character=character,
                actor_key=campaign_actor_key(index, len(characters)),
                role=roles[character.id],
                checkpoint="p5.custodio_poente",
            )
            for index, character in enumerate(characters, start=1)
        )
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=P5_ID,
            content_id=P5_CONTENT_ID,
            combat=combat,
            ruleset_version=combat.ruleset,
            checkpoint="p5.custodio_poente",
            campaign_boss=True,
        )
        activities = list(
            (
                await session.scalars(
                    select(CampaignSharedEncounterMember).where(
                        CampaignSharedEncounterMember.shared_encounter_id == encounter.id
                    )
                )
            ).all()
        )
        for member in activities:
            quest = await session.scalar(
                select(Quest)
                .where(
                    Quest.character_id == member.character_id,
                    Quest.quest_id == P5_ID,
                )
                .with_for_update()
            )
            if quest is None:
                raise GroupError("eligibility_changed")
            progress = dict(quest.progress or {})
            progress.update(
                combat_activity_id=str(member.game_activity_id),
                combat_result=None,
                awaiting_retry=False,
            )
            quest.progress = progress
            if member.role == "eligible":
                quest.step = 3
                quest.state_version += 1
        return str(encounter.id)

    async def action(
        self,
        actor: int,
        version: int,
        operation: str,
        item: str | None = None,
    ) -> P5View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)

            progress = dict(quest.progress or {})
            if operation == "follow_structures" and quest.step == 1 and self._at(world, RUINS):
                progress["deep_guard_structures_followed"] = True
                quest.step = 2
            elif operation == "find_door" and quest.step == 2 and self._at(world, RUINS):
                progress["door_known"] = True
                progress["ruins_updated"] = True
                quest.step = 3
                await self._ensure_codex_fragment(session, character.id, P5_DOOR_FRAGMENT)
            elif operation == "start_boss" and quest.step == 3 and self._at(world, RUINS):
                if not progress.get("door_known") or progress.get("awaiting_retry"):
                    return await self._view(session, character, quest, world)
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif (
                operation == "retry"
                and quest.step == 3
                and progress.get("awaiting_retry")
                and self._at(world, RUINS)
            ):
                progress["awaiting_retry"] = False
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    progress["awaiting_retry"] = True
                    quest.progress = progress
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif operation == "element" and quest.step == 4 and self._at(world, RUINS):
                if item not in P5_ELEMENTS:
                    return await self._view(session, character, quest, world)
                found = set(progress.get("door_elements", ()))
                if item in found:
                    return await self._view(session, character, quest, world)
                found.add(item)
                progress["door_elements"] = [key for key in P5_ELEMENTS if key in found]
                if len(found) == len(P5_ELEMENTS):
                    quest.step = 5
            elif operation == "record_symbol" and quest.step == 5 and self._at(world, RUINS):
                progress["recurring_symbol_recorded"] = True
                quest.step = 6
                await self._ensure_codex_fragment(session, character.id, P5_SYMBOL_FRAGMENT)
            elif (
                operation in {"report_alda", "report_oren"}
                and quest.step == 6
                and self._at(world, REFUGE)
            ):
                reports = set(progress.get("reports", ()))
                reports.add("alda" if operation == "report_alda" else "oren")
                progress["reports"] = [name for name in ("alda", "oren") if name in reports]
                if reports == {"alda", "oren"}:
                    quest.progress = progress
                    await self._complete(session, character, quest)
                    return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)

            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

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
    ) -> P5View | None:
        shared_view = await self._shared_action(
            actor,
            activity_id,
            version,
            action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
        )
        if shared_view is not None:
            return shared_view
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P5_CONTENT_ID,
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
                category=SUNSET_CUSTODIAN.category,
            )
            if updated is None or updated.version == version:
                return current

            # Establish the legitimate first encounter before replaying combat evidence,
            # so an Elite action observed on the opening exchange is not lost.
            observed = await session.scalar(
                select(BestiaryEntry.id).where(
                    BestiaryEntry.character_id == character.id,
                    BestiaryEntry.creature_id == SUNSET_CUSTODIAN.creature_id,
                )
            )
            if observed is None:
                await self.bestiary.record(
                    session,
                    character.id,
                    SUNSET_CUSTODIAN.creature_id,
                    elite=True,
                    observation_category="elite",
                )
            await self.bestiary.record_combat_events(
                session, character.id, SUNSET_CUSTODIAN.creature_id, None, updated
            )

            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session,
                    character.id,
                    SUNSET_CUSTODIAN.creature_id,
                    victory=True,
                    elite=True,
                    observation_category="elite",
                )
                progress.update(combat_result="victory", awaiting_retry=False)
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session,
                    character.id,
                    SUNSET_CUSTODIAN.creature_id,
                    elite=True,
                    observation_category="elite",
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, RUINS_LOCATION, world
                )
                progress.update(
                    combat_result="defeat",
                    awaiting_retry=True,
                    defeat_activity_id=str(activity.id),
                    recovery_brazier=brazier,
                    recovery_location=location,
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def campaign_action(
        self, actor: int, activity_id: UUID, version: int, action_index: int, target_code: str
    ):
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
        return await self.action_combat(actor, activity_id, version, action, target_id=target_id)

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
    ) -> P5View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            encounter_seed, member_seed, _ = await campaign_combat_for_activity(
                session, activity_id, seed.id
            )
            if member_seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id != P5_ID:
                return None
            character = locked.characters.get(seed.id)
            member = next(
                (row for row in locked.members if row.game_activity_id == activity_id), None
            )
            if character is None or member is None:
                return None
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(
                            Quest.character_id.in_(locked.characters),
                            Quest.quest_id == P5_ID,
                        )
                        .order_by(Quest.character_id)
                        .with_for_update()
                    )
                ).all()
            )
            quests = {row.character_id: row for row in quest_rows}
            quest = quests.get(character.id)
            activity = locked.activities.get(activity_id)
            world = await self._world(session, character.id)
            if quest is None or activity is None or (action is None) == (consumable_id is None):
                return await self._view(session, character, quest, world)
            if (
                locked.encounter.content_id != P5_CONTENT_ID
                or locked.encounter.state_version != version
                or activity.state_version != version
                or activity.status != "active"
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
                    SUNSET_CUSTODIAN.category, 0
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
                observed = await session.scalar(
                    select(BestiaryEntry.id).where(
                        BestiaryEntry.character_id == character_id,
                        BestiaryEntry.creature_id == SUNSET_CUSTODIAN.creature_id,
                    )
                )
                if observed is None:
                    await self.bestiary.record(
                        session,
                        character_id,
                        SUNSET_CUSTODIAN.creature_id,
                        elite=True,
                        observation_category="elite",
                    )
                await self.bestiary.record_combat_events(
                    session, character_id, SUNSET_CUSTODIAN.creature_id, None, updated
                )
                if updated.result == "victory":
                    await self.bestiary.record(
                        session,
                        character_id,
                        SUNSET_CUSTODIAN.creature_id,
                        victory=True,
                        elite=True,
                        observation_category="elite",
                    )
                    await self._grant_enemy_xp(
                        session, participant, locked.activities[roster_member.game_activity_id]
                    )
                    await consolidate_character_level(session, participant)
                if roster_member.role == "eligible" and participant_quest is not None:
                    progress = dict(participant_quest.progress or {})
                    if updated.result == "victory":
                        participant_quest.step = 4
                        progress.update(combat_result="victory", awaiting_retry=False)
                    elif updated.result == "defeat":
                        participant_world = await self._world(session, character_id)
                        brazier, location = await self.road.recover_normal_pve_defeat(
                            session, participant, RUINS_LOCATION, participant_world
                        )
                        progress.update(
                            combat_result="defeat",
                            awaiting_retry=True,
                            defeat_activity_id=str(roster_member.game_activity_id),
                            recovery_brazier=brazier,
                            recovery_location=location,
                        )
                    if updated.result:
                        participant_quest.progress = progress
                        participant_quest.state_version += 1
            if updated.result:
                await self._settle_campaign_activity(session, locked, updated.result)
            return await self._view(session, character, quest, world)

    async def _settle_campaign_activity(self, session, locked, result: str) -> None:
        from asterion.application.campaign_coop import settle_campaign_encounter

        await settle_campaign_encounter(session, locked, result)

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
    ) -> P5View | None:
        shared = await self.resume(actor)
        if shared is not None and shared.activity_id == activity_id and shared.combat is not None:
            if shared.combat.version != version:
                return replace(shared, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                shared,
                screen=screen,
                item_id=item_id,
                target_id=target_id,
                parent=parent,
            )
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P5_CONTENT_ID,
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
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    async def _materialize(self, session, character, quest):
        if await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session,
            character,
            P5_CONTENT_ID,
            SUNSET_CUSTODIAN,
            9,
            flavor="Uma figura blindada se ergue diante da Porta do Poente.",
            opening_log="🛡️ Custódio do Poente · Nv.9 guarda a estrutura deliberadamente protegida.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{P5_REWARD_SOURCE}:enemy-xp:{activity.id}"
        if await session.scalar(
            select(RewardEvent.id)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == source,
            )
            .with_for_update()
        ):
            return
        amount = enemy_xp(
            9,
            "elite",
            player_level=character.level,
            legacy_factor=legacy_xp_factor(character.legacy_level),
        )
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="enemy_xp",
                item_id=SUNSET_CUSTODIAN.creature_id,
                quantity=amount,
                payload={"enemy_level": 9, "category": "elite"},
            )
        )
        character.xp += amount

    async def _complete(self, session, character, quest):
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P5_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P5_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 7100
            character.crowns += 300
            session.add_all(
                [
                    RewardComponent(
                        reward_event_id=event.id, kind="xp", item_id=None, quantity=7100
                    ),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", item_id=None, quantity=300
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=P5_IRON,
                        quantity=3,
                        payload={"material_id": P5_IRON, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=P5_RESIDUE,
                        quantity=1,
                        payload={"material_id": P5_RESIDUE, "bound": True},
                    ),
                ]
            )
            await self.road.deliver_material(
                session,
                character,
                P5_IRON,
                3,
                f"{P5_REWARD_SOURCE}:material:{P5_IRON}",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                P5_RESIDUE,
                1,
                f"{P5_REWARD_SOURCE}:material:{P5_RESIDUE}",
                bound=True,
            )
        await self._ensure_codex_entry(session, character.id)
        quest.status = "completed"
        quest.progress = {
            **(quest.progress or {}),
            "completed": True,
            "ruins_updated": True,
            "door_known": True,
            "recurring_symbol_recorded": True,
        }
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _view(self, session, character, quest, world, requested_kind=None, *, available=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        stored = progress.get("combat_activity_id")
        try:
            stored_id = UUID(stored) if stored else None
        except (TypeError, ValueError):
            stored_id = None
        actor_key = None
        group_size = 1
        shared = None
        if stored_id is not None:
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, stored_id, character.id
            )
            if shared is not None:
                activity = await session.get(GameActivity, stored_id)
                combat = shared_combat if shared.status == "active" else None
                encounter = shared
                record = None
                actor_key = shared_member.actor_key
                group_size = shared.roster_size
        if stored_id is not None and shared is None:
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == stored_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P5_CONTENT_ID,
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
        status = quest.status if quest else "unaccepted"
        eligible = await self._eligible(session, character)
        can_offer = bool(eligible and quest is None)
        if requested_kind is not None:
            kind = requested_kind
        elif quest is None:
            kind = "offer" if can_offer and self._at(world, REFUGE) else "unavailable"
        elif combat is not None:
            kind = "combat"
        elif status == "completed":
            kind = "completed"
        elif status != "active":
            kind = "unavailable"
        elif quest.step == 3 and progress.get("awaiting_retry"):
            kind = "recovery"
        elif quest.step <= 5 and not self._at(world, RUINS):
            kind = "travel"
        elif quest.step == 1:
            kind = "follow_structures"
        elif quest.step == 2:
            kind = "find_door"
        elif quest.step == 3:
            kind = "combat_pending"
        elif quest.step == 4:
            kind = "elements"
        elif quest.step == 5:
            kind = "record_symbol"
        else:
            kind = "reports" if self._at(world, REFUGE) else "return"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(
                session,
                character,
                combat,
                SUNSET_CUSTODIAN.category,
                actor_key=actor_key,
            )
        return P5View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=bool(available if available is not None else can_offer),
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
            combat_actor_key=actor_key,
            group_size=group_size,
            proposal_id=UUID(progress["group_proposal_id"]) if progress.get("group_proposal_id") else None,
            proposal_status=progress.get("group_proposal_status"),
        )

    async def _eligible(self, session, character):
        return bool(
            character.level >= 9
            and await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == "P4",
                    Quest.status == "completed",
                )
            )
        )

    async def _ensure_codex_entry(self, session, character_id):
        entry = await session.scalar(
            select(CodexEntry)
            .where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == P5_CODEX_ENTRY,
            )
            .with_for_update()
        )
        if entry is None:
            session.add(CodexEntry(character_id=character_id, entry_id=P5_CODEX_ENTRY))
            await session.flush()

    async def _ensure_codex_fragment(self, session, character_id, fragment_id):
        await self._ensure_codex_entry(session, character_id)
        fragment = await session.scalar(
            select(CodexFragment)
            .where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == P5_CODEX_ENTRY,
                CodexFragment.fragment_id == fragment_id,
            )
            .with_for_update()
        )
        if fragment is None:
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=P5_CODEX_ENTRY,
                    fragment_id=fragment_id,
                )
            )
            await session.flush()

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
        quest = await session.scalar(
            select(Quest)
            .where(Quest.character_id == character.id, Quest.quest_id == P5_ID)
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

    async def _quest(self, session, character_id):
        return await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P5_ID)
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
            and quest.content_version == P5_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
