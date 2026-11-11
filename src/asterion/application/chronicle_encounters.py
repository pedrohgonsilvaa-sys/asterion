"""Encontros da Crônica I: ``[Enfrentar]`` and ``[Enfrentar o Eco de novo]`` (§11.1, §8).

The fight happens in the Local de Ressonância, at the character's level held inside the
band of the Região de Ressonância and frozen when the encounter is created: a retry after
a defeat reuses that level. The first victory pays the normal enemy XP once per character
and registers the objective; a repeated victory pays only the Trilha. Nothing here grants
Coroas, Materiais, Saque, Equipamento or Vigor, and a defeat costs nothing.

``pr_cr01_encontro_grupo``: an Encontro may also be fought by a Group of 1–4 after the
60s Confirmação de Entrada (GDD §51.2). Everyone must be in the Local de Ressonância of
the Personagem de Referência; the level is the Reference's. A member with the same
objective active and the same Região de Ressonância is ``eligible``; anyone else present
is a ``helper`` and counts for nothing (author decision on Dúvida 11). Only the Chefes
scale with the Group, with the Campaign boss scaling (GDD §51.5).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
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
from asterion.application.chronicle import (
    ChronicleError,
    calendar_of,
    completed_quests,
    load_cycle,
    record_objective,
    record_repeatable,
    repeatable_available,
)
from asterion.application.chronicle_activities import LatestLocal, Route, _flags, _Resolver
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.groups import (
    ActivityEligibility,
    ActivityProposalView,
    GroupError,
    GroupService,
)
from asterion.application.prologue import CombatView
from asterion.application.scripted_combat import (
    ENCOUNTER_CONSUMABLE_LIMITS,
    apply_action,
    consumable_state,
    current_combat,
    derive_consumable_selection,
    normalize_character_hp,
)
from asterion.domain.chronicle import (
    ENTRY_GATE_QUEST,
    OBJECTIVES_BY_ID,
    Calendar,
    Objective,
    objectives_of,
)
from asterion.domain.chronicle_encounters import (
    ENCOUNTER_SOURCE,
    ENCOUNTERS_BY_CONTENT,
    ENCOUNTERS_BY_OBJECTIVE,
    FEAT_NAMES,
    Encounter,
    configure_encounter,
    encounter_level,
    enemy_specs,
    scene_text,
)
from asterion.domain.combat import Combat
from asterion.domain.legacy import legacy_xp_factor
from asterion.domain.road import (
    RULESET,
    PlayerCombatantSpec,
    create_creature_party_combat,
    enemy_xp,
)
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Achievement,
    CampaignSharedEncounterMember,
    Character,
    ConsumableStack,
    GameActivity,
    GroupActivityParticipant,
    GroupActivityProposal,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    SocialGroupMember,
    WorldState,
)

CONTEXT = "chronicle"
GROUP_ACTIVITY_TYPE = "chronicle_encounter"
GROUP_QUEST_ID = "chronicle.cr01"

# (session, character, local_id, world) -> (brazier name, location) or (None, None).
RecoverDefeat = Callable[..., Awaitable[tuple[str | None, str | None]]]


@dataclass(frozen=True, slots=True)
class EncounterActionView:
    """One Encontro of an open chapter, for the chapter screen and the Local."""

    objective: Objective
    encounter: Encounter
    location: str
    here: bool
    level_locked: bool
    won: bool
    repeat_open: bool
    in_group: bool = False


@dataclass(frozen=True, slots=True)
class EncounterResultView:
    encounter: Encounter
    objective: Objective
    victory: bool
    repeat: bool
    enemy_level: int
    xp: int = 0
    objective_completed: bool = False
    trail_points: int = 0
    feat: str | None = None
    bestiary_stage: str | None = None
    recovery_location: str | None = None
    helper: bool = False
    context: str = CONTEXT


@dataclass(frozen=True, slots=True)
class _Scope:
    character: Character
    calendar: Calendar
    route: Route
    world: WorldState | None
    done: set[str]


class ChronicleEncounterService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        latest_local: LatestLocal,
        recover_defeat: RecoverDefeat,
        groups: GroupService | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        self.sessions, self.server_id = sessions, server_id
        self.latest_local, self.recover_defeat = latest_local, recover_defeat
        self.groups = groups
        # The Group eligibility resolver has no ``now``: it reads this clock.
        self.clock = clock or (lambda: datetime.now(UTC))
        self.bestiary = BestiaryRecorder()

    # ------------------------------------------------------------------ reads

    async def encounters(
        self, actor: int, *, now: datetime | None = None
    ) -> tuple[EncounterActionView, ...]:
        """The Encontros of every open chapter (empty while the Crônica is closed)."""
        moment = now or self.clock()
        async with self.sessions() as session:
            character = await session.scalar(self._character_query(actor))
            if character is None:
                return ()
            scope = await self._scope(session, character, moment)
            if scope is None:
                return ()
            repeat_open = await repeatable_available(
                session, character, ENCOUNTER_SOURCE, scope.calendar, moment
            )
            label = scope.route.local_label
            here = scope.world is not None and scope.world.location == label
            in_group = await self._group_size(session, character) > 1
            result = []
            for chapter in range(1, scope.calendar.chapters_open(moment) + 1):
                for objective in objectives_of(chapter):
                    encounter = ENCOUNTERS_BY_OBJECTIVE.get(objective.objective_id)
                    if encounter is None:
                        continue
                    result.append(
                        EncounterActionView(
                            objective,
                            encounter,
                            label,
                            here,
                            character.level < objective.min_level,
                            objective.objective_id in scope.done,
                            repeat_open,
                            in_group,
                        )
                    )
            return tuple(result)

    async def here(
        self, actor: int, *, now: datetime | None = None
    ) -> tuple[EncounterActionView, ...]:
        """What can be fought from the current Local right now."""
        return tuple(
            item
            for item in await self.encounters(actor, now=now)
            if item.here and not item.level_locked and (not item.won or item.repeat_open)
        )

    async def foreground(self, actor: int) -> CombatView | None:
        """The Encontro in progress, so /start and /menu return to it."""
        async with self.sessions() as session:
            character = await session.scalar(self._character_query(actor))
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == character.id,
                    GameActivity.status == "active",
                )
            )
            if activity is None or activity.content_id not in ENCOUNTERS_BY_CONTENT:
                return None
            return await self._combat_view(session, character, activity)

    # ----------------------------------------------------------------- writes

    async def start(
        self, actor: int, chapter: int, slot: int, *, now: datetime | None = None
    ) -> CombatView | EncounterResultView:
        moment = now or self.clock()
        async with self.sessions.begin() as session:
            character = await session.scalar(self._character_query(actor).with_for_update())
            if character is None:
                raise ChronicleError("no_character")
            encounter, scope, content_id = await self._startable(
                session, character, chapter, slot, moment
            )
            level, flavor = await self._level_and_scene(
                session, character, encounter, scope, content_id
            )
            activity, combat = await self._materialize(
                session, character, encounter, content_id, level, flavor
            )
            return await self._after(session, character, activity, encounter, combat, moment)

    # ------------------------------------------------------------ Group fight

    async def propose_group(
        self, actor: int, chapter: int, slot: int, *, now: datetime | None = None
    ) -> CombatView | EncounterResultView | ActivityProposalView:
        """Send the 60s Confirmação de Entrada to the Group, or fight Solo without one."""
        moment = now or self.clock()
        if self.groups is None:
            return await self.start(actor, chapter, slot, now=moment)
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start(actor, chapter, slot, now=moment)
        async with self.sessions() as session:
            character = await session.scalar(self._character_query(actor))
            if character is None:
                raise ChronicleError("no_character")
            encounter, scope, content_id = await self._startable(
                session, character, chapter, slot, moment
            )
            level, flavor = await self._level_and_scene(
                session, character, encounter, scope, content_id
            )
            payload = {
                "objective_id": encounter.objective_id,
                "content_id": content_id,
                "local": scope.route.local_label,
                "region": scope.route.region.name,
                "level": level,
                "flavor": flavor,
                "repeat": content_id == encounter.repeat_content_id,
                "reference_character_id": str(character.id),
                "title": f"Crônica · {encounter.creature.name}",
            }
            reference_id = character.id
        try:
            return await self.groups.propose_activity(
                actor,
                activity_type=GROUP_ACTIVITY_TYPE,
                participant_character_ids=tuple(item.character_id for item in group.members),
                eligibility_resolver=self.eligibility,
                context_payload=payload,
                journey_reference_character_id=reference_id,
                now=moment,
            )
        except GroupError as exc:
            raise ChronicleError(f"group_{exc.code}") from exc

    async def start_group(
        self, actor: int, proposal_id: UUID, *, expected_revision: int
    ) -> CombatView | EncounterResultView | None:
        """Commit a confirmed proposal; eligibility is checked again inside the commit."""
        if self.groups is None:
            return None
        result = await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self.eligibility,
            create_activity=self.create_group_activity,
            now=self.clock(),
        )
        if not result.started:
            return None
        return await self.foreground(actor)

    async def eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        """Present in the Reference's Local, not busy; ``eligible`` or ``helper`` (§11.1)."""
        moment = self.clock()
        world = await session.get(WorldState, character.id)
        active = await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character.id, GameActivity.status == "active"
            )
        )
        objective = OBJECTIVES_BY_ID.get(str(payload.get("objective_id")))
        here = world is not None and world.location == payload.get("local")
        if active is not None or not here or objective is None:
            role = "ineligible"
        else:
            role = "helper"
            scope = await self._scope(session, character, moment)
            if (
                scope is not None
                and scope.route.region.name == payload.get("region")
                and character.level >= objective.min_level
            ):
                won = objective.objective_id in scope.done
                if payload.get("repeat"):
                    if won and await repeatable_available(
                        session, character, ENCOUNTER_SOURCE, scope.calendar, moment
                    ):
                        role = "eligible"
                elif not won:
                    role = "eligible"
        snapshot = {
            "character_id": str(character.id),
            "role": role,
            "location": None if world is None else world.location,
            "level": character.level,
            "active_activity": None if active is None else str(active),
            "combat_configuration_version": character.combat_configuration_version,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def create_group_activity(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
        characters: Sequence[Character],
    ) -> str:
        payload = proposal.context_payload
        content_id = str(payload["content_id"])
        encounter = ENCOUNTERS_BY_CONTENT[content_id]
        rows = {
            row.character_id: row
            for row in (
                await session.scalars(
                    select(GroupActivityParticipant).where(
                        GroupActivityParticipant.proposal_id == proposal.id
                    )
                )
            ).all()
        }
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        roster = []
        for index, character in enumerate(characters, start=1):
            row = rows.get(character.id)
            if row is None or row.eligibility not in {"eligible", "helper"}:
                raise GroupError("eligibility_changed")
            roster.append(
                CampaignRosterMember(
                    character,
                    campaign_actor_key(index, len(characters)),
                    row.eligibility,
                    content_id,
                )
            )
        combat = await self._party_combat(
            session, roster, encounter, int(payload["level"]), str(payload.get("flavor") or "")
        )
        shared = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=GROUP_QUEST_ID,
            content_id=content_id,
            combat=combat,
            ruleset_version=combat.ruleset,
            checkpoint=content_id,
            campaign_boss=encounter.boss,
        )
        for member in roster:
            fighter = combat.fighters.get(member.actor_key)
            if fighter is not None:
                member.character.hp = fighter.hp
        return str(shared.id)

    async def _party_combat(
        self,
        session: AsyncSession,
        roster: Sequence[CampaignRosterMember],
        encounter: Encounter,
        level: int,
        flavor: str,
    ) -> Combat:
        party = []
        for member in roster:
            character = member.character
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment)
            party.append(
                PlayerCombatantSpec(
                    fighter_key=member.actor_key,
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
        lead = roster[0].character
        creature = encounter.creature
        return create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            enemy_specs(creature, level, len(roster)),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor=flavor,
            opening_log=f"🌌 {creature.name} · Nv.{level} se ergue durante o pulso.",
            active_art_ids=party[0].active_art_ids,
            party=tuple(party),
            configure_combat=configure_encounter,
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
        now: datetime | None = None,
    ) -> CombatView | EncounterResultView | None:
        """One combat intent. ``None`` when the activity is not an Encontro of this actor."""
        moment = now or self.clock()
        async with self.sessions.begin() as session:
            seed = await session.scalar(self._character_query(actor))
            if seed is not None and await self._shared_member(session, activity_id, seed.id):
                return await self._shared_action(
                    session,
                    seed,
                    activity_id,
                    version,
                    action=action,
                    consumable_id=consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    now=moment,
                )
            character, activity = await self._locked(session, actor, activity_id)
            if character is None or activity is None or activity.status != "active":
                return None
            encounter = ENCOUNTERS_BY_CONTENT[activity.content_id]
            if activity.state_version != version or (action is None) == (consumable_id is None):
                return await self._combat_view(session, character, activity)
            updated = await apply_action(
                session,
                character,
                activity,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                category=encounter.creature.category,
            )
            if updated is None:
                return await self._combat_view(session, character, activity)
            await self.bestiary.record_combat_events(
                session, character.id, encounter.creature.creature_id, None, updated
            )
            return await self._after(session, character, activity, encounter, updated, moment)

    async def intent(
        self, actor: int, activity_id: UUID, version: int, index: int, target_code: str
    ) -> CombatView | EncounterResultView | None:
        """An action chosen by index and target (Chefe with add, or a Group fight)."""
        async with self.sessions() as session:
            character = await session.scalar(self._character_query(actor))
            activity = None if character is None else await session.get(GameActivity, activity_id)
            if (
                character is None
                or activity is None
                or activity.character_id != character.id
                or activity.content_id not in ENCOUNTERS_BY_CONTENT
            ):
                return None
            combat, actor_key = await self._snapshot(session, character, activity)
        if combat is None:
            return None
        resolved = campaign_action_intent(combat, actor_key, index, target_code)
        if resolved is None:
            return await self.action(actor, activity_id, -1, "refresh")
        action, target_id = resolved
        return await self.action(actor, activity_id, version, action, target_id=target_id)

    async def consume_for_activity(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        item_id: str,
        target_id: str | None,
        effect_id: str | None,
    ) -> CombatView | EncounterResultView | None:
        return await self.action(
            actor,
            activity_id,
            version,
            consumable_id=item_id,
            target_id=target_id,
            effect_id=effect_id,
        )

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
    ) -> CombatView | None:
        async with self.sessions.begin() as session:
            character, activity = await self._locked(session, actor, activity_id)
            if character is None or activity is None or activity.status != "active":
                return None
            current = await self._combat_view(session, character, activity)
            if activity.state_version != version:
                return current
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    # ---------------------------------------------------------------- helpers

    def _character_query(self, actor: int):
        return select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )

    async def _locked(self, session: AsyncSession, actor: int, activity_id: UUID):
        character = await session.scalar(self._character_query(actor).with_for_update())
        if character is None:
            return None, None
        activity = await session.scalar(
            select(GameActivity)
            .where(GameActivity.id == activity_id, GameActivity.character_id == character.id)
            .with_for_update()
        )
        if activity is None or activity.content_id not in ENCOUNTERS_BY_CONTENT:
            return character, None
        return character, activity

    async def _scope(
        self, session: AsyncSession, character: Character, now: datetime
    ) -> _Scope | None:
        cycle = await load_cycle(session, self.server_id)
        if cycle is None:
            return None
        calendar = calendar_of(cycle)
        if not calendar.accepts_progress(now):
            return None
        if ENTRY_GATE_QUEST not in await completed_quests(session, character.id):
            return None
        route = await _Resolver(session, character, self.latest_local).resonance()
        if route is None:
            return None
        world = await session.get(WorldState, character.id)
        return _Scope(character, calendar, route, world, await _flags(session, character))

    async def _startable(
        self,
        session: AsyncSession,
        character: Character,
        chapter: int,
        slot: int,
        moment: datetime,
    ) -> tuple[Encounter, _Scope, str]:
        """Every check of ``[Enfrentar]``; returns the encounter, scope and content id."""
        objective = OBJECTIVES_BY_ID.get(f"cap_{chapter:02d}_obj_{slot:02d}")
        encounter = (
            None if objective is None else ENCOUNTERS_BY_OBJECTIVE.get(objective.objective_id)
        )
        if objective is None or encounter is None:
            raise ChronicleError("chronicle_unknown")
        cycle = await load_cycle(session, self.server_id)
        if cycle is None or not calendar_of(cycle).accepts_progress(moment):
            raise ChronicleError("chronicle_closed")
        if calendar_of(cycle).chapter_opens_at(chapter) > moment:
            raise ChronicleError("chronicle_chapter_locked")
        scope = await self._scope(session, character, moment)
        if scope is None:
            raise ChronicleError("chronicle_gate")
        if character.level < objective.min_level:
            raise ChronicleError("chronicle_level")
        if scope.world is None or scope.world.location != scope.route.local_label:
            raise ChronicleError("chronicle_not_here")
        if await self._busy(session, character):
            raise ChronicleError("chronicle_busy")
        repeat = objective.objective_id in scope.done
        if repeat and not await repeatable_available(
            session, character, ENCOUNTER_SOURCE, scope.calendar, moment
        ):
            raise ChronicleError("chronicle_repeat_limit")
        content_id = encounter.repeat_content_id if repeat else encounter.content_id
        return encounter, scope, content_id

    async def _level_and_scene(
        self,
        session: AsyncSession,
        character: Character,
        encounter: Encounter,
        scope: _Scope,
        content_id: str,
    ) -> tuple[int, str]:
        level, flavor = await self._frozen(session, character, content_id)
        if level is None:
            level = encounter_level(character.level, scope.route.region.name)
            flavor = scene_text(encounter, scope.route.region.name)
        return level, flavor or ""

    @staticmethod
    async def _group_size(session: AsyncSession, character: Character) -> int:
        membership = await session.get(SocialGroupMember, character.id)
        if membership is None:
            return 0
        return int(
            await session.scalar(
                select(func.count())
                .select_from(SocialGroupMember)
                .where(SocialGroupMember.group_id == membership.group_id)
            )
            or 0
        )

    @staticmethod
    async def _shared_member(
        session: AsyncSession, activity_id: UUID, character_id: UUID
    ) -> CampaignSharedEncounterMember | None:
        return await session.scalar(
            select(CampaignSharedEncounterMember).where(
                CampaignSharedEncounterMember.game_activity_id == activity_id,
                CampaignSharedEncounterMember.character_id == character_id,
            )
        )

    @staticmethod
    async def _snapshot(
        session: AsyncSession, character: Character, activity: GameActivity
    ) -> tuple[Combat | None, str]:
        """The combat of a Solo or a Group activity, and this character's fighter key."""
        _, member, combat = await campaign_combat_for_activity(session, activity.id, character.id)
        if member is not None:
            return combat, member.actor_key
        combat, _, _ = await current_combat(session, activity)
        return combat, "player"

    async def _shared_action(
        self,
        session: AsyncSession,
        seed: Character,
        activity_id: UUID,
        version: int,
        *,
        action: str | None,
        consumable_id: str | None,
        target_id: str | None,
        effect_id: str | None,
        now: datetime,
    ) -> CombatView | EncounterResultView | None:
        locked = await lock_campaign_encounter(session, activity_id, seed.id)
        if locked is None or locked.encounter.content_id not in ENCOUNTERS_BY_CONTENT:
            return None
        character = locked.characters[seed.id]
        activity = locked.activities[activity_id]
        if activity.status != "active":
            return None
        encounter = ENCOUNTERS_BY_CONTENT[locked.encounter.content_id]
        if (action is None) == (consumable_id is None) or version != activity.state_version:
            return await self._combat_view(session, character, activity)
        stack = None
        budget = ENCOUNTER_CONSUMABLE_LIMITS.get(encounter.creature.category, 0)
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
                return await self._combat_view(session, character, activity)
        before = locked.combat.version
        updated = resolve_campaign_action(
            locked,
            activity_id=activity_id,
            version=version,
            action=action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
            consumable_budget=budget,
        )
        if updated.version == before:
            return await self._combat_view(session, character, activity)
        if stack is not None:
            stack.quantity -= 1
        counted = {row.character_id for row in locked.members if row.role == "eligible"}
        for character_id in sorted(counted):
            await self.bestiary.record_combat_events(
                session, character_id, encounter.creature.creature_id, None, updated
            )
        if not updated.result:
            return await self._combat_view(session, character, activity)
        mine = None
        for row in sorted(locked.members, key=lambda item: item.character_id):
            member_character = locked.characters[row.character_id]
            result = await self._settle(
                session,
                member_character,
                locked.activities[row.game_activity_id],
                encounter,
                updated,
                now,
                counts=row.role == "eligible",
            )
            row.settlement_state = "settled"
            if row.character_id == seed.id:
                mine = result
        await settle_campaign_encounter(session, locked, updated.result)
        return mine

    @staticmethod
    async def _busy(session: AsyncSession, character: Character) -> bool:
        active = await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character.id, GameActivity.status == "active"
            )
        )
        if active is not None:
            return True
        reserved = await session.scalar(
            select(GroupActivityParticipant.character_id).where(
                GroupActivityParticipant.character_id == character.id,
                GroupActivityParticipant.reservation_state == "active",
            )
        )
        return reserved is not None

    @staticmethod
    async def _frozen(
        session: AsyncSession, character: Character, content_id: str
    ) -> tuple[int | None, str | None]:
        """Level and scene of the encounter lost last time: it is preserved (§11.1.8)."""
        last = await session.scalar(
            select(GameActivity)
            .where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == content_id,
            )
            .order_by(GameActivity.last_valid_action_at.desc(), GameActivity.id.desc())
            .limit(1)
        )
        if last is None or last.status != "failed":
            return None, None
        combat, _ = await ChronicleEncounterService._snapshot(session, character, last)
        if combat is None:
            return None, None
        return combat.fighters["enemy"].level, combat.flavor

    @staticmethod
    async def _materialize(
        session: AsyncSession,
        character: Character,
        encounter: Encounter,
        content_id: str,
        level: int,
        flavor: str,
    ) -> tuple[GameActivity, Combat]:
        configuration = await load_equipment_configuration(session, character)
        arts = await load_active_art_configuration(session, character)
        reconcile_character_hp(character, configuration)
        creature = encounter.creature
        combat = create_creature_party_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            character.hp,
            enemy_specs(creature, level),
            player_level=character.level,
            equipment_configuration=configuration,
            ruleset_version=RULESET,
            flavor=flavor,
            opening_log=f"🌌 {creature.name} · Nv.{level} se ergue durante o pulso.",
            active_art_ids=arts.art_ids,
            configure_combat=configure_encounter,
        )
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | arts.to_data()
        activity, _, _ = await CombatRepository(session).create(character, content_id, combat)
        character.hp = combat.fighters["player"].hp
        return activity, combat

    async def _combat_view(
        self, session: AsyncSession, character: Character, activity: GameActivity
    ) -> CombatView:
        category = ENCOUNTERS_BY_CONTENT[activity.content_id].creature.category
        shared, member, shared_combat = await campaign_combat_for_activity(
            session, activity.id, character.id
        )
        if member is not None and shared is not None and shared_combat is not None:
            options, quantities, budget = await consumable_state(
                session, character, shared_combat, category, actor_key=member.actor_key
            )
            return CombatView(
                activity.id,
                shared.id,
                character.id,
                shared_combat,
                character.stage,
                character.xp,
                CONTEXT,
                consumable_options=options,
                consumable_quantities=quantities,
                consumable_budget_limit=budget,
                combat_actor_key=member.actor_key,
                campaign_shared=True,
            )
        combat, encounter_row, _ = await current_combat(session, activity)
        options, quantities, budget = await consumable_state(session, character, combat, category)
        return CombatView(
            activity.id,
            encounter_row.id,
            character.id,
            combat,
            character.stage,
            character.xp,
            CONTEXT,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
        )

    async def _after(
        self,
        session: AsyncSession,
        character: Character,
        activity: GameActivity,
        encounter: Encounter,
        combat: Combat,
        now: datetime,
    ) -> CombatView | EncounterResultView:
        if combat.result not in ("victory", "defeat"):
            return await self._combat_view(session, character, activity)
        activity.status = "completed" if combat.result == "victory" else "failed"
        return await self._settle(
            session, character, activity, encounter, combat, now, counts=True
        )

    async def _settle(
        self,
        session: AsyncSession,
        character: Character,
        activity: GameActivity,
        encounter: Encounter,
        combat: Combat,
        now: datetime,
        *,
        counts: bool,
    ) -> EncounterResultView:
        """One character's result. A helper (``counts=False``) gets nothing but HP back."""
        creature = encounter.creature
        objective = OBJECTIVES_BY_ID[encounter.objective_id]
        repeat = activity.content_id == encounter.repeat_content_id
        level = combat.fighters["enemy"].level
        elite = creature.category in ("elite", "boss")
        if combat.result == "defeat":
            if counts:
                    await self.bestiary.record(
                    session,
                    character.id,
                    creature.creature_id,
                    elite=elite,
                    observation_category=creature.category,
                )
            route = await _Resolver(session, character, self.latest_local).resonance()
            world = await session.get(WorldState, character.id, with_for_update=True)
            _, location = await self.recover_defeat(
                session, character, None if route is None else route.local_id, world
            )
            return EncounterResultView(
                encounter, objective, False, repeat, level, recovery_location=location
            )
        await normalize_character_hp(session, character)
        if not counts:
            return EncounterResultView(encounter, objective, True, repeat, level, helper=True)
        xp = 0 if repeat else await self._grant_first_xp(session, character, encounter, level)
        notice = await self.bestiary.record(
            session,
            character.id,
            creature.creature_id,
            victory=True,
            elite=elite,
            observation_category=creature.category,
        )
        completed, points, feat = False, 0, None
        if repeat:
            points = await record_repeatable(
                session, self.server_id, character, ENCOUNTER_SOURCE, activity.id.hex, now=now
            )
        else:
            completed = await record_objective(
                session, self.server_id, character, encounter.objective_id, now=now
            )
            feat = await self._grant_feat(session, character, encounter)
        return EncounterResultView(
            encounter,
            objective,
            True,
            repeat,
            level,
            xp=xp,
            objective_completed=completed,
            trail_points=points,
            feat=feat,
            bestiary_stage=None if notice is None else notice["stage_label"],
        )

    @staticmethod
    async def _grant_first_xp(
        session: AsyncSession, character: Character, encounter: Encounter, level: int
    ) -> int:
        """Normal enemy XP (GDD §49.7), once per character per encounter (§11.1.7)."""
        source = f"chronicle:{encounter.encounter_id}:first-victory"
        if await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id, RewardEvent.source_id == source
            )
        ):
            return 0
        creature = encounter.creature
        amount = enemy_xp(
            level,
            creature.category,
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
                item_id=creature.creature_id,
                quantity=amount,
                payload={"enemy_level": level, "category": creature.category},
            )
        )
        character.xp += amount
        return amount

    @staticmethod
    async def _grant_feat(
        session: AsyncSession, character: Character, encounter: Encounter
    ) -> str | None:
        if encounter.feat_id is None:
            return None
        inserted = await session.scalar(
            insert(Achievement)
            .values(id=uuid4(), character_id=character.id, achievement_id=encounter.feat_id)
            .on_conflict_do_nothing()
            .returning(Achievement.id)
        )
        return None if inserted is None else FEAT_NAMES[encounter.feat_id]

