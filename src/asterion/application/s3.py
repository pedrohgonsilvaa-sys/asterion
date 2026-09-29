"""S3-specific quest flow built on the shared combat, bestiary, and delivery systems."""
# ruff: noqa: E501

from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.progression import consolidate_character_level
from asterion.application.road import BOSQUE, P3_QUEST_ID, REFUGE, REGION, RoadService
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    derive_consumable_selection,
    materialize,
    normalize_character_hp,
)
from asterion.domain.road import BOSQUE_LOCATION, CERVO, enemy_xp
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    Encounter,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

S3_ID = "S3"
S3_TITLE = "Rastros sob os Galhos"
S3_VERSION = "tdo-1.0.11"
S3_CONTENT_ID = "s3_scripted_cervo_escoriado"
S3_REWARD_SOURCE = "s3.rastros_sob_os_galhos"
S3_TRACKS = ("s3.track.1", "s3.track.2", "s3.track.3")
S3_MATERIAL = "material.tdo.couro_escoriado"


@dataclass(frozen=True)
class S3View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    reacceptable: bool = False
    context: str = "s3"
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
    campaign_active: bool = False
    tracked: bool = False


class S3Service:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def alda(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "alda")

    async def offer(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            available = (
                (quest is None or quest.status == "abandoned")
                and self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and await self._eligible(session, character)
            )
            return await self._view(
                session,
                character,
                quest,
                world,
                "offer" if available else "unavailable",
                available=available,
            )

    async def resume(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            return await self._view(
                session, character, quest, await self._world(session, character.id)
            )

    async def detail(self, actor: int) -> S3View | None:
        view = await self.resume(actor)
        if view is None or view.status != "active" or view.kind == "combat":
            return view
        return replace(view, kind="detail")

    async def accept(self, actor: int, version: int = 0, *, reaccept: bool = False) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                not self._at(world, REFUGE)
                or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            if reaccept:
                if quest is None or quest.status != "abandoned" or quest.state_version != version:
                    return await self._view(session, character, quest, world)
                quest.status = "active"
                quest.step = 1
                quest.progress = {"tracks": []}
                quest.content_version = S3_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world)
                quest = Quest(
                    character_id=character.id,
                    quest_id=S3_ID,
                    title=S3_TITLE,
                    status="active",
                    step=1,
                    content_version=S3_VERSION,
                    state_version=0,
                    progress={"tracks": []},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world)

    async def interact(self, actor: int, version: int, action: str, item: str | None = None) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            if action == "route" and quest.step == 1 and self._at(world, BOSQUE):
                progress["supply_route_examined"] = True
                progress["tracks"] = []
                quest.step = 2
            elif action == "track" and quest.step == 2 and self._at(world, BOSQUE):
                if item not in S3_TRACKS:
                    return await self._view(session, character, quest, world)
                tracks = set(progress.get("tracks", ()))
                if item in tracks:
                    return await self._view(session, character, quest, world)
                tracks.add(item)
                progress["tracks"] = [track for track in S3_TRACKS if track in tracks]
                if len(tracks) == len(S3_TRACKS):
                    quest.step = 3
                    progress.update(awaiting_retry=False, combat_result=None)
                    quest.progress = progress
                    await self._materialize(session, character, quest)
                    progress = dict(quest.progress or progress)
            elif action == "cargo" and quest.step == 4 and self._at(world, BOSQUE):
                progress["cargo_checked"] = True
                quest.step = 5
            elif action == "report" and quest.step == 5 and self._at(world, REFUGE):
                await self._complete(session, character, quest)
                return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def retry(self, actor: int, version: int) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or not progress.get("awaiting_retry")
                or not self._at(world, BOSQUE)
                or await self._foreground(session, character.id)
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

    async def abandon(self, actor: int, version: int) -> S3View | None:
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
            if character.tracked_secondary_quest_id == S3_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world)

    async def abandon_confirmation(self, actor: int) -> S3View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active" or world is None:
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def toggle_tracking(self, actor: int, version: int) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S3_ID else S3_ID
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
    ) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S3_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                not self._valid(quest, quest.state_version, step=3)
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
                category=CERVO.category,
            )
            if updated is None:
                return current
            await self.bestiary.record_combat_events(
                session, character.id, CERVO.creature_id, None, updated
            )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session, character.id, CERVO.creature_id, victory=True,
                    observation_category="common",
                )
                progress.update(combat_result="victory", awaiting_retry=False)
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session, character.id, CERVO.creature_id, observation_category="common"
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, BOSQUE_LOCATION, world
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
        self, actor: int, activity_id: UUID, version: int, *,
        screen: str = "items", item_id: str | None = None,
        target_id: str | None = None, parent: str = "items",
    ) -> S3View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S3_CONTENT_ID,
                ).with_for_update()
            )
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

    async def _materialize(self, session, character, quest):
        world = await self._world(session, character.id)
        if not self._at(world, BOSQUE) or await self._foreground(session, character.id):
            return None
        from dataclasses import replace

        creature = replace(CERVO, ai=("ocaso_charge", "antler_gore"))
        activity = await materialize(
            session, character, S3_CONTENT_ID, creature, 5,
            flavor="Rastros recentes terminam diante de um Cervo Escoriado.",
            opening_log="🦌 Cervo Escoriado · Nv.5 surge entre os galhos.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{S3_REWARD_SOURCE}:enemy-xp:{activity.id}"
        if await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id, RewardEvent.source_id == source
            ).with_for_update()
        ):
            return
        amount = enemy_xp(5, "common", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id, kind="enemy_xp", item_id=CERVO.creature_id,
                quantity=amount, payload={"enemy_level": 5, "category": "common"},
            )
        )
        character.xp += amount

    async def _complete(self, session, character, quest):
        source = S3_REWARD_SOURCE
        event = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source)
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=source)
            session.add(event)
            await session.flush()
            character.xp += 1760
            character.crowns += 90
            session.add_all(
                [
                    RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=1760),
                    RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=90),
                    RewardComponent(reward_event_id=event.id, kind="material", item_id=S3_MATERIAL, quantity=2,
                                    payload={"material_id": S3_MATERIAL, "bound": True}),
                ]
            )
            await self.road.deliver_material(
                session, character, S3_MATERIAL, 2, f"{S3_REWARD_SOURCE}:material:{S3_MATERIAL}", bound=True
            )
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        if character.tracked_secondary_quest_id == S3_ID:
            character.tracked_secondary_quest_id = None
        await consolidate_character_level(session, character)

    async def _view(self, session, character, quest, world, requested_kind=None, *, available=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        stored = progress.get("combat_activity_id")
        if stored:
            try:
                activity_id = UUID(stored)
            except (TypeError, ValueError):
                activity_id = None
            if activity_id:
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == S3_CONTENT_ID,
                    )
                )
                if activity is not None:
                    row = (
                        await session.execute(
                            select(Encounter, CombatRecord).join(CombatRecord)
                            .where(Encounter.game_activity_id == activity.id)
                        )
                    ).one_or_none()
                    if row:
                        encounter, record = row
                        if activity.status == "active":
                            combat = decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version)
        status = quest.status if quest else "unaccepted"
        available = (
            (quest is None or quest.status == "abandoned")
            and await self._eligible(session, character)
            if available is None else available
        )
        if requested_kind:
            kind = requested_kind
        elif quest is None or status == "abandoned":
            kind = "offer" if available else "unavailable"
        elif status == "completed":
            kind = "completed"
        elif combat is not None:
            kind = "combat"
        elif quest.step == 1:
            kind = "route"
        elif quest.step == 2:
            kind = "tracks"
        elif quest.step == 3:
            kind = "recovery" if progress.get("awaiting_retry") else "combat_pending"
        elif quest.step == 4:
            kind = "cargo"
        else:
            kind = "report"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(session, character, combat, CERVO.category)
        campaign_active = bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == P3_QUEST_ID,
                    Quest.status == "active",
                )
            )
        )
        return S3View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=bool(available and (quest is None or status == "abandoned")),
            reacceptable=bool(quest and status == "abandoned" and available),
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
            campaign_active=campaign_active,
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S3_ID
            ),
        )

    async def _eligible(self, session, character):
        p3 = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P3_QUEST_ID,
                Quest.status.in_(("active", "completed")),
            )
        )
        known = await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id, LocationDiscovery.location_id == BOSQUE_LOCATION
            )
        )
        return bool(p3 and known and character.level >= 5)

    async def _locked_state(self, session, actor):
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor, Character.server_id == self.server_id).with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == S3_ID).with_for_update()
        )
        world = await session.scalar(select(WorldState).where(WorldState.character_id == character.id).with_for_update())
        return character, quest, world

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(Character.telegram_id == actor, Character.server_id == self.server_id))

    async def _quest(self, session, character_id):
        return await session.scalar(select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S3_ID))

    async def _world(self, session, character_id):
        return await session.scalar(select(WorldState).where(WorldState.character_id == character_id))

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity).where(GameActivity.character_id == character_id, GameActivity.status == "active"))

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(quest and quest.status == "active" and quest.content_version == S3_VERSION and quest.state_version == version and (step is None or quest.step == step))

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
