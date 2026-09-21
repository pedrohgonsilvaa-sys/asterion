from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from asterion.application.p1 import P1Service
from asterion.application.world import WorldService
from asterion.infrastructure.db.models import (
    Account,
    Achievement,
    Brazier,
    Character,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)


def _ids():
    return uuid4(), uuid4()


async def _seed(database, actor=991100):
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
                xp=320,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
                vigor=77,
                max_vigor=100,
            )
        )
        await session.flush()
        session.add(
            Quest(
                character_id=cid,
                quest_id="P1",
                title="Vozes na Estrada",
                status="active",
                step=1,
                content_version="tdo-1.0.2",
            )
        )
        session.add(Brazier(character_id=cid, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=cid, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
        session.add(
            LocationDiscovery(character_id=cid, location_id="tdo.location.estrada_das_cinzas")
        )
        await session.commit()
    return actor, P1Service(sessions, "ocaso")


@pytest.mark.asyncio
async def test_p1_signs_are_ordered_idempotent_and_create_one_foreground(database):
    actor, service = await _seed(database)
    first = await service.follow_road(actor, 0)
    assert first.step == 2
    stale = await service.follow_road(actor, 0)
    assert stale.step == 2 and stale.state_version == 1
    rejected = await service.examine(actor, "sulcos", 1)
    assert rejected.step == 2 and not rejected.progress.get("sulcos")
    tracks = await service.examine(actor, "pegadas", 1)
    assert tracks.progress["pegadas"] is True
    duplicate = await service.examine(actor, "pegadas", 1)
    assert duplicate.state_version == tracks.state_version
    combat = await service.examine(actor, "sulcos", tracks.state_version)
    assert combat.step == 3 and combat.combat is not None
    again = await service.examine(actor, "sulcos", tracks.state_version)
    assert again.step == 3
    assert combat.activity_id != combat.encounter_id != combat.combat_id
    resumed = await service.resume(actor)
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )


@pytest.mark.asyncio
async def test_p1_refuge_codex_and_reward_are_persistent_and_idempotent(database):
    actor, service = await _seed(database, 991101)
    async with database[1]() as session:
        q = await session.scalar(select(Quest).where(Quest.quest_id == "P1"))
        q.step = 4
        q.state_version = 1
        await session.commit()
    view = await service.enter_refuge(actor, 1)
    assert view.step == 5
    assert view.known_locations.count("tdo.location.refugio_do_ocaso") == 1
    view = await service.follow_alda(actor, view.state_version)
    assert view.step == 6
    view = await service.follow_alda(actor, view.state_version)
    assert view.step == 6
    view = await service.go_brazier(actor, view.state_version)
    assert view.step == 7
    view = await service.activate_brazier(actor, view.state_version)
    assert view.status == "completed"
    duplicate = await service.activate_brazier(actor, view.state_version)
    assert duplicate.status == "completed"
    async with database[1]() as session:
        cid = await session.scalar(select(Character.id).where(Character.telegram_id == actor))
        assert (
            await session.scalar(select(RewardEvent).where(RewardEvent.character_id == cid))
        ).source_id == "p1.vozes_na_estrada"
        assert len((await session.scalars(select(RewardComponent).join(RewardEvent))).all()) == 4
        assert (
            len(
                (
                    await session.scalars(
                        select(MaterialStack).where(MaterialStack.character_id == cid)
                    )
                ).all()
            )
            == 2
        )
        assert (
            len((await session.scalars(select(Unlock).where(Unlock.character_id == cid))).all())
            == 2
        )
        assert await session.scalar(
            select(Brazier).where(
                Brazier.character_id == cid, Brazier.brazier_id == "tdo.brazier.refugio_do_ocaso"
            )
        )
        assert not await session.scalar(
            select(Unlock).where(Unlock.character_id == cid, Unlock.unlock_id.like("%ronda%"))
        )


@pytest.mark.asyncio
async def test_enter_refuge_without_world_state_has_no_partial_discovery(database):
    actor, service = await _seed(database, 991102)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P1")
        )
        quest.step = 4
        quest.state_version = 0
        await session.execute(
            delete(WorldState).where(WorldState.character_id == character.id)
        )
        await session.commit()

    view = await service.enter_refuge(actor, 0)
    assert view.step == 4
    assert view.state_version == 0
    async with database[1]() as session:
        assert not await session.scalar(
            select(LocationDiscovery).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == "tdo.location.refugio_do_ocaso",
            )
        )


@pytest.mark.asyncio
async def test_p1_retry_gets_new_ids(database):
    actor, service = await _seed(database, 991102)
    async with database[1]() as session:
        q = await session.scalar(select(Quest).where(Quest.quest_id == "P1"))
        q.step, q.progress, q.state_version = 3, {"defeat": True, "recovery": True}, 9
        await session.commit()
    retry = await service.retry(actor, 9)
    assert retry.combat is not None
    assert retry.combat.fighters["enemy"].name == "Cão Cinéreo"
    assert retry.activity_id and retry.encounter_id and retry.combat_id
    assert retry.combat.fighters["enemy"].stats.hp == Decimal("406")


@pytest.mark.asyncio
async def test_p1_completed_state_reconstructs_post_p1_menu(database):
    actor, service = await _seed(database, 991103)
    async with database[1]() as session:
        cid = await session.scalar(select(Character.id).where(Character.telegram_id == actor))
        q = await session.scalar(select(Quest).where(Quest.quest_id == "P1"))
        q.step, q.status, q.state_version = 7, "active", 3
        session.add(Achievement(character_id=cid, achievement_id="feat.tdo.cinzas_na_estrada"))
        session.add(Brazier(character_id=cid, brazier_id="tdo.brazier.refugio_do_ocaso"))
        world = await session.scalar(select(WorldState).where(WorldState.character_id == cid))
        world.location = "Refúgio do Ocaso"
        await session.commit()
    completed = await service.activate_brazier(actor, 3)
    assert completed.status == "completed"
    menu = await WorldService(database[1], "ocaso").resume(actor)
    assert menu.kind == "menu"
    assert menu.location == "Refúgio do Ocaso"
    assert menu.quest_title is None


@pytest.mark.asyncio
async def test_activate_brazier_rejects_active_foreground(database):
    actor, service = await _seed(database, 991104)
    progressed = await service.follow_road(actor, 0)
    tracks = await service.examine(actor, "pegadas", progressed.state_version)
    await service.examine(actor, "sulcos", tracks.state_version)
    async with database[1]() as session:
        q = await session.scalar(select(Quest).where(Quest.quest_id == "P1"))
        q.step, q.state_version = 7, q.state_version + 1
        version = q.state_version
        await session.commit()
    result = await service.activate_brazier(actor, version)
    assert result.status == "active"
    assert result.combat is not None
