"""Persistent P13/S13 progression for the opening of Planícies de Nareth."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.campaign_objectives import (
    campaign_roster_ids,
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import RoadService
from asterion.infrastructure.db.models import (
    Achievement,
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

REGION = "Planícies de Nareth"
P13_ID = "P13"
S13_ID = "S13"
CONTENT_VERSION = "nareth-1.0.0"
P13_TITLE = "Linhas no Horizonte"
S13_TITLE = "Pedras que Apontam"
P13_REWARD_SOURCE = "p13.linhas_no_horizonte"
S13_REWARD_SOURCE = "s13.pedras_que_apontam"
CAMPINAS = "Campinas do Meridiano"
POSTO = "Posto de Nareth"
CAMPINAS_LOCATION_ID = "nareth.location.campinas_do_meridiano"
POSTO_LOCATION_ID = "nareth.location.posto_de_nareth"
REGION_UNLOCK = "region.nareth.available"
EXPLORE_UNLOCK = "explore.nareth.campinas_do_meridiano"
HUNT_UNLOCK = "hunt.manual.nareth.campinas_do_meridiano"
CAMPINAS_POSTO_ROUTE = "route.nareth.campinas_posto"
HORIZON_BRAZIER = "nareth.brazier.horizonte"
POSTO_BRAZIER = "nareth.brazier.posto"
ROTAS_CODEX = "codex.route.rotas_de_nareth"
CODEX_INITIAL_FRAGMENT = "codex.fragment.nareth.p13.routes_initial"
CODEX_S13_FRAGMENT = "codex.fragment.nareth.s13.references"

TITLES = {P13_ID: P13_TITLE, S13_ID: S13_TITLE}


@dataclass(frozen=True, slots=True)
class NarethMissionView:
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


class NarethMissionService:
    """Reuses the persistent Quest and shared-objective records for Nareth."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.road = RoadService(sessions, server_id)

    async def on_location(self, actor: int) -> None:
        """Discover a reached Nareth Local and materialize automatic P13 on entry."""
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await session.scalar(
                select(WorldState)
                .where(WorldState.character_id == actor_row.id)
                .with_for_update()
            )
            if character is None or world is None or world.region != REGION:
                return
            if character.level < 21 or not await self._p12_complete(session, character.id):
                return
            if world.location == CAMPINAS:
                await self._ensure_unlock(session, character.id, REGION_UNLOCK)
                await self._ensure_location(session, character.id, CAMPINAS_LOCATION_ID)
                for member_id in character_ids:
                    member = await session.scalar(
                        select(Character).where(Character.id == member_id).with_for_update()
                    )
                    member_world = await session.scalar(
                        select(WorldState)
                        .where(WorldState.character_id == member_id)
                        .with_for_update()
                    )
                    if (
                        member is None
                        or member_world is None
                        or member_world.region != REGION
                        or member_world.location != CAMPINAS
                        or member.level < 21
                        or not await self._p12_complete(session, member_id)
                        or await self._foreground(session, member_id)
                    ):
                        continue
                    await self._ensure_unlock(session, member_id, REGION_UNLOCK)
                    await self._ensure_unlock(session, member_id, EXPLORE_UNLOCK)
                    await self._ensure_location(session, member_id, CAMPINAS_LOCATION_ID)
                    quest = await session.scalar(
                        select(Quest)
                        .where(Quest.character_id == member_id, Quest.quest_id == P13_ID)
                        .with_for_update()
                    )
                    if quest is None:
                        quest = Quest(
                            character_id=member_id,
                            quest_id=P13_ID,
                            title=P13_TITLE,
                            status="active",
                            step=3,
                            content_version=CONTENT_VERSION,
                            state_version=0,
                            progress={"line_examined": False, "markers_compared": False},
                        )
                        session.add(quest)
                        await session.flush()
                        for objective_id in ("p13.crossed_from_vales", "p13.entered_campinas"):
                            await record_campaign_objective_credit(
                                session,
                                character_id=member_id,
                                quest_id=P13_ID,
                                objective_id=objective_id,
                                source_key=f"{objective_id}:{member_id}",
                                evidence={"location": CAMPINAS, "automatic": True},
                            )
            elif world.location == POSTO:
                await self._ensure_location(session, character.id, POSTO_LOCATION_ID)
                members = await self._present(
                    session, character.id, P13_ID, step=7, location=POSTO
                )
                for member in members:
                    await self._ensure_location(session, member.character.id, POSTO_LOCATION_ID)
                    member.quest.step = 8
                    member.quest.state_version += 1
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "reached_posto": True,
                    }
                    await self._credit(
                        session,
                        member.character.id,
                        P13_ID,
                        "p13.reached_posto",
                        f"p13.reached_posto:{member.character.id}",
                        {"location": POSTO, "shared": len(members) > 1},
                    )

    async def resume(self, actor: int, quest_id: str) -> NarethMissionView | None:
        if quest_id not in TITLES:
            return None
        await self.on_location(actor)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == quest_id,
                )
            )
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            return await self._view(session, character, quest, world, quest_id)

    async def resume_active(self, actor: int) -> NarethMissionView | None:
        for quest_id in (P13_ID, S13_ID):
            view = await self.resume(actor, quest_id)
            if view is not None and view.status == "active":
                return view
        return None

    async def board(self, actor: int) -> tuple[NarethMissionView | None, ...]:
        return tuple([await self.resume(actor, P13_ID), await self.resume(actor, S13_ID)])

    async def region_access(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return bool(
                character
                and await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == REGION_UNLOCK,
                    )
                )
            )

    async def known_locations(self, actor: int) -> set[str]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return set()
            location_ids = set(
                (
                    await session.scalars(
                        select(LocationDiscovery.location_id).where(
                            LocationDiscovery.character_id == character.id,
                            LocationDiscovery.location_id.in_(
                                (CAMPINAS_LOCATION_ID, POSTO_LOCATION_ID)
                            ),
                        )
                    )
                ).all()
            )
            return {
                label
                for location_id, label in (
                    (CAMPINAS_LOCATION_ID, CAMPINAS),
                    (POSTO_LOCATION_ID, POSTO),
                )
                if location_id in location_ids
            }

    async def start(self, actor: int, quest_id: str) -> NarethMissionView | None:
        if quest_id != S13_ID:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            character, _character_ids = await self._locked_state(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if world is None:
                return None
            existing = await session.scalar(
                select(Quest)
                .where(Quest.character_id == character.id, Quest.quest_id == S13_ID)
                .with_for_update()
            )
            if existing is None:
                eligible = await self._s13_eligible(session, character, world)
                if not eligible:
                    return await self._view(session, character, None, world, S13_ID)
                members = await self._eligible_group_at(session, character.id, S13_ID)
                for member, member_world in members:
                    quest = Quest(
                        character_id=member.id,
                        quest_id=S13_ID,
                        title=S13_TITLE,
                        status="active",
                        step=2,
                        content_version=CONTENT_VERSION,
                        state_version=0,
                        progress={"markers": []},
                    )
                    session.add(quest)
                    await session.flush()
                    await self._credit(
                        session,
                        member.id,
                        S13_ID,
                        "s13.received_references",
                        f"s13.received_references:{member.id}",
                        {"giver": "Nera Voss", "location": member_world.location},
                    )
                existing = await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == character.id, Quest.quest_id == S13_ID)
                    .with_for_update()
                )
            return await self._view(session, character, existing, world, S13_ID)

    async def examine(self, actor: int, quest_id: str, version: int, point: str):
        if quest_id != S13_ID or point not in {"a", "b", "c"}:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            character, _ids = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, S13_ID)
            world = await self._world(session, character.id)
            if quest is None or world is None:
                return await self._view(session, character, quest, world, S13_ID)
            if not self._valid(
                quest, version, step=2 + len((quest.progress or {}).get("markers", []))
            ):
                return await self._view(session, character, quest, world, S13_ID)
            expected_location = CAMPINAS
            if world.region != REGION or world.location != expected_location:
                return await self._view(session, character, quest, world, S13_ID)
            members = await self._present(session, character.id, S13_ID, quest.step, CAMPINAS)
            for member in members:
                progress = dict(member.quest.progress or {})
                markers = list(progress.get("markers", []))
                next_point = ("a", "b", "c")[len(markers)] if len(markers) < 3 else None
                if point != next_point:
                    continue
                markers.append(point)
                member.quest.progress = {**progress, "markers": markers}
                member.quest.step = 2 + len(markers)
                member.quest.state_version += 1
                await self._credit(
                    session,
                    member.character.id,
                    S13_ID,
                    f"s13.marker.{point}",
                    f"s13.marker.{point}:{member.character.id}",
                    {"location": CAMPINAS, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world, S13_ID)

    async def advance(self, actor: int, quest_id: str, version: int, action: str):
        if quest_id not in TITLES:
            return None
        async with self.sessions.begin() as session:
            character, _ids = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if quest is None or world is None:
                return await self._view(session, character, quest, world, quest_id)

            p13_steps = {
                "line": (3, CAMPINAS, 4, "p13.old_stone_line"),
                "compare": (4, CAMPINAS, 5, "p13.compare_markers"),
                "horizon_brazier": (5, CAMPINAS, 6, "p13.register_horizon_brazier"),
                "follow_route": (6, CAMPINAS, 7, "p13.follow_verified_route"),
                "posto_brazier": (8, POSTO, 9, "p13.register_posto_brazier"),
                "speak_nera": (9, POSTO, 10, "p13.speak_nera"),
                "record_codex": (10, POSTO, 10, "p13.record_rotas_codex"),
            }
            s13_steps = {
                "compare": (5, CAMPINAS, 6, "s13.compare_references"),
                "report": (6, POSTO, 6, "s13.report_to_nera"),
            }
            config = (p13_steps if quest_id == P13_ID else s13_steps).get(action)
            if config is None:
                return await self._view(session, character, quest, world, quest_id)
            expected_step, expected_location, next_step, objective_id = config
            if not self._valid(quest, version, step=expected_step):
                return await self._view(session, character, quest, world, quest_id)
            if world.region != REGION or world.location != expected_location:
                return await self._view(session, character, quest, world, quest_id)
            members = await self._present(
                session, character.id, quest_id, expected_step, expected_location
            )
            for member in members:
                if quest_id == P13_ID and action == "horizon_brazier":
                    await self._ensure(
                        session,
                        Brazier,
                        member.character.id,
                        "brazier_id",
                        HORIZON_BRAZIER,
                    )
                elif quest_id == P13_ID and action == "posto_brazier":
                    await self._ensure(
                        session,
                        Brazier,
                        member.character.id,
                        "brazier_id",
                        POSTO_BRAZIER,
                    )
                elif quest_id == P13_ID and action == "follow_route":
                    await self._ensure_unlock(session, member.character.id, CAMPINAS_POSTO_ROUTE)
                elif quest_id == P13_ID and action == "speak_nera":
                    await self._ensure_codex(session, member.character.id, "codex.figure.nera_voss")
                elif quest_id == P13_ID and action == "record_codex":
                    await self._record_p13_codex(session, member.character.id)
                if quest_id == P13_ID and action == "line":
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "line_examined": True,
                    }
                elif quest_id == P13_ID and action == "compare":
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "markers_compared": True,
                    }
                member.quest.step = next_step
                member.quest.state_version += 1
                await self._credit(
                    session,
                    member.character.id,
                    quest_id,
                    objective_id,
                    f"{objective_id}:{member.character.id}",
                    {"location": expected_location, "shared": len(members) > 1},
                )
                if quest_id == P13_ID and action == "record_codex":
                    await self._complete_p13(session, member.character, member.quest)
                elif quest_id == S13_ID and action == "report":
                    await self._complete_s13(session, member.character, member.quest)
            return await self._view(session, character, quest, world, quest_id)

    async def _complete_p13(self, session, character, quest):
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await self._ensure_unlock(session, character.id, HUNT_UNLOCK)
        await self._reward(
            session,
            character,
            quest,
            P13_REWARD_SOURCE,
            19350,
            420,
            (
                ("material.nareth.bronze_de_marco", 1),
                ("material.nareth.couro_de_horizonte", 1),
            ),
        )
        achievement = await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == "feat.nareth.primeiro_meridiano",
            )
        )
        if achievement is None:
            session.add(
                Achievement(
                    character_id=character.id,
                    achievement_id="feat.nareth.primeiro_meridiano",
                )
            )
        await consolidate_character_level(session, character)

    async def _complete_s13(self, session, character, quest):
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await self._ensure_codex_fragment(session, character.id, ROTAS_CODEX, CODEX_S13_FRAGMENT)
        await self._reward(session, character, quest, S13_REWARD_SOURCE, 8260, 220, ())
        await consolidate_character_level(session, character)

    async def _reward(self, session, character, quest, source_id, xp, crowns, materials):
        existing = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        character.xp += xp
        character.crowns += crowns
        session.add_all(
            [
                RewardComponent(reward_event_id=event.id, kind="xp", quantity=xp),
                RewardComponent(reward_event_id=event.id, kind="crowns", quantity=crowns),
            ]
        )
        for material_id, quantity in materials:
            session.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind="material",
                    item_id=material_id,
                    quantity=quantity,
                    payload={"material_id": material_id, "bound": True},
                )
            )
            await self.road.deliver_material(
                session,
                character,
                material_id,
                quantity,
                f"{source_id}:material:{material_id}",
                bound=True,
            )

    async def _record_p13_codex(self, session, character_id):
        for entry in (
            "codex.location.campinas_do_meridiano",
            "codex.location.posto_de_nareth",
            "codex.figure.nera_voss",
            ROTAS_CODEX,
        ):
            await self._ensure_codex(session, character_id, entry)
        await self._ensure_codex_fragment(
            session, character_id, ROTAS_CODEX, CODEX_INITIAL_FRAGMENT
        )

    async def _view(self, session, character, quest, world, requested_quest_id):
        quest_id = quest.quest_id if quest is not None else requested_quest_id
        location = world.location if world is not None else ""
        if quest is None:
            available = (
                await self._p13_eligible(session, character, world)
                if quest_id == P13_ID
                else await self._s13_eligible(session, character, world)
            )
            return NarethMissionView(
                character.id,
                quest_id,
                TITLES[quest_id],
                "offer" if available else "unavailable",
                None,
                None,
                0,
                {},
                location,
                character.level,
                available,
            )
        if quest.status == "completed":
            kind = "completed"
        elif quest_id == P13_ID:
            kind = {
                3: "line",
                4: "compare",
                5: "horizon_brazier",
                6: "follow_route",
                7: "arrive_posto",
                8: "posto_brazier",
                9: "speak_nera",
                10: "record_codex",
            }.get(quest.step, "active")
        else:
            if quest.step == 1:
                kind = "receive"
            elif quest.step in {2, 3, 4}:
                kind = "markers"
            elif quest.step == 5:
                kind = "compare"
            else:
                kind = "report"
        return NarethMissionView(
            character.id,
            quest_id,
            TITLES[quest_id],
            kind,
            quest.status,
            quest.step,
            quest.state_version,
            dict(quest.progress or {}),
            location,
            character.level,
        )

    async def _p13_eligible(self, session, character, world):
        return bool(
            character
            and world
            and character.level >= 21
            and world.region == REGION
            and world.location == CAMPINAS
            and await self._p12_complete(session, character.id)
        )

    async def _s13_eligible(self, session, character, world):
        return bool(
            character
            and world
            and character.level >= 22
            and world.region == REGION
            and world.location == POSTO
            and await self._p13_complete(session, character.id)
            and await self._foreground(session, character.id) is None
        )

    async def _eligible_group_at(self, session, character_id, quest_id):
        members = []
        for member_id in await campaign_roster_ids(session, character_id):
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or not await self._s13_eligible(session, member, world)
            ):
                continue
            existing = await self._quest(session, member_id, quest_id)
            if existing is None:
                members.append((member, world))
        return members

    async def _present(self, session, character_id, quest_id, step, location):
        return await present_campaign_members(
            session,
            character_ids=await campaign_roster_ids(session, character_id),
            quest_id=quest_id,
            content_version=CONTENT_VERSION,
            step=step,
            region=REGION,
            location=location,
        )

    async def _locked_state(self, session, actor):
        actor_row = await self._character(session, actor)
        if actor_row is None:
            return None, ()
        _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
        character = await session.scalar(
            select(Character).where(Character.id == actor_row.id).with_for_update()
        )
        return character, character_ids

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _quest(self, session, character_id, quest_id):
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == quest_id)
            .with_for_update()
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id).with_for_update()
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        )

    async def _p12_complete(self, session, character_id):
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P12",
                    Quest.status == "completed",
                )
            )
        )

    async def _p13_complete(self, session, character_id):
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P13_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _ensure_location(self, session, character_id, location_id):
        await self._ensure(session, LocationDiscovery, character_id, "location_id", location_id)

    async def _ensure_unlock(self, session, character_id, unlock_id):
        await self._ensure(session, Unlock, character_id, "unlock_id", unlock_id)

    async def _ensure(self, session, model, character_id, key, value):
        column = getattr(model, key)
        found = await session.scalar(
            select(model.id).where(model.character_id == character_id, column == value)
        )
        if found is None:
            session.add(model(character_id=character_id, **{key: value}))

    async def _ensure_codex(self, session, character_id, entry_id):
        await self._ensure(session, CodexEntry, character_id, "entry_id", entry_id)

    async def _ensure_codex_fragment(self, session, character_id, entry_id, fragment_id):
        found = await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == fragment_id,
            )
        )
        if found is None:
            await self._ensure_codex(session, character_id, entry_id)
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
            )

    async def _credit(self, session, character_id, quest_id, objective_id, source_key, evidence):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=quest_id,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    @staticmethod
    def _valid(quest, version, *, step):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == CONTENT_VERSION
            and quest.state_version == version
            and quest.step == step
        )
