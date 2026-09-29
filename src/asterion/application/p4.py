"""P4 mission-specific campaign flow for the Ruínas do Vigia."""
# ruff: noqa: E501

from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.progression import consolidate_character_level
from asterion.application.road import (
    BOSQUE,
    P3_QUEST_ID,
    REFUGE,
    REGION,
    RUINS,
    RoadService,
)
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    derive_consumable_selection,
    materialize,
    normalize_character_hp,
)
from asterion.domain.road import RUINS_LOCATION, VIGIA, enemy_xp
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    Encounter,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

P4_ID = "P4"
P4_TITLE = "Pedras que Ainda Vigiam"
P4_VERSION = "tdo-1.0.11"
P4_CONTENT_ID = "p4_scripted_vigia_rachado"
P4_REWARD_SOURCE = "p4.pedras_que_ainda_vigiam"
P4_STRUCTURES = ("p4.guard_structure.1", "p4.guard_structure.2")
P4_ROUTE_UNLOCK = "route.tdo.bosque_ruinas"
P4_HUNT_UNLOCK = "hunt_manual.ruinas_do_vigia"
P4_EXPLORE_UNLOCK = "explore.ruinas_do_vigia"
P4_CODEX_ENTRY = "codex.history.antigos_asterianos"
P4_CODEX_FRAGMENT = "p4.ruinas.funcao_de_guarda"
P4_IRON = "material.tdo.ferro_de_fuligem"
P4_RESIDUE = "material.tdo.residuo_ocaso"


@dataclass(frozen=True)
class P4View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p4"
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


