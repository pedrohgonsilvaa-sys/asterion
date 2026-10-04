from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.p1 import P1Service
from asterion.application.road import CHARNECA, REFUGE, ROAD, RoadView
from asterion.application.round import RoundView
from asterion.application.world import WorldService, WorldView
from asterion.bot.character_ui import render_character
from asterion.bot.road_ui import (
    render_current_local,
    render_road,
    render_round_selection,
)
from asterion.bot.world_handlers import world_router
from asterion.bot.world_ui import render_adventure, render_world
from asterion.infrastructure.db.models import Character, LocationDiscovery
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road


def _callbacks(screen):
    return [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def _buttons(screen):
    return {
        button.callback_data: button.text
        for row in screen.keyboard.inline_keyboard
        for button in row
    }


def _button(screen, label):
    return next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == label
    )


def test_adventure_root_only_exposes_navigation_and_contextual_activities():
    screen = render_adventure(CHARNECA)
    assert "📍 Local Atual\n🌑 Charneca da Fuligem\nTerras do Ocaso" in screen.text
    assert set(_callbacks(screen)) == {
        "world:local",
        "world:map",
        "world:missions",
        "dungeon:known",
        "menu:back",
    }
    assert not any(
        callback in {"road:hunt", "road:explore", "road:prepare"}
        for callback in _callbacks(screen)
    )


def test_adventure_root_displays_only_supplied_current_principal_quest():
    screen = render_adventure(CHARNECA, "Fuligem sem Fogo")
    assert "📜 Missão Principal\nFuligem sem Fogo · Em Andamento" in screen.text
    assert "P2" not in screen.text


def test_primary_telegram_screens_have_live_compact_callbacks_and_exits():
    world = WorldView(
        kind="menu",
        character_id=uuid4(),
        name="Aster",
        race="remanescente",
        character_class="sentinela",
        hp=Decimal("100"),
        max_hp=Decimal("100"),
        vigor=80,
        max_vigor=100,
        xp=200,
        region="Terras do Ocaso",
        location=CHARNECA,
        quest_title="Fuligem sem Fogo",
    )
    screens = [
        render_world(world),
        render_adventure(CHARNECA, "Fuligem sem Fogo"),
        render_character(),
        render_current_local(
            RoadView(
                "charneca",
                uuid4(),
                CHARNECA,
                name="Aster",
                hp=Decimal("100"),
                max_hp=Decimal("100"),
                vigor=80,
                max_vigor=100,
            )
        ),
        render_round_selection(
            RoadView("charneca", uuid4(), CHARNECA, familiar=True)
        ),
        render_road(
            RoundView(
                kind="round_prepare",
                character_id=uuid4(),
                location=CHARNECA,
                round_id=uuid4(),
                state_version=1234,
                batch_size=10,
                hp=Decimal("100"),
                max_hp=Decimal("100"),
                vigor=80,
                max_vigor=100,
            )
        ),
    ]
    for screen in screens:
        callbacks = _callbacks(screen)
        assert callbacks, screen.image_key
        assert all(len(callback.encode("utf-8")) <= 64 for callback in callbacks)
        assert all(callback != "menu:noop" for callback in callbacks)
        assert all(not callback.startswith("road:unavailable:") for callback in callbacks)


def test_local_is_the_entry_for_manual_hunt_round_and_explore():
    local = render_current_local(
        RoadView(
            "charneca",
            uuid4(),
            CHARNECA,
            name="Aster",
            hp=120,
            max_hp=200,
            vigor=75,
            max_vigor=100,
            familiar=True,
            brazier_label="Braseiro do Vento Morto",
        ),
        explore_state="available",
    )
    assert _buttons(local)["road:hunt"] == "Caçar"
    assert _buttons(local)["world:round"] == "Ronda"
    assert _buttons(local)["road:explore:start"] == "Desbravar"
    assert "road:round:new:5" not in _callbacks(local)
    assert "road:route:refuge" not in _callbacks(local)
    assert "world:map:fromlocal" in _callbacks(local)
    assert "❤️ HP · 120 / 200" in local.text
    assert "⚡ Vigor · 75 / 100" in local.text

    selection = render_round_selection(
        RoadView("charneca", uuid4(), CHARNECA, familiar=True)
    )
    assert [
        button.text
        for row in selection.keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith("road:round:new:")
    ] == ["1", "2", "3"]
    assert _callbacks(selection)[-1] == "world:local"


