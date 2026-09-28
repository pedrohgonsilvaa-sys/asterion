"""Application services for the post-P1 Road hunt and exploration loop."""
# ruff: noqa: E501

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BESTIARY_STAGE_LABELS, BestiaryRecorder
from asterion.application.equipment import equipment_instance_payload
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.progression import consolidate_character_level, level_xp
from asterion.domain.combat import (
    CombatConsumableOption,
    act,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import (
    ENCOUNTER_CONSUMABLE_LIMITS,
    ConsumableFamily,
)
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    CHARNECA_BRAZIER,
    CHARNECA_LOCATION,
    CHARNECA_ROUTE_UNLOCK,
    EXPLORATION_PROFILES,
    ROAD_EXPLORATION_PROFILE,
    ROAD_LOCATION,
    RULESET,
    create_road_combat,
    creature_for,
    crowns,
    enemy_xp,
    equipment_rarity,
    hunt_profile_for_local_id,
    hunt_profile_for_location,
    material_for,
    materialize_equipment,
    rune_potency,
    select_creature,
    select_exploration_result,
    select_variant,
    weighted_choice,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    BlockedDelivery,
    Brazier,
    Character,
    CodexEntry,
    CodexFragment,
    ConsumableStack,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    MaterialStack,
    PendingItem,
    Quest,
    RewardComponent,
    RewardEvent,
    RuneStack,
    Unlock,
    WorldState,
)

ROAD = "Estrada das Cinzas"
REFUGE = "Refúgio do Ocaso"
CHARNECA = "Charneca da Fuligem"
REGION = "Terras do Ocaso"
P2_QUEST_ID = "P2"
CHARNECA_ROUTE_ENDPOINTS = frozenset((REFUGE, CHARNECA))
BRAZIER_FOR_LOCATION = {
    ROAD: "tdo.brazier.estrada",
    REFUGE: "tdo.brazier.refugio_do_ocaso",
    CHARNECA: CHARNECA_BRAZIER,
}
BRAZIER_DETAILS = {
    "tdo.brazier.estrada": (ROAD, "Braseiro da Estrada"),
    "tdo.brazier.refugio_do_ocaso": (REFUGE, "Braseiro do Refúgio"),
    CHARNECA_BRAZIER: (CHARNECA, "Braseiro do Vento Morto"),
}
HUNT_CONTENT = "road_manual_hunt"
EXPLORE_CONTENT = "road_exploration"
CHARNECA_DUNGEON_UNLOCK = "dungeon.tdo.cripta_ocaso"
CHARNECA_KNOWN_PATH_UNLOCK = "known_path.tdo.cripta_ocaso"
CHARNECA_MARKS_CODEX_ENTRY = "codex.mystery.marcas_na_fuligem"

VARIANT_LABELS = {
    "furious": "Furioso",
    "agile": "Ágil",
    "resistant": "Resistente",
    "hemorrhagic": "Hemorrágico",
    "venomous": "Venenoso",
}
ROAD_ACTIVITY_GRACE = timedelta(minutes=30)
RASTROS_CONTEXT_TEXT = {
    "dog_cinereo": "Pegadas de quatro patas cortam a fuligem em passadas rápidas. Marcas de garras indicam que a criatura percorre a Estrada com frequência.",
    "corvo_fuligem": "Pequenas marcas interrompem a cinza junto a riscos estreitos no chão. Algo pousa e parte repetidamente deste trecho da Estrada.",
    "peregrino_calcinado": "Passadas irregulares seguem por alguns metros antes de desaparecer entre pedra e fuligem. O mesmo padrão já foi associado aos Peregrinos da região.",
}
MATERIAL_LABELS = {
    "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
    "material.tdo.couro_escoriado": "Couro Escoriado",
    "material.tdo.erva_cinzenta": "Erva Cinzenta",
    "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
}

@dataclass(frozen=True)
class RoadView:
    kind: str
    character_id: UUID
    location: str
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    combat: object | None = None
    attempt_id: UUID | None = None
    result_id: str | None = None
    result_text: str | None = None
    state_version: int = 0
    vigor: int = 0
    max_vigor: int = 100
    name: str = ""
    hp: Decimal = Decimal(0)
    max_hp: Decimal = Decimal(0)
    reward_lines: tuple[str, ...] = ()
    familiar: bool = False
    retry_available: bool = True
    explore_available: bool = True
    creature: str | None = None
    variant: str | None = None
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    ready_consumable_option: CombatConsumableOption | None = None
    route_available: bool = False
    brazier_id: str | None = None
    brazier_label: str | None = None
    brazier_destinations: tuple[tuple[str, str, str], ...] = ()
    recovery_brazier: str | None = None
    recovery_location: str | None = None


def _exploration_local_id(profile) -> str:
    # Keep historical Road ExplorationAttempt.local_id rows query-compatible.
    return ROAD if profile.local_id == ROAD_LOCATION else profile.local_id


def _location_label(local_id: str | None) -> str:
    profile = hunt_profile_for_local_id(local_id)
    return profile.label


def _grade_fragment_for_level(level: int) -> str:
    if 1 <= level <= 10:
        return "material.tdo.fragmento_aprimoramento_i"
    raise ValueError(f"no global fragment grade configured for level {level}")


