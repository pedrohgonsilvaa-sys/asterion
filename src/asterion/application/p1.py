"""Authoritative application service for P1: Vozes na Estrada."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.domain.combat import Combat, act
from asterion.domain.prologue import P1_CONTENT_ID, RULESET, p1_combat_profile
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    CodexEntry,
    CombatRecord,
    Encounter,
    GameActivity,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

P1_ID = "P1"
P1_VERSION = "tdo-1.0.2"
ROAD = "Estrada das Cinzas"
REGION = "Terras do Ocaso"
REFUGE = "Refúgio do Ocaso"
REFUGE_BRAZIER = "tdo.brazier.refugio_do_ocaso"


@dataclass(frozen=True)
class P1View:
    character_id: UUID
    step: int
    state_version: int
    progress: dict
    combat: Combat | None = None
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    context: str = "p1"
    status: str = "active"
    known_locations: tuple[str, ...] = ()


class P1Service:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id

    async def resume(self, actor: int):
        async with self.sessions() as s:
            c = await self._character(s, actor)
            q = await self._quest(s, c.id) if c else None
            return await self._view(s, c, q) if q and q.content_version == P1_VERSION else None

    async def follow_road(self, actor: int, version: int):
        return await self._mutate(actor, version, 1, self._follow)

    async def examine(self, actor: int, signal: str, version: int):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, 2):
                return await self._view(s, c, q)
            p = dict(q.progress or {})
            if signal == "pegadas" and not p.get("pegadas"):
                p["pegadas"] = True
            elif signal == "sulcos" and p.get("pegadas") and not p.get("sulcos"):
                p["sulcos"] = True
                q.step = 3
                await CombatRepository(s).create(
                    c,
                    P1_CONTENT_ID,
                    p1_combat_profile(uuid4(), c.name, c.character_class, c.race, c.hp),
                )
            else:
                return await self._view(s, c, q)
            q.progress, q.state_version = p, q.state_version + 1
            return await self._view(s, c, q)

    async def action(self, actor: int, activity_id: UUID, version: int, action: str):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            a = (
                await s.scalar(
                    select(GameActivity)
                    .where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == c.id if c else False,
                        GameActivity.content_id == P1_CONTENT_ID,
                    )
                    .with_for_update()
                )
                if c
                else None
            )
            if a is None:
                return None
            if (
                q is None
                or q.status != "active"
                or q.content_version != P1_VERSION
                or q.step != 3
                or a.status != "active"
                or a.state_version != version
            ):
                return await self._view(s, c, q)
            e, r = (
                await s.execute(
                    select(Encounter, CombatRecord)
                    .join(CombatRecord)
                    .where(Encounter.game_activity_id == a.id)
                )
            ).one()
            combat = decode(r.snapshot, r.id, a.ruleset_version, a.state_version)
            updated = act(combat, action)
            if updated.version == combat.version:
                return await self._view(s, c, q)
            a.state_version = updated.version
            r.snapshot = encode(updated)
            c.hp = updated.fighters["player"].hp
            p = dict(q.progress or {})
            if updated.result == "victory":
                a.status = "completed"
                q.step = 4
                p.update(arrival=True, defeat=False)
                c.ruleset_version = RULESET
            elif updated.result == "defeat":
                a.status = "failed"
                q.step = 3
                c.hp = c.max_hp
                p.update(defeat=True, recovery=True)
                w = await s.scalar(
                    select(WorldState).where(WorldState.character_id == c.id).with_for_update()
                )
                if w:
                    w.region, w.location = REGION, ROAD
            q.progress, q.state_version = p, q.state_version + 1
            return await self._view(s, c, q)

    async def retry(self, actor: int, version: int):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, 3) or not (q.progress or {}).get("defeat"):
                return await self._view(s, c, q)
            await CombatRepository(s).create(
                c,
                P1_CONTENT_ID,
                p1_combat_profile(uuid4(), c.name, c.character_class, c.race, c.hp),
            )
            p = dict(q.progress or {})
            p.update(defeat=False, recovery=False)
            q.progress, q.state_version = p, q.state_version + 1
            return await self._view(s, c, q)

    async def enter_refuge(self, actor: int, version: int):
        return await self._mutate(actor, version, 4, self._enter_refuge)

    async def follow_alda(self, actor: int, version: int):
        return await self._mutate(actor, version, 5, self._alda)

    async def go_brazier(self, actor: int, version: int):
        return await self._mutate(actor, version, 6, self._oren)

    async def activate_brazier(self, actor: int, version: int):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, 7):
                return await self._view(s, c, q)
            active = await s.scalar(
                select(GameActivity)
                .where(GameActivity.character_id == c.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active is not None:
                return await self._view(s, c, q)
            await self._ensure(s, Brazier, character_id=c.id, brazier_id=REFUGE_BRAZIER)
            event = await s.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == c.id, RewardEvent.source_id == "p1.vozes_na_estrada"
                )
                .with_for_update()
            )
            if event is None:
                event = RewardEvent(character_id=c.id, source_id="p1.vozes_na_estrada")
                s.add(event)
                await s.flush()
                c.xp += 2400
                c.crowns += 120
                for kind, item, n in (
                    ("xp", None, 2400),
                    ("crowns", None, 120),
                    ("material", "material.tdo.ferro_de_fuligem", 1),
                    ("material", "material.tdo.couro_escoriado", 1),
                ):
                    s.add(
                        RewardComponent(
                            reward_event_id=event.id, kind=kind, item_id=item, quantity=n
                        )
                    )
                for item in ("material.tdo.ferro_de_fuligem", "material.tdo.couro_escoriado"):
                    stack = await s.scalar(
                        select(MaterialStack)
                        .where(
                            MaterialStack.character_id == c.id,
                            MaterialStack.material_id == item,
                            MaterialStack.bound.is_(True),
                        )
                        .with_for_update()
                    )
                    if stack is None:
                        s.add(
                            MaterialStack(
                                character_id=c.id, material_id=item, quantity=1, bound=True
                            )
                        )
                    else:
                        stack.quantity += 1
                for uid in ("hunt_manual.estrada_das_cinzas", "explore.estrada_das_cinzas"):
                    await self._ensure(s, Unlock, character_id=c.id, unlock_id=uid)
            q.status = "completed"
            p = dict(q.progress or {})
            p["completed"] = True
            q.progress, q.state_version = p, q.state_version + 1
            return await self._view(s, c, q)

    async def _mutate(self, actor, version, step, fn):
        async with self.sessions.begin() as s:
            c, q = await self._locked(s, actor)
            if not self._valid(c, q, version, step):
                return await self._view(s, c, q)
            changed = await fn(s, c, q)
            if changed is not False:
                q.state_version += 1
            return await self._view(s, c, q)

    async def _follow(self, s, c, q):
        q.step = 2
        return True

    async def _enter_refuge(self, s, c, q):
        await self._ensure(
            s, LocationDiscovery, character_id=c.id, location_id="tdo.location.refugio_do_ocaso"
        )
        w = await s.scalar(
            select(WorldState).where(WorldState.character_id == c.id).with_for_update()
        )
        if w is None:
            return False
        w.region, w.location = REGION, REFUGE
        q.step = 5
        return True

    async def _alda(self, s, c, q):
        await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.figure.alda_veyr")
        q.step = 6
        return True

    async def _oren(self, s, c, q):
        await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.figure.oren_cal")
        q.step = 7
        return True

    async def _locked(self, s, actor):
        c = await s.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        q = (
            await s.scalar(
                select(Quest)
                .where(Quest.character_id == c.id, Quest.quest_id == P1_ID)
                .with_for_update()
            )
            if c
            else None
        )
        return c, q

    async def _character(self, s, actor):
        return await s.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _quest(self, s, cid):
        return await s.scalar(
            select(Quest).where(Quest.character_id == cid, Quest.quest_id == P1_ID)
        )

    def _valid(self, c, q, v, step=None):
        return bool(
            c
            and q
            and q.status == "active"
            and q.content_version == P1_VERSION
            and q.state_version == v
            and (step is None or q.step == step)
        )

    async def _view(self, s, c, q):
        if c is None or q is None:
            return None
        a = await s.scalar(
            select(GameActivity).where(
                GameActivity.character_id == c.id,
                GameActivity.content_id == P1_CONTENT_ID,
                GameActivity.status == "active",
            )
        )
        locations = tuple(
            (
                await s.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == c.id
                    )
                )
            ).all()
        )
        if a is None:
            return P1View(
                c.id,
                q.step,
                q.state_version,
                q.progress or {},
                status=q.status,
                known_locations=locations,
            )
        e, r = (
            await s.execute(
                select(Encounter, CombatRecord)
                .join(CombatRecord)
                .where(Encounter.game_activity_id == a.id)
            )
        ).one()
        combat = decode(r.snapshot, r.id, a.ruleset_version, a.state_version)
        return P1View(
            c.id,
            q.step,
            q.state_version,
            q.progress or {},
            combat,
            a.id,
            e.id,
            r.id,
            status=q.status,
            known_locations=locations,
        )

    async def _ensure(self, s, model, **values):
        obj = await s.scalar(select(model).filter_by(**values).with_for_update())
        if obj is None:
            s.add(model(**values))
        return obj
