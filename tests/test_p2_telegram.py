from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.p1 import P1Service
from asterion.application.p2 import ASH_POINT_IDS, P2Service
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.s1 import S1Service, S1View
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import (
    CombatConsumableCallback,
    CombatConsumableFlowCallback,
    P2CombatCallback,
)
from asterion.bot.creation_handlers import creation_router
from asterion.bot.p2_handlers import p2_router
from asterion.bot.p2_ui import render_p2
from asterion.bot.world_handlers import world_router
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import (
    Character,
    ConsumableStack,
    GameActivity,
    Quest,
    RewardEvent,
    WorldState,
)
from tests.test_creation_ui import callback_update, message_update
from tests.test_p2_integration import _complete_p2, _finish_with, _seed, _start_combat


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _last_method(bot):
    return bot.session.make_request.call_args.args[1]


@pytest.mark.asyncio
async def test_p2_callbacks_run_mission_and_route_combat_hud(database, monkeypatch):
    actor = 984001
    character_id, service = await _seed(database, actor)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(p2_router(service, {}))
    dispatcher.include_router(
        combat_router(
            PrologueService(database[1], "ocaso", PROFILE),
            {},
            road=RoadService(database[1], "ocaso"),
            p2=service,
        )
    )
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot, callback_update("p2:alda", update_id=984001, actor=actor)
    )
    offer_method = _last_method(bot)
    assert "Fuligem sem Fogo" in offer_method.text
    assert any(
        button.text == "Aceitar Missão"
        for row in offer_method.reply_markup.inline_keyboard
        for button in row
    )
    async with database[1]() as session:
        assert await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == "P2"
            )
        ) is None

    await dispatcher.feed_raw_update(
        bot, callback_update("p2:0:accept", update_id=984002, actor=actor)
    )
    assert "Viajar até a Charneca da Fuligem" in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot, callback_update("p2:0:accept", update_id=984005, actor=actor)
    )
    assert "Viajar até a Charneca da Fuligem" in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot, callback_update("p2:0:travel", update_id=984003, actor=actor)
    )
    assert "Examinar Pontos de Fuligem · 0/3" in _last_method(bot).text
    # The duplicate old travel callback reconstructs the authoritative ash screen.
    await dispatcher.feed_raw_update(
        bot, callback_update("p2:0:travel", update_id=984004, actor=actor)
    )
    assert "Examinar Pontos de Fuligem · 0/3" in _last_method(bot).text

    # Any order is valid; the third distinct point immediately opens the fixed fight.
    stale_ash_callback = None
    for index, point_id in enumerate(
        (ASH_POINT_IDS[2], ASH_POINT_IDS[0], ASH_POINT_IDS[1]), start=5
    ):
        current = await service.resume(actor)
        assert current is not None and current.kind == "ash_points"
        callback = f"p2:{current.state_version}:ash:{point_id}"
        stale_ash_callback = stale_ash_callback or callback
        await dispatcher.feed_raw_update(
            bot, callback_update(callback, update_id=984000 + index, actor=actor)
        )

    current = await service.resume(actor)
    assert current is not None and current.kind == "combat"
    assert current.combat is not None and current.activity_id is not None
    assert current.encounter_id is not None and current.combat_id is not None
    await dispatcher.feed_raw_update(
        bot,
        callback_update(stale_ash_callback, update_id=984016, actor=actor),
    )
    stale_ash = await service.resume(actor)
    assert stale_ash is not None and stale_ash.activity_id == current.activity_id
    assert stale_ash.encounter_id == current.encounter_id
    assert stale_ash.combat_id == current.combat_id
    hud = render_p2(current)
    assert "📜 Registro de Combate · Recentes" in hud.text
    assert "Aranha de Cinza" in hud.text
    assert "Enfrentar" not in hud.text
    defense = next(
        button
        for row in hud.keyboard.inline_keyboard
        for button in row
        if button.text == "Defender"
    )
    combat_callback = P2CombatCallback.unpack(defense.callback_data)
    assert combat_callback.activity_id == current.activity_id
    assert combat_callback.version == current.combat.version

    await dispatcher.feed_raw_update(
        bot,
        callback_update(defense.callback_data, update_id=984010, actor=actor),
    )
    latest = await P2Service(database[1], "ocaso").resume(actor)
    assert latest is not None and latest.kind == "combat"
    assert latest.activity_id == current.activity_id
    assert latest.encounter_id == current.encounter_id
    assert latest.combat_id == current.combat_id
    assert latest.combat.version == current.combat.version + 1
    async with database[1]() as session:
        active = (
            await session.scalars(
                select(GameActivity).where(
                    GameActivity.character_id == character_id,
                    GameActivity.status == "active",
                )
            )
        ).all()
        assert [row.id for row in active] == [current.activity_id]

    import asterion.application.p2 as p2_module

    monkeypatch.setattr(p2_module, "act", _finish_with("victory"))
    attack = next(
        button
        for row in render_p2(latest).keyboard.inline_keyboard
        for button in row
        if button.text == "Atacar"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(attack.callback_data, update_id=984011, actor=actor)
    )
    stone = await service.resume(actor)
    assert stone is not None and stone.kind == "stone"
    await dispatcher.feed_raw_update(
        bot,
        callback_update(attack.callback_data, update_id=984017, actor=actor),
    )
    assert (await service.resume(actor)).kind == "stone"
    stone_button = next(
        button
        for row in render_p2(stone).keyboard.inline_keyboard
        for button in row
        if button.text == "Examinar Pedra Marcada"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(stone_button.callback_data, update_id=984012, actor=actor)
    )
    examined = await service.resume(actor)
    assert examined is not None and examined.progress["stone_examined"]
    await dispatcher.feed_raw_update(
        bot,
        callback_update(stone_button.callback_data, update_id=984018, actor=actor),
    )
    assert (await service.resume(actor)).progress["stone_examined"]
    refuge_button = next(
        button
        for row in render_p2(examined).keyboard.inline_keyboard
        for button in row
        if button.text == "Retornar ao Refúgio"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(refuge_button.callback_data, update_id=984013, actor=actor)
    )
    oren = await service.resume(actor)
    assert oren is not None and oren.kind == "oren" and oren.step == 5
    await dispatcher.feed_raw_update(
        bot,
        callback_update(refuge_button.callback_data, update_id=984019, actor=actor),
    )
    assert (await service.resume(actor)).kind == "oren"
    oren_button = next(
        button
        for row in render_p2(oren).keyboard.inline_keyboard
        for button in row
        if button.text == "Falar com Oren Cal"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(oren_button.callback_data, update_id=984014, actor=actor)
    )
    alda = await service.resume(actor)
    assert alda is not None and alda.kind == "alda" and alda.step == 6
    await dispatcher.feed_raw_update(
        bot, callback_update(oren_button.callback_data, update_id=984025, actor=actor)
    )
    assert (await service.resume(actor)).kind == "alda"
    assert "Também não vou chamá-la de escrita até termos prova." in render_p2(alda).text
    report_button = next(
        button
        for row in render_p2(alda).keyboard.inline_keyboard
        for button in row
        if button.text == "Alda Veyr"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(report_button.callback_data, update_id=984015, actor=actor)
    )
    completed = await service.resume(actor)
    assert completed is not None and completed.status == "completed"
    await dispatcher.feed_raw_update(
        bot,
        callback_update(report_button.callback_data, update_id=984026, actor=actor),
    )
    assert (await service.resume(actor)).status == "completed"
    async with database[1]() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == "p2.fuligem_sem_fogo",
            )
        ) is not None


