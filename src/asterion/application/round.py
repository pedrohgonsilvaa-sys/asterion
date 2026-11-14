"""Authoritative Ronda de Caça orchestration for the Estrada das Cinzas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.inventory_capacity import inventory_capacity
from asterion.application.road import (
    BOSQUE,
    CHARNECA,
    HUNT_CONTENT,
    MATERIAL_LABELS,
    PVPVE_CONTENT,
    PVPVE_QUEUE_CONTENT,
    REFUGE,
    ROAD,
    RUINS,
    VARIANT_LABELS,
    VARZEAS_REGION,
    RoadService,
    RoadView,
)
from asterion.application.ttk_telemetry import SOURCE_ROUND_AUTO
from asterion.application.vigor import reconcile_character_vigor
from asterion.domain.combat import (
    act,
    action_target_ids,
    allowed_actions,
    consumable_available,
    effective_heal_amount,
    player_actions_for,
    use_heal_consumable,
    use_purification_consumable,
)
from asterion.domain.combat_math import dot_damage
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.equipment_stats import (
    EquipmentConfigurationSnapshot,
    equipment_configuration_from_data,
)
from asterion.domain.road import (
    ALTOS_BASTILHA_LOCATION,
    ALTOS_ESCARPA_LOCATION,
    ALTOS_PEDREIRAS_LOCATION,
    ALTOS_PONTES_LOCATION,
    ALTOS_REGION,
    BOSQUE_LOCATION,
    CHARNECA_LOCATION,
    MATERIAL_POOLS,
    NARETH_CAMPINAS_LOCATION,
    NARETH_POSTO_LOCATION,
    NARETH_REGION_UNLOCK,
    ROAD_LOCATION,
    RUINS_LOCATION,
    RULESET,
    VARZEAS_GALERIAS_LOCATION,
    VDE_BAIXIOS_LOCATION,
    VDE_CLAUSTRO_LOCATION,
    VDE_GARGANTA_LOCATION,
    VDE_MATA_LOCATION,
    create_road_combat,
    creature_for,
    hunt_profile_for_local_id,
    hunt_profile_for_location,
    select_creature,
    select_variant,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    ConsumableStack,
    Encounter,
    GameActivity,
    HuntContext,
    HuntRound,
    HuntRoundEncounter,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

ROUND_CONTENT = "road_hunt_round"
ROUND_ENCOUNTER_CONTENT = "road_hunt_round_encounter"
HEAL_CONSUMABLE = "consumable.heal"
PURIFY_CONSUMABLE = "consumable.purification"
ROUND_CADENCE = timedelta(minutes=3)
ROUND_OPEN_STATUSES = ("preparing", "active", "interrupted")
ROUND_RESULT_STATUSES = ("completed", "cancelled", "defeated", "ended")
SAFETY_THRESHOLD = Decimal("0.35")
RECOVERY_THRESHOLD = Decimal("0.50")
CRITICAL_THRESHOLD = Decimal("0.30")
MIN_EFFECTIVE_HEAL = Decimal("0.10")
CONSUMABLE_LIMITS = ENCOUNTER_CONSUMABLE_LIMITS


def _encounter_ruleset(snapshot: dict) -> str:
    configuration = snapshot.get("configuration_snapshot")
    if isinstance(configuration, dict):
        ruleset = configuration.get("ruleset_version")
        if isinstance(ruleset, str) and ruleset:
            return ruleset
    return RULESET


@dataclass(frozen=True)
class RoundView:
    kind: str
    character_id: UUID
    location: str = ROAD
    round_id: UUID | None = None
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    combat: object | None = None
    state_version: int = 0
    batch_size: int = 0
    completed_encounters: int = 0
    vigor: int = 0
    max_vigor: int = 100
    name: str = ""
    hp: Decimal = Decimal(0)
    max_hp: Decimal = Decimal(0)
    reward_lines: tuple[str, ...] = ()
    heal_quantity: int = 0
    purify_quantity: int = 0
    prepared_heal: bool = False
    prepared_purify: bool = False
    cancel_requested: bool = False
    next_resolution_at: datetime | None = None
    end_reason: str | None = None
    creature: str | None = None
    enemy_level: int = 0
    variant: str | None = None
    result_text: str | None = None
    inventory_blocked: bool = False
    pending_blocked: bool = False
    recovery_brazier: str | None = None
    recovery_location: str | None = None
    route_available: bool = False


class RoundService(RoadService):
    """Road service plus persistent timed Ronda batches."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        super().__init__(sessions, server_id)

    async def _character(self, s, actor):
        character = await s.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is not None:
            await reconcile_character_vigor(s, character)
        return character

    async def _round_profile(self, s, c, world):
        profile = hunt_profile_for_location(world.location) if world is not None else None
        if profile is None:
            return None
        if profile.local_id == ROAD_LOCATION:
            if not await self._p1_completed(s, c.id):
                return None
        elif profile.local_id == CHARNECA_LOCATION and not await self._p2_completed(s, c.id):
            return None
        elif profile.local_id == BOSQUE_LOCATION and not await self._p3_completed(s, c.id):
            return None
        elif profile.local_id == RUINS_LOCATION:
            if c.level < 8 or not await self._p4_completed(s, c.id):
                return None
            if not await self._has_location(s, c.id, RUINS_LOCATION):
                return None
        elif profile.local_id == VDE_GARGANTA_LOCATION:
            if not await self._p7_completed(s, c.id):
                return None
        elif profile.local_id == VDE_MATA_LOCATION:
            if c.level < 13 or not await self._p8_completed(s, c.id):
                return None
        elif profile.local_id == VDE_BAIXIOS_LOCATION:
            if c.level < 15 or not await self._p9_started_or_completed(s, c.id):
                return None
        elif profile.local_id == VDE_CLAUSTRO_LOCATION:
            if c.level < 18 or not await self._p10_completed(s, c.id):
                return None
        elif profile.local_id == NARETH_CAMPINAS_LOCATION:
            if c.level < 21 or not await self._p12_completed(s, c.id):
                return None
            if not await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == NARETH_REGION_UNLOCK,
                )
            ):
                return None
            if not await self._nareth_p13_completed(s, c.id):
                return None
        elif profile.local_id == VARZEAS_GALERIAS_LOCATION:
            if (
                world.region != VARZEAS_REGION
                or c.level < 37
                or not await self._nareth_mission_completed(s, c.id, "P22")
            ):
                return None
        elif profile.local_id == ALTOS_ESCARPA_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 41
                or not await self._nareth_mission_completed(s, c.id, "P25")
                or not await self._has_location(s, c.id, ALTOS_ESCARPA_LOCATION)
            ):
                return None
        elif profile.local_id == ALTOS_PONTES_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 43
                or not await self._nareth_mission_completed(s, c.id, "P25")
                or not await self._nareth_mission_completed(s, c.id, "P26")
                or not await self._has_location(s, c.id, ALTOS_PONTES_LOCATION)
            ):
                return None
        elif profile.local_id == ALTOS_PEDREIRAS_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 45
                or not await self._nareth_mission_completed(s, c.id, "P26")
                or not await self._nareth_mission_completed(s, c.id, "P27")
                or not await self._has_location(s, c.id, ALTOS_PEDREIRAS_LOCATION)
            ):
                return None
        elif profile.local_id == ALTOS_BASTILHA_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 47
                or not await self._nareth_mission_completed(s, c.id, "P27")
                or not await self._nareth_mission_completed(s, c.id, "P28")
                or not await self._has_location(s, c.id, ALTOS_BASTILHA_LOCATION)
            ):
                return None
        elif profile.local_id == NARETH_POSTO_LOCATION:
            return None
        if profile.local_id in {
            VDE_GARGANTA_LOCATION,
            VDE_MATA_LOCATION,
            VDE_BAIXIOS_LOCATION,
            VDE_CLAUSTRO_LOCATION,
            NARETH_CAMPINAS_LOCATION,
            VARZEAS_GALERIAS_LOCATION,
            ALTOS_ESCARPA_LOCATION,
            ALTOS_PONTES_LOCATION,
            ALTOS_PEDREIRAS_LOCATION,
            ALTOS_BASTILHA_LOCATION,
        } and any(
            creature_id not in MATERIAL_POOLS for creature_id, _ in profile.creature_weights
        ):
            return None
        return profile

    async def _inventory_slots(self, s, character_id):
        return await super()._inventory_slots(s, character_id)

    async def _open_round(self, s, character_id, *, lock=False):
        statement = (
            select(HuntRound)
            .where(
                HuntRound.character_id == character_id,
                HuntRound.status.in_(ROUND_OPEN_STATUSES),
            )
            .order_by(HuntRound.created_at.desc(), HuntRound.id.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update()
        return await s.scalar(statement)

    async def _pending_round_result(self, s, character_id, *, lock=False):
        statement = (
            select(HuntRound)
            .where(
                HuntRound.character_id == character_id,
                HuntRound.status.in_(ROUND_RESULT_STATUSES),
                HuntRound.result_acknowledged.is_(False),
            )
            .order_by(HuntRound.completed_at.desc(), HuntRound.created_at.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update()
        return await s.scalar(statement)

    async def _road_blocking_view(self, s, c):
        round_state = await self._open_round(s, c.id, lock=True)
        if round_state is not None:
            if round_state.status == "preparing":
                return await self._round_view(s, c, round_state)
            if round_state.status == "active":
                activity = await self._round_activity(s, round_state)
                if activity is not None and activity.content_id in {
                    PVPVE_CONTENT,
                    PVPVE_QUEUE_CONTENT,
                }:
                    return await self.pvpve.view_for_activity(s, c, activity)
                await self._advance_round_locked(s, c, round_state, datetime.now(UTC))
                if round_state.status != "active":
                    return await self._round_view(s, c, round_state)
                return await self._round_view(s, c, round_state)
            if round_state.status == "interrupted" and not round_state.elite_engaged:
                return await self._round_view(s, c, round_state)
        result = await self._pending_round_result(s, c.id, lock=True)
        if result is not None:
            return await self._round_view(s, c, result)
        return await super()._road_blocking_view(s, c)

    async def prepare_round(self, actor: int, batch_size: int) -> RoadView | RoundView | None:
        if batch_size not in {5, 10, 20}:
            return None
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            profile = await self._round_profile(s, c, world)
            if profile is None:
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if not await s.scalar(
                select(Unlock).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == profile.round_familiarity,
                )
            ):
                return await self._view_for_world(s, c, world)
            current = await s.scalar(
                select(HuntRound)
                .where(
                    HuntRound.character_id == c.id,
                    HuntRound.status == "preparing",
                )
                .order_by(HuntRound.created_at.desc())
                .limit(1)
                .with_for_update()
            )
            if current is None:
                current = HuntRound(
                    character_id=c.id,
                    status="preparing",
                    batch_size=batch_size,
                    seed=uuid4().hex,
                    config_snapshot={"local_id": profile.local_id},
                )
                s.add(current)
                await s.flush()
            elif current.batch_size != batch_size:
                current.batch_size = batch_size
                current.state_version += 1
            if (current.config_snapshot or {}).get("local_id") != profile.local_id:
                current.config_snapshot = {
                    **(current.config_snapshot or {}),
                    "local_id": profile.local_id,
                }
                current.state_version += 1
            return await self._round_view(s, c, current)

    async def round_prepare_view(
        self, actor: int, round_id: UUID, version: int
    ) -> RoadView | RoundView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            state = await s.scalar(
                select(HuntRound)
                .where(HuntRound.id == round_id, HuntRound.character_id == c.id)
                .with_for_update()
            )
            if state is None:
                return await self._road_blocking_view(s, c)
            if state.status != "preparing" or state.state_version != version:
                return await self._round_view(s, c, state)
            return await self._round_view(s, c, state, kind="round_prepare")

    async def round_consumables(
        self, actor: int, round_id: UUID, version: int
    ) -> RoadView | RoundView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            state = await s.scalar(
                select(HuntRound)
                .where(HuntRound.id == round_id, HuntRound.character_id == c.id)
                .with_for_update()
            )
            if state is None:
                return await self._road_blocking_view(s, c)
            if state.status != "preparing" or state.state_version != version:
                return await self._round_view(s, c, state)
            return await self._round_view(s, c, state, kind="round_consumables")

    async def toggle_round_consumable(
        self, actor: int, round_id: UUID, version: int, consumable: str
    ) -> RoadView | RoundView | None:
        if consumable not in {HEAL_CONSUMABLE, PURIFY_CONSUMABLE}:
            return None
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            state = await s.scalar(
                select(HuntRound)
                .where(HuntRound.id == round_id, HuntRound.character_id == c.id)
                .with_for_update()
            )
            if state is None:
                return await self._road_blocking_view(s, c)
            if state.status != "preparing":
                return await self._round_view(s, c, state)
            if state.state_version != version:
                return await self._round_view(s, c, state, kind="round_consumables")
            stack = await s.scalar(
                select(ConsumableStack)
                .where(
                    ConsumableStack.character_id == c.id,
                    ConsumableStack.consumable_id == consumable,
                    ConsumableStack.quantity > 0,
                )
                .with_for_update()
            )
            if stack is not None:
                if consumable == HEAL_CONSUMABLE:
                    state.prepared_heal = not state.prepared_heal
                else:
                    state.prepared_purify = not state.prepared_purify
                state.state_version += 1
            return await self._round_view(s, c, state, kind="round_consumables")

    async def start_round(
        self, actor: int, round_id: UUID, version: int
    ) -> RoadView | RoundView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            profile = await self._round_profile(s, c, world)
            if profile is None:
                return None
            state = await s.scalar(
                select(HuntRound)
                .where(HuntRound.id == round_id, HuntRound.character_id == c.id)
                .with_for_update()
            )
            if state is None:
                return await self._view_for_world(s, c, world)
            if state.status != "preparing" or state.state_version != version:
                return await self._round_view(s, c, state)
            if not await s.scalar(
                select(Unlock).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == profile.round_familiarity,
                )
            ):
                return await self._view_for_world(s, c, world)
            active = await s.scalar(
                select(GameActivity)
                .where(GameActivity.character_id == c.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active is not None:
                return await self._road_blocking_view(s, c)
            equipment_configuration = await load_equipment_configuration(s, c)
            active_art_configuration = await load_active_art_configuration(s, c)
            reconcile_character_hp(c, equipment_configuration)
            now = datetime.now(UTC)
            activity = GameActivity(
                id=uuid4(),
                character_id=c.id,
                content_id=ROUND_CONTENT,
                status="active",
                state_version=state.state_version,
                ruleset_version=RULESET,
                last_valid_action_at=now,
            )
            s.add(activity)
            await s.flush()
            state.activity_id = activity.id
            state.status = "active"
            state.started_at = now
            state.config_snapshot = {
                "local_id": profile.local_id,
                "character_class": c.character_class,
                "race": c.race,
                "level_at_start": c.level,
                "ruleset_version": RULESET,
                "combat_configuration": (
                    equipment_configuration.to_data(RULESET)
                    | active_art_configuration.to_data()
                ),
                "prepared_consumables": {
                    HEAL_CONSUMABLE: bool(state.prepared_heal),
                    PURIFY_CONSUMABLE: bool(state.prepared_purify),
                },
            }
            state.state_version += 1
            activity.state_version = state.state_version
            await self._preflight_or_materialize(s, c, state, now, wall_now=now)
            activity = await self._round_activity(s, state)
            if activity is not None and activity.content_id in {
                PVPVE_CONTENT,
                PVPVE_QUEUE_CONTENT,
            }:
                pvpve_view = await self.pvpve.view_for_activity(s, c, activity)
                if pvpve_view is not None:
                    return pvpve_view
                return await self._road_blocking_view(s, c)
            return await self._round_view(s, c, state)

    async def cancel_round(
        self, actor: int, round_id: UUID, version: int
    ) -> RoadView | RoundView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            state = await s.scalar(
                select(HuntRound)
                .where(HuntRound.id == round_id, HuntRound.character_id == c.id)
                .with_for_update()
            )
            if state is None:
                return await self._road_blocking_view(s, c)
            if state.status != "active" or state.state_version != version:
                return await self._round_view(s, c, state)
            current = await self._current_encounter(s, state.id, lock=True)
            if current is None:
                await self._finish_round(s, state, "cancelled")
            else:
                state.cancel_requested = True
                state.state_version += 1
                activity = await self._round_activity(s, state)
                if activity is not None:
                    activity.state_version = state.state_version
                    activity.last_valid_action_at = datetime.now(UTC)
            return await self._round_view(s, c, state)

    async def engage_round_elite(
        self, actor: int, round_id: UUID, version: int
    ) -> RoadView | RoundView | None:
        async with self.sessions.begin() as s:
            # Serialize the transition from the interrupted Ronda blocker to its
            # Elite foreground combat with configuration mutations and other
            # activity starts. Keep Character first, like start_round/_locked_world.
            c = await s.scalar(
                select(Character)
                .where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
                .with_for_update()
            )
            if c is None:
                return None
            state = await s.scalar(
                select(HuntRound)
                .where(HuntRound.id == round_id, HuntRound.character_id == c.id)
                .with_for_update()
            )
            if state is None:
                return await self._road_blocking_view(s, c)
            if state.elite_engaged or (
                state.status == "ended" and state.end_reason == "elite_engaged"
            ):
                return await super()._road_blocking_view(s, c)
            if state.status != "interrupted" or state.end_reason != "elite":
                return await self._round_view(s, c, state)
            if state.state_version != version:
                return await self._round_view(s, c, state)
            encounter = await self._current_encounter(
                s, state.id, lock=True, statuses=("interrupted",)
            )
            if encounter is None:
                return await self._round_view(s, c, state)
            active = await s.scalar(
                select(GameActivity)
                .where(GameActivity.character_id == c.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active is not None:
                return await super()._road_blocking_view(s, c)
            now = datetime.now(UTC)
            activity = GameActivity(
                id=uuid4(),
                character_id=c.id,
                content_id=HUNT_CONTENT,
                status="active",
                state_version=encounter.state_version,
                ruleset_version=_encounter_ruleset(encounter.combat_snapshot),
                last_valid_action_at=now,
            )
            s.add(activity)
            await s.flush()
            s.add(Encounter(id=encounter.id, game_activity_id=activity.id))
            await s.flush()
            s.add(
                CombatRecord(
                    id=encounter.combat_id,
                    encounter_id=encounter.id,
                    snapshot=encounter.combat_snapshot,
                )
            )
            context_snapshot = dict(state.config_snapshot or {})
            pvpve_context = self._pvpve_context(context_snapshot)
            s.add(
                HuntContext(
                    game_activity_id=activity.id,
                    character_id=c.id,
                    local_id=str((state.config_snapshot or {}).get("local_id", ROAD_LOCATION)),
                    creature_id=encounter.creature_id,
                    category=encounter.category,
                    enemy_level=encounter.enemy_level,
                    variant=encounter.variant,
                    seed=encounter.seed,
                    loot_profile="hunt",
                    **pvpve_context,
                )
            )
            if pvpve_context:
                state.config_snapshot = self._clear_pvpve_context(context_snapshot)
            encounter.activity_id = activity.id
            encounter.status = "elite_combat"
            state.elite_engaged = True
            # The Ronda itself has ended at the interruption boundary.  Once the
            # persisted Elite is engaged, the manual encounter becomes the sole
            # foreground authority; the hidden round result must not block a later batch.
            state.status = "ended"
            state.end_reason = "elite_engaged"
            state.result_acknowledged = True
            state.completed_at = now
            state.state_version += 1
            await s.flush()
            return await self._combat_view(s, c, activity)

    async def round_back(
        self, actor: int, round_id: UUID | None = None
    ) -> RoadView | RoundView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            state = None
            cancelled_preparation = False
            if round_id is not None:
                state = await s.scalar(
                    select(HuntRound)
                    .where(HuntRound.id == round_id, HuntRound.character_id == c.id)
                    .with_for_update()
                )
            if state is not None and state.status == "preparing":
                # Leaving preparation is free: no Vigor or Consumables have been
                # reserved yet. Resolve only this uncommitted draft and return to
                # the batch-size selection at the same Local.
                state.status = "cancelled"
                state.result_acknowledged = True
                state.completed_at = datetime.now(UTC)
                state.state_version += 1
                cancelled_preparation = True
            if state is not None and state.status in ROUND_RESULT_STATUSES:
                state.result_acknowledged = True
            # A stale interruption/result callback cannot visually escape a manual
            # Elite encounter that already became foreground-authoritative.
            blocking = await super()._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if cancelled_preparation:
                local = await self._view_for_world(s, c, world)
                return RoadView(
                    "round_select",
                    c.id,
                    world.location,
                    familiar=local.familiar,
                    vigor=c.vigor,
                    max_vigor=c.max_vigor,
                    name=c.name,
                    hp=c.hp,
                    max_hp=c.max_hp,
                )
            if world.location in {ROAD, REFUGE, CHARNECA, BOSQUE, RUINS}:
                return await self._view_for_world(s, c, world)
            location = world.location
            return RoadView(
                "hunt_prepare",
                c.id,
                location,
                vigor=c.vigor,
                max_vigor=c.max_vigor,
                name=c.name,
                hp=c.hp,
                max_hp=c.max_hp,
            )

    async def advance_due_rounds(self, limit: int = 50) -> int:
        """Advance timed encounters without requiring a Telegram interaction."""
        processed = 0
        while processed < limit:
            queue_refresh: tuple[int, UUID] | None = None
            async with self.sessions.begin() as s:
                now = datetime.now(UTC)
                state = await s.scalar(
                    select(HuntRound)
                    .where(
                        HuntRound.status == "active",
                        HuntRound.next_resolution_at.is_not(None),
                        HuntRound.next_resolution_at <= now,
                    )
                    .order_by(HuntRound.next_resolution_at, HuntRound.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if state is None:
                    return processed
                c = await s.scalar(
                    select(Character).where(Character.id == state.character_id).with_for_update()
                )
                if c is None:
                    await self._finish_round(s, state, "ended", "invalid_character")
                else:
                    activity = await self._round_activity(s, state)
                    if activity is not None and activity.content_id == PVPVE_QUEUE_CONTENT:
                        queue_refresh = (c.telegram_id, activity.id)
                    elif activity is not None and activity.content_id == PVPVE_CONTENT:
                        state.next_resolution_at = None
                        state.state_version += 1
                        activity.state_version = state.state_version
                    else:
                        await self._advance_round_locked(s, c, state, now)
                processed += 1
            if queue_refresh is not None:
                await self.pvpve.refresh_queue(*queue_refresh)
        return processed

    async def _advance_round_locked(self, s, c, state, now: datetime) -> None:
        guard = 0
        while (
            state.status == "active"
            and state.next_resolution_at is not None
            and state.next_resolution_at <= now
        ):
            guard += 1
            if guard > state.batch_size + 1:
                raise RuntimeError("hunt round advancement exceeded batch guard")
            due_at = state.next_resolution_at
            # A delayed worker must replay each economic decision at its
            # scheduled boundary. Using worker wall-clock here would let later
            # Vigor finance encounters that should already have been skipped.
            await reconcile_character_vigor(s, c, now=due_at)
            encounter = await self._current_encounter(
                s, state.id, lock=True, statuses=("materialized",)
            )
            if encounter is None:
                state.next_resolution_at = None
                await self._preflight_or_materialize(s, c, state, due_at)
                continue
            await self._resolve_auto_encounter(s, c, state, encounter, due_at)
            if state.status == "active":
                await self._preflight_or_materialize(s, c, state, due_at)

    async def _preflight_or_materialize(
        self,
        s,
        c,
        state,
        anchor: datetime,
        *,
        wall_now: datetime | None = None,
        vigor_anchor: datetime | None = None,
    ) -> None:
        if state.status != "active":
            return
        if state.cancel_requested:
            await self._finish_round(s, state, "cancelled")
            return
        if state.completed_encounters >= state.batch_size:
            await self._finish_round(s, state, "completed")
            return
        await self._retry_blocked_deliveries(s, c)
        if c.delivery_blocked:
            inventory_blocked = await self._inventory_slots(s, c.id) >= (
                await inventory_capacity(s, c.id)
            )
            pending_blocked = await self._pending_slots(s, c.id) <= 0
            reason = (
                "inventory_pending"
                if inventory_blocked and pending_blocked
                else "inventory"
                if inventory_blocked
                else "pending"
            )
            await self._finish_round(s, state, "ended", reason)
            return
        await reconcile_character_vigor(s, c, now=vigor_anchor or anchor)
        if c.vigor < 2:
            await self._finish_round(s, state, "ended", "vigor")
            return
        snapshot = dict(state.config_snapshot or {})
        continue_after_pvp = bool(snapshot.pop("pvpve_continue_after_win", False))
        if continue_after_pvp:
            state.config_snapshot = snapshot
        if (
            not continue_after_pvp
            and c.max_hp > 0
            and c.hp < c.max_hp * SAFETY_THRESHOLD
        ):
            await self._finish_round(s, state, "ended", "hp")
            return
        current = await self._current_encounter(
            s, state.id, lock=True, statuses=("materialized",)
        )
        if current is not None:
            return
        ordinal = state.completed_encounters + 1
        snapshot = dict(state.config_snapshot or {})
        now = wall_now or datetime.now(UTC)
        if snapshot.get("pvpve_checked_for") != ordinal:
            if anchor + ROUND_CADENCE > now:
                activity = await self._round_activity(s, state)
                world = await s.scalar(
                    select(WorldState).where(WorldState.character_id == c.id)
                )
                profile = hunt_profile_for_local_id(snapshot.get("local_id"))
                if activity is not None and world is not None and profile is not None:
                    if await self.pvpve.queue_round_hunt(
                        s,
                        c,
                        world,
                        profile,
                        state,
                        activity,
                        now=now,
                        frontier_at=anchor + ROUND_CADENCE,
                    ):
                        return
            snapshot["pvpve_checked_for"] = ordinal
            state.config_snapshot = snapshot
        await self._materialize_next(s, c, state, anchor)

    async def continue_round_after_queue(
        self,
        session,
        queue,
        character,
        activity,
        *,
        anchor: datetime,
        now: datetime | None = None,
    ) -> bool:
        state = await session.scalar(
            select(HuntRound)
            .where(HuntRound.activity_id == activity.id)
            .with_for_update()
        )
        if state is None or state.status != "active":
            return False
        activity.content_id = ROUND_CONTENT
        activity.status = "active"
        state.next_resolution_at = None
        state.state_version += 1
        actual_now = now or datetime.now(UTC)
        # The queue expires at the next official Ronda frontier. Materialize the
        # queued prey from the beginning of this interval so it resolves at that
        # same boundary, preserving exactly three minutes per encounter.
        interval_start = anchor - ROUND_CADENCE
        activity.state_version = state.state_version
        activity.last_valid_action_at = actual_now
        await self._preflight_or_materialize(
            session,
            character,
            state,
            interval_start,
            wall_now=actual_now,
            vigor_anchor=min(actual_now, anchor),
        )
        if (
            state.status == "active"
            and state.next_resolution_at is not None
            and state.next_resolution_at <= actual_now
        ):
            await self._advance_round_locked(session, character, state, actual_now)
        return activity.content_id == ROUND_CONTENT and (
            state.status == "active"
            or (state.status == "interrupted" and state.end_reason == "elite")
        )

    async def continue_round_after_pvp(
        self,
        session,
        collision,
        queue,
        member,
        character,
        activity,
        *,
        reference_level: int,
        anchor: datetime,
    ) -> bool:
        state = await session.scalar(
            select(HuntRound)
            .where(HuntRound.activity_id == activity.id)
            .with_for_update()
        )
        if state is None or state.status != "active":
            return False
        state.config_snapshot = {
            **(state.config_snapshot or {}),
            "pvpve_checked_for": state.completed_encounters + 1,
            "pvpve_collision_id": collision.id.hex,
            "pvpve_reference_level": reference_level,
            "pvpve_domain_eligible": bool(member.domain_eligible),
            "pvpve_continue_after_win": True,
        }
        activity.content_id = ROUND_CONTENT
        activity.status = "active"
        state.next_resolution_at = None
        state.state_version += 1
        activity.state_version = state.state_version
        activity.last_valid_action_at = anchor
        await self._preflight_or_materialize(
            session, character, state, anchor, wall_now=anchor
        )
        return activity.content_id == ROUND_CONTENT and (
            state.status == "active"
            or (state.status == "interrupted" and state.end_reason == "elite")
        )

    async def finish_round_after_pvp_defeat(
        self,
        session,
        member,
        character,
        activity,
        *,
        local_id: str,
        world,
        now: datetime,
    ) -> bool:
        state = await session.scalar(
            select(HuntRound)
            .where(HuntRound.activity_id == activity.id)
            .with_for_update()
        )
        if state is None or state.status != "active":
            return False
        recovery_brazier, recovery_location = await self._recover_normal_pve_defeat(
            session, character, local_id, world
        )
        if recovery_brazier is not None:
            state.config_snapshot = {
                **(state.config_snapshot or {}),
                "recovery_brazier": recovery_brazier,
                "recovery_location": recovery_location,
            }
        await self._finish_round(session, state, "defeated", "pvpve_defeat")
        state.completed_at = now
        state.result_acknowledged = False
        member.result_acknowledged = True
        return True

    async def finish_round_after_queue_invalid(
        self, session, activity, *, now: datetime
    ) -> bool:
        state = await session.scalar(
            select(HuntRound)
            .where(HuntRound.activity_id == activity.id)
            .with_for_update()
        )
        if state is None or state.status != "active":
            return False
        await self._finish_round(session, state, "ended", "pvpve_context_changed")
        state.completed_at = now
        return True

    @staticmethod
    def _pvpve_context(snapshot: dict) -> dict:
        raw_id = snapshot.get("pvpve_collision_id")
        if not isinstance(raw_id, str):
            return {}
        try:
            collision_id = UUID(hex=raw_id)
        except ValueError:
            return {}
        return {
            "pvpve_collision_id": collision_id,
            "pvpve_reference_level": int(snapshot.get("pvpve_reference_level") or 0) or None,
            "pvpve_domain_eligible": bool(snapshot.get("pvpve_domain_eligible")),
        }

    @staticmethod
    def _clear_pvpve_context(snapshot: dict) -> dict:
        updated = dict(snapshot)
        for key in (
            "pvpve_collision_id",
            "pvpve_reference_level",
            "pvpve_domain_eligible",
            "pvpve_continue_after_win",
        ):
            updated.pop(key, None)
        return updated

    async def _materialize_next(self, s, c, state, anchor: datetime) -> None:
        ordinal = state.completed_encounters + 1
        seed = f"{state.seed}:encounter:{ordinal}"
        round_configuration = state.config_snapshot or {}
        local_id = round_configuration.get("local_id")
        profile = hunt_profile_for_local_id(local_id)
        creature = select_creature(seed, c.level, profile=profile)
        enemy_level = min(c.level, creature.max_level)
        variant = select_variant(seed, creature, profile=profile)
        combat_id = uuid4()
        encounter_id = uuid4()
        raw_combat_configuration = round_configuration.get("combat_configuration")
        raw_active_arts = (
            raw_combat_configuration.get("active_arts")
            if isinstance(raw_combat_configuration, dict)
            else None
        )
        frozen_active_arts = None
        if isinstance(raw_active_arts, list):
            frozen_active_arts = tuple(
                str(entry.get("art_id"))
                for entry in raw_active_arts
                if isinstance(entry, dict) and entry.get("art_id")
            )
        if isinstance(raw_combat_configuration, dict):
            equipment_configuration = equipment_configuration_from_data(
                raw_combat_configuration
            )
            encounter_ruleset = str(
                raw_combat_configuration.get("ruleset_version", RULESET)
            )
        else:
            # Legacy Ronda snapshots did not contain item state. Never add current
            # equipment retroactively to an already-started batch.
            equipment_configuration = None
            encounter_ruleset = str(round_configuration.get("ruleset_version", RULESET))
        combat = create_road_combat(
            combat_id,
            c.name,
            str(round_configuration.get("character_class", c.character_class)),
            str(round_configuration.get("race", c.race)),
            c.hp,
            creature,
            enemy_level,
            variant,
            player_level=c.level,
            equipment_configuration=equipment_configuration,
            ruleset_version=encounter_ruleset,
            location_label=profile.label,
            active_art_ids=frozen_active_arts,
        )
        if isinstance(raw_active_arts, list):
            combat.configuration_snapshot = dict(raw_combat_configuration)
        encounter = HuntRoundEncounter(
            id=encounter_id,
            round_id=state.id,
            ordinal=ordinal,
            combat_id=combat_id,
            seed=seed,
            creature_id=creature.creature_id,
            category=creature.category,
            enemy_level=enemy_level,
            variant=variant,
            status="materialized",
            state_version=combat.version,
            combat_snapshot=encode(combat),
        )
        s.add(encounter)
        await self._bestiary(
            s,
            c.id,
            creature.creature_id,
            variant=variant,
            elite=creature.category == "elite",
            grant_observation_xp=True,
            observation_level=enemy_level,
            observation_category=creature.category,
        )
        await self._record_charneca_habitat(
            s, c.id, creature.creature_id, profile
        )
        if creature.category == "elite":
            encounter.status = "interrupted"
            state.status = "interrupted"
            state.end_reason = "elite"
            state.next_resolution_at = None
            state.completed_at = datetime.now(UTC)
            state.state_version += 1
            activity = await self._round_activity(s, state)
            if activity is not None:
                activity.status = "completed"
                activity.state_version = state.state_version
                activity.last_valid_action_at = datetime.now(UTC)
            return
        state.next_resolution_at = anchor + ROUND_CADENCE
        state.state_version += 1
        activity = await self._round_activity(s, state)
        if activity is not None:
            activity.state_version = state.state_version
            activity.last_valid_action_at = datetime.now(UTC)

    async def _resolve_auto_encounter(self, s, c, state, encounter, due_at: datetime) -> None:
        combat = decode(
            encounter.combat_snapshot,
            encounter.combat_id,
            _encounter_ruleset(encounter.combat_snapshot),
            encounter.state_version,
        )
        steps = 0
        consumable_uses = 0
        consumable_limit = CONSUMABLE_LIMITS.get(encounter.category, 0)
        while combat.result is None:
            steps += 1
            if steps > 200:
                raise RuntimeError("automatic hunt combat exceeded action guard")
            choice = await self._choose_round_action(
                s,
                c,
                state,
                combat,
                consumable_uses=consumable_uses,
                consumable_limit=consumable_limit,
            )
            if choice is None:
                raise RuntimeError("automatic hunt combat has no valid action")
            kind, target = choice
            before = combat.version
            if kind == "heal":
                stack = await self._consumable_stack(s, c.id, HEAL_CONSUMABLE, lock=True)
                if stack is None or stack.quantity <= 0:
                    state.prepared_heal = False
                    continue
                updated = use_heal_consumable(combat)
                if updated.version != before:
                    stack.quantity -= 1
                    consumable_uses += 1
                combat = updated
            elif kind == "action_self":
                combat = act(
                    combat,
                    str(target),
                    target_id=combat.fighters["player"].id,
                )
            elif kind == "purify_dot":
                stack = await self._consumable_stack(s, c.id, PURIFY_CONSUMABLE, lock=True)
                if stack is None or stack.quantity <= 0:
                    state.prepared_purify = False
                    continue
                updated = use_purification_consumable(combat, dot_index=int(target))
                if updated.version != before:
                    stack.quantity -= 1
                    consumable_uses += 1
                combat = updated
            elif kind == "purify_effect":
                stack = await self._consumable_stack(s, c.id, PURIFY_CONSUMABLE, lock=True)
                if stack is None or stack.quantity <= 0:
                    state.prepared_purify = False
                    continue
                updated = use_purification_consumable(combat, effect_index=int(target))
                if updated.version != before:
                    stack.quantity -= 1
                    consumable_uses += 1
                combat = updated
            else:
                combat = act(combat, str(target))
            if combat.version == before:
                # State changed underneath a preferred action; deterministic fallback.
                actions = allowed_actions(combat)
                if "attack" in actions:
                    combat = act(combat, "attack")
                elif actions:
                    combat = act(combat, actions[0])
                else:
                    raise RuntimeError("automatic hunt fallback has no valid action")

        encounter.combat_snapshot = encode(combat)
        encounter.state_version = combat.version
        encounter.resolved_at = datetime.now(UTC)
        c.hp = combat.fighters["player"].hp

        child = GameActivity(
            id=uuid4(),
            character_id=c.id,
            content_id=ROUND_ENCOUNTER_CONTENT,
            status="completed" if combat.result == "victory" else "failed",
            state_version=combat.version,
            ruleset_version=combat.ruleset,
            last_valid_action_at=datetime.now(UTC),
        )
        s.add(child)
        await s.flush()
        s.add(Encounter(id=encounter.id, game_activity_id=child.id))
        await s.flush()
        s.add(
            CombatRecord(
                id=encounter.combat_id,
                encounter_id=encounter.id,
                snapshot=encode(combat),
            )
        )
        context_snapshot = dict(state.config_snapshot or {})
        pvpve_context = self._pvpve_context(context_snapshot)
        context = HuntContext(
            game_activity_id=child.id,
            character_id=c.id,
            local_id=str((state.config_snapshot or {}).get("local_id", ROAD_LOCATION)),
            creature_id=encounter.creature_id,
            category=encounter.category,
            enemy_level=encounter.enemy_level,
            variant=encounter.variant,
            seed=encounter.seed,
            loot_profile="round",
            result_acknowledged=True,
            **pvpve_context,
        )
        s.add(context)
        if pvpve_context:
            state.config_snapshot = self._clear_pvpve_context(context_snapshot)
        encounter.activity_id = child.id
        await s.flush()
        evidence = await self._record_bestiary_combat_events(s, c.id, context, combat)
        await self._record_ttk(s, c, context, combat, source=SOURCE_ROUND_AUTO)

        if combat.result == "defeat":
            encounter.status = "defeated"
            local_id = str((state.config_snapshot or {}).get("local_id", ROAD_LOCATION))
            recovery_brazier, recovery_location = await self._recover_normal_pve_defeat(
                s, c, local_id
            )
            if recovery_brazier is not None:
                state.config_snapshot = {
                    **(state.config_snapshot or {}),
                    "recovery_brazier": recovery_brazier,
                    "recovery_location": recovery_location,
                }
            state.next_resolution_at = None
            await self._finish_round(s, state, "defeated")
            if context.pvpve_collision_id is not None:
                await self.pvpve.finish_prey_member(
                    s, context.pvpve_collision_id, c.id, victory=False
                )
            return

        encounter.status = "completed"
        raw_configuration = (state.config_snapshot or {}).get("combat_configuration")
        frozen_configuration = (
            equipment_configuration_from_data(raw_configuration)
            if isinstance(raw_configuration, dict)
            else EquipmentConfigurationSnapshot(0)
        )
        await self._settle_hunt(
            s,
            c,
            child,
            encounter.id,
            evidence,
            equipment_configuration=frozen_configuration,
            now=due_at,
        )
        state.completed_encounters += 1
        state.next_resolution_at = None
        state.state_version += 1
        activity = await self._round_activity(s, state)
        if activity is not None:
            activity.state_version = state.state_version
            activity.last_valid_action_at = datetime.now(UTC)

        if state.cancel_requested:
            await self._finish_round(s, state, "cancelled")
        elif state.completed_encounters >= state.batch_size:
            await self._finish_round(s, state, "completed")
        elif c.delivery_blocked:
            inventory_blocked = await self._inventory_slots(s, c.id) >= (
                await inventory_capacity(s, c.id)
            )
            pending_blocked = await self._pending_slots(s, c.id) <= 0
            reason = (
                "inventory_pending"
                if inventory_blocked and pending_blocked
                else "inventory"
                if inventory_blocked
                else "pending"
            )
            await self._finish_round(s, state, "ended", reason)
        elif c.vigor < 2:
            await self._finish_round(s, state, "ended", "vigor")
        elif c.max_hp > 0 and c.hp < c.max_hp * SAFETY_THRESHOLD:
            await self._finish_round(s, state, "ended", "hp")

    async def _choose_round_action(
        self,
        s,
        c,
        state,
        combat,
        *,
        consumable_uses: int = 0,
        consumable_limit: int = 0,
    ):
        actions = allowed_actions(combat)
        if not actions:
            return None
        player = combat.fighters["player"]
        hp_ratio = player.hp / player.stats.hp if player.stats.hp else Decimal(0)
        can_consumable = (
            consumable_uses < consumable_limit
            and consumable_available(combat)
        )

        purify_available = (
            state.prepared_purify
            and can_consumable
            and (await self._consumable_quantity(s, c.id, PURIFY_CONSUMABLE)) > 0
        )
        heal_available = (
            state.prepared_heal
            and can_consumable
            and (await self._consumable_quantity(s, c.id, HEAL_CONSUMABLE)) > 0
            and self._effective_heal(combat) >= player.stats.hp * MIN_EFFECTIVE_HEAL
        )

        if purify_available:
            lethal = self._lethal_purification_candidate(combat)
            if lethal is not None:
                return lethal

        recovery_art = self._recovery_art_choice(combat, actions)
        if hp_ratio <= CRITICAL_THRESHOLD and heal_available:
            if recovery_art is not None:
                return ("action_self", recovery_art)
            return ("heal", None)
        if hp_ratio <= CRITICAL_THRESHOLD and recovery_art is not None:
            return ("action_self", recovery_art)
        if purify_available:
            critical = self._purification_candidate(combat, "critical")
            if critical is not None:
                return critical
        if hp_ratio <= RECOVERY_THRESHOLD and heal_available:
            if recovery_art is not None:
                return ("action_self", recovery_art)
            return ("heal", None)
        if hp_ratio <= RECOVERY_THRESHOLD and recovery_art is not None:
            return ("action_self", recovery_art)
        if purify_available:
            high = self._purification_candidate(combat, "high")
            if high is not None:
                return high

        danger = hp_ratio <= SAFETY_THRESHOLD
        if danger and "defend" in actions:
            return ("action", "defend")
        if "defend" in actions:
            return ("action", "defend")
        available_actions = player_actions_for(combat)
        offensive_arts = tuple(
            action
            for action in actions
            if action.startswith(("class_art.", "path_art."))
            and action in available_actions
            and available_actions[action].coefficient > 0
            and available_actions[action].effect_removal is None
        )
        # GDD §49.12 gives equipped AoE attacks priority when at least two
        # living enemies are valid targets. Keep the existing action order for
        # single-target encounters and as the normal offensive fallback.
        active_art = next(
            (
                action
                for action in offensive_arts
                if available_actions[action].target_mode == "all_opponents"
                and len(action_target_ids(combat, action)) >= 2
            ),
            None,
        )
        if active_art is None:
            active_art = next(iter(offensive_arts), None)
        if active_art is not None:
            return ("action", active_art)
        if "art" in actions:
            return ("action", "art")
        if "attack" in actions:
            return ("action", "attack")
        return ("action", actions[0])

    def _effective_heal(self, combat) -> Decimal:
        return effective_heal_amount(combat)

    @staticmethod
    def _recovery_art_choice(combat, actions: tuple[str, ...]) -> str | None:
        """Select the first equipped, legal recovery Art meeting the GDD floor."""
        player = combat.fighters["player"]
        available = player_actions_for(combat)
        for action_id in actions:
            action = available.get(action_id)
            if (
                action is None
                or not action_id.startswith(("class_art.", "path_art."))
                or action.heal_coefficient <= 0
                or action.target_mode not in {"self", "ally", "ally_or_self"}
                or action.effect_removal is not None
            ):
                continue
            preview = act(combat, action_id, target_id=player.id)
            if preview is combat:
                continue
            healing = sum(
                (
                    event.effective_healing
                    for event in preview.events[len(combat.events) :]
                    if event.action == action_id
                    and event.actor_entity_id == player.id
                ),
                Decimal(0),
            )
            if healing >= player.stats.hp * MIN_EFFECTIVE_HEAL:
                return action_id
        return None

    def _dot_metrics(self, combat, dot) -> tuple[Decimal, Decimal, Decimal]:
        coefficient = {
            "poison": Decimal("0.12"),
            "bleed": Decimal("0.10"),
            "burn": Decimal("0.15"),
        }.get(dot.kind, Decimal(0))
        snapshots = list(dot.stack_snapshots or [dot.snapshot_attack] * dot.stacks)
        player = combat.fighters["player"]
        source = combat.fighters.get(dot.source)
        attacker_level = source.level if source is not None else player.level
        tick_damage = Decimal(
            dot_damage(snapshots, coefficient, player.stat("defense"), attacker_level)
        )
        without_oldest = Decimal(
            dot_damage(snapshots[1:], coefficient, player.stat("defense"), attacker_level)
        )
        oldest_tick = max(Decimal(0), tick_damage - without_oldest)
        remaining = tick_damage * max(0, dot.remaining)
        removal_gain = oldest_tick * max(0, dot.remaining)
        return remaining, removal_gain, oldest_tick

    def _effect_category(self, effect) -> int:
        if effect.stat == "healing_received":
            return 1
        if effect.stat == "defense":
            return 2
        if effect.stat == "attack":
            return 3
        if effect.stat == "agility":
            return 4
        return 5

    def _purification_candidate(self, combat, tier: str):
        player = combat.fighters["player"]
        candidates: list[tuple[tuple, tuple[str, int]]] = []
        for index, dot in enumerate(combat.dot_states.get("player", [])):
            if dot.remaining <= 0 or dot.stacks <= 0:
                continue
            remaining, removal_gain, _ = self._dot_metrics(combat, dot)
            hp_max = player.stats.hp
            is_critical = remaining >= hp_max * Decimal("0.15")
            is_high = (
                not is_critical
                and (
                    remaining >= hp_max * Decimal("0.10")
                    or (dot.stacks >= 2 and dot.remaining > 0)
                )
            )
            if (tier == "critical" and is_critical) or (tier == "high" and is_high):
                candidates.append(
                    (
                        (
                            0,
                            -removal_gain,
                            -remaining,
                            -dot.stacks,
                            index,
                            dot.kind,
                        ),
                        ("purify_dot", index),
                    )
                )
        for index, effect in enumerate(player.effects):
            if effect.kind != "debuff" or not effect.removable:
                continue
            magnitude = effect.magnitude
            is_critical = (
                effect.stat == "healing_received"
                and magnitude >= Decimal("0.20")
                and player.hp <= player.stats.hp * Decimal("0.40")
            )
            is_high = (
                not is_critical
                and magnitude >= Decimal("0.15")
                and effect.remaining >= 2
            )
            if (tier == "critical" and is_critical) or (tier == "high" and is_high):
                candidates.append(
                    (
                        (
                            self._effect_category(effect),
                            -magnitude,
                            -effect.remaining,
                            index,
                            effect.id,
                        ),
                        ("purify_effect", index),
                    )
                )
        return min(candidates, key=lambda item: item[0])[1] if candidates else None

    def _lethal_purification_candidate(self, combat):
        player = combat.fighters["player"]
        dots = combat.dot_states.get("player", [])
        if not dots:
            return None
        metrics = [self._dot_metrics(combat, dot) for dot in dots]
        next_tick = sum(
            (
                remaining / Decimal(dot.remaining)
                for dot, (remaining, _, _) in zip(dots, metrics, strict=True)
                if dot.remaining > 0
            ),
            Decimal(0),
        )
        if next_tick < player.hp:
            return None
        rescuing = []
        for index, metric in enumerate(metrics):
            oldest_tick = metric[2]
            if next_tick - oldest_tick < player.hp:
                remaining, removal_gain, _ = metric
                dot = dots[index]
                rescuing.append(
                    (
                        (-oldest_tick, -removal_gain, -remaining, -dot.stacks, index, dot.kind),
                        ("purify_dot", index),
                    )
                )
        return min(rescuing, key=lambda item: item[0])[1] if rescuing else None

    async def _consumable_stack(self, s, character_id, consumable_id, *, lock=False):
        statement = select(ConsumableStack).where(
            ConsumableStack.character_id == character_id,
            ConsumableStack.consumable_id == consumable_id,
            ConsumableStack.quantity > 0,
        )
        if lock:
            statement = statement.with_for_update()
        return await s.scalar(statement)

    async def _consumable_quantity(self, s, character_id, consumable_id) -> int:
        value = await s.scalar(
            select(ConsumableStack.quantity).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == consumable_id,
            )
        )
        return int(value or 0)

    async def _current_encounter(
        self,
        s,
        round_id,
        *,
        lock=False,
        statuses=("materialized", "interrupted", "elite_combat"),
    ):
        statement = (
            select(HuntRoundEncounter)
            .where(
                HuntRoundEncounter.round_id == round_id,
                HuntRoundEncounter.status.in_(statuses),
            )
            .order_by(HuntRoundEncounter.ordinal.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update()
        return await s.scalar(statement)

    async def _round_activity(self, s, state):
        if state.activity_id is None:
            return None
        return await s.scalar(
            select(GameActivity).where(GameActivity.id == state.activity_id).with_for_update()
        )

    async def _finish_round(self, s, state, status: str, reason: str | None = None) -> None:
        state.status = status
        state.end_reason = reason
        state.next_resolution_at = None
        state.completed_at = datetime.now(UTC)
        state.state_version += 1
        activity = await self._round_activity(s, state)
        if activity is not None and activity.status == "active":
            activity.status = "failed" if status == "defeated" else "completed"
            activity.state_version = state.state_version
            activity.last_valid_action_at = datetime.now(UTC)

    async def _round_reward_lines(self, s, state) -> tuple[str, ...]:
        activity_ids = (
            await s.scalars(
                select(HuntRoundEncounter.activity_id).where(
                    HuntRoundEncounter.round_id == state.id,
                    HuntRoundEncounter.status == "completed",
                    HuntRoundEncounter.activity_id.is_not(None),
                )
            )
        ).all()
        if not activity_ids:
            return ()
        source_ids = [f"activity:{activity_id}" for activity_id in activity_ids]
        rows = (
            await s.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(RewardEvent.source_id.in_(source_ids))
                .order_by(RewardComponent.id)
            )
        ).all()
        xp = crowns = 0
        stackables: dict[tuple[str, str | None], int] = {}
        individual: list[str] = []
        labels = {
            **MATERIAL_LABELS,
            "material.tdo.catalisador_elite_i": "Catalisador de Elite I",
            "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
            "material.vde.catalisador_elite_ii": "Catalisador de Elite II",
            "material.vde.fragmento_aprimoramento_ii": "Fragmento de Aprimoramento II",
            "material.nareth.catalisador_elite_iii": "Catalisador de Elite III",
            "material.nareth.fragmento_aprimoramento_iii": "Fragmento de Aprimoramento III",
            "material.varzeas.catalisador_elite_iv": "Catalisador de Elite IV",
            "material.varzeas.fragmento_aprimoramento_iv": "Fragmento de Aprimoramento IV",
        }
        resource_icons = {
            "material.tdo.ferro_de_fuligem": "⛏️",
            "material.tdo.couro_escoriado": "🐾",
            "material.tdo.erva_cinzenta": "🌿",
            "material.tdo.residuo_ocaso": "💧",
            "material.tdo.catalisador_elite_i": "⚗️",
            "material.tdo.fragmento_aprimoramento_i": "🪨",
            "material.vde.catalisador_elite_ii": "⚗️",
            "material.vde.fragmento_aprimoramento_ii": "🪨",
            "material.nareth.catalisador_elite_iii": "⚗️",
            "material.nareth.fragmento_aprimoramento_iii": "🪨",
            "material.varzeas.catalisador_elite_iv": "⚗️",
            "material.varzeas.fragmento_aprimoramento_iv": "🪨",
        }
        for row in rows:
            payload = row.payload or {}
            if row.kind in {"xp", "bestiary_observation_xp", "bestiary_first_victory_xp"}:
                xp += row.quantity
            elif row.kind == "crowns":
                crowns += row.quantity
            elif row.kind in {"material", "catalyst", "fragment"}:
                key = (row.kind, row.item_id)
                stackables[key] = stackables.get(key, 0) + row.quantity
            elif row.kind == "equipment":
                slot_icons = {
                    "Principal": "🗡️",
                    "Secundária": "🛡️",
                    "2H": "⚔️",
                    "Cabeça": "🪖",
                    "Torso": "🥋",
                    "Mãos": "🧤",
                    "Pés": "🥾",
                    "Acessório": "💍",
                    "Artefato": "🧿",
                }
                individual.append(
                    f"{slot_icons.get(payload.get('slot'), '🛡️')} "
                    f"{payload.get('item_name', row.item_id or 'Equipamento')} · "
                    f"{payload.get('rarity', 'Raridade desconhecida')}"
                )
            elif row.kind == "rune":
                individual.append(
                    "🔷 Runa "
                    f"{payload.get('family', row.item_id or 'desconhecida')} · "
                    f"{payload.get('rarity', 'Raridade desconhecida')}"
                )
        lines: list[str] = []
        if xp:
            lines.append(f"✨ XP · {xp}")
        if crowns:
            lines.append(f"🪙 Coroas · {crowns}")
        for (_, item_id), quantity in sorted(
            stackables.items(),
            key=lambda item: (
                labels.get(item[0][1], item[0][1] or ""),
                item[0][0],
            ),
        ):
            icon = resource_icons.get(item_id, "🧱")
            lines.append(
                f"{icon} {labels.get(item_id, item_id or 'Recurso')} · {quantity}"
            )
        lines.extend(individual)
        return tuple(lines)

    async def _round_view(self, s, c, state, *, kind: str | None = None) -> RoundView:
        encounter = await self._current_encounter(s, state.id)
        heal_quantity = await self._consumable_quantity(s, c.id, HEAL_CONSUMABLE)
        purify_quantity = await self._consumable_quantity(s, c.id, PURIFY_CONSUMABLE)
        if kind is None:
            kind = {
                "preparing": "round_prepare",
                "active": "round_active",
                "completed": "round_completed",
                "cancelled": "round_cancelled",
                "defeated": "round_defeated",
                "ended": "round_ended",
                "interrupted": "round_interrupted",
            }[state.status]
        reward_lines = (
            await self._round_reward_lines(s, state)
            if state.status in ROUND_RESULT_STATUSES
            else ()
        )
        inventory_blocked = False
        pending_blocked = False
        if state.end_reason in {"inventory", "pending", "inventory_pending"}:
            inventory_blocked = state.end_reason in {"inventory", "inventory_pending"}
            pending_blocked = state.end_reason in {"pending", "inventory_pending"}
        recovery_brazier = (state.config_snapshot or {}).get("recovery_brazier")
        recovery_location = (state.config_snapshot or {}).get("recovery_location")
        route_available = bool(
            recovery_brazier is not None
            and (
                (
                    (state.config_snapshot or {}).get("local_id") == CHARNECA_LOCATION
                    and recovery_location == REFUGE
                )
                or (
                    (state.config_snapshot or {}).get("local_id") == BOSQUE_LOCATION
                    and recovery_location == "Charneca da Fuligem"
                )
                or (
                    (state.config_snapshot or {}).get("local_id") == RUINS_LOCATION
                    and recovery_location
                    in {"Bosque Calcinado", "Charneca da Fuligem", REFUGE}
                )
            )
        )
        flavor = None
        creature_name = None
        enemy_level = 0
        variant = None
        encounter_id = combat_id = None
        if encounter is not None:
            creature = creature_for(encounter.creature_id)
            creature_name = creature.name
            enemy_level = encounter.enemy_level
            variant = VARIANT_LABELS.get(encounter.variant, encounter.variant)
            encounter_id = encounter.id
            combat_id = encounter.combat_id
            combat = decode(
                encounter.combat_snapshot,
                encounter.combat_id,
                _encounter_ruleset(encounter.combat_snapshot),
                encounter.state_version,
            )
            flavor = combat.flavor
        return RoundView(
            kind=kind,
            character_id=c.id,
            location=hunt_profile_for_local_id(
                (state.config_snapshot or {}).get("local_id")
            ).label,
            round_id=state.id,
            activity_id=state.activity_id,
            encounter_id=encounter_id,
            combat_id=combat_id,
            state_version=state.state_version,
            batch_size=state.batch_size,
            completed_encounters=state.completed_encounters,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            reward_lines=reward_lines,
            heal_quantity=heal_quantity,
            purify_quantity=purify_quantity,
            prepared_heal=state.prepared_heal,
            prepared_purify=state.prepared_purify,
            cancel_requested=state.cancel_requested,
            next_resolution_at=state.next_resolution_at,
            end_reason=state.end_reason,
            creature=creature_name,
            enemy_level=enemy_level,
            variant=variant,
            result_text=flavor,
            inventory_blocked=inventory_blocked,
            pending_blocked=pending_blocked,
            recovery_brazier=recovery_brazier,
            recovery_location=recovery_location,
            route_available=route_available,
        )
