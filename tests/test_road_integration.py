from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.road import ROAD, RoadService
from asterion.domain.combat import allowed_actions
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    Character,
    MaterialStack,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)


async def _seed_road(database, actor=771100, vigor=100):
    _, sessions = database
    cid = uuid4()
    async with sessions() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=cid,
                telegram_id=actor,
                server_id="ocaso",
                name="Heroa",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.3-baseline-1.0",
                level=1,
                xp=2720,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
                vigor=vigor,
                max_vigor=100,
                crowns=0,
            )
        )
        await session.flush()
        session.add_all(
            [
                Brazier(character_id=cid, brazier_id="tdo.brazier.estrada"),
                Brazier(character_id=cid, brazier_id="tdo.brazier.refugio_do_ocaso"),
                WorldState(character_id=cid, region="Terras do Ocaso", location="Refúgio do Ocaso"),
                Unlock(character_id=cid, unlock_id="hunt_manual.estrada_das_cinzas"),
                Unlock(character_id=cid, unlock_id="explore.estrada_das_cinzas"),
            ]
        )
        await session.commit()
    return actor, RoadService(sessions, "ocaso")


@pytest.mark.asyncio
async def test_road_travel_and_hunt_reconnect_are_persistent(database):
    actor, service = await _seed_road(database)
    refuge = await service.resume(actor)
    assert refuge.kind == "refuge"
    road = await service.travel(actor, ROAD)
    assert road.kind == "road"
    assert road.location == ROAD
    combat = await service.start_hunt(actor)
    assert combat.kind == "combat"
    assert combat.activity_id != combat.encounter_id != combat.combat_id
    resumed = await service.resume(actor)
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    assert set(allowed_actions(resumed.combat)) >= {"attack", "defend", "art"}


@pytest.mark.asyncio
async def test_hunt_victory_receipt_reconstructs_without_duplicate_reward(database):
    actor, service = await _seed_road(database, 771104)
    await service.travel(actor, ROAD)
    view = await service.start_hunt(actor)
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    assert view.kind == "hunt_victory"
    receipt = (view.creature, view.variant, view.reward_lines)
    resumed = await service.resume(actor)
    assert resumed.kind == "hunt_victory"
    assert (resumed.creature, resumed.variant, resumed.reward_lines) == receipt
    await service.acknowledge_result(actor)
    assert (await service.resume(actor)).kind == "road"


@pytest.mark.asyncio
async def test_road_exploration_result_is_persisted_once(database):
    actor, service = await _seed_road(database, 771101)
    await service.travel(actor, ROAD)
    first = await service.explore(actor)
    assert first.kind in {"exploration", "combat"}
    async with database[1]() as session:
        from asterion.infrastructure.db.models import ExplorationAttempt

        attempts = (await session.scalars(select(ExplorationAttempt))).all()
        assert len(attempts) == 1
        assert attempts[0].seed


@pytest.mark.asyncio
async def test_exploration_combat_pays_xp_crowns_material_and_vigor(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771102, vigor=100)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("combat", "explore.tdo.estrada.combat.dog_cinereo", "Cão"),
    )
    view = await service.explore(actor)
    assert view.kind == "combat"
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    assert view.kind == "exploration"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2960
        assert character.crowns == 20
        assert character.vigor == 96
        assert (await session.scalar(select(func.count(RewardEvent.id)).where(
            RewardEvent.character_id == character.id,
            RewardEvent.source_id == f"explore:{view.attempt_id}",
        ))) == 1
        assert (await session.scalar(select(func.count(RewardComponent.id)).join(RewardEvent).where(
            RewardEvent.character_id == character.id,
            RewardEvent.source_id == f"explore:{view.attempt_id}",
        ))) >= 2
        assert (
            await session.scalar(
                select(func.count(MaterialStack.id)).where(
                    MaterialStack.character_id == character.id
                )
            )
        ) >= 1


@pytest.mark.asyncio
async def test_exploration_combat_with_low_vigor_only_pays_quarter_xp(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771103, vigor=3)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("combat", "explore.tdo.estrada.combat.dog_cinereo", "Cão"),
    )
    view = await service.explore(actor)
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2780
        assert character.crowns == 0
        assert character.vigor == 3
        assert (await session.scalar(select(func.count(MaterialStack.id)).where(
            MaterialStack.character_id == character.id
        ))) == 0
