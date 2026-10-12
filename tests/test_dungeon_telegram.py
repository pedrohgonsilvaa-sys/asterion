from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.dungeons import DungeonService
from asterion.bot.combat_ui import DungeonCombatCallback
from asterion.bot.dungeon_handlers import dungeon_router
from asterion.bot.dungeon_ui import render_dungeons
from asterion.infrastructure.db.models import GameActivity
from tests.test_creation_ui import callback_update
from tests.test_tdo_crypt import _seed


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _button(screen, label):
    return next(
        button for row in screen.keyboard.inline_keyboard for button in row if button.text == label
    )


@pytest.mark.asyncio
async def test_clicking_attack_in_crypt_routes_through_the_live_dungeon_service(database):
    actor = 774405
    character_id, sessions = await _seed(database, actor=actor)
    service = DungeonService(sessions, "ocaso")
    lobby = await service.start_solo(actor, "stable")
    fight = await service.begin_encounter(actor, lobby.run_id, lobby.state_version)
    screen = render_dungeons(fight)
    attack = _button(screen, "Atacar")
    assert attack.callback_data.startswith("df:")
    assert len(attack.callback_data.encode("utf-8")) <= 64
    callback = DungeonCombatCallback.unpack(attack.callback_data)
    assert callback.run == fight.run_id.hex[:16]
    assert callback.activity_id == fight.activity_id

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot,
        callback_update(attack.callback_data, update_id=774406, actor=actor),
    )

    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.combat.version == fight.combat.version + 1
    async with sessions() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == fight.activity_id)
        )
        assert activity.state_version == resumed.combat.version

    current_attack = _button(render_dungeons(resumed), "Atacar")
    current = DungeonCombatCallback.unpack(current_attack.callback_data)
    forged_indices = DungeonCombatCallback(
        run=current.run,
        activity=current.activity,
        version=current.version,
        action="-1",
        target="d0",
    ).pack()
    forged_target = DungeonCombatCallback(
        run=current.run,
        activity=current.activity,
        version=current.version,
        action=current.action,
        target="z",
    ).pack()
    await dispatcher.feed_raw_update(
        bot, callback_update(forged_indices, update_id=774407, actor=actor)
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(forged_target, update_id=774408, actor=actor)
    )
    after_forgery = await service.resume(actor)
    assert after_forgery is not None
    assert after_forgery.combat.version == resumed.combat.version


@pytest.mark.asyncio
async def test_explicit_unknown_dungeon_family_resumes_without_falling_back_to_crypt():
    actor = 774410
    service = AsyncMock()
    service.resume.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot,
        callback_update("dungeon:start:x:s", update_id=774411, actor=actor),
    )

    service.resume.assert_awaited_once_with(actor)
    service.start_solo.assert_not_awaited()
    service.detail.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_dungeon_start_callback_still_targets_the_crypt():
    actor = 774412
    service = AsyncMock()
    service.start_solo.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot,
        callback_update("dungeon:start:s", update_id=774413, actor=actor),
    )

    service.start_solo.assert_awaited_once_with(
        actor, "stable", "dungeon.tdo.cripta_ocaso"
    )
