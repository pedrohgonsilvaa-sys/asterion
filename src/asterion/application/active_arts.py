"""Authoritative persistence and validation for the three active-Art slots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    lock_for_combat_configuration_mutation,
)
from asterion.domain.arts import ActiveArtDefinition, active_art_definition
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


def _validate_definition(character: Character, definition: ActiveArtDefinition) -> None:
    if definition.character_class != character.character_class:
        raise ActiveArtConfigurationError("Equipped Art does not belong to the character Class.")
    if character.level < definition.min_level:
        raise ActiveArtConfigurationError("Equipped Art level requirement is not met.")
    # Path selection is not persisted by the current repository yet. Keep the
    # authoritative hook explicit and fail closed when path Arts are introduced.
    if definition.path_id is not None:
        raise ActiveArtConfigurationError("Path-backed Arts require authoritative Path state.")


async def load_active_art_configuration(
    session: AsyncSession,
    character: Character,
    *,
    lock_rows: bool = True,
) -> ActiveArtConfigurationSnapshot:
    """Load the character's persisted active Arts in slot order and validate them."""
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
        _validate_definition(character, definition)
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
            rows, current = await self._load_rows(session, character)
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
        if definition.path_id is not None:
            raise ActiveArtMutationRejected(ActiveArtMutationCode.PATH_REQUIRED)

    @staticmethod
    async def _load_rows(
        session: AsyncSession, character: Character
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
