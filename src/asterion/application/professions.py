"""Transactional selection and progression for active character professions."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    find_combat_configuration_blocker,
    lock_for_combat_configuration_mutation,
)
from asterion.domain.professions import (
    PROFESSION_BY_ID,
    PROFESSION_IDS,
    ProfessionSlot,
    apply_profession_pxp,
    profession_change_cost,
    profession_grade,
    required_pxp,
    slot_cap,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterProfession,
    DungeonRun,
    DungeonRunMember,
    WorldState,
)

REFUGE = "Refúgio do Ocaso"
SAFE_PROFESSION_LOCATIONS = frozenset((REFUGE, "Vigília do Vale"))


class ProfessionMutationCode:
    CHARACTER_MISSING = "character_missing"
    INVALID_PROFESSION = "invalid_profession"
    SAME_PROFESSION = "same_profession"
    ALREADY_CONFIGURED = "already_configured"
    NOT_CONFIGURED = "not_configured"
    STALE_PREVIEW = "stale_preview"
    WRONG_LOCATION = "wrong_location"
    FOREGROUND = "foreground"
    INSUFFICIENT_CROWNS = "insufficient_crowns"
    INVALID_OPERATION = "invalid_operation"


class ProfessionMutationRejected(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ProfessionProgress:
    profession_id: str
    slot: str
    level: int
    pxp: int
    next_level_pxp: int | None
    cap: int

    @property
    def grade(self) -> int:
        return profession_grade(self.level)


@dataclass(frozen=True, slots=True)
class ProfessionHomeView:
    character_id: UUID
    character_name: str
    character_level: int
    crowns: int
    location: str | None
    foreground: bool
    primary: ProfessionProgress | None
    secondary: ProfessionProgress | None
    others: tuple[str, ...]
    configured: bool


@dataclass(frozen=True, slots=True)
class ProfessionChangePreview:
    operation: str
    slot: str | None
    profession_id: str | None
    token: str
    cost: int
    lost_level: int
    lost_pxp: int
    location: str | None
    foreground: bool
    crowns: int
    primary: ProfessionProgress | None
    secondary: ProfessionProgress | None
    valid: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProfessionMutationResult:
    operation: str
    primary: ProfessionProgress | None
    secondary: ProfessionProgress | None
    crowns: int


class ProfessionService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> ProfessionHomeView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            rows = await self._rows(session, character.id)
            by_slot = {row.slot: self._progress(row) for row in rows}
            location = await self._location(session, character.id)
            foreground = await self._has_foreground(session, character.id)
            active_ids = {row.profession_id for row in rows}
            return ProfessionHomeView(
                character_id=character.id,
                character_name=character.name,
                character_level=character.level,
                crowns=int(character.crowns),
                location=location,
                foreground=foreground,
                primary=by_slot.get(ProfessionSlot.PRIMARY.value),
                secondary=by_slot.get(ProfessionSlot.SECONDARY.value),
                others=tuple(item for item in PROFESSION_IDS if item not in active_ids),
                configured=bool(rows),
            )

    async def initial_selection(
        self, actor: int, primary_id: str, secondary_id: str
    ) -> ProfessionMutationResult | None:
        if primary_id not in PROFESSION_BY_ID or secondary_id not in PROFESSION_BY_ID:
            raise ProfessionMutationRejected(ProfessionMutationCode.INVALID_PROFESSION)
        if primary_id == secondary_id:
            raise ProfessionMutationRejected(ProfessionMutationCode.SAME_PROFESSION)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            if await self._rows(session, character.id, lock=True):
                raise ProfessionMutationRejected(ProfessionMutationCode.ALREADY_CONFIGURED)
            await self._require_safe_idle(session, character.id)
            session.add_all(
                [
                    CharacterProfession(
                        character_id=character.id,
                        slot=ProfessionSlot.PRIMARY.value,
                        profession_id=primary_id,
                        level=1,
                        pxp=0,
                    ),
                    CharacterProfession(
                        character_id=character.id,
                        slot=ProfessionSlot.SECONDARY.value,
                        profession_id=secondary_id,
                        level=1,
                        pxp=0,
                    ),
                ]
            )
            await session.flush()
            rows = await self._rows(session, character.id)
            return self._result("initial", rows, int(character.crowns))

    async def change_preview(
        self,
        actor: int,
        operation: str,
        *,
        slot: str | None = None,
        profession_id: str | None = None,
    ) -> ProfessionChangePreview | None:
        if operation not in {"swap", "replace"}:
            raise ProfessionMutationRejected(ProfessionMutationCode.INVALID_OPERATION)
        if operation == "replace" and (
            slot not in {item.value for item in ProfessionSlot}
            or profession_id not in PROFESSION_BY_ID
        ):
            raise ProfessionMutationRejected(ProfessionMutationCode.INVALID_OPERATION)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            rows = await self._rows(session, character.id)
            state = {row.slot: row for row in rows}
            primary = self._progress(state.get(ProfessionSlot.PRIMARY.value))
            secondary = self._progress(state.get(ProfessionSlot.SECONDARY.value))
            location = await self._location(session, character.id)
            foreground = await self._has_foreground(session, character.id)
            reason = self._change_reason(
                operation,
                slot,
                profession_id,
                state,
                location,
                foreground,
                int(character.crowns),
                character.level,
            )
            replacement = operation == "replace"
            cost = profession_change_cost(character.level, replacement=replacement)
            lost_level = 0
            lost_pxp = 0
            if operation == "swap" and state:
                old_primary = state.get(ProfessionSlot.PRIMARY.value)
                if old_primary is not None:
                    secondary_cap = slot_cap(ProfessionSlot.SECONDARY)
                    lost_level = max(0, old_primary.level - secondary_cap)
                    lost_pxp = old_primary.pxp if old_primary.level >= secondary_cap else 0
            elif replacement and slot is not None and (old := state.get(slot)) is not None:
                lost_level = old.level - 1
                lost_pxp = old.pxp
            token = self._change_token(character, rows, location, operation, slot, profession_id)
            return ProfessionChangePreview(
                operation=operation,
                slot=slot,
                profession_id=profession_id,
                token=token,
                cost=cost,
                lost_level=max(0, lost_level),
                lost_pxp=lost_pxp,
                location=location,
                foreground=foreground,
                crowns=int(character.crowns),
                primary=primary,
                secondary=secondary,
                valid=reason is None,
                reason=reason,
            )

    async def confirm_change(
        self,
        actor: int,
        token: str,
        operation: str,
        *,
        slot: str | None = None,
        profession_id: str | None = None,
    ) -> ProfessionMutationResult | None:
        if operation not in {"swap", "replace"}:
            raise ProfessionMutationRejected(ProfessionMutationCode.INVALID_OPERATION)
        async with self.sessions.begin() as session:
            character = await self._lock_character(session, actor)
            if character is None:
                return None
            rows = await self._rows(session, character.id, lock=True)
            state = {row.slot: row for row in rows}
            location = await self._location(session, character.id, lock=True)
            current_token = self._change_token(
                character, rows, location, operation, slot, profession_id
            )
            if current_token != token:
                raise ProfessionMutationRejected(ProfessionMutationCode.STALE_PREVIEW)
            reason = self._change_reason(
                operation,
                slot,
                profession_id,
                state,
                location,
                False,
                int(character.crowns),
                character.level,
            )
            if reason == ProfessionMutationCode.FOREGROUND:
                raise ProfessionMutationRejected(reason)
            if reason:
                raise ProfessionMutationRejected(reason)
            await self._require_no_foreground(session, character.id)
            replacement = operation == "replace"
            cost = profession_change_cost(character.level, replacement=replacement)
            if character.crowns < cost:
                raise ProfessionMutationRejected(ProfessionMutationCode.INSUFFICIENT_CROWNS)

            if operation == "swap":
                primary = state[ProfessionSlot.PRIMARY.value]
                secondary = state[ProfessionSlot.SECONDARY.value]
                # A secondary can never retain PXP above its active cap.
                if primary.level >= slot_cap(ProfessionSlot.SECONDARY):
                    primary.level = slot_cap(ProfessionSlot.SECONDARY)
                    primary.pxp = 0
                await session.execute(
                    delete(CharacterProfession).where(
                        CharacterProfession.character_id == character.id
                    )
                )
                session.add_all(
                    [
                        CharacterProfession(
                            character_id=character.id,
                            slot=ProfessionSlot.PRIMARY.value,
                            profession_id=secondary.profession_id,
                            level=secondary.level,
                            pxp=secondary.pxp,
                        ),
                        CharacterProfession(
                            character_id=character.id,
                            slot=ProfessionSlot.SECONDARY.value,
                            profession_id=primary.profession_id,
                            level=primary.level,
                            pxp=primary.pxp,
                        ),
                    ]
                )
            else:
                assert slot is not None and profession_id is not None
                old = state[slot]
                await session.delete(old)
                await session.flush()
                session.add(
                    CharacterProfession(
                        character_id=character.id,
                        slot=slot,
                        profession_id=profession_id,
                        level=1,
                        pxp=0,
                    )
                )
            character.crowns -= cost
            await session.flush()
            result_rows = await self._rows(session, character.id)
            return self._result(operation, result_rows, int(character.crowns))

    async def progress_after_craft(
        self,
        session: AsyncSession,
        character: Character,
        recipe_profession_id: str,
        recipe_level: int,
        recipe_grade: int,
    ) -> tuple[int, int, int] | None:
        rows = await self._rows(session, character.id, lock=True)
        row = next((item for item in rows if item.profession_id == recipe_profession_id), None)
        if row is None:
            return None
        cap = slot_cap(row.slot)
        gained = 0
        from asterion.domain.professions import recipe_pxp

        gained = recipe_pxp(recipe_level, row.level, recipe_grade)
        old_level = row.level
        row.level, row.pxp = apply_profession_pxp(row.level, row.pxp, gained, cap)
        return old_level, row.level, gained

    @staticmethod
    def _progress(row: CharacterProfession | None) -> ProfessionProgress | None:
        if row is None:
            return None
        cap = slot_cap(row.slot)
        next_pxp = required_pxp(row.level) if row.level < cap else None
        return ProfessionProgress(row.profession_id, row.slot, row.level, row.pxp, next_pxp, cap)

    @classmethod
    def _result(
        cls, operation: str, rows: list[CharacterProfession], crowns: int
    ) -> ProfessionMutationResult:
        by_slot = {row.slot: row for row in rows}
        return ProfessionMutationResult(
            operation,
            cls._progress(by_slot.get(ProfessionSlot.PRIMARY.value)),
            cls._progress(by_slot.get(ProfessionSlot.SECONDARY.value)),
            crowns,
        )

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
            raise ProfessionMutationRejected(ProfessionMutationCode.FOREGROUND) from exc

    @staticmethod
    async def _rows(
        session: AsyncSession, character_id: UUID, *, lock: bool = False
    ) -> list[CharacterProfession]:
        statement = (
            select(CharacterProfession)
            .where(CharacterProfession.character_id == character_id)
            .order_by(CharacterProfession.slot)
        )
        if lock:
            statement = statement.with_for_update()
        return list((await session.scalars(statement)).all())

    @staticmethod
    async def _location(
        session: AsyncSession, character_id: UUID, *, lock: bool = False
    ) -> str | None:
        statement = select(WorldState).where(WorldState.character_id == character_id)
        if lock:
            statement = statement.with_for_update()
        world = await session.scalar(statement)
        return world.location if world is not None else None

    @staticmethod
    async def _has_foreground(session: AsyncSession, character_id: UUID) -> bool:
        if await find_combat_configuration_blocker(session, character_id) is not None:
            return True
        active_dungeon = await session.scalar(
            select(DungeonRun.id)
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == character_id,
                DungeonRunMember.status == "active",
                DungeonRun.status == "active",
            )
            .limit(1)
        )
        return active_dungeon is not None

    async def _require_safe_idle(self, session: AsyncSession, character_id: UUID) -> None:
        location = await self._location(session, character_id, lock=True)
        if location not in SAFE_PROFESSION_LOCATIONS:
            raise ProfessionMutationRejected(ProfessionMutationCode.WRONG_LOCATION)
        await self._require_no_foreground(session, character_id)

    async def _require_no_foreground(self, session: AsyncSession, character_id: UUID) -> None:
        if await self._has_foreground(session, character_id):
            raise ProfessionMutationRejected(ProfessionMutationCode.FOREGROUND)

    @staticmethod
    def _change_reason(
        operation, slot, profession_id, state, location, foreground, crowns, character_level
    ):
        if len(state) != 2:
            return ProfessionMutationCode.NOT_CONFIGURED
        if location not in SAFE_PROFESSION_LOCATIONS:
            return ProfessionMutationCode.WRONG_LOCATION
        if foreground:
            return ProfessionMutationCode.FOREGROUND
        if operation == "swap":
            if crowns < profession_change_cost(character_level, replacement=False):
                return ProfessionMutationCode.INSUFFICIENT_CROWNS
            return None
        if slot not in {ProfessionSlot.PRIMARY.value, ProfessionSlot.SECONDARY.value}:
            return ProfessionMutationCode.INVALID_OPERATION
        if profession_id not in PROFESSION_BY_ID:
            return ProfessionMutationCode.INVALID_PROFESSION
        if state[slot].profession_id == profession_id:
            return ProfessionMutationCode.SAME_PROFESSION
        other_slot = (
            ProfessionSlot.SECONDARY.value
            if slot == ProfessionSlot.PRIMARY.value
            else ProfessionSlot.PRIMARY.value
        )
        if state[other_slot].profession_id == profession_id:
            return ProfessionMutationCode.SAME_PROFESSION
        cost = profession_change_cost(character_level, replacement=True)
        if crowns < cost:
            return ProfessionMutationCode.INSUFFICIENT_CROWNS
        return None

    @staticmethod
    def _change_token(character, rows, location, operation, slot, profession_id) -> str:
        payload = {
            "character": str(character.id),
            "level": character.level,
            "crowns": int(character.crowns),
            "location": location,
            "operation": operation,
            "slot": slot,
            "profession_id": profession_id,
            "rows": [
                (row.slot, row.profession_id, row.level, row.pxp)
                for row in sorted(rows, key=lambda item: item.slot)
            ],
        }
        return sha256(dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[
            :12
        ]
