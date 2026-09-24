from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.consumables import ConsumableService
from asterion.application.inventory import InventoryService
from asterion.application.world import WorldService
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    BlockedDelivery,
    Character,
    ConsumableStack,
    EquipmentItem,
    MaterialStack,
    PendingItem,
    RuneStack,
)
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road


@pytest.mark.asyncio
async def test_inventory_root_and_categories_reflect_persisted_character_state(database):
    actor, _ = await _seed_road(database, 773001)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                EquipmentItem(
                    character_id=character.id,
                    source_key="test:inventory:equipment",
                    item_name="Lâmina de Teste",
                    rarity="Raro",
                    slot="Arma Principal",
                    item_level=2,
                    bound=False,
                    payload={"enhancement": 1},
                ),
                ConsumableStack(
                    character_id=character.id,
                    consumable_id="consumable.heal",
                    quantity=4,
                ),
                MaterialStack(
                    character_id=character.id,
                    material_id="material.tdo.ferro_de_fuligem",
                    quantity=7,
                    bound=True,
                ),
                RuneStack(
                    character_id=character.id,
                    family="Brasa",
                    rarity="Raro",
                    grade=1,
                    potency="ATQ +2%",
                    quantity=2,
                    bound=False,
                ),
            ]
        )
        await session.commit()

    service = InventoryService(sessions, "ocaso")
    root = await service.root(actor)
    assert root is not None
    assert root.used_slots == 4
    assert (
        root.equipment_slots,
        root.consumable_slots,
        root.material_slots,
        root.rune_slots,
    ) == (1, 1, 1, 1)

    equipment = await service.category(actor, "equipment")
    consumables = await service.category(actor, "consumables")
    materials = await service.category(actor, "materials")
    runes = await service.category(actor, "runes")

    assert equipment.entries[0].title == "Lâmina de Teste"
    assert equipment.entries[0].item_level == 2
    assert consumables.entries[0].title == "Poção de Cura"
    assert consumables.entries[0].quantity == 4
    assert materials.entries[0].title == "Ferro de Fuligem"
    assert materials.entries[0].bound is True
    assert runes.entries[0].title == "Runa de Brasa"
    assert runes.entries[0].quantity == 2


@pytest.mark.asyncio
async def test_inventory_resolves_catalog_names_and_grades_for_legacy_and_new_stock(database):
    actor, _ = await _seed_road(database, 773003)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                ConsumableStack(
                    character_id=character.id,
                    consumable_id="consumable.heal",
                    quantity=4,
                ),
                ConsumableStack(
                    character_id=character.id,
                    consumable_id="consumable.purification",
                    quantity=2,
                ),
                ConsumableStack(
                    character_id=character.id,
                    consumable_id="consumable.protection.vde.ii",
                    quantity=3,
                ),
            ]
        )
        await session.commit()

    view = await InventoryService(sessions, "ocaso").category(actor, "consumables")
    assert view is not None
    assert [(entry.key, entry.title, entry.quantity, entry.grade) for entry in view.entries] == [
        ("consumable.heal", "Poção de Cura", 4, 1),
        ("consumable.protection.vde.ii", "Preparado de Proteção Enredada", 3, 2),
        ("consumable.purification", "Preparado de Purificação", 2, 1),
    ]


@pytest.mark.asyncio
async def test_pending_root_lists_real_pending_and_blocked_delivery_state(database):
    actor, _ = await _seed_road(database, 773002)
    sessions = database[1]
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            PendingItem(
                character_id=character.id,
                source_key="test:pending:material",
                kind="material",
                payload={
                    "material_id": "material.tdo.couro_escoriado",
                    "bound": False,
                },
                quantity=3,
            )
        )
        session.add(
            BlockedDelivery(
                character_id=character.id,
                source_key="test:blocked:rune",
                kind="rune",
                payload={
                    "family": "Brasa",
                    "rarity": "Raro",
                    "grade": 1,
                    "potency": "ATQ +2%",
                    "bound": False,
                },
                quantity=1,
                status="pending",
            )
        )
        await session.commit()

    service = InventoryService(sessions, "ocaso")
    view = await service.pending(actor)

    assert view is not None
    assert view.pending_count == 1
    assert view.pending_capacity == 20
    assert view.blocked_delivery_count == 1
    assert view.entries[0].title == "Couro Escoriado"
    assert view.entries[0].quantity == 3


@pytest.mark.asyncio
async def test_inventory_service_is_scoped_by_actor_and_server(database):
    actor, _ = await _seed_road(database, 773003)
    service = InventoryService(database[1], "ocaso")
    assert await service.root(actor) is not None
    assert await service.root(999999999) is None
    assert await InventoryService(database[1], "outro").root(actor) is None


@pytest.mark.asyncio
async def test_vigor_detail_tracks_current_stock_and_hides_use_after_consumption(database):
    actor, _ = await _seed_road(database, 773004)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.vigor = 60
        character.vigor_consumable_cycle = None
        session.add(
            ConsumableStack(
                character_id=character.id,
                consumable_id="consumable.vigor.tdo.i",
                quantity=2,
            )
        )

    inventory = InventoryService(sessions, "ocaso")
    before = await inventory.consumable_detail(actor, "consumable.vigor.tdo.i")
    assert before is not None and before.vigor == 60 and before.vigor_usable
    assert before.entries[0].quantity == 2

    updated_vigor = await ConsumableService(sessions, "ocaso").use_vigor_potion(
        actor, "consumable.vigor.tdo.i"
    )
    assert updated_vigor == 80
    after = await inventory.consumable_detail(actor, "consumable.vigor.tdo.i")
    assert after is not None and after.vigor == 80 and not after.vigor_usable
    assert after.entries[0].quantity == 1


@pytest.mark.asyncio
async def test_vigor_inventory_callback_revalidates_and_refreshes_the_detail(database):
    actor, _ = await _seed_road(database, 773005)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.vigor = 60
        character.vigor_consumable_cycle = None
        session.add(
            ConsumableStack(
                character_id=character.id,
                consumable_id="consumable.vigor.tdo.i",
                quantity=1,
            )
        )

    inventory = InventoryService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            inventory=inventory,
            consumables=ConsumableService(sessions, "ocaso"),
        )
    )
    telegram = Bot("123456:local-test-token")
    telegram.session.make_request = AsyncMock(return_value=True)

    await dispatcher.feed_raw_update(
        telegram,
        callback_update(
            "inventory:consumable:consumable.vigor.tdo.i",
            update_id=891,
            actor=actor,
        ),
    )
    detail = telegram.session.make_request.call_args.args[1]
    assert "⚡ Vigor · +20" in detail.text
    use_callback = detail.reply_markup.inline_keyboard[0][0].callback_data
    assert use_callback == "consumable:vigor:consumable.vigor.tdo.i"

    await dispatcher.feed_raw_update(
        telegram,
        callback_update(use_callback, update_id=892, actor=actor),
    )
    updated_detail = telegram.session.make_request.call_args.args[1]
    assert "🎒 Quantidade · 0" in updated_detail.text
    assert all(
        button.text != "Usar"
        for row in updated_detail.reply_markup.inline_keyboard
        for button in row
    )
    answer_texts = [
        getattr(call.args[1], "text", None)
        for call in telegram.session.make_request.call_args_list
    ]
    assert "Vigor recuperado · 80/100." in answer_texts
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        quantity = await session.scalar(
            select(ConsumableStack.quantity).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == "consumable.vigor.tdo.i",
            )
        )
        assert character.vigor == 80
        assert quantity == 0
