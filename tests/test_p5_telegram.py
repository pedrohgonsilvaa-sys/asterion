from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.p2 import P2Service
from asterion.application.p4 import P4Service
from asterion.application.p5 import P5_ID, P5Service
from asterion.application.prologue import PrologueService
from asterion.application.road import REFUGE, RUINS, RoadService
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import P5CombatCallback
from asterion.bot.creation_handlers import creation_router
from asterion.bot.p2_handlers import p2_router
from asterion.bot.p5_handlers import p5_router
from asterion.bot.p5_ui import render_p5
from asterion.bot.world_handlers import world_router
from asterion.domain.creation import NamePolicy
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import Quest
from tests.test_creation_ui import callback_update, message_update
from tests.test_p5_integration import _start_combat
from tests.test_s4_s5_integration import _seed_p4, _set_location, _terminal


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
async def test_alda_offer_and_missions_menu_do_not_create_p5_until_accept(database):
    actor = 998711
    character_id, sessions = await _seed_p4(database, actor, level=9)
    p4 = P4Service(sessions, "ocaso")
    p5 = P5Service(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(p2_router(P2Service(sessions, "ocaso"), {}, p4=p4, p5=p5))
    dispatcher.include_router(p5_router(p5, {}))
    dispatcher.include_router(
        world_router(WorldService(sessions, "ocaso"), {}, p4=p4, p5=p5)
    )
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("p2:alda", update_id=998712, actor=actor)
    )
    alda = _last_method(bot)
    assert "Alda Veyr" in alda.text and "Refúgio do Ocaso" in alda.text
    mission_button = _button(
        type("ScreenRef", (), {"keyboard": alda.reply_markup})(), "A Porta do Poente"
    )
    assert mission_button.callback_data == "p5:offer"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == P5_ID)
        ) is None

    await dispatcher.feed_raw_update(
        bot, callback_update("world:missions", update_id=998713, actor=actor)
    )
    missions = _last_method(bot)
    assert "A Porta do Poente · Disponível" in missions.text
    assert _button(
        type("ScreenRef", (), {"keyboard": missions.reply_markup})(), "Principal"
    ).callback_data == "p5:offer"

    await dispatcher.feed_raw_update(
        bot, callback_update(mission_button.callback_data, update_id=998714, actor=actor)
    )
    offer = _last_method(bot)
    accept = _button(
        type("ScreenRef", (), {"keyboard": offer.reply_markup})(), "Aceitar Missão"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(accept.callback_data, update_id=998715, actor=actor)
    )
    assert "Seguir as estruturas" in _last_method(bot).text
    async with sessions() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P5_ID)
        )
        assert quest is not None and quest.status == "active" and quest.step == 1


