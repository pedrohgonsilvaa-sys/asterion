from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.p1 import P1Service
from asterion.application.p2 import CHARNECA, P2Service
from asterion.application.p3 import P3Service
from asterion.application.round import RoundService
from asterion.application.world import WorldService
from asterion.bot.creation_handlers import creation_router
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    Character,
    HuntRound,
    LocationDiscovery,
    Quest,
    WorldState,
)
from tests.test_charneca_content import _seed_charneca
from tests.test_creation_ui import callback_update, message_update
from tests.test_p2_integration import _seed


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _last_method(bot):
    return bot.session.make_request.call_args.args[1]


def _text(method):
    return getattr(method, "text", None) or getattr(method, "caption", None) or ""


def _callbacks(method):
    return [
        button.callback_data
        for row in method.reply_markup.inline_keyboard
        for button in row
    ]


def _command_update(text: str, update_id: int, actor: int):
    update = message_update(text, update_id=update_id, actor=actor)
    update["message"]["entities"] = [
        {"type": "bot_command", "offset": 0, "length": len(text)}
    ]
    return update


@pytest.mark.asyncio
async def test_map_hides_charneca_before_discovery(database):
    actor = 880401
    character_id, _ = await _seed(database, actor)
    async with database[1]() as session:
        session.add_all(
            [
                LocationDiscovery(
                    character_id=character_id,
                    location_id="tdo.location.estrada_das_cinzas",
                ),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="tdo.location.refugio_do_ocaso",
                ),
            ]
        )
        await session.commit()

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=RoundService(database[1], "ocaso"),
            p2=P2Service(database[1], "ocaso"),
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:map:region:tdo", update_id=880401, actor=actor),
    )
    method = _last_method(bot)
    assert "Charneca da Fuligem" not in method.text
    assert "world:map:local:charneca" not in _callbacks(method)


@pytest.mark.asyncio
async def test_map_opens_p2_context_during_mission_and_normal_local_after_completion(
    database,
):
    actor = 880402
    _, p2 = await _seed(database, actor)
    offer = await p2.alda(actor)
    accepted = await p2.accept(actor, offer.state_version)
    arrived = await p2.travel_to_charneca(actor, accepted.state_version)
    assert arrived.location == CHARNECA

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=RoundService(database[1], "ocaso"),
            p2=p2,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:adventure", update_id=880430, actor=actor),
    )
    adventure = _last_method(bot)
    assert "📜 Missão Principal\nFuligem sem Fogo · Em Andamento" in adventure.text
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:map:region:tdo", update_id=880403, actor=actor),
    )
    region = _last_method(bot)
    assert "Charneca da Fuligem · Local Atual" in region.text
    assert "world:map:local:charneca" in _callbacks(region)
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:map:local:charneca", update_id=880404, actor=actor),
    )
    contextual = _last_method(bot)
    assert "Examinar Pontos de Fuligem · 0/3" not in contextual.text
    assert "world:local" in _callbacks(contextual)
    assert "Caçadas · Disponível" not in contextual.text
    assert "Desbravar · Disponível" not in contextual.text
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:local", update_id=880408, actor=actor),
    )
    local = _last_method(bot)
    assert "Local Atual" in local.text
    assert local.text.count("Local Atual") == 1
    assert "Examinar Pontos de Fuligem · 0/3" not in local.text
    assert "world:missions" in _callbacks(local)

    completed_actor = 880405
    await _seed_charneca(
        database,
        actor=completed_actor,
        location=CHARNECA,
    )
    completed_dispatcher = Dispatcher(disable_fsm=True)
    completed_dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=RoundService(database[1], "ocaso"),
            p2=P2Service(database[1], "ocaso"),
        )
    )
    await completed_dispatcher.feed_raw_update(
        bot,
        callback_update(
            "world:map:local:charneca", update_id=880406, actor=completed_actor
        ),
    )
    normal = _last_method(bot)
    assert "Charneca da Fuligem" in normal.text
    assert normal.text.count("Local Atual") == 1
    assert "world:local" in _callbacks(normal)
    assert "road:prepare" not in _callbacks(normal)
    assert "road:explore" not in _callbacks(normal)
    assert "Cripta" not in normal.text
    assert "p2:resume" not in _callbacks(normal)


