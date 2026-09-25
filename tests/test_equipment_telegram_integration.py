from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.equipment import EquipmentService
from asterion.application.equipment_view import EquipmentViewService
from asterion.application.inventory import InventoryService
from asterion.application.world import WorldService
from asterion.bot.equipment_handlers import equipment_router
from asterion.bot.world_handlers import world_router
from asterion.domain.equipment import EquipmentSlot
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    EquipmentItem,
    GameActivity,
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


def _last_callback_answer(bot):
    for call in reversed(bot.session.make_request.call_args_list):
        method = call.args[1]
        if method.__class__.__name__ == "AnswerCallbackQuery":
            return method
    return None


def _buttons(screen):
    return [
        button
        for row in screen.reply_markup.inline_keyboard
        for button in row
    ]


def _dispatcher(database):
    sessions = database[1]
    inventory = InventoryService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        equipment_router(
            EquipmentViewService(sessions, "ocaso"),
            EquipmentService(sessions, "ocaso"),
            inventory,
            {},
        )
    )
    dispatcher.include_router(
        world_router(WorldService(sessions, "ocaso"), {}, inventory=inventory)
    )
    return dispatcher


async def _click(dispatcher, telegram, data, *, actor, update_id):
    await dispatcher.feed_raw_update(
        telegram,
        callback_update(data, update_id=update_id, actor=actor),
    )
    return _last_screen(telegram)


async def _add_item(
    database,
    actor,
    *,
    name,
    slot,
    core,
    rarity="Raro",
    item_level=1,
    enhancement=0,
    secondaries=None,
):
    item_id = uuid4()
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character.id,
                source_key=f"test:telegram-equipment:{item_id}",
                item_name=name,
                rarity=rarity,
                slot=slot,
                item_level=item_level,
                bound=True,
                payload={
                    "slot": slot,
                    "core": core,
                    "secondaries": secondaries or [],
                    "enhancement": enhancement,
                    "rune": None,
                    "enchantment": None,
                },
            )
        )
    return item_id


async def _equipped_state(database, actor):
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        slots = (
            await session.scalars(
                select(CharacterEquipmentSlot).where(
                    CharacterEquipmentSlot.character_id == character.id
                )
            )
        ).all()
        return character, {row.slot: row.equipment_item_id for row in slots}


@pytest.mark.asyncio
async def test_telegram_inventory_equip_unequip_and_duplicate_callback_are_persisted(database):
    actor, _ = await _seed_road(database, actor=783101)
    item_id = await _add_item(
        database,
        actor,
        name="Elmo de Cinzas",
        slot="Cabeça",
        core={"HP": 12},
        enhancement=1,
        secondaries=[{"attribute": "PER", "value": "0.25"}],
    )
    dispatcher, telegram = _dispatcher(database), _telegram()

    screen = await _click(dispatcher, telegram, "character:root", actor=actor, update_id=9101)
    assert "🪪 Personagem" in screen.text
    screen = await _click(dispatcher, telegram, "inventory:root", actor=actor, update_id=9102)
    assert "🎒 Inventário" in screen.text
    screen = await _click(
        dispatcher,
        telegram,
        "inventory:category:equipment",
        actor=actor,
        update_id=9103,
    )
    assert "1 🪖 Elmo de Cinzas · +1" in screen.text
    detail_callback = _buttons(screen)[0].callback_data
    assert detail_callback == f"eq:v:{item_id.hex}"

    screen = await _click(
        dispatcher, telegram, detail_callback, actor=actor, update_id=9104
    )
    assert "🔵 Raro · Cabeça" in screen.text
    assert "🔗 Vinculado" in screen.text
    assert "📈 Nível do Item · 1" in screen.text
    assert "❤️ HP +12.24" in screen.text
    assert "🗡️ PER +0.255%" in screen.text
    assert [button.text for button in _buttons(screen)] == ["Equipar", "← Equipamentos"]
    equip_callback = _buttons(screen)[0].callback_data
    assert len(equip_callback.encode()) <= 64

    character_before, _ = await _equipped_state(database, actor)
    hp_before = character_before.max_hp
    screen = await _click(
        dispatcher, telegram, equip_callback, actor=actor, update_id=9105
    )
    assert "✅ Equipado" in screen.text
    assert "Equipar" not in [button.text for button in _buttons(screen)]
    assert [button.text for button in _buttons(screen)] == ["Desequipar", "← Equipamentos"]
    character_after, equipped = await _equipped_state(database, actor)
    assert equipped == {EquipmentSlot.CABECA.value: item_id}
    assert character_after.combat_configuration_version == 1
    assert character_after.max_hp > hp_before

    # A callback replay retains its old version and cannot change HP/version twice.
    screen = await _click(
        dispatcher, telegram, equip_callback, actor=actor, update_id=9106
    )
    assert "✅ Equipado" in screen.text
    assert character_after.combat_configuration_version == 1
    assert _last_callback_answer(telegram).text == "Configuração atualizada."
    character_replayed, replayed_slots = await _equipped_state(database, actor)
    assert replayed_slots == equipped
    assert character_replayed.combat_configuration_version == 1
    assert character_replayed.hp == character_after.hp
    assert character_replayed.max_hp == character_after.max_hp

    unequip_callback = _buttons(screen)[0].callback_data
    assert unequip_callback == "eq:u:h:1:i"
    screen = await _click(
        dispatcher, telegram, unequip_callback, actor=actor, update_id=9107
    )
    assert "Elmo de Cinzas" in screen.text
    assert "✅ Equipado" not in screen.text
    assert [button.text for button in _buttons(screen)] == ["Equipar", "← Equipamentos"]
    character_final, final_slots = await _equipped_state(database, actor)
    assert final_slots == {}
    assert character_final.combat_configuration_version == 2


