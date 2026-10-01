"""S4 mission flow, composed from persistent quests and scripted combat."""
# ruff: noqa: E501

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.progression import consolidate_character_level
from asterion.application.road import REFUGE, REGION, RUINS, RoadService
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
    CombatRecord,
    Encounter,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

S4_ID = "S4"
S4_TITLE = "Vigília sem Voz"
S4_VERSION = "tdo-1.0.11"
S4_CONTENT_ID = "s4_scripted_vigia_rachado"
S4_REWARD_SOURCE = "s4.vigilia_sem_voz"
S4_WATCH_POINTS = ("s4.watch_point.1", "s4.watch_point.2", "s4.watch_point.3")
S4_MATERIALS = (
    ("material.tdo.ferro_de_fuligem", 2),
    ("material.tdo.couro_escoriado", 1),
    ("material.tdo.residuo_ocaso", 1),
)


@dataclass(frozen=True)
class S4View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    eligible: bool = False
    reacceptable: bool = False
    context: str = "s4"
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
    tracked: bool = False


class S4Service:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def oren(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, await self._quest(session, character.id), world)

    async def offer(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            eligible = await self._eligible(session, character)
            available = bool(
                eligible and self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and (quest is None or quest.status == "abandoned")
            )
            return await self._view(
                session, character, quest, world,
                "offer" if available else "unavailable", available=available,
            )

    async def summary(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view(
                session, character, await self._quest(session, character.id),
                await self._world(session, character.id),
            )

    async def resume(self, actor: int) -> S4View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            return await self._view(session, character, quest, await self._world(session, character.id))

    async def detail(self, actor: int) -> S4View | None:
        view = await self.resume(actor)
        if view is None or view.status != "active" or view.kind == "combat":
            return view
        from dataclasses import replace

        return replace(view, kind="detail")

    async def accept(self, actor: int, version: int = 0, *, reaccept: bool = False) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                not self._at(world, REFUGE) or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            if reaccept:
                if quest is None or quest.status != "abandoned" or quest.state_version != version:
                    return await self._view(session, character, quest, world)
                quest.status = "active"
                quest.step = 1
                quest.content_version = S4_VERSION
                quest.progress = {"watch_points": []}
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world)
                quest = Quest(
                    character_id=character.id, quest_id=S4_ID, title=S4_TITLE,
                    status="active", step=1, content_version=S4_VERSION,
                    state_version=0, progress={"watch_points": []},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world)

    async def action(
        self, actor: int, version: int, operation: str, item: str | None = None,
    ) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            if operation == "watch" and quest.step == 1 and self._at(world, RUINS):
                if item not in S4_WATCH_POINTS:
                    return await self._view(session, character, quest, world)
                found = set(progress.get("watch_points", ()))
                if item in found:
                    return await self._view(session, character, quest, world)
                found.add(item)
                progress["watch_points"] = [key for key in S4_WATCH_POINTS if key in found]
                if len(found) == len(S4_WATCH_POINTS):
                    quest.step = 2
            elif operation == "orientation" and quest.step == 2 and self._at(world, RUINS):
                if progress.get("patrol_orientation_recorded"):
                    return await self._view(session, character, quest, world)
                progress["patrol_orientation_recorded"] = True
                quest.step = 3
                quest.progress = progress
                await self._materialize(session, character, quest)
                progress = dict(quest.progress or progress)
            elif operation == "turn_point" and quest.step == 4 and self._at(world, RUINS):
                if progress.get("patrol_turn_point_found"):
                    return await self._view(session, character, quest, world)
                progress["patrol_turn_point_found"] = True
                quest.step = 5
            elif operation == "examine" and quest.step == 5 and self._at(world, RUINS):
                if progress.get("turn_point_examined"):
                    return await self._view(session, character, quest, world)
                progress["turn_point_examined"] = True
                quest.step = 6
            elif operation == "report" and quest.step == 6 and self._at(world, REFUGE):
                await self._complete(session, character, quest)
                return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def retry(self, actor: int, version: int) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3) or not progress.get("awaiting_retry")
                or not self._at(world, RUINS) or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            progress["awaiting_retry"] = False
            quest.progress = progress
            if await self._materialize(session, character, quest) is None:
                progress["awaiting_retry"] = True
                quest.progress = progress
                return await self._view(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def abandon_confirmation(self, actor: int) -> S4View | None:
        view = await self.resume(actor)
        if view is None or view.status != "active" or view.kind == "combat":
            return None
        if await self._has_foreground(actor):
            return None
        from dataclasses import replace

        return replace(view, kind="abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            quest.status = "abandoned"
            quest.step = 1
            quest.progress = {}
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S4_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world)

    async def toggle_tracking(self, actor: int, version: int) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S4_ID else S4_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def action_combat(
        self, actor: int, activity_id: UUID, version: int, action: str | None = None, *,
        consumable_id: str | None = None, target_id: str | None = None, effect_id: str | None = None,
    ) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == activity_id, GameActivity.character_id == character.id,
                GameActivity.content_id == S4_CONTENT_ID,
            ).with_for_update())
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                not self._valid(quest, quest.state_version, step=3) or activity.status != "active"
                or activity.state_version != version or foreground is None or foreground.id != activity.id
                or (action is None) == (consumable_id is None)
            ):
                return current
            updated = await apply_action(
                session, character, activity, action=action, consumable_id=consumable_id,
                target_id=target_id, effect_id=effect_id, category=VIGIA.category,
            )
            if updated is None or updated.version == version:
                return current
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

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, *, screen: str = "items",
        item_id: str | None = None, target_id: str | None = None, parent: str = "items",
    ) -> S4View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == activity_id, GameActivity.character_id == character.id,
                GameActivity.content_id == S4_CONTENT_ID,
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
                from dataclasses import replace

                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    async def _materialize(self, session, character, quest):
        world = await self._world(session, character.id)
        if not self._at(world, RUINS) or await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session, character, S4_CONTENT_ID, VIGIA, 7,
            flavor="As marcas parecem ter conduzido o Vigia Rachado a este ponto.",
            opening_log="🛡️ Vigia Rachado · Nv.7 surge entre os antigos pontos de vigia.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{S4_REWARD_SOURCE}:enemy-xp:{activity.id}"
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
        event = await session.scalar(select(RewardEvent).where(
            RewardEvent.character_id == character.id,
            RewardEvent.source_id == S4_REWARD_SOURCE,
        ).with_for_update())
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S4_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 3990
            character.crowns += 150
            components = [
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=3990),
                RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=150),
                *[
                    RewardComponent(
                        reward_event_id=event.id, kind="material", item_id=material_id,
                        quantity=quantity, payload={"material_id": material_id, "bound": True},
                    )
                    for material_id, quantity in S4_MATERIALS
                ],
            ]
            session.add_all(components)
            for material_id, quantity in S4_MATERIALS:
                await self.road.deliver_material(
                    session, character, material_id, quantity,
                    f"{S4_REWARD_SOURCE}:material:{material_id}", bound=True,
                )
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        if character.tracked_secondary_quest_id == S4_ID:
            character.tracked_secondary_quest_id = None
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
                GameActivity.content_id == S4_CONTENT_ID,
            ))
            if activity is not None:
                row = (await session.execute(select(Encounter, CombatRecord).join(CombatRecord).where(
                    Encounter.game_activity_id == activity.id
                ))).one_or_none()
                if row:
                    encounter, record = row
                    if activity.status == "active":
                        combat = decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version)
        status = quest.status if quest else "unaccepted"
        eligible = await self._eligible(session, character)
        can_offer = bool(eligible and (quest is None or status == "abandoned"))
        if requested_kind:
            kind = requested_kind
        elif quest is None or status == "abandoned":
            kind = "offer" if can_offer and self._at(world, REFUGE) else "unavailable"
        elif status == "completed":
            kind = "completed"
        elif combat is not None:
            kind = "combat"
        elif quest.step == 3:
            kind = "recovery" if progress.get("awaiting_retry") else "combat_pending"
        elif quest.step == 6:
            kind = "report" if self._at(world, REFUGE) else "return"
        elif not self._at(world, RUINS):
            kind = "travel"
        elif quest.step == 1:
            kind = "watch_points"
        elif quest.step == 2:
            kind = "orientation"
        elif quest.step == 4:
            kind = "turn_point"
        else:
            kind = "examine"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(session, character, combat, VIGIA.category)
        return S4View(
            character_id=character.id, kind=kind, status=status, step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0, progress=progress,
            location=world.location if world else "", level=character.level,
            available=bool(available if available is not None else can_offer), eligible=eligible,
            reacceptable=bool(quest and status == "abandoned" and eligible), combat=combat,
            activity_id=activity.id if activity else None,
            activity_state_version=activity.state_version if activity else None,
            activity_status=activity.status if activity else None,
            encounter_id=encounter.id if encounter else None, combat_id=record.id if record else None,
            consumable_options=options, consumable_quantities=quantities,
            consumable_budget_limit=budget, xp=character.xp,
            tracked=bool(quest and status == "active" and character.tracked_secondary_quest_id == S4_ID),
        )

    async def _eligible(self, session, character):
        return bool(character.level >= 7 and await session.scalar(select(Quest.id).where(
            Quest.character_id == character.id, Quest.quest_id == "P4", Quest.status == "completed",
        )))

    async def _locked_state(self, session, actor):
        character = await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ).with_for_update())
        if character is None:
            return None, None, None
        quest = await session.scalar(select(Quest).where(
            Quest.character_id == character.id, Quest.quest_id == S4_ID
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
            Quest.character_id == character_id, Quest.quest_id == S4_ID
        ))

    async def _world(self, session, character_id):
        return await session.scalar(select(WorldState).where(WorldState.character_id == character_id))

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity).where(
            GameActivity.character_id == character_id, GameActivity.status == "active"
        ))

    async def _has_foreground(self, actor):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return bool(character and await self._foreground(session, character.id))

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest and quest.status == "active" and quest.content_version == S4_VERSION
            and quest.state_version == version and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
