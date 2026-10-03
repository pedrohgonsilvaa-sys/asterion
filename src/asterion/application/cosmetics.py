"""Persistent collection and selection of presentation-only cosmetics."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.cosmetic_catalog import (
    COSMETIC_TYPES,
    COSMETICS,
    COSMETICS_BY_ID,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterCosmetic,
    CharacterCosmeticSelection,
)


@dataclass(frozen=True, slots=True)
class CosmeticItemView:
    cosmetic_id: str
    cosmetic_type: str
    name: str
    source_achievement_id: str


@dataclass(frozen=True, slots=True)
class CosmeticCategoryView:
    cosmetic_type: str
    selected: CosmeticItemView | None
    items: tuple[CosmeticItemView, ...]


@dataclass(frozen=True, slots=True)
class CosmeticsView:
    character_name: str
    categories: tuple[CosmeticCategoryView, ...]


@dataclass(frozen=True, slots=True)
class CosmeticSelectionResult:
    changed: bool
    view: CosmeticsView


class CosmeticMutationRejected(RuntimeError):
    pass


class CosmeticService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id

    async def view(self, actor: int) -> CosmeticsView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view(session, character)

    async def select(
        self,
        actor: int,
        cosmetic_id: str,
        expected_selected_id: str | None,
    ) -> CosmeticSelectionResult | None:
        definition = COSMETICS_BY_ID.get(cosmetic_id)
        if definition is None:
            raise CosmeticMutationRejected("unknown_cosmetic")
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            if character is None:
                return None
            owned = await session.scalar(
                select(CharacterCosmetic.cosmetic_id).where(
                    CharacterCosmetic.character_id == character.id,
                    CharacterCosmetic.cosmetic_id == cosmetic_id,
                    CharacterCosmetic.cosmetic_type == definition.cosmetic_type,
                )
            )
            if owned is None:
                raise CosmeticMutationRejected("cosmetic_not_owned")
            current = await session.scalar(
                select(CharacterCosmeticSelection.cosmetic_id)
                .where(
                    CharacterCosmeticSelection.character_id == character.id,
                    CharacterCosmeticSelection.cosmetic_type == definition.cosmetic_type,
                )
                .with_for_update()
            )
            if current != expected_selected_id:
                raise CosmeticMutationRejected("stale_selection")
            if current == cosmetic_id:
                return CosmeticSelectionResult(False, await self._view(session, character))
            await session.execute(
                pg_insert(CharacterCosmeticSelection)
                .values(
                    character_id=character.id,
                    cosmetic_type=definition.cosmetic_type,
                    cosmetic_id=cosmetic_id,
                )
                .on_conflict_do_update(
                    index_elements=[
                        CharacterCosmeticSelection.character_id,
                        CharacterCosmeticSelection.cosmetic_type,
                    ],
                    set_={"cosmetic_id": cosmetic_id},
                )
            )
            return CosmeticSelectionResult(True, await self._view(session, character))

    async def _character(
        self, session: AsyncSession, actor: int, *, lock: bool = False
    ) -> Character | None:
        statement = select(Character).where(
            Character.telegram_id == actor,
            Character.server_id == self.server_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    async def _view(self, session: AsyncSession, character: Character) -> CosmeticsView:
        owned_rows = list(
            (
                await session.scalars(
                    select(CharacterCosmetic)
                    .where(CharacterCosmetic.character_id == character.id)
                    .order_by(CharacterCosmetic.cosmetic_id)
                )
            ).all()
        )
        owned = {row.cosmetic_id: row for row in owned_rows if row.cosmetic_id in COSMETICS_BY_ID}
        selected_rows = list(
            (
                await session.scalars(
                    select(CharacterCosmeticSelection).where(
                        CharacterCosmeticSelection.character_id == character.id
                    )
                )
            ).all()
        )
        selected_by_type = {row.cosmetic_type: row.cosmetic_id for row in selected_rows}

        def item_view(cosmetic_id: str) -> CosmeticItemView:
            definition = COSMETICS_BY_ID[cosmetic_id]
            return CosmeticItemView(
                cosmetic_id=cosmetic_id,
                cosmetic_type=definition.cosmetic_type,
                name=definition.name,
                source_achievement_id=definition.achievement_id,
            )

        categories = []
        for cosmetic_type in COSMETIC_TYPES:
            selected_id = selected_by_type.get(cosmetic_type)
            selected = (
                item_view(selected_id)
                if selected_id in owned
                and COSMETICS_BY_ID[selected_id].cosmetic_type == cosmetic_type
                else None
            )
            items = tuple(
                item_view(definition.cosmetic_id)
                for definition in COSMETICS
                if definition.cosmetic_type == cosmetic_type
                and definition.cosmetic_id in owned
                and definition.cosmetic_id != selected_id
            )
            categories.append(CosmeticCategoryView(cosmetic_type, selected, items))
        return CosmeticsView(character.name, tuple(categories))
