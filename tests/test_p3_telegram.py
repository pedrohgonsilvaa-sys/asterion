from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.p3 import P3_ID, P3View
from asterion.application.prologue import PrologueService
from asterion.application.road import BOSQUE, CHARNECA, RoadService
from asterion.application.s2 import S2Service
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import CombatConsumableFlowCallback, P3CombatCallback
from asterion.bot.creation_handlers import creation_router
from asterion.bot.p3_handlers import p3_router
from asterion.bot.p3_ui import render_p3
from asterion.bot.world_handlers import world_router
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import (
    Character,
    ConsumableStack,
    LocationDiscovery,
    Quest,
    Unlock,
    WorldState,
)
from tests.test_creation_ui import callback_update, message_update
from tests.test_p3_integration import _seed_p3, _start_scripted_combat


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _last_method(bot):
    return bot.session.make_request.call_args.args[1]


def _command_update(text: str, update_id: int, actor: int):
    update = message_update(text, update_id=update_id, actor=actor)
    update["message"]["entities"] = [
        {"type": "bot_command", "offset": 0, "length": len(text)}
    ]
    return update


def test_p3_group_combat_prompt_is_explicit_and_callbacks_are_compact():
    view = P3View(
        character_id=uuid4(),
        kind="combat_pending",
        status="active",
        step=3,
        state_version=17,
        progress={"fragments": ["p3.fragment.1", "p3.fragment.2", "p3.fragment.3"]},
        location=BOSQUE,
        level=9,
        group_size=2,
    )
    screen = render_p3(view)
    buttons = {
        button.text: button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    assert "Propor combate em Grupo" in buttons
    assert buttons["Propor combate em Grupo"] == "p3:17:group"
    assert "Enfrentar Solo" in buttons
    assert all(len(callback.encode("utf-8")) <= 64 for callback in buttons.values())

    pending = render_p3(replace(view, proposal_id=uuid4(), proposal_status="pending"))
    pending_buttons = {
        button.text
        for row in pending.keyboard.inline_keyboard
        for button in row
    }
    assert "Abrir Grupo" in pending_buttons
    assert "Enfrentar Solo" not in pending_buttons


@pytest.mark.asyncio
async def test_p3_oren_offer_is_read_only_until_explicit_accept(database):
    actor = 998321
    character_id, p3 = await _seed_p3(database, actor)
    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    dispatcher.include_router(p3_router(p3, {}))
    dispatcher.include_router(world_router(world, {}, road=road, p3=p3))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("world:oren", update_id=998322, actor=actor)
    )
    oren = _last_method(bot)
    assert "Oren Cal" in oren.text
    assert any(
        button.callback_data == "p3:offer"
        for row in oren.reply_markup.inline_keyboard
        for button in row
    )

    await dispatcher.feed_raw_update(
        bot, callback_update("p3:offer", update_id=998323, actor=actor)
    )
    offer = _last_method(bot)
    assert "Sob Galhos Calcinados" in offer.text
    accept = next(
        button.callback_data
        for row in offer.reply_markup.inline_keyboard
        for button in row
        if button.text == "Aceitar Missão"
    )
    async with database[1]() as session:
        assert await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P3_ID)
        ) is None

    await dispatcher.feed_raw_update(
        bot, callback_update(accept, update_id=998324, actor=actor)
    )
    assert "Viajar até a Charneca da Fuligem" in _last_method(bot).text
    async with database[1]() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P3_ID)
        )
        assert quest is not None and quest.status == "active" and quest.step == 1


