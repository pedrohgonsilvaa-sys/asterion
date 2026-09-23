import pytest
from sqlalchemy import select

from asterion.application.s1 import S1Service
from asterion.application.world import WorldService
from asterion.infrastructure.db.models import Achievement, Character
from tests.test_road_integration import _seed_road


@pytest.mark.asyncio
async def test_tracked_s1_appears_in_world_hud_with_real_level_and_xp_goal(database):
    actor = 774101
    await _seed_road(database, actor)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.level = 2
        character.xp = 321
        session.add(
            Achievement(
                character_id=character.id,
                achievement_id="feat.tdo.cinzas_na_estrada",
            )
        )
        await session.commit()

    s1 = S1Service(sessions, "ocaso")
    accepted = await s1.accept(actor)
    tracked = await s1.toggle_tracking(actor, accepted.state_version)
    assert tracked.tracked is True

    world = await WorldService(sessions, "ocaso").resume(actor)
    assert world is not None
    assert world.level == 2
    assert world.xp == 321
    assert world.xp_required == 5672
    assert world.tracked_secondary_quest_title == "Luzes sob as Cinzas"