@pytest.mark.asyncio
async def test_p2_defeat_retry_ui_keeps_consumable_stock_and_resets_only_encounter_budget(
    database, monkeypatch
):
    actor = 984030
    character_id, service = await _seed(database, actor)
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.hp = Decimal(100)
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id="consumable.heal",
                quantity=2,
            )
        )
    initial = await _start_combat(service, actor)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(p2_router(service, {}))
    dispatcher.include_router(
        combat_router(
            PrologueService(database[1], "ocaso", PROFILE),
            {},
            road=RoadService(database[1], "ocaso"),
            p2=service,
        )
    )
    bot = _telegram()

    hud = render_p2(initial)
    open_callback = next(
        button.callback_data
        for row in hud.keyboard.inline_keyboard
        for button in row
        if button.text == "Consumível"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(open_callback, update_id=984031, actor=actor)
    )
    item_callback = next(
        button.callback_data
        for row in _last_method(bot).reply_markup.inline_keyboard
        for button in row
        if button.text.isdigit()
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(item_callback, update_id=984032, actor=actor)
    )
    used = await service.resume(actor)
    assert used is not None and used.combat is not None
    assert used.combat.consumable_uses == 1
    assert await _stack_quantity(database, actor, "consumable.heal") == 1

    import asterion.application.p2 as p2_module

    monkeypatch.setattr(p2_module, "act", _finish_with("defeat"))
    attack = next(
        button.callback_data
        for row in render_p2(used).keyboard.inline_keyboard
        for button in row
        if button.text == "Atacar"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(attack, update_id=984033, actor=actor)
    )
    recovery = _last_method(bot)
    assert "💀 Derrota" in recovery.text
    assert "❤️ HP · Restaurado" in recovery.text
    assert "Braseiro da Estrada" not in recovery.text
    assert "Descansar" not in recovery.text
    retry_callback = next(
        button.callback_data
        for row in recovery.reply_markup.inline_keyboard
        for button in row
        if button.text == "Retornar à Charneca"
    )
    assert await _stack_quantity(database, actor, "consumable.heal") == 1

    await dispatcher.feed_raw_update(
        bot, callback_update(retry_callback, update_id=984034, actor=actor)
    )
    retried = await service.resume(actor)
    assert retried is not None and retried.kind == "combat"
    assert retried.activity_id != initial.activity_id
    assert retried.encounter_id != initial.encounter_id
    assert retried.combat_id != initial.combat_id
    assert retried.combat.consumable_uses == 0
    assert retried.consumable_budget_limit == 1
    assert retried.combat.fighters["enemy"].name == "Aranha de Cinza"
    assert retried.combat.variant is None
    assert await _stack_quantity(database, actor, "consumable.heal") == 1

    await dispatcher.feed_raw_update(
        bot, callback_update(retry_callback, update_id=984035, actor=actor)
    )
    repeated = await service.resume(actor)
    assert repeated is not None and repeated.activity_id == retried.activity_id
    assert repeated.encounter_id == retried.encounter_id
    assert repeated.combat_id == retried.combat_id
    assert repeated.combat.consumable_uses == 0
    assert await _stack_quantity(database, actor, "consumable.heal") == 1


