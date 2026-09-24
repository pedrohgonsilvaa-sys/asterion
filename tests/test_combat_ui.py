from copy import deepcopy
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import EditMessageText

from asterion.application.prologue import CombatView, PrologueService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import (
    CombatCallback,
    CombatConsumableFlowCallback,
    event_line,
    hp_bar,
    render_combat,
)
from asterion.bot.creation_handlers import creation_router
from asterion.domain.combat import Action, CombatEvent, Effect, combat_consumable_options
from asterion.domain.prologue import PROFILE
from asterion.domain.road import CREATURES, create_road_combat
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
    assert "🐺 🐺" not in screen.text
    assert screen.text.count("🐺") == 2  # HUD creature plus opening-log entry
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
    assert "⚔️ <b>Heroa</b> ataca <b>🐺" not in screen.text
    assert "🐺 <b>Cão Cinéreo</b> usa <b>Mordida Cinérea</b> em <b>Heroa</b>" in screen.text
    view = await prologue.action(1, view.activity_id, view.combat.version, "defend")
    screen = render_combat(view)
    assert [button.text for button in screen.keyboard.inline_keyboard[0]] == ["Golpe de Guarda"]
    assert "🎴 <b>Golpe de Guarda</b> · Arte de Classe" in screen.text
    assert "⚔️ Dano · <code>110%</code> ATQ" in screen.text
    assert "🐺 <b>Cão Cinéreo</b> usa <b>Investida Cinérea</b> em <b>Heroa</b>" in screen.text
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


def _combat_view_with_consumables(item_ids, *, screen=None, selected_item=None, parent="items"):
    state = create_road_combat(
        uuid4(),
        "Heroa",
        "sentinela",
        "remanescente",
        Decimal("500"),
        CREATURES[0],
        1,
        None,
    )
    state.fighters["player"].hp = Decimal("300")
    options = combat_consumable_options(state, item_ids, budget_limit=3)
    activity_id = uuid4()
    return CombatView(
        activity_id,
        uuid4(),
        uuid4(),
        state,
        "combat",
        0,
        context="road",
        consumable_options=options,
        consumable_screen=screen,
        selected_consumable_id=selected_item,
        selected_target_id="player" if screen == "effects" else None,
        selection_parent=parent,
        consumable_quantities=tuple((item_id, 2) for item_id in item_ids),
    )


def test_consumable_button_opens_numbered_list_even_for_one_option():
    view = _combat_view_with_consumables(("consumable.heal",))
    hud = render_combat(view)
    assert hud.keyboard is not None
    assert hud.keyboard.inline_keyboard[-1][0].text == "Consumível"
    open_callback = CombatConsumableFlowCallback.unpack(
        hud.keyboard.inline_keyboard[-1][0].callback_data
    )
    assert open_callback.step == "o"
    assert open_callback.activity_id == view.activity_id
    assert open_callback.state_version == view.combat.version

    menu = render_combat(
        CombatView(
            view.activity_id,
            view.encounter_id,
            view.character_id,
            view.combat,
            view.stage,
            view.xp,
            context=view.context,
            consumable_options=view.consumable_options,
            consumable_screen="items",
            consumable_quantities=view.consumable_quantities,
        )
    )
    assert "🧪 Consumíveis" in menu.text
    assert "1 🧪 Poção de Cura · 2" in menu.text
    assert "❤️ Cura · 22% HP Máximo" in menu.text
    assert [button.text for row in menu.keyboard.inline_keyboard for button in row] == [
        "1",
        "← Combate",
    ]
    item_callback = CombatConsumableFlowCallback.unpack(
        menu.keyboard.inline_keyboard[0][0].callback_data
    )
    assert item_callback.step == "i"
    assert item_callback.item_id == "consumable.heal"
    assert len(menu.keyboard.inline_keyboard[0][0].callback_data.encode()) <= 64
    assert view.combat.version == 0


def test_effect_selection_callbacks_carry_stable_identity_not_list_position():
    view = _combat_view_with_consumables(("consumable.purification",))
    view.combat.fighters["player"].effects.extend(
        [
            Effect("weak", "attack", Decimal("0.1"), 2, 0, instance_id="e9"),
            Effect("slow", "defense", Decimal("0.1"), 3, 0, instance_id="ea"),
        ]
    )
    options = combat_consumable_options(
        view.combat, ("consumable.purification",), budget_limit=3
    )
    selection = CombatView(
        view.activity_id,
        view.encounter_id,
        view.character_id,
        view.combat,
        view.stage,
        view.xp,
        context="road",
        consumable_options=options,
        consumable_screen="effects",
        selected_consumable_id="consumable.purification",
        selected_target_id="player",
        selection_parent="items",
        consumable_quantities=(("consumable.purification", 2),),
    )
    screen = render_combat(selection)
    callbacks = [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text.isdigit()
    ]
    restored = [CombatConsumableFlowCallback.unpack(value) for value in callbacks]
    assert [callback.effect_id for callback in restored] == ["e9", "ea"]
    assert all(callback.item_id == "consumable.purification" for callback in restored)
    assert all(callback.target_id == "player" for callback in restored)
    assert all(len(value.encode()) <= 64 for value in callbacks)
    assert [button.text for row in screen.keyboard.inline_keyboard for button in row] == [
        "1",
        "2",
        "← Consumíveis",
    ]


def test_combat_button_is_absent_without_any_eligible_option():
    view = _combat_view_with_consumables(())
    screen = render_combat(view)
    assert screen.keyboard is not None
    assert not any(
        button.text == "Consumível"
        for row in screen.keyboard.inline_keyboard
        for button in row
    )


