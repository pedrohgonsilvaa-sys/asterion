from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.s4 import S4Service
from asterion.application.s5 import S5Service
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import S4CombatCallback, S5CombatCallback
from asterion.bot.creation_handlers import creation_router
from asterion.bot.s4_handlers import s4_router
from asterion.bot.s4_ui import render_s4
from asterion.bot.s5_handlers import s5_router
from asterion.bot.s5_ui import render_s5
from asterion.bot.world_handlers import world_router
from asterion.domain.creation import NamePolicy
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import Quest
from tests.test_creation_ui import callback_update, message_update
from tests.test_s4_s5_integration import _seed_p4, _start_s4, _start_s5


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _last_method(bot):
    return bot.session.make_request.call_args.args[1]


def _button(screen, label):
    return next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == label
    )


def _command_update(text: str, update_id: int, actor: int):
    update = message_update(text, update_id=update_id, actor=actor)
    update["message"]["entities"] = [
        {"type": "bot_command", "offset": 0, "length": len(text)}
    ]
    return update


@pytest.mark.asyncio
async def test_oren_and_missions_expose_s4_and_s5_together_without_accepting(database):
    actor = 998621
    character_id, sessions = await _seed_p4(database, actor, level=8)
    s4 = S4Service(sessions, "ocaso")
    s5 = S5Service(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"), {},
            road=RoadService(sessions, "ocaso"), s4=s4, s5=s5,
        )
    )
    dispatcher.include_router(s4_router(s4, {}))
    dispatcher.include_router(s5_router(s5, {}))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("world:oren", update_id=998622, actor=actor)
    )
    oren = _last_method(bot)
    assert "Vigília sem Voz · Disponível" in oren.text
    assert "A Luz que Não Aquece · Disponível" in oren.text
    assert _button(render_s4(await s4.offer(actor)), "Aceitar Missão")
    assert _button(render_s5(await s5.offer(actor)), "Aceitar Missão")

    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == "S4")
        ) is None
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == "S5")
        ) is None

    await dispatcher.feed_raw_update(
        bot, callback_update("world:missions", update_id=998623, actor=actor)
    )
    missions = _last_method(bot)
    assert "Vigília sem Voz · Disponível" in missions.text
    assert "A Luz que Não Aquece · Disponível" in missions.text
    mission_buttons = {
        button.callback_data: button.text
        for row in missions.reply_markup.inline_keyboard
        for button in row
    }
    assert mission_buttons["s4:offer"] == "1"
    assert mission_buttons["s5:offer"] == "2"

    for mission, update_id in (("s4", 998627), ("s5", 998629)):
        await dispatcher.feed_raw_update(
            bot, callback_update(f"{mission}:offer", update_id=update_id, actor=actor)
        )
        offer = _last_method(bot)
        accept = _button(
            SimpleNamespace(keyboard=offer.reply_markup), "Aceitar Missão"
        ).callback_data
        await dispatcher.feed_raw_update(
            bot, callback_update(accept, update_id=update_id + 1, actor=actor)
        )
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.status).where(Quest.character_id == character_id, Quest.quest_id == "S4")
        ) == "active"
        assert await session.scalar(
            select(Quest.status).where(Quest.character_id == character_id, Quest.quest_id == "S5")
        ) == "active"


@pytest.mark.asyncio
@pytest.mark.parametrize("mission", ["s4", "s5"])
async def test_menu_restores_s4_and_s5_scripted_combat(database, mission):
    actor = 998624 if mission == "s4" else 998625
    character_id, sessions = await _seed_p4(database, actor, level=8)
    s4 = S4Service(sessions, "ocaso")
    s5 = S5Service(sessions, "ocaso")
    if mission == "s4":
        await _start_s4(actor, s4, sessions, character_id)
    else:
        await _start_s5(actor, s5, sessions, character_id)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"), {},
            road=RoadService(sessions, "ocaso"), s4=s4, s5=s5,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, _command_update("/menu", update_id=998626, actor=actor)
    )
    response = _last_method(bot)
    expected_title = "Vigília sem Voz" if mission == "s4" else "A Luz que Não Aquece"
    assert expected_title in response.text
    assert "Encontro de Missão" in response.text
    assert "Turno" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("mission", ["s4", "s5"])
async def test_start_restores_s4_and_s5_scripted_combat(database, mission):
    actor = 998631 if mission == "s4" else 998632
    character_id, sessions = await _seed_p4(database, actor, level=8)
    s4 = S4Service(sessions, "ocaso")
    s5 = S5Service(sessions, "ocaso")
    if mission == "s4":
        await _start_s4(actor, s4, sessions, character_id)
    else:
        await _start_s5(actor, s5, sessions, character_id)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        creation_router(
            CreationService(sessions, "ocaso", NamePolicy()),
            {},
            s4=s4,
            s5=s5,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, _command_update("/start", update_id=998633, actor=actor)
    )
    response = _last_method(bot)
    expected_title = "Vigília sem Voz" if mission == "s4" else "A Luz que Não Aquece"
    assert expected_title in response.text
    assert "Encontro de Missão" in response.text
    assert "Turno" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("mission", ["s4", "s5"])
async def test_s4_s5_combat_action_callbacks_are_routed(database, mission):
    actor = 998641 if mission == "s4" else 998642
    character_id, sessions = await _seed_p4(database, actor, level=8)
    s4 = S4Service(sessions, "ocaso")
    s5 = S5Service(sessions, "ocaso")
    view = (
        await _start_s4(actor, s4, sessions, character_id)
        if mission == "s4"
        else await _start_s5(actor, s5, sessions, character_id)
    )
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        combat_router(
            PrologueService(sessions, "ocaso", PROFILE),
            {},
            road=RoadService(sessions, "ocaso"),
            s4=s4,
            s5=s5,
        )
    )
    bot = _telegram()
    callback_type = S4CombatCallback if mission == "s4" else S5CombatCallback
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            callback_type(
                activity=view.activity_id.hex,
                version=view.combat.version,
                action="attack",
            ).pack(),
            update_id=998643 if mission == "s4" else 998644,
            actor=actor,
        ),
    )
    response = _last_method(bot)
    expected_title = "Vigília sem Voz" if mission == "s4" else "A Luz que Não Aquece"
    assert expected_title in response.text
    assert "Encontro de Missão" in response.text


@pytest.mark.asyncio
async def test_s4_s5_routers_are_registered_by_runtime(monkeypatch):
    import asterion.bot.runtime as runtime

    settings = SimpleNamespace(
        telegram_bot_enabled=True,
        telegram_bot_token="123456:local-test-token",
        server_id="ocaso",
        creation_images={},
        blocked_character_names=(),
        community_chat_id=None,
        community_market_topic_id=None,
        community_relatos_topic_id=None,
        community_url=None,
        rate_limit_burst=12,
        rate_limit_per_second=4.0,
        contracts_enabled=False,
        ttk_telemetry=False,
        build_version="test",
    )
    monkeypatch.setattr(runtime, "get_settings", lambda: settings)
    runtime.get_bot_runtime.cache_clear()
    bot_runtime = runtime.get_bot_runtime()
    names = {router.name for router in bot_runtime.dispatcher.sub_routers}
    assert {"s4", "s5", "world", "foreground_combat", "character_creation"} <= names
    await bot_runtime.bot.session.close()
    runtime.get_bot_runtime.cache_clear()
