"""Persistent post-prologue brazier and menu boundary."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    Character,
    GameActivity,
    Quest,
    WorldState,
)

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
    quest_title: str | None


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
            active_p1 = await session.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id,
                    GameActivity.content_id == "p1_step3_scripted_dog",
                    GameActivity.status == "active",
                )
            )
            if active_p1 is not None:
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
            if c.stage == "menu:ready":
                valid_active = (
                    q is not None
                    and q.status == "active"
                    and q.step >= 1
                    and q.content_version == "tdo-1.0.2"
                    and achievement is not None
                )
                valid_completed = (
                    q is not None
                    and q.status == "completed"
                    and achievement is not None
                    and world.location == "Refúgio do Ocaso"
                )
                if not (valid_active or valid_completed):
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
                quest_title=q.title if q and q.status == "active" else None,
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
                        content_version="tdo-1.0.2",
                    )
                )
                c.stage = "menu:ready"
            elif c.stage == "menu:ready":
                q = await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == c.id, Quest.quest_id == "P1")
                    .with_for_update()
                )
                world = await session.scalar(
                    select(WorldState).where(WorldState.character_id == c.id).with_for_update()
                )
                refuge = await session.scalar(
                    select(Brazier).where(
                        Brazier.character_id == c.id,
                        Brazier.brazier_id == "tdo.brazier.refugio_do_ocaso",
                    )
                )
                if not (
                    q
                    and q.status == "completed"
                    and world
                    and world.location == "Refúgio do Ocaso"
                    and refuge
                ):
                    return await self.resume(actor)
                c.hp = c.max_hp
            else:
                return None
        return await self.resume(actor)