class P4Service:
    """Owns only P4 state transitions; movement and combat rules stay shared."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def alda(self, actor: int) -> P4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "alda")

    async def offer(self, actor: int) -> P4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            available = quest is None and self._at(world, REFUGE) and not await self._foreground(
                session, character.id
            ) and await self._eligible(session, character)
            return await self._view(
                session, character, quest, world,
                "offer" if available else "unavailable", available=available,
            )

    async def resume(self, actor: int) -> P4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def accept(self, actor: int, version: int = 0) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                quest is not None or version != 0 or not self._at(world, REFUGE)
                or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            quest = Quest(
                character_id=character.id, quest_id=P4_ID, title=P4_TITLE,
                status="active", step=1, content_version=P4_VERSION,
                state_version=0, progress={},
            )
            session.add(quest)
            await session.flush()
            return await self._view(session, character, quest, world)

    async def action(self, actor: int, version: int, operation: str, item: str | None = None) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            if operation == "path" and quest.step == 1 and self._at(world, BOSQUE):
                # Campaign passage; no ExplorationAttempt or Explore reward.
                progress["western_path_followed"] = True
                quest.step = 2
            elif (
                operation == "enter" and quest.step == 2
                and progress.get("western_path_followed") and self._at(world, BOSQUE)
            ):
                await self._ensure(
                    session, LocationDiscovery, character_id=character.id,
                    location_id=RUINS_LOCATION,
                )
                await self._ensure(
                    session, Unlock, character_id=character.id, unlock_id=P4_ROUTE_UNLOCK
                )
                world.region = REGION
                world.location = RUINS
                progress.update(ruins_discovered=True, awaiting_retry=False)
                quest.step = 3
                quest.progress = progress
                await self._materialize(session, character, quest)
                progress = dict(quest.progress or progress)
            elif (
                operation == "enter" and quest.step == 3
                and progress.get("awaiting_retry") and self._at(world, BOSQUE)
                and await self._has_unlock(session, character.id, P4_ROUTE_UNLOCK)
            ):
                world.region = REGION
                world.location = RUINS
                progress["returned_for_retry"] = True
            elif operation == "retry" and quest.step == 3 and progress.get("awaiting_retry"):
                if not self._at(world, RUINS):
                    return await self._view(session, character, quest, world)
                progress["awaiting_retry"] = False
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    progress["awaiting_retry"] = True
                    quest.progress = progress
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif operation == "structure" and quest.step == 4 and self._at(world, RUINS):
                if item not in P4_STRUCTURES:
                    return await self._view(session, character, quest, world)
                found = set(progress.get("structures", ()))
                if item in found:
                    return await self._view(session, character, quest, world)
                found.add(item)
                progress["structures"] = [key for key in P4_STRUCTURES if key in found]
                if len(found) == 2:
                    quest.step = 5
            elif operation == "safe_route" and quest.step == 5 and self._at(world, RUINS):
                progress["safe_route_identified"] = True
                quest.step = 6
            elif operation == "return" and quest.step == 6 and self._at(world, RUINS):
                if not await self._has_unlock(session, character.id, P4_ROUTE_UNLOCK):
                    return await self._view(session, character, quest, world)
                world.region = REGION
                world.location = BOSQUE
                progress["returned_to_bosque"] = True
            elif operation in {"report_alda", "report_oren"} and quest.step == 6 and self._at(world, REFUGE):
                progress["reports"] = list(progress.get("reports", ()))
                person = "alda" if operation.endswith("alda") else "oren"
                if person not in progress["reports"]:
                    progress["reports"].append(person)
                if set(progress["reports"]) == {"alda", "oren"}:
                    quest.progress = progress
                    await self._complete(session, character, quest)
                    return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, *,
        screen: str = "items", item_id: str | None = None,
        target_id: str | None = None, parent: str = "items",
    ) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == activity_id, GameActivity.character_id == character.id,
                GameActivity.content_id == P4_CONTENT_ID,
            ).with_for_update())
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                quest.status != "active" or quest.step != 3 or activity.status != "active"
                or foreground is None or foreground.id != activity.id
            ):
                return current
            if activity.state_version != version:
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    async def action_combat(
        self, actor: int, activity_id: UUID, version: int, action: str | None = None,
        *, consumable_id: str | None = None, target_id: str | None = None,
        effect_id: str | None = None,
    ) -> P4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P4_CONTENT_ID,
                ).with_for_update()
            )
            if activity is None:
                return None
            current_view = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                not self._valid(quest, quest.state_version, step=3)
                or activity.status != "active" or activity.state_version != version
                or foreground is None or foreground.id != activity.id
                or (action is None) == (consumable_id is None)
            ):
                return current_view
            updated = await apply_action(
                session, character, activity, action=action, consumable_id=consumable_id,
                target_id=target_id, effect_id=effect_id, category=VIGIA.category,
            )
            if updated is None:
                return current_view
            await self.bestiary.record_combat_events(
                session, character.id, VIGIA.creature_id, None, updated
            )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session, character.id, VIGIA.creature_id, victory=True,
                    observation_category="common",
                )
                progress.update(combat_result="victory", awaiting_retry=False)
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session, character.id, VIGIA.creature_id, observation_category="common"
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, RUINS_LOCATION, world
                )
                progress.update(
                    combat_result="defeat", awaiting_retry=True,
                    defeat_activity_id=str(activity.id), recovery_brazier=brazier,
                    recovery_location=location,
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _materialize(self, session, character, quest):
        if await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session, character, P4_CONTENT_ID, VIGIA, 7,
            flavor="Um Vigia Rachado se ergue entre as estruturas de guarda.",
            opening_log="🛡️ Vigia Rachado · Nv.7 protege os limites das Ruínas.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{P4_REWARD_SOURCE}:enemy-xp:{activity.id}"
        if await session.scalar(select(RewardEvent.id).where(
            RewardEvent.character_id == character.id, RewardEvent.source_id == source
        ).with_for_update()):
            return
        amount = enemy_xp(7, "common", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        session.add(RewardComponent(
            reward_event_id=event.id, kind="enemy_xp", item_id=VIGIA.creature_id,
            quantity=amount, payload={"enemy_level": 7, "category": "common"},
        ))
        character.xp += amount

    async def _complete(self, session, character, quest):
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P4_REWARD_SOURCE,
            ).with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P4_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 5700
            character.crowns += 250
            components = [
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=5700),
                RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=250),
                RewardComponent(reward_event_id=event.id, kind="material", item_id=P4_IRON, quantity=2,
                                payload={"material_id": P4_IRON, "bound": True}),
                RewardComponent(reward_event_id=event.id, kind="material", item_id=P4_RESIDUE, quantity=2,
                                payload={"material_id": P4_RESIDUE, "bound": True}),
            ]
            session.add_all(components)
            await self.road.deliver_material(session, character, P4_IRON, 2,
                                             f"{P4_REWARD_SOURCE}:material:{P4_IRON}", bound=True)
            await self.road.deliver_material(session, character, P4_RESIDUE, 2,
                                             f"{P4_REWARD_SOURCE}:material:{P4_RESIDUE}", bound=True)
        await self._ensure(session, CodexEntry, character_id=character.id, entry_id=P4_CODEX_ENTRY)
        await self._ensure(session, CodexFragment, character_id=character.id,
                           entry_id=P4_CODEX_ENTRY, fragment_id=P4_CODEX_FRAGMENT)
        await self._ensure(session, Unlock, character_id=character.id, unlock_id=P4_HUNT_UNLOCK)
        await self._ensure(session, Unlock, character_id=character.id, unlock_id=P4_EXPLORE_UNLOCK)
        await self._ensure(session, Unlock, character_id=character.id, unlock_id=P4_ROUTE_UNLOCK)
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
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
        if stored_id:
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == stored_id, GameActivity.character_id == character.id,
                GameActivity.content_id == P4_CONTENT_ID,
            ))
            if activity:
                row = (await session.execute(
                    select(Encounter, CombatRecord).join(CombatRecord).where(
                        Encounter.game_activity_id == activity.id
                    )
                )).one_or_none()
                if row:
                    encounter, record = row
                    if activity.status == "active":
                        combat = decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version)
        status = quest.status if quest else "unaccepted"
        available = (
            quest is None and await self._eligible(session, character)
            if available is None else available
        )
        if requested_kind:
            kind = requested_kind
        elif quest is None:
            kind = "offer" if available else "unavailable"
        elif status == "completed":
            kind = "completed"
        elif combat is not None:
            kind = "combat"
        elif quest.step == 1:
            kind = "path"
        elif quest.step == 2:
            kind = "enter_ruins" if self._at(world, BOSQUE) else "path"
        elif quest.step == 3:
            kind = "recovery" if progress.get("awaiting_retry") else "combat_pending"
        elif quest.step == 4:
            kind = "structures"
        elif quest.step == 5:
            kind = "safe_route"
        else:
            kind = "reports" if self._at(world, REFUGE) else "return"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(session, character, combat, VIGIA.category)
        return P4View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=bool(available and quest is None),
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
        )

    async def _eligible(self, session, character):
        return bool(
            character.level >= 7 and await session.scalar(select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P3_QUEST_ID,
                Quest.status == "completed",
            ))
        )

    async def _ensure(self, session, model, **values):
        row = await session.scalar(select(model).filter_by(**values).with_for_update())
        if row is None:
            row = model(**values)
            session.add(row)
            await session.flush()
        return row

    async def _has_unlock(self, session, character_id, unlock_id):
        return bool(await session.scalar(select(Unlock.id).where(
            Unlock.character_id == character_id, Unlock.unlock_id == unlock_id
        )))

    async def _locked_state(self, session, actor):
        character = await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ).with_for_update())
        if character is None:
            return None, None, None
        quest = await session.scalar(select(Quest).where(
            Quest.character_id == character.id, Quest.quest_id == P4_ID
        ).with_for_update())
        world = await session.scalar(select(WorldState).where(
            WorldState.character_id == character.id
        ).with_for_update())
        return character, quest, world

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ))

    async def _quest(self, session, character_id):
        return await session.scalar(select(Quest).where(
            Quest.character_id == character_id, Quest.quest_id == P4_ID
        ))

    async def _world(self, session, character_id):
        return await session.scalar(select(WorldState).where(WorldState.character_id == character_id))

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity).where(
            GameActivity.character_id == character_id, GameActivity.status == "active"
        ))

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(quest and quest.status == "active" and quest.content_version == P4_VERSION
                    and quest.state_version == version and (step is None or quest.step == step))

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
