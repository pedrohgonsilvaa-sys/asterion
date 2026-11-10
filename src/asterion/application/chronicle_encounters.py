"""Encontros da Crônica I: ``[Enfrentar]`` and ``[Enfrentar o Eco de novo]`` (§11.1, §8).

The fight happens in the Local de Ressonância, at the character's level held inside the
band of the Região de Ressonância and frozen when the encounter is created: a retry after
a defeat reuses that level. The first victory pays the normal enemy XP once per character
and registers the objective; a repeated victory pays only the Trilha. Nothing here grants
Coroas, Materiais, Saque, Equipamento or Vigor, and a defeat costs nothing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BestiaryRecorder
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
from asterion.application.prologue import CombatView
from asterion.application.scripted_combat import (
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
    scene_text,
)
from asterion.domain.combat import Combat
from asterion.domain.legacy import legacy_xp_factor
from asterion.domain.road import (
    RULESET,
    CreatureCombatantSpec,
    create_creature_party_combat,
    enemy_xp,
)
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Achievement,
    Character,
    GameActivity,
    GroupActivityParticipant,
    RewardComponent,
    RewardEvent,
    WorldState,
)

CONTEXT = "chronicle"

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
    ):
        self.sessions, self.server_id = sessions, server_id
        self.latest_local, self.recover_defeat = latest_local, recover_defeat
        self.bestiary = BestiaryRecorder()

    # ------------------------------------------------------------------ reads

    async def encounters(
        self, actor: int, *, now: datetime | None = None
    ) -> tuple[EncounterActionView, ...]:
        """The Encontros of every open chapter (empty while the Crônica is closed)."""
        moment = now or datetime.now(UTC)
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
        moment = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
            objective = OBJECTIVES_BY_ID.get(f"cap_{chapter:02d}_obj_{slot:02d}")
            encounter = (
                None if objective is None else ENCOUNTERS_BY_OBJECTIVE.get(objective.objective_id)
            )
            if objective is None or encounter is None:
                raise ChronicleError("chronicle_unknown")
            character = await session.scalar(self._character_query(actor).with_for_update())
            if character is None:
                raise ChronicleError("no_character")
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
            level, flavor = await self._frozen(session, character, content_id)
            if level is None:
                level = encounter_level(character.level, scope.route.region.name)
                flavor = scene_text(encounter, scope.route.region.name)
            activity, combat = await self._materialize(
                session, character, encounter, content_id, level, flavor or ""
            )
            return await self._after(session, character, activity, encounter, combat, moment)

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
        moment = now or datetime.now(UTC)
        async with self.sessions.begin() as session:
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
        combat, _, _ = await current_combat(session, last)
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
            (CreatureCombatantSpec(creature, level, "enemy"),),
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
        combat, encounter_row, _ = await current_combat(session, activity)
        category = ENCOUNTERS_BY_CONTENT[activity.content_id].creature.category
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
        creature = encounter.creature
        objective = OBJECTIVES_BY_ID[encounter.objective_id]
        repeat = activity.content_id == encounter.repeat_content_id
        level = combat.fighters["enemy"].level
        elite = creature.category == "elite"
        if combat.result == "defeat":
            activity.status = "failed"
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
        activity.status = "completed"
        xp = 0 if repeat else await self._grant_first_xp(session, character, encounter, level)
        await normalize_character_hp(session, character)
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