def test_dispeller_target_and_effect_screens_use_numeric_stable_choices():
    view = _combat_view_with_consumables(("consumable.dispeller.iii",))
    state = view.combat
    state.fighters["enemy"].effects = [
        Effect("power_up", "attack", Decimal("0.1"), 3, 0, kind="buff", instance_id="e1"),
        Effect("guard_up", "defense", Decimal("0.1"), 2, 0, kind="buff", instance_id="e2"),
    ]
    second_enemy = deepcopy(state.fighters["enemy"])
    second_enemy.id = "enemy2"
    second_enemy.name = "Aranha Cinérea"
    second_enemy.effects = [
        Effect("speed_up", "agility", Decimal("0.1"), 2, 0, kind="buff", instance_id="e3")
    ]
    state.fighters["enemy2"] = second_enemy
    options = combat_consumable_options(
        state, ("consumable.dispeller.iii",), budget_limit=3
    )
    target_screen = render_combat(
        CombatView(
            view.activity_id,
            view.encounter_id,
            view.character_id,
            state,
            view.stage,
            view.xp,
            context="road",
            consumable_options=options,
            consumable_screen="targets",
            selected_consumable_id="consumable.dispeller.iii",
        )
    )
    assert "Dissipador · Escolha o Alvo" in target_screen.text
    assert "Efeitos Removíveis · 2" in target_screen.text
    assert "Efeitos Removíveis · 1" in target_screen.text
    target_callbacks = [
        CombatConsumableFlowCallback.unpack(button.callback_data)
        for row in target_screen.keyboard.inline_keyboard
        for button in row
        if button.text.isdigit()
    ]
    assert [callback.target_id for callback in target_callbacks] == ["enemy", "enemy2"]

    effect_screen = render_combat(
        CombatView(
            view.activity_id,
            view.encounter_id,
            view.character_id,
            state,
            view.stage,
            view.xp,
            context="road",
            consumable_options=options,
            consumable_screen="effects",
            selected_consumable_id="consumable.dispeller.iii",
            selected_target_id="enemy",
            selection_parent="targets",
        )
    )
    assert "✨ Dissipador · Escolha o Efeito" in effect_screen.text
    assert "🐺 Cão Cinéreo" in effect_screen.text
    assert [button.text for row in effect_screen.keyboard.inline_keyboard for button in row] == [
        "1",
        "2",
        "← Alvos",
    ]


def test_consumable_and_ward_combat_log_lines_follow_the_ui_source():
    view = _combat_view_with_consumables(())
    state = view.combat
    player = state.fighters["player"]
    enemy = state.fighters["enemy"]
    player.name = "Luiken"
    enemy.name = "Cão Cinéreo"
    state.enemy_actions["weak"] = Action("weak", "Fraqueza", Decimal("0"))
    state.enemy_actions["rally"] = Action("rally", "Brado de Guerra", Decimal("0"))
    state.enemy_actions["claw"] = Action("claw", "Garra", Decimal("0.8"))

    def consumable(item_id, *, target="player", healed=Decimal(0), barrier=Decimal(0), effect=""):
        return event_line(
            state,
            CombatEvent(
                sequence=1,
                round=1,
                actor="player",
                action=f"consumable:{item_id}",
                target=target,
                healed=healed,
                effect_id=effect,
                barrier_value=barrier,
            ),
        )

    assert consumable("consumable.heal", healed=Decimal(220)) == (
        "🧪 <b>Luiken</b> usa <b>Poção de Cura</b>.\n"
        "❤️ <b>Luiken</b> recupera <code>220</code> HP."
    )
    assert consumable("consumable.purification.vde.ii", effect="weak") == (
        "🧪 <b>Luiken</b> usa <b>Preparado de Purificação Enredada</b>.\n"
        "✨ <b>Fraqueza</b> · Removido"
    )
    assert consumable("consumable.antidote.tdo.i", effect="dot:burn") == (
        "🧪 <b>Luiken</b> usa <b>Antídoto Cinzento</b>.\n"
        "☣️ <b>Queimadura</b> · Removido"
    )
    assert consumable("consumable.protection.vde.ii", barrier=Decimal(120)) == (
        "🧪 <b>Luiken</b> usa <b>Preparado de Proteção Enredada</b>.\n"
        "🔰 Barreira · <code>120</code> · <code>2T</code>"
    )
    assert consumable(
        "consumable.dispeller.iii", target="enemy", effect="rally"
    ) == (
        "🧪 <b>Luiken</b> usa <b>Dissipador</b> em <b>Cão Cinéreo</b>.\n"
        "✨ <b>Brado de Guerra</b> · Removido"
    )
    assert consumable("consumable.warding.iv") == (
        "🧪 <b>Luiken</b> usa <b>Preparado de Resguardo</b>.\n"
        "🛡️ Resguardo · <code>2T</code> · <code>1 Carga</code>"
    )

    damage = event_line(
        state,
        CombatEvent(
            sequence=2,
            round=1,
            actor="enemy",
            action="claw",
            target="player",
            damage=12,
        ),
    )
    blocked = event_line(
        state,
        CombatEvent(
            sequence=3,
            round=1,
            actor="player",
            action="resguardo:block",
            target="player",
            effect_id="weak",
        ),
    )
    assert damage == (
        "🐺 <b>Cão Cinéreo</b> usa <b>Garra</b> em <b>Luiken</b> "
        "e causa <code>12</code> de dano."
    )
    assert blocked == "🛡️ Resguardo bloqueia <b>Fraqueza</b> em <b>Luiken</b>."
    assert "weak" not in blocked