class RoadService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id
        self.bestiary = BestiaryRecorder()

    async def resume(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                return None
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            if world is None or world.location not in {ROAD, REFUGE, CHARNECA}:
                return None
            if world.location == CHARNECA:
                if not await self._p2_completed(s, c.id):
                    return None
            elif not await self._p1_completed(s, c.id):
                return None
            return await self._view_for_world(s, c, world)

    async def travel(self, actor: int, destination: str) -> RoadView | None:
        """Compatibility entry point; route and brazier travel stay distinct."""
        if destination not in BRAZIER_FOR_LOCATION:
            return None
        async with self.sessions() as s:
            c = await self._character(s, actor)
            world = (
                await s.scalar(
                    select(WorldState).where(WorldState.character_id == c.id)
                )
                if c is not None
                else None
            )
            current = world.location if world is not None else None
        if current is None:
            return None
        if {current, destination} == CHARNECA_ROUTE_ENDPOINTS:
            return await self.travel_route(actor, destination)
        return await self.travel_brazier(actor, BRAZIER_FOR_LOCATION[destination])

    async def travel_route(self, actor: int, destination: str) -> RoadView | None:
        """Use the free, post-P2 Refuge/Charneca overland connection."""
        if destination not in CHARNECA_ROUTE_ENDPOINTS:
            return None
        return await self._travel(actor, destination, mode="route")

    async def travel_brazier(self, actor: int, brazier_id: str) -> RoadView | None:
        """Travel only between permanent Braziers already discovered by the character."""
        detail = BRAZIER_DETAILS.get(brazier_id)
        if detail is None:
            return None
        return await self._travel(actor, detail[0], mode="brazier", brazier_id=brazier_id)

    async def _travel(
        self,
        actor: int,
        destination: str,
        *,
        mode: str,
        brazier_id: str | None = None,
    ) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if (
                c is None
                or world is None
                or destination not in BRAZIER_FOR_LOCATION
                or world.location not in {ROAD, REFUGE, CHARNECA}
                or destination == world.location
            ):
                return None
            active_p2 = await s.scalar(
                select(Quest).where(
                    Quest.character_id == c.id,
                    Quest.quest_id == P2_QUEST_ID,
                    Quest.status == "active",
                )
            )
            if active_p2 is not None:
                return None
            if mode == "route":
                if {world.location, destination} != CHARNECA_ROUTE_ENDPOINTS:
                    return None
                if not await self._p2_completed(s, c.id):
                    return None
                if not await s.scalar(
                    select(Unlock).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CHARNECA_ROUTE_UNLOCK,
                    )
                ):
                    return None
                if await s.scalar(
                    select(Quest).where(
                        Quest.character_id == c.id,
                        Quest.quest_id == P2_QUEST_ID,
                        Quest.status == "active",
                    )
                ):
                    return None
            elif mode == "brazier":
                if brazier_id not in BRAZIER_DETAILS:
                    return None
                source_brazier = BRAZIER_FOR_LOCATION.get(world.location)
                if source_brazier is None or source_brazier == brazier_id:
                    return None
                if world.location == CHARNECA or destination == CHARNECA:
                    if (
                        not await self._p2_completed(s, c.id)
                        or not await s.scalar(
                            select(Unlock).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == CHARNECA_ROUTE_UNLOCK,
                            )
                        )
                    ):
                        return None
                elif not await self._p1_completed(s, c.id):
                    return None
                source_known = await s.scalar(
                    select(Brazier).where(
                        Brazier.character_id == c.id,
                        Brazier.brazier_id == source_brazier,
                    )
                )
                target_known = await s.scalar(
                    select(Brazier).where(
                        Brazier.character_id == c.id,
                        Brazier.brazier_id == brazier_id,
                    )
                )
                if source_known is None or target_known is None:
                    return None
            else:
                return None
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                if active.content_id not in {HUNT_CONTENT, EXPLORE_CONTENT}:
                    return None
                if self._expired(active):
                    return await self._expire_activity(s, c, active)
                return await self._road_blocking_view(s, c)
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            world.location = destination
            return await self._view_for_world(s, c, world)

    async def start_hunt(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            profile = await self._available_local_profile(s, c, world, "hunt")
            if profile is None:
                return None
            await self._retry_blocked_deliveries(s, c)
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            active = await s.scalar(
                select(GameActivity)
                .where(GameActivity.character_id == c.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active is not None:
                if active.content_id in {HUNT_CONTENT, EXPLORE_CONTENT}:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    return await self._combat_view(s, c, active)
                return await self._view_for_world(s, c, world)
            seed = uuid4().hex
            creature = select_creature(seed, c.level, profile=profile)
            level = min(c.level, creature.max_level)
            variant = select_variant(seed, creature, profile=profile)
            combat_id = uuid4()
            equipment_configuration = await load_equipment_configuration(s, c)
            reconcile_character_hp(c, equipment_configuration)
            combat = create_road_combat(
                combat_id, c.name, c.character_class, c.race, c.hp, creature, level, variant,
                player_level=c.level,
                equipment_configuration=equipment_configuration,
                location_label=profile.label,
            )
            activity, encounter, record = await CombatRepository(s).create(c, HUNT_CONTENT, combat)
            s.add(
                HuntContext(
                    game_activity_id=activity.id,
                    character_id=c.id,
                    local_id=profile.local_id,
                    creature_id=creature.creature_id,
                    category=creature.category,
                    enemy_level=level,
                    variant=variant,
                    seed=seed,
                    loot_profile="hunt",
                )
            )
            await self._bestiary(
                s,
                c.id,
                creature.creature_id,
                variant=variant,
                elite=creature.category == "elite",
                grant_observation_xp=True,
                observation_level=level,
                observation_category=creature.category,
            )
            await self._record_charneca_habitat(
                s, c.id, creature.creature_id, profile
            )
            await s.flush()
            return await self._combat_view(s, c, activity)

    async def prepare_hunt(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            profile = await self._available_local_profile(s, c, world, "hunt")
            if profile is None:
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            return RoadView("hunt_prepare", c.id, profile.label, vigor=c.vigor, max_vigor=c.max_vigor,
                            name=c.name, hp=c.hp, max_hp=c.max_hp)

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
    ) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None:
                return None
            if not await self._p1_completed(s, c.id):
                return None
            activity = await s.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == c.id,
                    GameActivity.content_id.in_((HUNT_CONTENT, EXPLORE_CONTENT)),
                )
                .with_for_update()
            )
            if activity is None:
                return None
            if activity.status != "active":
                return await self._result_view_for_activity(s, c, activity, world)
            if self._expired(activity):
                return await self._expire_activity(s, c, activity)
            if activity.state_version != version:
                current = await self._combat_view(s, c, activity)
                if consumable_id is not None:
                    return replace(
                        current,
                        consumable_notice=self._consumable_rejection_notice(
                            current.combat, current.consumable_budget_limit
                        ),
                    )
                return current
            encounter, record = await CombatRepository(s).combat(activity)
            combat = decode(
                record.snapshot, record.id, activity.ruleset_version, activity.state_version
            )
            if consumable_id is None:
                if action is None:
                    return await self._combat_view(s, c, activity)
                updated = act(combat, action)
            else:
                context = await s.scalar(
                    select(HuntContext).where(HuntContext.game_activity_id == activity.id)
                )
                budget_limit = (
                    ENCOUNTER_CONSUMABLE_LIMITS.get(context.category, 0)
                    if context is not None
                    else 0
                )
                stack = await s.scalar(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == c.id,
                        ConsumableStack.consumable_id == consumable_id,
                        ConsumableStack.quantity > 0,
                    )
                    .with_for_update()
                )
                if stack is None:
                    return replace(
                        await self._combat_view(s, c, activity),
                        consumable_notice="⚠️ Consumível · Não está mais disponível.",
                    )
                before = combat.version
                updated = use_combat_consumable(
                    combat,
                    consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=budget_limit,
                )
                if updated.version == before:
                    current = await self._combat_view(s, c, activity)
                    notice = self._consumable_rejection_notice(current.combat, budget_limit)
                    return replace(
                        current,
                        consumable_notice=notice
                        or "⚠️ Consumível · Não está mais disponível.",
                    )
                stack.quantity -= 1
            if updated.version == combat.version:
                return await self._combat_view(s, c, activity)
            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            c.hp = updated.fighters["player"].hp
            context = await s.scalar(select(HuntContext).where(HuntContext.game_activity_id == activity.id))
            bestiary_evidence_ids = set()
            if context is not None:
                bestiary_evidence_ids = await self._record_bestiary_combat_events(
                    s, c.id, context, updated
                )
            if updated.result == "victory":
                activity.status = "completed"
                if activity.content_id == HUNT_CONTENT:
                    await self._settle_hunt(
                        s, c, activity, encounter.id, bestiary_evidence_ids
                    )
                    return await self._hunt_victory_view(s, c, activity)
                else:
                    attempt = await s.scalar(
                        select(ExplorationAttempt)
                        .where(ExplorationAttempt.activity_id == activity.id)
                        .with_for_update()
                    )
                    if attempt is not None:
                        attempt.status = "completed"
                        attempt.state_version += 1
                        await self._settle_exploration(s, c, attempt)
                    return (
                        await self._attempt_view(s, c, attempt)
                        if attempt is not None
                        else await self._combat_view(s, c, activity)
                    )
            elif updated.result == "defeat":
                activity.status = "failed"
                recovery_brazier, recovery_location = await self._recover_normal_pve_defeat(
                    s,
                    c,
                    context.local_id if context is not None else None,
                    world,
                )
                if activity.content_id == EXPLORE_CONTENT:
                    attempt = await s.scalar(
                        select(ExplorationAttempt)
                        .where(ExplorationAttempt.activity_id == activity.id)
                        .with_for_update()
                    )
                    if attempt is not None:
                        attempt.status = "failed"
                        attempt.completed_at = datetime.now(UTC)
                        attempt.progress = {
                            **(attempt.progress or {}),
                            "receipt_text": "A exploração foi interrompida.",
                            **(
                                {
                                    "recovery_brazier": recovery_brazier,
                                    "recovery_location": recovery_location,
                                }
                                if recovery_brazier is not None
                                else {}
                            ),
                            "settled": True,
                        }
                        await consolidate_character_level(s, c)
                        return await self._attempt_view(s, c, attempt)
                await consolidate_character_level(s, c)
                return RoadView(
                    "hunt_defeat",
                    c.id,
                    _location_label(context.local_id if context else None),
                    activity_id=activity.id,
                    vigor=c.vigor,
                    max_vigor=c.max_vigor,
                    recovery_brazier=recovery_brazier,
                    recovery_location=recovery_location,
                    route_available=(
                        context is not None
                        and context.local_id == CHARNECA_LOCATION
                        and recovery_location == REFUGE
                    ),
                )
            return await self._combat_view(s, c, activity)

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
    ) -> RoadView | None:
        """Rebuild a read-only Consumable choice screen from current combat state."""
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or not await self._p1_completed(s, c.id):
                return None
            activity = await s.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == c.id,
                    GameActivity.content_id.in_((HUNT_CONTENT, EXPLORE_CONTENT)),
                )
                .with_for_update()
            )
            if activity is None:
                return None
            if activity.status != "active":
                return await self._result_view_for_activity(s, c, activity, world)
            if self._expired(activity):
                return await self._expire_activity(s, c, activity)

            current = await self._combat_view(s, c, activity)
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
                option
                for option in current.consumable_options
                if option.item_id == item_id
            )
            if item is None or not item_options:
                if current.consumable_options:
                    return replace(
                        current,
                        consumable_screen="items",
                        consumable_notice="⚠️ Consumível · Não está mais disponível.",
                    )
                return current

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
                    target_id = "player"
                    parent = "items"
                selected = tuple(
                    option for option in item_options if option.target_id == target_id
                )
                return self._selection_after_target(
                    current, item, target_id, selected, parent=parent
                )

            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(
                    option for option in item_options if option.target_id == target_id
                )
                if not selected:
                    return replace(
                        current,
                        consumable_screen="items" if current.consumable_options else None,
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
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
            )

    @staticmethod
    def _selection_after_target(current, item, target_id, selected, *, parent):
        if not selected:
            return replace(
                current,
                consumable_screen="items" if current.consumable_options else None,
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
        player = combat.fighters["player"]
        if player.cooldowns.get("consumable", 0) > player.opportunity:
            return "⏳ Consumíveis · Em Recarga"
        if budget_limit and combat.consumable_uses >= budget_limit:
            return "🔒 Consumíveis · Limite Atingido"
        return None

    async def retry_hunt(self, actor: int) -> RoadView | None:
        return await self.prepare_hunt(actor)

    async def retry_blocked_deliveries(self, actor: int) -> bool:
        """Retry durable delivery holds without rerolling or duplicating loot."""
        async with self.sessions.begin() as s:
            c = await s.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if c is None:
                return False
            await self._retry_blocked_deliveries(s, c)
            return not c.delivery_blocked

    async def acknowledge_defeat(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            context = await s.scalar(
                select(HuntContext)
                .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
                .where(HuntContext.character_id == c.id, GameActivity.status == "failed")
                .order_by(GameActivity.id.desc()).limit(1).with_for_update()
            )
            if context is not None:
                context.result_acknowledged = True
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._view_for_world(s, c, world) if world else None

    async def acknowledge_result(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            attempt = await s.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.status.in_(("completed", "failed")),
                    ExplorationAttempt.result_acknowledged.is_(False),
                )
                .order_by(ExplorationAttempt.completed_at.desc(), ExplorationAttempt.id.desc())
                .limit(1)
                .with_for_update()
            )
            if attempt is not None:
                attempt.result_acknowledged = True
                world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
                return await self._view_for_world(s, c, world) if world else None
            context = await s.scalar(
                select(HuntContext)
                .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
                .where(HuntContext.character_id == c.id, GameActivity.content_id == HUNT_CONTENT)
                .order_by(GameActivity.id.desc()).limit(1).with_for_update()
            )
            if context is not None:
                context.result_acknowledged = True
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._view_for_world(s, c, world) if world else None

    async def explore(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            hunt_profile = await self._available_local_profile(s, c, world, "explore")
            if hunt_profile is None:
                return None
            explore_profile = EXPLORATION_PROFILES[hunt_profile.local_id]
            attempt_local_id = _exploration_local_id(hunt_profile)
            await self._retry_blocked_deliveries(s, c)
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                if active.content_id == HUNT_CONTENT:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    return await self._combat_view(s, c, active)
                if active.content_id != EXPLORE_CONTENT:
                    return None
                if self._expired(active):
                    return await self._expire_activity(s, c, active)
                attempt = await s.scalar(
                    select(ExplorationAttempt).where(ExplorationAttempt.activity_id == active.id)
                )
                return await self._combat_view(s, c, active) if attempt and attempt.status == "active" else await self._attempt_view(s, c, attempt)
            now = datetime.now(UTC)
            recent = await s.scalar(
                select(func.count(ExplorationAttempt.id)).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                )
            ) or 0
            last = await s.scalar(
                select(ExplorationAttempt)
                .where(ExplorationAttempt.character_id == c.id, ExplorationAttempt.local_id == attempt_local_id)
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            if recent >= 6:
                sixth = await s.scalar(select(ExplorationAttempt).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                ).order_by(ExplorationAttempt.created_at.desc()).offset(5).limit(1))
                return self._explore_limit_view(c, recent, last, now, sixth, hunt_profile.label)
            if last and last.created_at and last.created_at > now - timedelta(minutes=5):
                return self._explore_limit_view(c, recent, last, now, location=hunt_profile.label)
            seed = uuid4().hex
            recent_rows = (await s.scalars(
                select(ExplorationAttempt.result_id)
                .where(ExplorationAttempt.character_id == c.id, ExplorationAttempt.local_id == attempt_local_id)
                .order_by(ExplorationAttempt.created_at.desc()).limit(3)
            )).all()
            unique_result_ids = tuple(
                item.result_id for item in explore_profile.results if item.unique
            )
            resolved_unique = tuple(
                (await s.scalars(select(ExplorationAttempt.result_id).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                    ExplorationAttempt.status == "completed",
                    ExplorationAttempt.result_id.in_(unique_result_ids),
                ))).all()
            )
            result = _explore_result(
                seed, c.level, tuple(str(item).rsplit(".", 1)[-1] for item in recent_rows),
                tuple(str(item) for item in resolved_unique),
                explore_profile,
            )
            category, result_id, result_text = result
            attempt = ExplorationAttempt(
                character_id=c.id,
                local_id=attempt_local_id,
                ruleset_version=RULESET,
                seed=seed,
                category=category,
                result_id=result_id,
                status="active" if category == "combat" else "completed",
                state_version=0 if category == "combat" else 1,
                progress={"result_text": result_text},
            )
            s.add(attempt)
            await s.flush()
            if category == "combat":
                result_key = result_id.rsplit(".", 1)[-1]
                creature_id = explore_profile.result(result_key).creature_id
                if creature_id is None:
                    raise RuntimeError(f"combat exploration result {result_id!r} has no creature")
                creature = creature_for(creature_id)
                level = min(c.level, creature.max_level)
                variant = select_variant(seed, creature, profile=hunt_profile)
                equipment_configuration = await load_equipment_configuration(s, c)
                reconcile_character_hp(c, equipment_configuration)
                combat = create_road_combat(
                    uuid4(), c.name, c.character_class, c.race, c.hp, creature, level, variant,
                    player_level=c.level,
                    equipment_configuration=equipment_configuration,
                    location_label=hunt_profile.label,
                )
                activity, encounter, _ = await CombatRepository(s).create(
                    c, EXPLORE_CONTENT, combat
                )
                attempt.activity_id = activity.id
                attempt.encounter_id = encounter.id
                s.add(
                    HuntContext(
                        game_activity_id=activity.id,
                        character_id=c.id,
                        local_id=hunt_profile.local_id,
                        creature_id=creature.creature_id,
                        category=creature.category,
                        enemy_level=level,
                        variant=variant,
                        seed=seed,
                        loot_profile="exploration_combat",
                    )
                )
                await self._bestiary(
                    s, c.id, creature.creature_id, variant=variant,
                    elite=creature.category == "elite",
                    grant_observation_xp=True,
                    observation_level=level,
                    observation_category=creature.category,
                )
                await self._record_charneca_habitat(s, c.id, creature_id, hunt_profile)
                await s.flush()
                return await self._combat_view(s, c, activity)
            await self._settle_exploration(s, c, attempt)
            return await self._attempt_view(s, c, attempt)

    async def prepare_explore(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            hunt_profile = await self._available_local_profile(s, c, world, "explore")
            if hunt_profile is None:
                return None
            attempt_local_id = _exploration_local_id(hunt_profile)
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            active = await s.scalar(select(GameActivity).where(
                GameActivity.character_id == c.id, GameActivity.status == "active"
            ))
            if active is not None:
                if active.content_id in {HUNT_CONTENT, EXPLORE_CONTENT}:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    if active.content_id == HUNT_CONTENT:
                        return await self._combat_view(s, c, active)
                    attempt = await s.scalar(
                        select(ExplorationAttempt).where(ExplorationAttempt.activity_id == active.id)
                    )
                    return await self._combat_view(s, c, active) if attempt and attempt.status == "active" else await self._attempt_view(s, c, attempt)
                return None
            now = datetime.now(UTC)
            recent = await s.scalar(select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == attempt_local_id,
                ExplorationAttempt.created_at >= now - timedelta(minutes=60),
            )) or 0
            last = await s.scalar(select(ExplorationAttempt).where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == attempt_local_id,
            ).order_by(ExplorationAttempt.created_at.desc()).limit(1))
            if recent >= 6:
                sixth = await s.scalar(select(ExplorationAttempt).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                ).order_by(ExplorationAttempt.created_at.desc()).offset(5).limit(1))
                return self._explore_limit_view(c, recent, last, now, sixth, hunt_profile.label)
            if last and last.created_at and last.created_at > now - timedelta(minutes=5):
                return self._explore_limit_view(c, recent, last, now, location=hunt_profile.label)
            return RoadView("explore_prepare", c.id, hunt_profile.label, vigor=c.vigor, max_vigor=c.max_vigor, name=c.name, hp=c.hp, max_hp=c.max_hp)

    async def _settle_hunt(
        self,
        s,
        c,
        activity,
        encounter_id,
        bestiary_evidence_ids=frozenset(),
        *,
        equipment_configuration: EquipmentConfigurationSnapshot | None = None,
    ):
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id).with_for_update()
        )
        if context is None:
            return 0
        if context.category not in {"common", "uncommon", "elite"}:
            raise ValueError(
                f"Hunt settlement is not configured for {context.category!r}"
            )
        event = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id, RewardEvent.source_id == f"activity:{activity.id}"
            )
            .with_for_update()
        )
        if event is not None:
            return 0
        event = RewardEvent(character_id=c.id, source_id=f"activity:{activity.id}")
        s.add(event)
        await s.flush()
        enough = c.vigor >= 2
        factor = Decimal(1) if enough else Decimal("0.25")
        xp = enemy_xp(context.enemy_level, context.category, factor, player_level=c.level)
        c.xp += xp
        crowns_award = crowns(context.enemy_level, context.category) if enough else 0
        c.crowns += crowns_award
        components = [("xp", None, xp, {})]
        if crowns_award:
            components.append(("crowns", None, crowns_award, {}))
        if enough:
            c.vigor -= 2
            material_count = (
                0
                if context.category == "common"
                and _draw_int(context.seed, "material-roll", 100) >= 80
                else 1
                if context.category == "common"
                else 1 + _draw_int(context.seed, "uncommon-materials", 2)
                if context.category == "uncommon"
                else 3 + _draw_int(context.seed, "elite-materials", 2)
            )
            for ordinal in range(material_count):
                # Keep the historical Common/Road ordinal-zero seed stable.
                # Uncommon has multiple independent units and therefore gets
                # an explicit ordinal in each sub-roll.
                material_seed = (
                    context.seed
                    if context.category == "common" and ordinal == 0
                    else f"{context.seed}:material:{ordinal}"
                )
                material = material_for(context.creature_id, material_seed)
                components.append(("material", material, 1, {"material_id": material, "bound": False}))
                await self._deliver_material(
                    s, c, material, 1, f"activity:{activity.id}:material:{ordinal}"
                )
            if context.category == "elite":
                components.append(("catalyst", "material.tdo.catalisador_elite_i", 1, {}))
                if _draw_int(context.seed, "fragment", 100) < 40:
                    components.append(("fragment", _grade_fragment_for_level(context.enemy_level), 1, {}))
            elif context.category == "uncommon" and _draw_int(context.seed, "fragment", 100) < 5:
                components.append(("fragment", _grade_fragment_for_level(context.enemy_level), 1, {}))
            await self._materialize_optional_loot(s, c, context, components)
            for kind, item_id, quantity, *_ in components:
                if kind in {"catalyst", "fragment"}:
                    await self._deliver_material(
                        s, c, item_id, quantity, f"activity:{activity.id}:{kind}"
                    )
        bestiary_update = await self._bestiary(s, c.id, context.creature_id, victory=True)
        if bestiary_update is None and bestiary_evidence_ids:
            entry = await s.scalar(
                select(BestiaryEntry).where(
                    BestiaryEntry.character_id == c.id,
                    BestiaryEntry.creature_id == context.creature_id,
                )
            )
            if entry is not None:
                bestiary_update = {
                    "creature_id": context.creature_id,
                    "creature_name": creature_for(context.creature_id).name,
                    "stage": entry.stage,
                    "stage_label": BESTIARY_STAGE_LABELS[entry.stage],
                }
        if bestiary_update is not None:
            components.append(("bestiary", context.creature_id, 1, bestiary_update))
        for component in components:
            kind, item_id, quantity = component[:3]
            payload = component[3] if len(component) > 3 else {}
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        profile = hunt_profile_for_local_id(context.local_id)
        await self._ensure(
            s,
            Unlock,
            character_id=c.id,
            unlock_id=profile.round_familiarity,
        )
        await consolidate_character_level(s, c, equipment_configuration)
        return xp

    async def _materialize_optional_loot(self, s, c, context, components):
        equipment_chance = {"common": 8, "uncommon": 14, "elite": 35}[context.category]
        rune_chance = {"common": 5, "uncommon": 15, "elite": 50}[context.category]
        if _draw_int(context.seed, "equipment", 100) < equipment_chance:
            rarity = equipment_rarity(
                context.seed, context.category,
                c.elite_equipment_pity if context.category == "elite" else 0,
                c.elite_legendary_pity if context.category == "elite" else 0,
            )
            if context.category == "elite":
                c.elite_equipment_pity += 1
                if rarity in {"Épico", "Lendário", "Mítico"}:
                    c.elite_equipment_pity = 0
                c.elite_legendary_pity += 1
                if rarity in {"Lendário", "Mítico"}:
                    c.elite_legendary_pity = 0
            item = materialize_equipment(context.seed, rarity, context.enemy_level)
            item_instance_id, item = equipment_instance_payload(item)
            if await self._inventory_slots(s, c.id) < 60:
                s.add(
                    EquipmentItem(
                        id=item_instance_id,
                        character_id=c.id,
                        source_key=f"activity:{context.game_activity_id}:equipment",
                        item_name=item["item_name"],
                        rarity=item["rarity"],
                        slot=item["slot"],
                        item_level=context.enemy_level,
                        bound=False,
                        payload=item,
                    )
                )
            else:
                await self._pending(
                    s, c.id, f"activity:{context.game_activity_id}:equipment", "equipment", item
                )
            components.append(("equipment", item["item_name"], 1, dict(item)))
        if _draw_int(context.seed, "rune", 1000) < rune_chance:
            rarity = _rarity(context.seed, context.category, "rune")
            families = (
                "Brasa",
                "Pedra",
                "Caminhante",
                "Fresta",
                "Presságio",
                "Persistência",
                "Desvio",
                "Guarda",
            )
            family = families[_draw_int(context.seed, "rune.family", len(families))]
            stack = await s.scalar(
                select(RuneStack)
                .where(
                    RuneStack.character_id == c.id,
                    RuneStack.family == family,
                    RuneStack.rarity == rarity,
                    RuneStack.grade == 1,
                    RuneStack.bound.is_(False),
                )
                .with_for_update()
            )
            if stack is None:
                rune_payload = {
                    "family": family,
                    "rarity": rarity,
                    "grade": 1,
                    "potency": rune_potency(family, rarity),
                    "bound": False,
                }
                if await self._inventory_slots(s, c.id) < 60:
                    s.add(
                        RuneStack(
                            character_id=c.id,
                            family=family,
                            rarity=rarity,
                            grade=1,
                            potency=rune_payload["potency"],
                            quantity=1,
                            bound=False,
                        )
                    )
                else:
                    await self._pending(
                        s,
                        c.id,
                        f"activity:{context.game_activity_id}:rune",
                        "rune",
                        rune_payload,
                    )
            else:
                stack.quantity += 1
                rune_payload = {
                    "family": family,
                    "rarity": rarity,
                    "grade": stack.grade,
                    "potency": stack.potency,
                    "bound": stack.bound,
                }
            components.append(("rune", family, 1, rune_payload))

    async def _settle_exploration(self, s, c, attempt):
        if (attempt.progress or {}).get("settled"):
            return
        base_text = (attempt.progress or {}).get("result_text", "")
        if attempt.local_id == CHARNECA_LOCATION:
            await self._settle_charneca_exploration(s, c, attempt, base_text)
            return
        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == attempt.activity_id)
            )
            if context is not None:
                source_id = f"explore:{attempt.id}"
                event = await s.scalar(select(RewardEvent).where(
                    RewardEvent.character_id == c.id,
                    RewardEvent.source_id == source_id,
                ).with_for_update())
                if event is not None:
                    return
                event = RewardEvent(character_id=c.id, source_id=source_id)
                s.add(event)
                await s.flush()
                factor = Decimal(1) if c.vigor >= 4 else Decimal("0.25")
                xp = enemy_xp(
                    context.enemy_level,
                    context.category,
                    factor,
                    player_level=c.level,
                )
                c.xp += xp
                components = [("xp", None, xp, {})]
                receipt_lines = [base_text, f"✨ XP · {xp}"]
                if c.vigor >= 4:
                    c.vigor -= 4
                    # Exploration combat pays the normal repeatable currency
                    # coefficient, independently of the full Hunt reward.
                    crowns_award = int(
                        ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10)
                        .quantize(Decimal(1), rounding=ROUND_HALF_EVEN) * 10
                    )
                    c.crowns += crowns_award
                    components.append(("crowns", None, crowns_award, {}))
                    receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                    pool = (("material.tdo.ferro_de_fuligem", 30), ("material.tdo.couro_escoriado", 30), ("material.tdo.erva_cinzenta", 20), ("material.tdo.residuo_ocaso", 20))
                    units = 1 + (1 if _draw_int(attempt.seed, "exploration-material-extra", 100) < 20 else 0)
                    for ordinal in range(units):
                        material = weighted_choice(
                            f"{attempt.seed}:exploration-material:{ordinal}", pool
                        )
                        components.append(("material", material, 1, {"material_id": material}))
                        receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                        await self._deliver_material(s, c, material, 1, f"explore:{attempt.id}:material:{ordinal}")
                bestiary_update = await self._bestiary(s, c.id, context.creature_id, victory=True)
                if bestiary_update is not None:
                    components.append(("bestiary", context.creature_id, 1, bestiary_update))
                    receipt_lines.append(
                        f"📖 Bestiário · {bestiary_update['creature_name']} · "
                        f"{bestiary_update['stage_label']}"
                    )
                for kind, item_id, quantity, payload in components:
                    s.add(RewardComponent(
                        reward_event_id=event.id,
                        kind=kind,
                        item_id=item_id,
                        quantity=quantity,
                        payload=payload,
                    ))
                attempt.progress = {
                    **(attempt.progress or {}),
                    "receipt_text": "\n\n".join(receipt_lines),
                    "settled": True,
                }
                attempt.completed_at = attempt.completed_at or datetime.now(UTC)
                await consolidate_character_level(s, c)
            return
        if attempt.category == "resource":
            receipt_lines = [base_text]
            if c.vigor >= 4:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10).quantize(
                        Decimal(1), rounding="ROUND_HALF_EVEN"
                    )
                    * 10
                )
                c.crowns += crowns_award
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                material_ids = {
                    "ferro": "material.tdo.ferro_de_fuligem",
                    "couro": "material.tdo.couro_escoriado",
                    "erva": "material.tdo.erva_cinzenta",
                    "residuo": "material.tdo.residuo_ocaso",
                }
                material = material_ids.get(attempt.result_id.rsplit(".", 1)[-1])
                if material:
                    receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                    await self._deliver_material(s, c, material, 1, f"explore:{attempt.id}:resource")
            attempt.progress = {
                **(attempt.progress or {}),
                "receipt_text": "\n\n".join(receipt_lines),
                "settled": True,
            }
            attempt.completed_at = attempt.completed_at or datetime.now(UTC)
            await consolidate_character_level(s, c)
            return
        receipt_lines = [base_text]
        if attempt.result_id == "explore.tdo.estrada.marco_viajantes":
            c.xp += 456
            entry_new = await self._ensure(
                s, CodexEntry, character_id=c.id, entry_id="codex.location.estrada_das_cinzas"
            )
            fragment_new = await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id="codex.location.estrada_das_cinzas",
                fragment_id="codex.fragment.estrada.memoria_viajantes",
            )
            receipt_lines.append("✨ XP · 456")
            if entry_new or fragment_new:
                receipt_lines.append("📖 Códice/Trecho novo")
        elif attempt.result_id == "explore.tdo.estrada.luzes":
            c.xp += 143
            entry_new = await self._ensure(
                s, CodexEntry, character_id=c.id, entry_id="codex.location.estrada_das_cinzas"
            )
            fragment_new = await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id="codex.location.estrada_das_cinzas",
                fragment_id="codex.fragment.estrada.luzes_na_estrada",
            )
            receipt_lines.append("✨ XP · 143")
            if entry_new or fragment_new:
                receipt_lines.append("📖 Códice/Trecho novo")
        elif attempt.result_id == "explore.tdo.estrada.rastros_cinereos":
            identifiable = []
            without_habitat = []
            for creature in ("dog_cinereo", "corvo_fuligem", "peregrino_calcinado"):
                profile = creature_for(creature)
                entry = await s.scalar(select(BestiaryEntry).where(
                    BestiaryEntry.character_id == c.id, BestiaryEntry.creature_id == creature
                ))
                habitat = await s.scalar(select(BestiaryEvidence).where(
                    BestiaryEvidence.character_id == c.id,
                    BestiaryEvidence.creature_id == creature,
                    BestiaryEvidence.evidence_id == "habitat:estrada",
                ))
                if c.level >= profile.unlock_level and entry is not None:
                    identifiable.append(creature)
                    if habitat is None:
                        without_habitat.append(creature)
            eligible = without_habitat or identifiable
            if eligible:
                chosen = eligible[_draw_int(attempt.seed, "habitat", len(eligible))]
                entry = await s.scalar(select(BestiaryEntry).where(
                    BestiaryEntry.character_id == c.id, BestiaryEntry.creature_id == chosen
                ).with_for_update())
                if entry is not None:
                    added_habitat = False
                    if chosen in without_habitat:
                        added_habitat = await self._add_bestiary_evidence(
                            s, entry, c.id, chosen, "habitat:estrada", "habitat", 3
                        )
                    context_text = RASTROS_CONTEXT_TEXT[chosen]
                    attempt.progress = {
                        **(attempt.progress or {}),
                        "context_creature_id": chosen,
                        "context_materialized": True,
                        "result_text": f"{base_text}\n\n{context_text}",
                    }
                    receipt_lines[0] = attempt.progress["result_text"]
                    if added_habitat:
                        receipt_lines.append(
                            f"📖 Bestiário · {creature_for(chosen).name} · Habitat novo"
                        )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(receipt_lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        await consolidate_character_level(s, c)

    async def _settle_charneca_exploration(self, s, c, attempt, base_text: str):
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        receipt_lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Charneca exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            receipt_lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10)
                    .quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += crowns_award
                components.append(("crowns", None, crowns_award, {}))
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                units = 1 + int(
                    _draw_int(attempt.seed, "exploration-material-extra", 100) < 20
                )
                for ordinal in range(units):
                    material = material_for(
                        context.creature_id,
                        f"{attempt.seed}:exploration-material:{ordinal}",
                    )
                    components.append(("material", material, 1, {"material_id": material}))
                    receipt_lines.append(
                        f"📦 {MATERIAL_LABELS.get(material, material)} · 1"
                    )
                    await self._deliver_material(
                        s,
                        c,
                        material,
                        1,
                        f"explore:{attempt.id}:material:{ordinal}",
                    )
            bestiary_update = await self._bestiary(
                s, c.id, context.creature_id, victory=True
            )
            if bestiary_update is not None:
                components.append(
                    ("bestiary", context.creature_id, 1, bestiary_update)
                )
                receipt_lines.append(
                    f"📖 Bestiário · {bestiary_update['creature_name']} · "
                    f"{bestiary_update['stage_label']}"
                )
            should_consolidate = True

        elif attempt.category == "resource":
            if c.vigor >= 4:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10)
                    .quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += crowns_award
                components.append(("crowns", None, crowns_award, {}))
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                material_id = {
                    "explore.tdo.charneca.erva": "material.tdo.erva_cinzenta",
                    "explore.tdo.charneca.residuo": "material.tdo.residuo_ocaso",
                    "explore.tdo.charneca.couro": "material.tdo.couro_escoriado",
                }.get(attempt.result_id)
                if material_id is None:
                    raise RuntimeError(
                        f"unknown Charneca resource result {attempt.result_id!r}"
                    )
                components.append(("material", material_id, 1, {"material_id": material_id}))
                receipt_lines.append(
                    f"📦 {MATERIAL_LABELS.get(material_id, material_id)} · 1"
                )
                await self._deliver_material(
                    s, c, material_id, 1, f"explore:{attempt.id}:resource"
                )

        elif attempt.result_id == "explore.tdo.charneca.braseiro":
            xp = _fixed_percent_xp(4, "0.08")
            c.xp += xp
            await self._ensure(
                s,
                Brazier,
                character_id=c.id,
                brazier_id=CHARNECA_BRAZIER,
            )
            components.extend(
                (
                    ("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.08"}),
                    ("brazier", CHARNECA_BRAZIER, 1, {}),
                )
            )
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.charneca.cripta":
            xp = _fixed_percent_xp(4, "0.08")
            c.xp += xp
            for unlock_id in (CHARNECA_DUNGEON_UNLOCK, CHARNECA_KNOWN_PATH_UNLOCK):
                await self._ensure(
                    s, Unlock, character_id=c.id, unlock_id=unlock_id
                )
                components.append(("unlock", unlock_id, 1, {}))
            components.append(
                ("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.08"})
            )
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.charneca.pedra_marcada":
            xp = _fixed_percent_xp(4, "0.025")
            c.xp += xp
            await self._ensure(
                s,
                CodexEntry,
                character_id=c.id,
                entry_id=CHARNECA_MARKS_CODEX_ENTRY,
            )
            components.append(
                ("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.025"})
            )
            components.append(("codex", CHARNECA_MARKS_CODEX_ENTRY, 1, {}))
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.charneca.vestigios_fuligem":
            creatures = ("aranha_cinza", "cervo_escoriado", "peregrino_calcinado")
            identifiable = []
            without_habitat = []
            habitat_id = f"habitat:{CHARNECA_LOCATION}"
            for creature_id in creatures:
                profile = creature_for(creature_id)
                entry = await s.scalar(
                    select(BestiaryEntry).where(
                        BestiaryEntry.character_id == c.id,
                        BestiaryEntry.creature_id == creature_id,
                    )
                )
                if entry is None or c.level < profile.unlock_level:
                    continue
                identifiable.append(creature_id)
                habitat = await s.scalar(
                    select(BestiaryEvidence).where(
                        BestiaryEvidence.character_id == c.id,
                        BestiaryEvidence.creature_id == creature_id,
                        BestiaryEvidence.evidence_id == habitat_id,
                    )
                )
                if habitat is None:
                    without_habitat.append(creature_id)
            eligible = without_habitat or identifiable
            if eligible:
                creature_id = eligible[_draw_int(attempt.seed, "habitat", len(eligible))]
                entry = await s.scalar(
                    select(BestiaryEntry)
                    .where(
                        BestiaryEntry.character_id == c.id,
                        BestiaryEntry.creature_id == creature_id,
                    )
                    .with_for_update()
                )
                if entry is not None and creature_id in without_habitat:
                    added = await self._add_bestiary_evidence(
                        s,
                        entry,
                        c.id,
                        creature_id,
                        habitat_id,
                        "habitat",
                        3,
                    )
                    if added:
                        components.append(("bestiary_habitat", creature_id, 3, {}))

        elif attempt.category == "narrative" and attempt.result_id == "explore.tdo.charneca.vento_morto":
            xp = _fixed_percent_xp(4, "0.025")
            c.xp += xp
            components.append(
                ("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.025"})
            )
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(receipt_lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)

    async def _bestiary(
        self,
        s,
        character_id,
        creature_id,
        *,
        victory=False,
        evidence_id=None,
        evidence_category=None,
        evidence_points=0,
        variant=None,
        elite=False,
        grant_observation_xp=False,
        observation_level=None,
        observation_category="common",
    ):
        return await self.bestiary.record(
            s,
            character_id,
            creature_id,
            victory=victory,
            evidence_id=evidence_id,
            evidence_category=evidence_category,
            evidence_points=evidence_points,
            variant=variant,
            elite=elite,
            grant_observation_xp=grant_observation_xp,
            observation_level=observation_level,
            observation_category=observation_category,
        )

    async def _record_bestiary_combat_events(self, s, character_id, context, combat):
        return await self.bestiary.record_combat_events(
            s, character_id, context.creature_id, context.variant, combat
        )

    async def _add_bestiary_evidence(
        self, s, entry, character_id, creature_id, evidence_id, category, points=0
    ):
        return await self.bestiary.add_evidence(
            s, entry, character_id, creature_id, evidence_id, category, points
        )

    async def _p1_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P1",
                    Quest.status == "completed",
                )
            )
        )

    async def _p2_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P2_QUEST_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _available_local_profile(self, s, c, world, activity_kind: str):
        profile = hunt_profile_for_location(world.location) if world is not None else None
        if profile is None:
            return None
        if profile.local_id == ROAD_LOCATION:
            if not await self._p1_completed(s, c.id):
                return None
        elif not await self._p2_completed(s, c.id):
            return None
        unlock_id = profile.hunt_unlock if activity_kind == "hunt" else profile.explore_unlock
        if not await s.scalar(
            select(Unlock).where(
                Unlock.character_id == c.id,
                Unlock.unlock_id == unlock_id,
            )
        ):
            return None
        return profile

    async def _recover_normal_pve_defeat(self, s, c, local_id, world=None):
        """Apply only the regional destination rule for normal Charneca PvE defeats."""
        c.hp = c.max_hp
        if local_id != CHARNECA_LOCATION:
            return None, None
        if world is None:
            world = await s.scalar(
                select(WorldState)
                .where(WorldState.character_id == c.id)
                .with_for_update()
            )
        vento = await s.scalar(
            select(Brazier).where(
                Brazier.character_id == c.id,
                Brazier.brazier_id == CHARNECA_BRAZIER,
            )
        )
        recovery_location = CHARNECA if vento is not None else REFUGE
        if world is not None:
            world.region = REGION
            world.location = recovery_location
        return (
            BRAZIER_DETAILS[CHARNECA_BRAZIER if vento is not None else BRAZIER_FOR_LOCATION[REFUGE]][1],
            recovery_location,
        )

    async def _record_charneca_habitat(self, s, character_id, creature_id, profile):
        if profile.local_id != CHARNECA_LOCATION:
            return False
        entry = await s.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            return False
        return await self._add_bestiary_evidence(
            s,
            entry,
            character_id,
            creature_id,
            f"habitat:{CHARNECA_LOCATION}",
            "habitat",
            3,
        )

    async def _road_blocking_view(self, s, c):
        """Return the authoritative Road foreground/result before new callbacks run."""
        active = await s.scalar(
            select(GameActivity)
            .where(GameActivity.character_id == c.id, GameActivity.status == "active")
            .with_for_update()
        )
        if active is not None:
            if active.content_id not in {HUNT_CONTENT, EXPLORE_CONTENT}:
                return None
            if self._expired(active):
                return await self._expire_activity(s, c, active)
            if active.content_id == HUNT_CONTENT:
                return await self._combat_view(s, c, active)
            attempt = await s.scalar(
                select(ExplorationAttempt).where(
                    ExplorationAttempt.activity_id == active.id
                )
            )
            if attempt is None or attempt.status == "active":
                return await self._combat_view(s, c, active)
            return await self._attempt_view(s, c, attempt)

        attempt = await s.scalar(
            select(ExplorationAttempt)
            .where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.status.in_(("completed", "failed")),
                ExplorationAttempt.result_acknowledged.is_(False),
            )
            .order_by(ExplorationAttempt.completed_at.desc(), ExplorationAttempt.id.desc())
            .limit(1)
            .with_for_update()
        )
        if attempt is not None:
            return await self._attempt_view(s, c, attempt)

        context = await s.scalar(
            select(HuntContext)
            .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
            .where(
                HuntContext.character_id == c.id,
                GameActivity.content_id == HUNT_CONTENT,
                GameActivity.status.in_(("completed", "failed")),
                HuntContext.result_acknowledged.is_(False),
            )
            .order_by(GameActivity.id.desc())
            .limit(1)
            .with_for_update()
        )
        if context is None:
            return None
        activity = await s.scalar(
            select(GameActivity).where(GameActivity.id == context.game_activity_id)
        )
        if activity is None:
            return None
        if activity.status == "completed":
            return await self._hunt_victory_view(s, c, activity)
        return await self._hunt_defeat_view(s, c, activity, context)

    async def _hunt_defeat_view(self, s, c, activity, context=None):
        if context is None:
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == activity.id)
            )
        recovery_brazier = recovery_location = None
        if context is not None and context.local_id == CHARNECA_LOCATION:
            world = await s.scalar(
                select(WorldState).where(WorldState.character_id == c.id)
            )
            if world is not None and world.location in {REFUGE, CHARNECA}:
                recovery_location = world.location
                brazier_id = (
                    CHARNECA_BRAZIER
                    if world.location == CHARNECA
                    else BRAZIER_FOR_LOCATION[REFUGE]
                )
                recovery_brazier = BRAZIER_DETAILS[brazier_id][1]
        return RoadView(
            "hunt_defeat",
            c.id,
            _location_label(context.local_id if context is not None else None),
            activity_id=activity.id,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            recovery_brazier=recovery_brazier,
            recovery_location=recovery_location,
            route_available=(
                context is not None
                and context.local_id == CHARNECA_LOCATION
                and recovery_location == REFUGE
            ),
        )

    @staticmethod
    def _expired(activity) -> bool:
        return bool(
            activity.last_valid_action_at
            and datetime.now(UTC) - activity.last_valid_action_at > ROAD_ACTIVITY_GRACE
        )

    async def _expire_activity(self, s, c, activity):
        """Resolve an abandoned Road foreground exactly once."""
        if activity.status != "active":
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._result_view_for_activity(s, c, activity, world)
        activity.status = "failed"
        activity.last_valid_action_at = datetime.now(UTC)
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id)
        )
        recovery_brazier, recovery_location = await self._recover_normal_pve_defeat(
            s,
            c,
            context.local_id if context is not None else None,
        )
        if activity.content_id == EXPLORE_CONTENT:
            attempt = await s.scalar(
                select(ExplorationAttempt)
                .where(ExplorationAttempt.activity_id == activity.id)
                .with_for_update()
            )
            if attempt is not None:
                attempt.status = "failed"
                attempt.completed_at = datetime.now(UTC)
                attempt.progress = {
                    **(attempt.progress or {}),
                    "receipt_text": "A exploração expirou por inatividade.",
                    **(
                        {
                            "recovery_brazier": recovery_brazier,
                            "recovery_location": recovery_location,
                        }
                        if recovery_brazier is not None
                        else {}
                    ),
                    "settled": True,
                }
                await consolidate_character_level(s, c)
                return await self._attempt_view(s, c, attempt)
        await consolidate_character_level(s, c)
        return await self._hunt_defeat_view(s, c, activity, context)

    async def _result_view_for_activity(self, s, c, activity, world):
        if activity.content_id == HUNT_CONTENT:
            if activity.status == "completed":
                context = await s.scalar(
                    select(HuntContext).where(HuntContext.game_activity_id == activity.id)
                )
                if context is not None and not context.result_acknowledged:
                    return await self._hunt_victory_view(s, c, activity)
            else:
                context = await s.scalar(
                    select(HuntContext)
                    .where(HuntContext.game_activity_id == activity.id)
                    .with_for_update()
                )
                if context is not None and not context.result_acknowledged:
                    return await self._hunt_defeat_view(s, c, activity, context)
        elif activity.content_id == EXPLORE_CONTENT:
            attempt = await s.scalar(
                select(ExplorationAttempt).where(ExplorationAttempt.activity_id == activity.id)
            )
            if attempt is not None and not attempt.result_acknowledged:
                return await self._attempt_view(s, c, attempt)
        return await self._view_for_world(s, c, world) if world is not None else None

    async def _combat_view(self, s, c, activity):
        encounter, record = await CombatRepository(s).combat(activity)
        combat = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id)
        )
        budget_limit = (
            ENCOUNTER_CONSUMABLE_LIMITS.get(context.category, 0)
            if context is not None
            else 0
        )
        stock = (
            await s.scalars(
                select(ConsumableStack)
                .where(
                    ConsumableStack.character_id == c.id,
                    ConsumableStack.quantity > 0,
                )
                .order_by(ConsumableStack.consumable_id)
            )
        ).all()
        stock_ids = tuple(row.consumable_id for row in stock)
        consumable_options = combat_consumable_options(
            combat, stock_ids, budget_limit=budget_limit
        )
        return RoadView(
            "combat",
            c.id,
            _location_label(context.local_id if context is not None else None),
            activity.id,
            encounter.id,
            record.id,
            combat,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            consumable_options=consumable_options,
            consumable_quantities=tuple(
                (row.consumable_id, row.quantity) for row in stock
            ),
            consumable_budget_limit=budget_limit,
        )

    async def _view_for_world(self, s, c, world):
        hunt_profile = hunt_profile_for_location(world.location)
        familiar = bool(
            hunt_profile
            and await s.scalar(
                select(Unlock).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == hunt_profile.round_familiarity,
                )
            )
        )
        explore_available = True
        if hunt_profile is not None:
            now = datetime.now(UTC)
            attempt_local_id = _exploration_local_id(hunt_profile)
            recent = await s.scalar(
                select(func.count(ExplorationAttempt.id)).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                )
            ) or 0
            last = await s.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                )
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            explore_available = not (
                recent >= 6
                or (last is not None and last.created_at > now - timedelta(minutes=5))
            )
        known_brazier_ids = set(
            (
                await s.scalars(
                    select(Brazier.brazier_id).where(Brazier.character_id == c.id)
                )
            ).all()
        )
        current_brazier = BRAZIER_FOR_LOCATION.get(world.location)
        brazier_id = (
            current_brazier if current_brazier in known_brazier_ids else None
        )
        brazier_label = (
            BRAZIER_DETAILS[brazier_id][1] if brazier_id is not None else None
        )
        brazier_destinations = tuple(
            (candidate_id, label, location)
            for candidate_id, (location, label) in BRAZIER_DETAILS.items()
            if candidate_id in known_brazier_ids
            and location != world.location
        )
        route_available = bool(
            world.location in CHARNECA_ROUTE_ENDPOINTS
            and await self._p2_completed(s, c.id)
            and await s.scalar(
                select(Unlock).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == CHARNECA_ROUTE_UNLOCK,
                )
            )
        )
        return RoadView(
            "road" if world.location == ROAD else "charneca" if world.location == CHARNECA else "refuge",
            c.id,
            world.location,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            familiar=familiar,
            explore_available=explore_available,
            route_available=route_available,
            brazier_id=brazier_id,
            brazier_label=brazier_label,
            brazier_destinations=brazier_destinations,
        )

    async def _locked_world(self, s, actor):
        c = await s.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if c is None:
            return None, None
        world = await s.scalar(
            select(WorldState).where(WorldState.character_id == c.id).with_for_update()
        )
        return c, world

    async def _character(self, s, actor):
        return await s.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _ensure(self, s, model, **values):
        found = await s.scalar(select(model).filter_by(**values).with_for_update())
        if found is None:
            s.add(model(**values))
            return True
        return False

    async def deliver_material(
        self,
        s,
        c,
        material_id: str,
        quantity: int,
        source_key: str,
        *,
        bound: bool = False,
    ) -> None:
        """Share the existing Inventory/Pending/Blocked material policy."""
        await self._deliver_material(
            s, c, material_id, quantity, source_key, bound=bound
        )

    async def _deliver_material(
        self,
        s,
        c,
        material_id: str,
        quantity: int,
        source_key: str,
        *,
        bound: bool = False,
    ) -> None:
        existing_delivery = await s.scalar(
            select(BlockedDelivery)
            .where(
                BlockedDelivery.character_id == c.id,
                BlockedDelivery.source_key == source_key,
            )
            .with_for_update()
        )
        if existing_delivery is not None:
            if existing_delivery.status == "pending":
                c.delivery_blocked = True
            return
        if await s.scalar(
            select(PendingItem)
            .where(
                PendingItem.character_id == c.id,
                PendingItem.source_key == source_key,
            )
            .with_for_update()
        ) is not None:
            return
        remaining = await self._deliver_material_to_inventory(
            s, c, material_id, quantity, bound
        )
        if remaining:
            await self._pending(
                s,
                c.id,
                source_key,
                "material",
                {"material_id": material_id, "bound": bound},
                remaining,
            )

    async def _deliver_material_to_inventory(self, s, c, material_id, quantity, bound):
        stacks = (
            await s.scalars(
                select(MaterialStack)
                .where(
                    MaterialStack.character_id == c.id,
                    MaterialStack.material_id == material_id,
                    MaterialStack.bound.is_(bound),
                )
                .order_by(MaterialStack.id)
                .with_for_update()
            )
        ).all()
        remaining = quantity
        for stack in stacks:
            if remaining <= 0:
                break
            available = max(0, 999 - stack.quantity)
            added = min(remaining, available)
            stack.quantity += added
            remaining -= added
        while remaining > 0 and await self._inventory_slots(s, c.id) < 60:
            added = min(remaining, 999)
            s.add(
                MaterialStack(
                    character_id=c.id,
                    material_id=material_id,
                    quantity=added,
                    bound=bound,
                )
            )
            remaining -= added
        return remaining

    async def _inventory_slots(self, s, character_id):
        equipment = await s.scalar(select(func.count(EquipmentItem.id)).where(EquipmentItem.character_id == character_id)) or 0
        materials = await s.scalar(select(func.count(MaterialStack.id)).where(MaterialStack.character_id == character_id)) or 0
        runes = await s.scalar(select(func.count(RuneStack.id)).where(RuneStack.character_id == character_id)) or 0
        return int(equipment + materials + runes)

    async def _pending(self, s, character_id, source_key, kind, payload, quantity=1):
        if kind == "equipment":
            _, payload = equipment_instance_payload(payload)
        hold = await s.scalar(
            select(BlockedDelivery)
            .where(
                BlockedDelivery.character_id == character_id,
                BlockedDelivery.source_key == source_key,
            )
            .with_for_update()
        )
        if hold is not None:
            character = await s.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
            if character is not None and hold.status == "pending":
                character.delivery_blocked = True
            return
        existing = await s.scalar(select(PendingItem).where(
            PendingItem.character_id == character_id, PendingItem.source_key == source_key
        ).with_for_update())
        if existing is not None:
            return
        count = await s.scalar(select(func.count(PendingItem.id)).where(PendingItem.character_id == character_id)) or 0
        if count < 20:
            s.add(PendingItem(character_id=character_id, source_key=source_key, kind=kind, payload=payload, quantity=quantity))
        else:
            character = await s.scalar(select(Character).where(Character.id == character_id).with_for_update())
            if character is not None:
                character.delivery_blocked = True
                s.add(
                    BlockedDelivery(
                        character_id=character_id,
                        source_key=source_key,
                        kind=kind,
                        payload=payload,
                        quantity=quantity,
                        status="pending",
                    )
                )

    async def _retry_blocked_deliveries(self, s, c) -> None:
        holds = (
            await s.scalars(
                select(BlockedDelivery)
                .where(
                    BlockedDelivery.character_id == c.id,
                    BlockedDelivery.status == "pending",
                )
                .order_by(BlockedDelivery.created_at, BlockedDelivery.id)
                .with_for_update()
            )
        ).all()
        for hold in holds:
            payload = dict(hold.payload or {})
            if hold.kind == "material":
                remaining = await self._deliver_material_to_inventory(
                    s,
                    c,
                    payload["material_id"],
                    hold.quantity,
                    bool(payload.get("bound", False)),
                )
                if remaining and await self._pending_slots(s, c.id) > 0:
                    s.add(
                        PendingItem(
                            character_id=c.id,
                            source_key=hold.source_key,
                            kind=hold.kind,
                            payload=payload,
                            quantity=remaining,
                        )
                    )
                    remaining = 0
                hold.quantity = remaining or hold.quantity
                if remaining == 0:
                    self._resolve_delivery(hold)
            elif hold.kind == "equipment":
                item_instance_id, payload = equipment_instance_payload(payload)
                if await self._inventory_slots(s, c.id) < 60:
                    s.add(
                        EquipmentItem(
                            id=item_instance_id,
                            character_id=c.id,
                            source_key=hold.source_key,
                            item_name=payload["item_name"],
                            rarity=payload["rarity"],
                            slot=payload["slot"],
                            item_level=payload["item_level"],
                            bound=bool(payload.get("bound", False)),
                            payload=payload,
                        )
                    )
                    self._resolve_delivery(hold)
                elif await self._pending_slots(s, c.id) > 0:
                    s.add(
                        PendingItem(
                            character_id=c.id,
                            source_key=hold.source_key,
                            kind=hold.kind,
                            payload=payload,
                            quantity=hold.quantity,
                        )
                    )
                    self._resolve_delivery(hold)
            elif hold.kind == "rune":
                stack = await s.scalar(
                    select(RuneStack)
                    .where(
                        RuneStack.character_id == c.id,
                        RuneStack.family == payload["family"],
                        RuneStack.rarity == payload["rarity"],
                        RuneStack.grade == payload.get("grade", 1),
                        RuneStack.bound.is_(bool(payload.get("bound", False))),
                    )
                    .with_for_update()
                )
                if stack is not None:
                    stack.quantity += hold.quantity
                    self._resolve_delivery(hold)
                elif await self._inventory_slots(s, c.id) < 60:
                    s.add(
                        RuneStack(
                            character_id=c.id,
                            family=payload["family"],
                            rarity=payload["rarity"],
                            grade=payload.get("grade", 1),
                            potency=payload["potency"],
                            quantity=hold.quantity,
                            bound=bool(payload.get("bound", False)),
                        )
                    )
                    self._resolve_delivery(hold)
                elif await self._pending_slots(s, c.id) > 0:
                    s.add(
                        PendingItem(
                            character_id=c.id,
                            source_key=hold.source_key,
                            kind=hold.kind,
                            payload=payload,
                            quantity=hold.quantity,
                        )
                    )
                    self._resolve_delivery(hold)
        c.delivery_blocked = bool(
            await s.scalar(
                select(func.count(BlockedDelivery.id)).where(
                    BlockedDelivery.character_id == c.id,
                    BlockedDelivery.status == "pending",
                )
            )
        )

    async def _pending_slots(self, s, character_id):
        count = await s.scalar(
            select(func.count(PendingItem.id)).where(PendingItem.character_id == character_id)
        ) or 0
        return 20 - int(count)

    @staticmethod
    def _resolve_delivery(hold):
        hold.status = "resolved"
        hold.resolved_at = datetime.now(UTC)

    async def _hunt_victory_view(self, s, c, activity):
        context = await s.scalar(select(HuntContext).where(HuntContext.game_activity_id == activity.id))
        if context is None:
            return None
        rows = (await s.scalars(select(RewardComponent).join(RewardEvent).where(
            RewardEvent.character_id == c.id,
            RewardEvent.source_id == f"activity:{activity.id}",
        ).order_by(RewardComponent.id))).all()
        labels = {
            "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
            "material.tdo.couro_escoriado": "Couro Escoriado",
            "material.tdo.erva_cinzenta": "Erva Cinzenta",
            "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
            "material.tdo.catalisador_elite_i": "Catalisador de Elite I",
            "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
        }
        reward_lines = []
        for row in rows:
            payload = row.payload or {}
            if row.kind == "xp":
                reward_lines.append(f"✨ XP · {row.quantity}")
            elif row.kind == "crowns":
                reward_lines.append(f"🪙 Coroas · {row.quantity}")
            elif row.kind == "equipment":
                reward_lines.append(
                    "🛡️ "
                    f"{payload.get('item_name', row.item_id or 'Equipamento')} · "
                    f"+{payload.get('enhancement', 0)} · "
                    f"{payload.get('rarity', 'Raridade desconhecida')} · "
                    f"{payload.get('slot', 'Slot desconhecido')} · "
                    f"Nível do Item {payload.get('item_level', '?')} · "
                    f"{'Vinculado' if payload.get('bound', False) else 'Negociável'}"
                )
            elif row.kind == "rune":
                reward_lines.append(
                    "🔮 Runa "
                    f"{payload.get('family', row.item_id or 'desconhecida')} · "
                    f"{payload.get('rarity', 'Raridade desconhecida')} · "
                    f"Grau {payload.get('grade', 1)} · "
                    f"{'Vinculada' if payload.get('bound', False) else 'Negociável'}"
                )
            elif row.kind == "bestiary":
                reward_lines.append(
                    f"📖 Bestiário · {payload.get('creature_name', 'Atualização registrada')} · "
                    f"{payload.get('stage_label', payload.get('stage', 'Atualizado'))}"
                )
            else:
                reward_lines.append(f"📦 {labels.get(row.item_id, row.item_id or row.kind)} · {row.quantity}")
        return RoadView(
            "hunt_victory", c.id, _location_label(context.local_id),
            activity_id=activity.id,
            vigor=c.vigor, max_vigor=c.max_vigor,
            name=c.name, hp=c.hp, max_hp=c.max_hp,
            reward_lines=tuple(reward_lines),
            creature=creature_for(context.creature_id).name,
            variant=VARIANT_LABELS.get(context.variant, context.variant),
        )

    def _explore_limit_view(self, c, recent, last, now, sixth=None, location=ROAD):
        if recent >= 6:
            attempts = [sixth.created_at + timedelta(minutes=60)] if sixth and sixth.created_at else []
            available_at = min(attempts) if attempts else now
            return RoadView("explore_limit", c.id, location, vigor=c.vigor, max_vigor=c.max_vigor,
                            name=c.name, hp=c.hp, max_hp=c.max_hp,
                            result_text=_remaining(available_at, now))
        available_at = last.created_at + timedelta(minutes=5)
        return RoadView("explore_cooldown", c.id, location, vigor=c.vigor, max_vigor=c.max_vigor,
                        name=c.name, hp=c.hp, max_hp=c.max_hp,
                        result_text=_remaining(available_at, now))

    async def _explore_retry_available(self, s, c, attempt) -> bool:
        if attempt is None or attempt.status == "active":
            return False
        now = datetime.now(UTC)
        local_id = attempt.local_id
        recent = await s.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == local_id,
                ExplorationAttempt.created_at >= now - timedelta(minutes=60),
            )
        ) or 0
        if recent >= 6:
            return False
        last = await s.scalar(
            select(ExplorationAttempt)
            .where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == local_id,
            )
            .order_by(ExplorationAttempt.created_at.desc(), ExplorationAttempt.id.desc())
            .limit(1)
        )
        return not (
            last is not None
            and last.created_at
            and last.created_at > now - timedelta(minutes=5)
        )

    async def _attempt_view(self, s, c, attempt, location=None, text=None):
        location = location or _location_label(attempt.local_id if attempt else ROAD)
        persisted = (attempt.progress or {}).get("receipt_text") or (attempt.progress or {}).get("result_text")
        return RoadView(
            "exploration",
            c.id,
            location,
            attempt_id=attempt.id if attempt else None,
            result_id=attempt.result_id if attempt else None,
            result_text=text or persisted,
            state_version=attempt.state_version if attempt else 0,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            retry_available=await self._explore_retry_available(s, c, attempt),
            recovery_brazier=(attempt.progress or {}).get("recovery_brazier"),
            recovery_location=(attempt.progress or {}).get("recovery_location"),
            route_available=(
                attempt.local_id == CHARNECA_LOCATION
                and (attempt.progress or {}).get("recovery_location") == REFUGE
            ),
        )