@pytest.mark.asyncio
async def test_p2_consumable_flow_is_shared_idempotent_and_reconnectable(database):
    actor = 984020
    character_id, service = await _seed(database, actor)
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.hp = Decimal(100)
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id="consumable.heal",
                quantity=2,
            )
        )

    initial = await _start_combat(service, actor)
    assert any(option.item_id == "consumable.heal" for option in initial.consumable_options)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        combat_router(
            PrologueService(database[1], "ocaso", PROFILE),
            {},
            road=RoadService(database[1], "ocaso"),
            p2=service,
        )
    )
    bot = _telegram()
    hud = render_p2(initial)
    open_callback = next(
        button.callback_data
        for row in hud.keyboard.inline_keyboard
        for button in row
        if button.text == "Consumível"
    )
    open_data = CombatConsumableFlowCallback.unpack(open_callback)
    assert open_data.step == "o"
    await dispatcher.feed_raw_update(
        bot, callback_update(open_callback, update_id=984021, actor=actor)
    )
    item_method = _last_method(bot)
    item_callback = next(
        button.callback_data
        for row in item_method.reply_markup.inline_keyboard
        for button in row
        if button.text.isdigit()
    )
    item_choice = CombatConsumableFlowCallback.unpack(item_callback)
    assert item_choice.step == "i" and item_choice.item_id == "consumable.heal"
    assert item_choice.state_version == initial.combat.version

    await dispatcher.feed_raw_update(
        bot, callback_update(item_callback, update_id=984022, actor=actor)
    )
    used = await P2Service(database[1], "ocaso").resume(actor)
    assert used is not None and used.combat is not None
    assert used.activity_id == initial.activity_id
    assert used.encounter_id == initial.encounter_id
    assert used.combat_id == initial.combat_id
    assert used.combat.version == initial.combat.version + 1
    assert used.combat.consumable_uses == 1
    assert await _stack_quantity(database, actor, "consumable.heal") == 1

    # A duplicate callback from the chooser uses the old combat version.
    await dispatcher.feed_raw_update(
        bot, callback_update(item_callback, update_id=984023, actor=actor)
    )
    stale = await P2Service(database[1], "ocaso").resume(actor)
    assert stale is not None and stale.combat is not None
    assert stale.combat.version == used.combat.version
    assert stale.combat.consumable_uses == 1
    assert await _stack_quantity(database, actor, "consumable.heal") == 1

    # A forged fresh-version use is rejected by the encounter-wide uncommon budget.
    rejected_callback = CombatConsumableCallback.for_option(
        used.activity_id,
        used.combat.version,
        initial.consumable_options[0],
    ).pack()
    await dispatcher.feed_raw_update(
        bot, callback_update(rejected_callback, update_id=984024, actor=actor)
    )
    rejected = await service.resume(actor)
    assert rejected is not None and rejected.combat is not None
    assert rejected.combat.version == used.combat.version
    assert rejected.combat.consumable_uses == 1
    assert await _stack_quantity(database, actor, "consumable.heal") == 1

    reconnected = await P2Service(database[1], "ocaso").resume(actor)
    assert reconnected is not None
    assert reconnected.activity_id == used.activity_id
    assert reconnected.encounter_id == used.encounter_id
    assert reconnected.combat_id == used.combat_id
    assert reconnected.combat.consumable_uses == 1
    assert dict(reconnected.consumable_quantities)["consumable.heal"] == 1
    assert reconnected.consumable_budget_limit == 1


