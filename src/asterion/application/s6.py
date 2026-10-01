"""S6 campaign content composed from persistent Quests and shared combat."""
# ruff: noqa: E501

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.bestiary import BestiaryRecorder
from asterion.application.p5 import P5_ID
from asterion.application.progression import consolidate_character_level
from asterion.application.road import REFUGE, REGION, RUINS, RoadService
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    derive_consumable_selection,
    materialize,
    normalize_character_hp,
)
from asterion.domain.road import FACELESS_CUSTODIAN, RUINS_LOCATION, enemy_xp
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Character,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    Encounter,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

S6_ID = "S6"
S6_TITLE = "Onde os Nomes Terminaram"
S6_VERSION = "tdo-1.0.11"
S6_CONTENT_ID = "s6_scripted_custodio_sem_rosto"
S6_REWARD_SOURCE = "s6.onde_os_nomes_terminaram"
S6_MARKS = ("s6.pilgrim_mark.1", "s6.pilgrim_mark.2", "s6.pilgrim_mark.3")
S6_CODEX_PEREGRINOS = "codex.mystery.peregrinos_do_ocaso"
S6_CODEX_FRAGMENT = "codex.fragment.peregrinos.ruinas.trilha_termina"
S6_RUINS_CODEX = "codex.location.ruinas_do_vigia"
S6_RUINS_FRAGMENT = "codex.fragment.ruinas.peregrinos_passaram"
S6_MATERIALS = (
    ("material.tdo.ferro_de_fuligem", 2),
    ("material.tdo.couro_escoriado", 2),
    ("material.tdo.erva_cinzenta", 2),
    ("material.tdo.residuo_ocaso", 2),
)


@dataclass(frozen=True)
class S6View:
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
    tracked: bool = False
    context: str = "s6"
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


