"""O Despertar dos Flagelos — exclusividade de atividade (regra global de primeiro plano).

Quem está em combate no Flagelo mantém uma ``GameActivity`` ativa (a linha única
``uq_active_foreground``, a mesma do Evento Mundial genérico). Caçada, Desbravar, Masmorra, PvP,
Missões e Ofícios já consultam essa linha; nenhuma trava paralela foi criada.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select, update

from asterion.application.combat_configuration_guard import find_combat_configuration_blocker
from asterion.application.dungeons import DungeonService
from asterion.application.flagelos import ACTIVITY_CONTENT, FlageloService
from asterion.application.pvp import PvpError, PvpService
from asterion.domain import flagelos as fl
from asterion.infrastructure.db.models import (
    Character,
    DungeonRun,
    FlageloParticipant,
    GameActivity,
)
from tests.test_dungeon_multiplayer import _seed_party
from tests.test_flagelos_service import (
    SERVER,
    T0,
    FakeSimulator,
    _characters,
    _eligible_kill,
    _spawn,
)
from tests.test_pvp import NOW as PVP_NOW
from tests.test_pvp import A as PVP_A
from tests.test_pvp import _seed as _seed_pvp
from tests.test_road_integration import ROAD, _seed_road


@pytest.fixture
def service(database) -> FlageloService:
    return FlageloService(database[1], SERVER, FakeSimulator())


async def _active_contents(database, telegram_id: int) -> list[str]:
    async with database[1]() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == telegram_id)
        )
        rows = await session.scalars(
            select(GameActivity.content_id).where(
                GameActivity.character_id == character_id, GameActivity.status == "active"
            )
        )
        return sorted(rows.all())


async def _blocker(database, telegram_id: int):
    async with database[1]() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == telegram_id)
        )
        return await find_combat_configuration_blocker(session, character_id)


# ------------------------------------------------------------------ entrada recusada


async def test_entering_creates_exactly_one_foreground_activity_and_is_idempotent(
    service, database
):
    ((actor, _),) = await _characters(database, 1)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    await service.enter(actor, now=T0)  # clique duplicado: nenhuma segunda linha
    assert await _active_contents(database, actor) == [ACTIVITY_CONTENT]
    assert (await _blocker(database, actor)) is not None


async def test_flagelo_blocks_hunt_and_desbravar(service, database):
    actor, road = await _seed_road(database, 771_801)
    await road.travel(actor, ROAD)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    hunt = await road.start_hunt(actor)
    assert getattr(hunt, "kind", None) != "combat"
    explore = await road.explore(actor)
    assert getattr(explore, "kind", None) != "combat"
    assert await _active_contents(database, actor) == [ACTIVITY_CONTENT]


async def test_flagelo_blocks_dungeon(service, database):
    sessions, _ids = await _seed_party(database, [771_802])
    await _spawn(database, service)
    await service.enter(771_802, now=T0)
    await DungeonService(sessions, SERVER).start_solo(771_802, "stable")
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(DungeonRun)) == 0
    assert await _active_contents(database, 771_802) == [ACTIVITY_CONTENT]


async def test_flagelo_blocks_pvp_queue(service, database):
    await _seed_pvp(database)
    await _spawn(database, service)
    await service.enter(PVP_A, now=T0)
    with pytest.raises(PvpError) as refused:
        await PvpService(database[1], SERVER).enter_queue(PVP_A, now=PVP_NOW)
    assert refused.value.code == "busy"
    assert await _active_contents(database, PVP_A) == [ACTIVITY_CONTENT]


async def test_other_activity_blocks_entering_the_flagelo(service, database):
    actor, road = await _seed_road(database, 771_803)
    await road.travel(actor, ROAD)
    await _spawn(database, service)
    assert getattr(await road.start_hunt(actor), "kind", None) == "combat"
    with pytest.raises(fl_error()) as refused:
        await service.enter(actor, now=T0)
    assert refused.value.code == "busy"


def fl_error():
    from asterion.application.flagelos import FlageloError

    return FlageloError


# ------------------------------------------------------------------ liberação


async def test_leaving_releases_and_the_hunt_opens_again(service, database):
    actor, road = await _seed_road(database, 771_804)
    await road.travel(actor, ROAD)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    assert getattr(await road.start_hunt(actor), "kind", None) != "combat"
    await service.leave(actor, now=T0)
    assert await _active_contents(database, actor) == []
    assert await _blocker(database, actor) is None
    assert getattr(await road.start_hunt(actor), "kind", None) == "combat"


async def test_defeat_of_the_player_releases(database):
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=1, player_hp=1))
    ((actor, _),) = await _characters(database, 1)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    round_ = await service.open_round(now=T0)
    assert await service.resolve_round(round_.id, now=T0 + fl.DECISION_WINDOW)
    async with database[1]() as session:
        participant = (await session.scalars(select(FlageloParticipant))).one()
        assert not participant.in_combat and participant.defeated_at is not None
    assert await _active_contents(database, actor) == []


async def test_inactivity_releases(service, database):
    ((actor, _),) = await _characters(database, 1)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    now = T0
    for _ in range(fl.INACTIVE_ROUNDS):
        round_ = await service.open_round(now=now)
        now += fl.DECISION_WINDOW
        await service.resolve_round(round_.id, now=now)
    assert await _active_contents(database, actor) == []


async def test_death_of_the_flagelo_releases_everyone(database):
    service, event, players, now = await _eligible_kill(database)
    for actor, _ in players:
        assert await _active_contents(database, actor) == []
        assert await _blocker(database, actor) is None
    async with database[1]() as session:
        left = await session.scalar(
            select(func.count())
            .select_from(GameActivity)
            .where(GameActivity.content_id == ACTIVITY_CONTENT, GameActivity.status == "active")
        )
    assert left == 0


# ------------------------------------------------------------------ restart


async def test_restart_keeps_the_lock_while_in_combat(service, database):
    actor, road = await _seed_road(database, 771_805)
    await road.travel(actor, ROAD)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    restarted = FlageloService(database[1], SERVER, FakeSimulator())  # novo processo
    await restarted.tick(now=T0)
    assert await _active_contents(database, actor) == [ACTIVITY_CONTENT]
    assert getattr(await road.start_hunt(actor), "kind", None) != "combat"


async def test_restart_never_leaves_a_phantom_lock(service, database):
    actor, road = await _seed_road(database, 771_806)
    await road.travel(actor, ROAD)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    # Crash entre a saída gravada e a liberação da atividade: ``in_combat`` já é falso.
    async with database[1].begin() as session:
        await session.execute(update(FlageloParticipant).values(in_combat=False))
    assert await _active_contents(database, actor) == [ACTIVITY_CONTENT]  # fantasma
    restarted = FlageloService(database[1], SERVER, FakeSimulator())
    await restarted.tick(now=T0)
    assert await _active_contents(database, actor) == []
    assert getattr(await road.start_hunt(actor), "kind", None) == "combat"
    await restarted.tick(now=T0)  # idempotente
