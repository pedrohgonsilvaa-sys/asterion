"""Persistent post-prologue brazier and menu boundary."""

from dataclasses import dataclass
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
    hp: int
    max_hp: int
    vigor: int
    max_vigor: int
    xp: int
    region: str = "Terras do Ocaso"
    location: str = "Estrada das Cinzas"
    quest_title: str | None = None


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
            q = await session.scalar(
                select(Quest).where(Quest.character_id == c.id, Quest.quest_id == "P1")
            )
            return WorldView(
                "menu" if c.stage == "menu:ready" else "brazier",
                c.id,
                c.name,
                c.race,
                c.character_class,
                int(c.hp),
                int(c.max_hp),
                c.vigor,
                c.max_vigor,
                c.xp,
                quest_title=q.title if q else None,
            )

    async def rest(self, actor: int) -> WorldView | None:
        async with self.sessions.begin() as session:
            c = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if c is None or c.stage not in {
                "cinzas_na_estrada:ready_for_first_brazier",
                "menu:ready",
            }:
                return None
            c.hp = c.max_hp
            if (
                await session.scalar(
                    select(Brazier).where(
                        Brazier.character_id == c.id, Brazier.brazier_id == BRAZIER_ID
                    )
                )
                is None
            ):
                session.add(Brazier(character_id=c.id, brazier_id=BRAZIER_ID))
            if (
                await session.scalar(
                    select(Achievement).where(
                        Achievement.character_id == c.id,
                        Achievement.achievement_id == ACHIEVEMENT_ID,
                    )
                )
                is None
            ):
                session.add(Achievement(character_id=c.id, achievement_id=ACHIEVEMENT_ID))
            if (
                await session.scalar(
                    select(Quest).where(Quest.character_id == c.id, Quest.quest_id == "P1")
                )
                is None
            ):
                session.add(
                    Quest(
                        character_id=c.id,
                        quest_id="P1",
                        title="Vozes na Estrada",
                        status="active",
                        step=1,
                    )
                )
            if (
                await session.scalar(select(WorldState).where(WorldState.character_id == c.id))
                is None
            ):
                session.add(
                    WorldState(
                        character_id=c.id, region="Terras do Ocaso", location="Estrada das Cinzas"
                    )
                )
            c.stage = "menu:ready"
        return await self.resume(actor)
