from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import func, select

import asterion.application.road as road_application
from asterion.application.creation import CreationService
from asterion.application.road import BOSQUE, CHARNECA, ROAD, RoadService
from asterion.application.world import WorldService
from asterion.bot.creation_handlers import creation_router
from asterion.bot.road_ui import render_road
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    Account,
    Character,
    ExplorationAttempt,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_creation_ui import callback_update, message_update


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _last_method(bot):
    return bot.session.make_request.call_args.args[1]


def _last_message_method(bot):
    return next(
        call.args[1]
        for call in reversed(bot.session.make_request.call_args_list)
        if hasattr(call.args[1], "reply_markup")
    )


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


async def _seed_local(database, actor: int, location: str):
    _, sessions = database
    character_id = uuid4()
    location_data = {
        ROAD: ("explore.estrada_das_cinzas", 3),
        CHARNECA: ("explore.charneca_da_fuligem", 4),
        BOSQUE: ("explore.bosque_calcinado", 5),
    }
    explore_unlock, level = location_data[location]
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Tester",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id="P1",
                    title="Vozes na Estrada",
                    status="completed",
                    step=7,
                    content_version="tdo-1.0.2",
                ),
                Quest(
                    character_id=character_id,
                    quest_id="P2",
                    title="Fuligem sem Fogo",
                    status="completed",
                    step=6,
                    content_version="tdo-1.0.9",
                    progress={"completed": True},
                ),
                WorldState(
                    character_id=character_id,
                    region="Terras do Ocaso",
                    location=location,
                ),
                Unlock(character_id=character_id, unlock_id=explore_unlock),
                *(
                    [
                        Quest(
                            character_id=character_id,
                            quest_id="P3",
                            title="Sob Galhos Calcinados",
                            status="completed",
                            step=6,
                            content_version="tdo-1.0.10",
                            progress={"completed": True},
                        ),
                        Unlock(
                            character_id=character_id,
                            unlock_id="route.tdo.charneca_bosque",
                        ),
                    ]
                    if location == BOSQUE
                    else []
                ),
                *(
                    [
                        Unlock(
                            character_id=character_id,
                            unlock_id="route.tdo.refugio_charneca",
                        )
                    ]
                    if location in {CHARNECA, BOSQUE}
                    else []
                ),
            ]
        )
        session.add_all(
            LocationDiscovery(character_id=character_id, location_id=location_id)
            for location_id in (
                "tdo.location.estrada_das_cinzas",
                "tdo.location.refugio_do_ocaso",
                "tdo.location.charneca_da_fuligem",
                "tdo.location.bosque_calcinado",
            )
        )
    return RoadService(sessions, "ocaso")


def _force_result(monkeypatch, category: str, result_id: str, result_text: str):
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda seed, player_level, recent, excluded, profile: (
            category,
            result_id,
            result_text,
        ),
    )


def _dispatcher(database, road):
    world = WorldService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(world_router(world, {}, road=road))
    dispatcher.include_router(
        creation_router(
            CreationService(database[1], "ocaso"), {}, world=world, road=road
        )
    )
    return dispatcher


@pytest.mark.parametrize(
    ("location", "result_id"),
    [
        (ROAD, "explore.tdo.estrada.fogueira"),
        (CHARNECA, "explore.tdo.charneca.pedras_negras"),
        (BOSQUE, "explore.tdo.bosque.troncos_ocos"),
    ],
)
@pytest.mark.asyncio
async def test_explore_result_return_acknowledges_once_in_each_local(
    database, monkeypatch, location, result_id
):
    actor = 881501 + (0 if location == ROAD else 1 if location == CHARNECA else 2)
    road = await _seed_local(database, actor, location)
    _force_result(monkeypatch, "atmospheric", result_id, "Resultado persistido.")
    dispatcher = _dispatcher(database, road)
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("road:explore", update_id=actor, actor=actor)
    )
    assert "Desbravar" in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot,
        callback_update("road:explore:start", update_id=actor + 10, actor=actor),
    )
    result_screen = _last_method(bot)
    assert "Resultado persistido." in result_screen.text
    result_callback = next(
        callback for callback in _callbacks(result_screen) if callback.startswith("road:local:")
    )
    attempt_id = UUID(hex=result_callback.rsplit(":", 1)[1])
    async with database[1]() as session:
        attempt = await session.get(ExplorationAttempt, attempt_id)
        assert attempt is not None
        character_id = attempt.character_id
        events_before_ack = await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id
            )
        )

    await dispatcher.feed_raw_update(
        bot, callback_update(result_callback, update_id=actor + 20, actor=actor)
    )
    local_screen = _last_method(bot)
    assert location in local_screen.text
    assert "Resultado persistido." not in local_screen.text
    async with database[1]() as session:
        attempt = await session.get(ExplorationAttempt, attempt_id)
        assert attempt is not None and attempt.result_acknowledged is True
        character_id = attempt.character_id
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == character_id
            )
        ) == 1
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id
            )
        ) == events_before_ack

    await dispatcher.feed_raw_update(
        bot, callback_update(result_callback, update_id=actor + 30, actor=actor)
    )
    duplicate = _last_method(bot)
    assert location in duplicate.text
    assert "Resultado persistido." not in duplicate.text
    await dispatcher.feed_raw_update(
        bot, _command_update("/menu", update_id=actor + 40, actor=actor)
    )
    assert "Resultado persistido." not in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot, _command_update("/start", update_id=actor + 50, actor=actor)
    )
    assert "Resultado persistido." not in _last_method(bot).text

    async with database[1]() as session:
        attempt = await session.get(ExplorationAttempt, attempt_id)
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)
        await session.commit()
    await dispatcher.feed_raw_update(
        bot, callback_update("road:explore", update_id=actor + 60, actor=actor)
    )
    await dispatcher.feed_raw_update(
        bot,
        callback_update("road:explore:start", update_id=actor + 70, actor=actor),
    )
    next_result = _last_method(bot)
    next_callback = next(
        callback
        for callback in _callbacks(next_result)
        if callback.startswith("road:local:")
    )
    next_attempt_id = UUID(hex=next_callback.rsplit(":", 1)[1])
    assert next_attempt_id != attempt_id
    async with database[1]() as session:
        events_before_stale = await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id
            )
        )
    await dispatcher.feed_raw_update(
        bot, callback_update(result_callback, update_id=actor + 80, actor=actor)
    )
    assert "Resultado persistido." in _last_message_method(bot).text
    async with database[1]() as session:
        next_attempt = await session.get(ExplorationAttempt, next_attempt_id)
        assert next_attempt is not None and next_attempt.result_acknowledged is False
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == character_id
            )
        ) == 2
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id
            )
        ) == events_before_stale


