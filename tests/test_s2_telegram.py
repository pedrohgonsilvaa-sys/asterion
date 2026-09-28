from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import CombatConsumableFlowCallback, S2CombatCallback
from asterion.bot.creation_handlers import creation_router
from asterion.bot.s2_handlers import s2_router
from asterion.bot.s2_ui import render_s2
from asterion.bot.world_handlers import world_router
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import ConsumableStack, GameActivity
from tests.test_creation_ui import callback_update, message_update
from tests.test_s2_integration import _seed_s2, _start_scripted_combat


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


@pytest.mark.asyncio
async def test_s2_combat_callback_and_start_menu_reconnect_same_foreground(database):
    actor = 997201
    _, s2 = await _seed_s2(database, actor)
    combat = await _start_scripted_combat(s2, actor)
    dispatcher = Dispatcher(disable_fsm=True)
    prologue = PrologueService(database[1], "ocaso", PROFILE)
    road = RoadService(database[1], "ocaso")
    world = WorldService(database[1], "ocaso")
    dispatcher.include_router(s2_router(s2, {}))
    dispatcher.include_router(combat_router(prologue, {}, world, road, s2=s2))
    dispatcher.include_router(world_router(world, {}, road=road, s2=s2))
    dispatcher.include_router(
        creation_router(
            CreationService(database[1], "ocaso"),
            {},
            road=road,
            s2=s2,
        )
    )
    bot = _telegram()

    screen = render_s2(combat)
    assert "Os Nomes Esquecidos · Combate" in screen.text
    attack = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Atacar"
    )
    callback = S2CombatCallback.unpack(attack.callback_data)
    assert callback.activity_id == combat.activity_id
    assert callback.version == combat.combat.version
    await dispatcher.feed_raw_update(
        bot,
        callback_update(attack.callback_data, update_id=997202, actor=actor),
    )
    after_action = await s2.resume(actor)
    assert after_action.kind == "combat"
    assert after_action.combat.version == combat.combat.version + 1

    ids_before = (
        after_action.activity_id,
        after_action.encounter_id,
        after_action.combat_id,
        after_action.activity_state_version,
    )
    await dispatcher.feed_raw_update(
        bot,
        _command_update("/menu", update_id=997203, actor=actor),
    )
    menu_screen = _last_method(bot)
    assert "Os Nomes Esquecidos · Combate" in menu_screen.text
    await dispatcher.feed_raw_update(
        bot,
        _command_update("/start", update_id=997204, actor=actor),
    )
    start_screen = _last_method(bot)
    assert "Os Nomes Esquecidos · Combate" in start_screen.text
    after_reconnect = await s2.resume(actor)
    assert (
        after_reconnect.activity_id,
        after_reconnect.encounter_id,
        after_reconnect.combat_id,
        after_reconnect.activity_state_version,
    ) == ids_before
    async with database[1]() as session:
        active = (
            await session.scalars(
                select(GameActivity).where(
                    GameActivity.character_id == after_action.character_id,
                    GameActivity.status == "active",
                )
            )
        ).all()
        assert [row.id for row in active] == [combat.activity_id]


@pytest.mark.asyncio
async def test_s2_router_offer_accept_camp_vestiges_and_immediate_combat(database):
    actor = 997205
    _, service = await _seed_s2(database, actor)
    dispatcher = Dispatcher(disable_fsm=True)
    world = WorldService(database[1], "ocaso")
    road = RoadService(database[1], "ocaso")
    dispatcher.include_router(s2_router(service, {}))
    dispatcher.include_router(world_router(world, {}, road=road, s2=service))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("s2:oren", update_id=997206, actor=actor)
    )
    oren = _last_method(bot)
    assert "Os Nomes Esquecidos · Disponível" in oren.text
    offer_callback = next(
        button.callback_data
        for row in oren.reply_markup.inline_keyboard
        for button in row
        if button.text == "Os Nomes Esquecidos"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(offer_callback, update_id=997207, actor=actor)
    )
    offer = _last_method(bot)
    assert "XP · 2.695" in offer.text
    accept_callback = next(
        button.callback_data
        for row in offer.reply_markup.inline_keyboard
        for button in row
        if button.text == "Aceitar Missão"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(accept_callback, update_id=997208, actor=actor)
    )
    accepted = _last_method(bot)
    assert "Encontrar o acampamento abandonado" in accepted.text
    route_callback = next(
        button.callback_data
        for row in accepted.reply_markup.inline_keyboard
        for button in row
        if button.text == "Seguir para a Charneca"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(route_callback, update_id=997209, actor=actor)
    )
    at_charneca = _last_method(bot)
    assert "Encontrar o acampamento abandonado" in at_charneca.text
    camp_callback = next(
        button.callback_data
        for row in at_charneca.reply_markup.inline_keyboard
        for button in row
        if button.text == "Examinar acampamento"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(camp_callback, update_id=997210, actor=actor)
    )
    for update_id in (997211, 997212, 997213):
        current = _last_method(bot)
        vestige_callback = next(
            button.callback_data
            for row in current.reply_markup.inline_keyboard
            for button in row
            if ":vestige:" in button.callback_data
        )
        await dispatcher.feed_raw_update(
            bot,
            callback_update(vestige_callback, update_id=update_id, actor=actor),
        )
    assert "Os Nomes Esquecidos · Combate" in _last_method(bot).text
    current = await service.resume(actor)
    assert current.kind == "combat"
    assert current.activity_id is not None


@pytest.mark.asyncio
async def test_s2_combat_consumable_is_selectable_through_shared_telegram_flow(database):
    actor = 997214
    character_id, s2 = await _seed_s2(database, actor)
    async with database[1].begin() as session:
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id="consumable.protection.vde.ii",
                quantity=2,
            )
        )
    combat = await _start_scripted_combat(s2, actor)
    dispatcher = Dispatcher(disable_fsm=True)
    prologue = PrologueService(database[1], "ocaso", PROFILE)
    road = RoadService(database[1], "ocaso")
    world = WorldService(database[1], "ocaso")
    dispatcher.include_router(combat_router(prologue, {}, world, road, s2=s2))
    bot = _telegram()

    screen = render_s2(combat)
    open_callback = next(
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Consumível"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(open_callback, update_id=997215, actor=actor)
    )
    items_screen = _last_method(bot)
    assert "Consumíveis" in items_screen.text
    choose_item = next(
        button.callback_data
        for row in items_screen.reply_markup.inline_keyboard
        for button in row
        if button.callback_data.startswith("cf:")
        and CombatConsumableFlowCallback.unpack(button.callback_data).item_id
        == "consumable.protection.vde.ii"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(choose_item, update_id=997216, actor=actor)
    )
    after_use = await s2.resume(actor)
    assert after_use.kind == "combat" and after_use.combat.consumable_uses == 1
    assert after_use.activity_state_version == combat.activity_state_version + 1

    # Replaying the old selection callback cannot consume a second unit.
    await dispatcher.feed_raw_update(
        bot, callback_update(choose_item, update_id=997217, actor=actor)
    )
    current = await s2.resume(actor)
    assert current.combat.consumable_uses == 1
    async with database[1]() as session:
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.protection.vde.ii",
            )
        )
        assert stack.quantity == 1