class S6Service:
    """Owns S6 Quest progression while combat, rewards and recovery stay shared."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def offer(self, actor: int) -> S6View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            eligible = await self._eligible(session, character)
            available = bool(
                eligible
                and self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and (quest is None or quest.status == "abandoned")
            )
            return await self._view(
                session,
                character,
                quest,
                world,
                "offer" if available else "unavailable",
                available=available,
            )

    async def oren(self, actor: int) -> S6View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            quest = await self._quest(session, character.id)
            eligible = await self._eligible(session, character)
            available = bool(
                eligible
                and self._at(world, REFUGE)
                and (quest is None or quest.status == "abandoned")
                and not await self._foreground(session, character.id)
            )
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "oren", available=available)

    async def summary(self, actor: int) -> S6View | None:
        return await self.resume(actor)

    async def resume(self, actor: int) -> S6View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view(
                session,
                character,
                await self._quest(session, character.id),
                await self._world(session, character.id),
            )

    async def accept(self, actor: int, version: int, *, reaccept: bool = False) -> S6View | None:
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
                quest.content_version = S6_VERSION
                quest.progress = {}
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world)
                quest = Quest(
                    character_id=character.id,
                    quest_id=S6_ID,
                    title=S6_TITLE,
                    status="active",
                    step=1,
                    content_version=S6_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            character.tracked_secondary_quest_id = S6_ID
            return await self._view(session, character, quest, world)

    async def abandon(self, actor: int, version: int) -> S6View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            quest.status = "abandoned"
            quest.progress = {}
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S6_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world)

    async def toggle_tracking(self, actor: int, version: int) -> S6View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or quest.status != "active":
                return await self._view(session, character, quest, world)
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S6_ID else S6_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def action(self, actor: int, version: int, operation: str, item: str | None = None):
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            if operation == "review" and quest.step == 1 and self._at(world, REFUGE):
                progress["s2_fragments_reviewed"] = True
                quest.step = 2
            elif operation == "mark" and quest.step == 2 and self._at(world, RUINS):
                if item not in S6_MARKS:
                    return await self._view(session, character, quest, world)
                found = set(progress.get("pilgrim_marks", ()))
                if item in found:
                    return await self._view(session, character, quest, world)
                found.add(item)
                progress["pilgrim_marks"] = [key for key in S6_MARKS if key in found]
                if len(found) == len(S6_MARKS):
                    quest.step = 3
            elif operation == "shelter" and quest.step == 3 and self._at(world, RUINS):
                if progress.get("abandoned_shelter_examined"):
                    return await self._view(session, character, quest, world)
                progress["abandoned_shelter_examined"] = True
                quest.step = 4
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    quest.step = 3
                    progress.pop("abandoned_shelter_examined", None)
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif operation == "retry" and quest.step == 4 and progress.get("awaiting_retry") and self._at(world, RUINS):
                progress["awaiting_retry"] = False
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    progress["awaiting_retry"] = True
                    quest.progress = progress
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif operation == "last_record" and quest.step == 5 and self._at(world, RUINS):
                progress["last_route_record_found"] = True
                quest.step = 6
            elif operation == "report" and quest.step == 6 and self._at(world, REFUGE):
                if not progress.get("last_route_record_found"):
                    return await self._view(session, character, quest, world)
                await self._complete(session, character, quest)
                return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def action_combat(self, actor: int, activity_id: UUID, version: int, action: str | None = None, *, consumable_id=None, target_id=None, effect_id=None):
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S6_CONTENT_ID,
                ).with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                not self._valid(quest, quest.state_version, step=4)
                or activity.status != "active"
                or activity.state_version != version
                or foreground is None
                or foreground.id != activity.id
                or (action is None) == (consumable_id is None)
            ):
                return current
            updated = await apply_action(
                session, character, activity, action=action,
                consumable_id=consumable_id, target_id=target_id,
                effect_id=effect_id, category=FACELESS_CUSTODIAN.category,
            )
            if updated is None or updated.version == version:
                return current
            existing = await session.scalar(
                select(BestiaryEntry.id).where(
                    BestiaryEntry.character_id == character.id,
                    BestiaryEntry.creature_id == FACELESS_CUSTODIAN.creature_id,
                )
            )
            if existing is None:
                await self.bestiary.record(
                    session, character.id, FACELESS_CUSTODIAN.creature_id,
                    observation_category="uncommon",
                )
            await self.bestiary.record_combat_events(
                session, character.id, FACELESS_CUSTODIAN.creature_id, None, updated
            )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session, character.id, FACELESS_CUSTODIAN.creature_id,
                    victory=True, observation_category="uncommon",
                )
                progress.update(combat_result="victory", awaiting_retry=False)
                quest.step = 5
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session, character.id, FACELESS_CUSTODIAN.creature_id,
                    observation_category="uncommon",
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, RUINS_LOCATION, world
                )
                progress.update(
                    combat_result="defeat", awaiting_retry=True,
                    defeat_activity_id=str(activity.id),
                    recovery_brazier=brazier, recovery_location=location,
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def consumable_selection(self, actor: int, activity_id: UUID, version: int, **kwargs):
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S6_CONTENT_ID,
                ).with_for_update()
            )
            if activity is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                quest.status != "active" or quest.step != 4
                or activity.status != "active" or foreground is None
                or foreground.id != activity.id
            ):
                return current
            if activity.state_version != version:
                from dataclasses import replace
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(current, **kwargs)

    async def _materialize(self, session, character, quest):
        if await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session, character, S6_CONTENT_ID, FACELESS_CUSTODIAN, 10,
            flavor="Marcas de passagem terminam diante de uma figura imóvel.",
            opening_log="🛡️ Custódio Sem Rosto · Nv.10 interrompe a trilha dos Peregrinos.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{S6_REWARD_SOURCE}:enemy-xp:{activity.id}"
        event = await session.scalar(select(RewardEvent).where(
            RewardEvent.character_id == character.id, RewardEvent.source_id == source
        ).with_for_update())
        if event is not None:
            return
        amount = enemy_xp(10, "uncommon", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        session.add(RewardComponent(
            reward_event_id=event.id, kind="enemy_xp",
            item_id=FACELESS_CUSTODIAN.creature_id, quantity=amount,
            payload={"enemy_level": 10, "category": "uncommon"},
        ))
        character.xp += amount

    async def _complete(self, session, character, quest):
        event = await session.scalar(select(RewardEvent).where(
            RewardEvent.character_id == character.id,
            RewardEvent.source_id == S6_REWARD_SOURCE,
        ).with_for_update())
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S6_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 7900
            character.crowns += 310
            session.add_all([
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=7900),
                RewardComponent(reward_event_id=event.id, kind="crowns", item_id=None, quantity=310),
                *[
                    RewardComponent(
                        reward_event_id=event.id, kind="material", item_id=material_id,
                        quantity=quantity, payload={"material_id": material_id, "bound": True},
                    )
                    for material_id, quantity in S6_MATERIALS
                ],
            ])
            for material_id, quantity in S6_MATERIALS:
                await self.road.deliver_material(
                    session, character, material_id, quantity,
                    f"{S6_REWARD_SOURCE}:material:{material_id}", bound=True,
                )
        await self._ensure_codex_fragment(
            session, character.id, S6_CODEX_PEREGRINOS, S6_CODEX_FRAGMENT
        )
        await self._ensure_codex_fragment(
            session, character.id, S6_RUINS_CODEX, S6_RUINS_FRAGMENT
        )
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True, "last_route_record_found": True}
        quest.state_version += 1
        if character.tracked_secondary_quest_id == S6_ID:
            character.tracked_secondary_quest_id = None
        await consolidate_character_level(session, character)

    async def _view(self, session, character, quest, world, requested_kind=None, *, available=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = combat = encounter = record = None
        stored_id = None
        try:
            stored_id = UUID(progress["combat_activity_id"]) if progress.get("combat_activity_id") else None
        except (TypeError, ValueError):
            pass
        if stored_id is not None:
            activity = await session.scalar(select(GameActivity).where(
                GameActivity.id == stored_id, GameActivity.character_id == character.id,
                GameActivity.content_id == S6_CONTENT_ID,
            ))
            if activity is not None:
                pair = (await session.execute(select(Encounter, CombatRecord)
                    .join(CombatRecord)
                    .where(Encounter.game_activity_id == activity.id))).one_or_none()
                if pair:
                    encounter, record = pair
                    if activity.status == "active":
                        combat = decode(record.snapshot, record.id, activity.ruleset_version, activity.state_version)
        status = quest.status if quest else "unaccepted"
        eligible = await self._eligible(session, character)
        can_offer = bool(eligible and (quest is None or quest.status == "abandoned"))
        if requested_kind is not None:
            kind = requested_kind
        elif quest is None:
            kind = "offer" if can_offer and self._at(world, REFUGE) else "unavailable"
        elif status == "completed":
            kind = "completed"
        elif status == "abandoned":
            kind = "abandoned"
        elif combat is not None:
            kind = "combat"
        elif quest.step == 4 and progress.get("awaiting_retry"):
            kind = "recovery"
        elif quest.step == 1 and not self._at(world, REFUGE):
            kind = "travel_refuge"
        elif quest.step in {2, 3, 4, 5} and not self._at(world, RUINS):
            kind = "travel_ruins"
        elif quest.step == 1:
            kind = "review"
        elif quest.step == 2:
            kind = "marks"
        elif quest.step == 3:
            kind = "shelter"
        elif quest.step == 4:
            kind = "combat_pending"
        elif quest.step == 5:
            kind = "last_record"
        else:
            kind = "report" if self._at(world, REFUGE) else "return_refuge"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(
                session, character, combat, FACELESS_CUSTODIAN.category
            )
        return S6View(
            character_id=character.id, kind=kind, status=status,
            step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0,
            progress=progress, location=world.location if world else "",
            level=character.level,
            available=bool(available if available is not None else can_offer),
            reacceptable=bool(quest and quest.status == "abandoned" and eligible),
            tracked=bool(quest and quest.status == "active" and character.tracked_secondary_quest_id == S6_ID),
            combat=combat, activity_id=activity.id if activity else None,
            activity_state_version=activity.state_version if activity else None,
            activity_status=activity.status if activity else None,
            encounter_id=encounter.id if encounter else None,
            combat_id=record.id if record else None,
            consumable_options=options, consumable_quantities=quantities,
            consumable_budget_limit=budget, xp=character.xp,
        )

    async def _eligible(self, session, character):
        if character.level < 10:
            return False
        completed = await session.scalar(select(Quest.id).where(
            Quest.character_id == character.id, Quest.quest_id == "S2", Quest.status == "completed"
        ))
        p5_completed = await session.scalar(select(Quest.id).where(
            Quest.character_id == character.id, Quest.quest_id == P5_ID, Quest.status == "completed"
        ))
        return bool(completed and p5_completed)

    async def _ensure_codex_fragment(self, session, character_id, entry_id, fragment_id):
        if await session.scalar(select(CodexEntry.id).where(
            CodexEntry.character_id == character_id, CodexEntry.entry_id == entry_id
        )) is None:
            session.add(CodexEntry(character_id=character_id, entry_id=entry_id))
            await session.flush()
        if await session.scalar(select(CodexFragment.id).where(
            CodexFragment.character_id == character_id,
            CodexFragment.entry_id == entry_id,
            CodexFragment.fragment_id == fragment_id,
        )) is None:
            session.add(CodexFragment(
                character_id=character_id, entry_id=entry_id, fragment_id=fragment_id
            ))
            await session.flush()

    async def _locked_state(self, session, actor):
        character = await session.scalar(select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        ).with_for_update())
        if character is None:
            return None, None, None
        quest = await session.scalar(select(Quest).where(
            Quest.character_id == character.id, Quest.quest_id == S6_ID
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
            Quest.character_id == character_id, Quest.quest_id == S6_ID
        ))

    async def _world(self, session, character_id):
        return await session.scalar(select(WorldState).where(WorldState.character_id == character_id))

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity).where(
            GameActivity.character_id == character_id, GameActivity.status == "active"
        ))

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == S6_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
