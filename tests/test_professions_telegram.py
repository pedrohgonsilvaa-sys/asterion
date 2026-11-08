from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.crafting import CraftingService
from asterion.application.professions import ProfessionService
from asterion.bot.character_ui import render_character
from asterion.bot.profession_handlers import profession_router
from asterion.domain.professions import RECIPE_DEFINITIONS, VARZEAS_ESSENCE, VARZEAS_REAGENT
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    CharacterProfession,
    ConsumableStack,
    EquipmentItem,
    MaterialStack,
    WorldState,
)
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _last_screen(bot):
    for call in reversed(bot.session.make_request.call_args_list):
        method = call.args[1]
        if hasattr(method, "reply_markup") and hasattr(method, "text"):
            return method
    raise AssertionError("Telegram did not receive a screen update")


def _button(screen, label):
    for row in screen.reply_markup.inline_keyboard:
        for button in row:
            if button.text == label:
                return button
    raise AssertionError(f"Button {label!r} is missing from the current screen")


def _assert_callbacks_fit(screen):
    if screen.reply_markup is None:
        return
    for row in screen.reply_markup.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) <= 64


async def _click(dispatcher, bot, data, *, actor, update_id):
    await dispatcher.feed_raw_update(
        bot,
        callback_update(data, update_id=update_id, actor=actor),
    )
    screen = _last_screen(bot)
    _assert_callbacks_fit(screen)
    return screen


@pytest.mark.asyncio
async def test_telegram_character_to_professions_crafting_and_change(database):
    actor = 841101
    actor, _road = await _seed_road(database, actor=actor)
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.name = "Crafttelegram"
        character.level = 10
        character.crowns = 5000
        session.add_all(
            [
                MaterialStack(
                    character_id=character.id,
                    material_id="material.tdo.ferro_de_fuligem",
                    quantity=7,
                    bound=False,
                ),
                MaterialStack(
                    character_id=character.id,
                    material_id="material.tdo.residuo_ocaso",
                    quantity=3,
                    bound=False,
                ),
            ]
        )
        character_id = character.id

    screen = render_character()
    assert any(
        button.callback_data == "character:professions"
        for row in screen.keyboard.inline_keyboard
        for button in row
    )

    sessions = database[1]
    profession_service = ProfessionService(sessions, "ocaso")
    crafting_service = CraftingService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(profession_router(profession_service, crafting_service, {}))
    bot = _telegram()
    step = 0

    screen = await _click(dispatcher, bot, "character:professions", actor=actor, update_id=step)
    step += 1
    assert "escolha inicial" in screen.text
    screen = await _click(
        dispatcher,
        bot,
        _button(screen, "Escolher Ofícios").callback_data,
        actor=actor,
        update_id=step,
    )
    step += 1
    screen = await _click(dispatcher, bot, "prof:ip:0", actor=actor, update_id=step)
    step += 1
    screen = await _click(dispatcher, bot, "prof:is:0:2", actor=actor, update_id=step)
    step += 1
    assert "Ferreiro" in screen.text and "Alquimista" in screen.text

    screen = await _click(dispatcher, bot, "craft:root", actor=actor, update_id=step)
    step += 1
    assert "Ferreiro" in screen.text
    screen = await _click(dispatcher, bot, "craft:recipes:0", actor=actor, update_id=step)
    step += 1
    assert "Arma do Caminhante" in screen.text
    screen = await _click(dispatcher, bot, "craft:r:0", actor=actor, update_id=step)
    step += 1
    assert "Preview de Criação" in [
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    ]
    screen = await _click(
        dispatcher,
        bot,
        _button(screen, "Preview de Criação").callback_data,
        actor=actor,
        update_id=step,
    )
    step += 1
    assert "🛠️ Criação · Preview" in screen.text
    create_callback = _button(screen, "Criar").callback_data
    assert len(create_callback.encode()) < 64
    screen = await _click(dispatcher, bot, create_callback, actor=actor, update_id=step)
    step += 1
    assert "Criação concluída" in screen.text

    screen = await _click(dispatcher, bot, create_callback, actor=actor, update_id=step)
    step += 1
    assert "Criação concluída" in screen.text
    async with sessions() as session:
        items = (
            await session.scalars(
                select(EquipmentItem).where(EquipmentItem.character_id == character_id)
            )
        ).all()
        assert len(items) == 1

    screen = await _click(dispatcher, bot, "prof:change", actor=actor, update_id=step)
    step += 1
    screen = await _click(dispatcher, bot, "prof:swap", actor=actor, update_id=step)
    step += 1
    assert "Confirmar Inversão" in [
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    ]
    confirm_callback = _button(screen, "Confirmar Inversão").callback_data
    assert len(confirm_callback.encode()) < 64
    screen = await _click(dispatcher, bot, confirm_callback, actor=actor, update_id=step)
    assert "Alquimista" in screen.text and "Ferreiro" in screen.text
    async with sessions() as session:
        slots = (
            await session.scalars(
                select(CharacterProfession).where(CharacterProfession.character_id == character_id)
            )
        ).all()
        assert {row.slot: row.profession_id for row in slots} == {
            "primary": "alchemist",
            "secondary": "blacksmith",
        }


