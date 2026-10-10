"""Persistent P6 campaign climax, composed from shared Quest and combat services."""
# ruff: noqa: E501

import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
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
    settle_campaign_encounter,
)
from asterion.application.groups import ActivityEligibility, GroupError, GroupService
from asterion.application.p5 import P5_ID
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
from asterion.domain.road import RUINS_LOCATION, VIGIA_PARTIDO, materialize_equipment
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
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
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    SocialGroupMember,
    Unlock,
    WorldState,
)

P6_ID = "P6"
P6_TITLE = "O Vigia Partido"
P6_VERSION = "tdo-1.0.11"
P6_CONTENT_ID = "p6_scripted_vigia_partido"
P6_REWARD_SOURCE = "p6.o_vigia_partido"
P6_NUCLEUS_SOURCE = "p6.vigia_partido.nucleo:first_victory"
P6_CHAMBER = "Câmara do Poente"
P6_CHAMBER_LOCATION_ID = "tdo.location.camara_do_poente"
P6_CODEX_ANCHOR = "codex.mystery.ancora_do_poente"
P6_CODEX_ANCHOR_FRAGMENTS = (
    "codex.fragment.ancora_do_poente.nome_registrado",
    "codex.fragment.ancora_do_poente.protegida_pelo_vigia",
    "codex.fragment.ancora_do_poente.outras_ancoras",
)
P6_OLD_ASTERIANS = "codex.history.antigos_asterianos"
P6_RUINS_CODEX = "codex.location.ruinas_do_vigia"
P6_CHAMBER_CODEX = "codex.location.camara_do_poente"
P6_RECIPE_UNLOCK = "recipe.tdo.vigia_partido.eco"
P6_CAMPAIGN_UNLOCK = "campaign.tdo.completed"
P6_NUCLEUS = "material.tdo.nucleo_vigia_partido"
P6_IRON = "material.tdo.ferro_de_fuligem"
P6_RESIDUE = "material.tdo.residuo_ocaso"
P6_CHOICES = {
    "last_post": ("Guarda do Último Posto", "Torso"),
    "sunset_seal": ("Selo do Poente", "Acessório"),
    "veiled_reliquary": ("Relicário da Âncora Velada", "Artefato"),
}


@dataclass(frozen=True)
class P6View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p6"
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
    guidance: str | None = None
    xp: int = 0
    combat_actor_key: str | None = None
    group_size: int = 1


