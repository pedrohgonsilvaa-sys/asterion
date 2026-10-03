"""Authoritative application flow for S2: Os Nomes Esquecidos."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BestiaryRecorder
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import CHARNECA_LOCATION, REFUGE, REGION, RoadService
from asterion.domain.combat import (
    Combat,
    CombatConsumableOption,
    act,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS, ConsumableFamily
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.road import RULESET, create_creature_combat, creature_for, enemy_xp
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CombatRecord,
    ConsumableStack,
    Encounter,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

S2_ID = "S2"
S2_TITLE = "Os Nomes Esquecidos"
S2_VERSION = "tdo-1.0.9"
S2_COMBAT_CONTENT_ID = "s2_scripted_peregrino_calcinado"
S2_REWARD_SOURCE = "s2.os_nomes_esquecidos"
S2_CODEX_ENTRY = "codex.mystery.peregrinos_do_ocaso"
S2_VESTIGE_IDS = (
    "s2.vestige.1",
    "s2.vestige.2",
    "s2.vestige.3",
)
S2_MATERIAL_REWARDS = (
    ("material.tdo.erva_cinzenta", 1),
    ("material.tdo.residuo_ocaso", 1),
)
P2_ID = "P2"
CHARNECA = "Charneca da Fuligem"
PEREGRINO = creature_for("peregrino_calcinado")


@dataclass(frozen=True)
class S2View:
    character_id: UUID
    kind: str
    status: str
    step: int
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    reacceptable: bool = False
    tracked: bool = False
    context: str = "s2"
    combat: Combat | None = None
    activity_id: UUID | None = None
    activity_state_version: int | None = None
    activity_status: str | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: CombatConsumableOption | None = None
    stage: str = "s2"
    xp: int = 0


class S2Service:
    """Quest-specific flow composed from the shared Quest, combat and reward systems."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def oren(self, actor: int) -> S2View | None:
        """Rebuild Oren's local mission options without creating a Quest."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return None
            return await self._view(session, character, quest, world, "oren")

    async def offer(self, actor: int) -> S2View | None:
        """Return the offer or current authoritative state; no Quest is created."""
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is not None:
                if (
                    quest.status == "abandoned"
                    and self._at(world, REFUGE)
                    and not await self._foreground(session, character.id)
                ):
                    available = await self._eligible(session, character)
                    return await self._view(
                        session,
                        character,
                        quest,
                        world,
                        "offer" if available else "unavailable",
                    )
                return await self._view(session, character, quest, world)
            if not self._at(world, REFUGE) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world, "unavailable")
            available = await self._eligible(session, character)
            return await self._view(
                session,
                character,
                quest,
                world,
                "offer" if available else "unavailable",
            )

    async def resume(self, actor: int) -> S2View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def accept(
        self, actor: int, version: int = 0, *, reaccept: bool = False
    ) -> S2View | None:
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
                quest.progress = {}
                quest.content_version = S2_VERSION
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world)
                quest = Quest(
                    character_id=character.id,
                    quest_id=S2_ID,
                    title=S2_TITLE,
                    status="active",
                    step=1,
                    content_version=S2_VERSION,
                    state_version=0,
                    progress={},
                )
                session.add(quest)
                await session.flush()
            return await self._view(session, character, quest, world)

    async def objective(self, actor: int) -> S2View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            world = await self._world(session, character.id)
            # Read-only objective callbacks must preserve the current foreground
            # combat/result state instead of replacing it with a narrative screen.
            return await self._view(session, character, quest, world)

    async def find_camp(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version, step=1) or not self._at(world, CHARNECA):
                return await self._view(session, character, quest, world)
            if await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            progress["camp_found"] = True
            quest.progress = progress
            quest.step = 2
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def examine_vestige(self, actor: int, vestige_id: str, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=2)
                or not self._at(world, CHARNECA)
                or vestige_id not in S2_VESTIGE_IDS
                or not (quest.progress or {}).get("camp_found")
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)

            progress = dict(quest.progress or {})
            vestiges = set(progress.get("vestiges", []))
            if vestige_id in vestiges:
                return await self._view(session, character, quest, world)
            vestiges.add(vestige_id)
            progress["vestiges"] = [item for item in S2_VESTIGE_IDS if item in vestiges]
            quest.progress = progress
            if len(vestiges) == len(S2_VESTIGE_IDS):
                quest.step = 3
                activity = await self._materialize_combat(session, character, quest, world)
                if activity is None:
                    # Do not commit a completed objective without its fixed encounter.
                    quest.step = 2
                    quest.progress = {
                        **(quest.progress or {}),
                        "vestiges": [
                            item for item in S2_VESTIGE_IDS if item in vestiges - {vestige_id}
                        ],
                    }
                    return await self._view(session, character, quest, world)
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def retry(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            progress = dict(quest.progress or {})
            if (
                not self._valid(quest, version, step=3)
                or not progress.get("awaiting_retry")
                or not self._at(world, CHARNECA)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            progress.update(awaiting_retry=False, combat_pending=False)
            quest.progress = progress
            activity = await self._materialize_combat(session, character, quest, world)
            if activity is None:
                progress["awaiting_retry"] = True
                quest.progress = progress
                return await self._view(session, character, quest, world)
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
    ) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S2_COMBAT_CONTENT_ID,
                )
                .with_for_update()
            )
            if activity is None or quest is None:
                return None
            current = await self._view(session, character, quest, world)
            foreground = await self._foreground(session, character.id)
            if (
                quest.status != "active"
                or quest.content_version != S2_VERSION
                or quest.step != 3
                or activity.status != "active"
                or activity.state_version != version
                or foreground is None
                or foreground.id != activity.id
                or not self._at(world, CHARNECA)
                or (action is None) == (consumable_id is None)
            ):
                return current

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
                    return replace(
                        current,
                        consumable_notice="⚠️ Consumível · Não está mais disponível.",
                    )
                budget = ENCOUNTER_CONSUMABLE_LIMITS.get(PEREGRINO.category, 0)
                updated = use_combat_consumable(
                    combat,
                    consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=budget,
                )
                if updated.version == combat.version:
                    notice = self._consumable_rejection_notice(combat, budget)
                    return replace(
                        current,
                        consumable_notice=notice or "⚠️ Consumível · Não está mais disponível.",
                    )
                stack.quantity -= 1

            if updated.version == combat.version:
                return current
            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            character.hp = updated.fighters["player"].hp
            await self.bestiary.record_combat_events(
                session, character.id, PEREGRINO.creature_id, None, updated
            )

            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await self._grant_enemy_xp(session, character, activity)
                await self.bestiary.record(
                    session,
                    character.id,
                    PEREGRINO.creature_id,
                    victory=True,
                    observation_category="common",
                )
                await self._normalize_character_hp(session, character)
                # Step 4 is satisfied by this terminal Victory; step 5 is the next action.
                quest.step = 5
                progress.update(
                    encounter_result="victory",
                    awaiting_retry=False,
                    combat_pending=False,
                    fragment_recovered=False,
                )
            elif updated.result == "defeat":
                activity.status = "failed"
                await self.bestiary.record(
                    session,
                    character.id,
                    PEREGRINO.creature_id,
                    observation_category="common",
                )
                await self._normalize_character_hp(session, character)
                recovery_brazier, recovery_location = await self.road.recover_normal_pve_defeat(
                    session, character, CHARNECA_LOCATION, world
                )
                progress.update(
                    encounter_result="defeat",
                    awaiting_retry=True,
                    combat_pending=False,
                    defeat_activity_id=str(activity.id),
                    recovery_brazier=recovery_brazier,
                    recovery_location=recovery_location,
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
    ) -> S2View | None:
        """Rebuild shared combat Consumable selection from current persisted state."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id == S2_COMBAT_CONTENT_ID,
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
                option for option in current.consumable_options if option.item_id == item_id
            )
            if item is None or not item_options:
                return replace(
                    current,
                    consumable_screen=("items" if current.consumable_options else None),
                    consumable_notice="⚠️ Consumível · Não está mais disponível.",
                )
            if screen == "choose_item":
                if item.family == ConsumableFamily.DISPELLER:
                    target_ids = tuple(dict.fromkeys(option.target_id for option in item_options))
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
                    target_id, parent = "player", "items"
                selected = tuple(option for option in item_options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent=parent
                )
            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(option for option in item_options if option.target_id == target_id)
                if not selected:
                    return replace(
                        current,
                        consumable_screen=("items" if current.consumable_options else None),
                        consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
                    )
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )
            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                target_ids = tuple(dict.fromkeys(option.target_id for option in item_options))
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
                consumable_screen=("items" if current.consumable_options else None),
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

    async def recover_fragment(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if (
                not self._valid(quest, version, step=5)
                or not self._at(world, CHARNECA)
                or (quest.progress or {}).get("encounter_result") != "victory"
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            progress = dict(quest.progress or {})
            progress["fragment_recovered"] = True
            quest.progress = progress
            quest.step = 6
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def complete_with_oren(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if quest.status == "completed":
                return await self._view(session, character, quest, world)
            if (
                not self._valid(quest, version, step=6)
                or not self._at(world, REFUGE)
                or not (quest.progress or {}).get("fragment_recovered")
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)

            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == S2_REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                event = RewardEvent(
                    character_id=character.id,
                    source_id=S2_REWARD_SOURCE,
                )
                session.add(event)
                await session.flush()
                character.xp += 2695
                character.crowns += 120
                components = [
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="xp",
                        item_id=None,
                        quantity=2695,
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="crowns",
                        item_id=None,
                        quantity=120,
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
                    for material_id, quantity in S2_MATERIAL_REWARDS
                )
                session.add_all(components)
                for material_id, quantity in S2_MATERIAL_REWARDS:
                    await self.road.deliver_material(
                        session,
                        character,
                        material_id,
                        quantity,
                        f"{S2_REWARD_SOURCE}:material:{material_id}",
                        bound=True,
                    )
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=S2_CODEX_ENTRY,
            )
            await self._normalize_character_hp(session, character)
            quest.status = "completed"
            quest.progress = {
                **(quest.progress or {}),
                "completed": True,
                "codex_recorded": True,
            }
            quest.state_version += 1
            from asterion.application.tdo_feats import reconcile_tdo_feats

            await reconcile_tdo_feats(session, character)
            if character.tracked_secondary_quest_id == S2_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world)

    async def toggle_tracking(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S2_ID else S2_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def abandon_confirmation(self, actor: int) -> S2View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S2View | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor)
            if character is None or quest is None or world is None:
                return None
            if not self._valid(quest, version) or await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            quest.status = "abandoned"
            quest.step = 1
            quest.progress = {}
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S2_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _materialize_combat(self, session, character, quest, world):
        if not self._at(world, CHARNECA):
            return None
        foreground = await self._foreground(session, character.id)
        if foreground is not None:
            if foreground.content_id == S2_COMBAT_CONTENT_ID and str(foreground.id) == (
                quest.progress or {}
            ).get("combat_activity_id"):
                return foreground
            return None
        configuration = await load_equipment_configuration(session, character)
        active_art_configuration = await load_active_art_configuration(session, character)
        reconcile_character_hp(character, configuration)
        combat = create_creature_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            character.hp,
            PEREGRINO,
            4,
            None,
            player_level=character.level,
            equipment_configuration=configuration,
            ruleset_version=RULESET,
            flavor="As cinzas cedem sob os passos. Um Peregrino Calcinado se volta para você.",
            opening_log="🧥 Peregrino Calcinado · Nv.4 surge junto ao acampamento.",
            active_art_ids=active_art_configuration.art_ids,
        )
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | (
            active_art_configuration.to_data()
        )
        activity, encounter, record = await CombatRepository(session).create(
            character, S2_COMBAT_CONTENT_ID, combat
        )
        progress = dict(quest.progress or {})
        progress.update(
            combat_activity_id=str(activity.id),
            encounter_result=None,
            awaiting_retry=False,
            combat_pending=False,
        )
        quest.progress = progress
        await self.bestiary.record(
            session,
            character.id,
            PEREGRINO.creature_id,
            evidence_id=f"habitat:{CHARNECA_LOCATION}",
            evidence_category="habitat",
            evidence_points=3,
            grant_observation_xp=True,
            observation_level=4,
            observation_category="common",
        )
        await session.flush()
        return activity

    async def _grant_enemy_xp(self, session, character, activity) -> int:
        source_id = f"{S2_REWARD_SOURCE}:enemy-xp:{activity.id}"
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
        amount = enemy_xp(4, "common", player_level=character.level)
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="enemy_xp",
                item_id=PEREGRINO.creature_id,
                quantity=amount,
                payload={
                    "enemy_level": 4,
                    "category": "common",
                    "observation_context": "S2",
                },
            )
        )
        character.xp += amount
        return amount

    async def _normalize_character_hp(self, session, character):
        configuration = await load_equipment_configuration(session, character)
        reconcile_character_hp(character, configuration)
        await consolidate_character_level(session, character, configuration)
        reconcile_character_hp(character, configuration)

    async def _view(self, session, character, quest, world, requested_kind=None):
        progress = dict(quest.progress or {}) if quest else {}
        activity = None
        encounter_id = None
        combat_id = None
        combat = None
        activity_status = None
        activity_state_version = None
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
                    GameActivity.content_id == S2_COMBAT_CONTENT_ID,
                )
            )
            if activity is not None:
                activity_status = activity.status
                activity_state_version = activity.state_version
                result = await session.execute(
                    select(Encounter, CombatRecord)
                    .join(CombatRecord)
                    .where(Encounter.game_activity_id == activity.id)
                )
                row = result.one_or_none()
                encounter, record = row if row is not None else (None, None)
                if encounter is not None and record is not None:
                    encounter_id = encounter.id
                    combat_id = record.id
                    if activity.status == "active":
                        combat = decode(
                            record.snapshot,
                            record.id,
                            activity.ruleset_version,
                            activity.state_version,
                        )

        if quest is None:
            status = "unaccepted"
            step = 1
            state_version = 0
        else:
            status, step, state_version = (
                quest.status,
                quest.step,
                quest.state_version,
            )

        available = await self._eligible(session, character) if quest is None else False
        reacceptable = bool(
            quest is not None
            and quest.status == "abandoned"
            and await self._eligible(session, character)
        )
        if requested_kind is not None:
            kind = requested_kind
        elif quest is None:
            kind = "offer" if available else "unavailable"
        elif quest.status == "completed":
            kind = "completed"
        elif quest.status == "abandoned":
            kind = "abandoned"
        elif combat is not None:
            kind = "combat"
        elif step == 1:
            kind = "detail"
        elif step == 2:
            kind = "objective"
        elif step == 3 and progress.get("awaiting_retry"):
            kind = "recovery"
        elif step == 3:
            kind = "combat_pending"
        elif step == 5:
            kind = "fragment"
        else:
            kind = "return"

        quantities: tuple[tuple[str, int], ...] = ()
        options: tuple[CombatConsumableOption, ...] = ()
        budget = 0
        if activity is not None and activity.status == "active" and combat is not None:
            budget = ENCOUNTER_CONSUMABLE_LIMITS.get(PEREGRINO.category, 0)
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
            quantities = tuple((row.consumable_id, row.quantity) for row in stock)
            options = combat_consumable_options(
                combat,
                tuple(row.consumable_id for row in stock),
                budget_limit=budget,
            )

        return S2View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=step,
            state_version=state_version,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=available,
            reacceptable=reacceptable,
            tracked=bool(
                quest and quest.status == "active" and character.tracked_secondary_quest_id == S2_ID
            ),
            combat=combat,
            activity_id=activity.id if activity is not None else None,
            activity_state_version=activity_state_version,
            activity_status=activity_status,
            encounter_id=encounter_id,
            combat_id=combat_id,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            stage=character.stage,
            xp=character.xp,
        )

    async def _eligible(self, session, character):
        p2_completed = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == P2_ID,
                Quest.status == "completed",
            )
        )
        return bool(p2_completed and character.level >= 4)

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
        quest = await self._locked_quest(session, character.id)
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id).with_for_update()
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
                Quest.quest_id == S2_ID,
            )
        )

    async def _locked_quest(self, session, character_id):
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id == S2_ID,
            )
            .with_for_update()
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

    async def _ensure(self, session, model, **values):
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return found
        row = model(**values)
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    def _valid(quest, version, *, step=None):
        return bool(
            quest is not None
            and quest.status == "active"
            and quest.content_version == S2_VERSION
            and quest.state_version == version
            and (step is None or quest.step == step)
        )

    @staticmethod
    def _at(world, location):
        return bool(world is not None and world.region == REGION and world.location == location)
