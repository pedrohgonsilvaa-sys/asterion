import pytest
from sqlalchemy import func, select

from asterion.application.bestiary import BestiaryRecorder
from asterion.infrastructure.db.models import Character, RewardComponent, RewardEvent
from tests.test_vde_p12_matriarch_integration import _seed_p12_gate


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("actor", "creature_id", "reference_level", "configured_xp"),
    (
        (998931, "no_feroz", 14, 687),
        (998932, "viuva_cipos", 17, 876),
        (998933, "carrasco_casca", 20, 1086),
    ),
)
async def test_vales_world_elite_first_victory_grants_configured_xp_once(
    database,
    actor,
    creature_id,
    reference_level,
    configured_xp,
):
    character_id, sessions = await _seed_p12_gate(database, actor, level=20)
    recorder = BestiaryRecorder()
    source_id = f"bestiary:first_victory:{character_id}:{creature_id}"

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        initial_xp = character.xp
        await recorder.record(
            session,
            character_id,
            creature_id,
            victory=True,
            elite=True,
            observation_category="elite",
        )
        assert character.xp == initial_xp + configured_xp

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        xp_after_first_victory = character.xp
        await recorder.record(
            session,
            character_id,
            creature_id,
            victory=True,
            elite=True,
            observation_category="elite",
        )
        assert character.xp == xp_after_first_victory

    async with sessions() as session:
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == source_id,
            )
        ) == 1
        component = await session.scalar(
            select(RewardComponent)
            .join(RewardEvent)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == source_id,
                RewardComponent.kind == "bestiary_first_victory_xp",
            )
        )
        assert component is not None
        assert component.item_id == creature_id
        assert component.quantity == configured_xp
        assert component.payload == {
            "reference_level": reference_level,
            "configured_xp": configured_xp,
        }
