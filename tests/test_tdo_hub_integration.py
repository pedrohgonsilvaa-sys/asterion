"""Bloco A (Navegacao) da TdO v1.0.18 contra PostgreSQL: hub do Refugio.

Criterios 11, 12, 13, 18 e "personagem aparece onde estava" do 20 (secao 33.16).
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.road import (
    BOSQUE,
    BOSQUE_BRAZIER,
    CAMARA,
    CHARNECA,
    CHARNECA_BRAZIER,
    REFUGE,
    ROAD,
    RUINS,
    RUINS_BRAZIER,
    RoadService,
)
from asterion.domain.tdo_explore import (
    BOSQUE_LOCATION_ID,
    CAMARA_LOCATION_ID,
    CHARNECA_LOCATION_ID,
    RUINS_LOCATION_ID,
)
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    Character,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardEvent,
    WorldState,
)

REFUGE_BRAZIER = "tdo.brazier.refugio_do_ocaso"


async def _seed(
    database,
    actor,
    *,
    location=REFUGE,
    discovered=(),
    braziers=(),
    p1="completed",
    p6=None,
):
    cid = uuid4()
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor))
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=cid,
                telegram_id=actor,
                server_id="ocaso",
                name=f"H{suffix}",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.7.0-baseline-1.0",
                level=1,
                xp=0,
                hp=Decimal("500"),
                max_hp=Decimal("900"),
                vigor=77,
                max_vigor=100,
                crowns=5,
            )
        )
        await session.flush()
        session.add(WorldState(character_id=cid, region="Terras do Ocaso", location=location))
        session.add(Brazier(character_id=cid, brazier_id="tdo.brazier.estrada"))
        session.add(Brazier(character_id=cid, brazier_id=REFUGE_BRAZIER))
        for brazier_id in braziers:
            session.add(Brazier(character_id=cid, brazier_id=brazier_id))
        if p1:
            session.add(
                Quest(
                    character_id=cid,
                    quest_id="P1",
                    title="Vozes na Estrada",
                    status=p1,
                    step=7,
                    content_version="tdo-1.0.2",
                )
            )
        if p6:
            session.add(
                Quest(
                    character_id=cid,
                    quest_id="P6",
                    title="O Vigia Partido",
                    status=p6,
                    step=8,
                    content_version="tdo-1.0.11",
                )
            )
        for location_id in discovered:
            session.add(LocationDiscovery(character_id=cid, location_id=location_id))
    return cid


def _road(database):
    return RoadService(database[1], "ocaso")


async def _world_location(database, cid):
    async with database[1]() as session:
        return (await session.get(WorldState, cid)).location


ALL_IDS = (CHARNECA_LOCATION_ID, BOSQUE_LOCATION_ID, RUINS_LOCATION_ID, CAMARA_LOCATION_ID)


@pytest.mark.asyncio
async def test_refuge_lists_only_discovered_locals(database):
    actor = 920001
    await _seed(database, actor, discovered=(CHARNECA_LOCATION_ID, CAMARA_LOCATION_ID))
    view = await _road(database).resume(actor)
    assert view.kind == "refuge"
    assert view.route_destinations == (ROAD, CHARNECA, CAMARA)
    assert BOSQUE not in view.route_destinations and RUINS not in view.route_destinations
    # Travessia dos Braseiros nao existe nas Terras do Ocaso.
    assert view.brazier_destinations == ()


@pytest.mark.asyncio
async def test_hub_round_trip_costs_nothing(database):
    actor = 920002
    cid = await _seed(database, actor, discovered=ALL_IDS)
    road = _road(database)
    for label in (ROAD, CHARNECA, BOSQUE, RUINS, CAMARA):
        out = await road.travel_route(actor, label)
        assert out is not None and out.location == label
        assert await _world_location(database, cid) == label
        # De qualquer Local so se volta ao Refugio.
        assert out.route_destinations == (REFUGE,)
        back = await road.travel_route(actor, REFUGE)
        assert back is not None and back.location == REFUGE
        assert await _world_location(database, cid) == REFUGE
    async with database[1]() as session:
        character = await session.get(Character, cid)
        assert (character.vigor, character.crowns, character.xp) == (77, 5, 0)
        rewards = await session.scalar(
            select(func.count()).select_from(RewardEvent).where(RewardEvent.character_id == cid)
        )
        assert rewards == 0


@pytest.mark.asyncio
async def test_cannot_enter_undiscovered_local(database):
    actor = 920003
    cid = await _seed(database, actor, discovered=(CHARNECA_LOCATION_ID,))
    road = _road(database)
    for label in (BOSQUE, RUINS, CAMARA):
        assert await road.travel_route(actor, label) is None
        assert await road.travel(actor, label) is None
    assert await _world_location(database, cid) == REFUGE


@pytest.mark.asyncio
async def test_no_direct_local_to_local_travel(database):
    actor = 920004
    cid = await _seed(
        database,
        actor,
        location=CHARNECA,
        discovered=ALL_IDS,
        braziers=(CHARNECA_BRAZIER, BOSQUE_BRAZIER, RUINS_BRAZIER),
    )
    road = _road(database)
    for label in (ROAD, BOSQUE, RUINS, CAMARA):
        assert await road.travel_route(actor, label) is None
        assert await road.travel(actor, label) is None
    # Travessia dos Braseiros tambem esta oculta nas Terras do Ocaso.
    assert await road.travel_brazier(actor, BOSQUE_BRAZIER) is None
    assert await road.travel_brazier(actor, REFUGE_BRAZIER) is None
    assert await _world_location(database, cid) == CHARNECA
    view = await road.resume(actor)
    assert view.route_destinations == (REFUGE,)
    assert view.brazier_destinations == ()


@pytest.mark.asyncio
async def test_old_routes_are_gone(database):
    from asterion.application import road as road_module

    pairs = road_module.OVERLAND_ROUTE_PAIRS
    assert frozenset((REFUGE, CHARNECA)) not in pairs
    assert frozenset((CHARNECA, BOSQUE)) not in pairs
    assert frozenset((BOSQUE, RUINS)) not in pairs


@pytest.mark.asyncio
async def test_travel_refused_during_foreground_activity(database):
    actor = 920005
    cid = await _seed(database, actor, discovered=ALL_IDS)
    async with database[1].begin() as session:
        session.add(
            GameActivity(
                character_id=cid,
                content_id="tdo_hub_test_combat",
                status="active",
                ruleset_version="gdd-1.7.0-baseline-1.0",
            )
        )
    assert await _road(database).travel_route(actor, CHARNECA) is None
    assert await _world_location(database, cid) == REFUGE


@pytest.mark.asyncio
async def test_hub_needs_p1_completed(database):
    actor = 920006
    cid = await _seed(database, actor, discovered=ALL_IDS, p1="active")
    assert await _road(database).travel_route(actor, CHARNECA) is None
    assert await _world_location(database, cid) == REFUGE


@pytest.mark.asyncio
async def test_camara_has_no_hunt_explore_round_or_brazier(database):
    actor = 920007
    await _seed(database, actor, location=CAMARA, discovered=ALL_IDS)
    road = _road(database)
    view = await road.resume(actor)
    assert view.kind == "camara"
    assert not view.hunt_enabled and not view.explore_enabled
    assert view.brazier_id is None and view.brazier_label is None
    assert view.route_destinations == (REFUGE,)
    assert await road.start_hunt(actor) is None


@pytest.mark.asyncio
async def test_camara_p6_text_state_follows_the_viewer(database):
    done, other = 920008, 920009
    await _seed(database, done, location=CAMARA, discovered=ALL_IDS, p6="completed")
    await _seed(database, other, location=CAMARA, discovered=ALL_IDS)
    road = _road(database)
    assert (await road.resume(done)).camara_p6_completed is True
    assert (await road.resume(other)).camara_p6_completed is False


@pytest.mark.asyncio
async def test_p6_completion_does_not_discover_camara(database):
    actor = 920010
    cid = await _seed(database, actor, p6="completed")
    road = _road(database)
    view = await road.resume(actor)
    assert CAMARA not in view.route_destinations
    assert await road.travel_route(actor, CAMARA) is None
    async with database[1]() as session:
        found = await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == cid,
                LocationDiscovery.location_id == CAMARA_LOCATION_ID,
            )
        )
        assert found is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("label", "expected_kind"),
    [
        (CHARNECA, "charneca"),
        (BOSQUE, "bosque"),
        (RUINS, "ruinas"),
        (ROAD, "road"),
        (CAMARA, "camara"),
    ],
)
async def test_game_opens_where_the_character_was(database, label, expected_kind):
    actor = 920100 + len(label)
    cid = await _seed(database, actor, location=label, discovered=ALL_IDS)
    view = await _road(database).resume(actor)  # servico novo = jogo reaberto
    assert view is not None
    assert view.kind == expected_kind and view.location == label
    assert await _world_location(database, cid) == label


async def _recover(database, cid, local_id):
    road = _road(database)
    async with database[1].begin() as session:
        character = await session.get(Character, cid)
        result = await road.recover_normal_pve_defeat(session, character, local_id)
        world = await session.get(WorldState, cid)
        return result, world.location, character.hp


@pytest.mark.asyncio
async def test_recovery_uses_own_local_brazier_and_never_discovery(database):
    from asterion.domain.road import BOSQUE_LOCATION, CHARNECA_LOCATION, RUINS_LOCATION

    # Tudo descoberto, mas sem Braseiros alem do Refugio: LocationDiscovery nao conta.
    actor = 920201
    cid = await _seed(database, actor, location=RUINS, discovered=ALL_IDS)
    for local_id in (CHARNECA_LOCATION, BOSQUE_LOCATION, RUINS_LOCATION):
        (_, recovery), location, hp = await _recover(database, cid, local_id)
        assert recovery == REFUGE and location == REFUGE
        assert hp == Decimal("900")

    # Com o Braseiro do proprio Local, volta nele.
    actor = 920202
    cid = await _seed(
        database,
        actor,
        discovered=ALL_IDS,
        braziers=(CHARNECA_BRAZIER, BOSQUE_BRAZIER, RUINS_BRAZIER),
    )
    for local_id, label in (
        (CHARNECA_LOCATION, CHARNECA),
        (BOSQUE_LOCATION, BOSQUE),
        (RUINS_LOCATION, RUINS),
    ):
        (_, recovery), location, _ = await _recover(database, cid, local_id)
        assert recovery == label and location == label

    # Ruinas sem o Braseiro de Poente cai no de Galhos Mortos (prioridade de 11.9).
    actor = 920203
    cid = await _seed(database, actor, discovered=ALL_IDS, braziers=(BOSQUE_BRAZIER,))
    (_, recovery), location, _ = await _recover(database, cid, RUINS_LOCATION)
    assert recovery == BOSQUE and location == BOSQUE


@pytest.mark.asyncio
async def test_camara_recovery_is_the_refuge(database):
    actor = 920204
    cid = await _seed(
        database,
        actor,
        location=CAMARA,
        discovered=ALL_IDS,
        braziers=(CHARNECA_BRAZIER, BOSQUE_BRAZIER, RUINS_BRAZIER),
    )
    (brazier_label, recovery), location, hp = await _recover(database, cid, CAMARA_LOCATION_ID)
    assert brazier_label and recovery == REFUGE and location == REFUGE
    assert hp == Decimal("900")