@pytest.mark.asyncio
async def test_telegram_slot_swap_and_two_handed_equipment_use_authoritative_service(database):
    actor, _ = await _seed_road(database, actor=783102)
    first_head = await _add_item(
        database,
        actor,
        name="Elmo Antigo",
        slot="Cabeça",
        core={"HP": 3},
    )
    second_head = await _add_item(
        database,
        actor,
        name="Elmo Novo",
        slot="Cabeça",
        core={"HP": 8},
    )
    offhand = await _add_item(
        database,
        actor,
        name="Escudo de Cinzas",
        slot="Secundária",
        core={"DEF": 5},
    )
    two_handed = await _add_item(
        database,
        actor,
        name="Lança Longa",
        slot="2H",
        core={"ATQ": 15},
    )
    service = EquipmentService(database[1], "ocaso")
    assert (await service.equip_item(actor, first_head)).changed
    assert (await service.equip_item(actor, offhand)).changed
    dispatcher, telegram = _dispatcher(database), _telegram()

    screen = await _click(dispatcher, telegram, "eq:r", actor=actor, update_id=9201)
    assert "3 🪖 Cabeça · Elmo Antigo · +0" in screen.text
    screen = await _click(
        dispatcher, telegram, "eq:s:h:2", actor=actor, update_id=9202
    )
    assert "Elmo Antigo" in screen.text
    assert [button.text for button in _buttons(screen)][:2] == ["Trocar", "Desequipar"]
    screen = await _click(
        dispatcher, telegram, "eq:c:h:2", actor=actor, update_id=9203
    )
    assert "Elmo Novo" in screen.text
    assert "Elmo Antigo" not in screen.text
    assert _buttons(screen)[0].callback_data == f"eq:e:{second_head.hex}:2:s"
    screen = await _click(
        dispatcher,
        telegram,
        _buttons(screen)[0].callback_data,
        actor=actor,
        update_id=9204,
    )
    assert "3 🪖 Cabeça · Elmo Novo · +0" in screen.text
    character, equipped = await _equipped_state(database, actor)
    assert equipped[EquipmentSlot.CABECA.value] == second_head
    assert character.combat_configuration_version == 3

    # Principal is empty: its candidate list contains the two-handed item only.
    screen = await _click(
        dispatcher,
        telegram,
        f"eq:s:p:{character.combat_configuration_version}",
        actor=actor,
        update_id=9205,
    )
    assert "Lança Longa · +0" in screen.text
    screen = await _click(
        dispatcher,
        telegram,
        _buttons(screen)[0].callback_data,
        actor=actor,
        update_id=9206,
    )
    assert "1 🗡️ Arma Principal · Lança Longa · +0" in screen.text
    assert "2 ⚔️ Arma Secundária · Bloqueada" in screen.text
    character, equipped = await _equipped_state(database, actor)
    assert equipped == {
        EquipmentSlot.CABECA.value: second_head,
        EquipmentSlot.PRINCIPAL.value: two_handed,
    }
    assert character.combat_configuration_version == 4

    inventory = await InventoryService(database[1], "ocaso").category(actor, "equipment")
    assert inventory is not None
    by_id = {entry.key: entry for entry in inventory.entries}
    assert not by_id[str(offhand)].equipped
    assert by_id[str(two_handed)].equipped


@pytest.mark.asyncio
async def test_telegram_equipment_callback_rejects_foreign_item_and_locked_mutation(
    database,
):
    actor, _ = await _seed_road(database, actor=783103)
    item_id = await _add_item(
        database,
        actor,
        name="Peitoral de Cinzas",
        slot="Torso",
        core={"HP": 8},
    )
    dispatcher, telegram = _dispatcher(database), _telegram()

    foreign = await EquipmentViewService(database[1], "ocaso").detail(99999999, item_id)
    assert foreign is None
    await dispatcher.feed_raw_update(
        telegram,
        callback_update(f"eq:v:{item_id.hex}", update_id=9301, actor=99999999),
    )
    assert "Equipamento indisponível." in _last_callback_answer(telegram).text
    assert (await _equipped_state(database, actor))[1] == {}

    detail = await EquipmentViewService(database[1], "ocaso").detail(actor, item_id)
    assert detail is not None
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            GameActivity(
                character_id=character.id,
                content_id="test.combat",
                status="active",
                state_version=1,
                ruleset_version="test-ruleset",
            )
        )

    screen = await _click(
        dispatcher,
        telegram,
        f"eq:e:{item_id.hex}:{detail.combat_configuration_version}:i",
        actor=actor,
        update_id=9302,
    )
    assert "Peitoral de Cinzas" in screen.text
    assert "Equipar" in [button.text for button in _buttons(screen)]
    assert _last_callback_answer(telegram).text == (
        "Equipamentos não podem ser alterados durante esta atividade."
    )
    character, equipped = await _equipped_state(database, actor)
    assert equipped == {}
    assert character.combat_configuration_version == 0
