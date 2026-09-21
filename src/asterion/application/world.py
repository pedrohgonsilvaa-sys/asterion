"""Persistent post-prologue brazier and menu boundary."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.infrastructure.db.models import Achievement, Brazier, Character, Quest, WorldState

BRAZIER_ID = "tdo.brazier.estrada"
ACHIEVEMENT_ID = "feat.tdo.cinzas_na_estrada"


@dataclass(frozen=True)
class WorldView:
    kind: str
    character_id: UUID
    name: str
    race: str
    character_class: str
    hp: Decimal
    max_hp: Decimal
    vigor: int
    max_vigor: int
    xp: int
    region: str
    location: str
    quest_title: str


class WorldService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id

    async def resume(self, actor: int) -> WorldView | None:
        async with self.sessions() as session:
            c = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if c is None or c.stage not in {
                "cinzas_na_estrada:ready_for_first_brazier",
                "menu:ready",
            }:
                return None
            brazier = await session.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id, Brazier.brazier_id == BRAZIER_ID
                )
            )
            world = await session.scalar(select(WorldState).where(WorldState.character_id == c.id))
            if brazier is None or world is None:
                return None
            q = await session.scalar(
                select(Quest).where(Quest.character_id == c.id, Quest.quest_id == "P1")
            )
            achievement = await session.scalar(
                select(Achievement).where(
                    Achievement.character_id == c.id, Achievement.achievement_id == ACHIEVEMENT_ID
                )
            )
            if c.stage == "menu:ready" and (
                q is None
                or q.status != "active"
                or q.step < 1
                or q.content_version != "tdo-1.0.1"
                or achievement is None
            ):
                return None
            return WorldView(
                "menu" if c.stage == "menu:ready" else "brazier",
                c.id,
                c.name,
                c.race,
                c.character_class,
                c.hp,
                c.max_hp,
                c.vigor,
                c.max_vigor,
                c.xp,
                region=world.region,
                location=world.location,
                quest_title=q.title if q else None,
            )

    async def rest(self, actor: int) -> WorldView | None:
        async with self.sessions.begin() as session:
            c = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if c is None:
                return None
            if c.stage == "cinzas_na_estrada:ready_for_first_brazier":
                brazier = await session.scalar(
                    select(Brazier).where(
                        Brazier.character_id == c.id, Brazier.brazier_id == BRAZIER_ID
                    )
                )
                world = await session.scalar(
                    select(WorldState).where(WorldState.character_id == c.id)
                )
                if brazier is None or world is None:
                    return None
                c.hp = c.max_hp
                session.add(Achievement(character_id=c.id, achievement_id=ACHIEVEMENT_ID))
                session.add(
                    Quest(
                        character_id=c.id,
                        quest_id="P1",
                        title="Vozes na Estrada",
                        status="active",
                        step=1,
                        content_version="tdo-1.0.1",
                    )
                )
                c.stage = "menu:ready"
            elif c.stage != "menu:ready":
                return None
        return await self.resume(actor)
