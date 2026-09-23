from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from asterion.application.round import (
    HEAL_CONSUMABLE,
    PURIFY_CONSUMABLE,
    RoundService,
)
from asterion.application.road import ROAD
from asterion.domain.road import CREATURES, ROUND_FAMILIARITY
from asterion.infrastructure.db.models import (
    Character,
    ConsumableStack,
    GameActivity,
    HuntRound,
    HuntRoundEncounter,
    RewardEvent,
    Unlock,
)
from tests.test_road_integration import _seed_road


async def _seed_round(database, actor: int, *, vigor: int = 100):
    await _seed_road(database, actor, vigor=vigor)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(Unlock(character_id=character.id, unlock_id=ROUND_FAMILIARITY))
        await session.commit()
    service = RoundService(sessions, "ocaso")
    await service.travel(actor, ROAD)
    return actor, service


@pytest.mark.asyncio
async def test_round_preparation_consumables_and_reconnect_are_persistent(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772001)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level: CREATURES[0])

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                ConsumableStack(
                    character_id=character.id,
                    consumable_id=HEAL_CONSUMABLE,
                    quantity=4,
                ),
                ConsumableStack(
                    character_id=character.id,
                    consumable_id=PURIFY_CONSUMABLE,
                    quantity=2,
                ),
            ]
        )
        await session.commit()

    prepared = await service.prepare_round(actor, 5)
    assert prepared.kind == "round_prepare"
    consumables = await service.round_consumables(
        actor, prepared.round_id, prepared.state_version
    )
    assert (consumables.heal_quantity, consumables.purify_quantity) == (4, 2)

    toggled = await service.toggle_round_consumable(
        actor,
        prepared.round_id,
        consumables.state_version,
        HEAL_CONSUMABLE,
    )
    assert toggled.prepared_heal is True
    started = await service.start_round(actor, toggled.round_id, toggled.state_version)
    assert started.kind == "round_active"
    assert started.prepared_heal is True
    assert started.completed_encounters == 0
    assert started.next_resolution_at is not None

    resumed = await service.resume(actor)
    assert resumed.kind == "round_active"
    assert resumed.round_id == started.round_id
    assert resumed.encounter_id == started.encounter_id

    stale = await service.start_round(actor, toggled.round_id, toggled.state_version)
    assert stale.kind == "round_active"
    async with database[1]() as session:
        assert (
            await session.scalar(select(func.count(HuntRound.id)))
        ) == 1
        assert (
            await session.scalar(select(func.count(HuntRoundEncounter.id)))
        ) == 1


@pytest.mark.asyncio
async def test_round_resolves_due_encounter_once_and_charges_two_vigor(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772002)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level: CREATURES[0])
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    assert await service.advance_due_rounds() == 1
    resumed = await service.resume(actor)
    assert resumed.kind == "round_active"
    assert resumed.completed_encounters == 1
    assert resumed.vigor == 98

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter)
                .where(HuntRoundEncounter.round_id == state.id)
                .order_by(HuntRoundEncounter.ordinal)
            )
        ).all()
        assert [row.ordinal for row in encounters] == [1, 2]
        assert encounters[0].status == "completed"
        assert encounters[1].status == "materialized"
        first_activity = encounters[0].activity_id
        assert first_activity is not None
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.source_id == f"activity:{first_activity}"
            )
        ) == 1


@pytest.mark.asyncio
async def test_cancel_during_materialized_encounter_waits_for_boundary(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772003)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level: CREATURES[0])
    prepared = await service.prepare_round(actor, 10)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)

    cancellation = await service.cancel_round(
        actor, started.round_id, started.state_version
    )
    assert cancellation.kind == "round_active"
    assert cancellation.cancel_requested is True

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    await service.advance_due_rounds()
    result = await service.resume(actor)
    assert result.kind == "round_cancelled"
    assert result.completed_encounters == 1
    assert result.reward_lines
    async with database[1]() as session:
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter).where(
                    HuntRoundEncounter.round_id == started.round_id
                )
            )
        ).all()
        assert len(encounters) == 1


@pytest.mark.asyncio
async def test_vigor_ending_happens_before_next_encounter_is_created(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772004, vigor=2)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level: CREATURES[0])
    prepared = await service.prepare_round(actor, 5)
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)

    async with database[1]() as session:
        state = await session.scalar(select(HuntRound).where(HuntRound.id == started.round_id))
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    await service.advance_due_rounds()
    result = await service.resume(actor)
    assert result.kind == "round_ended"
    assert result.end_reason == "vigor"
    assert result.completed_encounters == 1
    assert result.vigor == 0
    async with database[1]() as session:
        count = await session.scalar(
            select(func.count(HuntRoundEncounter.id)).where(
                HuntRoundEncounter.round_id == started.round_id
            )
        )
        assert count == 1


@pytest.mark.asyncio
async def test_elite_interrupts_before_auto_combat_and_reuses_encounter_id(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772005)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level: CREATURES[3])
    prepared = await service.prepare_round(actor, 5)
    interrupted = await service.start_round(actor, prepared.round_id, prepared.state_version)

    assert interrupted.kind == "round_interrupted"
    assert interrupted.completed_encounters == 0
    assert interrupted.creature == "Alfa Cinéreo"
    persisted_encounter_id = interrupted.encounter_id

    reopened = await service.resume(actor)
    assert reopened.kind == "round_interrupted"
    assert reopened.encounter_id == persisted_encounter_id

    combat = await service.engage_round_elite(
        actor, interrupted.round_id, interrupted.state_version
    )
    assert combat.kind == "combat"
    assert combat.encounter_id == persisted_encounter_id

    stale = await service.engage_round_elite(
        actor, interrupted.round_id, interrupted.state_version
    )
    assert stale.kind == "combat"
    assert stale.encounter_id == persisted_encounter_id

    async with database[1]() as session:
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == interrupted.round_id)
        )
        assert state.status == "ended"
        assert state.end_reason == "elite_engaged"
        assert state.result_acknowledged is True
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == interrupted.character_id,
                GameActivity.status == "active",
            )
        ) == 1


@pytest.mark.asyncio
async def test_terminal_round_result_acknowledges_without_restarting_batch(database, monkeypatch):
    import asterion.application.round as round_module

    actor, service = await _seed_round(database, 772006, vigor=0)
    monkeypatch.setattr(round_module, "select_creature", lambda seed, level: CREATURES[0])
    prepared = await service.prepare_round(actor, 5)
    result = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert result.kind == "round_ended"
    assert result.end_reason == "vigor"

    back = await service.round_back(actor, result.round_id)
    assert back.kind == "hunt_prepare"
    resumed = await service.resume(actor)
    assert resumed.kind == "road"