@pytest.mark.asyncio
async def test_p5fight_attack_callback_routes_to_service_and_stale_click_is_safe(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998716
    character_id, sessions = await _seed_p4(database, actor, level=9)
    p5 = P5Service(sessions, "ocaso")
    combat = await _start_combat(p5, actor, sessions, character_id)
    assert combat is not None and combat.combat is not None

    def advance_once(state, action):
        updated = deepcopy(state)
        updated.version += 1
        return updated

    monkeypatch.setattr(scripted_combat, "act", advance_once)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        combat_router(
            PrologueService(sessions, "ocaso", PROFILE),
            {},
            road=RoadService(sessions, "ocaso"),
            p5=p5,
        )
    )
    bot = _telegram()
    screen = render_p5(combat)
    action_button = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith("p5fight:")
    )
    callback_data = action_button.callback_data
    assert len(callback_data.encode("utf-8")) <= 64
    callback = P5CombatCallback.unpack(callback_data)
    assert callback.action == "attack"

    await dispatcher.feed_raw_update(
        bot, callback_update(callback_data, update_id=998717, actor=actor)
    )
    response = _last_method(bot)
    assert "A Porta do Poente · Encontro de Missão" in response.text
    assert "Turno" in response.text
    current = await p5.resume(actor)
    assert current is not None and current.kind == "combat"
    assert current.activity_id == combat.activity_id
    assert current.combat.version == combat.combat.version + 1

    await dispatcher.feed_raw_update(
        bot, callback_update(callback_data, update_id=998718, actor=actor)
    )
    after_stale = await p5.resume(actor)
    assert after_stale is not None and after_stale.combat.version == current.combat.version


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/menu", "/start"])
async def test_p5_combat_is_restored_by_menu_and_start(database, command):
    actor = 998719 if command == "/menu" else 998720
    character_id, sessions = await _seed_p4(database, actor, level=9)
    p5 = P5Service(sessions, "ocaso")
    combat = await _start_combat(p5, actor, sessions, character_id)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            road=RoadService(sessions, "ocaso"),
            p5=p5,
        )
    )
    dispatcher.include_router(
        creation_router(
            CreationService(sessions, "ocaso", NamePolicy()),
            {},
            p5=p5,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, _command_update(command, update_id=998721, actor=actor)
    )
    response = _last_method(bot)
    assert "A Porta do Poente · Encontro de Missão" in response.text
    assert "Custódio do Poente · Nv.9" in response.text
    resumed = await p5.resume(actor)
    assert resumed is not None and resumed.activity_id == combat.activity_id
    assert resumed.encounter_id == combat.encounter_id


@pytest.mark.asyncio
async def test_p5_stage_and_report_screens_follow_real_callbacks(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998722
    character_id, sessions = await _seed_p4(database, actor, level=9)
    p5 = P5Service(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(p5_router(p5, {}))
    dispatcher.include_router(
        combat_router(
            PrologueService(sessions, "ocaso", PROFILE),
            {},
            road=RoadService(sessions, "ocaso"),
            p5=p5,
        )
    )
    bot = _telegram()

    offer = await p5.offer(actor)
    assert offer is not None and offer.available
    offer_screen = render_p5(offer)
    assert "Missão Principal · Terras do Ocaso" in offer_screen.text
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(offer_screen, "Aceitar Missão").callback_data,
            update_id=998723,
            actor=actor,
        ),
    )
    assert "Seguir as estruturas" in _last_method(bot).text

    await _set_location(sessions, character_id, RUINS)
    follow = await p5.resume(actor)
    assert follow is not None and follow.kind == "follow_structures"
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(render_p5(follow), "Seguir estruturas de guarda").callback_data,
            update_id=998724,
            actor=actor,
        ),
    )
    door = await p5.resume(actor)
    assert door is not None and door.kind == "find_door"
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(render_p5(door), "Encontrar Porta do Poente").callback_data,
            update_id=998725,
            actor=actor,
        ),
    )
    pending = await p5.resume(actor)
    assert pending is not None and pending.kind == "combat_pending"
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(render_p5(pending), "Enfrentar Solo").callback_data,
            update_id=998726,
            actor=actor,
        ),
    )
    combat = await p5.resume(actor)
    assert combat is not None and combat.kind == "combat"
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    attack = next(
        button.callback_data
        for row in render_p5(combat).keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith("p5fight:")
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(attack, update_id=998730, actor=actor)
    )
    elements = await p5.resume(actor)
    assert elements is not None and elements.kind == "elements"
    screen = render_p5(elements)
    assert "Elementos da Estrutura · 0/3" in screen.text
    for update_id in (998731, 998732, 998733):
        screen = render_p5(await p5.resume(actor))
        number = str(update_id - 998730)
        await dispatcher.feed_raw_update(
            bot,
            callback_update(
                _button(screen, number).callback_data,
                update_id=update_id,
                actor=actor,
            ),
        )
    symbol = await p5.resume(actor)
    assert symbol is not None and symbol.kind == "record_symbol"
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(render_p5(symbol), "Registrar símbolo").callback_data,
            update_id=998734,
            actor=actor,
        ),
    )
    await _set_location(sessions, character_id, REFUGE)

    oren = await p5.oren(actor)
    assert oren is not None
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(render_p5(oren), "Reportar a Oren Cal").callback_data,
            update_id=998735,
            actor=actor,
        ),
    )
    assert "1/2" in _last_method(bot).text
    alda = await p5.alda(actor)
    assert alda is not None
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(render_p5(alda), "Reportar a Alda Veyr").callback_data,
            update_id=998736,
            actor=actor,
        ),
    )
    completed = _last_method(bot)
    assert "A Porta do Poente · Concluída" in completed.text
    assert "XP · 7.100" in completed.text and "Coroas · 300" in completed.text
