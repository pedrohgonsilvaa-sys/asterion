"""Persistent P19/S19 progression for the Várzeas opening slice."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import RoadService
from asterion.application.varzeas_feats import reconcile_varzeas_feats
from asterion.domain.road import (
    VARZEAS_DIQUES,
    VARZEAS_DIQUES_BRAZIER,
    VARZEAS_DIQUES_EXPLORE_UNLOCK,
    VARZEAS_DIQUES_HUNT_UNLOCK,
    VARZEAS_DIQUES_LOCATION,
    VARZEAS_DIQUES_PORTO_ROUTE,
    VARZEAS_PORTO,
    VARZEAS_PORTO_BRAZIER,
    VARZEAS_PORTO_LOCATION,
    VARZEAS_REGION_ENTRY_UNLOCK,
)
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

REGION = "Várzeas Carmesins"
P19_ID = "P19"
S19_ID = "S19"
P19_TITLE = "Águas de Ferro"
S19_TITLE = "Sal nas Feridas"
CONTENT_VERSION = "varzeas-1.0.0"
P19_REWARD_SOURCE = "p19.aguas_de_ferro"
S19_REWARD_SOURCE = "s19.sal_nas_feridas"
ROTAS_CODEX = "codex.route.rotas_das_varzeas"
ROTAS_FRAGMENT = "codex.fragment.varzeas.p19.rotas_initial"


@dataclass(frozen=True, slots=True)
class VarzeasMissionView:
    character_id: UUID
    quest_id: str
    title: str
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False


class VarzeasMissionService:
    """P19 starts on the authorized Nareth exit; S19 is accepted from Sera."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.road = RoadService(sessions, server_id)

    async def on_location(self, actor: int) -> None:
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None or world.region != REGION:
                return
            if world.location == VARZEAS_DIQUES:
                for member_id in character_ids:
                    member_world = await self._world(session, member_id)
                    if member_world is not None and member_world.region == REGION and member_world.location == VARZEAS_DIQUES:
                        await self._ensure(session, LocationDiscovery, character_id=member_id, location_id=VARZEAS_DIQUES_LOCATION)
                        await self._ensure_codex(session, member_id, "codex.location.diques_rubros")
                await self._start_p19_for_present_roster(session, character_ids)
            elif world.location == VARZEAS_PORTO:
                for member_id in character_ids:
                    member_world = await self._world(session, member_id)
                    if member_world is not None and member_world.region == REGION and member_world.location == VARZEAS_PORTO:
                        await self._ensure(session, LocationDiscovery, character_id=member_id, location_id=VARZEAS_PORTO_LOCATION)
                        await self._ensure_codex(session, member_id, "codex.location.porto_da_salmoura")
                await self._credit_port_arrival(session, character_ids)

    async def _start_p19_for_present_roster(self, session, character_ids) -> None:
        for member_id in character_ids:
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or world.region != REGION
                or world.location != VARZEAS_DIQUES
                or member.level < 31
                or await self._foreground(session, member_id)
                or not await self._quest_completed(session, member_id, "P18")
                or not await self._has_unlock(session, member_id, VARZEAS_REGION_ENTRY_UNLOCK)
            ):
                continue
            quest = await self._quest(session, member_id, P19_ID)
            if quest is None:
                quest = Quest(
                    character_id=member_id,
                    quest_id=P19_ID,
                    title=P19_TITLE,
                    status="active",
                    step=3,
                    content_version=CONTENT_VERSION,
                    state_version=0,
                    progress={"crossed_from_nareth": True, "entered_diques": True},
                )
                session.add(quest)
                await session.flush()
                for objective_id in ("p19.crossed_from_nareth", "p19.entered_diques"):
                    await self._credit(
                        session,
                        member_id,
                        P19_ID,
                        objective_id,
                        f"{objective_id}:{member_id}",
                        {"location": VARZEAS_DIQUES, "source": "authorized_region_entry"},
                    )

    async def _credit_port_arrival(self, session, character_ids) -> None:
        members = await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P19_ID,
            content_version=CONTENT_VERSION,
            step=6,
            region=REGION,
            location=VARZEAS_PORTO,
        )
        for member in members:
            member.quest.step = 7
            member.quest.state_version += 1
            member.quest.progress = {**(member.quest.progress or {}), "reached_porto": True}
            await self._credit(
                session,
                member.character.id,
                P19_ID,
                "p19.reached_porto",
                f"p19.reached_porto:{member.character.id}",
                {"location": VARZEAS_PORTO},
            )

    async def resume(self, actor: int, quest_id: str) -> VarzeasMissionView | None:
        if quest_id not in {P19_ID, S19_ID}:
            return None
        await self.on_location(actor)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, quest_id, lock=False)
            world = await self._world(session, character.id, lock=False)
            return await self._view(session, character, quest, world, quest_id)

    async def resume_active(self, actor: int) -> VarzeasMissionView | None:
        await self.on_location(actor)
        for quest_id in (P19_ID, S19_ID):
            view = await self.resume(actor, quest_id)
            if view is not None and view.status == "active":
                return view
        return None

    async def board(self, actor: int) -> tuple[VarzeasMissionView | None, ...]:
        return tuple([await self.resume(actor, P19_ID), await self.resume(actor, S19_ID)])

    async def start(self, actor: int, quest_id: str) -> VarzeasMissionView | None:
        if quest_id != S19_ID:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None:
                return None
            if (
                world.region != REGION
                or world.location != VARZEAS_PORTO
                or character.level < 32
                or await self._foreground(session, character.id)
                or not await self._quest_completed(session, character.id, P19_ID)
            ):
                return await self._view(
                    session,
                    character,
                    await self._quest(session, character.id, S19_ID),
                    world,
                    S19_ID,
                )
            for member_id in character_ids:
                member = await session.scalar(
                    select(Character).where(Character.id == member_id).with_for_update()
                )
                member_world = await self._world(session, member_id)
                if (
                    member is None
                    or member_world is None
                    or member_world.region != REGION
                    or member_world.location != VARZEAS_PORTO
                    or member.level < 32
                    or await self._foreground(session, member_id)
                    or not await self._quest_completed(session, member_id, P19_ID)
                    or await self._quest(session, member_id, S19_ID) is not None
                ):
                    continue
                quest = Quest(
                    character_id=member_id,
                    quest_id=S19_ID,
                    title=S19_TITLE,
                    status="active",
                    step=1,
                    content_version=CONTENT_VERSION,
                    state_version=0,
                    progress={"corrosion_points": []},
                )
                session.add(quest)
                await session.flush()
                await self._credit(
                    session,
                    member_id,
                    S19_ID,
                    "s19.received_from_sera_morn",
                    f"s19.started:{member_id}",
                    {"giver": "Sera Morn", "location": VARZEAS_PORTO},
                )
            return await self._view(
                session,
                character,
                await self._quest(session, character.id, S19_ID),
                world,
                S19_ID,
            )

    async def advance(self, actor: int, quest_id: str, version: int, action: str):
        if quest_id not in {P19_ID, S19_ID}:
            return None
        await self.on_location(actor)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            quest = await self._quest(session, actor_row.id, quest_id)
            if character is None or world is None or quest is None:
                return None
            if (
                quest.status != "active"
                or quest.content_version != CONTENT_VERSION
                or quest.state_version != version
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, quest_id)
            members = await present_campaign_members(
                session,
                character_ids=character_ids,
                quest_id=quest_id,
                content_version=CONTENT_VERSION,
                step=quest.step,
                region=REGION,
                location=world.location,
            )
            if quest_id == P19_ID:
                await self._advance_p19(session, members, world.location, action)
            else:
                await self._advance_s19(session, members, world.location, action)
            return await self._view(
                session,
                character,
                await self._quest(session, character.id, quest_id),
                world,
                quest_id,
            )

    async def _advance_p19(self, session, members, location: str, action: str) -> None:
        expected = {
            (3, VARZEAS_DIQUES, "inspect_water"): 4,
            (4, VARZEAS_DIQUES, "register_dique_brazier"): 5,
            (5, VARZEAS_DIQUES, "follow_safe_route"): 6,
            (7, VARZEAS_PORTO, "register_porto_brazier"): 8,
            (8, VARZEAS_PORTO, "speak_sera"): 9,
        }
        if not members:
            return
        old_step = members[0].quest.step
        if action == "record_codex" and (old_step, location) == (9, VARZEAS_PORTO):
            for member in members:
                member.quest.step = 10
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {**(member.quest.progress or {}), "completed": True}
                await self._ensure_codex(session, member.character.id, ROTAS_CODEX)
                await self._ensure(session, CodexFragment, character_id=member.character.id, entry_id=ROTAS_CODEX, fragment_id=ROTAS_FRAGMENT)
                await self._credit(session, member.character.id, P19_ID, "p19.recorded_routes", f"p19.codex:{member.character.id}", {"codex_entry": ROTAS_CODEX})
                await self._reward(session, member.character, P19_ID, P19_REWARD_SOURCE, 34300, 570, (("material.varzeas.ferro_de_salmoura", 1), ("material.varzeas.couro_de_varzea", 1)))
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_DIQUES_HUNT_UNLOCK)
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_DIQUES_EXPLORE_UNLOCK)
                await reconcile_varzeas_feats(session, member.character)
                await consolidate_character_level(session, member.character)
            return
        next_step = expected.get((old_step, location, action))
        if next_step is None:
            return
        for member in members:
            member.quest.step = next_step
            member.quest.state_version += 1
            objective = {
                "inspect_water": "p19.examined_water_and_gate",
                "register_dique_brazier": "p19.registered_dique_brazier",
                "follow_safe_route": "p19.followed_safe_route",
                "register_porto_brazier": "p19.registered_porto_brazier",
                "speak_sera": "p19.spoke_with_sera_morn",
            }[action]
            member.quest.progress = {**(member.quest.progress or {}), objective: True}
            if action == "register_dique_brazier":
                await self._ensure(session, Brazier, character_id=member.character.id, brazier_id=VARZEAS_DIQUES_BRAZIER)
            elif action == "follow_safe_route":
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_DIQUES_PORTO_ROUTE)
            elif action == "register_porto_brazier":
                await self._ensure(session, Brazier, character_id=member.character.id, brazier_id=VARZEAS_PORTO_BRAZIER)
            elif action == "speak_sera":
                await self._ensure_codex(session, member.character.id, "codex.figure.sera_morn")
                await self._ensure(session, CodexFragment, character_id=member.character.id, entry_id="codex.figure.sera_morn", fragment_id="codex.fragment.varzeas.figure.sera_morn")
            await self._credit(session, member.character.id, P19_ID, objective, f"{objective}:{member.character.id}", {"location": location})

    async def _advance_s19(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        if quest.step == 1 and location == VARZEAS_DIQUES and action in {"inspect_a", "inspect_b", "inspect_c"}:
            objective = f"s19.corrosion_point_{action[-1]}"
            for member in members:
                member_points = set((member.quest.progress or {}).get("corrosion_points", []))
                if action[-1] in member_points:
                    continue
                member_points.add(action[-1])
                member.quest.progress = {**(member.quest.progress or {}), "corrosion_points": sorted(member_points)}
                member.quest.state_version += 1
                await self._credit(session, member.character.id, S19_ID, objective, f"{objective}:{member.character.id}", {"location": VARZEAS_DIQUES})
                if len(member_points) == 3:
                    member.quest.step = 2
            return
        if quest.step == 2 and location == VARZEAS_DIQUES and action == "differentiate_brine_damage":
            for member in members:
                member.quest.step = 3
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "distinguished_salt_from_recent_damage": True}
                await self._credit(session, member.character.id, S19_ID, "s19.differentiated_brine", f"s19.differentiated:{member.character.id}", {"points": 3})
            return
        if quest.step == 3 and location == VARZEAS_DIQUES and action == "repair_and_record":
            for member in members:
                member.quest.step = 4
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {**(member.quest.progress or {}), "repair_recorded": True, "completed": True}
                await self._credit(session, member.character.id, S19_ID, "s19.repaired_and_recorded", f"s19.completed:{member.character.id}", {"location": VARZEAS_DIQUES})
                await self._reward(session, member.character, S19_ID, S19_REWARD_SOURCE, 14400, 290, ())
                await consolidate_character_level(session, member.character)

    async def region_access(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return bool(character and await self._has_unlock(session, character.id, VARZEAS_REGION_ENTRY_UNLOCK))

    async def known_locations(self, actor: int) -> set[str]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return set()
            ids = set(
                (
                    await session.scalars(
                        select(LocationDiscovery.location_id).where(
                            LocationDiscovery.character_id == character.id,
                            LocationDiscovery.location_id.in_(
                                (VARZEAS_DIQUES_LOCATION, VARZEAS_PORTO_LOCATION)
                            ),
                        )
                    )
                ).all()
            )
            return {label for key, label in ((VARZEAS_DIQUES_LOCATION, VARZEAS_DIQUES), (VARZEAS_PORTO_LOCATION, VARZEAS_PORTO)) if key in ids}

    async def _view(self, session, character, quest, world, quest_id) -> VarzeasMissionView:
        location = world.location if world is not None else ""
        if quest is None:
            available = False
            if quest_id == S19_ID:
                available = bool(
                    character.level >= 32
                    and location == VARZEAS_PORTO
                    and world is not None
                    and world.region == REGION
                    and await self._quest_completed(session, character.id, P19_ID)
                )
            return VarzeasMissionView(character.id, quest_id, P19_TITLE if quest_id == P19_ID else S19_TITLE, "offer" if available else "unavailable", None, None, 0, {}, location, character.level, available)
        if quest.status == "completed":
            kind = "completed"
        elif quest_id == P19_ID:
            kind = {3: "inspect_water", 4: "register_dique_brazier", 5: "follow_safe_route", 6: "arrive_porto", 7: "register_porto_brazier", 8: "speak_sera", 9: "record_codex"}.get(quest.step, "active")
        elif quest.step == 1:
            kind = "corrosion_points"
        elif quest.step == 2:
            kind = "differentiate_brine_damage"
        else:
            kind = "repair_and_record"
        return VarzeasMissionView(character.id, quest_id, quest.title, kind, quest.status, quest.step, quest.state_version, quest.progress or {}, location, character.level)

    async def _reward(self, session, character, quest_id, source_id, xp, crowns, materials) -> None:
        existing = await session.scalar(select(RewardEvent).where(RewardEvent.character_id == character.id, RewardEvent.source_id == source_id).with_for_update())
        if existing is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        character.xp += xp
        character.crowns += crowns
        session.add_all((RewardComponent(reward_event_id=event.id, kind="xp", quantity=xp), RewardComponent(reward_event_id=event.id, kind="crowns", quantity=crowns)))
        for material_id, quantity in materials:
            session.add(RewardComponent(reward_event_id=event.id, kind="material", item_id=material_id, quantity=quantity, payload={"material_id": material_id, "bound": True}))
            await self.road.deliver_material(session, character, material_id, quantity, f"{source_id}:material:{material_id}", bound=True)

    async def _credit(self, session, character_id, quest_id, objective_id, source_key, evidence) -> None:
        await record_campaign_objective_credit(session, character_id=character_id, quest_id=quest_id, objective_id=objective_id, source_key=source_key, evidence=evidence)

    async def _ensure_codex(self, session, character_id, entry_id) -> None:
        await self._ensure(session, CodexEntry, character_id=character_id, entry_id=entry_id)

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        return True

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(Character.telegram_id == actor, Character.server_id == self.server_id))

    async def _quest(self, session, character_id, quest_id, *, lock=True):
        statement = select(Quest).where(Quest.character_id == character_id, Quest.quest_id == quest_id)
        return await session.scalar(statement.with_for_update() if lock else statement)

    async def _world(self, session, character_id, *, lock=True):
        statement = select(WorldState).where(WorldState.character_id == character_id)
        return await session.scalar(statement.with_for_update() if lock else statement)

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity.id).where(GameActivity.character_id == character_id, GameActivity.status == "active"))

    async def _quest_completed(self, session, character_id, quest_id):
        return bool(await session.scalar(select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == quest_id, Quest.status == "completed")))

    async def _has_unlock(self, session, character_id, unlock_id):
        return bool(await session.scalar(select(Unlock.id).where(Unlock.character_id == character_id, Unlock.unlock_id == unlock_id)))
