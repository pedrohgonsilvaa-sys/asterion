"""Falar com NPC, Leituras and Desbravar of the Crônica on PostgreSQL (§0.3, §2, §8)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.chronicle import ChronicleAdmin, ChronicleError, record_repeatable
from asterion.application.chronicle_activities import (
    ChronicleActivityService,
    desbravar_offer,
)
from asterion.application.road import RoadService
from asterion.domain.chronicle import calendar_for
from asterion.domain.chronicle_content import (
    NARETH,
    OCASO,
    VALES,
    VESTIGIO_RESULT,
)
from asterion.domain.road import (
    EXPLORATION_PROFILES,
    EXPLORE_UNLOCK,
    NARETH_CAMPINAS_LOCATION,
    ROAD_LOCATION,
    VDE_GARGANTA_LOCATION,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    ChronicleCompletion,
    ChroniclePointGrant,
    ExplorationAttempt,
    Quest,
    Unlock,
    WorldState,
)

SERVER = "ocaso"
DAY1 = date(2026, 12, 1)
CAL = calendar_for(DAY1)
BEFORE = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
WEEK1 = CAL.starts_at + timedelta(hours=1)
WEEK3 = CAL.chapter_opens_at(3) + timedelta(hours=1)
WEEK4 = CAL.chapter_opens_at(4) + timedelta(hours=1)
ANA = 940001
REFUGE = "Refúgio do Ocaso"
ROAD = "Estrada das Cinzas"


async def _make(database, actor=ANA, *, p1=True, level=10, location=REFUGE, region=OCASO):
    async with database[1].begin() as session:
        await session.merge(Account(telegram_id=actor))
        character = Character(
            telegram_id=actor,
            server_id=SERVER,
            name="Ana",
            race="remanescente",
            character_class="sentinela",
            stage="menu",
            ruleset_version="tdo-1.0.15",
            level=level,
            hp=Decimal("100"),
            max_hp=Decimal("100"),
            created_at=BEFORE,
        )
        session.add(character)
        await session.flush()
        session.add(WorldState(character_id=character.id, region=region, location=location))
        if p1:
            session.add(
                Quest(character_id=character.id, quest_id="P1", title="P1", status="completed")
            )
        return character.id


async def _schedule(database, day1=DAY1, now=BEFORE):
    await ChronicleAdmin(database[1], SERVER).set_day1(day1, "teste", now=now)


def _resolver(**by_region):
    async def latest(_session, _character, region):
        return by_region.get(region)

    return latest


def _service(database, **by_region):
    return ChronicleActivityService(database[1], SERVER, _resolver(**by_region))


async def _move(database, location, region=OCASO, actor=ANA):
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        world = await session.get(WorldState, character.id)
        world.location, world.region = location, region


async def _done(database, actor=ANA) -> set[str]:
    async with database[1]() as session:
        return set(
            (
                await session.scalars(
                    select(ChronicleCompletion.objective_id).where(
                        ChronicleCompletion.account_id == actor
                    )
                )
            ).all()
        )


async def _points(database, actor=ANA) -> int:
    async with database[1]() as session:
        rows = (
            await session.scalars(
                select(ChroniclePointGrant.points).where(ChroniclePointGrant.account_id == actor)
            )
        ).all()
        return sum(rows)


_OCASO_ONLY = {OCASO: ROAD_LOCATION}


async def test_talk_needs_the_hub_and_pays_once(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    service = _service(database, **_OCASO_ONLY)
    with pytest.raises(ChronicleError) as error:
        await service.talk(ANA, 1, 1, now=WEEK1)
    assert error.value.code == "chronicle_not_here"
    await _move(database, REFUGE)
    first = await service.talk(ANA, 1, 1, now=WEEK1)
    assert first.completed_now and first.npc == "Oren Cal" and "Oren Cal" in first.text
    second = await service.talk(ANA, 1, 1, now=WEEK1)
    assert not second.completed_now
    assert await _points(database) == 50


async def test_talk_is_gated_by_chapter_date_and_p1(database):
    await _make(database, p1=False)
    await _schedule(database)
    service = _service(database, **_OCASO_ONLY)
    with pytest.raises(ChronicleError) as error:
        await service.talk(ANA, 1, 1, now=WEEK1)
    assert error.value.code == "chronicle_gate"
    with pytest.raises(ChronicleError) as error:
        await service.talk(ANA, 2, 3, now=WEEK1)
    assert error.value.code == "chronicle_chapter_locked"


async def test_talk_uses_mirror_without_the_focus_region(database):
    await _make(database)
    await _schedule(database)
    talk = await _service(database, **_OCASO_ONLY).talk(ANA, 3, 1, now=WEEK3)
    assert talk.npc == "Alda Veyr" and "travessias distantes" in talk.text
    assert "Dara Venn" not in talk.text


async def test_talk_uses_focus_with_the_region(database):
    await _make(database, level=15, location="Vigília do Vale", region=VALES)
    await _schedule(database)
    talk = await _service(
        database, **{OCASO: ROAD_LOCATION, VALES: VDE_GARGANTA_LOCATION}
    ).talk(ANA, 3, 1, now=WEEK3)
    assert talk.npc == "Dara Venn" and talk.completed_now


async def test_resonance_ignores_regions_above_the_character_level(database):
    await _make(database, level=10)
    await _schedule(database)
    talk = await _service(
        database, **{OCASO: ROAD_LOCATION, VALES: VDE_GARGANTA_LOCATION}
    ).talk(ANA, 1, 1, now=WEEK1)
    assert talk.npc == "Oren Cal"


async def test_complement_only_with_the_layer(database):
    await _make(database, level=25, location="Posto de Nareth", region=NARETH)
    await _schedule(database)
    resolver = {OCASO: ROAD_LOCATION, NARETH: NARETH_CAMPINAS_LOCATION}
    without = await _service(database, **resolver).talk(ANA, 4, 2, now=WEEK4)
    assert "comparação de referências" not in without.text
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == ANA))
        session.add(
            Quest(character_id=character.id, quest_id="P18", title="P18", status="completed")
        )
    with_layer = await _service(database, **resolver).talk(ANA, 4, 2, now=WEEK4)
    assert "comparação de referências" in with_layer.text


async def test_readings_complete_the_objective_only_with_every_point(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    service = _service(database, **_OCASO_ONLY)
    for suffix in ("a", "b"):
        view = await service.examine(ANA, 1, 3, f"lei_cr01_c01_{suffix}", now=WEEK1)
        assert not view.completed_now and view.last_text
    assert "cap_01_obj_03" not in await _done(database)
    repeat = await service.examine(ANA, 1, 3, "lei_cr01_c01_a", now=WEEK1)
    assert sum(item.done for item in repeat.points) == 2
    last = await service.examine(ANA, 1, 3, "lei_cr01_c01_c", now=WEEK1)
    assert last.completed_now
    assert await _points(database) == 60


async def test_reading_requires_the_resonance_local_and_a_valid_point(database):
    await _make(database)
    await _schedule(database)
    service = _service(database, **_OCASO_ONLY)
    with pytest.raises(ChronicleError) as error:
        await service.examine(ANA, 1, 3, "lei_cr01_c01_a", now=WEEK1)
    assert error.value.code == "chronicle_not_here"
    await _move(database, ROAD)
    with pytest.raises(ChronicleError) as error:
        await service.examine(ANA, 1, 3, "lei_cr01_c07_a1", now=WEEK1)
    assert error.value.code == "chronicle_unknown"


async def test_actions_list_only_what_is_pending_here(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    service = _service(database, **_OCASO_ONLY)
    actions = {item.objective.objective_id: item for item in await service.actions(ANA, now=WEEK1)}
    assert set(actions) == {"cap_01_obj_01", "cap_01_obj_02", "cap_01_obj_03"}
    assert actions["cap_01_obj_01"].location == REFUGE and not actions["cap_01_obj_01"].here
    assert actions["cap_01_obj_02"].here
    here = {item.objective.objective_id for item in await service.here(ANA, now=WEEK1)}
    assert here == {"cap_01_obj_03"}


async def test_nothing_is_offered_after_the_cutoff(database):
    await _make(database)
    await _schedule(database)
    assert await _service(database, **_OCASO_ONLY).actions(ANA, now=CAL.end_at) == ()


async def _offer(database, *, now, attempts=0, by_region=None):
    profile = EXPLORATION_PROFILES[ROAD_LOCATION]
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == ANA))
        for index in range(attempts):
            session.add(
                ExplorationAttempt(
                    character_id=character.id,
                    local_id="Estrada das Cinzas",
                    ruleset_version="teste",
                    seed=f"s{index}",
                    category="atmospheric",
                    result_id="explore.tdo.estrada.fogueira",
                    status="completed",
                    result_acknowledged=True,
                    created_at=now - timedelta(minutes=30 + index),
                )
            )
        await session.flush()
        return await desbravar_offer(
            session,
            character,
            profile,
            "Estrada das Cinzas",
            _resolver(**(by_region or _OCASO_ONLY)),
            now,
        )


async def test_pending_chapter_result_takes_the_narrative_category(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    offer = await _offer(database, now=WEEK1)
    assert offer.forced is None
    narrative = [item for item in offer.profile.results if item.category == "narrative"]
    assert [item.result_id for item in narrative] == ["dsc_cr01_c01_pulso"]
    others = {item.category for item in offer.profile.results}
    assert others == {
        item.category for item in EXPLORATION_PROFILES[ROAD_LOCATION].results
    }


async def test_third_attempt_is_guaranteed(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    offer = await _offer(database, now=WEEK1, attempts=2)
    assert offer.forced is not None and offer.forced.result_id == "dsc_cr01_c01_pulso"


async def test_result_is_only_offered_in_the_resonance_local(database):
    await _make(database, level=15)
    await _schedule(database)
    offer = await _offer(
        database, now=WEEK1, by_region={OCASO: ROAD_LOCATION, VALES: VDE_GARGANTA_LOCATION}
    )
    assert offer.forced is None
    assert "dsc_cr01_c01_pulso" not in {item.result_id for item in offer.profile.results}
    assert VESTIGIO_RESULT in {item.result_id for item in offer.profile.results}


async def _clear_chapter_one(database):
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == ANA))
        session.add(
            ChronicleCompletion(
                character_id=character.id,
                chronicle_id="cr01",
                objective_id="cap_01_obj_02",
                account_id=ANA,
                server_id=SERVER,
                completed_at=WEEK1,
            )
        )


async def test_vestigio_leaves_the_pool_at_the_daily_limit(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    await _clear_chapter_one(database)
    offer = await _offer(database, now=WEEK1)
    vestigio = next(item for item in offer.profile.results if item.result_id == VESTIGIO_RESULT)
    assert vestigio.weight == 100 and vestigio.category == "narrative"
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == ANA).with_for_update()
        )
        for key in ("a", "b"):
            await record_repeatable(
                session, SERVER, character, "rep_cr01_desbravar", key, now=WEEK1
            )
    offer = await _offer(database, now=WEEK1)
    assert VESTIGIO_RESULT not in {item.result_id for item in offer.profile.results}


async def test_real_desbravar_settles_the_guaranteed_objective_without_cost(database):
    today = datetime.now(UTC).date()
    await _make(database, location=ROAD)
    await _schedule(database, today - timedelta(days=2), BEFORE - timedelta(days=30))
    await _offer(database, now=datetime.now(UTC), attempts=2)
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == ANA))
        session.add(Unlock(character_id=character.id, unlock_id=EXPLORE_UNLOCK))
    async with database[1]() as session:
        before = await session.scalar(select(Character).where(Character.telegram_id == ANA))
        vigor, crowns, xp = before.vigor, before.crowns, before.xp
    view = await RoadService(database[1], SERVER).explore(ANA)
    assert view.result_id == "dsc_cr01_c01_pulso"
    assert "concluído" in view.result_text
    assert "cap_01_obj_02" in await _done(database)
    assert await _points(database) == 70
    async with database[1]() as session:
        after = await session.scalar(select(Character).where(Character.telegram_id == ANA))
        assert (after.vigor, after.crowns, after.xp) == (vigor, crowns, xp)
