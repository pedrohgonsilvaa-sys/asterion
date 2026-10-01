"""P5 campaign mission composed from persistent quests and shared combat."""
# ruff: noqa: E501

from dataclasses import dataclass, replace
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
from asterion.domain.road import RUINS_LOCATION, SUNSET_CUSTODIAN, enemy_xp
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

P5_ID = "P5"
P5_TITLE = "A Porta do Poente"
P5_VERSION = "tdo-1.0.11"
P5_CONTENT_ID = "p5_scripted_custodio_poente"
P5_REWARD_SOURCE = "p5.a_porta_do_poente"
P5_ELEMENTS = (
    "p5.door_element.1",
    "p5.door_element.2",
    "p5.door_element.3",
)
P5_CODEX_ENTRY = "codex.history.antigos_asterianos"
P5_DOOR_FRAGMENT = "codex.fragment.ruinas.porta_do_poente"
P5_SYMBOL_FRAGMENT = "codex.fragment.ruinas.simbolo_recorrente"
P5_IRON = "material.tdo.ferro_de_fuligem"
P5_RESIDUE = "material.tdo.residuo_ocaso"


@dataclass(frozen=True)
class P5View:
    character_id: UUID
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    context: str = "p5"
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


class P5Service:
    """Owns P5 transitions; movement and combat remain shared services."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def offer(self, actor: int) -> P5View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            available = bool(
                quest is None
                and self._at(world, REFUGE)
                and not await self._foreground(session, character.id)
                and await self._eligible(session, character)
            )
            return await self._view(
                session,
                character,
                quest,
                world,
                "offer" if available else "unavailable" if quest is None else None,
                available=available,
            )

    async def alda(self, actor: int) -> P5View | None:
        return await self._npc(actor, "alda")

    async def oren(self, actor: int) -> P5View | None:
        return await self._npc(actor, "oren")

    async def _npc(self, actor: int, npc: str) -> P5View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            available = bool(
                quest is None and await self._eligible(session, character)
            )
            return await self._view(
                session, character, quest, world, npc, available=available
            )

    async def resume(self, actor: int) -> P5View | None:
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

    async def accept(self, actor: int, version: int = 0) -> P5View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            if (
                quest is not None
                or version != 0
                or not self._at(world, REFUGE)
                or await self._foreground(session, character.id)
                or not await self._eligible(session, character)
            ):
                return await self._view(session, character, quest, world)
            quest = Quest(
                character_id=character.id,
                quest_id=P5_ID,
                title=P5_TITLE,
                status="active",
                step=1,
                content_version=P5_VERSION,
                state_version=0,
                progress={},
            )
            session.add(quest)
            await session.flush()
            return await self._view(session, character, quest, world)

    async def action(
        self,
        actor: int,
        version: int,
        operation: str,
        item: str | None = None,
    ) -> P5View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)

            progress = dict(quest.progress or {})
            if operation == "follow_structures" and quest.step == 1 and self._at(world, RUINS):
                progress["deep_guard_structures_followed"] = True
                quest.step = 2
            elif operation == "find_door" and quest.step == 2 and self._at(world, RUINS):
                progress["door_known"] = True
                progress["ruins_updated"] = True
                quest.step = 3
                quest.progress = progress
                activity = await self._materialize(session, character, quest)
                if activity is None:
                    quest.step = 2
                    progress.pop("door_known", None)
                    progress.pop("ruins_updated", None)
                    return await self._view(session, character, quest, world)
                await self._ensure_codex_fragment(session, character.id, P5_DOOR_FRAGMENT)
                progress = dict(quest.progress or progress)
            elif (
                operation == "retry"
                and quest.step == 3
                and progress.get("awaiting_retry")
                and self._at(world, RUINS)
            ):
                progress["awaiting_retry"] = False
                quest.progress = progress
                if await self._materialize(session, character, quest) is None:
                    progress["awaiting_retry"] = True
                    quest.progress = progress
                    return await self._view(session, character, quest, world)
                progress = dict(quest.progress or progress)
            elif operation == "element" and quest.step == 4 and self._at(world, RUINS):
                if item not in P5_ELEMENTS:
                    return await self._view(session, character, quest, world)
                found = set(progress.get("door_elements", ()))
                if item in found:
                    return await self._view(session, character, quest, world)
                found.add(item)
                progress["door_elements"] = [key for key in P5_ELEMENTS if key in found]
                if len(found) == len(P5_ELEMENTS):
                    quest.step = 5
            elif operation == "record_symbol" and quest.step == 5 and self._at(world, RUINS):
                progress["recurring_symbol_recorded"] = True
                quest.step = 6
                await self._ensure_codex_fragment(session, character.id, P5_SYMBOL_FRAGMENT)
            elif (
                operation in {"report_alda", "report_oren"}
                and quest.step == 6
                and self._at(world, REFUGE)
            ):
                reports = set(progress.get("reports", ()))
                reports.add("alda" if operation == "report_alda" else "oren")
                progress["reports"] = [name for name in ("alda", "oren") if name in reports]
                if reports == {"alda", "oren"}:
                    quest.progress = progress
                    await self._complete(session, character, quest)
                    return await self._view(session, character, quest, world)
            else:
                return await self._view(session, character, quest, world)

            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def action_combat(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ) -> P5View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P5_CONTENT_ID,
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
                category=SUNSET_CUSTODIAN.category,
            )
            if updated is None or updated.version == version:
                return current

            # Establish the legitimate first encounter before replaying combat evidence,
            # so an Elite action observed on the opening exchange is not lost.
            observed = await session.scalar(
                select(BestiaryEntry.id).where(
                    BestiaryEntry.character_id == character.id,
                    BestiaryEntry.creature_id == SUNSET_CUSTODIAN.creature_id,
                )
            )
            if observed is None:
                await self.bestiary.record(
                    session,
                    character.id,
                    SUNSET_CUSTODIAN.creature_id,
                    elite=True,
                    observation_category="elite",
                )
            await self.bestiary.record_combat_events(
                session, character.id, SUNSET_CUSTODIAN.creature_id, None, updated
            )

            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await normalize_character_hp(session, character)
                await self.bestiary.record(
                    session,
                    character.id,
                    SUNSET_CUSTODIAN.creature_id,
                    victory=True,
                    elite=True,
                    observation_category="elite",
                )
                progress.update(combat_result="victory", awaiting_retry=False)
                quest.step = 4
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session,
                    character.id,
                    SUNSET_CUSTODIAN.creature_id,
                    elite=True,
                    observation_category="elite",
                )
                brazier, location = await self.road.recover_normal_pve_defeat(
                    session, character, RUINS_LOCATION, world
                )
                progress.update(
                    combat_result="defeat",
                    awaiting_retry=True,
                    defeat_activity_id=str(activity.id),
                    recovery_brazier=brazier,
                    recovery_location=location,
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
    ) -> P5View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P5_CONTENT_ID,
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
                return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
            return derive_consumable_selection(
                current, screen=screen, item_id=item_id, target_id=target_id, parent=parent
            )

    async def _materialize(self, session, character, quest):
        if await self._foreground(session, character.id):
            return None
        activity = await materialize(
            session,
            character,
            P5_CONTENT_ID,
            SUNSET_CUSTODIAN,
            9,
            flavor="Uma figura blindada se ergue diante da Porta do Poente.",
            opening_log="🛡️ Custódio do Poente · Nv.9 guarda a estrutura deliberadamente protegida.",
        )
        if activity is not None:
            progress = dict(quest.progress or {})
            progress["combat_activity_id"] = str(activity.id)
            progress.update(combat_result=None, awaiting_retry=False)
            quest.progress = progress
        return activity

    async def _grant_enemy_xp(self, session, character, activity):
        source = f"{P5_REWARD_SOURCE}:enemy-xp:{activity.id}"
        if await session.scalar(
            select(RewardEvent.id)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == source,
            )
            .with_for_update()
        ):
            return
        amount = enemy_xp(9, "elite", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="enemy_xp",
                item_id=SUNSET_CUSTODIAN.creature_id,
                quantity=amount,
                payload={"enemy_level": 9, "category": "elite"},
            )
        )
        character.xp += amount

    async def _complete(self, session, character, quest):
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P5_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P5_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 7100
            character.crowns += 300
            session.add_all(
                [
                    RewardComponent(
                        reward_event_id=event.id, kind="xp", item_id=None, quantity=7100
                    ),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", item_id=None, quantity=300
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=P5_IRON,
                        quantity=3,
                        payload={"material_id": P5_IRON, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=P5_RESIDUE,
                        quantity=1,
                        payload={"material_id": P5_RESIDUE, "bound": True},
                    ),
                ]
            )
            await self.road.deliver_material(
                session,
                character,
                P5_IRON,
                3,
                f"{P5_REWARD_SOURCE}:material:{P5_IRON}",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                P5_RESIDUE,
                1,
                f"{P5_REWARD_SOURCE}:material:{P5_RESIDUE}",
                bound=True,
            )
        await self._ensure_codex_entry(session, character.id)
        quest.status = "completed"
        quest.progress = {
            **(quest.progress or {}),
            "completed": True,
            "ruins_updated": True,
            "door_known": True,
            "recurring_symbol_recorded": True,
        }
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
        if stored_id is not None:
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == stored_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == P5_CONTENT_ID,
                )
            )
            if activity is not None:
                row = (
                    await session.execute(
                        select(Encounter, CombatRecord)
                        .join(CombatRecord)
                        .where(Encounter.game_activity_id == activity.id)
                    )
                ).one_or_none()
                if row:
                    encounter, record = row
                    if activity.status == "active":
                        combat = decode(
                            record.snapshot,
                            record.id,
                            activity.ruleset_version,
                            activity.state_version,
                        )
        status = quest.status if quest else "unaccepted"
        eligible = await self._eligible(session, character)
        can_offer = bool(eligible and quest is None)
        if requested_kind is not None:
            kind = requested_kind
        elif quest is None:
            kind = "offer" if can_offer and self._at(world, REFUGE) else "unavailable"
        elif status == "completed":
            kind = "completed"
        elif combat is not None:
            kind = "combat"
        elif status != "active":
            kind = "unavailable"
        elif quest.step == 3 and progress.get("awaiting_retry"):
            kind = "recovery"
        elif quest.step <= 5 and not self._at(world, RUINS):
            kind = "travel"
        elif quest.step == 1:
            kind = "follow_structures"
        elif quest.step == 2:
            kind = "find_door"
        elif quest.step == 3:
            kind = "combat_pending"
        elif quest.step == 4:
            kind = "elements"
        elif quest.step == 5:
            kind = "record_symbol"
        else:
            kind = "reports" if self._at(world, REFUGE) else "return"
        options = quantities = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            options, quantities, budget = await consumable_state(
                session, character, combat, SUNSET_CUSTODIAN.category
            )
        return P5View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest else 1,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level,
            available=bool(available if available is not None else can_offer),
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
            character.level >= 9
            and await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == "P4",
                    Quest.status == "completed",
                )
            )
        )

    async def _ensure_codex_entry(self, session, character_id):
        entry = await session.scalar(
            select(CodexEntry)
            .where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == P5_CODEX_ENTRY,
            )
            .with_for_update()
        )
        if entry is None:
            session.add(CodexEntry(character_id=character_id, entry_id=P5_CODEX_ENTRY))
            await session.flush()

    async def _ensure_codex_fragment(self, session, character_id, fragment_id):
        await self._ensure_codex_entry(session, character_id)
        fragment = await session.scalar(
            select(CodexFragment)
            .where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == P5_CODEX_ENTRY,
                CodexFragment.fragment_id == fragment_id,
            )
            .with_for_update()
        )
        if fragment is None:
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=P5_CODEX_ENTRY,
                    fragment_id=fragment_id,
                )
            )
            await session.flush()

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
            .where(Quest.character_id == character.id, Quest.quest_id == P5_ID)
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
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P5_ID)
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        )

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == P5_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world and world.region == REGION and world.location == location)
