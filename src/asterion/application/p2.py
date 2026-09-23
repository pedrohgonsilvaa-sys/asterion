"""Authoritative P2 — Fuligem sem Fogo and normal-world movement."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.progression import consolidate_level
from asterion.application.road import RoadService, enemy_xp
from asterion.domain.combat import act
from asterion.domain.road import RULESET, create_road_combat, creature_for
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CombatRecord,
    Encounter,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

P2_ID = "P2"
P2_TITLE = "Fuligem sem Fogo"
P2_VERSION = "tdo-1.0.3"
P2_CONTENT_ID = "p2_scripted_encounter"
P2_REWARD_SOURCE = "p2.fuligem_sem_fogo"

REGION = "Terras do Ocaso"
ROAD = "Estrada das Cinzas"
REFUGE = "Refúgio do Ocaso"
CHARNECA = "Charneca da Fuligem"

ROAD_LOCATION_ID = "tdo.location.estrada_das_cinzas"
REFUGE_LOCATION_ID = "tdo.location.refugio_do_ocaso"
CHARNECA_LOCATION_ID = "tdo.location.charneca_da_fuligem"
CHARNECA_CONNECTION = "world.connection.tdo.refuge_road_charneca"

CHARNECA_HUNT_UNLOCK = "hunt_manual.charneca_da_fuligem"
CHARNECA_EXPLORE_UNLOCK = "explore.charneca_da_fuligem"
CHARNECA_ROUND_FAMILIARITY = "hunt_round.charneca_da_fuligem"

MARCAS_CODEX = "codex.mystery.marcas_na_fuligem"

P2_REWARDS = (
    ("xp", None, 3300),
    ("crowns", None, 140),
    ("material", "material.tdo.ferro_de_fuligem", 1),
    ("material", "material.tdo.erva_cinzenta", 2),
    ("material", "material.tdo.residuo_ocaso", 1),
)


@dataclass(frozen=True)
class P2View:
    kind: str
    character_id: UUID
    status: str
    step: int
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    combat: object | None = None
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    known_locations: tuple[str, ...] = ()


class P2Service(RoadService):
    """P2 state machine plus the first normal-world connection to Charneca."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        super().__init__(sessions, server_id)

    async def resume(self, actor: int) -> P2View | None:
        async with self.sessions() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            q = await self._quest(s, c.id)
            world = await self._world(s, c.id)
            if q is None or world is None:
                return None
            if q.content_version != P2_VERSION or q.status != "active":
                return None
            return await self._view(s, c, q, world, "detail")

    async def alda(self, actor: int) -> P2View | None:
        async with self.sessions() as s:
            c = await self._character(s, actor)
            if c is None or await self._foreground(s, c.id):
                return None
            world = await self._world(s, c.id)
            if (
                world is None
                or world.location != REFUGE
                or not await self._p1_completed(s, c.id)
            ):
                return None
            q = await self._quest(s, c.id)
            return await self._view(s, c, q, world, "alda")

    async def offer(self, actor: int) -> P2View | None:
        async with self.sessions() as s:
            c = await self._character(s, actor)
            if c is None or await self._foreground(s, c.id):
                return None
            world = await self._world(s, c.id)
            if (
                world is None
                or world.location != REFUGE
                or c.level < 3
                or not await self._p1_completed(s, c.id)
            ):
                return None
            q = await self._quest(s, c.id)
            if q is not None:
                return await self._view(s, c, q, world, "alda")
            return await self._view(s, c, q, world, "offer")

    async def accept(self, actor: int) -> P2View | None:
        async with self.sessions.begin() as s:
            c = await self._locked_character(s, actor)
            if c is None or await self._foreground(s, c.id):
                return None
            world = await self._locked_world_by_character(s, c.id)
            if (
                world is None
                or world.location != REFUGE
                or c.level < 3
                or not await self._p1_completed(s, c.id)
            ):
                return None
            q = await self._locked_quest(s, c.id)
            if q is None:
                q = Quest(
                    character_id=c.id,
                    quest_id=P2_ID,
                    title=P2_TITLE,
                    status="active",
                    step=1,
                    content_version=P2_VERSION,
                    progress={"points": []},
                )
                s.add(q)
                await self._ensure(
                    s,
                    Unlock,
                    character_id=c.id,
                    unlock_id=CHARNECA_CONNECTION,
                )
                await s.flush()
            return await self._view(s, c, q, world, "detail")

    async def objective(self, actor: int) -> P2View | None:
        async with self.sessions() as s:
            c = await self._character(s, actor)
            if c is None or await self._foreground(s, c.id):
                return None
            q = await self._quest(s, c.id)
            world = await self._world(s, c.id)
            if q is None or q.status != "active" or world is None:
                return None
            return await self._view(s, c, q, world, "objective")

    async def travel_normal(self, actor: int, destination: str) -> P2View | None:
        """Move through the permanently unlocked world connection, never via brazier."""
        async with self.sessions.begin() as s:
            c = await self._locked_character(s, actor)
            if c is None:
                return None
            world = await self._locked_world_by_character(s, c.id)
            if world is None:
                return None
            if await self._foreground(s, c.id):
                return None
            if not await self._connection_unlocked(s, c.id):
                return None
            valid = (
                world.location in {ROAD, REFUGE}
                and destination == CHARNECA
            ) or (
                world.location == CHARNECA
                and destination in {ROAD, REFUGE}
            )
            if not valid:
                return None
            q = await self._locked_quest(s, c.id)
            world.location = destination
            if destination == CHARNECA:
                first_arrival = await self._ensure(
                    s,
                    LocationDiscovery,
                    character_id=c.id,
                    location_id=CHARNECA_LOCATION_ID,
                )
                if q is not None and q.status == "active":
                    p = dict(q.progress or {})
                    if q.step == 1:
                        p["charneca_discovered_this_transition"] = bool(first_arrival)
                        p["charneca_arrived"] = True
                        q.step = 2
                        q.progress = p
                        q.state_version += 1
                    elif q.step == 3 and p.get("defeat"):
                        await self._materialize_scripted_encounter(s, c, q)
            if q is not None:
                return await self._view(s, c, q, world, "objective")
            return P2View(
                "world",
                c.id,
                "unaccepted",
                1,
                0,
                {},
                world.location,
                c.level,
                known_locations=await self._known_locations(s, c.id),
            )

    async def investigate_point(
        self, actor: int, point: int, version: int
    ) -> P2View | None:
        async with self.sessions.begin() as s:
            c, q, world = await self._locked_state(s, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid(q, version, 2)
                or world.location != CHARNECA
                or point not in {1, 2, 3}
                or await self._foreground(s, c.id)
            ):
                return await self._view(s, c, q, world, "objective")
            p = dict(q.progress or {})
            points = {
                int(value)
                for value in p.get("points", [])
                if int(value) in {1, 2, 3}
            }
            if point in points:
                return await self._view(s, c, q, world, "objective")
            points.add(point)
            p["points"] = sorted(points)
            q.progress = p
            q.state_version += 1
            if len(points) == 3:
                q.step = 3
                await self._materialize_scripted_encounter(s, c, q)
            return await self._view(s, c, q, world, "objective")

    async def action(
        self, actor: int, activity_id: UUID, version: int, action_id: str
    ) -> P2View | None:
        async with self.sessions.begin() as s:
            c, q, world = await self._locked_state(s, actor)
            if c is None or q is None or world is None:
                return None
            activity = await s.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == c.id,
                    GameActivity.content_id == P2_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None:
                return await self._view(s, c, q, world, "objective")
            if (
                not self._valid(q, q.state_version, 3)
                or activity.status != "active"
                or activity.state_version != version
            ):
                return await self._view(s, c, q, world, "objective")
            encounter, record = (
                await s.execute(
                    select(Encounter, CombatRecord)
                    .join(CombatRecord)
                    .where(Encounter.game_activity_id == activity.id)
                )
            ).one()
            combat = decode(
                record.snapshot,
                record.id,
                activity.ruleset_version,
                activity.state_version,
            )
            updated = act(combat, action_id)
            if updated.version == combat.version:
                return await self._view(s, c, q, world, "objective")
            activity.state_version = updated.version
            record.snapshot = encode(updated)
            c.hp = updated.fighters["player"].hp
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == activity.id)
            )
            evidence = set()
            if context is not None:
                evidence = await self._record_bestiary_combat_events(
                    s, c.id, context, updated
                )
            p = dict(q.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                if context is not None:
                    await self._settle_scripted_victory(
                        s, c, activity, encounter.id, context, evidence
                    )
                q.step = 4
                p["defeat"] = False
                p["recovery"] = False
                q.progress = p
                q.state_version += 1
                consolidate_level(c)
            elif updated.result == "defeat":
                activity.status = "failed"
                c.hp = c.max_hp
                world.region = REGION
                world.location = REFUGE
                p["defeat"] = True
                p["recovery"] = True
                q.progress = p
                q.state_version += 1
                consolidate_level(c)
            return await self._view(s, c, q, world, "objective")

    async def examine_stone(self, actor: int, version: int) -> P2View | None:
        async with self.sessions.begin() as s:
            c, q, world = await self._locked_state(s, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid(q, version, 4)
                or world.location != CHARNECA
                or await self._foreground(s, c.id)
            ):
                return await self._view(s, c, q, world, "objective")
            await self._ensure(
                s,
                CodexEntry,
                character_id=c.id,
                entry_id=MARCAS_CODEX,
            )
            p = dict(q.progress or {})
            p["marked_stone_examined"] = True
            q.progress = p
            q.step = 5
            q.state_version += 1
            return await self._view(s, c, q, world, "objective")

    async def deliver_record(self, actor: int, version: int) -> P2View | None:
        async with self.sessions.begin() as s:
            c, q, world = await self._locked_state(s, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid(q, version, 5)
                or world.location != REFUGE
                or await self._foreground(s, c.id)
            ):
                return await self._view(s, c, q, world, "oren")
            p = dict(q.progress or {})
            p["oren_record_delivered"] = True
            q.progress = p
            q.step = 6
            q.state_version += 1
            return await self._view(s, c, q, world, "oren_reported")

    async def complete_with_alda(self, actor: int, version: int) -> P2View | None:
        async with self.sessions.begin() as s:
            c, q, world = await self._locked_state(s, actor)
            if c is None or q is None or world is None:
                return None
            if (
                not self._valid(q, version, 6)
                or world.location != REFUGE
                or await self._foreground(s, c.id)
            ):
                return await self._view(s, c, q, world, "alda")
            await self._grant_final_reward(s, c)
            await self._ensure(
                s,
                LocationDiscovery,
                character_id=c.id,
                location_id=CHARNECA_LOCATION_ID,
            )
            await self._ensure(
                s,
                CodexEntry,
                character_id=c.id,
                entry_id=MARCAS_CODEX,
            )
            for unlock_id in (CHARNECA_HUNT_UNLOCK, CHARNECA_EXPLORE_UNLOCK):
                await self._ensure(
                    s,
                    Unlock,
                    character_id=c.id,
                    unlock_id=unlock_id,
                )
            p = dict(q.progress or {})
            p["completed"] = True
            q.progress = p
            q.status = "completed"
            q.state_version += 1
            consolidate_level(c)
            return await self._view(s, c, q, world, "completed")

    async def oren(self, actor: int) -> P2View | None:
        async with self.sessions() as s:
            c = await self._character(s, actor)
            if c is None or await self._foreground(s, c.id):
                return None
            q = await self._quest(s, c.id)
            world = await self._world(s, c.id)
            if q is None or world is None or world.location != REFUGE:
                return None
            return await self._view(s, c, q, world, "oren")

    async def _materialize_scripted_encounter(self, s, c, q) -> None:
        active = await s.scalar(
            select(GameActivity).where(
                GameActivity.character_id == c.id,
                GameActivity.status == "active",
            )
        )
        if active is not None:
            return
        p = dict(q.progress or {})
        creature_id = p.get("scripted_creature_id")
        if not creature_id:
            creature_id = "aranha_cinza" if c.level >= 3 else "peregrino_calcinado"
            p["scripted_creature_id"] = creature_id
        creature = creature_for(creature_id)
        level = min(c.level, creature.max_level)
        combat = create_road_combat(
            uuid4(),
            c.name,
            c.character_class,
            c.race,
            c.hp,
            creature,
            level,
            None,
            player_level=c.level,
        )
        combat.flavor = "A Charneca guarda ameaças entre a fuligem."
        combat.opening_log = f"🐾 {creature.name} surge na Charneca."
        activity, _, _ = await CombatRepository(s).create(
            c,
            P2_CONTENT_ID,
            combat,
        )
        s.add(
            HuntContext(
                game_activity_id=activity.id,
                character_id=c.id,
                creature_id=creature.creature_id,
                category=creature.category,
                enemy_level=level,
                variant=None,
                seed=f"p2:{q.id}:{creature.creature_id}",
                loot_profile="mission_scripted_p2",
            )
        )
        await self._bestiary(
            s,
            c.id,
            creature.creature_id,
            variant=None,
            elite=False,
            grant_observation_xp=True,
            observation_level=level,
            observation_category=creature.category,
        )
        p["defeat"] = False
        p["recovery"] = False
        q.progress = p
        q.state_version += 1
        await s.flush()

    async def _settle_scripted_victory(
        self,
        s,
        c,
        activity,
        encounter_id,
        context,
        bestiary_evidence_ids,
    ) -> None:
        source_id = f"p2:encounter:{encounter_id}"
        event = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=c.id, source_id=source_id)
            s.add(event)
            await s.flush()
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1),
                player_level=c.level,
            )
            c.xp += xp
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind="xp",
                    item_id=context.creature_id,
                    quantity=xp,
                    payload={"profile": "mission_scripted_p2"},
                )
            )
        update = await self._bestiary(
            s,
            c.id,
            context.creature_id,
            victory=True,
        )
        if update is None and bestiary_evidence_ids:
            update = {"evidence": sorted(bestiary_evidence_ids)}
        if update is not None:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind="bestiary",
                    item_id=context.creature_id,
                    quantity=1,
                    payload=update,
                )
            )

    async def _grant_final_reward(self, s, c) -> None:
        event = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == P2_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=P2_REWARD_SOURCE)
        s.add(event)
        await s.flush()
        c.xp += 3300
        c.crowns += 140
        for kind, item_id, quantity in P2_REWARDS:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                )
            )
            if kind == "material" and item_id is not None:
                remaining = await self._deliver_material_to_inventory(
                    s, c, item_id, quantity, True
                )
                if remaining:
                    await self._pending(
                        s,
                        c.id,
                        f"{P2_REWARD_SOURCE}:{item_id}",
                        "material",
                        {"material_id": item_id, "bound": True},
                        remaining,
                    )

    async def _view(
        self,
        s: AsyncSession,
        c: Character,
        q: Quest | None,
        world: WorldState,
        kind: str,
    ) -> P2View:
        combat = None
        activity_id = encounter_id = combat_id = None
        if q is not None and q.status == "active" and q.step == 3:
            activity = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id,
                    GameActivity.content_id == P2_CONTENT_ID,
                    GameActivity.status == "active",
                )
            )
            if activity is not None:
                encounter, record = (
                    await s.execute(
                        select(Encounter, CombatRecord)
                        .join(CombatRecord)
                        .where(Encounter.game_activity_id == activity.id)
                    )
                ).one()
                combat = decode(
                    record.snapshot,
                    record.id,
                    activity.ruleset_version,
                    activity.state_version,
                )
                activity_id = activity.id
                encounter_id = encounter.id
                combat_id = record.id
        status = q.status if q is not None else "unaccepted"
        step = q.step if q is not None else 1
        version = q.state_version if q is not None else 0
        progress = dict(q.progress or {}) if q is not None else {}
        return P2View(
            kind=kind,
            character_id=c.id,
            status=status,
            step=step,
            state_version=version,
            progress=progress,
            location=world.location,
            level=c.level,
            available=bool(q is None and c.level >= 3 and await self._p1_completed(s, c.id)),
            combat=combat,
            activity_id=activity_id,
            encounter_id=encounter_id,
            combat_id=combat_id,
            known_locations=await self._known_locations(s, c.id),
        )

    async def _locked_state(self, s, actor):
        c = await self._locked_character(s, actor)
        if c is None:
            return None, None, None
        q = await self._locked_quest(s, c.id)
        world = await self._locked_world_by_character(s, c.id)
        return c, q, world

    async def _locked_character(self, s, actor):
        return await s.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
            .with_for_update()
        )

    async def _quest(self, s, character_id):
        return await s.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == P2_ID,
            )
        )

    async def _locked_quest(self, s, character_id):
        return await s.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id == P2_ID,
            )
            .with_for_update()
        )

    async def _world(self, s, character_id):
        return await s.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )

    async def _locked_world_by_character(self, s, character_id):
        return await s.scalar(
            select(WorldState)
            .where(WorldState.character_id == character_id)
            .with_for_update()
        )

    async def _known_locations(self, s, character_id) -> tuple[str, ...]:
        return tuple(
            (
                await s.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character_id
                    )
                )
            ).all()
        )

    async def _connection_unlocked(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == CHARNECA_CONNECTION,
                )
            )
        )

    async def _foreground(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == character_id,
                    GameActivity.status == "active",
                )
            )
        )

    @staticmethod
    def _valid(q: Quest, version: int, step: int | None = None) -> bool:
        return bool(
            q.status == "active"
            and q.content_version == P2_VERSION
            and q.state_version == version
            and (step is None or q.step == step)
        )
