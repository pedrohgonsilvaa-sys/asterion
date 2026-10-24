"""Authoritative persistence and validation for the three active-Art slots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    find_combat_configuration_blocker,
    lock_for_combat_configuration_mutation,
)
from asterion.application.weapon_metadata import equipped_weapon_compatibility_tags
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ActiveArtDefinition,
    active_art_definition,
    weapon_requirement_satisfied,
)
from asterion.infrastructure.db.models import Character, CharacterActiveArtSlot

ACTIVE_ART_SLOTS = (1, 2, 3)


class ActiveArtConfigurationError(ValueError):
    """Raised when persisted active-Art state is internally invalid."""


class ActiveArtMutationCode(StrEnum):
    INVALID_SLOT = "invalid_slot"
    UNKNOWN_ART = "unknown_art"
    WRONG_CLASS = "wrong_class"
    LEVEL_REQUIRED = "level_required"
    PATH_REQUIRED = "path_required"
    DUPLICATE_ART = "duplicate_art"
    STALE_CONFIGURATION = "stale_configuration"
    INVALID_CURRENT_CONFIGURATION = "invalid_current_configuration"
    WEAPON_REQUIREMENT = "weapon_requirement"


class ActiveArtMutationRejected(RuntimeError):
    def __init__(self, code: ActiveArtMutationCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class ActiveArtSlotSnapshot:
    slot: int
    art_id: str

    def to_data(self) -> dict[str, int | str]:
        return {"slot": self.slot, "art_id": self.art_id}


@dataclass(frozen=True, slots=True)
class ActiveArtConfigurationSnapshot:
    combat_configuration_version: int
    slots: tuple[ActiveArtSlotSnapshot, ...] = ()

    @property
    def art_ids(self) -> tuple[str, ...]:
        return tuple(entry.art_id for entry in self.slots)

    def to_data(self) -> dict:
        return {
            "combat_configuration_version": self.combat_configuration_version,
            "active_arts": [entry.to_data() for entry in self.slots],
        }


@dataclass(frozen=True, slots=True)
class ActiveArtMutationResult:
    changed: bool
    slot: int
    art_id: str | None
    combat_configuration_version: int


@dataclass(frozen=True, slots=True)
class ActiveArtCharacterView:
    character_id: UUID
    character_name: str
    character_class: str
    level: int
    selected_path: str | None
    combat_configuration_version: int
    slots: tuple[ActiveArtSlotSnapshot, ...]
    available_art_ids: tuple[str, ...]
    foreground: bool
    weapon_incompatible_art_ids: tuple[str, ...] = ()
    ineligible_art_ids: tuple[str, ...] = ()


def _validate_definition(character: Character, definition: ActiveArtDefinition) -> None:
    if definition.character_class != character.character_class:
        raise ActiveArtConfigurationError("Equipped Art does not belong to the character Class.")
    if character.level < definition.min_level:
        raise ActiveArtConfigurationError("Equipped Art level requirement is not met.")
    if definition.path_id is not None and character.selected_path != definition.path_id:
        raise ActiveArtConfigurationError("Equipped Path Art does not match the selected Path.")


async def load_active_art_configuration(
    session: AsyncSession,
    character: Character,
    *,
    lock_rows: bool = True,
    weapon_compatibility_tags: frozenset[str] | None = None,
    validate_weapon_requirements: bool = True,
    validate_eligibility: bool = True,
) -> ActiveArtConfigurationSnapshot:
    """Load persisted Arts and validate explicit weapon requirements."""
    if not session.in_transaction():
        raise RuntimeError("Active Art configuration loading requires an open transaction.")
    statement = (
        select(CharacterActiveArtSlot)
        .where(CharacterActiveArtSlot.character_id == character.id)
        .order_by(CharacterActiveArtSlot.slot)
    )
    if lock_rows:
        statement = statement.with_for_update()
    rows = list((await session.scalars(statement)).all())
    needs_weapon_check = any(
        (definition := active_art_definition(row.art_id)) is not None
        and definition.weapon_requirement
        for row in rows
    )
    if needs_weapon_check and weapon_compatibility_tags is None:
        weapon_compatibility_tags = await equipped_weapon_compatibility_tags(
            session, character.id
        )
    equipped_tags = weapon_compatibility_tags or frozenset()
    seen_slots: set[int] = set()
    seen_arts: set[str] = set()
    snapshots: list[ActiveArtSlotSnapshot] = []
    for row in rows:
        if row.slot not in ACTIVE_ART_SLOTS or row.slot in seen_slots:
            raise ActiveArtConfigurationError("Invalid active-Art slot state.")
        if row.art_id in seen_arts:
            raise ActiveArtConfigurationError("The same Art cannot occupy two active slots.")
        definition = active_art_definition(row.art_id)
        if definition is None:
            raise ActiveArtConfigurationError("Persisted active Art is unknown to the runtime.")
        right_class_and_path = (
            definition.character_class == character.character_class
            and (definition.path_id is None or definition.path_id == character.selected_path)
        )
        dormant_after_legacy = character.legacy_level > 0 and right_class_and_path and (
            character.level < definition.min_level
            or not weapon_requirement_satisfied(definition, equipped_tags)
        )
        if dormant_after_legacy:
            # Keep the saved slot as remembered configuration, but freeze it out of
            # combat snapshots until level and equipment requirements are satisfied.
            seen_slots.add(row.slot)
            seen_arts.add(row.art_id)
            continue
        if validate_eligibility:
            _validate_definition(character, definition)
        if (
            validate_weapon_requirements
            and not weapon_requirement_satisfied(definition, equipped_tags)
        ):
            raise ActiveArtConfigurationError(
                "Equipped Art weapon requirement is not met."
            )
        seen_slots.add(row.slot)
        seen_arts.add(row.art_id)
        snapshots.append(ActiveArtSlotSnapshot(row.slot, row.art_id))
    return ActiveArtConfigurationSnapshot(
        character.combat_configuration_version,
        tuple(snapshots),
    )

class ActiveArtService:
    """Serialize active-Art mutations through Character and the shared combat guard."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> ActiveArtCharacterView | None:
        async with self.sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
            )
            if character is None:
                return None
            compatibility_tags = await equipped_weapon_compatibility_tags(
                session, character.id
            )
            configuration = await load_active_art_configuration(
                session,
                character,
                lock_rows=False,
                weapon_compatibility_tags=compatibility_tags,
                validate_weapon_requirements=False,
                validate_eligibility=False,
            )
            blocker = await find_combat_configuration_blocker(session, character.id)
            available = tuple(
                art_id
                for art_id, definition in ACTIVE_ART_DEFINITIONS.items()
                if definition.character_class == character.character_class
                and character.level >= definition.min_level
                and (definition.path_id is None or definition.path_id == character.selected_path)
            )
            weapon_incompatible = tuple(
                art_id
                for art_id in available
                if not weapon_requirement_satisfied(
                    ACTIVE_ART_DEFINITIONS[art_id], compatibility_tags
                )
            )
            saved_rows = list(
                (
                    await session.scalars(
                        select(CharacterActiveArtSlot.art_id).where(
                            CharacterActiveArtSlot.character_id == character.id
                        )
                    )
                ).all()
            )
            ineligible = tuple(
                art_id
                for art_id in saved_rows
                if (definition := ACTIVE_ART_DEFINITIONS.get(art_id)) is not None
                and (
                    definition.character_class != character.character_class
                    or character.level < definition.min_level
                    or (
                        definition.path_id is not None
                        and definition.path_id != character.selected_path
                    )
                    or not weapon_requirement_satisfied(definition, compatibility_tags)
                )
            )
            return ActiveArtCharacterView(
                character.id,
                character.name,
                character.character_class,
                character.level,
                character.selected_path,
                character.combat_configuration_version,
                configuration.slots,
                available,
                blocker is not None,
                weapon_incompatible,
                ineligible,
            )

    async def equip_art(
        self,
        actor: int,
        slot: int,
        art_id: str,
        *,
        expected_configuration_version: int | None = None,
    ) -> ActiveArtMutationResult | None:
        if slot not in ACTIVE_ART_SLOTS:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.INVALID_SLOT)
        definition = active_art_definition(art_id)
        if definition is None:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.UNKNOWN_ART)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            self._validate_mutation_definition(character, definition)
            rows, current = await self._load_rows(session, character)
            existing_slot = next(
                (current_slot for current_slot, value in current.items() if value == art_id),
                None,
            )
            if existing_slot is not None and existing_slot != slot:
                raise ActiveArtMutationRejected(ActiveArtMutationCode.DUPLICATE_ART)
            if current.get(slot) == art_id:
                return ActiveArtMutationResult(
                    False,
                    slot,
                    art_id,
                    character.combat_configuration_version,
                )
            final = dict(current)
            final[slot] = art_id
            compatibility_tags = await equipped_weapon_compatibility_tags(
                session, character.id
            )
            for final_art_id in final.values():
                final_definition = active_art_definition(final_art_id)
                if final_definition is not None and character.legacy_level > 0 and (
                    character.level < final_definition.min_level
                    or not weapon_requirement_satisfied(final_definition, compatibility_tags)
                ) and (
                    final_definition.character_class == character.character_class
                    and (
                        final_definition.path_id is None
                        or final_definition.path_id == character.selected_path
                    )
                ):
                    continue
                if final_definition is None or weapon_requirement_satisfied(
                    final_definition, compatibility_tags
                ):
                    continue
                code = (
                    ActiveArtMutationCode.WEAPON_REQUIREMENT
                    if final_art_id == art_id
                    else ActiveArtMutationCode.INVALID_CURRENT_CONFIGURATION
                )
                raise ActiveArtMutationRejected(code)
            await self._write_rows(session, character.id, rows, current, final)
            character.combat_configuration_version += 1
            await session.flush()
            return ActiveArtMutationResult(
                True,
                slot,
                art_id,
                character.combat_configuration_version,
            )

    async def unequip_slot(
        self,
        actor: int,
        slot: int,
        *,
        expected_configuration_version: int | None = None,
    ) -> ActiveArtMutationResult | None:
        if slot not in ACTIVE_ART_SLOTS:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.INVALID_SLOT)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            self._check_version(character, expected_configuration_version)
            rows, current = await self._load_rows(
                session, character, allow_ineligible=True
            )
            if slot not in current:
                return ActiveArtMutationResult(
                    False,
                    slot,
                    None,
                    character.combat_configuration_version,
                )
            final = dict(current)
            final.pop(slot)
            await self._write_rows(session, character.id, rows, current, final)
            character.combat_configuration_version += 1
            await session.flush()
            return ActiveArtMutationResult(
                True,
                slot,
                None,
                character.combat_configuration_version,
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
        return await lock_for_combat_configuration_mutation(session, character_id)

    @staticmethod
    def _check_version(character: Character, expected: int | None) -> None:
        if expected is not None and expected != character.combat_configuration_version:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.STALE_CONFIGURATION)

    @staticmethod
    def _validate_mutation_definition(
        character: Character, definition: ActiveArtDefinition
    ) -> None:
        if definition.character_class != character.character_class:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.WRONG_CLASS)
        if character.level < definition.min_level:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.LEVEL_REQUIRED)
        if definition.path_id is not None and character.selected_path != definition.path_id:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.PATH_REQUIRED)

    @staticmethod
    async def _load_rows(
        session: AsyncSession,
        character: Character,
        *,
        allow_ineligible: bool = False,
    ) -> tuple[list[CharacterActiveArtSlot], dict[int, str]]:
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
        current: dict[int, str] = {}
        seen_arts: set[str] = set()
        try:
            for row in rows:
                if row.slot not in ACTIVE_ART_SLOTS or row.slot in current:
                    raise ActiveArtConfigurationError("Invalid active-Art slot state.")
                if row.art_id in seen_arts:
                    raise ActiveArtConfigurationError("Duplicate active Art in persisted state.")
                definition = active_art_definition(row.art_id)
                if definition is None:
                    raise ActiveArtConfigurationError("Unknown persisted active Art.")
                dormant_after_legacy = (
                    character.legacy_level > 0
                    and character.level < definition.min_level
                    and definition.character_class == character.character_class
                    and (
                        definition.path_id is None
                        or definition.path_id == character.selected_path
                    )
                )
                if not allow_ineligible and not dormant_after_legacy:
                    _validate_definition(character, definition)
                current[row.slot] = row.art_id
                seen_arts.add(row.art_id)
        except ActiveArtConfigurationError as exc:
            raise ActiveArtMutationRejected(
                ActiveArtMutationCode.INVALID_CURRENT_CONFIGURATION
            ) from exc
        return rows, current

    @staticmethod
    async def _write_rows(
        session: AsyncSession,
        character_id: UUID,
        rows: list[CharacterActiveArtSlot],
        current: dict[int, str],
        final: dict[int, str],
    ) -> None:
        row_by_slot = {row.slot: row for row in rows}
        for slot, row in row_by_slot.items():
            if final.get(slot) != row.art_id:
                await session.delete(row)
        await session.flush()
        for slot, art_id in sorted(final.items()):
            if current.get(slot) != art_id:
                session.add(
                    CharacterActiveArtSlot(
                        character_id=character_id,
                        slot=slot,
                        art_id=art_id,
                    )
                )
