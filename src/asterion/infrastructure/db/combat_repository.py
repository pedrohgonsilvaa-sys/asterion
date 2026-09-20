"""PostgreSQL storage primitives; callers own the encompassing transaction."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.domain.combat import Combat
from asterion.infrastructure.db.combat_codec import encode
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CombatRecord,
    Encounter,
    GameActivity,
    RewardGrant,
)


class CombatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def owned_character(self, actor: int, server_id: str) -> Character | None:
        account = await self.session.scalar(
            select(Account).where(Account.telegram_id == actor).with_for_update()
        )
        if account is None:
            return None
        return await self.session.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == server_id,
            )
            .with_for_update()
        )

    async def activity(self, character: Character, content_id: str) -> GameActivity | None:
        active = await self.session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        )
        if active is not None:
            return active
        return await self.session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == content_id,
            )
        )

    async def combat(self, activity: GameActivity) -> tuple[Encounter, CombatRecord]:
        result = await self.session.execute(
            select(Encounter, CombatRecord)
            .join(CombatRecord)
            .where(
                Encounter.game_activity_id == activity.id,
            )
        )
        return result.one()

    async def create(self, character: Character, content_id: str, state: Combat):
        activity = GameActivity(
            id=uuid4(),
            character_id=character.id,
            content_id=content_id,
            status="active",
            state_version=state.version,
            ruleset_version=state.ruleset,
        )
        self.session.add(activity)
        await self.session.flush()
        encounter = Encounter(id=uuid4(), game_activity_id=activity.id)
        self.session.add(encounter)
        await self.session.flush()
        record = CombatRecord(id=state.id, encounter_id=encounter.id, snapshot=encode(state))
        self.session.add(record)
        await self.session.flush()
        return activity, encounter, record

    async def grant(self, character: Character, activity: GameActivity, xp: int) -> bool:
        granted = await self.session.scalar(
            insert(RewardGrant)
            .values(
                game_activity_id=activity.id,
                character_id=character.id,
                xp=xp,
                ruleset_version=activity.ruleset_version,
            )
            .on_conflict_do_nothing(index_elements=[RewardGrant.game_activity_id])
            .returning(RewardGrant.game_activity_id)
        )
        if granted is not None:
            character.xp += xp
            return True
        return False