class P6Service:
    """Owns the P6 state machine; combat, delivery and progression stay shared."""

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

    async def resume(self, actor: int) -> P6View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._ensure_started(session, character, quest)
            return await self._view(session, character, quest, world)

    async def summary(self, actor: int) -> P6View | None:
        return await self.resume(actor)

    async def action(self, actor: int, version: int, operation: str) -> P6View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._ensure_started(session, character, quest)
            if quest is None:
                return await self._view(session, character, None, world)
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            if operation == "cross_door" and quest.step == 1 and self._at(world, RUINS):
                if not progress.get("door_known"):
                    return await self._view(session, character, quest, world)
                progress["door_crossed"] = True
                quest.step = 2
            elif (
                operation == "enter_chamber"
                and quest.step == 2
                and progress.get("door_crossed")
                and self._at(world, RUINS)
            ):
                world.region, world.location = REGION, P6_CHAMBER
                await self._ensure_location(session, character.id, P6_CHAMBER_LOCATION_ID)
                progress["chamber_discovered"] = True
                quest.step = 3
            elif (
                operation == "enter_chamber"
                and quest.step == 5
                and progress.get("awaiting_retry")
                and self._at(world, RUINS)
            ):
                world.region, world.location = REGION, P6_CHAMBER
                await self._ensure_location(session, character.id, P6_CHAMBER_LOCATION_ID)
            elif operation == "inspect_before" and quest.step == 3 and self._at(world, P6_CHAMBER):
                progress["central_structure_examined_before"] = True
                quest.step = 4
            elif operation == "start_boss" and quest.step == 4 and self._at(world, P6_CHAMBER):
                quest.step = 5
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    quest.step = 4
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif (
                operation == "retry"
                and quest.step == 5
                and progress.get("awaiting_retry")
                and self._at(world, P6_CHAMBER)
            ):
                progress["awaiting_retry"] = False
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    progress["awaiting_retry"] = True
                    quest.progress = progress
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif operation == "inspect_after" and quest.step == 6 and self._at(world, P6_CHAMBER):
                progress["central_structure_examined_after"] = True
                quest.step = 7
            elif operation == "record_anchor" and quest.step == 7 and self._at(world, P6_CHAMBER):
                progress["anchor_name_recorded"] = True
                quest.step = 8
                await self._ensure_codex(session, character.id, P6_CODEX_ANCHOR)
                for fragment in P6_CODEX_ANCHOR_FRAGMENTS:
                    await self._ensure_fragment(session, character.id, P6_CODEX_ANCHOR, fragment)
                await self._ensure_codex(session, character.id, P6_OLD_ASTERIANS)
                await self._ensure_fragment(
                    session,
                    character.id,
                    P6_OLD_ASTERIANS,
                    "codex.fragment.antigos_asterianos.outras_ancoras_existiram",
                )
                await self._ensure_codex(session, character.id, P6_RUINS_CODEX)
                await self._ensure_fragment(
                    session,
                    character.id,
                    P6_RUINS_CODEX,
                    "codex.fragment.ruinas_do_vigia.vigia_protegia_estrutura",
                )
                await self._ensure_codex(session, character.id, P6_CHAMBER_CODEX)
                await self._ensure_fragment(
                    session,
                    character.id,
                    P6_CHAMBER_CODEX,
                    "codex.fragment.camara_do_poente.estrutura_chamada_ancora",
                )
            elif operation == "return_ruins" and quest.step == 8 and self._at(world, P6_CHAMBER):
                world.region, world.location = REGION, RUINS
            elif (
                operation in {"report_alda", "report_oren"}
                and quest.step == 8
                and self._at(world, REFUGE)
            ):
                reports = set(progress.get("reports", ()))
                reports.add("alda" if operation == "report_alda" else "oren")
                progress["reports"] = [key for key in ("alda", "oren") if key in reports]
                if reports == {"alda", "oren"}:
                    quest.step = 9
            else:
                return await self._view(session, character, quest, world)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, version: int):
        if self.groups is None:
            return await self.resume(actor)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            quest = await self._quest(session, character.id) if character else None
            world = await self._world(session, character.id) if character else None
            quest = await self._ensure_started(session, character, quest) if character else None
            if (
                character is None
                or quest is None
                or quest.state_version != version
                or quest.step not in {4, 5}
                or not self._at(world, P6_CHAMBER)
                or (quest.step == 4 and not (quest.progress or {}).get("central_structure_examined_before"))
                or (quest.step == 5 and not (quest.progress or {}).get("awaiting_retry"))
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
            activity_type="campaign_p6",
            participant_character_ids=participants,
            eligibility_resolver=self._p6_combat_eligibility,
            journey_reference_character_id=character.id,
            context_payload={
                "title": P6_TITLE,
                "quest_id": P6_ID,
                "checkpoint": "p6.vigia_partido",
                "location": P6_CHAMBER,
            },
        )
        return await self.resume(actor)

    async def start_group_combat(
        self, actor: int, proposal_id: UUID, *, expected_revision: int
    ):
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._p6_combat_eligibility,
            create_activity=self._create_p6_group_combat,
        )
        return await self.resume(actor)

    async def _p6_combat_eligibility(self, session, character, payload):
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == P6_ID)
        )
        quest = await self._ensure_started(session, character, quest)
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        same_location = self._at(world, payload.get("location")) and payload.get(
            "location"
        ) == P6_CHAMBER
        if active is not None or not same_location or quest is None or quest.content_version != P6_VERSION:
            role = "ineligible"
        elif (
            quest.status == "active"
            and (
                (quest.step == 4 and (quest.progress or {}).get("central_structure_examined_before"))
                or (quest.step == 5 and (quest.progress or {}).get("awaiting_retry"))
            )
        ):
            role = "eligible"
        elif quest.status == "completed" or quest.step > 5:
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
            "active_activity": str(active.id) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
            "level": character.level,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_p6_group_combat(self, session, proposal, characters):
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
            VIGIA_PARTIDO,
            10,
            flavor="O Vigia Partido ergue-se diante da estrutura central.",
            opening_log="⚔️ Vigia Partido · Nv.10 protege a Câmara do Poente.",
        )
        roster = tuple(
            CampaignRosterMember(
                character=character,
                actor_key=campaign_actor_key(index, len(characters)),
                role=roles[character.id],
                checkpoint="p6.vigia_partido",
            )
            for index, character in enumerate(characters, start=1)
        )
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=P6_ID,
            content_id=P6_CONTENT_ID,
            combat=combat,
            ruleset_version=combat.ruleset,
            checkpoint="p6.vigia_partido",
            campaign_boss=True,
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
            quest = await session.scalar(
                select(Quest)
                .where(Quest.character_id == member.character_id, Quest.quest_id == P6_ID)
                .with_for_update()
            )
            if quest is None:
                raise GroupError("eligibility_changed")
            progress = dict(quest.progress or {})
            progress.update(boss_activity_id=str(member.game_activity_id), boss_result=None)
            if member.role == "eligible":
                quest.step = 5
                progress["awaiting_retry"] = False
                quest.state_version += 1
            quest.progress = progress
        return str(encounter.id)

    async def choose_reward(self, actor: int, version: int, choice: str) -> P6View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._ensure_started(session, character, quest)
            if quest is None:
                return await self._view(session, character, None, world)
            if (
                quest.status == "completed"
                or not self._valid(quest, version, step=9)
                or choice not in P6_CHOICES
                or not self._at(world, REFUGE)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            await self._complete(session, character, quest, choice)
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
    ) -> P6View | None:
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
            if character is None:
                return None
            quest = await self._ensure_started(session, character, quest)
            if quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P6_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                not self._valid(quest, quest.state_version, step=5)
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
                category=VIGIA_PARTIDO.category,
            )
            if updated is None or updated.version == version:
                return current

            entry = await self._ensure_bestiary_entry(session, character.id)
            await self.bestiary.record_combat_events(
                session, character.id, VIGIA_PARTIDO.creature_id, None, updated
            )
            enemy = updated.fighters.get("enemy")
            if enemy is not None and enemy.stats.hp > 0:
                hp_fraction = enemy.hp / enemy.stats.hp
                if hp_fraction < 1 and hp_fraction <= Decimal("0.70"):
                    await self.bestiary.add_evidence(
                        session,
                        entry,
                        character.id,
                        VIGIA_PARTIDO.creature_id,
                        "phase:a_fratura",
                        "phase",
                        5,
                    )
                if hp_fraction <= Decimal("0.35"):
                    await self.bestiary.add_evidence(
                        session,
                        entry,
                        character.id,
                        VIGIA_PARTIDO.creature_id,
                        "phase:o_ultimo_posto",
                        "phase",
                        5,
                    )

            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_nucleus_once(session, character)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session,
                    character.id,
                    VIGIA_PARTIDO.creature_id,
                    victory=True,
                    observation_category="boss",
                )
                await self._ensure_achievement(session, character.id, "feat.tdo.a_ultima_guarda")
                progress.update(boss_defeated=True, awaiting_retry=False, boss_result="victory")
                quest.step = 6
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session,
                    character.id,
                    VIGIA_PARTIDO.creature_id,
                    observation_category="boss",
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, RUINS_LOCATION, world
                )
                progress.update(
                    boss_result="defeat",
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
        action, target = intent
        return await self.action_combat(actor, activity_id, version, action, target_id=target)

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
    ):
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _, member_seed, _ = await campaign_combat_for_activity(
                session, activity_id, seed.id
            )
            if member_seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id != P6_ID:
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
                        .where(
                            Quest.character_id.in_(locked.characters), Quest.quest_id == P6_ID
                        )
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
            if (
                locked.encounter.content_id != P6_CONTENT_ID
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
                    VIGIA_PARTIDO.category, 0
                ),
            )
            if updated.version == version:
                return await self._view(session, character, quest, world)
            if stack is not None:
                stack.quantity -= 1
            member_by_character = {row.character_id: row for row in locked.members}
            enemy = updated.fighters.get("enemy")
            for character_id, participant in locked.characters.items():
                roster_member = member_by_character[character_id]
                entry = await self._ensure_bestiary_entry(session, character_id)
                await self.bestiary.record_combat_events(
                    session, character_id, VIGIA_PARTIDO.creature_id, None, updated
                )
                if enemy is not None and enemy.stats.hp > 0:
                    hp_fraction = enemy.hp / enemy.stats.hp
                    if hp_fraction < 1 and hp_fraction <= Decimal("0.70"):
                        await self.bestiary.add_evidence(
                            session, entry, character_id, VIGIA_PARTIDO.creature_id,
                            "phase:a_fratura", "phase", 5,
                        )
                    if hp_fraction <= Decimal("0.35"):
                        await self.bestiary.add_evidence(
                            session, entry, character_id, VIGIA_PARTIDO.creature_id,
                            "phase:o_ultimo_posto", "phase", 5,
                        )
                participant_quest = quests.get(character_id)
                recovery = None
                if updated.result == "victory":
                    await normalize_character_hp(session, participant)
                    await self.bestiary.record(
                        session, character_id, VIGIA_PARTIDO.creature_id,
                        victory=True, observation_category="boss",
                    )
                    await self._ensure_achievement(
                        session, character_id, "feat.tdo.a_ultima_guarda"
                    )
                    if roster_member.role == "eligible":
                        await self._grant_nucleus_once(session, participant)
                        if participant_quest is not None:
                            progress = dict(participant_quest.progress or {})
                            progress.update(
                                boss_defeated=True,
                                awaiting_retry=False,
                                boss_result="victory",
                            )
                            participant_quest.progress = progress
                            participant_quest.step = 6
                            participant_quest.state_version += 1
                elif updated.result == "defeat":
                    participant_world = await self._world(session, character_id)
                    recovery = await self.road.recover_normal_pve_defeat(
                        session, participant, RUINS_LOCATION, participant_world
                    )
                    if roster_member.role == "eligible" and participant_quest is not None:
                        progress = dict(participant_quest.progress or {})
                        progress.update(
                            boss_result="defeat",
                            awaiting_retry=True,
                            defeat_activity_id=str(roster_member.game_activity_id),
                            recovery_brazier=recovery[0] if recovery else None,
                            recovery_location=recovery[1] if recovery else None,
                        )
                        participant_quest.progress = progress
                        participant_quest.state_version += 1
            if updated.result:
                await settle_campaign_encounter(session, locked, updated.result)
            return await self._view(session, character, quest, world)

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, **kwargs
    ) -> P6View | None:
        shared = await self.resume(actor)
        if shared is not None and shared.activity_id == activity_id and shared.combat is not None:
            if shared.combat.version != version:
                return replace(shared, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(shared, **kwargs)
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._ensure_started(session, character, quest)
            if quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P6_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if activity.status != "active" or foreground is None or foreground.id != activity.id:
                return current
            if activity.state_version != version:
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(current, **kwargs)

    async def _ensure_started(self, session, character, quest):
        if quest is not None or character.level < 10:
            return quest
        p5 = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == P5_ID,
                Quest.status == "completed",
            )
        )
        if not p5:
            return None
        p5_quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == P5_ID)
        )
        progress = dict(p5_quest.progress or {}) if p5_quest else {}
        if not progress.get("door_known"):
            return None
        quest = Quest(
            character_id=character.id,
            quest_id=P6_ID,
            title=P6_TITLE,
            status="active",
            step=1,
            content_version=P6_VERSION,
            state_version=0,
            progress={"door_known": bool(progress.get("door_known"))},
        )
        session.add(quest)
        await session.flush()
        return quest

    async def _materialize(self, session, character, quest):
        if await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session,
            character,
            P6_CONTENT_ID,
            VIGIA_PARTIDO,
            10,
            flavor="O Vigia Partido ergue-se diante da estrutura central.",
            opening_log="⚔️ Vigia Partido · Nv.10 protege a Câmara do Poente.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["boss_activity_id"] = str(activity.id)
            progress.update(boss_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_nucleus_once(self, session, character):
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P6_NUCLEUS_SOURCE,
            )
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=P6_NUCLEUS_SOURCE)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="material",
                item_id=P6_NUCLEUS,
                quantity=1,
                payload={"material_id": P6_NUCLEUS, "bound": True, "first_victory": True},
            )
        )
        await self.road.deliver_material(
            session,
            character,
            P6_NUCLEUS,
            1,
            f"{P6_NUCLEUS_SOURCE}:material",
            bound=True,
        )

    async def _complete(self, session, character, quest, choice):
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P6_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            name, slot = P6_CHOICES[choice]
            payload = materialize_equipment(
                f"{P6_REWARD_SOURCE}:{character.id}:{choice}",
                "Épico",
                10,
                forced_name=name,
                forced_slot=slot,
                bound=True,
            )
            event = RewardEvent(character_id=character.id, source_id=P6_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 14220
            character.crowns += 500
            components = [
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=14220),
                RewardComponent(
                    reward_event_id=event.id, kind="crowns", item_id=None, quantity=500
                ),
                RewardComponent(
                    reward_event_id=event.id,
                    kind="equipment",
                    item_id=None,
                    quantity=1,
                    payload=payload | {"choice": choice},
                ),
                RewardComponent(
                    reward_event_id=event.id,
                    kind="material",
                    item_id=P6_IRON,
                    quantity=4,
                    payload={"material_id": P6_IRON, "bound": True},
                ),
                RewardComponent(
                    reward_event_id=event.id,
                    kind="material",
                    item_id=P6_RESIDUE,
                    quantity=4,
                    payload={"material_id": P6_RESIDUE, "bound": True},
                ),
            ]
            session.add_all(components)
            await self.road.deliver_material(
                session, character, P6_IRON, 4, f"{P6_REWARD_SOURCE}:material:{P6_IRON}", bound=True
            )
            await self.road.deliver_material(
                session,
                character,
                P6_RESIDUE,
                4,
                f"{P6_REWARD_SOURCE}:material:{P6_RESIDUE}",
                bound=True,
            )
            source_key = f"{P6_REWARD_SOURCE}:equipment:{choice}"
            if await self.road._inventory_slots(session, character.id) < 60:
                from asterion.application.equipment import equipment_instance_payload

                item_id, instance = equipment_instance_payload(payload)
                session.add(
                    EquipmentItem(
                        id=item_id,
                        character_id=character.id,
                        source_key=source_key,
                        item_name=instance["item_name"],
                        rarity=instance["rarity"],
                        slot=instance["slot"],
                        item_level=instance["item_level"],
                        bound=True,
                        payload=instance,
                    )
                )
            else:
                await self.road._pending(session, character.id, source_key, "equipment", payload)

        await self._ensure_codex(session, character.id, P6_OLD_ASTERIANS)
        await self._ensure_codex(session, character.id, P6_RUINS_CODEX)
        await self._ensure_codex(session, character.id, P6_CODEX_ANCHOR)
        await self._ensure_unlock(session, character.id, P6_RECIPE_UNLOCK)
        await self._ensure_unlock(session, character.id, P6_CAMPAIGN_UNLOCK)
        await self._ensure_achievement(session, character.id, "feat.tdo.campaign.completed")
        quest.status = "completed"
        quest.step = 9
        quest.progress = {**(quest.progress or {}), "completed": True, "reward_choice": choice}
        quest.state_version += 1
        entry = await self._ensure_bestiary_entry(session, character.id)
        await self.bestiary.add_evidence(
            session,
            entry,
            character.id,
            VIGIA_PARTIDO.creature_id,
            "p6_completed",
            "campaign",
            5,
        )
        await self.bestiary.refresh_boss_mastery(session, character.id, VIGIA_PARTIDO.creature_id)
        await consolidate_character_level(session, character)
        await self._award_regional_completion_if_eligible(session, character.id, character.level)
        from asterion.application.tdo_feats import reconcile_tdo_feats

        await reconcile_tdo_feats(session, character)

    async def _award_regional_completion_if_eligible(self, session, character_id, level):
        if level < 10:
            return
        required = {
            "tdo.location.estrada_das_cinzas",
            "tdo.location.refugio_do_ocaso",
            "tdo.location.charneca_da_fuligem",
            "tdo.location.bosque_calcinado",
            "tdo.location.ruinas_do_vigia",
        }
        found = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character_id,
                    )
                )
            ).all()
        )
        if required.issubset(found):
            await self._ensure_achievement(session, character_id, "feat.tdo.terras_do_ocaso")

    async def _view(self, session, character, quest, world, requested_kind=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        try:
            activity_id = (
                UUID(progress.get("boss_activity_id")) if progress.get("boss_activity_id") else None
            )
        except (TypeError, ValueError):
            activity_id = None
        actor_key = None
        group_size = 1
        shared = None
        if activity_id is not None:
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if shared is not None:
                activity = await session.get(GameActivity, activity_id)
                combat = shared_combat if shared.status == "active" else None
                encounter = shared
                record = None
                actor_key = shared_member.actor_key
                group_size = shared.roster_size
        if activity_id is not None and shared is None:
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P6_CONTENT_ID,
                )
            )
            if activity is not None:
                row = (
                    await session.execute(
                        select(Encounter, CombatRecord)
                        .join(CombatRecord)
                        .where(
                            Encounter.game_activity_id == activity.id,
                        )
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
        if requested_kind is not None:
            kind = requested_kind
        elif quest is None:
            kind = "unavailable"
        elif combat is not None:
            kind = "combat"
        elif quest.status == "completed":
            kind = "completed"
        elif quest.step == 5 and progress.get("awaiting_retry"):
            kind = (
                "retry"
                if self._at(world, P6_CHAMBER)
                else "retry_chamber"
                if self._at(world, RUINS)
                else "retry_travel"
            )
        elif quest.step == 1:
            kind = "cross_door" if self._at(world, RUINS) else "travel_ruins"
        elif quest.step == 2:
            kind = "enter_chamber" if self._at(world, RUINS) else "travel_chamber"
        elif quest.step in {3, 4}:
            kind = (
                "inspect_before"
                if quest.step == 3 and self._at(world, P6_CHAMBER)
                else "start_boss"
                if quest.step == 4 and self._at(world, P6_CHAMBER)
                else "travel_chamber"
            )
        elif quest.step in {6, 7}:
            kind = "inspect_after" if quest.step == 6 else "record_anchor"
        elif quest.step == 8:
            kind = (
                "reports"
                if self._at(world, REFUGE)
                else "return_refuge"
                if self._at(world, RUINS)
                else "return_ruins"
            )
        elif quest.step == 9:
            kind = "choose_reward"
        else:
            kind = "unavailable"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(
                session, character, combat, VIGIA_PARTIDO.category, actor_key=actor_key
            )
        guidance = await self._journey_guidance(session, character)
        return P6View(
            character_id=character.id,
            kind=kind,
            status=quest.status if quest else None,
            step=quest.step if quest else None,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=quest is not None and quest.status == "active",
            combat=combat,
            activity_id=activity.id if activity else None,
            activity_state_version=activity.state_version if activity else None,
            activity_status=activity.status if activity else None,
            encounter_id=encounter.id if encounter else None,
            combat_id=record.id if record else None,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            guidance=guidance,
            xp=character.xp,
            combat_actor_key=actor_key,
            group_size=group_size,
        )

    async def _journey_guidance(self, session, character):
        from asterion.domain.talents import TALENT_POINT_LEVELS
        from asterion.infrastructure.db.models import CharacterTalentChoice, ClassTrialState

        points_due = sum(level <= character.level for level in TALENT_POINT_LEVELS)
        spent = (
            await session.scalar(
                select(func.count())
                .select_from(CharacterTalentChoice)
                .where(CharacterTalentChoice.character_id == character.id)
            )
            or 0
        )
        if spent < points_due:
            return "talents"
        trial = await session.scalar(
            select(ClassTrialState).where(ClassTrialState.character_id == character.id)
        )
        if trial is None or trial.status != "completed":
            return "trial"
        if character.selected_path is None:
            return "path"
        return None

    async def _ensure_bestiary_entry(self, session, character_id):
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == VIGIA_PARTIDO.creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            await self.bestiary.record(
                session, character_id, VIGIA_PARTIDO.creature_id, observation_category="boss"
            )
            entry = await session.scalar(
                select(BestiaryEntry)
                .where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id == VIGIA_PARTIDO.creature_id,
                )
                .with_for_update()
            )
        return entry

    async def _ensure_location(self, session, character_id, location_id):
        found = await session.scalar(
            select(LocationDiscovery)
            .where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == location_id,
            )
            .with_for_update()
        )
        if found is None:
            session.add(LocationDiscovery(character_id=character_id, location_id=location_id))

    async def _ensure_codex(self, session, character_id, entry_id):
        found = await session.scalar(
            select(CodexEntry)
            .where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == entry_id,
            )
            .with_for_update()
        )
        if found is None:
            session.add(CodexEntry(character_id=character_id, entry_id=entry_id))

    async def _ensure_fragment(self, session, character_id, entry_id, fragment_id):
        await self._ensure_codex(session, character_id, entry_id)
        found = await session.scalar(
            select(CodexFragment)
            .where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == entry_id,
                CodexFragment.fragment_id == fragment_id,
            )
            .with_for_update()
        )
        if found is None:
            session.add(
                CodexFragment(character_id=character_id, entry_id=entry_id, fragment_id=fragment_id)
            )

    async def _ensure_unlock(self, session, character_id, unlock_id):
        found = await session.scalar(
            select(Unlock)
            .where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == unlock_id,
            )
            .with_for_update()
        )
        if found is None:
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))

    async def _ensure_achievement(self, session, character_id, achievement_id):
        found = await session.scalar(
            select(Achievement)
            .where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == achievement_id,
            )
            .with_for_update()
        )
        if found is None:
            session.add(Achievement(character_id=character_id, achievement_id=achievement_id))

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
            .where(
                Quest.character_id == character.id,
                Quest.quest_id == P6_ID,
            )
            .with_for_update()
        )
        world = await session.scalar(
            select(WorldState)
            .where(
                WorldState.character_id == character.id,
            )
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
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P6_ID,
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
            and quest.content_version == P6_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