def test_refuge_does_not_offer_combat_or_exploration_actions():
    local = render_current_local(
        RoadView("refuge", uuid4(), REFUGE, name="Aster", hp=100, max_hp=100),
        mission_available=True,
    )
    assert "Local narrativo seguro." in local.text
    assert not any(
        callback in {"road:hunt", "road:explore:start", "world:round"}
        for callback in _callbacks(local)
    )
    assert "world:missions" in _callbacks(local)
    assert "p2:alda" in _callbacks(local)
    assert "world:oren" in _callbacks(local)


@pytest.mark.asyncio
async def test_telegram_adventure_local_hunt_and_map_callbacks_use_real_services(database):
    actor = 883401
    _, service = await _seed_road(database, actor=actor)
    start_hunt = service.start_hunt
    start_hunt_results = []

    async def record_start_hunt(request_actor):
        result = await start_hunt(request_actor)
        start_hunt_results.append(result.kind if result is not None else None)
        return result

    service.start_hunt = record_start_hunt
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                LocationDiscovery(
                    character_id=character.id,
                    location_id="tdo.location.estrada_das_cinzas",
                ),
                LocationDiscovery(
                    character_id=character.id,
                    location_id="tdo.location.refugio_do_ocaso",
                ),
            ]
        )
        await session.commit()
    await service.travel(actor, ROAD)
    world = WorldService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    p1 = P1Service(database[1], "ocaso")
    dispatcher.include_router(world_router(world, {}, p1=p1, road=service))
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)

    async def click(data: str, update_id: int):
        await dispatcher.feed_raw_update(
            bot,
            callback_update(data, update_id=update_id, actor=actor),
        )
        return bot.session.make_request.call_args.args[1]

    adventure = await click("world:adventure", 883402)
    assert "Aventura" in adventure.text
    assert "world:local" in {
        button.callback_data
        for row in adventure.reply_markup.inline_keyboard
        for button in row
    }

    map_screen = await click("world:map:fromlocal", 883405)
    map_region_callback = next(
        button.callback_data
        for row in map_screen.reply_markup.inline_keyboard
        for button in row
        if button.text == "1"
    )
    region = await click(map_region_callback, 883406)
    assert "Terras do Ocaso" in region.text
    current_place_callback = next(
        button.callback_data
        for row in region.reply_markup.inline_keyboard
        for button in row
        if button.text == "1"
    )
    place = await click(current_place_callback, 883407)
    assert "Local Atual" in place.text
    assert "world:local" in {
        button.callback_data
        for row in place.reply_markup.inline_keyboard
        for button in row
    }

    local = await click("world:local", 883408)
    local_buttons = {
        button.callback_data: button.text
        for row in local.reply_markup.inline_keyboard
        for button in row
    }
    assert local_buttons["road:hunt"] == "Caçar"

    combat = await click("road:hunt", 883409)
    assert "⚔️" in combat.text, start_hunt_results
    assert start_hunt_results == ["combat"]
    assert any(
        button.text in {"Ataque Básico", "Defender"}
        for row in combat.reply_markup.inline_keyboard
        for button in row
    )


@pytest.mark.asyncio
async def test_legacy_oren_entry_without_available_missions_has_local_exit(database):
    actor = 883402
    _, road = await _seed_road(database, actor=actor)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(WorldService(database[1], "ocaso"), {}, road=road)
    )
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:oren", update_id=883403, actor=actor),
    )
    response = bot.session.make_request.call_args.args[1]
    callbacks = [
        button.callback_data
        for row in response.reply_markup.inline_keyboard
        for button in row
    ]
    assert "Não há uma missão disponível" in response.text
    assert callbacks == ["world:local"]

