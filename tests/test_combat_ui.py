from copy import deepcopy
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import EditMessageText

from asterion.application.prologue import CombatView, PrologueService
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import (
    CombatCallback,
    CombatConsumableFlowCallback,
    event_line,
    hp_bar,
    render_combat,
)
from asterion.bot.creation_handlers import creation_router
from asterion.domain.arts import DEVASTADOR_ART_IDS
from asterion.domain.combat import (
    Action,
    ActionCondition,
    ActionConditionalModifier,
    ActionResourceUse,
    CombatEvent,
    Effect,
    act,
    combat_consumable_options,
)
from asterion.domain.consumables import CONSUMABLE_CATALOG
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.prologue import PROFILE
from asterion.domain.road import CREATURES, create_road_combat
from tests.test_creation_ui import callback_update, message_update
from tests.test_prologue_persistence import character, prepare_defeat_snapshot


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


def _class_mechanic_combat_view(
    character_class: str,
    selected_path: str | None = None,
    *,
    context: str = "road",
    party_mode: bool = False,
):
    state = PROFILE.create(
        uuid4(),
        "Luiken",
        character_class,
        "remanescente",
        Decimal("500"),
    )
    state.tutorial = None
    state.party_mode = party_mode
    state.fighters["player"].selected_path = selected_path
    state.fighters["player"].side = "player"
    state.fighters["enemy"].side = "enemy"
    return CombatView(
        uuid4(),
        uuid4(),
        uuid4(),
        state,
        "combat",
        0,
        context=context,
    )


@pytest.mark.parametrize(
    ("character_class", "selected_path", "path_state", "expected"),
    [
        ("sentinela", None, {}, "🛡️ Retaliação · <code>2T</code>"),
        (
            "tecelao",
            "conjurador",
            {
                "trama_state": {
                    "origin_art": "class_art.tecelao.preparo",
                    "remaining": 2,
                }
            },
            "🪄 Trama · <code>2T · Arte de Tecelão</code>",
        ),
        (
            "luminar",
            "guardiao",
            {"luminar_state": {"kind": "fulgor", "remaining": 2}},
            "☀️ Fulgor · <code>2T</code>",
        ),
        (
            "luminar",
            "inquisidor",
            {"luminar_state": {"kind": "julgamento", "remaining": 1}},
            "⚖️ Julgamento · <code>1T</code>",
        ),
    ],
)
def test_class_resource_indicators_are_compact_and_separate(
    character_class, selected_path, path_state, expected
):
    view = _class_mechanic_combat_view(character_class, selected_path)
    player = view.combat.fighters["player"]
    player.path_state.update(path_state)
    player.retaliation_charges = 1 if character_class == "sentinela" else 0
    player.retaliation_remaining = 2 if character_class == "sentinela" else 0
    if character_class == "sentinela":
        player.barrier = Decimal("100")
        player.barrier_remaining = 2

    text = render_combat(view).text

    assert expected in text
    assert "Origem ·" not in text
    if character_class == "sentinela":
        assert (
            "🔰 Barreira · <code>100</code> · <code>2T</code>\n\n"
            "🛡️ Retaliação · <code>2T</code>"
        ) in text