@pytest.mark.asyncio
async def test_menu_and_start_reconstruct_charneca_and_round_preparing_without_new_batch(
    database,
):
    actor = 880407
    await _seed_charneca(
        database,
        actor=actor,
        location=CHARNECA,
        round_familiarity=True,
    )
    rounds = RoundService(database[1], "ocaso")
    prepared = await rounds.prepare_round(actor, 10)
    assert prepared.kind == "round_prepare"

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=rounds,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    dispatcher.include_router(
        creation_router(
            CreationService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=rounds,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, _command_update("/menu", update_id=880408, actor=actor)
    )
    menu_method = _last_method(bot)
    assert "Charneca da Fuligem" in menu_method.text
    assert "Ronda · 10 Encontros" in menu_method.text
    start_callback = next(
        callback
        for callback in _callbacks(menu_method)
        if callback.startswith("road:round:start:")
    )

    await dispatcher.feed_raw_update(
        bot, _command_update("/start", update_id=880409, actor=actor)
    )
    start_method = _last_method(bot)
    assert "Charneca da Fuligem" in start_method.text
    assert "Ronda · 10 Encontros" in start_method.text
    assert start_callback in _callbacks(start_method)

    resumed = await RoundService(database[1], "ocaso").resume(actor)
    assert resumed.kind == "round_prepare"
    assert resumed.round_id == prepared.round_id
    assert resumed.state_version == prepared.state_version
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        state = await session.get(HuntRound, prepared.round_id)
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        assert state.config_snapshot["local_id"] == "tdo.location.charneca_da_fuligem"
        assert state.status == "preparing"
        assert world.location == CHARNECA
        assert await session.scalar(
            select(HuntRound.id).where(HuntRound.character_id == character.id)
        ) == prepared.round_id


@pytest.mark.asyncio
async def test_brazier_travel_lists_only_known_destinations_and_keeps_route_distinct(
    database,
):
    undiscovered_actor = 880410
    undiscovered_road = await _seed_charneca(
        database,
        actor=undiscovered_actor,
        name="Ventos",
        location="Refúgio do Ocaso",
        permanent_braziers=("tdo.brazier.refugio_do_ocaso",),
    )
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=undiscovered_road,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:travel", update_id=880411, actor=undiscovered_actor),
    )
    unknown_screen = _last_method(bot)
    assert "Braseiro do Vento Morto" not in _text(unknown_screen)
    assert not any(
        callback.startswith("road:travel:") for callback in _callbacks(unknown_screen)
    )
    for stale_callback, update_id in (
        ("road:travel:brazier:vento_morto", 880416),
        ("road:route:road", 880417),
    ):
        await dispatcher.feed_raw_update(
            bot,
            callback_update(stale_callback, update_id=update_id, actor=undiscovered_actor),
        )
        restored = _last_method(bot)
        assert "Refúgio do Ocaso" in _text(restored)
        assert "world:map:fromlocal" in _callbacks(restored)

    actor = 880412
    road = await _seed_charneca(
        database,
        actor=actor,
        name="Fuligem",
        location="Refúgio do Ocaso",
        permanent_braziers=(
            "tdo.brazier.estrada",
            "tdo.brazier.refugio_do_ocaso",
            "tdo.brazier.vento_morto",
        ),
    )
    known_dispatcher = Dispatcher(disable_fsm=True)
    known_dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=road,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    await known_dispatcher.feed_raw_update(
        bot, callback_update("world:travel", update_id=880413, actor=actor)
    )
    travel_screen = _last_method(bot)
    assert "Braseiro do Vento Morto · Charneca da Fuligem" in travel_screen.text
    assert "Braseiro do Refúgio · Refúgio do Ocaso" not in travel_screen.text
    vento_callback = next(
        callback
        for callback in _callbacks(travel_screen)
        if callback == "road:travel:brazier:vento_morto"
    )
    await known_dispatcher.feed_raw_update(
        bot, callback_update(vento_callback, update_id=880414, actor=actor)
    )
    arrived = _last_method(bot)
    assert "📍 Local Atual\n🌑 Charneca da Fuligem" in arrived.text
    assert "world:map:fromlocal" in _callbacks(arrived)
    await known_dispatcher.feed_raw_update(
        bot,
        callback_update("world:map:fromlocal", update_id=880415, actor=actor),
    )
    map_screen = _last_method(bot)
    region_callback = next(
        callback
        for callback in _callbacks(map_screen)
        if callback == "world:map:region:tdo:fromlocal"
    )
    await known_dispatcher.feed_raw_update(
        bot,
        callback_update(region_callback, update_id=880418, actor=actor),
    )
    region = _last_method(bot)
    charneca_callback = next(
        callback
        for callback in _callbacks(region)
        if callback == "world:map:local:charneca:fromlocal"
    )
    await known_dispatcher.feed_raw_update(
        bot,
        callback_update(charneca_callback, update_id=880419, actor=actor),
    )
    detail = _last_method(bot)
    assert "road:route:refuge" in _callbacks(detail)
    await known_dispatcher.feed_raw_update(
        bot,
        callback_update("road:route:refuge", update_id=880420, actor=actor),
    )
    returned = _last_method(bot)
    assert "Refúgio do Ocaso" in returned.text

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        assert world.location == "Refúgio do Ocaso"
        assert await session.scalar(
            select(HuntRound.id).where(HuntRound.character_id == character.id)
        ) is None


