from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher

from asterion.application.p6 import P6Service
from asterion.application.prologue import PrologueService
from asterion.application.road import RUINS, RoadService
from asterion.application.s6 import S6_MARKS, S6Service
from asterion.bot.combat_handlers import combat_router
from asterion.bot.p6_ui import render_p6
from asterion.bot.s6_handlers import s6_router
from asterion.bot.s6_ui import render_s6
from asterion.domain.prologue import PROFILE
from tests.test_creation_ui import callback_update
from tests.test_s4_s5_integration import _set_location
from tests.test_s6_p6_integration import _ready_p6_character, _seed_final_campaign


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _last_method(bot):
    return bot.session.make_request.call_args.args[1]


def _fight_button(screen, prefix):
    return next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith(f"{prefix}:")
    )


def _button(screen, label):
    return next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == label
    )


def _advance_one(combat, _action, **_kwargs):
    updated = deepcopy(combat)
    updated.version += 1
    return updated


@pytest.mark.asyncio
async def test_s6fight_callback_executes_shared_combat_and_renders_again(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998931
    character_id, sessions = await _seed_final_campaign(database, actor)
    service = S6Service(sessions, "ocaso")
    offer = await service.oren(actor)
    accepted = await service.accept(actor, offer.state_version)
    reviewed = await service.action(actor, accepted.state_version, "review")
    await _set_location(sessions, character_id, RUINS)
    marked = reviewed
    for mark in S6_MARKS:
        marked = await service.action(actor, marked.state_version, "mark", mark)
    pending = await service.action(actor, marked.state_version, "shelter")
    assert pending is not None and pending.kind == "combat_pending"
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(s6_router(service, {}))
    dispatcher.include_router(
        combat_router(
            PrologueService(sessions, "ocaso", PROFILE),
            {},
            road=RoadService(sessions, "ocaso"),
            s6=service,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(render_s6(pending), "Enfrentar Solo").callback_data,
            update_id=998931,
            actor=actor,
        ),
    )
    combat = await service.resume(actor)
    assert combat is not None and combat.kind == "combat"

    monkeypatch.setattr(scripted_combat, "act", _advance_one)
    button = _fight_button(render_s6(combat), "s6fight")
    assert len(button.callback_data.encode("utf-8")) <= 64
    await dispatcher.feed_raw_update(
        bot, callback_update(button.callback_data, update_id=998932, actor=actor)
    )
    response = _last_method(bot)
    current = await service.resume(actor)
    assert current is not None and current.kind == "combat"
    assert current.activity_id == combat.activity_id
    assert current.combat.version == combat.combat.version + 1
    assert "Onde os Nomes Terminaram · Encontro de Missão" in response.text
    assert "Turno" in response.text


@pytest.mark.asyncio
async def test_p6fight_callback_executes_shared_combat_and_renders_again(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998941
    character_id, sessions = await _seed_final_campaign(database, actor)
    await _ready_p6_character(sessions, character_id)
    service = P6Service(sessions, "ocaso")
    initial = await service.resume(actor)
    assert initial is not None and initial.guidance is None
    await _set_location(sessions, character_id, RUINS)
    crossed = await service.action(actor, initial.state_version, "cross_door")
    chamber = await service.action(actor, crossed.state_version, "enter_chamber")
    structure = await service.action(actor, chamber.state_version, "inspect_before")
    combat = await service.action(actor, structure.state_version, "start_boss")
    assert combat is not None and combat.kind == "combat"

    monkeypatch.setattr(scripted_combat, "act", _advance_one)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        combat_router(
            PrologueService(sessions, "ocaso", PROFILE),
            {},
            road=RoadService(sessions, "ocaso"),
            p6=service,
        )
    )
    bot = _telegram()
    button = _fight_button(render_p6(combat), "p6fight")
    assert len(button.callback_data.encode("utf-8")) <= 64
    await dispatcher.feed_raw_update(
        bot, callback_update(button.callback_data, update_id=998942, actor=actor)
    )
    response = _last_method(bot)
    current = await service.resume(actor)
    assert current is not None and current.kind == "combat"
    assert current.activity_id == combat.activity_id
    assert current.combat.version == combat.combat.version + 1
    assert "O Vigia Partido · Câmara do Poente" in response.text
    assert "Turno" in response.text