async def _stack_quantity(database, actor, item_id):
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        quantity = await session.scalar(
            select(ConsumableStack.quantity).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == item_id,
            )
        )
        return int(quantity)


@pytest.mark.asyncio
async def test_menu_start_and_missions_reconstruct_p2_without_exposing_normal_charneca(
    database,
):
    actor = 984040
    _, p2_service = await _seed(database, actor)
    view = await p2_service.alda(actor)
    await p2_service.accept(actor, view.state_version)
    await p2_service.travel_to_charneca(actor, 0)
    await p2_service.examine_ash_point(actor, ASH_POINT_IDS[1], 1)

    p1_service = AsyncMock(spec=P1Service)
    p1_service.resume.return_value = None
    world_service = AsyncMock(spec=WorldService)
    world_service.resume.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            world_service,
            {},
            p1=p1_service,
            road=RoadService(database[1], "ocaso"),
            p2=p2_service,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, message_update("/menu", update_id=984041, actor=actor)
    )
    menu_method = _last_method(bot)
    assert "Examinar Pontos de Fuligem · 1/3" in menu_method.text
    assert "Caçadas · Disponível" not in menu_method.text
    assert "Desbravar · Disponível" not in menu_method.text

    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:missions", update_id=984042, actor=actor),
    )
    assert "Fuligem sem Fogo · Em Andamento" in _last_method(bot).text
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:principal", update_id=984043, actor=actor),
    )
    assert "Examinar Pontos de Fuligem · 1/3" in _last_method(bot).text


@pytest.mark.asyncio
async def test_refuge_map_does_not_offer_remote_npc_interaction(database):
    actor = 984050
    character_id, _ = await _seed(database, actor)
    async with database[1].begin() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        assert world is not None
        world.location = "Estrada das Cinzas"

    p1 = AsyncMock(spec=P1Service)
    p1.resume.return_value = SimpleNamespace(
        known_locations=(
            "tdo.location.estrada_das_cinzas",
            "tdo.location.refugio_do_ocaso",
        ),
        status="completed",
        combat=None,
    )
    world_service = AsyncMock(spec=WorldService)
    world_service.resume.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            world_service,
            {},
            p1=p1,
            road=RoadService(database[1], "ocaso"),
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot,
        callback_update("world:map:local:refuge", update_id=984051, actor=actor),
    )
    screen = _last_method(bot)
    assert "Refúgio do Ocaso" in screen.text
    labels = [
        button.text
        for row in screen.reply_markup.inline_keyboard
        for button in row
    ]
    assert "Alda Veyr" not in labels and "Oren Cal" not in labels


@pytest.mark.asyncio
async def test_generic_refuge_oren_route_preserves_s1_when_p2_is_not_at_oren(database):
    actor = 984052
    p2 = AsyncMock(spec=P2Service)
    p2.resume.return_value = None
    p1 = AsyncMock(spec=P1Service)
    p1.resume.return_value = None
    s1 = AsyncMock(spec=S1Service)
    s1.oren.return_value = S1View(
        kind="oren",
        character_id=uuid4(),
        status="active",
        step=4,
        state_version=2,
        progress={},
        tracked=False,
        location="Refúgio do Ocaso",
        level=3,
    )
    world_service = AsyncMock(spec=WorldService)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(world_service, {}, p1=p1, s1=s1, p2=p2)
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, callback_update("world:oren", update_id=984053, actor=actor)
    )

    s1.oren.assert_awaited_once_with(actor)
    assert "Luzes sob as Cinzas · Em Andamento" in _last_method(bot).text
    assert any(
        button.callback_data == "s1:2:complete"
        for row in _last_method(bot).reply_markup.inline_keyboard
        for button in row
    )