def test_conditional_resource_requirements_and_consumption_are_visible_to_owner_only():
    view = _class_mechanic_combat_view("vigia", "atirador")
    state = view.combat
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    target.path_state["aim_from"] = {
        actor.id: {"stacks": 4, "remaining": 2, "applied_opportunity": 0}
    }
    state.player_actions["terminal_test"] = Action(
        "class_art.vigia.terminal_test",
        "Finalização",
        Decimal("1.0"),
        resource_uses=(
            ActionResourceUse(
                "aim",
                minimum=4,
                consume=4,
                consume_at="after_resolution",
                target_selector="primary_target",
                required=True,
            ),
        ),
        conditional_modifiers=(
            ActionConditionalModifier(
                "vigia.test.crit_if_aim",
                ActionCondition("class_resource_at_least", resource="aim", minimum=4),
                "crit_bonus",
                Decimal(15),
                target_scope="primary_target",
            ),
        ),
    )
    state.events.append(
        CombatEvent(
            sequence=1,
            round=1,
            actor="player",
            action="terminal_test",
            target=target.id,
            actor_entity_id=actor.id,
            class_resource_changes=(("aim", target.id, 4, 0),),
        )
    )

    text = render_combat(view).text
    assert "Exige Mira <code>4</code> no alvo principal" in text
    assert "disponível: Cão Cinéreo 4" in text
    assert "Mira: em <b>Cão Cinéreo</b> <code>4</code> acúmulo(s) consumida(s)" in text
    assert "restam <code>0</code>" in text

    hidden = event_line(
        state,
        CombatEvent(
            sequence=2,
            round=1,
            actor="enemy",
            action="secret_resource",
            target=actor.id,
            actor_entity_id=target.id,
            class_resource_changes=(("aim", actor.id, 4, 0),),
        ),
        viewer_key="player",
    )
    assert "Mira" not in hidden


def test_target_markers_appear_on_the_relevant_target_card():
    view = _class_mechanic_combat_view("vigia", "atirador")
    enemy = view.combat.fighters["enemy"]
    enemy.path_state["aim_from"] = {
        "player": {"stacks": 2, "remaining": 2},
    }
    screen = render_combat(view)
    aim = "🎯 Mira · 2/4 · <code>2T</code>"
    assert aim in screen.text
    assert screen.text.index("<b>🐺 Cão Cinéreo</b>") < screen.text.index(aim)
    assert screen.text.index(aim) < screen.text.index(view.combat.flavor)

    view = _class_mechanic_combat_view("oraculo", "agoureiro")
    view.combat.fighters["player"].path_state["omen_offensive"] = {
        "enemy": {"remaining": 2},
    }
    screen = render_combat(view)
    omen = "🔮 Presságio Ofensivo · <code>2T</code>"
    assert omen in screen.text
    assert screen.text.index("<b>🐺 Cão Cinéreo</b>") < screen.text.index(omen)
    assert screen.text.index(omen) < screen.text.index(view.combat.flavor)

    view = _class_mechanic_combat_view("oraculo", "agoureiro")
    view.combat.fighters["player"].path_state["omen_defensive"] = {
        "player": {"remaining": 2},
    }
    screen = render_combat(view)
    defensive_omen = "🔮 Presságio Defensivo · <code>2T</code>"
    assert defensive_omen in screen.text
    assert screen.text.index("👉 🔮 <b>Luiken</b>") < screen.text.index(defensive_omen)
    assert screen.text.index(defensive_omen) < screen.text.index("📜 Registro de Combate")

    view = _class_mechanic_combat_view("errante")
    view.combat.fighters["enemy"].effects.append(
        Effect(
            "slow",
            "agility",
            Decimal("0.10"),
            2,
            0,
            kind="debuff",
        )
    )
    screen = render_combat(view)
    opportunity = "🗡️ Oportunismo · elegível"
    assert opportunity in screen.text
    assert screen.text.index("<b>🐺 Cão Cinéreo</b>") < screen.text.index(opportunity)
    assert screen.text.index(opportunity) < screen.text.index(view.combat.flavor)

    view.combat.fighters["enemy"].effects[0] = Effect(
        "fixed.slow",
        "agility",
        Decimal("0.10"),
        2,
        0,
        kind="debuff",
        fixed_mechanic=True,
    )
    assert "Oportunismo · elegível" not in render_combat(view).text