@pytest.mark.asyncio
async def test_p3_combat_callback_start_and_menu_reconnect_same_activity(database):
    actor = 998325
    _, p3 = await _seed_p3(database, actor)
    combat = await _start_scripted_combat(p3, actor)
    world = WorldService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(
        PrologueService(database[1], "ocaso", PROFILE), {}, world, road, p3=p3
    ))
    dispatcher.include_router(world_router(world, {}, road=road, p3=p3))
    dispatcher.include_router(
        creation_router(CreationService(database[1], "ocaso"), {}, world=world, road=road, p3=p3)
    )
    bot = _telegram()

    screen = render_p3(combat)
    attack = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Atacar"
    )
    assert attack.callback_data.startswith("p3fight:")
    callback = P3CombatCallback.unpack(attack.callback_data)
    await dispatcher.feed_raw_update(
        bot, callback_update(attack.callback_data, update_id=998326, actor=actor)
    )
    after_action = await p3.resume(actor)
    assert after_action is not None and after_action.activity_id == combat.activity_id
    assert after_action.combat.version == combat.combat.version + 1
    expected = (
        after_action.activity_id,
        after_action.encounter_id,
        after_action.combat_id,
        after_action.activity_state_version,
    )
    assert callback.activity_id == after_action.activity_id

    await dispatcher.feed_raw_update(
        bot, _command_update("/menu", update_id=998327, actor=actor)
    )
    assert "Combate de Missão" in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot, _command_update("/start", update_id=998328, actor=actor)
    )
    assert "Combate de Missão" in _last_method(bot).text
    resumed = await p3.resume(actor)
    assert (
        resumed.activity_id,
        resumed.encounter_id,
        resumed.combat_id,
        resumed.activity_state_version,
    ) == expected


@pytest.mark.asyncio
async def test_start_prefers_active_p3_over_narrative_s2(database):
    actor = 998341
    character_id, p3 = await _seed_p3(database, actor)
    accepted = await p3.accept(actor)
    assert accepted is not None
    async with database[1].begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id="S2",
                title="Os Nomes Esquecidos",
                status="active",
                step=1,
                content_version="tdo-1.0.9",
                state_version=0,
                progress={},
            )
        )

    world = WorldService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        creation_router(
            CreationService(database[1], "ocaso"),
            {},
            world=world,
            road=road,
            s2=S2Service(database[1], "ocaso"),
            p3=p3,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, _command_update("/start", update_id=998342, actor=actor)
    )
    assert "Sob Galhos Calcinados" in _last_method(bot).text


@pytest.mark.asyncio
async def test_p3_combat_consumable_selection_and_use_are_persisted_once(database):
    actor = 998337
    character_id, p3 = await _seed_p3(database, actor)
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        character.hp = character.max_hp / 2
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id="consumable.heal",
                quantity=2,
            )
        )
    combat = await _start_scripted_combat(p3, actor)
    assert any(option.item_id == "consumable.heal" for option in combat.consumable_options)

    world = WorldService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        combat_router(PrologueService(database[1], "ocaso", PROFILE), {}, world, road, p3=p3)
    )
    bot = _telegram()
    open_menu = CombatConsumableFlowCallback.for_step(
        combat.activity_id, combat.combat.version, "o"
    ).pack()
    await dispatcher.feed_raw_update(
        bot, callback_update(open_menu, update_id=998338, actor=actor)
    )
    assert "Consumíveis" in _last_method(bot).text
    choose_heal = next(
        button.callback_data
        for row in _last_method(bot).reply_markup.inline_keyboard
        for button in row
        if button.callback_data and button.callback_data.startswith("cf:")
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(choose_heal, update_id=998339, actor=actor)
    )
    after = await p3.resume(actor)
    assert after is not None and after.activity_id == combat.activity_id
    assert after.combat.version == combat.combat.version + 1
    async with database[1]() as session:
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.heal",
            )
        )
        assert stack.quantity == 1
    await dispatcher.feed_raw_update(
        bot, callback_update(choose_heal, update_id=998340, actor=actor)
    )
    async with database[1]() as session:
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.heal",
            )
        )
        assert stack.quantity == 1


