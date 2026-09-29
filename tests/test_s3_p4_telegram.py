from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.creation import CreationService
from asterion.application.p2 import P2Service
from asterion.application.p4 import P4Service
from asterion.application.prologue import PrologueService
from asterion.application.road import BOSQUE, CHARNECA, RoadService
from asterion.application.s3 import S3Service
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import P4CombatCallback
from asterion.bot.creation_handlers import creation_router
from asterion.bot.p2_handlers import p2_router
from asterion.bot.p4_handlers import p4_router
from asterion.bot.p4_ui import render_p4
from asterion.bot.s3_handlers import s3_router
from asterion.bot.s3_ui import render_s3
from asterion.bot.world_handlers import world_router
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import Quest
from tests.test_creation_ui import callback_update, message_update
from tests.test_p3_integration import _terminal
from tests.test_s3_p4_integration import _reach_bosque, _seed_campaign


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


def _button(screen, label):
    markup = getattr(screen, "reply_markup", None) or screen.keyboard
    return next(
        button
        for row in markup.inline_keyboard
        for button in row
        if button.text == label
    )


@pytest.mark.asyncio
async def test_alda_exposes_s3_alongside_available_p4_without_creating_quest(database):
    actor = 998421
    character_id, sessions = await _seed_campaign(database, actor, level=7)
    p2 = P2Service(sessions, "ocaso")
    s3 = S3Service(sessions, "ocaso")
    p4 = P4Service(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(p2_router(p2, {}, s3=s3, p4=p4))
    dispatcher.include_router(s3_router(s3, {}))
    dispatcher.include_router(p4_router(p4, {}))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("p2:alda", update_id=998422, actor=actor)
    )
    alda = _last_method(bot)
    assert _button(alda, "Pedras que Ainda Vigiam")
    s3_button = _button(alda, "Rastros sob os Galhos")
    assert s3_button.callback_data == "s3:offer"

    await dispatcher.feed_raw_update(
        bot, callback_update(s3_button.callback_data, update_id=998423, actor=actor)
    )
    offer = _last_method(bot)
    assert "Rastros sob os Galhos" in offer.text
    accept = _button(offer, "Aceitar Missão").callback_data
    assert accept.startswith("s3:") and accept.endswith(":accept")
    async with sessions() as session:
        assert await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == "S3")
        ) is None

    await dispatcher.feed_raw_update(
        bot, callback_update(accept, update_id=998430, actor=actor)
    )
    active = await s3.alda(actor)
    assert active is not None
    active_screen = render_s3(active)
    assert _button(active_screen, "Ver Rastros sob os Galhos").callback_data == "s3:resume"
    assert not any(
        button.callback_data.endswith(":report")
        for row in active_screen.keyboard.inline_keyboard
        for button in row
    )

    abandoned = await s3.abandon(actor, active.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    reaccept = _button(render_s3(abandoned), "Reaceitar Missão")
    assert reaccept.callback_data.endswith(":reaccept")
    await dispatcher.feed_raw_update(
        bot, callback_update(reaccept.callback_data, update_id=998431, actor=actor)
    )
    resumed = await s3.resume(actor)
    assert resumed is not None and resumed.status == "active" and resumed.step == 1
    async with sessions() as session:
        quests = (
            await session.scalars(
                select(Quest).where(Quest.character_id == character_id, Quest.quest_id == "S3")
            )
        ).all()
        assert len(quests) == 1


@pytest.mark.asyncio
async def test_p4_campaign_navigation_and_s3_return_report_buttons(database, monkeypatch):
    actor = 998424
    _, sessions = await _seed_campaign(database, actor, level=7)
    p4 = P4Service(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    accepted = await p4.accept(actor)
    assert accepted is not None

    refuge = render_p4(accepted)
    assert _button(refuge, "Seguir para a Charneca").callback_data == "road:route:charneca"

    await road.travel_route(actor, CHARNECA)
    charneca = await p4.resume(actor)
    assert charneca is not None
    assert _button(render_p4(charneca), "Seguir para o Bosque").callback_data == "road:route:bosque"
    await road.travel_route(actor, BOSQUE)
    bosque = await p4.resume(actor)
    assert bosque is not None
    path = await p4.action(actor, bosque.state_version, "path")
    assert path is not None and path.kind == "enter_ruins"

    # Rebuild the S3 report view away from its giver; it must route home first.
    actor2 = 998425
    _, sessions2 = await _seed_campaign(database, actor2, level=5)
    s3_other = S3Service(sessions2, "ocaso")
    accepted_s3 = await s3_other.accept(actor2)
    assert accepted_s3 is not None
    await _reach_bosque(sessions2, actor2)
    view = await s3_other.resume(actor2)
    assert view is not None
    route = await s3_other.interact(actor2, view.state_version, "route")
    assert route is not None
    for index in (1, 2, 3):
        route = await s3_other.interact(actor2, route.state_version, "track", f"s3.track.{index}")
    # A scripted win advances to cargo without creating a normal Explore result.
    import asterion.application.scripted_combat as scripted_combat

    combat = route
    assert combat is not None and combat.kind == "combat"
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    cargo = await s3_other.action(
        actor2, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert cargo is not None
    cargo = await s3_other.interact(actor2, cargo.state_version, "cargo")
    assert cargo is not None and cargo.location == BOSQUE
    report = render_s3(cargo)
    assert _button(report, "Seguir para a Charneca").callback_data == "road:route:charneca"
    assert not any(
        button.callback_data.endswith(":report")
        for row in report.keyboard.inline_keyboard
        for button in row
    )


@pytest.mark.asyncio
async def test_p4_combat_callback_menu_and_start_reconnect_same_activity(database):
    actor = 998426
    _, sessions = await _seed_campaign(database, actor, level=7)
    p4 = P4Service(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    world = WorldService(sessions, "ocaso")
    await p4.accept(actor)
    await _reach_bosque(sessions, actor)
    view = await p4.resume(actor)
    path = await p4.action(actor, view.state_version, "path")
    combat = await p4.action(actor, path.state_version, "enter")
    assert combat is not None and combat.kind == "combat"
    attack = _button(render_p4(combat), "Atacar")
    callback = P4CombatCallback.unpack(attack.callback_data)
    assert callback.activity_id == combat.activity_id

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(p4_router(p4, {}))
    dispatcher.include_router(combat_router(
        PrologueService(sessions, "ocaso", PROFILE), {}, world, road, p4=p4
    ))
    dispatcher.include_router(world_router(world, {}, road=road, p4=p4))
    dispatcher.include_router(creation_router(
        CreationService(sessions, "ocaso"), {}, world=world, road=road, p4=p4
    ))
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, callback_update(attack.callback_data, update_id=998427, actor=actor)
    )
    after_attack = await p4.resume(actor)
    expected = (
        after_attack.activity_id,
        after_attack.encounter_id,
        after_attack.combat_id,
        after_attack.activity_state_version,
    )
    assert expected[0] == combat.activity_id
    await dispatcher.feed_raw_update(
        bot, _command_update("/menu", update_id=998428, actor=actor)
    )
    assert "Pedras que Ainda Vigiam" in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot, _command_update("/start", update_id=998429, actor=actor)
    )
    assert "Encontro de Missão" in _last_method(bot).text
    resumed = await p4.resume(actor)
    assert (
        resumed.activity_id,
        resumed.encounter_id,
        resumed.combat_id,
        resumed.activity_state_version,
    ) == expected