def test_campaign_solo_path_art_uses_short_frozen_slot_callback():
    ariete = DEVASTADOR_ART_IDS["ariete"]
    combat = create_road_combat(
        uuid4(),
        "Luiken",
        "sentinela",
        "remanescente",
        Decimal("500"),
        CREATURES[0],
        12,
        None,
        player_level=12,
        equipment_configuration=EquipmentConfigurationSnapshot(
            combat_configuration_version=4,
            selected_path="devastador",
        ),
        active_art_ids=(ariete,),
    )
    combat.configuration_snapshot = (combat.configuration_snapshot or {}) | {
        "active_arts": [{"slot": 2, "art_id": ariete}]
    }
    view = CombatView(
        uuid4(),
        uuid4(),
        uuid4(),
        combat,
        "combat",
        0,
        context="p12",
    )

    screen = render_combat(view)
    button = next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Aríete"
    )
    assert len(button.callback_data.encode("utf-8")) <= 64
    assert CombatCallback.unpack(button.callback_data).action == "a2"

    updated = act(combat, ariete, target_id="enemy")
    cooldown_view = CombatView(
        view.activity_id,
        view.encounter_id,
        view.character_id,
        updated,
        "combat",
        0,
        context="p12",
    )
    assert "Aríete · CD<code>1</code>" in render_combat(cooldown_view).text


def test_competitive_hud_hides_opponent_owned_class_state():
    view = _class_mechanic_combat_view(
        "sentinela",
        context="pvpve",
        party_mode=True,
    )
    player = view.combat.fighters["player"]
    enemy = view.combat.fighters["enemy"]
    player.retaliation_charges = 1
    player.retaliation_remaining = 2
    enemy.character_class = "sentinela"
    enemy.retaliation_charges = 1
    enemy.retaliation_remaining = 3
    enemy.path_state["luminar_state"] = {"kind": "fulgor", "remaining": 2}

    screen = render_combat(view)

    assert screen.text.count("🛡️ Retaliação ·") == 1
    assert "🛡️ Retaliação · <code>2T</code>" in screen.text
    assert "🛡️ Retaliação · <code>3T</code>" not in screen.text
    assert "☀️ Fulgor · <code>2T</code>" not in screen.text


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


async def test_prologue_defeat_render_has_no_xp_receipt_or_retry(prologue, database):
    await character(database)
    initial = await prologue.enter(1)
    await prepare_defeat_snapshot(prologue, initial, database)
    defeated = await prologue.action(1, initial.activity_id, initial.combat.version, "attack")
    screen = render_combat(defeated)
    assert defeated.combat.result == "defeat"
    assert "320 XP" not in screen.text
    assert screen.keyboard is None
    assert "Tentar Novamente" not in screen.text


async def test_terminal_prologue_defeat_dispatches_to_existing_brazier(
    database, telegram
):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    initial = await service.enter(1)
    await prepare_defeat_snapshot(service, initial, database)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(combat_router(service, {}, WorldService(database[1], "ocaso")))

    callback = CombatCallback(
        activity=initial.activity_id.hex,
        version=initial.combat.version,
        action="attack",
    ).pack()
    await dispatcher.feed_raw_update(telegram, callback_update(callback, actor=1))

    sent = telegram.session.make_request.call_args.args[1]
    assert "🔥 Braseiro · Descoberto" in sent.text
    assert [button.text for row in sent.reply_markup.inline_keyboard for button in row] == [
        "Descansar"
    ]


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


def test_combat_consumable_callbacks_cover_canonical_round_eligible_catalog():
    activity_id = uuid4()
    eligible = {
        item_id
        for item_id, item in CONSUMABLE_CATALOG.items()
        if item.round_eligible
    }
    callbacks = {
        item_id: CombatConsumableFlowCallback.for_step(
            activity_id, 7, "i", item_id=item_id
        )
        for item_id in eligible
    }

    assert {item_id: callback.item_id for item_id, callback in callbacks.items()} == {
        item_id: item_id for item_id in eligible
    }
    tokens = [callback.item for callback in callbacks.values()]
    assert len(tokens) == len(set(tokens))
    assert all(
        len(callback.pack().encode("utf-8")) <= 64
        for callback in callbacks.values()
    )
    with pytest.raises(KeyError):
        CombatConsumableFlowCallback.for_step(
            activity_id, 7, "i", item_id="consumable.unknown"
        )


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
