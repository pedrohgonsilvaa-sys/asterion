"""Persistent dungeon-run lifecycle and solo Cripta do Ocaso execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BestiaryRecorder
from asterion.application.equipment import equipment_instance_payload
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import CHARNECA, REGION, RoadService
from asterion.domain.combat import (
    CombatConsumableOption,
    act,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import ConsumableFamily
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.dungeons import (
    CRYPT_FAMILY_ID,
    CRYPT_RULESET_VERSION,
    DIFFICULTIES,
    difficulty_gate,
    dungeon_completion_xp,
    dungeon_crowns,
    fragment_material_id,
    material_for_ordinal,
    rarity_with_pity,
    roll_brazier,
    roll_weighted,
    stable_draw,
)
from asterion.domain.equipment_stats import (
    equipment_configuration_from_data,
)
from asterion.domain.road import (
    RULESET,
    enemy_xp,
    materialize_equipment,
    rune_potency,
)
from asterion.domain.road import (
    RUNE_FAMILIES as ROAD_RUNE_FAMILIES,
)
from asterion.domain.tdo_crypt import (
    CRYPT_ENCOUNTERS,
    create_crypt_combat,
    encounter_specs,
    enemy_rewards,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CodexEntry,
    CodexFragment,
    ConsumableStack,
    DungeonPityState,
    DungeonRun,
    DungeonRunEncounter,
    DungeonRunMember,
    Encounter,
    EquipmentItem,
    GameActivity,
    RewardComponent,
    RewardEvent,
    RuneStack,
    Unlock,
    WorldState,
)

D = Decimal
REFUGE = "Refúgio do Ocaso"
CRYPT_LOCATION = "Cripta do Ocaso"
CRYPT_DISCOVERY_UNLOCK = "dungeon.tdo.cripta_ocaso"
CRYPT_KNOWN_PATH_UNLOCK = "known_path.tdo.cripta_ocaso"
CRYPT_FIRST_CLEAR_PREFIX = "dungeon.tdo.cripta_ocaso.first_clear."
CRYPT_REWARD_PREFIX = "dungeon.tdo.cripta_ocaso.run."
CRYPT_CODEX_ENTRY = "codex.location.cripta_do_ocaso"
CRYPT_CONTENT = "dungeon_crypt_encounter"
DUNGEON_ACTIVITY_PREFIX = "dungeon_run_"
DUNGEON_IDLE_LIMIT = timedelta(hours=4)
DUNGEON_ABSOLUTE_LIMIT = timedelta(hours=24)
RUNE_FAMILY_IDS = tuple(family for family, _stat in ROAD_RUNE_FAMILIES)


@dataclass(frozen=True, slots=True)
class DungeonView:
    kind: str
    character_id: UUID
    character_name: str
    level: int
    location: str
    hp: Decimal
    max_hp: Decimal
    vigor: int
    max_vigor: int
    run_id: UUID | None = None
    state_version: int = 0
    difficulty: str | None = None
    difficulty_label: str | None = None
    difficulty_gates: tuple[tuple[str, str], ...] = ()
    ordinal: int = 0
    environment: str = ""
    has_brazier: bool | None = None
    brazier_activated: bool = False
    consumable_uses: int = 0
    consumable_limit: int = 0
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat: object | None = None
    context: str = "dungeon"
    stage: str = "dungeon"
    xp: int = 0
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: CombatConsumableOption | None = None
    reward_lines: tuple[str, ...] = ()
    first_clear: bool = False
    reason: str | None = None


class DungeonService:
    """Global durable run semantics. D1 exposes only solo run creation."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def known(self, actor: int) -> DungeonView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            known = await self._has_unlock(session, character.id, CRYPT_DISCOVERY_UNLOCK)
            if not known:
                return self._view(character, kind="empty")
            stable = await self._has_unlock(
                session, character.id, CRYPT_FIRST_CLEAR_PREFIX + "stable"
            )
            fractured = await self._has_unlock(
                session, character.id, CRYPT_FIRST_CLEAR_PREFIX + "fractured"
            )
            gates = difficulty_gate(
                level=character.level,
                discovered=True,
                stable_first_clear=stable,
                fractured_first_clear=fractured,
            )
            return self._view(
                character,
                kind="known",
                difficulty_gates=tuple(gates.items()),
            )

    async def detail(self, actor: int) -> DungeonView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            if not await self._has_unlock(session, character.id, CRYPT_DISCOVERY_UNLOCK):
                return self._view(character, kind="hidden")
            stable = await self._has_unlock(
                session, character.id, CRYPT_FIRST_CLEAR_PREFIX + "stable"
            )
            fractured = await self._has_unlock(
                session, character.id, CRYPT_FIRST_CLEAR_PREFIX + "fractured"
            )
            gates = difficulty_gate(
                level=character.level,
                discovered=True,
                stable_first_clear=stable,
                fractured_first_clear=fractured,
            )
            return self._view(
                character,
                kind="detail",
                difficulty_gates=tuple(gates.items()),
                first_clear=stable,
            )

    async def start_solo(self, actor: int, difficulty: str) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, lock=True)
            if run is not None:
                if self._expired(run):
                    await self._expire(session, character, run, member)
                    return await self._run_view(session, character, run, member, kind="expired")
                return await self._run_view(session, character, run, member)
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id).with_for_update()
            )
            if (
                difficulty not in DIFFICULTIES
                or world is None
                or world.location != CHARNECA
                or not await self._has_unlock(session, character.id, CRYPT_DISCOVERY_UNLOCK)
            ):
                return self._view(character, kind="detail", reason="gate")
            stable = await self._has_unlock(
                session, character.id, CRYPT_FIRST_CLEAR_PREFIX + "stable"
            )
            fractured = await self._has_unlock(
                session, character.id, CRYPT_FIRST_CLEAR_PREFIX + "fractured"
            )
            gates = difficulty_gate(
                level=character.level,
                discovered=True,
                stable_first_clear=stable,
                fractured_first_clear=fractured,
            )
            if gates.get(difficulty) != "available":
                return self._view(
                    character, kind="detail", difficulty_gates=tuple(gates.items()), reason="gate"
                )
            active_activity = await session.scalar(
                select(GameActivity.id)
                .where(GameActivity.character_id == character.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active_activity is not None:
                return self._view(character, kind="detail", reason="foreground")
            profile = DIFFICULTIES[difficulty]
            if character.vigor < profile.vigor:
                return self._view(character, kind="detail", reason="vigor")
            equipment = await load_equipment_configuration(session, character)
            reconcile_character_hp(character, equipment)
            arts = await load_active_art_configuration(session, character)
            snapshot = equipment.to_data(RULESET) | arts.to_data()
            run_id = uuid4()
            seed = uuid4().hex
            now = datetime.now(UTC)
            character.vigor -= profile.vigor
            run = DungeonRun(
                id=run_id,
                dungeon_family_id=CRYPT_FAMILY_ID,
                difficulty=difficulty,
                status="active",
                ruleset_version=CRYPT_RULESET_VERSION,
                content_version="tdo-1.0.11",
                reference_level=profile.reference_level,
                initial_group_size=1,
                current_encounter_ordinal=1,
                state_version=0,
                seed=seed,
                has_brazier=roll_brazier(seed, difficulty),
                brazier_activated=False,
                brazier_after_encounter=3,
                active_checkpoint_encounter=None,
                progress={"internal_xp": 0, "retry_available": False},
                vigor_refunded=False,
                created_at=now,
                last_activity_at=now,
            )
            member = DungeonRunMember(
                run_id=run_id,
                character_id=character.id,
                position=1,
                status="active",
                vigor_reserved=profile.vigor,
                consumable_uses=0,
                combat_configuration=snapshot,
                hp=character.hp,
                max_hp=character.max_hp,
                run_state={},
                contribution={},
            )
            session.add_all([run, member])
            session.add_all(
                DungeonRunEncounter(
                    run_id=run_id,
                    encounter_ordinal=ordinal,
                    definition_id=CRYPT_ENCOUNTERS[ordinal].definition_id,
                    status="pending",
                    activity_id=None,
                    attempt_count=0,
                    progress={},
                    reward_settled=False,
                )
                for ordinal in range(1, 6)
            )
            await session.flush()
            await self._create_lobby_activity(session, character, run)
            await self._ensure_codex_entry(session, character.id, CRYPT_CODEX_ENTRY)
            world.region = REGION
            world.location = CRYPT_LOCATION
            return await self._run_view(session, character, run, member)

    async def resume(self, actor: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, lock=True)
            if run is None:
                return None
            now = datetime.now(UTC)
            if (
                now - run.last_activity_at >= DUNGEON_IDLE_LIMIT
                or now - run.created_at >= DUNGEON_ABSOLUTE_LIMIT
            ):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            activity = await self._active_activity(session, character.id)
            return await self._run_view(session, character, run, member, activity=activity)

    async def begin_encounter(
        self, actor: int, run_id: UUID, state_version: int
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            if run.state_version != state_version or (run.progress or {}).get("awaiting_brazier"):
                activity = await self._active_activity(session, character.id)
                return await self._run_view(session, character, run, member, activity=activity)
            current = await self._active_activity(session, character.id)
            if current is not None:
                linked = await session.scalar(
                    select(DungeonRunEncounter).where(DungeonRunEncounter.activity_id == current.id)
                )
                if linked is not None:
                    return await self._run_view(session, character, run, member, activity=current)
                current.status = "completed"
                await session.flush()
            encounter = await session.scalar(
                select(DungeonRunEncounter)
                .where(
                    DungeonRunEncounter.run_id == run.id,
                    DungeonRunEncounter.encounter_ordinal == run.current_encounter_ordinal,
                )
                .with_for_update()
            )
            if encounter is None or encounter.status == "completed":
                return await self._run_view(session, character, run, member, kind="stale")
            equipment = equipment_configuration_from_data(member.combat_configuration)
            active_arts = tuple(
                str(entry["art_id"])
                for entry in member.combat_configuration.get("active_arts", ())
                if isinstance(entry, dict) and entry.get("art_id")
            )
            combat = create_crypt_combat(
                uuid4(),
                name=character.name,
                character_class=character.character_class,
                race=character.race,
                hp=member.hp,
                level=character.level,
                difficulty=run.difficulty,
                equipment=equipment,
                active_art_ids=active_arts,
                ordinal=run.current_encounter_ordinal,
                run_seed=run.seed,
            )
            combat.configuration_snapshot = (combat.configuration_snapshot or {}) | {
                "active_arts": list(member.combat_configuration.get("active_arts", ()))
            }
            activity, _, record = await CombatRepository(session).create(
                character, CRYPT_CONTENT, combat
            )
            encounter.activity_id = activity.id
            encounter.status = "active"
            encounter.attempt_count += 1
            encounter.progress = {"event_cursor": 0}
            run.state_version += 1
            run.last_activity_at = datetime.now(UTC)
            await self._record_encounter_observations(
                session, character, run.current_encounter_ordinal
            )
            await self._ensure_codex_for_encounter(
                session, character.id, run.current_encounter_ordinal
            )
            return await self._run_view(
                session,
                character,
                run,
                member,
                activity=activity,
                combat=combat,
                record=record,
                encounter=encounter,
            )

    async def action(
        self,
        actor: int,
        run_id: UUID,
        activity_id: UUID,
        version: int,
        action_id: str,
        target_id: str | None = None,
        *,
        consumable_id: str | None = None,
        effect_id: str | None = None,
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            activity = await self._active_activity(session, character.id)
            encounter = await session.scalar(
                select(DungeonRunEncounter)
                .where(
                    DungeonRunEncounter.run_id == run.id,
                    DungeonRunEncounter.activity_id == activity_id,
                )
                .with_for_update()
            )
            if (
                activity is None
                or activity.id != activity_id
                or encounter is None
                or encounter.status != "active"
                or activity.state_version != version
            ):
                return await self._run_view(session, character, run, member, activity=activity)
            pair = await CombatRepository(session).combat(activity)
            current_encounter, record = pair
            state = decode(
                record.snapshot, record.id, activity.ruleset_version, activity.state_version
            )
            stack = None
            if consumable_id is not None:
                remaining = DIFFICULTIES[run.difficulty].consumable_limit - member.consumable_uses
                if remaining <= 0:
                    return await self._run_view(
                        session,
                        character,
                        run,
                        member,
                        activity=activity,
                        combat=state,
                        record=record,
                        encounter=encounter,
                    )
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
                    return await self._run_view(
                        session,
                        character,
                        run,
                        member,
                        activity=activity,
                        combat=state,
                        record=record,
                        encounter=encounter,
                    )
                updated = use_combat_consumable(
                    state,
                    consumable_id,
                    target_id=target_id or "player",
                    effect_id=effect_id,
                    budget_limit=remaining,
                )
            else:
                updated = act(state, action_id, target_id=target_id)
            if updated.version == state.version:
                return await self._run_view(
                    session,
                    character,
                    run,
                    member,
                    activity=activity,
                    combat=state,
                    record=record,
                    encounter=encounter,
                )
            if stack is not None:
                stack.quantity -= 1
                member.consumable_uses += 1
            record.snapshot = encode(updated)
            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            run.last_activity_at = datetime.now(UTC)
            character.hp = updated.fighters["player"].hp
            member.hp = character.hp
            await self._record_combat_events(session, character, run, encounter, state, updated)
            if updated.result == "victory":
                await self._encounter_victory(
                    session, character, run, member, encounter, activity, updated
                )
                return await self._run_view(session, character, run, member)
            if updated.result == "defeat":
                await self._encounter_defeat(
                    session, character, run, member, encounter, activity, updated
                )
                return await self._run_view(session, character, run, member)
            return await self._run_view(
                session,
                character,
                run,
                member,
                activity=activity,
                combat=updated,
                record=record,
                encounter=current_encounter,
            )

    async def activate_brazier(
        self, actor: int, run_id: UUID, state_version: int
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            progress = dict(run.progress or {})
            if (
                run.state_version != state_version
                or not run.has_brazier
                or run.brazier_activated
                or not progress.get("awaiting_brazier")
                or run.current_encounter_ordinal != 4
            ):
                return await self._run_view(session, character, run, member)
            character.hp = character.max_hp
            member.hp = member.max_hp
            run.brazier_activated = True
            run.active_checkpoint_encounter = 4
            run.state_version += 1
            run.last_activity_at = datetime.now(UTC)
            progress["awaiting_brazier"] = False
            progress["retry_available"] = False
            run.progress = progress
            return await self._run_view(session, character, run, member)

    async def retry(self, actor: int, run_id: UUID, state_version: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            progress = dict(run.progress or {})
            if (
                run.state_version != state_version
                or not run.brazier_activated
                or not progress.get("retry_available")
            ):
                return await self._run_view(session, character, run, member)
            progress["retry_available"] = False
            run.progress = progress
            run.state_version += 1
            run.last_activity_at = datetime.now(UTC)
            return await self._run_view(session, character, run, member)

    async def abandon(self, actor: int, run_id: UUID, state_version: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            activity = await self._active_activity(session, character.id)
            if (
                run.state_version != state_version
                or activity is None
                or await session.scalar(
                    select(Encounter.id).where(Encounter.game_activity_id == activity.id)
                )
                is not None
            ):
                return await self._run_view(session, character, run, member, activity=activity)
            activity.status = "failed"
            await self._refund_vigor(character, run, member)
            run.status = "failed"
            run.failed_at = datetime.now(UTC)
            run.state_version += 1
            progress = dict(run.progress or {})
            progress["internal_xp"] = 0
            progress["abandoned"] = True
            run.progress = progress
            member.status = "left"
            await self._return_to_charneca(session, character.id)
            return await self._run_view(session, character, run, member, kind="failed")

    async def _encounter_victory(
        self, session, character, run, member, encounter, activity, combat
    ) -> None:
        ordinal = encounter.encounter_ordinal
        await self._record_combat_events(session, character, run, encounter, combat, combat)
        specs = encounter_specs(ordinal, run.difficulty)
        for spec in specs:
            fighter = combat.fighters[spec.fighter_key]
            if spec.required_for_victory and fighter.hp <= 0:
                await self.bestiary.record(
                    session,
                    character.id,
                    spec.creature.creature_id,
                    victory=True,
                    elite=spec.creature.category == "elite",
                    observation_category=spec.creature.category,
                )
                if spec.creature.creature_id == "sem_nome":
                    await self._grant_boss_milestone(
                        session, character, run, spec.creature.creature_id
                    )
                    await self._refresh_crypt_boss_mastery(session, character.id)
        encounter.status = "completed"
        encounter.reward_settled = True
        encounter.completed_at = datetime.now(UTC)
        activity.status = "completed"
        member.hp = combat.fighters["player"].hp
        character.hp = member.hp
        progress = dict(run.progress or {})
        earned = sum(
            enemy_xp(level, category, powerlevel_factor=D("0.25"))
            for _, level, category in enemy_rewards(ordinal)
        )
        progress["internal_xp"] = int(progress.get("internal_xp", 0)) + earned
        progress["retry_available"] = False
        run.progress = progress
        if ordinal == 5:
            await self._settle_run(session, character, run, member)
            await self._return_to_charneca(session, character.id)
            return
        run.current_encounter_ordinal = ordinal + 1
        run.state_version += 1
        run.last_activity_at = datetime.now(UTC)
        if ordinal == 3 and run.has_brazier:
            progress["awaiting_brazier"] = True
            run.progress = progress
        await self._create_lobby_activity(session, character, run)

    async def _encounter_defeat(
        self, session, character, run, member, encounter, activity, combat
    ) -> None:
        await self._record_combat_events(session, character, run, encounter, combat, combat)
        encounter.status = "pending"
        activity.status = "failed"
        progress = dict(run.progress or {})
        progress["retry_available"] = False
        if not run.brazier_activated:
            run.status = "failed"
            run.failed_at = datetime.now(UTC)
            progress["internal_xp"] = 0
            run.progress = progress
            run.state_version += 1
            member.status = "left"
            await self._refund_vigor(character, run, member)
            await self._return_to_charneca(session, character.id)
            return
        member.hp = member.max_hp
        character.hp = member.max_hp
        progress["retry_available"] = True
        run.progress = progress
        run.state_version += 1
        run.last_activity_at = datetime.now(UTC)
        await self._create_lobby_activity(session, character, run)

    async def _settle_run(self, session, character, run, member) -> None:
        source = CRYPT_REWARD_PREFIX + run.id.hex
        event = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source)
            .with_for_update()
        )
        if event is None:
            difficulty = run.difficulty
            first_clear_id = CRYPT_FIRST_CLEAR_PREFIX + difficulty
            first_clear = not await self._has_unlock(session, character.id, first_clear_id)
            completion_xp = dungeon_completion_xp(
                run.reference_level, difficulty, first_clear=first_clear
            )
            internal_xp = int((run.progress or {}).get("internal_xp", 0))
            total_xp = internal_xp + completion_xp
            crown_reward = dungeon_crowns(run.reference_level, difficulty)
            profile = DIFFICULTIES[difficulty]
            character.xp += total_xp
            character.crowns += crown_reward
            event = RewardEvent(character_id=character.id, source_id=source)
            session.add(event)
            await session.flush()
            components = [
                RewardComponent(
                    reward_event_id=event.id,
                    kind="xp",
                    item_id=None,
                    quantity=total_xp,
                    payload={
                        "internal": internal_xp,
                        "completion": completion_xp,
                        "first_clear": first_clear,
                    },
                ),
                RewardComponent(
                    reward_event_id=event.id,
                    kind="crowns",
                    item_id=None,
                    quantity=crown_reward,
                    payload={},
                ),
            ]
            material_counts: dict[str, int] = {}
            for ordinal in range(profile.basic_materials):
                material_id = material_for_ordinal(run.seed, ordinal)
                material_counts[material_id] = material_counts.get(material_id, 0) + 1
            material_counts["material.tdo.catalisador_elite_i"] = profile.catalysts
            material_counts["material.tdo.nucleo_cripta_ocaso"] = profile.cores
            material_counts[fragment_material_id(run.reference_level)] = profile.fragments
            for material_id, quantity in sorted(material_counts.items()):
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=material_id,
                        quantity=quantity,
                        payload={"material_id": material_id, "bound": False},
                    )
                )
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    f"{source}:material:{material_id}",
                    bound=False,
                )
            pity = await session.scalar(
                select(DungeonPityState)
                .where(DungeonPityState.character_id == character.id)
                .with_for_update()
            )
            if pity is None:
                pity = DungeonPityState(
                    character_id=character.id, legendary_plus_points=0, mythic_points=0
                )
                session.add(pity)
                await session.flush()
            rarity, legendary_points, mythic_points = rarity_with_pity(
                run.seed, difficulty, pity.legendary_plus_points, pity.mythic_points
            )
            pity.legendary_plus_points = legendary_points
            pity.mythic_points = mythic_points
            equipment_payload = materialize_equipment(
                f"{source}:equipment", rarity, run.reference_level, bound=False
            )
            components.append(
                RewardComponent(
                    reward_event_id=event.id,
                    kind="equipment",
                    item_id=None,
                    quantity=1,
                    payload=equipment_payload,
                )
            )
            await self._deliver_equipment(
                session, character.id, f"{source}:equipment", equipment_payload
            )
            rune_payload = self._roll_rune(run)
            if rune_payload is not None:
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="rune",
                        item_id=rune_payload["family"],
                        quantity=1,
                        payload=rune_payload,
                    )
                )
                await self._deliver_rune(session, character.id, f"{source}:rune", rune_payload)
            has_recipe = await self._has_unlock(
                session, character.id, "recipe.tdo.cripta.relicario_sem_nome"
            )
            if (
                not has_recipe
                and stable_draw(run.seed, "recipe.discovery", 10_000) < profile.recipe_chance * 100
            ):
                await self._ensure_unlock(
                    session, character.id, "recipe.tdo.cripta.relicario_sem_nome"
                )
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="unlock",
                        item_id="recipe.tdo.cripta.relicario_sem_nome",
                        quantity=1,
                        payload={"revealed": True},
                    )
                )
            if first_clear:
                await self._ensure_unlock(session, character.id, first_clear_id)
                if difficulty == "stable":
                    await self._refresh_crypt_boss_mastery(session, character.id)
            await self._record_crypt_codex_completion(session, character.id)
            session.add_all(components)
            run.progress = {
                **(run.progress or {}),
                "internal_xp": 0,
                "completed": True,
                "reward_lines": self._reward_lines(
                    total_xp,
                    crown_reward,
                    material_counts,
                    equipment_payload,
                    rune_payload,
                    not has_recipe
                    and stable_draw(run.seed, "recipe.discovery", 10_000)
                    < profile.recipe_chance * 100,
                ),
                "first_clear": first_clear,
                "consumed_vigor": member.vigor_reserved,
            }
            await consolidate_character_level(session, character)
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.last_activity_at = datetime.now(UTC)
        run.state_version += 1
        member.status = "left"

    def _roll_rune(self, run) -> dict | None:
        profile = DIFFICULTIES[run.difficulty]
        if stable_draw(run.seed, "rune.drop", 10_000) >= profile.rune_chance * 100:
            return None
        rarity = roll_weighted(run.seed, "rune.rarity", profile.rune_rarity_bands)
        family = RUNE_FAMILY_IDS[stable_draw(run.seed, "rune.family", len(RUNE_FAMILY_IDS))]
        return {
            "family": family,
            "rarity": rarity,
            "grade": min(6, max(1, (run.reference_level - 1) // 10 + 1)),
            "potency": rune_potency(family, rarity),
            "bound": False,
        }

    def _reward_lines(self, xp, crowns, materials, equipment, rune, recipe) -> tuple[str, ...]:
        lines = [f"✨ XP · {xp:,}".replace(",", "."), f"🪙 Coroas · {crowns:,}".replace(",", ".")]
        labels = {
            "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
            "material.tdo.couro_escoriado": "Couro Escoriado",
            "material.tdo.erva_cinzenta": "Erva Cinzenta",
            "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
            "material.tdo.catalisador_elite_i": "Catalisador de Elite I",
            "material.tdo.nucleo_cripta_ocaso": "Núcleo da Cripta do Ocaso",
            "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
        }
        for material_id, quantity in sorted(materials.items()):
            lines.append(f"📦 {labels.get(material_id, material_id)} · {quantity}")
        lines.append(
            f"🛡️ {equipment['item_name']} · {equipment['rarity']} · Nv.{equipment['item_level']}"
        )
        if rune:
            lines.append(f"🔷 Runa · {rune['family']} · {rune['rarity']} · Grau {rune['grade']}")
        if recipe:
            lines.append("📜 Receita · Relicário dos Sem-Nome · Revelada")
        return tuple(lines)

    async def _deliver_equipment(self, session, character_id, source_key, payload):
        item_id, item_data = equipment_instance_payload(payload)
        if await self.road._inventory_slots(session, character_id) < 60:
            session.add(
                EquipmentItem(
                    id=item_id,
                    character_id=character_id,
                    source_key=source_key,
                    item_name=item_data["item_name"],
                    rarity=item_data["rarity"],
                    slot=item_data["slot"],
                    item_level=item_data["item_level"],
                    bound=False,
                    payload=item_data,
                )
            )
        else:
            await self.road._pending(session, character_id, source_key, "equipment", item_data)

    async def _deliver_rune(self, session, character_id, source_key, payload):
        stack = await session.scalar(
            select(RuneStack)
            .where(
                RuneStack.character_id == character_id,
                RuneStack.family == payload["family"],
                RuneStack.rarity == payload["rarity"],
                RuneStack.grade == payload["grade"],
                RuneStack.bound.is_(False),
            )
            .with_for_update()
        )
        if stack is not None:
            stack.quantity += 1
        elif await self.road._inventory_slots(session, character_id) < 60:
            session.add(
                RuneStack(
                    character_id=character_id,
                    family=payload["family"],
                    rarity=payload["rarity"],
                    grade=payload["grade"],
                    potency=payload["potency"],
                    quantity=1,
                    bound=False,
                )
            )
        else:
            await self.road._pending(session, character_id, source_key, "rune", payload)

    async def _grant_boss_milestone(self, session, character, run, creature_id):
        source = f"bestiary.first_victory:{creature_id}"
        event = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source)
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        character.xp += 342
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="xp",
                item_id=None,
                quantity=342,
                payload={"bestiary_milestone": True},
            )
        )

    async def _refresh_crypt_boss_mastery(self, session, character_id):
        if not await self._has_unlock(
            session, character_id, CRYPT_FIRST_CLEAR_PREFIX + "stable"
        ):
            return
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id, BestiaryEntry.creature_id == "sem_nome"
            )
            .with_for_update()
        )
        if entry is None:
            return
        evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == "sem_nome",
                    )
                )
            ).all()
        )
        required = {
            "first_victory",
            "phase:nobody_rest",
            "action:peso_sepulcro",
            "action:maos_esquecidos",
        }
        entry.stage = "dominated" if required.issubset(evidence) else entry.stage

    async def _record_encounter_observations(self, session, character, ordinal):
        for spec in encounter_specs(ordinal, "stable"):
            if spec.passive:
                continue
            await self.bestiary.record(
                session,
                character.id,
                spec.creature.creature_id,
                elite=spec.creature.category == "elite",
                observation_category=spec.creature.category,
            )

    async def _record_combat_events(self, session, character, run, encounter, before, after):
        cursor = int((encounter.progress or {}).get("event_cursor", 0))
        if cursor > len(after.events):
            cursor = 0
        specs = encounter_specs(encounter.encounter_ordinal, run.difficulty)
        creature_by_key = {spec.fighter_key: spec.creature for spec in specs}
        boss = after.fighters.get("enemy") if encounter.encounter_ordinal == 5 else None
        for event in after.events[cursor:]:
            if boss is not None:
                for fighter_id, hp in event.fighter_hp_after:
                    if fighter_id == boss.id and boss.stats.hp > 0:
                        ratio = D(hp) / D(boss.stats.hp)
                        await self._phase_evidence(session, character.id, ratio)
            creature = creature_by_key.get(event.actor)
            if creature is None:
                continue
            action_id = event.action.removeprefix("prepare:")
            if action_id.startswith("e0_") or action_id.startswith("e1_"):
                action_id = action_id[3:]
            entry = await session.scalar(
                select(BestiaryEntry)
                .where(
                    BestiaryEntry.character_id == character.id,
                    BestiaryEntry.creature_id == creature.creature_id,
                )
                .with_for_update()
            )
            if entry is not None:
                await self.bestiary.add_evidence(
                    session,
                    entry,
                    character.id,
                    creature.creature_id,
                    f"action:{action_id}",
                    "behavior",
                    4,
                )
                if event.action.startswith("prepare:"):
                    await self.bestiary.add_evidence(
                        session,
                        entry,
                        character.id,
                        creature.creature_id,
                        f"mechanic:prepared_{action_id}",
                        "mechanic",
                        5,
                    )

        encounter.progress = {**(encounter.progress or {}), "event_cursor": len(after.events)}
        if encounter.encounter_ordinal == 5:
            await self._refresh_crypt_boss_mastery(session, character.id)

    async def _phase_evidence(self, session, character_id, hp_ratio):
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id, BestiaryEntry.creature_id == "sem_nome"
            )
            .with_for_update()
        )
        if entry is None:
            return
        if hp_ratio < D("0.70"):
            await self.bestiary.add_evidence(
                session, entry, character_id, "sem_nome", "phase:weight_of_dead", "phase", 5
            )
        if hp_ratio <= D("0.35"):
            await self.bestiary.add_evidence(
                session, entry, character_id, "sem_nome", "phase:nobody_rest", "phase", 5
            )

    async def _ensure_codex_for_encounter(self, session, character_id, ordinal):
        fragments = {
            1: ("codex.location.cripta_do_ocaso", "codex.fragment.crypt.entry"),
            3: ("codex.history.camadas_de_sepultamento", "codex.fragment.crypt.layers"),
            4: ("codex.history.camara_dos_nomes", "codex.fragment.crypt.names"),
        }
        if ordinal == 5:
            return
        values = fragments.get(ordinal)
        if values is None:
            return
        entry_id, fragment_id = values
        await self._ensure_codex_entry(session, character_id, entry_id)
        await self._ensure_fragment(session, character_id, entry_id, fragment_id)

    async def _record_crypt_codex_completion(self, session, character_id):
        for entry_id, fragment_id in (
            ("codex.history.o_ultimo_guardiao", "codex.fragment.crypt.last_guardian"),
            ("codex.history.os_sem_nome", "codex.fragment.crypt.sem_nome"),
        ):
            await self._ensure_codex_entry(session, character_id, entry_id)
            await self._ensure_fragment(session, character_id, entry_id, fragment_id)

    async def _create_lobby_activity(self, session, character, run):
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character.id,
                content_id=f"{DUNGEON_ACTIVITY_PREFIX}{run.id.hex}",
                status="active",
                state_version=run.state_version,
                ruleset_version=CRYPT_RULESET_VERSION,
                last_valid_action_at=datetime.now(UTC),
            )
        )
        await session.flush()

    async def _run_view(
        self,
        session,
        character,
        run,
        member,
        *,
        activity=None,
        combat=None,
        record=None,
        encounter=None,
        kind=None,
    ):
        if activity is None:
            activity = await self._active_activity(session, character.id)
        if activity is not None and combat is None:
            encounter = encounter or await session.scalar(
                select(DungeonRunEncounter).where(DungeonRunEncounter.activity_id == activity.id)
            )
            if encounter is not None and activity.status == "active":
                _, record = await CombatRepository(session).combat(activity)
                combat = decode(
                    record.snapshot, record.id, activity.ruleset_version, activity.state_version
                )
        if combat is not None and activity is not None:
            quantities = tuple(
                (row.consumable_id, row.quantity)
                for row in (
                    await session.scalars(
                        select(ConsumableStack)
                        .where(
                            ConsumableStack.character_id == character.id,
                            ConsumableStack.quantity > 0,
                        )
                        .order_by(ConsumableStack.consumable_id)
                    )
                ).all()
            )
            remaining = max(
                0, DIFFICULTIES[run.difficulty].consumable_limit - member.consumable_uses
            )
            options = combat_consumable_options(
                combat, tuple(item for item, _ in quantities), budget_limit=remaining
            )
            return self._view(
                character,
                kind=kind or "combat",
                run=run,
                member=member,
                activity_id=activity.id,
                encounter_id=None,
                combat=combat,
                consumable_options=options,
                consumable_quantities=quantities,
                consumable_budget_limit=remaining,
            )
        if kind is None:
            progress = run.progress or {}
            if run.status == "completed":
                kind = "completed"
            elif run.status in {"failed", "expired"}:
                kind = run.status
            elif progress.get("awaiting_brazier"):
                kind = "brazier"
            elif progress.get("retry_available"):
                kind = "retry"
            else:
                kind = "ready"
        return self._view(character, kind=kind, run=run, member=member)

    def _view(
        self,
        character,
        *,
        kind,
        run=None,
        member=None,
        difficulty_gates=(),
        reason=None,
        activity_id=None,
        encounter_id=None,
        combat=None,
        consumable_options=(),
        consumable_quantities=(),
        consumable_budget_limit=0,
    ):
        ordinal = run.current_encounter_ordinal if run is not None else 0
        environment = CRYPT_ENCOUNTERS[ordinal].environment if ordinal in CRYPT_ENCOUNTERS else ""
        progress = run.progress or {} if run is not None else {}
        return DungeonView(
            kind=kind,
            character_id=character.id,
            character_name=character.name,
            level=character.level,
            location="Cripta do Ocaso"
            if run is not None and run.status == "active"
            else self._location(None),
            hp=D(character.hp),
            max_hp=D(character.max_hp),
            vigor=character.vigor,
            max_vigor=character.max_vigor,
            run_id=run.id if run is not None else None,
            state_version=run.state_version if run is not None else 0,
            difficulty=run.difficulty if run is not None else None,
            difficulty_label=DIFFICULTIES[run.difficulty].label if run is not None else None,
            difficulty_gates=tuple(difficulty_gates),
            ordinal=ordinal,
            environment=environment,
            has_brazier=run.has_brazier if run is not None and ordinal >= 4 else None,
            brazier_activated=run.brazier_activated if run is not None else False,
            consumable_uses=member.consumable_uses if member is not None else 0,
            consumable_limit=DIFFICULTIES[run.difficulty].consumable_limit
            if run is not None
            else 0,
            activity_id=activity_id,
            encounter_id=encounter_id,
            combat=combat,
            context="dungeon",
            stage="dungeon",
            xp=character.xp,
            consumable_options=tuple(consumable_options),
            consumable_quantities=tuple(consumable_quantities),
            consumable_budget_limit=consumable_budget_limit,
            reward_lines=tuple(progress.get("reward_lines", ())),
            first_clear=bool(progress.get("first_clear", False)),
            reason=reason,
        )

    @staticmethod
    def _location(_world):
        return "Charneca da Fuligem"

    @staticmethod
    def _expired(run) -> bool:
        now = datetime.now(UTC)
        return (
            now - run.last_activity_at >= DUNGEON_IDLE_LIMIT
            or now - run.created_at >= DUNGEON_ABSOLUTE_LIMIT
        )

    async def _expire(self, session, character, run, member):
        activity = await self._active_activity(session, character.id)
        if activity is not None:
            activity.status = "failed"
        run.status = "expired"
        run.expired_at = datetime.now(UTC)
        run.state_version += 1
        run.progress = {**(run.progress or {}), "internal_xp": 0, "expired": True}
        member.status = "left"
        await self._refund_vigor(character, run, member)
        await self._return_to_charneca(session, character.id)

    async def _refund_vigor(self, character, run, member):
        if run.vigor_refunded or member.vigor_reserved <= 0:
            return
        character.vigor = min(character.max_vigor, character.vigor + member.vigor_reserved)
        run.vigor_refunded = True
        member.vigor_reserved = 0

    async def _active_run(self, session, character_id, *, run_id=None, lock=False):
        statement = (
            select(DungeonRun)
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == character_id,
                DungeonRunMember.status == "active",
                DungeonRun.status == "active",
            )
            .order_by(DungeonRun.created_at.desc())
            .limit(1)
        )
        if run_id is not None:
            statement = statement.where(DungeonRun.id == run_id)
        if lock:
            statement = statement.with_for_update(of=DungeonRun)
        run = await session.scalar(statement)
        if run is None:
            return None, None
        member_statement = select(DungeonRunMember).where(
            DungeonRunMember.run_id == run.id,
            DungeonRunMember.character_id == character_id,
        )
        if lock:
            member_statement = member_statement.with_for_update()
        member = await session.scalar(member_statement)
        return run, member

    async def _active_activity(self, session, character_id):
        return await session.scalar(
            select(GameActivity)
            .where(GameActivity.character_id == character_id, GameActivity.status == "active")
            .with_for_update()
        )

    async def _locked_character(self, session, actor):
        return await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _has_unlock(self, session, character_id, unlock_id):
        return (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id, Unlock.unlock_id == unlock_id
                )
            )
            is not None
        )

    async def _ensure_unlock(self, session, character_id, unlock_id):
        existing = await session.scalar(
            select(Unlock)
            .where(Unlock.character_id == character_id, Unlock.unlock_id == unlock_id)
            .with_for_update()
        )
        if existing is None:
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))
            await session.flush()
            return True
        return False

    async def _ensure_codex_entry(self, session, character_id, entry_id):
        existing = await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character_id, CodexEntry.entry_id == entry_id
            )
        )
        if existing is None:
            session.add(CodexEntry(character_id=character_id, entry_id=entry_id))
            await session.flush()

    async def _ensure_fragment(self, session, character_id, entry_id, fragment_id):
        existing = await session.scalar(
            select(CodexFragment).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == fragment_id,
            )
        )
        if existing is None:
            session.add(
                CodexFragment(character_id=character_id, entry_id=entry_id, fragment_id=fragment_id)
            )
            await session.flush()

    async def _return_to_charneca(self, session, character_id):
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id).with_for_update()
        )
        if world is not None:
            world.region = REGION
            world.location = CHARNECA

    @staticmethod
    def _view_base(character, kind):
        return DungeonView(
            kind=kind,
            character_id=character.id,
            character_name=character.name,
            level=character.level,
            location=CHARNECA,
            hp=D(character.hp),
            max_hp=D(character.max_hp),
            vigor=character.vigor,
            max_vigor=character.max_vigor,
            xp=character.xp,
        )

    async def consume_for_activity(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        item_id: str,
        target_id: str,
        effect_id: str | None,
    ) -> DungeonView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, _member = await self._active_run(session, character.id)
            if run is None:
                return None
            owns_activity = await session.scalar(
                select(DungeonRunEncounter.run_id).where(
                    DungeonRunEncounter.run_id == run.id,
                    DungeonRunEncounter.activity_id == activity_id,
                )
            )
            if owns_activity is None:
                return None
        return await self.action(
            actor,
            run.id,
            activity_id,
            version,
            "consumable",
            target_id,
            consumable_id=item_id,
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
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, lock=True)
            if run is None:
                return None
            activity = await self._active_activity(session, character.id)
            if activity is None or activity.id != activity_id:
                return await self._run_view(session, character, run, member, activity=activity)
            current = await self._run_view(session, character, run, member, activity=activity)
            if activity.state_version != version:
                return replace(
                    current, consumable_notice="⚠️ Consumível · A tela ficou desatualizada."
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
            options = tuple(
                option for option in current.consumable_options if option.item_id == item_id
            )
            if item is None or not options:
                return replace(
                    current,
                    consumable_screen="items",
                    consumable_notice="⚠️ Consumível · Não está disponível.",
                )
            if screen == "choose_item":
                if item.family == ConsumableFamily.DISPELLER:
                    target_ids = tuple(dict.fromkeys(option.target_id for option in options))
                    if len(target_ids) > 1:
                        return replace(
                            current, consumable_screen="targets", selected_consumable_id=item.id
                        )
                    target_id = target_ids[0] if target_ids else None
                    parent = "items"
                else:
                    target_id = "player"
                    parent = "items"
                selected = tuple(option for option in options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent=parent
                )
            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(option for option in options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )
            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                target_ids = tuple(dict.fromkeys(option.target_id for option in options))
                return (
                    replace(current, consumable_screen="targets", selected_consumable_id=item.id)
                    if len(target_ids) > 1
                    else replace(current, consumable_screen="items")
                )
            if screen == "effects" and target_id is not None:
                selected = tuple(
                    option
                    for option in options
                    if option.target_id == target_id and option.effect_id is not None
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
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está disponível.",
            )

    @staticmethod
    def _selection_after_target(current, item, target_id, selected, *, parent):
        if not selected:
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Sem alvo válido.",
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

    async def consume(
        self,
        actor: int,
        run_id: UUID,
        activity_id: UUID,
        version: int,
        item_id: str,
        target_id: str,
        effect_id: str | None = None,
    ) -> DungeonView | None:
        return await self.action(
            actor,
            run_id,
            activity_id,
            version,
            "consumable",
            target_id,
            consumable_id=item_id,
            effect_id=effect_id,
        )