def _explore_result(
    seed: str,
    player_level: int = 1,
    recent: tuple[str, ...] = (),
    excluded: tuple[str, ...] = (),
    profile=ROAD_EXPLORATION_PROFILE,
) -> tuple[str, str, str]:
    key = select_exploration_result(
        seed, player_level, recent, excluded, profile=profile
    )
    result = profile.result(key)
    return result.category, result.result_id, result.text


def _draw_int(seed: str, purpose: str, modulo: int) -> int:
    return int.from_bytes(sha256(f"{seed}:{purpose}".encode()).digest(), "big") % modulo


def _fixed_percent_xp(reference_level: int, percent: str) -> int:
    return int(
        (Decimal(level_xp(reference_level)) * Decimal(percent)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )


def _repeat_bkp(wins: int, elite: bool) -> int:
    if elite:
        return 3 if wins == 2 else 2 if wins == 3 else 1 if 4 <= wins <= 5 else 0
    if 2 <= wins <= 5:
        return 2
    if 6 <= wins <= 10:
        return 1
    if wins in {15, 25, 40}:
        return 3
    return 0


def _remaining(available_at, now) -> str:
    seconds = max(0, int((available_at - now).total_seconds() + 0.999999))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _rarity(seed: str, category: str, purpose: str) -> str:
    if category not in {"common", "uncommon", "elite"}:
        raise ValueError(f"Hunt loot rarity is not configured for {category!r}")
    roll = _draw_int(seed, purpose + ":rarity", 10000) / 100
    if purpose == "equipment":
        bands = (
            (
                (78, "Comum"),
                (97, "Raro"),
                (99.8, "Épico"),
                (100, "Lendário"),
            )
            if category == "common"
            else ((65, "Comum"), (94, "Raro"), (99.5, "Épico"), (100, "Lendário"))
            if category == "uncommon"
            else (
                (45, "Comum"),
                (87, "Raro"),
                (98, "Épico"),
                (99.9, "Lendário"),
                (100, "Mítico"),
            )
        )
    else:
        bands = (
            ((90, "Rara"), (99.5, "Épica"), (100, "Lendária"))
            if category in {"common", "uncommon"}
            else ((80, "Rara"), (98, "Épica"), (100, "Lendária"))
        )
    for limit, rarity in bands:
        if roll < limit:
            return rarity
    return bands[-1][1]
