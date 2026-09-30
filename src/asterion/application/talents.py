"""Transactional Talent progression and character-facing read model."""

from __future__ import annotations

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
from asterion.domain.economy import crowns_per_level
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TALENT_POINT_LEVELS,
    TALENTS_BY_CLASS,
    TalentDefinition,
    talent_points_at_level,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterTalentChoice,
    WorldState,
)

SAFE_RESPEC_LOCATIONS = frozenset({"Refúgio do Ocaso"})


class TalentMutationCode(StrEnum):
    STALE_CONFIGURATION = "stale_configuration"
    FOREGROUND = "foreground"
    UNKNOWN_TALENT = "unknown_talent"
    WRONG_CLASS = "wrong_class"
    LEVEL_REQUIRED = "level_required"
    TIER_NOT_IMPLEMENTED = "tier_not_implemented"
    NO_POINTS = "no_points"
    DUPLICATE_TALENT = "duplicate_talent"
    INVALID_CURRENT_CONFIGURATION = "invalid_current_configuration"
    WRONG_LOCATION = "wrong_location"
    INSUFFICIENT_CROWNS = "insufficient_crowns"
    NOTHING_TO_RESPEC = "nothing_to_respec"


class TalentMutationRejected(RuntimeError):
    def __init__(self, code: TalentMutationCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class TalentChoiceView:
    point_slot: int
    talent_id: str


@dataclass(frozen=True, slots=True)
class TalentView:
    character_id: UUID
    character_name: str
    character_class: str
    level: int
    selected_path: str | None
    combat_configuration_version: int
    total_points: int
    available_points: int
    choices: tuple[TalentChoiceView, ...]
    crowns: int
    location: str | None
    foreground: bool

    @property
    def respec_cost(self) -> int:
        return 2 * crowns_per_level(self.level)

    @property
    def talents(self) -> tuple[TalentDefinition, ...]:
        return TALENTS_BY_CLASS[self.character_class]


@dataclass(frozen=True, slots=True)
class TalentMutationResult:
    changed: bool
    point_slot: int | None
    combat_configuration_version: int
    view: TalentView


class TalentService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> TalentView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view(session, character)

    async def acquire(
        self,
        actor: int,
        talent_id: str,
        expected_configuration_version: int,
    ) -> TalentMutationResult | None:
        definition = TALENT_DEFINITIONS.get(talent_id)
        if definition is None:
            raise TalentMutationRejected(TalentMutationCode.UNKNOWN_TALENT)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            if definition.character_class != character.character_class:
                raise TalentMutationRejected(TalentMutationCode.WRONG_CLASS)
            if character.level < definition.level:
                raise TalentMutationRejected(TalentMutationCode.LEVEL_REQUIRED)
            if definition.level not in IMPLEMENTED_TALENT_LEVELS:
                raise TalentMutationRejected(TalentMutationCode.TIER_NOT_IMPLEMENTED)

            rows = await self._locked_choices(session, character.id)
            current = self._validated_choices(character, rows)
            if talent_id in {talent for _, talent in current}:
                raise TalentMutationRejected(TalentMutationCode.DUPLICATE_TALENT)
            total_points = talent_points_at_level(character.level)
            occupied = {slot for slot, _ in current if slot <= total_points}
            point_slot = next(
                (slot for slot in range(1, total_points + 1) if slot not in occupied),
                None,
            )
            if point_slot is None:
                raise TalentMutationRejected(TalentMutationCode.NO_POINTS)
            if definition.level > TALENT_POINT_LEVELS[point_slot - 1]:
                raise TalentMutationRejected(TalentMutationCode.LEVEL_REQUIRED)

            session.add(
                CharacterTalentChoice(
                    character_id=character.id,
                    point_slot=point_slot,
                    talent_id=talent_id,
                )
            )
            await session.flush()
            await self._reconcile_hp(session, character)
            character.combat_configuration_version += 1
            await session.flush()
            view = await self._view(session, character)
            return TalentMutationResult(
                True, point_slot, character.combat_configuration_version, view
            )

    async def respec(
        self,
        actor: int,
        expected_configuration_version: int,
    ) -> TalentMutationResult | None:
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            rows = await self._locked_choices(session, character.id)
            self._validated_choices(character, rows)
            if not rows:
                raise TalentMutationRejected(TalentMutationCode.NOTHING_TO_RESPEC)
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id).with_for_update()
            )
            if world is None or world.location not in SAFE_RESPEC_LOCATIONS:
                raise TalentMutationRejected(TalentMutationCode.WRONG_LOCATION)
            cost = 2 * crowns_per_level(character.level)
            if character.crowns < cost:
                raise TalentMutationRejected(TalentMutationCode.INSUFFICIENT_CROWNS)
            for row in rows:
                await session.delete(row)
            character.crowns -= cost
            await session.flush()
            await self._reconcile_hp(session, character)
            character.combat_configuration_version += 1
            await session.flush()
            view = await self._view(session, character)
            return TalentMutationResult(True, None, character.combat_configuration_version, view)

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
            raise TalentMutationRejected(TalentMutationCode.FOREGROUND) from exc

    @staticmethod
    def _check_version(character: Character, expected: int) -> None:
        if character.combat_configuration_version != expected:
            raise TalentMutationRejected(TalentMutationCode.STALE_CONFIGURATION)

    @staticmethod
    async def _locked_choices(
        session: AsyncSession,
        character_id: UUID,
    ) -> list[CharacterTalentChoice]:
        return list(
            (
                await session.scalars(
                    select(CharacterTalentChoice)
                    .where(CharacterTalentChoice.character_id == character_id)
                    .order_by(CharacterTalentChoice.point_slot)
                    .with_for_update()
                )
            ).all()
        )

    @staticmethod
    def _validated_choices(
        character: Character,
        rows: list[CharacterTalentChoice],
    ) -> tuple[tuple[int, str], ...]:
        result = []
        slots: set[int] = set()
        talents: set[str] = set()
        for row in rows:
            definition = TALENT_DEFINITIONS.get(row.talent_id)
            if (
                isinstance(row.point_slot, bool)
                or not 1 <= row.point_slot <= len(TALENT_POINT_LEVELS)
                or row.point_slot in slots
                or row.talent_id in talents
                or definition is None
                or definition.character_class != character.character_class
                or definition.level > TALENT_POINT_LEVELS[row.point_slot - 1]
            ):
                raise TalentMutationRejected(TalentMutationCode.INVALID_CURRENT_CONFIGURATION)
            slots.add(row.point_slot)
            talents.add(row.talent_id)
            result.append((row.point_slot, row.talent_id))
        return tuple(result)

    @staticmethod
    async def _reconcile_hp(session: AsyncSession, character: Character) -> None:
        configuration = await load_equipment_configuration(session, character)
        stats = resolve_character_combat_stats(character, configuration)
        character.hp = hp_after_equipment_change(character, stats.hp)
        character.max_hp = stats.hp

    async def _view(self, session: AsyncSession, character: Character) -> TalentView:
        rows = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice)
                    .where(CharacterTalentChoice.character_id == character.id)
                    .order_by(CharacterTalentChoice.point_slot)
                )
            ).all()
        )
        choices = self._validated_choices(character, rows)
        total_points = talent_points_at_level(character.level)
        active_choices = tuple(
            (slot, talent_id) for slot, talent_id in choices if slot <= total_points
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        blocker = await find_combat_configuration_blocker(session, character.id)
        return TalentView(
            character.id,
            character.name,
            character.character_class,
            character.level,
            character.selected_path,
            character.combat_configuration_version,
            total_points,
            max(0, total_points - len(active_choices)),
            tuple(TalentChoiceView(slot, talent_id) for slot, talent_id in choices),
            character.crowns,
            world.location if world is not None else None,
            blocker is not None,
        )
