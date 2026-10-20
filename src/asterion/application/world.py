"""Persistent post-prologue brazier and menu boundary."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.progression import level_xp
from asterion.application.vigor import reconcile_character_vigor
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
    level: int = 1
    xp_required: int = 4800
    tracked_secondary_quest_title: str | None = None


class WorldService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id

    async def principal_quest_title(self, actor: int) -> str | None:
        """Return the active principal quest persisted for the player's character."""
        async with self.sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
            )
            if character is None:
                return None
            quests = (
                await session.scalars(
                    select(Quest).where(
                        Quest.character_id == character.id,
                        Quest.quest_id.in_(("P1", "P2", "P3", "P4", "P5", "P6")),
                        Quest.status == "active",
                    )
                )
            ).all()
            if not quests:
                return None
            # Principal progression is linear; if legacy data has multiple active
            # rows, show the furthest authored step rather than a stale predecessor.
            rank = {f"P{level}": level for level in range(1, 7)}
            return max(quests, key=lambda quest: rank[quest.quest_id]).title

    async def resume(self, actor: int) -> WorldView | None:
        async with self.sessions.begin() as session:
            c = await session.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if c is not None:
                await reconcile_character_vigor(session, c)
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
            tracked_secondary = None
            if c.tracked_secondary_quest_id:
                tracked_secondary = await session.scalar(
                    select(Quest).where(
                        Quest.character_id == c.id,
                        Quest.quest_id == c.tracked_secondary_quest_id,
                        Quest.status == "active",
                    )
                )
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
                level=c.level,
                xp_required=level_xp(c.level) if c.level < 60 else 0,
                tracked_secondary_quest_title=(
                    tracked_secondary.title if tracked_secondary is not None else None
                ),
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
                await reconcile_character_vigor(session, c)
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
                from asterion.application.tdo_feats import reconcile_tdo_feats

                await reconcile_tdo_feats(session, c)
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
            elif c.stage != "menu:ready":
                return None
            # The legacy callback only reconstructs the current view for a
            # ready character. Permanent rest is authorized by RoadService.
        return await self.resume(actor)