@pytest.mark.asyncio
async def test_telegram_porto_alchemy_preview_confirmation_and_duplicate_callback(database):
    actor = 841102
    actor, _road = await _seed_road(database, actor=actor)
    sessions = database[1]
    profession_service = ProfessionService(sessions, "ocaso")
    assert await profession_service.initial_selection(actor, "alchemist", "artificer")
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 40
        character.crowns = 41310
        world = await session.get(WorldState, character.id)
        world.region = "Várzeas Carmesins"
        world.location = "Porto da Salmoura"
        alchemist = await session.scalar(
            select(CharacterProfession).where(
                CharacterProfession.character_id == character.id,
                CharacterProfession.profession_id == "alchemist",
            )
        )
        alchemist.level = 12
        session.add(Brazier(character_id=character.id, brazier_id="varzeas.brazier.porto"))
        session.add_all(
            [
                MaterialStack(
                    character_id=character.id,
                    material_id=VARZEAS_REAGENT,
                    quantity=3,
                    bound=False,
                ),
                MaterialStack(
                    character_id=character.id,
                    material_id=VARZEAS_ESSENCE,
                    quantity=1,
                    bound=False,
                ),
            ]
        )
        character_id = character.id

    crafting_service = CraftingService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(profession_router(profession_service, crafting_service, {}))
    bot = _telegram()
    step = 0
    screen = await _click(dispatcher, bot, "character:professions", actor=actor, update_id=step)
    step += 1
    alchemist_index = 2
    screen = await _click(
        dispatcher,
        bot,
        f"prof:d:{alchemist_index}",
        actor=actor,
        update_id=step,
    )
    step += 1
    assert "Criação · Produzir" in screen.text
    assert "Criação" in [
        button.text for row in screen.reply_markup.inline_keyboard for button in row
    ]

    screen = await _click(
        dispatcher, bot, "craft:recipes:2", actor=actor, update_id=step
    )
    step += 1
    recipe_index = next(
        index
        for index, recipe in enumerate(RECIPE_DEFINITIONS)
        if recipe.recipe_id == "recipe.varzeas.alchemist.heal.varzeas.iv"
    )
    screen = await _click(
        dispatcher,
        bot,
        f"craft:r:{recipe_index}",
        actor=actor,
        update_id=step,
    )
    step += 1
    preview_callback = _button(screen, "Preview de Criação").callback_data
    screen = await _click(dispatcher, bot, preview_callback, actor=actor, update_id=step)
    step += 1
    assert "🛠️ Criação · Preview" in screen.text
    assert "Poção de Cura da Salmoura" in screen.text
    create_callback = _button(screen, "Criar").callback_data
    screen = await _click(dispatcher, bot, create_callback, actor=actor, update_id=step)
    step += 1
    assert "Criação concluída" in screen.text
    screen = await _click(dispatcher, bot, create_callback, actor=actor, update_id=step)
    assert "Criação concluída" in screen.text

    async with sessions() as session:
        character = await session.get(Character, character_id)
        potion = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.heal.varzeas.iv",
            )
        )
        materials = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character_id)
            )
        ).all()
        assert character.crowns == 41240
        assert potion is not None and potion.quantity == 1
        assert materials == []