@pytest.mark.asyncio
async def test_start_restores_same_p2_combat_and_does_not_reopen_completed_p2(
    database, monkeypatch
):
    actor = 984060
    _, p2_service = await _seed(database, actor)
    active = await _start_combat(p2_service, actor)
    creation = AsyncMock()
    creation.start.return_value = object()
    p1_service = AsyncMock(spec=P1Service)
    p1_service.resume.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        creation_router(
            creation,
            {},
            p1=p1_service,
            road=RoadService(database[1], "ocaso"),
            p2=p2_service,
        )
    )
    bot = _telegram()
    await dispatcher.feed_raw_update(
        bot, message_update("/start", update_id=984061, actor=actor)
    )
    restored = _last_method(bot)
    assert "Registro de Combate · Recentes" in restored.text
    current = await p2_service.resume(actor)
    assert current is not None and current.activity_id == active.activity_id
    assert current.encounter_id == active.encounter_id
    assert current.combat_id == active.combat_id

    completed_actor = 984063
    _, completed_service = await _seed(database, completed_actor)
    await _complete_p2(completed_service, completed_actor, monkeypatch)
    completed_dispatcher = Dispatcher(disable_fsm=True)
    completed_dispatcher.include_router(
        creation_router(
            creation,
            {},
            p1=p1_service,
            road=RoadService(database[1], "ocaso"),
            p2=P2Service(database[1], "ocaso"),
        )
    )
    await completed_dispatcher.feed_raw_update(
        bot, message_update("/start", update_id=984064, actor=completed_actor)
    )
    assert "Braseiro do Refúgio" in _last_method(bot).text
    assert "Fuligem sem Fogo · Concluída" not in _last_method(bot).text


@pytest.mark.asyncio
async def test_start_reconstructs_every_active_p2_narrative_state(database, monkeypatch):
    import asterion.application.p2 as p2_module

    dispatcher = Dispatcher(disable_fsm=True)
    creation = AsyncMock()
    bot = _telegram()
    runtime_service = P2Service(database[1], "ocaso")
    dispatcher.include_router(creation_router(creation, {}, p2=runtime_service))
    states = (
        ("travel", "Viajar até a Charneca da Fuligem"),
        ("ash", "Examinar Pontos de Fuligem · 1/3"),
        ("combat", "Registro de Combate · Recentes"),
        ("recovery", "💀 Derrota"),
        ("stone", "Examinar a Pedra Marcada"),
        ("oren", "Entregar o registro da Pedra Marcada"),
        ("alda", "Reportar a situação a Alda Veyr"),
    )
    update_id = 984070
    for index, (state, expected_text) in enumerate(states):
        actor = 984080 + index
        _, service = await _seed(database, actor)
        if state == "travel":
            offer = await service.alda(actor)
            await service.accept(actor, offer.state_version)
        elif state == "ash":
            offer = await service.alda(actor)
            accepted = await service.accept(actor, offer.state_version)
            traveled = await service.travel_to_charneca(actor, accepted.state_version)
            await service.examine_ash_point(actor, ASH_POINT_IDS[0], traveled.state_version)
        elif state == "combat":
            await _start_combat(service, actor)
        elif state == "recovery":
            combat = await _start_combat(service, actor)
            monkeypatch.setattr(p2_module, "act", _finish_with("defeat"))
            await service.action(
                actor, combat.activity_id, combat.activity_state_version, "attack"
            )
        elif state in {"stone", "oren", "alda"}:
            combat = await _start_combat(service, actor)
            monkeypatch.setattr(p2_module, "act", _finish_with("victory"))
            victory = await service.action(
                actor, combat.activity_id, combat.activity_state_version, "attack"
            )
            stone = victory
            if state in {"oren", "alda"}:
                stone = await service.examine_pedra_marcada(
                    actor, victory.state_version
                )
                refuge = await service.return_to_refuge(actor, stone.state_version)
                if state == "alda":
                    await service.oren(actor, refuge.state_version)
        await dispatcher.feed_raw_update(
            bot,
            message_update("/start", update_id=update_id, actor=actor),
        )
        update_id += 1
        assert expected_text in _last_method(bot).text