@pytest.mark.asyncio
async def test_remote_known_local_offers_travel_only_when_authoritatively_available(
    database,
):
    actor = 880418
    road = await _seed_charneca(
        database,
        actor=actor,
        name="Viaja",
        location="Refúgio do Ocaso",
        permanent_braziers=(
            "tdo.brazier.estrada",
            "tdo.brazier.refugio_do_ocaso",
            "tdo.brazier.vento_morto",
        ),
    )
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=road,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:map:local:road", update_id=880418, actor=actor),
    )
    remote = _last_method(bot)
    assert "Local Atual" not in remote.text
    travel_callback = "world:travel:to:road"
    assert travel_callback in _callbacks(remote)
    assert "world:travel" not in _callbacks(remote)

    await dispatcher.feed_raw_update(
        bot,
        callback_update(travel_callback, update_id=880419, actor=actor),
    )
    arrived = _last_method(bot)
    assert "Estrada das Cinzas" in _text(arrived)
    assert "Travessia dos Braseiros" not in _text(arrived)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        assert world.location == "Estrada das Cinzas"


@pytest.mark.asyncio
async def test_map_region_lists_all_known_locations_and_brazier_detail_travels_directly(
    database,
):
    actor = 880424
    road = await _seed_charneca(
        database,
        actor=actor,
        name="Rota",
        location=CHARNECA,
        permanent_braziers=(
            "tdo.brazier.refugio_do_ocaso",
            "tdo.brazier.vento_morto",
        ),
    )
    travel_calls = []
    travel_brazier = road.travel_brazier

    async def record_travel(request_actor, brazier_id):
        travel_calls.append(brazier_id)
        return await travel_brazier(request_actor, brazier_id)

    road.travel_brazier = record_travel
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=road,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    bot = _telegram()

    async def click(data, update_id):
        await dispatcher.feed_raw_update(
            bot, callback_update(data, update_id=update_id, actor=actor)
        )
        return _last_method(bot)

    await click("world:map:fromlocal", 880425)
    await click("world:map:region:tdo:fromlocal", 880426)
    region = _last_method(bot)
    numeric_buttons = [
        button
        for row in region.reply_markup.inline_keyboard
        for button in row
        if button.text.isdigit()
    ]
    assert [button.text for button in numeric_buttons] == ["1", "2", "3"]
    assert len({button.callback_data for button in numeric_buttons}) == 3

    detail = await click("world:map:local:refuge:fromlocal", 880427)
    assert "Viajar pelo Braseiro" in [
        button.text
        for row in detail.reply_markup.inline_keyboard
        for button in row
    ]
    direct = "world:travel:to:refuge:fromlocal"
    assert direct in _callbacks(detail)
    arrived = await click(direct, 880428)
    assert "Refúgio do Ocaso" in _text(arrived)
    assert travel_calls == ["tdo.brazier.refugio_do_ocaso"]

    stale = await click(direct, 880429)
    assert "Refúgio do Ocaso" in _text(stale)
    assert travel_calls == ["tdo.brazier.refugio_do_ocaso"]


