"""Transactional initial selection and safe-location Path changes."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    find_combat_configuration_blocker,
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment_configuration import (
    hp_after_equipment_change,
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.domain.arts import active_art_definition
from asterion.domain.economy import path_switch_cost
from asterion.domain.paths import path_belongs_to_class, paths_for_class
from asterion.infrastructure.db.models import (
    Character,
    CharacterActiveArtSlot,
    ClassTrialState,
    Unlock,
    WorldState,
)

REFUGE = "Refúgio do Ocaso"
COMPLETED_TRIAL_UNLOCK = "class_trial_completed"
SAFE_PATH_CHANGE_LOCATIONS = frozenset({REFUGE})


class PathMutationCode(StrEnum):
    STALE_CONFIGURATION = "stale_configuration"
    TRIAL_REQUIRED = "trial_required"
    WRONG_PATH = "wrong_path"
    ALREADY_SELECTED = "already_selected"
    PATH_REQUIRED = "path_required"
    SAME_PATH = "same_path"
    WRONG_LOCATION = "wrong_location"
    INSUFFICIENT_CROWNS = "insufficient_crowns"
    FOREGROUND = "foreground"
    INVALID_CONFIGURATION = "invalid_configuration"


class PathMutationRejected(RuntimeError):
    def __init__(self, code: PathMutationCode):
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class PathView:
    character_id: UUID
    character_name: str
    character_class: str
    level: int
    crowns: int
    selected_path: str | None
    trial_completed: bool
    trial_state_version: int
    trial_status: str
    trial_stage: int
    location: str | None
    foreground: bool
    configuration_version: int
    incompatible_art_count: int = 0

    @property
    def available_paths(self) -> tuple[str, ...]:
        return paths_for_class(self.character_class) if self.trial_completed else ()

    @property
    def switch_cost(self) -> int:
        return path_switch_cost(self.level)

    @property
    def safe_location(self) -> bool:
        return self.location in SAFE_PATH_CHANGE_LOCATIONS


@dataclass(frozen=True, slots=True)
class PathMutationResult:
    changed: bool
    view: PathView


class PathSelectionService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> PathView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view(session, character)

    async def choose_initial(
        self,
        actor: int,
        path_id: str,
        expected_configuration_version: int,
    ) -> PathMutationResult | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            if not await self._trial_completed(session, character.id):
                raise PathMutationRejected(PathMutationCode.TRIAL_REQUIRED)
            if not path_belongs_to_class(path_id, character.character_class):
                raise PathMutationRejected(PathMutationCode.WRONG_PATH)
            if character.selected_path is not None:
                if character.selected_path == path_id:
                    view = await self._view(session, character)
                    return PathMutationResult(False, view)
                raise PathMutationRejected(PathMutationCode.ALREADY_SELECTED)
            self._check_version(character, expected_configuration_version)

            character.selected_path = path_id
            configuration = await load_equipment_configuration(session, character)
            stats = resolve_character_combat_stats(character, configuration)
            new_hp = hp_after_equipment_change(character, stats.hp)
            character.max_hp = stats.hp
            character.hp = new_hp
            character.combat_configuration_version += 1
            await session.flush()
            view = await self._view(session, character)
            return PathMutationResult(True, view)

    async def exchange(
        self,
        actor: int,
        path_id: str,
        expected_configuration_version: int,
    ) -> PathMutationResult | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            if not await self._trial_completed(session, character.id):
                raise PathMutationRejected(PathMutationCode.TRIAL_REQUIRED)
            if not path_belongs_to_class(path_id, character.character_class):
                raise PathMutationRejected(PathMutationCode.WRONG_PATH)
            if character.selected_path is None:
                raise PathMutationRejected(PathMutationCode.PATH_REQUIRED)
            if character.selected_path == path_id:
                raise PathMutationRejected(PathMutationCode.SAME_PATH)
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id).with_for_update()
            )
            if world is None or world.location not in SAFE_PATH_CHANGE_LOCATIONS:
                raise PathMutationRejected(PathMutationCode.WRONG_LOCATION)
            cost = path_switch_cost(character.level)
            if character.crowns < cost:
                raise PathMutationRejected(PathMutationCode.INSUFFICIENT_CROWNS)

            rows = list(
                (
                    await session.scalars(
                        select(CharacterActiveArtSlot)
                        .where(CharacterActiveArtSlot.character_id == character.id)
                        .order_by(CharacterActiveArtSlot.slot)
                        .with_for_update()
                    )
                ).all()
            )
            incompatible = []
            for row in rows:
                definition = active_art_definition(row.art_id)
                if definition is None:
                    raise PathMutationRejected(PathMutationCode.INVALID_CONFIGURATION)
                if definition.path_id is not None and definition.path_id != path_id:
                    incompatible.append(row)

            character.crowns -= cost
            character.selected_path = path_id
            for row in incompatible:
                await session.delete(row)
            if incompatible:
                await session.flush()
            configuration = await load_equipment_configuration(session, character)
            stats = resolve_character_combat_stats(character, configuration)
            new_hp = hp_after_equipment_change(character, stats.hp)
            character.max_hp = stats.hp
            character.hp = new_hp
            character.combat_configuration_version += 1
            await session.flush()
            view = await self._view(session, character)
            return PathMutationResult(True, view)

    async def incompatible_art_count(self, actor: int, path_id: str) -> int | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            if not path_belongs_to_class(path_id, character.character_class):
                return 0
            rows = list(
                (
                    await session.scalars(
                        select(CharacterActiveArtSlot).where(
                            CharacterActiveArtSlot.character_id == character.id
                        )
                    )
                ).all()
            )
            count = 0
            for row in rows:
                definition = active_art_definition(row.art_id)
                if definition is None:
                    raise PathMutationRejected(PathMutationCode.INVALID_CONFIGURATION)
                if definition.path_id is not None and definition.path_id != path_id:
                    count += 1
            return count

    async def _character(self, session: AsyncSession, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _lock_character(self, session: AsyncSession, actor: int) -> Character | None:
        character_id = await session.scalar(
            select(Character.id).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )
        if character_id is None:
            return None
        try:
            return await lock_for_combat_configuration_mutation(session, character_id)
        except CombatConfigurationLocked as exc:
            raise PathMutationRejected(PathMutationCode.FOREGROUND) from exc

    @staticmethod
    def _check_version(character: Character, expected: int) -> None:
        if character.combat_configuration_version != expected:
            raise PathMutationRejected(PathMutationCode.STALE_CONFIGURATION)

    @staticmethod
    async def _trial_completed(session: AsyncSession, character_id: UUID) -> bool:
        unlocked = await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == COMPLETED_TRIAL_UNLOCK,
            )
        )
        if unlocked is not None:
            return True
        state = await session.scalar(
            select(ClassTrialState.status).where(ClassTrialState.character_id == character_id)
        )
        return state == "completed"

    async def _view(self, session: AsyncSession, character: Character) -> PathView:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        state = await session.scalar(
            select(ClassTrialState).where(ClassTrialState.character_id == character.id)
        )
        blocker = await find_combat_configuration_blocker(session, character.id)
        active_slots = list(
            (
                await session.scalars(
                    select(CharacterActiveArtSlot).where(
                        CharacterActiveArtSlot.character_id == character.id
                    )
                )
            ).all()
        )
        incompatible_count = sum(
            1
            for row in active_slots
            if (definition := active_art_definition(row.art_id)) is not None
            and definition.path_id is not None
            and definition.path_id != character.selected_path
        )
        trial_completed = await self._trial_completed(session, character.id)
        return PathView(
            character_id=character.id,
            character_name=character.name,
            character_class=character.character_class,
            level=character.level,
            crowns=character.crowns,
            selected_path=character.selected_path,
            trial_completed=trial_completed,
            trial_state_version=state.state_version if state is not None else 0,
            trial_status=state.status if state is not None else "unstarted",
            trial_stage=state.current_stage if state is not None else 1,
            location=world.location if world is not None else None,
            foreground=blocker is not None,
            configuration_version=character.combat_configuration_version,
            incompatible_art_count=incompatible_count,
        )
