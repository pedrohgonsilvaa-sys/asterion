from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import EditMessageText

from asterion.application.prologue import PrologueService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import CombatCallback, hp_bar, render_combat
from asterion.bot.creation_handlers import creation_router
from asterion.domain.prologue import PROFILE
from tests.test_creation_ui import callback_update, message_update
from tests.test_prologue_persistence import character


@pytest.fixture
def telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def prologue(database):
    return PrologueService(database[1], "ocaso", PROFILE)


async def test_first_hud_matches_authoritative_shape(prologue, database):
    await character(database)
    view = await prologue.enter(1)
    screen = render_combat(view)
    assert screen.text.startswith(
        "Turno 1 · <b>Heroa</b>\n\n<b>🐺 Cão Cinéreo</b>\n❤️ <code>244 / 244</code>"
    )
    assert "Um rosnado rompe o silêncio da estrada." in screen.text
    assert "👉 🛡️ <b>Heroa</b>" in screen.text
    assert "📜 Registro de Combate · Recentes" in screen.text
    assert "🐺 Cão Cinéreo bloqueia o caminho." in screen.text
    assert "⚔️ Atacar · Causa Dano" in screen.text
    assert "🛡️ Defender · Reduz Dano até seu próximo Turno" in screen.text
    assert [[button.text for button in row] for row in screen.keyboard.inline_keyboard] == [
        ["Atacar", "Defender"]
    ]
    assert all(
        forbidden not in screen.text
        for forbidden in (
            "Guilda",
            "Vigor",
            "Sentinela",
            "240 / 240",
            "132 / 240",
            "SIMULAR",
            "[Imagem",
        )
    )


def test_hp_bar_is_derived_from_real_values():
    from decimal import Decimal

    assert hp_bar(Decimal(244), Decimal(244)) == "🟩" * 10
    assert hp_bar(Decimal(132), Decimal(244)) == "🟩" * 5 + "⬜" * 5
    assert hp_bar(Decimal(0), Decimal(244)) == "⬜" * 10


async def test_hud_reconstructs_persisted_events_and_tutorial_buttons(prologue, database):
    await character(database)
    view = await prologue.enter(1)
    view = await prologue.action(1, view.activity_id, view.combat.version, "attack")
    screen = render_combat(view)
    assert [button.text for button in screen.keyboard.inline_keyboard[0]] == ["Defender"]
    assert "⚔️ <b>Heroa</b> ataca <b>Cão Cinéreo</b>" in screen.text
    assert "🐺 <b>Cão Cinéreo</b> usa <b>Mordida Cinérea</b> em <b>Heroa</b>" in screen.text
    view = await prologue.action(1, view.activity_id, view.combat.version, "defend")
    screen = render_combat(view)
    assert [button.text for button in screen.keyboard.inline_keyboard[0]] == ["Golpe de Guarda"]
    assert "🎴 <b>Golpe de Guarda</b> · Arte de Classe" in screen.text
    assert "⚔️ Dano · <code>110%</code> ATQ" in screen.text
    # Reconnect uses the same persisted log and controls.
    assert render_combat(await prologue.resume(1)) == screen


async def test_combat_callbacks_are_small_and_contain_intention_only(prologue, database):
    await character(database)
    view = await prologue.enter(1)
    for button in render_combat(view).keyboard.inline_keyboard[0]:
        assert len(button.callback_data.encode()) <= 64
        data = CombatCallback.unpack(button.callback_data)
        assert data.activity_id == view.activity_id
        assert data.version == view.combat.version
        assert data.action in ("attack", "defend")


async def test_real_dispatcher_enters_and_executes_backend_actions(database, telegram):
    from asterion.application.creation import CreationService

    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(service, {}))
    dispatcher.include_router(creation_router(CreationService(database[1], "ocaso"), {}, service))
    await dispatcher.feed_raw_update(telegram, callback_update("prologue:continue", actor=1))
    entered = await service.resume(1)
    assert entered is not None
    sent = telegram.session.make_request.call_args.args[1]
    assert "🐺 Cão Cinéreo" in (getattr(sent, "text", None) or getattr(sent, "caption", ""))
    callback = CombatCallback(
        activity=entered.activity_id.hex,
        version=entered.combat.version,
        action="attack",
    ).pack()
    await dispatcher.feed_raw_update(telegram, callback_update(callback, update_id=3, actor=1))
    assert (await service.resume(1)).combat.version == entered.combat.version + 1


async def test_start_mid_combat_reconstructs_combat_instead_of_intro(database, telegram):
    from asterion.application.creation import CreationService

    await character(database)
    prologue = PrologueService(database[1], "ocaso", PROFILE)
    entered = await prologue.enter(1)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(prologue, {}))
    dispatcher.include_router(creation_router(CreationService(database[1], "ocaso"), {}, prologue))
    await dispatcher.feed_raw_update(telegram, message_update("/start", actor=1))
    sent = telegram.session.make_request.call_args.args[1]
    assert sent.text == render_combat(entered).text
    assert "O mundo desperta" not in sent.text


async def test_deleted_message_uses_new_message_without_losing_combat(database, telegram):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    view = await service.enter(1)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(service, {}))
    telegram.session.make_request.side_effect = [
        True,  # answerCallbackQuery
        TelegramBadRequest(
            method=EditMessageText(text="x"),
            message="message to edit not found",
        ),
        True,  # fallback sendMessage
    ]
    callback = CombatCallback(
        activity=view.activity_id.hex,
        version=view.combat.version,
        action="attack",
    ).pack()
    await dispatcher.feed_raw_update(telegram, callback_update(callback, actor=1))
    assert (await service.resume(1)).combat.version == view.combat.version + 1
    assert telegram.session.make_request.await_count == 3


async def test_telegram_failure_after_commit_does_not_rollback(database, telegram):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    view = await service.enter(1)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(service, {}))
    telegram.session.make_request.side_effect = [
        True,
        TelegramForbiddenError(method=EditMessageText(text="x"), message="bot blocked"),
    ]
    callback = CombatCallback(
        activity=view.activity_id.hex,
        version=view.combat.version,
        action="attack",
    ).pack()
    with pytest.raises(TelegramForbiddenError):
        await dispatcher.feed_raw_update(telegram, callback_update(callback, actor=1))
    assert (await service.resume(1)).combat.version == view.combat.version + 1


async def test_malformed_and_foreign_callbacks_do_not_mutate(database, telegram):
    await character(database, 1)
    await character(database, 2)
    service = PrologueService(database[1], "ocaso", PROFILE)
    view = await service.enter(1)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(service, {}))
    for data in ("fight:broken", "fight:no-uuid:0:attack", "fight:bad:x:reward"):
        await dispatcher.feed_raw_update(telegram, callback_update(data, actor=1))
    callback = CombatCallback(
        activity=view.activity_id.hex,
        version=view.combat.version,
        action="attack",
    ).pack()
    await dispatcher.feed_raw_update(telegram, callback_update(callback, actor=2))
    assert await service.resume(1) == view
