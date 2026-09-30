"""Persistent, content-neutral lifecycle for the three-stage Class Trials."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
    resolve_character_combat_stats,
)
from asterion.domain.class_trials import (
    CLASS_PATHS,
    SENTINEL_TRIAL_ID,
    TRIAL_COMPLETED_UNLOCK,
    TRIAL_CONTENT_PREFIX,
    TRIAL_IDS_BY_CLASS,
    TrialCombatEvent,
    TrialStageDefinition,
    create_sentinel_trial_combat,
    fresh_attempt_state,
    reset_trial_combat,
    sentinel_conditions_for_event,
    sentinel_stage_definition,
    trial_event_from_combat_event,
)
from asterion.domain.combat import (
    Combat,
    Fighter,
    act,
    allowed_actions,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    ClassTrialState,
    CombatRecord,
    Encounter,
    GameActivity,
    Unlock,
    WorldState,
)

REGION = "Terras do Ocaso"
REFUGE = "Refúgio do Ocaso"
CLASS_TRIAL_ART_LEVEL = 12


@dataclass(frozen=True, slots=True)
class ClassTrialView:
    character_id: UUID
    kind: str
    status: str
    character_class: str
    trial_id: str | None
    level: int
    state_version: int
    current_stage: int | None
    completed_stages: tuple[int, ...]
    context: str
    attempt_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    stage_definition: dict | None = None
    attempt_state: dict | None = None
    available_paths: tuple[str, ...] = ()
    selected_path: str | None = None
    path_art_unlocked: bool = False
    path_art_min_level: int = CLASS_TRIAL_ART_LEVEL
    consumable_options: tuple = ()
    blocker: str | None = None
    combat_version: int | None = None


class ClassTrialService:
    """Owns durable checkpoints and attempts; each Class supplies its own stage plan."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id

    async def resume(self, actor: int) -> ClassTrialView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            state = await session.scalar(
                select(ClassTrialState).where(ClassTrialState.character_id == character.id)
            )
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            foreground = await self._foreground(session, character.id)
            return await self._view(session, character, state, world, foreground)

    async def begin(self, actor: int, version: int = 0) -> ClassTrialView | None:
        """Enter the Circle context without creating a Quest or economic reward."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            foreground = await self._foreground(session, character.id)
            if state is None:
                if (
                    version == 0
                    and self._eligible(character, world)
                    and foreground is None
                    and not await self._has_completed_unlock(session, character.id)
                ):
                    trial_id = TRIAL_IDS_BY_CLASS[character.character_class]
                    state = ClassTrialState(
                        character_id=character.id,
                        character_class=character.character_class,
                        trial_id=trial_id,
                        status="ready",
                        current_stage=1,
                        completed_stages=[],
                        state_version=0,
                        context="circle",
                    )
                    session.add(state)
                    await session.flush()
            elif (
                version == state.state_version
                and state.status == "ready"
                and state.context == "refuge"
                and self._eligible(character, world)
                and foreground is None
            ):
                state.context = "circle"
                state.state_version += 1
            return await self._view(session, character, state, world, foreground)

    async def start_attempt(
        self,
        actor: int,
        version: int,
        definition: TrialStageDefinition | None = None,
    ) -> ClassTrialView | None:
        """Start or retry the current stage using its persisted, immutable template."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            foreground = await self._foreground(session, character.id)
            if state is None:
                return await self._view(session, character, None, world, foreground)
            if state.status == "active":
                return await self._view(session, character, state, world, foreground)
            if (
                version != state.state_version
                or state.status != "ready"
                or state.context != "circle"
                or not self._eligible(character, world)
                or foreground is not None
                or await self._has_completed_unlock(session, character.id)
            ):
                return await self._view(session, character, state, world, foreground)

            sentinel = state.trial_id == SENTINEL_TRIAL_ID
            active_art_configuration = None
            if sentinel:
                active_art_configuration = await load_active_art_configuration(
                    session, character
                )
                selected_arts = active_art_configuration.art_ids
                canonical_attempt = sentinel_stage_definition(
                    state.current_stage, allowed_art_ids=selected_arts
                )
                if definition is not None and definition.to_data() != canonical_attempt.to_data():
                    return await self._view(session, character, state, world, foreground)
                canonical_plan = sentinel_stage_definition(state.current_stage)
                stored_definition = (
                    TrialStageDefinition.from_data(state.stage_definition)
                    if state.stage_definition is not None
                    else canonical_plan
                )
                if (
                    stored_definition is not None
                    and stored_definition.to_data() != canonical_plan.to_data()
                ):
                    return await self._view(session, character, state, world, foreground)
                state.stage_definition = canonical_plan.to_data()
            else:
                stored_definition = (
                    TrialStageDefinition.from_data(state.stage_definition)
                    if state.stage_definition is not None
                    else None
                )
                if stored_definition is None:
                    if definition is None or definition.stage != state.current_stage:
                        return await self._view(session, character, state, world, foreground)
                    stored_definition = definition
                    state.stage_definition = definition.to_data()
                elif definition is not None and definition.to_data() != state.stage_definition:
                    return await self._view(session, character, state, world, foreground)

            configuration = await load_equipment_configuration(session, character)
            reconcile_character_hp(character, configuration)
            character.hp = character.max_hp
            attempt_id = uuid4()
            activity = GameActivity(
                id=attempt_id,
                character_id=character.id,
                content_id=f"{TRIAL_CONTENT_PREFIX}{state.trial_id.removeprefix('trial.')}",
                status="active",
                state_version=0,
                ruleset_version=CURRENT_COMBAT_RULESET,
            )
            session.add(activity)
            await session.flush()
            state.status = "active"
            state.current_attempt_id = attempt_id
            state.attempt_state = fresh_attempt_state(
                stored_definition, Decimal(character.max_hp)
            )
            if sentinel:
                state.attempt_state["active_arts"] = [
                    entry.to_data() for entry in active_art_configuration.slots
                ]
                # Transitional read-model field retained for existing trial views;
                # it is derived only from the authoritative persisted slot rows.
                state.attempt_state["equipped_art_ids"] = list(selected_arts)
            state.state_version += 1
            state.context = "circle"
            if sentinel:
                attempt_definition = sentinel_stage_definition(
                    state.current_stage, allowed_art_ids=selected_arts
                )
                configuration = await load_equipment_configuration(session, character)
                player = Fighter(
                    "player",
                    character.name,
                    character.level,
                    resolve_character_combat_stats(character, configuration),
                    Decimal(character.hp),
                    race=character.race,
                    character_class=character.character_class,
                )
                combat = create_sentinel_trial_combat(player, attempt_definition)
                combat.configuration_snapshot = (
                    configuration.to_data(CURRENT_COMBAT_RULESET)
                    | active_art_configuration.to_data()
                    | {"equipped_class_art_ids": list(selected_arts)}
                )
                combat = start_combat(
                    reset_trial_combat(combat, attempt_definition, Decimal(character.max_hp))
                )
                encounter = Encounter(id=uuid4(), game_activity_id=activity.id)
                session.add(encounter)
                await session.flush()
                session.add(
                    CombatRecord(
                        id=combat.id,
                        encounter_id=encounter.id,
                        snapshot=encode(combat),
                    )
                )
                activity.state_version = combat.version
                character.hp = combat.fighters["player"].hp
                state.attempt_state["combat_id"] = str(combat.id)
                state.attempt_state["encounter_id"] = str(encounter.id)
                self._sync_attempt_combat(state.attempt_state, stored_definition, combat)
                for combat_event in combat.events:
                    self._append_sentinel_event(
                        state.attempt_state,
                        stored_definition,
                        trial_event_from_combat_event(combat, combat_event),
                    )
            await session.flush()
            return await self._view(session, character, state, world, activity)

    async def record_combat_event(
        self,
        actor: int,
        attempt_id: UUID,
        version: int,
        event: TrialCombatEvent,
    ) -> ClassTrialView | None:
        """Persist server-observed events and their deterministic condition matches."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            activity = await self._attempt_activity(session, character.id, attempt_id, lock=True)
            foreground = await self._foreground(session, character.id)
            if not self._owns_attempt(state, activity, foreground, attempt_id):
                return await self._view(session, character, state, world, foreground)
            if state.trial_id == SENTINEL_TRIAL_ID:
                # Sentinela pedagogy is derived only from the persisted shared-engine log.
                return await self._view(session, character, state, world, activity)
            attempt = dict(state.attempt_state or {})
            processed = set(attempt.get("processed_event_ids", ()))
            if event.event_id in processed:
                return await self._view(session, character, state, world, activity)
            if version != state.state_version:
                return await self._view(session, character, state, world, activity)
            definition = TrialStageDefinition.from_data(state.stage_definition or {})
            entity_ids = {entity.entity_id for entity in definition.entities}
            actor_ids = entity_ids | {"player"}
            satisfied_conditions = (
                sentinel_conditions_for_event(definition.stage, event)
                if state.trial_id == SENTINEL_TRIAL_ID
                else event.satisfied_conditions
            )
            if (
                event.actor_id not in actor_ids
                or not set(event.target_ids).issubset(actor_ids)
                or not set((event.entity_hp or {}).keys()).issubset(entity_ids)
                or not set((event.entity_barriers or {}).keys()).issubset(entity_ids)
                or not set(satisfied_conditions).issubset(set(definition.required_conditions))
            ):
                return await self._view(session, character, state, world, activity)

            for entity_id, hp in (event.entity_hp or {}).items():
                maximum = next(
                    entity.max_hp
                    for entity in definition.entities
                    if entity.entity_id == entity_id
                )
                if hp > maximum:
                    return await self._view(session, character, state, world, activity)
                attempt["entities"][entity_id]["hp"] = str(hp)
            for entity_id, (value, duration) in (event.entity_barriers or {}).items():
                attempt["entities"][entity_id]["barrier"] = str(value)
                attempt["entities"][entity_id]["barrier_remaining"] = duration
            if event.player_hp is not None:
                if event.player_hp > Decimal(character.max_hp):
                    return await self._view(session, character, state, world, activity)
                attempt["player"]["hp"] = str(event.player_hp)
                character.hp = event.player_hp

            processed.add(event.event_id)
            attempt["processed_event_ids"] = sorted(processed)
            event_conditions = set(attempt.get("pedagogic_conditions", ()))
            event_conditions.update(satisfied_conditions)
            attempt["pedagogic_conditions"] = sorted(event_conditions)
            attempt.setdefault("events", []).append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "actor_id": event.actor_id,
                    "target_ids": list(event.target_ids),
                    "action_id": event.action_id,
                    "action_instance_id": event.action_instance_id,
                    "conditions": list(satisfied_conditions),
                    "calculated_damage": str(event.calculated_damage),
                    "effective_damage": str(event.effective_damage),
                    "barrier_absorbed": str(event.barrier_absorbed),
                    "target_barrier_source": event.target_barrier_source,
                    "target_effect_ids": list(event.target_effect_ids),
                    "defender_mitigation_applied": event.defender_mitigation_applied,
                    "defender_prevented_damage": str(event.defender_prevented_damage),
                    "prepared_resolution": event.prepared_resolution,
                    "effect_applied": event.effect_applied,
                    "actor_effect_id": event.actor_effect_id,
                    "retaliation_valid": event.retaliation_valid,
                    "retaliation_used": event.retaliation_used,
                    "retaliation_activation_id": event.retaliation_activation_id,
                    "retaliation_source_type": event.retaliation_source_type,
                    "retaliation_source_event_id": event.retaliation_source_event_id,
                    "retaliation_source_actor_id": event.retaliation_source_actor_id,
                    "dodged": event.dodged,
                    "entity_barriers": {
                        entity_id: {"value": str(value), "remaining": duration}
                        for entity_id, (value, duration) in (event.entity_barriers or {}).items()
                    },
                    "data": self._json_safe(dict(event.data or {})),
                }
            )
            state.attempt_state = attempt
            state.state_version += 1
            required_ally_defeated = any(
                entity.required_to_survive
                and Decimal(attempt["entities"][entity.entity_id]["hp"]) <= 0
                for entity in definition.entities
            )
            if (
                (event.player_hp is not None and event.player_hp <= 0)
                or required_ally_defeated
            ):
                await self._fail_locked(state, activity)
                await session.flush()
                return await self._view(session, character, state, world, None)
            await session.flush()
            return await self._view(session, character, state, world, activity)

    async def action(
        self,
        actor: int,
        attempt_id: UUID,
        combat_version: int,
        action_id: str,
        *,
        target_id: str | None = None,
    ) -> ClassTrialView | None:
        """Apply one player action to an active Sentinel trial combat snapshot."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            activity = await self._attempt_activity(
                session, character.id, attempt_id, lock=True
            )
            foreground = await self._foreground(session, character.id)
            if (
                state is None
                or state.trial_id != SENTINEL_TRIAL_ID
                or not self._owns_attempt(state, activity, foreground, attempt_id)
                or activity.state_version != combat_version
                or action_id.startswith("consumable:")
            ):
                return await self._view(session, character, state, world, foreground)
            row = await session.execute(
                select(Encounter, CombatRecord)
                .join(CombatRecord, CombatRecord.encounter_id == Encounter.id)
                .where(Encounter.game_activity_id == activity.id)
                .with_for_update()
            )
            pair = row.one_or_none()
            if pair is None:
                return await self._view(session, character, state, world, activity)
            _, record = pair
            combat = decode(
                record.snapshot,
                record.id,
                activity.ruleset_version,
                activity.state_version,
            )
            if (
                combat.version != combat_version
                or combat.external_consumables_allowed
                or combat.consumable_uses != 0
                or action_id not in allowed_actions(combat)
            ):
                return await self._view(session, character, state, world, activity)
            updated = act(combat, action_id, target_id=target_id)
            if updated.version == combat.version or updated.consumable_uses != 0:
                return await self._view(session, character, state, world, activity)

            definition = TrialStageDefinition.from_data(state.stage_definition or {})
            attempt = dict(state.attempt_state or {})
            attempt["last_combat_version"] = updated.version
            frozen_configuration = combat.configuration_snapshot or {}
            active_arts = list(frozen_configuration.get("active_arts", ()))
            attempt["active_arts"] = active_arts
            attempt["equipped_art_ids"] = [
                str(entry["art_id"])
                for entry in active_arts
                if isinstance(entry, dict) and "art_id" in entry
            ]
            self._sync_attempt_combat(attempt, definition, updated)
            for combat_event in updated.events[len(combat.events) :]:
                self._append_sentinel_event(
                    attempt,
                    definition,
                    trial_event_from_combat_event(updated, combat_event),
                )

            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            character.hp = updated.fighters["player"].hp
            state.attempt_state = attempt
            state.state_version += 1
            if updated.result == "defeat":
                await self._fail_locked(state, activity)
                await session.flush()
                return await self._view(session, character, state, world, None)
            if updated.result == "victory":
                if await self._checkpoint_locked(session, character, state, activity):
                    await session.flush()
                    return await self._view(session, character, state, world, None)
                # A defeated Echo cannot remain as a live foreground encounter.
                # Without the required pedagogy the stage is not complete, so
                # end this attempt and leave the same frozen stage ready to retry.
                await self._fail_locked(state, activity)
                await session.flush()
                return await self._view(session, character, state, world, None)
            await session.flush()
            return await self._view(session, character, state, world, activity)

    @staticmethod
    def _sync_attempt_combat(
        attempt: dict, definition: TrialStageDefinition, combat: Combat
    ) -> None:
        def fighter_state(fighter: Fighter) -> dict:
            return {
                "hp": str(fighter.hp),
                "effects": [
                    {
                        "id": effect.id,
                        "stat": effect.stat,
                        "magnitude": str(effect.magnitude),
                        "remaining": effect.remaining,
                        "kind": effect.kind,
                    }
                    for effect in fighter.effects
                ],
                "barrier": str(fighter.barrier),
                "barrier_remaining": fighter.barrier_remaining,
                "barrier_source": fighter.barrier_source,
                "cooldowns": dict(fighter.cooldowns),
                "resources": {
                    "ward_charges": fighter.ward_charges,
                    "ward_remaining": fighter.ward_remaining,
                    "opportunity": fighter.opportunity,
                    "retaliation": {
                        "charges": fighter.retaliation_charges,
                        "remaining_T": fighter.retaliation_remaining,
                        "activation_id": fighter.retaliation_activation_id,
                        "source_type": fighter.retaliation_source_type,
                        "source_event_id": fighter.retaliation_source_event_id,
                        "source_actor_id": fighter.retaliation_source_actor_id,
                    },
                },
            }

        attempt["player"] = fighter_state(combat.fighters["player"])
        attempt["entities"] = {
            entity.entity_id: fighter_state(
                next(f for f in combat.fighters.values() if f.id == entity.entity_id)
            )
            for entity in definition.entities
        }
        attempt["combat_context"] = {
            "prepared_action": combat.prepared_action,
            "prepared_source": (
                combat.fighters[combat.prepared_source].id
                if combat.prepared_source in combat.fighters
                else combat.prepared_source
            ),
            "prepared_target": combat.prepared_target,
            "response_window_seen": combat.response_window_seen,
            "resolving_prepared": combat.resolving_prepared,
            "combat_version": combat.version,
        }
        attempt["external_consumables_used"] = combat.consumable_uses

    @staticmethod
    def _append_sentinel_event(
        attempt: dict,
        definition: TrialStageDefinition,
        event: TrialCombatEvent,
    ) -> None:
        processed = set(attempt.get("processed_event_ids", ()))
        if event.event_id in processed:
            return
        conditions = sentinel_conditions_for_event(definition.stage, event)
        if not set(conditions).issubset(set(definition.required_conditions)):
            return
        processed.add(event.event_id)
        attempt["processed_event_ids"] = sorted(processed)
        progress = set(attempt.get("pedagogic_conditions", ()))
        progress.update(conditions)
        attempt["pedagogic_conditions"] = sorted(progress)
        attempt.setdefault("events", []).append(
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "actor_id": event.actor_id,
                "target_ids": list(event.target_ids),
                "action_id": event.action_id,
                "action_instance_id": event.action_instance_id,
                "conditions": list(conditions),
                "calculated_damage": str(event.calculated_damage),
                "effective_damage": str(event.effective_damage),
                "barrier_absorbed": str(event.barrier_absorbed),
                "target_barrier_source": event.target_barrier_source,
                "target_effect_ids": list(event.target_effect_ids),
                "defender_mitigation_applied": event.defender_mitigation_applied,
                "defender_prevented_damage": str(event.defender_prevented_damage),
                "prepared_resolution": event.prepared_resolution,
                "effect_applied": event.effect_applied,
                "actor_effect_id": event.actor_effect_id,
                "retaliation_valid": event.retaliation_valid,
                "retaliation_used": event.retaliation_used,
                "retaliation_activation_id": event.retaliation_activation_id,
                "retaliation_source_type": event.retaliation_source_type,
                "retaliation_source_event_id": event.retaliation_source_event_id,
                "retaliation_source_actor_id": event.retaliation_source_actor_id,
                "dodged": event.dodged,
            }
        )

    async def attach_combat(
        self,
        actor: int,
        attempt_id: UUID,
        version: int,
        combat: Combat,
    ) -> ClassTrialView | None:
        """Attach exactly one shared-engine snapshot to an existing trial attempt."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            activity = await self._attempt_activity(
                session, character.id, attempt_id, lock=True
            )
            foreground = await self._foreground(session, character.id)
            if not self._owns_attempt(state, activity, foreground, attempt_id):
                return await self._view(session, character, state, world, foreground)
            existing = await session.scalar(
                select(Encounter).where(Encounter.game_activity_id == activity.id)
            )
            if existing is not None or version != state.state_version:
                return await self._view(session, character, state, world, activity)
            if activity.ruleset_version != combat.ruleset:
                return await self._view(session, character, state, world, activity)
            definition = TrialStageDefinition.from_data(state.stage_definition or {})
            try:
                prepared = reset_trial_combat(
                    combat, definition, Decimal(character.max_hp)
                )
            except ValueError:
                return await self._view(session, character, state, world, activity)
            encounter = Encounter(id=uuid4(), game_activity_id=activity.id)
            session.add(encounter)
            await session.flush()
            session.add(
                CombatRecord(
                    id=prepared.id,
                    encounter_id=encounter.id,
                    snapshot=encode(prepared),
                )
            )
            activity.state_version = prepared.version
            attempt = dict(state.attempt_state or {})
            attempt["combat_id"] = str(prepared.id)
            attempt["encounter_id"] = str(encounter.id)
            state.attempt_state = attempt
            state.state_version += 1
            await session.flush()
            return await self._view(session, character, state, world, activity)

    async def combat(self, actor: int, attempt_id: UUID) -> Combat | None:
        """Decode the same persisted encounter snapshot used by reconnect."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == attempt_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id.like(f"{TRIAL_CONTENT_PREFIX}%"),
                )
            )
            if activity is None:
                return None
            record = await session.scalar(
                select(CombatRecord)
                .join(Encounter, Encounter.id == CombatRecord.encounter_id)
                .where(Encounter.game_activity_id == activity.id)
            )
            if record is None:
                return None
            return decode(
                record.snapshot,
                record.id,
                activity.ruleset_version,
                activity.state_version,
            )

    async def fail_attempt(
        self, actor: int, attempt_id: UUID, version: int
    ) -> ClassTrialView | None:
        """End only the current attempt; the checkpoint and frozen stage plan remain."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            activity = await self._attempt_activity(session, character.id, attempt_id, lock=True)
            foreground = await self._foreground(session, character.id)
            if (
                self._owns_attempt(state, activity, foreground, attempt_id)
                and state.state_version == version
            ):
                await self._fail_locked(state, activity)
                await session.flush()
                foreground = None
            return await self._view(session, character, state, world, foreground)

    async def complete_stage(
        self, actor: int, attempt_id: UUID, version: int
    ) -> ClassTrialView | None:
        """Acknowledge victory only when every target and pedagogic checkpoint is valid."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            activity = (
                await self._attempt_activity(
                    session, character.id, state.current_attempt_id, lock=True
                )
                if state and state.current_attempt_id
                else None
            )
            foreground = await self._foreground(session, character.id)
            if state is None or activity is None or not self._owns_attempt(
                state, activity, foreground, attempt_id
            ) or state.state_version != version:
                return await self._view(session, character, state, world, foreground)

            if state.trial_id == SENTINEL_TRIAL_ID:
                row = await session.execute(
                    select(Encounter, CombatRecord)
                    .join(CombatRecord, CombatRecord.encounter_id == Encounter.id)
                    .where(Encounter.game_activity_id == activity.id)
                )
                pair = row.one_or_none()
                if pair is None:
                    return await self._view(session, character, state, world, activity)
                _, record = pair
                combat = decode(
                    record.snapshot,
                    record.id,
                    activity.ruleset_version,
                    activity.state_version,
                )
                if combat.result != "victory":
                    return await self._view(session, character, state, world, activity)
            if not await self._checkpoint_locked(session, character, state, activity):
                return await self._view(session, character, state, world, activity)
            await session.flush()
            return await self._view(session, character, state, world, None)

    async def _checkpoint_locked(self, session, character, state, activity) -> bool:
        definition = TrialStageDefinition.from_data(state.stage_definition or {})
        attempt = state.attempt_state or {}
        hp = attempt.get("entities", {})
        conditions = set(attempt.get("pedagogic_conditions", ()))
        hostiles_defeated = all(
            Decimal(hp.get(entity.entity_id, {}).get("hp", str(entity.max_hp))) <= 0
            for entity in definition.entities
            if entity.team == "hostile"
        )
        required_allies_alive = all(
            Decimal(hp.get(entity.entity_id, {}).get("hp", str(entity.max_hp))) > 0
            for entity in definition.entities
            if entity.required_to_survive
        )
        if (
            not hostiles_defeated
            or not required_allies_alive
            or not set(definition.required_conditions).issubset(conditions)
        ):
            return False

        activity.status = "completed"
        checkpoints = list(state.completed_stages or ())
        if state.current_stage not in checkpoints:
            checkpoints.append(state.current_stage)
        state.completed_stages = sorted(checkpoints)
        state.current_attempt_id = None
        state.attempt_state = None
        state.state_version += 1
        state.context = "circle"
        if state.current_stage == 3:
            state.status = "completed"
            state.stage_definition = None
            await self._grant_completed_unlock(session, character.id)
        else:
            state.status = "ready"
            state.current_stage += 1
            state.stage_definition = None
        return True

    async def leave_to_refuge(self, actor: int, version: int) -> ClassTrialView | None:
        """Leave between attempts or checkpoints without changing durable progress."""
        return await self._set_context(actor, version, "circle", "refuge")

    async def return_to_circle(self, actor: int, version: int) -> ClassTrialView | None:
        return await self._set_context(actor, version, "refuge", "circle")

    async def _set_context(
        self, actor: int, version: int, source: str, destination: str
    ) -> ClassTrialView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            state = await self._state(session, character.id, lock=True)
            world = await self._world(session, character.id, lock=True)
            foreground = await self._foreground(session, character.id)
            if (
                state is not None
                and state.status == "ready"
                and state.state_version == version
                and state.context == source
                and self._eligible(character, world)
                and foreground is None
            ):
                state.context = destination
                state.state_version += 1
                await session.flush()
            return await self._view(session, character, state, world, foreground)

    async def _view(self, session, character, state, world, foreground) -> ClassTrialView:
        completed_unlock = await self._has_completed_unlock(session, character.id)
        path_options = (
            CLASS_PATHS.get(character.character_class, ()) if completed_unlock else ()
        )
        if state is None and completed_unlock:
            return ClassTrialView(
                character_id=character.id,
                kind="completed",
                status="completed",
                character_class=character.character_class,
                trial_id=TRIAL_IDS_BY_CLASS.get(character.character_class),
                level=character.level,
                state_version=0,
                current_stage=3,
                completed_stages=(1, 2, 3),
                context="refuge",
                available_paths=path_options,
                path_art_unlocked=False,
            )
        trial_id = state.trial_id if state is not None else TRIAL_IDS_BY_CLASS.get(
            character.character_class
        )
        activity = foreground
        if state is not None and state.current_attempt_id is not None:
            activity = await session.scalar(
                select(GameActivity).where(GameActivity.id == state.current_attempt_id)
            )
        encounter_id = None
        combat_id = None
        if activity is not None and activity.content_id.startswith(TRIAL_CONTENT_PREFIX):
            encounter_id = await session.scalar(
                select(Encounter.id).where(Encounter.game_activity_id == activity.id)
            )
            if encounter_id is not None:
                combat_id = await session.scalar(
                    select(CombatRecord.id)
                    .join(Encounter, Encounter.id == CombatRecord.encounter_id)
                    .where(Encounter.game_activity_id == activity.id)
                )

        if state is None:
            eligible = self._eligible(character, world)
            has_foreground = foreground is not None
            kind = "available" if eligible and not has_foreground else "unavailable"
            blocker = None if kind == "available" else (
                "foreground" if has_foreground else self._eligibility_blocker(character, world)
            )
            return ClassTrialView(
                character_id=character.id,
                kind=kind,
                status="unstarted",
                character_class=character.character_class,
                trial_id=trial_id,
                level=character.level,
                state_version=0,
                current_stage=1,
                completed_stages=(),
                context="refuge" if self._at_refuge(world) else "outside",
                blocker=blocker,
            )

        active_is_valid = bool(
            state.status == "active"
            and activity is not None
            and activity.id == state.current_attempt_id
            and activity.status == "active"
        )
        if state.status == "completed":
            kind = "completed"
        elif state.status == "active" and active_is_valid:
            kind = "active"
        elif state.status == "active":
            kind = "unavailable"
        elif foreground is not None and state.status != "active":
            kind = "unavailable"
        elif state.context == "refuge":
            kind = "between_attempts"
        else:
            kind = "ready"
        stage_definition = dict(state.stage_definition) if state.stage_definition else None
        attempt_state = (
            dict(state.attempt_state)
            if active_is_valid and state.attempt_state
            else None
        )
        return ClassTrialView(
            character_id=character.id,
            kind=kind,
            status=state.status if active_is_valid or state.status != "active" else "unavailable",
            character_class=state.character_class,
            trial_id=state.trial_id,
            level=character.level,
            state_version=state.state_version,
            current_stage=state.current_stage,
            completed_stages=tuple(state.completed_stages or ()),
            context=state.context,
            attempt_id=state.current_attempt_id if active_is_valid else None,
            encounter_id=encounter_id if active_is_valid else None,
            combat_id=combat_id if active_is_valid else None,
            stage_definition=stage_definition,
            attempt_state=attempt_state,
            available_paths=path_options,
            selected_path=None,
            path_art_unlocked=False,
            consumable_options=(),
            blocker=(
                "attempt_missing"
                if state.status == "active" and not active_is_valid
                else "foreground" if foreground is not None and state.status != "active" else None
            ),
            combat_version=(activity.state_version if active_is_valid and combat_id else None),
        )

    async def _grant_completed_unlock(self, session, character_id: UUID) -> None:
        await session.execute(
            insert(Unlock)
            .values(character_id=character_id, unlock_id=TRIAL_COMPLETED_UNLOCK)
            .on_conflict_do_nothing(index_elements=[Unlock.character_id, Unlock.unlock_id])
        )

    async def _has_completed_unlock(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == TRIAL_COMPLETED_UNLOCK,
                )
            )
        )

    @classmethod
    def _json_safe(cls, value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, dict):
            return {str(key): cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._json_safe(item) for item in value]
        return value

    async def _fail_locked(self, state: ClassTrialState, activity: GameActivity) -> None:
        activity.status = "failed"
        state.status = "ready"
        state.current_attempt_id = None
        state.attempt_state = None
        state.context = "circle"
        state.state_version += 1

    async def _attempt_activity(self, session, character_id: UUID, attempt_id: UUID, *, lock: bool):
        statement = select(GameActivity).where(
            GameActivity.id == attempt_id,
            GameActivity.character_id == character_id,
            GameActivity.content_id.like(f"{TRIAL_CONTENT_PREFIX}%"),
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    @staticmethod
    def _owns_attempt(state, activity, foreground, attempt_id) -> bool:
        return bool(
            state is not None
            and state.status == "active"
            and state.current_attempt_id == attempt_id
            and activity is not None
            and activity.status == "active"
            and activity.id == attempt_id
            and foreground is not None
            and foreground.id == attempt_id
        )

    async def _character(self, session, actor, *, lock: bool = False):
        statement = select(Character).where(
            Character.telegram_id == actor,
            Character.server_id == self.server_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    @staticmethod
    async def _state(session, character_id, *, lock: bool = False):
        statement = select(ClassTrialState).where(ClassTrialState.character_id == character_id)
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    @staticmethod
    async def _world(session, character_id, *, lock: bool = False):
        statement = select(WorldState).where(WorldState.character_id == character_id)
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    @staticmethod
    async def _foreground(session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        )

    @staticmethod
    def _eligible(character, world) -> bool:
        return bool(
            character.level >= 10
            and character.character_class in TRIAL_IDS_BY_CLASS
            and ClassTrialService._at_refuge(world)
        )

    @staticmethod
    def _at_refuge(world) -> bool:
        return bool(world and world.region == REGION and world.location == REFUGE)

    @staticmethod
    def _eligibility_blocker(character, world) -> str:
        if character.level < 10:
            return "level"
        if character.character_class not in TRIAL_IDS_BY_CLASS:
            return "class"
        if not ClassTrialService._at_refuge(world):
            return "location"
        return "unavailable"
