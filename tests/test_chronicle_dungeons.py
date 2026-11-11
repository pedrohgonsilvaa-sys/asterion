"""Masmorra objectives of the Crônica and the Desbravar alternative (§0.3.4, §2, §8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from asterion.application.chronicle_activities import record_dungeon_run
from asterion.application.dungeons import DungeonService
from asterion.application.road import RoadService
from asterion.domain.chronicle_content import DEEP_VESTIGIO_RESULT, VESTIGIO_RESULT
from asterion.domain.road import EXPLORE_UNLOCK
from asterion.domain.vde_fosso import FOSSO_FAMILY_ID
from asterion.infrastructure.db.models import (
    Character,
    ChronicleCompletion,
    DungeonRun,
    DungeonRunMember,
    Quest,
    Unlock,
)
from tests.test_chronicle_activities import (
    _OCASO_ONLY,
    ANA,
    BEFORE,
    CAL,
    ROAD,
    SERVER,
    WEEK3,
    _done,
    _make,
    _offer,
    _points,
    _resolver,
    _schedule,
    _service,
)
from tests.test_dungeon_multiplayer import _form_matchmade_party, _seed_party

WEEK2 = CAL.chapter_opens_at(2) + timedelta(hours=1)
CRYPT = "dungeon.tdo.cripta_ocaso"


async def _complete(database, *objective_ids, actor=ANA):
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        for objective_id in objective_ids:
            session.add(
                ChronicleCompletion(
                    character_id=character.id,
                    chronicle_id="cr01",
                    objective_id=objective_id,
                    account_id=actor,
                    server_id=SERVER,
                    completed_at=BEFORE,
                )
            )


async def _unlock(database, unlock_id, actor=ANA):
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(Unlock(character_id=character.id, unlock_id=unlock_id))


def _narrative(offer) -> list[str]:
    return [item.result_id for item in offer.profile.results if item.category == "narrative"]


async def test_alternative_takes_the_narrative_category_without_a_released_masmorra(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    await _complete(database, "cap_01_obj_02", "cap_02_obj_01")
    offer = await _offer(database, now=WEEK2)
    assert offer.forced is None and offer.objective_id == "cap_02_obj_04"
    assert _narrative(offer) == [DEEP_VESTIGIO_RESULT]
    forced = await _offer(database, now=WEEK2, attempts=2)
    assert forced.forced is not None and forced.forced.result_id == DEEP_VESTIGIO_RESULT
    actions = {
        item.objective.objective_id: item
        for item in await _service(database, **_OCASO_ONLY).actions(ANA, now=WEEK2)
    }
    assert actions["cap_02_obj_04"].dungeons == () and actions["cap_02_obj_04"].here


async def test_released_masmorra_replaces_the_alternative(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    await _complete(database, "cap_01_obj_02", "cap_02_obj_01")
    await _unlock(database, CRYPT)
    offer = await _offer(database, now=WEEK2)
    # No chapter result pending: the Local keeps its own pool plus the Vestígio.
    assert VESTIGIO_RESULT in _narrative(offer)
    assert DEEP_VESTIGIO_RESULT not in _narrative(offer)
    service = _service(database, **_OCASO_ONLY)
    actions = {item.objective.objective_id: item for item in await service.actions(ANA, now=WEEK2)}
    assert actions["cap_02_obj_04"].dungeons == ("Cripta do Ocaso",)
    assert actions["cap_02_obj_04"].focus
    assert "cap_02_obj_04" not in {
        item.objective.objective_id for item in await service.here(ANA, now=WEEK2)
    }


async def test_masmorra_below_its_minimum_level_is_not_released(database):
    await _make(database, location=ROAD, level=3)
    await _schedule(database)
    await _complete(database, "cap_01_obj_02", "cap_02_obj_01")
    await _unlock(database, CRYPT)
    offer = await _offer(database, now=WEEK2)
    assert _narrative(offer) == [DEEP_VESTIGIO_RESULT]


async def test_mirror_accepts_any_released_masmorra(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    await _unlock(database, CRYPT)
    actions = {
        item.objective.objective_id: item
        for item in await _service(database, **_OCASO_ONLY).actions(ANA, now=WEEK3)
    }
    mirror = actions["cap_03_obj_03"]
    assert mirror.dungeons == ("Cripta do Ocaso",) and not mirror.focus


async def test_run_completes_the_oldest_accepted_objective_once(database):
    await _make(database, location=ROAD)
    await _schedule(database)
    latest = _resolver(**_OCASO_ONLY)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == ANA).with_for_update()
        )
        # Chapter 2 runs in focus (Ocaso pair only); chapter 3 in mirror (any Masmorra).
        assert await record_dungeon_run(
            session, character, FOSSO_FAMILY_ID, latest, now=WEEK3
        ) == "cap_03_obj_03"
        assert await record_dungeon_run(session, character, CRYPT, latest, now=WEEK3) == (
            "cap_02_obj_04"
        )
        assert await record_dungeon_run(session, character, CRYPT, latest, now=WEEK3) is None
    assert await _points(database) == 140


async def test_run_counts_nothing_without_the_entry_gate(database):
    await _make(database, location=ROAD, p1=False)
    await _schedule(database)
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == ANA).with_for_update()
        )
        assert (
            await record_dungeon_run(
                session, character, CRYPT, _resolver(**_OCASO_ONLY), now=WEEK3
            )
            is None
        )
    assert await _points(database) == 0


def _live_day1():
    """A Day 1 that leaves chapter 2 open now, for the services that read the clock."""
    return datetime.now(UTC).date() - timedelta(days=8)


async def test_real_desbravar_settles_the_alternative_without_trail_vestigio(database):
    await _make(database, location=ROAD)
    await _schedule(database, _live_day1(), BEFORE - timedelta(days=30))
    await _complete(database, "cap_01_obj_02", "cap_02_obj_01")
    await _offer(database, now=datetime.now(UTC), attempts=2)
    await _unlock(database, EXPLORE_UNLOCK)
    view = await RoadService(database[1], SERVER).explore(ANA)
    assert view.result_id == DEEP_VESTIGIO_RESULT
    assert "concluído" in view.result_text
    assert "cap_02_obj_04" in await _done(database)
    assert await _points(database) == 70


async def test_valid_run_pays_objective_and_repeatable_only_with_participation(database):
    actors = (941001, 941002)
    sessions, character_ids = await _seed_party(database, actors)
    async with sessions.begin() as session:
        for character_id in character_ids:
            session.add(
                Quest(character_id=character_id, quest_id="P1", title="P1", status="completed")
            )
            session.add(Unlock(character_id=character_id, unlock_id=EXPLORE_UNLOCK))
    await _schedule(database, _live_day1(), BEFORE - timedelta(days=30))
    service = DungeonService(sessions, SERVER)
    ready = await _form_matchmade_party(service, actors, CRYPT)
    async with sessions.begin() as session:
        run = await session.get(DungeonRun, ready.run_id)
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == ready.run_id)
                .order_by(DungeonRunMember.position)
            )
        ).all()
        characters = (
            await session.scalars(select(Character).where(Character.id.in_(character_ids)))
        ).all()
        by_id = {character.id: character for character in characters}
        active = next(
            member for member in members if by_id[member.character_id].telegram_id == actors[0]
        )
        idle = next(member for member in members if member is not active)
        active.contribution = {"points": "100", "actions": 4}
        idle.contribution = {"points": "0", "actions": 0}
        await service._settle_run(session, by_id[active.character_id], run, members, by_id)
    assert "cap_02_obj_04" in await _done(database, actors[0])
    assert await _points(database, actors[0]) == 70 + 25
    assert await _done(database, actors[1]) == set()
    assert await _points(database, actors[1]) == 0


def test_chapter_lines_say_where_each_masmorra_objective_runs():
    from asterion.application.chronicle_activities import ActionView
    from asterion.bot.chronicle_ui import _action_line
    from asterion.domain.chronicle import OBJECTIVES_BY_ID

    objective = OBJECTIVES_BY_ID["cap_02_obj_04"]
    pair = ("Galerias do Vigia", "Cripta do Ocaso")
    focus = ActionView(objective, ROAD, True, dungeons=pair)
    assert _action_line(focus).endswith("Masmorra: Galerias do Vigia ou Cripta do Ocaso")
    mirror = ActionView(objective, ROAD, True, dungeons=pair[1:], focus=False)
    assert _action_line(mirror).endswith("qualquer Masmorra com Estável liberada")
    alternative = ActionView(objective, ROAD, True)
    assert _action_line(alternative).endswith(f"sem Masmorra liberada: Desbravar em {ROAD}")
