"""Authoritative P2 quest flow and scripted encounter settlement."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import REFUGE, REGION, RoadService
from asterion.domain.combat import (
    Combat,
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
from asterion.domain.road import RULESET, SPIDER, create_creature_combat, enemy_xp
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CombatRecord,
    ConsumableStack,
    Encounter,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

P2_ID = "P2"
P2_TITLE = "Fuligem sem Fogo"
P2_VERSION = "tdo-1.0.7"
P2_COMBAT_CONTENT_ID = "p2_step3_scripted_spider"
P2_REWARD_SOURCE = "p2.fuligem_sem_fogo"

CHARNECA = "Charneca da Fuligem"
CHARNECA_LOCATION_ID = "tdo.location.charneca_da_fuligem"
ROUTE_UNLOCK = "route.tdo.refugio_charneca"
HUNT_UNLOCK = "hunt_manual.charneca_da_fuligem"
EXPLORE_UNLOCK = "explore.charneca_da_fuligem"
CODEX_MARKS_ENTRY = "codex.mystery.marcas_na_fuligem"
CODEX_OREN_ENTRY = "codex.figure.oren_cal"

ASH_POINT_IDS = (
    "p2.ash_point.1",
    "p2.ash_point.2",
    "p2.ash_point.3",
)
P2_MATERIAL_REWARDS = (
    ("material.tdo.ferro_de_fuligem", 1),
    ("material.tdo.erva_cinzenta", 2),
    ("material.tdo.residuo_ocaso", 1),
)


@dataclass(frozen=True)
class P2View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p2"
    combat: Combat | None = None
    activity_id: UUID | None = None
    activity_state_version: int | None = None
    activity_status: str | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    result_state: str | None = None
    rewarded: bool = False
    blocked_by_foreground: bool = False
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: CombatConsumableOption | None = None


class P2Service:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        # Share Bestiary rules and the established material-delivery policy.
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def alda(self, actor: int) -> P2View | None:
        """Return Alda's offer or the authoritative state without creating P2."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def resume(self, actor: int) -> P2View | None:
        """Rebuild an already-created P2 state; never pre-create the Quest."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def accept(self, actor: int, version: int = 0) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if quest is not None:
                return await self._view(session, character, quest, world)
            if version != 0 or not await self._eligible(
                session, character, world, quest
            ):
                return await self._view(session, character, quest, world)
            quest = Quest(
                character_id=character.id,
                quest_id=P2_ID,
                title=P2_TITLE,
                status="active",
                step=1,
                content_version=P2_VERSION,
                state_version=0,
                progress={"ash_points": []},
            )
            session.add(quest)
            await session.flush()
            return await self._view(session, character, quest, world)

    async def travel_to_charneca(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=1):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, REFUGE)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            await self._ensure(
                session,
                LocationDiscovery,
                character_id=character.id,
                location_id=CHARNECA_LOCATION_ID,
            )
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=ROUTE_UNLOCK,
            )
            world.region, world.location = REGION, CHARNECA
            quest.step = 2
            quest.state_version += 1
            quest.progress = {**(quest.progress or {}), "ash_points": []}
            return await self._view(session, character, quest, world)

    async def examine_ash_point(
        self, actor: int, point_id: str, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=2):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, CHARNECA)
                or point_id not in ASH_POINT_IDS
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            progress = dict(quest.progress or {})
            points = list(progress.get("ash_points", []))
            if point_id in points:
                return await self._view(session, character, quest, world)
            points.append(point_id)
            progress["ash_points"] = points
            quest.progress = progress
            if len(points) == len(ASH_POINT_IDS):
                quest.step = 3
                await self._materialize_combat(
                    session, character, quest, world
                )
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
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None or quest is None:
                return await self._view(session, character, quest, world)
            if (
                quest.status != "active"
                or quest.content_version != P2_VERSION
                or quest.step != 3
                or activity.status != "active"
                or activity.state_version != version
                or not self._at(world, CHARNECA)
            ):
                return await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if foreground is None or foreground.id != activity.id:
                return await self._view(session, character, quest, world)
            if (action is None) == (consumable_id is None):
                return await self._view(session, character, quest, world)

            _, record = await CombatRepository(session).combat(activity)
            combat = decode(
                record.snapshot,
                record.id,
                activity.ruleset_version,
                activity.state_version,
            )
            stack = None
            if consumable_id is None:
                updated = act(combat, action)
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
                    return await self._view(session, character, quest, world)
                budget_limit = ENCOUNTER_CONSUMABLE_LIMITS.get(
                    SPIDER.category, 0
                )
                updated = use_combat_consumable(
                    combat,
                    consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=budget_limit,
                )
            if updated.version == combat.version:
                return await self._view(session, character, quest, world)
            if stack is not None:
                stack.quantity -= 1

            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            character.hp = updated.fighters["player"].hp
            await self.bestiary.record_combat_events(
                session, character.id, SPIDER.creature_id, None, updated
            )

            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await self.bestiary.record(
                    session,
                    character.id,
                    SPIDER.creature_id,
                    victory=True,
                    observation_category="uncommon",
                )
                configuration = await load_equipment_configuration(
                    session, character
                )
                reconcile_character_hp(character, configuration)
                await consolidate_character_level(
                    session, character, configuration
                )
                reconcile_character_hp(character, configuration)
                progress.update(
                    combat_result="victory",
                    awaiting_retry=False,
                )
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session,
                    character.id,
                    SPIDER.creature_id,
                    observation_category="uncommon",
                )
                configuration = await load_equipment_configuration(
                    session, character
                )
                reconcile_character_hp(character, configuration)
                await consolidate_character_level(
                    session, character, configuration
                )
                reconcile_character_hp(character, configuration)
                character.hp = character.max_hp
                world.region, world.location = REGION, REFUGE
                progress.update(
                    combat_result="defeat",
                    awaiting_retry=True,
                    defeat_activity_id=str(activity.id),
                )

            quest.progress = progress
            quest.state_version += 1
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
    ) -> P2View | None:
        """Rebuild the shared combat Consumable chooser without persisting UI state."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P2_COMBAT_CONTENT_ID,
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
                    target_ids = tuple(
                        dict.fromkeys(option.target_id for option in item_options)
                    )
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
                        consumable_screen=(
                            "items" if current.consumable_options else None
                        ),
                        consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
                    )
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )

            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                target_ids = tuple(
                    dict.fromkeys(option.target_id for option in item_options)
                )
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

    async def return_to_charneca(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            foreground = await self._foreground(session, character.id)
            if foreground is not None:
                return await self._view(session, character, quest, world)
            if (
                not self._valid(quest, version, step=3)
                or not (quest.progress or {}).get("awaiting_retry")
                or not self._at(world, REFUGE)
            ):
                return await self._view(session, character, quest, world)

            route = await session.scalar(
                select(Unlock).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == ROUTE_UNLOCK,
                )
            )
            if route is None:
                return await self._view(session, character, quest, world)
            world.region, world.location = REGION, CHARNECA
            progress = dict(quest.progress or {})
            progress["awaiting_retry"] = False
            quest.progress = progress
            await self._materialize_combat(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def examine_pedra_marcada(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=4):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, CHARNECA)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            progress = dict(quest.progress or {})
            if progress.get("stone_examined"):
                return await self._view(session, character, quest, world)
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=CODEX_MARKS_ENTRY,
            )
            progress["stone_examined"] = True
            progress["stone_evidence"] = (
                "recurrent marks associated with ash and the route; authorship unknown"
            )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def return_to_refuge(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=4):
                return await self._view(session, character, quest, world)
            if (
                not (quest.progress or {}).get("stone_examined")
                or not self._at(world, CHARNECA)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)
            world.region, world.location = REGION, REFUGE
            quest.step = 5
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def oren(self, actor: int, version: int) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=5):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, REFUGE)
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=CODEX_OREN_ENTRY,
            )
            progress = dict(quest.progress or {})
            progress["oren_spoken"] = True
            quest.progress = progress
            quest.step = 6
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def report_to_alda(
        self, actor: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if quest.status == "completed":
                return await self._view(session, character, quest, world)
            if not self._valid(quest, version, step=6):
                return await self._view(session, character, quest, world)
            if (
                not self._at(world, REFUGE)
                or not (quest.progress or {}).get("oren_spoken")
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)

            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P2_REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                event = RewardEvent(
                    character_id=character.id,
                    source_id=P2_REWARD_SOURCE,
                )
                session.add(event)
                await session.flush()
                character.xp += 3300
                character.crowns += 140
                components = [
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        item_id=None,
                        quantity=3300,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        item_id=None,
                        quantity=140,
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
                    for material_id, quantity in P2_MATERIAL_REWARDS
                )
                session.add_all(components)
                for material_id, quantity in P2_MATERIAL_REWARDS:
                    await self.road.deliver_material(
                        session,
                        character,
                        material_id,
                        quantity,
                        f"{P2_REWARD_SOURCE}:material:{material_id}",
                        bound=True,
                    )

            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=HUNT_UNLOCK,
            )
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=EXPLORE_UNLOCK,
            )
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=ROUTE_UNLOCK,
            )
            configuration = await load_equipment_configuration(
                session, character
            )
            reconcile_character_hp(character, configuration)
            await consolidate_character_level(
                session, character, configuration
            )
            reconcile_character_hp(character, configuration)
            quest.status = "completed"
            quest.progress = {
                **(quest.progress or {}),
                "completed": True,
                "awaiting_retry": False,
            }
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _materialize_combat(
        self, session, character, quest, world
    ) -> GameActivity | None:
        if not self._at(world, CHARNECA):
            return None
        foreground = await self._foreground(session, character.id)
        if foreground is not None:
            return (
                foreground
                if foreground.content_id == P2_COMBAT_CONTENT_ID
                else None
            )
        configuration = await load_equipment_configuration(session, character)
        reconcile_character_hp(character, configuration)
        combat = create_creature_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            character.hp,
            SPIDER,
            3,
            None,
            player_level=character.level,
            equipment_configuration=configuration,
            ruleset_version=RULESET,
            flavor="A fuligem se move sobre a pedra; a Aranha de Cinza avança.",
            opening_log="🕷️ Aranha de Cinza · Nv.3 surge entre a fuligem.",
        )
        activity, _, _ = await CombatRepository(session).create(
            character, P2_COMBAT_CONTENT_ID, combat
        )
        progress = dict(quest.progress or {})
        progress.update(
            combat_activity_id=str(activity.id),
            combat_result=None,
            awaiting_retry=False,
        )
        quest.progress = progress
        await self.bestiary.record(
            session,
            character.id,
            SPIDER.creature_id,
            evidence_id=f"habitat:{CHARNECA_LOCATION_ID}",
            evidence_category="habitat",
            evidence_points=3,
            grant_observation_xp=True,
            observation_level=3,
            observation_category="uncommon",
        )
        await session.flush()
        return activity

    async def _grant_enemy_xp(
        self, session, character: Character, activity: GameActivity
    ) -> int:
        source_id = f"{P2_REWARD_SOURCE}:enemy-xp:{activity.id}"
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
        xp = enemy_xp(3, "uncommon", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="enemy_xp",
                item_id=SPIDER.creature_id,
                quantity=xp,
                payload={
                    "enemy_level": 3,
                    "category": "uncommon",
                    "observation_context": "P2",
                },
            )
        )
        character.xp += xp
        return xp

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
                Quest.quest_id == P2_ID,
            )
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
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P2_ID,
            )
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(
                WorldState.character_id == character_id
            )
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity)
            .where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
            .with_for_update()
        )

    async def _eligible(self, session, character, world, quest):
        if (
            quest is not None
            or character.level < 3
            or world is None
            or world.region != REGION
            or world.location != REFUGE
        ):
            return False
        p1_completed = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == "P1",
                Quest.status == "completed",
            )
        )
        if p1_completed is None:
            return False
        return await self._foreground(session, character.id) is None

    async def _view(self, session, character, quest, world):
        if character is None:
            return None
        world = world or await self._world(session, character.id)
        progress = dict(quest.progress or {}) if quest is not None else {}
        active = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        activity = active
        if activity is None and progress.get("combat_activity_id"):
            try:
                stored_activity_id = UUID(progress["combat_activity_id"])
            except (TypeError, ValueError):
                stored_activity_id = None
            if stored_activity_id is not None:
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == stored_activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                    )
                )

        encounter_id = None
        combat_id = None
        combat = None
        if activity is not None:
            pair = await session.execute(
                select(Encounter, CombatRecord)
                .join(CombatRecord)
                .where(Encounter.game_activity_id == activity.id)
            )
            row = pair.first()
            if row is not None:
                encounter, record = row
                encounter_id, combat_id = encounter.id, record.id
                combat = decode(
                    record.snapshot,
                    record.id,
                    activity.ruleset_version,
                    activity.state_version,
                )

        consumable_options = ()
        consumable_quantities = ()
        consumable_budget_limit = 0
        if (
            activity is not None
            and activity.status == "active"
            and combat is not None
        ):
            consumable_budget_limit = ENCOUNTER_CONSUMABLE_LIMITS.get(
                SPIDER.category, 0
            )
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
            stock_ids = tuple(row.consumable_id for row in stock)
            consumable_quantities = tuple(
                (row.consumable_id, row.quantity) for row in stock
            )
            consumable_options = combat_consumable_options(
                combat,
                stock_ids,
                budget_limit=consumable_budget_limit,
            )

        foreground = await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        )
        blocked_by_foreground = bool(
            foreground is not None and (activity is None or foreground != activity.id)
        )
        available = (
            await self._eligible(session, character, world, quest)
            if quest is None
            else False
        )
        if quest is None:
            kind = "offer" if available else "unavailable"
            status = None
            step = None
            state_version = 0
        else:
            status = quest.status
            step = quest.step
            state_version = quest.state_version
            if quest.status == "completed":
                kind = "completed"
            elif active is not None:
                kind = "combat"
            elif step == 1:
                kind = "travel"
            elif step == 2:
                kind = "ash_points"
            elif step == 3 and progress.get("awaiting_retry"):
                kind = "recovery"
            elif step == 3:
                kind = "combat_pending"
            elif step == 4:
                kind = "stone"
            elif step == 5:
                kind = "oren"
            else:
                kind = "alda"

        rewarded = bool(
            await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P2_REWARD_SOURCE,
                )
            )
        )
        result_state = progress.get("combat_result")
        if progress.get("awaiting_retry"):
            result_state = "awaiting_retry"
        return P2View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=step,
            state_version=state_version,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=available,
            combat=combat,
            activity_id=activity.id if activity is not None else None,
            activity_state_version=(
                activity.state_version if activity is not None else None
            ),
            activity_status=activity.status if activity is not None else None,
            encounter_id=encounter_id,
            combat_id=combat_id,
            result_state=result_state,
            rewarded=rewarded,
            blocked_by_foreground=blocked_by_foreground,
            consumable_options=consumable_options,
            consumable_quantities=consumable_quantities,
            consumable_budget_limit=consumable_budget_limit,
        )

    def _valid(self, quest, version, *, step=None):
        return bool(
            quest is not None
            and quest.status == "active"
            and quest.content_version == P2_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(
            world is not None
            and world.region == REGION
            and world.location == location
        )

    async def _ensure(self, session, model, **values):
        existing = await session.scalar(
            select(model).filter_by(**values).with_for_update()
        )
        if existing is not None:
            return existing
        row = model(**values)
        session.add(row)
        await session.flush()
        return row