@pytest.mark.asyncio
async def test_bosque_map_does_not_auto_open_p3_and_mission_remains_reachable(database):
    actor = 998329
    _, p3 = await _seed_p3(database, actor)
    accepted = await p3.accept(actor)
    to_charneca = await p3.mission_route(actor, accepted.state_version, CHARNECA)
    entered = await p3.enter_bosque(actor, to_charneca.state_version)
    assert entered.location == BOSQUE

    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    dispatcher.include_router(world_router(world, {}, road=road, p3=p3))
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, callback_update("world:map:region:tdo", update_id=998330, actor=actor)
    )
    region = _last_method(bot)
    bosque_button = next(
        button
        for row in region.reply_markup.inline_keyboard
        for button in row
        if button.callback_data == "world:map:local:bosque"
    )
    assert bosque_button.text.isdigit()
    await dispatcher.feed_raw_update(
        bot, callback_update(bosque_button.callback_data, update_id=998331, actor=actor)
    )
    place = _last_method(bot)
    assert "Fragmentos de Construção" not in place.text
    assert "world:local" in [
        button.callback_data
        for row in place.reply_markup.inline_keyboard
        for button in row
    ]
    await dispatcher.feed_raw_update(
        bot, callback_update("world:local", update_id=998337, actor=actor)
    )
    local = _last_method(bot)
    assert "world:missions" in [
        button.callback_data
        for row in local.reply_markup.inline_keyboard
        for button in row
    ]
    await dispatcher.feed_raw_update(
        bot, callback_update("world:missions", update_id=998338, actor=actor)
    )
    missions = _last_method(bot)
    assert "Sob Galhos Calcinados · Em Andamento" in missions.text
    await dispatcher.feed_raw_update(
        bot, callback_update("world:principal", update_id=998339, actor=actor)
    )
    assert "fragmentos de construção" in _last_method(bot).text


@pytest.mark.asyncio
async def test_completed_p3_map_exposes_bosque_and_route(database):
    actor = 998332
    character_id, p3 = await _seed_p3(database, actor)
    async with database[1].begin() as session:
        world_state = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        world_state.location = CHARNECA
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id=P3_ID,
                    title="Sob Galhos Calcinados",
                    status="completed",
                    step=6,
                    content_version="tdo-1.0.10",
                    progress={"bosque_entered": True, "selected_reward": "veil"},
                ),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="tdo.location.bosque_calcinado",
                ),
                *[
                    Unlock(character_id=character_id, unlock_id=unlock_id)
                    for unlock_id in (
                        "route.tdo.charneca_bosque",
                        "hunt_manual.bosque_calcinado",
                        "explore.bosque_calcinado",
                        "hunt_manual.charneca_da_fuligem",
                        "explore.charneca_da_fuligem",
                    )
                ],
            ]
        )
    world = WorldService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(world_router(world, {}, road=road, p3=p3))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("world:map:region:tdo", update_id=998333, actor=actor)
    )
    region = _last_method(bot)
    assert any(
        button.callback_data == "world:map:local:bosque"
        for row in region.reply_markup.inline_keyboard
        for button in row
    )
    await dispatcher.feed_raw_update(
        bot, callback_update("world:map:local:bosque", update_id=998334, actor=actor)
    )
    accessible = _last_method(bot)
    route_button = next(
        button
        for row in accessible.reply_markup.inline_keyboard
        for button in row
        if button.callback_data == "road:route:bosque"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(route_button.callback_data, update_id=998335, actor=actor)
    )
    assert "📍 Local Atual\n🌲 Bosque Calcinado" in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot, callback_update("world:map:local:bosque", update_id=998336, actor=actor)
    )
    bosque = _last_method(bot)
    assert "Bosque Calcinado · Local Atual" in bosque.text
    callbacks = [
        button.callback_data
        for row in bosque.reply_markup.inline_keyboard
        for button in row
    ]
    assert "world:local" in callbacks
    assert "road:prepare" not in callbacks
    assert "road:explore" not in callbacks
    assert "road:route:charneca" in callbacks
    assert "Caçar" not in [
        button.text for row in bosque.reply_markup.inline_keyboard for button in row
    ]
    await dispatcher.feed_raw_update(
        bot, callback_update("world:local", update_id=998337, actor=actor)
    )
    local = _last_method(bot)
    assert "Caçar" in [button.text for row in local.reply_markup.inline_keyboard for button in row]
    assert "road:hunt" in [
        button.callback_data
        for row in local.reply_markup.inline_keyboard
        for button in row
    ]
