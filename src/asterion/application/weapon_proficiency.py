"""Proficiências de Armas: persistence, equip eligibility and the Treinador de Armas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.weapon_metadata import resolve_equipment_weapon
from asterion.domain.equipment import EquipmentSlot, assignment_for_item_slot
from asterion.domain.weapon_proficiency import (
    IDENTITY_FAMILY,
    INITIAL_PROFICIENCY,
    AcquisitionTerms,
    ProficiencyFamily,
    WeaponIdentity,
    acquisition_terms,
    class_allows_identity,
    learnable_families,
    parse_family,
    weapon_identity_for_type,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterWeaponProficiency,
    EquipmentItem,
    WorldState,
)

TRAINER_LOCATION = "Refúgio do Ocaso"
_WEAPON_SLOTS = frozenset({EquipmentSlot.PRINCIPAL, EquipmentSlot.SECUNDARIA})


class WeaponEligibility(StrEnum):
    ALLOWED = "allowed"
    UNMAPPED = "unmapped"
    NOT_TRAINED = "not_trained"
    CLASS_FORBIDDEN = "class_forbidden"


async def owned_families(
    session: AsyncSession, character_id: UUID
) -> frozenset[ProficiencyFamily]:
    rows = await session.scalars(
        select(CharacterWeaponProficiency.family).where(
            CharacterWeaponProficiency.character_id == character_id
        )
    )
    return frozenset(
        family for value in rows.all() if (family := parse_family(value)) is not None
    )


async def grant_initial_proficiency(session: AsyncSession, character: Character) -> None:
    """Idempotently persist the free creation Proficiência of the Classe."""
    family = INITIAL_PROFICIENCY.get(character.character_class or "")
    if family is None:
        return
    await session.execute(
        insert(CharacterWeaponProficiency)
        .values(
            character_id=character.id,
            family=family.value,
            ordinal=1,
            source="initial",
            cost_crowns=0,
        )
        .on_conflict_do_nothing()
    )


async def item_weapon_identity(
    session: AsyncSession, item: EquipmentItem
) -> tuple[bool, WeaponIdentity | None]:
    """Return (is_weapon_slot, identity). Identity comes only from weapon_type_id."""
    assignment = assignment_for_item_slot(item.slot)
    if assignment is None or assignment.slot not in _WEAPON_SLOTS:
        return False, None
    definition = await resolve_equipment_weapon(session, item)
    if definition is None:
        return True, None
    return True, weapon_identity_for_type(definition.weapon_type_id)


async def weapon_eligibility(
    session: AsyncSession,
    character: Character,
    item: EquipmentItem,
    owned: frozenset[ProficiencyFamily] | None = None,
) -> WeaponEligibility:
    """Proficiência first, then the concrete Classe whitelist (spec §14 steps 6-7)."""
    is_weapon, identity = await item_weapon_identity(session, item)
    if not is_weapon:
        return WeaponEligibility.ALLOWED
    if identity is None:
        return WeaponEligibility.UNMAPPED
    if owned is None:
        owned = await owned_families(session, character.id)
    if IDENTITY_FAMILY[identity] not in owned:
        return WeaponEligibility.NOT_TRAINED
    if not class_allows_identity(character.character_class, identity):
        return WeaponEligibility.CLASS_FORBIDDEN
    return WeaponEligibility.ALLOWED


class TrainingRejected(StrEnum):
    UNKNOWN_FAMILY = "unknown_family"
    NOT_LEARNABLE = "not_learnable"
    LOCATION_REQUIRED = "location_required"
    LEVEL_REQUIRED = "level_required"
    NOT_ENOUGH_CROWNS = "not_enough_crowns"


@dataclass(frozen=True, slots=True)
class TrainerEntry:
    family: ProficiencyFamily
    owned: bool


@dataclass(frozen=True, slots=True)
class TrainerView:
    character_class: str
    level: int
    crowns: int
    at_trainer: bool
    next_terms: AcquisitionTerms
    entries: tuple[TrainerEntry, ...]


@dataclass(frozen=True, slots=True)
class TrainingOutcome:
    learned: bool
    already_owned: bool
    reason: TrainingRejected | None
    view: TrainerView


class WeaponTrainerService:
    """Permanent purchase of Proficiências. Character is locked first, like equip."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> TrainerView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor, lock=False)
            if character is None:
                return None
            return await self._view(session, character)

    async def learn(self, actor: int, family_value: str) -> TrainingOutcome | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            await grant_initial_proficiency(session, character)
            owned = await owned_families(session, character.id)
            family = parse_family(family_value)
            reason: TrainingRejected | None = None
            if family is None:
                reason = TrainingRejected.UNKNOWN_FAMILY
            elif family in owned:
                view = await self._view(session, character)
                return TrainingOutcome(False, True, None, view)
            elif family not in learnable_families(character.character_class):
                reason = TrainingRejected.NOT_LEARNABLE
            elif await self._location(session, character.id) != TRAINER_LOCATION:
                reason = TrainingRejected.LOCATION_REQUIRED
            else:
                terms = acquisition_terms(len(owned) + 1)
                if character.level < terms.min_level:
                    reason = TrainingRejected.LEVEL_REQUIRED
                elif character.crowns < terms.cost_crowns:
                    reason = TrainingRejected.NOT_ENOUGH_CROWNS
                else:
                    character.crowns -= terms.cost_crowns
                    session.add(
                        CharacterWeaponProficiency(
                            character_id=character.id,
                            family=family.value,
                            ordinal=terms.ordinal,
                            source="trainer",
                            cost_crowns=terms.cost_crowns,
                        )
                    )
                    await session.flush()
            view = await self._view(session, character)
            return TrainingOutcome(reason is None, False, reason, view)

    async def _view(self, session: AsyncSession, character: Character) -> TrainerView:
        owned = await owned_families(session, character.id)
        location = await self._location(session, character.id)
        return TrainerView(
            character_class=character.character_class or "",
            level=character.level,
            crowns=character.crowns,
            at_trainer=location == TRAINER_LOCATION,
            next_terms=acquisition_terms(max(1, len(owned) + 1)),
            entries=tuple(
                TrainerEntry(family, family in owned)
                for family in learnable_families(character.character_class)
            ),
        )

    @staticmethod
    async def _location(session: AsyncSession, character_id: UUID) -> str | None:
        return await session.scalar(
            select(WorldState.location).where(WorldState.character_id == character_id)
        )

    async def _character(
        self, session: AsyncSession, actor: int, *, lock: bool
    ) -> Character | None:
        statement = select(Character).where(
            Character.telegram_id == actor, Character.server_id == self.server_id
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)
