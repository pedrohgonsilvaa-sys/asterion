from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.p1 import P1Service
from asterion.application.p2 import CHARNECA, P2Service
from asterion.application.round import RoundService
from asterion.application.world import WorldService
from asterion.bot.creation_handlers import creation_router
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    Character,
    HuntRound,
    LocationDiscovery,
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
    assert "Examinar Pontos de Fuligem · 0/3" in contextual.text
    assert "Caçadas · Disponível" not in contextual.text
    assert "Desbravar · Disponível" not in contextual.text

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
    assert "Charneca da Fuligem · Local Atual" in normal.text
    assert "road:prepare" in _callbacks(normal)
    assert "road:explore" in _callbacks(normal)
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
        assert "road:route:charneca" in _callbacks(restored)

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
    assert "Charneca da Fuligem · Local Atual" in arrived.text
    assert "Retornar ao Refúgio" in [
        button.text
        for row in arrived.reply_markup.inline_keyboard
        for button in row
    ]
    await known_dispatcher.feed_raw_update(
        bot,
        callback_update("road:route:refuge", update_id=880415, actor=actor),
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