@pytest.mark.asyncio
async def test_explore_retry_acknowledges_exact_attempt_and_stale_retry_is_safe(
    database, monkeypatch
):
    actor = 881504
    road = await _seed_local(database, actor, BOSQUE)
    _force_result(
        monkeypatch,
        "atmospheric",
        "explore.tdo.bosque.troncos_ocos",
        "Resultado persistido.",
    )
    dispatcher = _dispatcher(database, road)
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, callback_update("road:explore", update_id=actor, actor=actor)
    )
    await dispatcher.feed_raw_update(
        bot,
        callback_update("road:explore:start", update_id=actor + 1, actor=actor),
    )
    async with database[1]() as session:
        attempt = await session.scalar(select(ExplorationAttempt))
        attempt_id = attempt.id
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)
        await session.commit()

    current = await road.resume(actor)
    assert current is not None and current.retry_available is True
    retry_callback = next(
        callback
        for row in render_road(current).keyboard.inline_keyboard
        for callback in [button.callback_data for button in row]
        if callback.startswith("road:explore:")
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(retry_callback, update_id=actor + 2, actor=actor)
    )
    assert _last_method(bot).text.startswith("🧭 Desbravar")
    async with database[1]() as session:
        attempt = await session.get(ExplorationAttempt, attempt_id)
        assert attempt is not None and attempt.result_acknowledged is True
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == attempt.character_id
            )
        ) == 1

    await dispatcher.feed_raw_update(
        bot, callback_update(retry_callback, update_id=actor + 3, actor=actor)
    )
    assert _last_method(bot).text.startswith("🧭 Desbravar")
    async with database[1]() as session:
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == attempt.character_id
            )
        ) == 1


@pytest.mark.asyncio
async def test_active_explore_combat_remains_foreground_and_reconnects_same_attempt(
    database, monkeypatch
):
    actor = 881505
    road = await _seed_local(database, actor, BOSQUE)
    _force_result(
        monkeypatch,
        "combat",
        "explore.tdo.bosque.combat.carnical_fuligem",
        "Um Carniçal de Fuligem bloqueia o caminho.",
    )
    dispatcher = _dispatcher(database, road)
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, callback_update("road:explore", update_id=actor, actor=actor)
    )
    await dispatcher.feed_raw_update(
        bot,
        callback_update("road:explore:start", update_id=actor + 1, actor=actor),
    )
    active = await road.resume(actor)
    assert active is not None and active.kind == "combat"
    attempt_id = active.attempt_id
    activity_id = active.activity_id
    encounter_id = active.encounter_id

    await dispatcher.feed_raw_update(
        bot, callback_update("world:map", update_id=actor + 2, actor=actor)
    )
    blocked = _last_message_method(bot)
    assert any(callback.startswith("fight:") for callback in _callbacks(blocked))
    resumed = await road.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert (resumed.attempt_id, resumed.activity_id, resumed.encounter_id) == (
        attempt_id,
        activity_id,
        encounter_id,
    )
    async with database[1]() as session:
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == resumed.character_id
            )
        ) == 1
        activity = await session.get(GameActivity, activity_id)
        assert activity is not None and activity.status == "active"