@pytest.mark.asyncio
async def test_known_inaccessible_location_has_map_detail_without_fake_travel(database):
    actor = 880431
    road = await _seed_charneca(
        database,
        actor=actor,
        location=CHARNECA,
        permanent_braziers=("tdo.brazier.vento_morto",),
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            Quest(
                character_id=character.id,
                quest_id="P3",
                title="Sob Galhos Calcinados",
                status="completed",
                step=5,
                content_version="tdo-1.0.11",
                progress={"completed": True},
            )
        )
        await session.commit()
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=road,
            p2=P2Service(database[1], "ocaso"),
            p3=P3Service(database[1], "ocaso"),
        )
    )
    bot = _telegram()

    async def click(data, update_id):
        await dispatcher.feed_raw_update(
            bot, callback_update(data, update_id=update_id, actor=actor)
        )
        return _last_method(bot)

    await click("world:map", 880432)
    await click("world:map:region:tdo", 880433)
    region = _last_method(bot)
    assert "Bosque Calcinado · Conhecido" in region.text
    assert "world:map:local:bosque" in _callbacks(region)
    detail = await click("world:map:local:bosque", 880434)
    assert "Bosque Calcinado" in _text(detail)
    assert "Deslocamento · Indisponível a partir do Local atual" in _text(detail)
    assert not any(
        callback.startswith("road:route:") or callback.startswith("world:travel")
        for callback in _callbacks(detail)
    )
    assert "world:map:region:tdo" in _callbacks(detail)

    unavailable_actor = 880420
    unavailable_road = await _seed_charneca(
        database,
        actor=unavailable_actor,
        name="Nuvem",
        location="Refúgio do Ocaso",
        permanent_braziers=("tdo.brazier.refugio_do_ocaso",),
    )
    unavailable_dispatcher = Dispatcher(disable_fsm=True)
    unavailable_dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=unavailable_road,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    await unavailable_dispatcher.feed_raw_update(
        bot,
        callback_update(
            "world:map:local:road", update_id=880421, actor=unavailable_actor
        ),
    )
    unavailable = _last_method(bot)
    assert "world:travel" not in _callbacks(unavailable)

    p2_actor = 880422
    p2_road = await _seed_charneca(
        database,
        actor=p2_actor,
        name="Brasa",
        location="Refúgio do Ocaso",
        permanent_braziers=(
            "tdo.brazier.estrada",
            "tdo.brazier.refugio_do_ocaso",
        ),
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == p2_actor)
        )
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == "P2",
            )
        )
        quest.status = "active"
        await session.commit()
    p2_dispatcher = Dispatcher(disable_fsm=True)
    p2_dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            p1=P1Service(database[1], "ocaso"),
            road=p2_road,
            p2=P2Service(database[1], "ocaso"),
        )
    )
    await p2_dispatcher.feed_raw_update(
        bot,
        callback_update("world:map:local:road", update_id=880423, actor=p2_actor),
    )
    during_p2 = _last_method(bot)
    assert "world:travel" not in _callbacks(during_p2)
