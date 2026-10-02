"""Telegram equipment actions use the persisted C2 service and compact callbacks."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.equipment import EquipmentService
from asterion.application.equipment_modifications import EquipmentModificationService
from asterion.application.equipment_view import EquipmentViewService
from asterion.application.inventory import InventoryService
from asterion.bot.equipment_handlers import equipment_router
from asterion.bot.equipment_modification_handlers import equipment_modification_router
from asterion.infrastructure.db.models import (
    Character,
    CharacterProfession,
    EquipmentItem,
    MaterialStack,
    RuneStack,
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
    raise AssertionError("Telegram did not receive a screen")


def _button(screen, label):
    for row in screen.reply_markup.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) <= 64
            if button.text == label:
                return button
    raise AssertionError(f"Missing button: {label}")


async def _click(dispatcher, bot, callback, *, actor, update_id):
    await dispatcher.feed_raw_update(
        bot,
        callback_update(callback, actor=actor, update_id=update_id),
    )
    return _last_screen(bot)


def _dispatcher(database):
    sessions = database[1]
    inventory = InventoryService(sessions, "ocaso")
    reads = EquipmentViewService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        equipment_router(reads, EquipmentService(sessions, "ocaso"), inventory, {})
    )
    dispatcher.include_router(
        equipment_modification_router(
            EquipmentModificationService(sessions, "ocaso"), reads, inventory, {}
        )
    )
    return dispatcher


@pytest.mark.asyncio
async def test_telegram_equipment_modification_rejects_stale_and_preserves_item(database):
    actor, _ = await _seed_road(database, actor=984201)
    item_id = uuid4()
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 10
        character.crowns = 5000
        session.add_all(
            [
                EquipmentItem(
                    id=item_id,
                    character_id=character.id,
                    source_key=f"test:c2:telegram:{item_id}",
                    item_name="Elmo de Fuligem",
                    rarity="Raro",
                    slot="Cabeça",
                    item_level=10,
                    bound=False,
                    payload={
                        "item_instance_id": str(item_id),
                        "slot": "Cabeça",
                        "core": {"HP": 12, "DEF": 2},
                        "secondaries": [{"attribute": "PER", "value": "0.25"}],
                        "enhancement": 0,
                        "rune": None,
                        "enchantment": None,
                    },
                ),
                CharacterProfession(
                    character_id=character.id,
                    slot="primary",
                    profession_id="artificer",
                    level=10,
                    pxp=0,
                ),
                MaterialStack(
                    character_id=character.id,
                    material_id="material.tdo.fragmento_aprimoramento_i",
                    quantity=20,
                    bound=False,
                ),
                MaterialStack(
                    character_id=character.id,
                    material_id="material.tdo.residuo_ocaso",
                    quantity=20,
                    bound=False,
                ),
                MaterialStack(
                    character_id=character.id,
                    material_id="material.tdo.ferro_de_fuligem",
                    quantity=20,
                    bound=False,
                ),
                RuneStack(
                    character_id=character.id,
                    family="Persistência",
                    rarity="Rara",
                    grade=1,
                    potency="0.35%",
                    quantity=1,
                    bound=False,
                ),
            ]
        )
    dispatcher, bot = _dispatcher(database), _telegram()
    index = 1
    screen = await _click(dispatcher, bot, f"eq:v:{item_id.hex}", actor=actor, update_id=index)
    index += 1
    assert "Elmo de Fuligem" in screen.text
    assert "Runas" in [button.text for row in screen.reply_markup.inline_keyboard for button in row]

    screen = await _click(
        dispatcher, bot, _button(screen, "Aprimorar").callback_data, actor=actor,
        update_id=index,
    )
    index += 1
    assert "🔼 Aprimoramento" in screen.text
    enhance = _button(screen, "Aprimorar").callback_data
    screen = await _click(dispatcher, bot, enhance, actor=actor, update_id=index)
    index += 1
    assert "+1" in screen.text
    screen = await _click(dispatcher, bot, enhance, actor=actor, update_id=index)
    index += 1
    assert "+1" in screen.text

    screen = await _click(
        dispatcher, bot, _button(screen, "Runas").callback_data, actor=actor,
        update_id=index,
    )
    index += 1
    assert "Persistência" in screen.text
    # A new, earlier-sorting stack must not retarget the old button by index.
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(
            RuneStack(
                character_id=character.id,
                family="Brasa",
                rarity="Rara",
                grade=1,
                potency="0.35%",
                quantity=1,
                bound=False,
            )
        )
    screen = await _click(
        dispatcher, bot, _button(screen, "1").callback_data, actor=actor,
        update_id=index,
    )
    index += 1
    assert "Instalar Runa" in screen.text
    assert "Persistência" in screen.text and "Brasa" not in screen.text
    screen = await _click(
        dispatcher, bot, _button(screen, "Instalar Runa").callback_data,
        actor=actor, update_id=index,
    )
    index += 1
    assert "Persistência" in screen.text

    screen = await _click(
        dispatcher, bot, _button(screen, "Encantamento").callback_data,
        actor=actor, update_id=index,
    )
    index += 1
    assert "Receitas Disponíveis" in screen.text
    assert _button(screen, "1").callback_data.startswith("em:ep:")
    screen = await _click(
        dispatcher, bot, _button(screen, "1").callback_data,
        actor=actor, update_id=index,
    )
    index += 1
    assert "💫 Encantamento · Preview" in screen.text
    assert "🔓 Negociável" in screen.text
    assert "Consumir · 3 Negociável" in screen.text
    screen = await _click(
        dispatcher, bot, _button(screen, "Aplicar Encantamento").callback_data,
        actor=actor, update_id=index,
    )
    index += 1
    assert "Pele de Pedra" in screen.text

    screen = await _click(
        dispatcher, bot, f"eq:v:{item_id.hex}", actor=actor, update_id=index,
    )
    index += 1
    screen = await _click(
        dispatcher, bot, _button(screen, "Favoritar").callback_data,
        actor=actor, update_id=index,
    )
    assert "⭐ Favorito" in screen.text
    assert not any(
        button.text == "Desmontar"
        for row in screen.reply_markup.inline_keyboard
        for button in row
    )

    async with database[1]() as session:
        item = await session.get(EquipmentItem, item_id)
        assert item is not None
        assert item.payload["enhancement"] == 1
        assert item.payload["favorite"] is True
