import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import delete, select

from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.crafting import CraftingService
from asterion.application.doctrines import DoctrineService
from asterion.application.inventory import MATERIAL_LABELS, InventoryService
from asterion.application.inventory_capacity import (
    inventory_slot_counts,
    inventory_slots,
    warehouse_slots,
)
from asterion.application.warehouse import WarehouseRejected, WarehouseService
from asterion.application.world import WorldService
from asterion.bot.inventory_ui import render_inventory
from asterion.bot.warehouse_ui import render_warehouse
from asterion.bot.world_handlers import world_router
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    ConsumableStack,
    EquipmentItem,
    MaterialStack,
    PendingItem,
    RuneStack,
    WarehouseConsumableStack,
    WarehouseEquipmentItem,
    WarehouseMaterialStack,
    WarehouseOperation,
    WarehouseRuneStack,
    WorldState,
)
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road


@pytest.mark.asyncio
async def test_equipment_and_material_transfers_preserve_identity_and_properties(database):
    actor, _ = await _seed_road(database, 781001)
    sessions = database[1]
    equipment_id = uuid4()
    material_id = uuid4()
    payload = {
        "enhancement": 2,
        "favorite": True,
        "runes": [{"family": "Brasa", "grade": 1}],
    }
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                EquipmentItem(
                    id=equipment_id,
                    character_id=character.id,
                    source_key="test:warehouse:equipment",
                    item_name="Peitoral preservado",
                    rarity="Raro",
                    slot="Torso",
                    item_level=3,
                    bound=True,
                    payload=payload,
                ),
                MaterialStack(
                    id=material_id,
                    character_id=character.id,
                    material_id="material.tdo.ferro_de_fuligem",
                    quantity=17,
                    bound=True,
                ),
            ]
        )

    service = WarehouseService(sessions, "ocaso")
    for kind, source_id in (("equipment", equipment_id), ("material", material_id)):
        preview = await service.prepare_transfer(actor, "deposit", kind, source_id)
        assert preview is not None and preview.status == "preview"
        result = await service.confirm(actor, preview.operation_id)
        assert result.status == "COMMITTED"
        assert (await service.confirm(actor, preview.operation_id)).status == "ALREADY_COMMITTED"

    async with sessions() as session:
        stored_equipment = await session.get(WarehouseEquipmentItem, equipment_id)
        stored_material = await session.get(WarehouseMaterialStack, material_id)
        assert await session.get(EquipmentItem, equipment_id) is None
        assert await session.get(MaterialStack, material_id) is None
        assert stored_equipment is not None
        assert stored_equipment.payload == payload
        assert stored_equipment.source_key == "test:warehouse:equipment"
        assert stored_equipment.bound is True
        assert stored_material is not None
        assert (stored_material.quantity, stored_material.bound) == (17, True)
        assert await session.scalar(
            select(CharacterEquipmentSlot.equipment_item_id).where(
                CharacterEquipmentSlot.character_id == stored_equipment.character_id,
                CharacterEquipmentSlot.equipment_item_id == equipment_id,
            )
        ) is None

    for kind, source_id in (("equipment", equipment_id), ("material", material_id)):
        preview = await service.prepare_transfer(actor, "withdraw", kind, source_id)
        assert preview is not None
        assert (await service.confirm(actor, preview.operation_id)).status == "COMMITTED"

    async with sessions() as session:
        restored_equipment = await session.get(EquipmentItem, equipment_id)
        restored_material = await session.get(MaterialStack, material_id)
        assert restored_equipment is not None
        assert restored_equipment.payload == payload
        assert restored_equipment.source_key == "test:warehouse:equipment"
        assert restored_equipment.bound is True
        assert restored_material is not None
        assert (restored_material.quantity, restored_material.bound) == (17, True)
        assert await session.get(WarehouseEquipmentItem, equipment_id) is None
        assert await session.get(WarehouseMaterialStack, material_id) is None


@pytest.mark.asyncio
async def test_safe_location_stale_preview_and_operation_snapshot(database):
    actor, _ = await _seed_road(database, 781002)
    sessions = database[1]
    stack_id = uuid4()
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            MaterialStack(
                id=stack_id,
                character_id=character.id,
                material_id="material.tdo.couro_escoriado",
                quantity=3,
                bound=False,
            )
        )
    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_transfer(actor, "deposit", "material", stack_id)
    assert preview is not None
    async with sessions.begin() as session:
        row = await session.get(MaterialStack, stack_id)
        row.quantity = 4
    result = await service.confirm(actor, preview.operation_id)
    assert result.status == "STALE"
    async with sessions() as session:
        assert await session.get(MaterialStack, stack_id) is not None
        assert await session.get(WarehouseMaterialStack, stack_id) is None
        operation = await session.get(WarehouseOperation, preview.operation_id)
        assert operation.status == "stale"
        assert operation.snapshot["quantity"] == 3

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.get(WorldState, character.id)
        world.location = "Área sem Braseiro"
    with pytest.raises(WarehouseRejected, match="SAFE_LOCATION_REQUIRED"):
        await service.prepare_transfer(actor, "deposit", "material", stack_id)


@pytest.mark.asyncio
async def test_pending_material_recovery_merges_only_matching_bind_and_keeps_origin(database):
    actor, _ = await _seed_road(database, 781003)
    sessions = database[1]
    pending_id = uuid4()
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                MaterialStack(
                    character_id=character.id,
                    material_id="material.tdo.ferro_de_fuligem",
                    quantity=998,
                    bound=True,
                ),
                PendingItem(
                    id=pending_id,
                    character_id=character.id,
                    source_key="reward:mission:test",
                    kind="material",
                    payload={
                        "material_id": "material.tdo.ferro_de_fuligem",
                        "bound": True,
                    },
                    quantity=4,
                ),
            ]
        )

    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_pending_claim(actor, pending_id)
    assert preview is not None
    assert preview.quantity == 4
    result = await service.confirm(actor, preview.operation_id)
    assert result.status == "COMMITTED"
    assert (await service.confirm(actor, preview.operation_id)).status == "ALREADY_COMMITTED"

    async with sessions() as session:
        stacks = (
            await session.scalars(
                select(MaterialStack).where(
                    MaterialStack.character_id == preview.character_id,
                    MaterialStack.material_id == "material.tdo.ferro_de_fuligem",
                    MaterialStack.bound.is_(True),
                )
            )
        ).all()
        assert sum(row.quantity for row in stacks) == 1002
        assert all(row.quantity <= 999 for row in stacks)
        assert await session.get(PendingItem, pending_id) is None
        operation = await session.get(WarehouseOperation, preview.operation_id)
        assert operation.source_key == "reward:mission:test"
        assert operation.snapshot["payload"]["bound"] is True


@pytest.mark.asyncio
async def test_pending_claim_requires_destination_and_counts_positive_stacks(database):
    actor, _ = await _seed_road(database, 781004)
    sessions = database[1]
    pending_id = uuid4()
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            [
                ConsumableStack(
                    character_id=character.id,
                    consumable_id="consumable.heal",
                    quantity=0,
                ),
                ConsumableStack(
                    character_id=character.id,
                    consumable_id="consumable.vigor.tdo.i",
                    quantity=1,
                ),
                PendingItem(
                    id=pending_id,
                    character_id=character.id,
                    source_key="reward:pending:vigor",
                    kind="consumable",
                    payload={"consumable_id": "consumable.vigor.tdo.i"},
                    quantity=1,
                ),
            ]
        )
        counts = await inventory_slot_counts(session, character.id)
        assert counts["consumables"] == 1
        assert await inventory_slots(session, character.id) == 1
    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_pending_claim(actor, pending_id)
    assert preview is None or preview.quantity == 1
    if preview is not None:
        assert (await service.confirm(actor, preview.operation_id)).status == "COMMITTED"


@pytest.mark.asyncio
async def test_zero_quantity_unique_stack_uses_slot_only_when_recovered(database):
    sessions = database[1]
    service = WarehouseService(sessions, "ocaso")

    for actor, target in ((781006, 60), (781007, 59)):
        actor, _ = await _seed_road(database, actor)
        pending_id = uuid4()
        async with sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            occupied = await inventory_slots(session, character.id)
            assert occupied <= target
            session.add_all(
                EquipmentItem(
                    character_id=character.id,
                    source_key=f"test:warehouse:capacity:{actor}:{index}",
                    item_name=f"Teste de capacidade {index}",
                    rarity="Comum",
                    slot="Torso",
                    item_level=1,
                    bound=False,
                    payload={},
                )
                for index in range(target - occupied)
            )
            session.add_all(
                [
                    ConsumableStack(
                        character_id=character.id,
                        consumable_id="consumable.vigor.tdo.i",
                        quantity=0,
                    ),
                    PendingItem(
                        id=pending_id,
                        character_id=character.id,
                        source_key=f"reward:pending:capacity:{actor}",
                        kind="consumable",
                        payload={"consumable_id": "consumable.vigor.tdo.i"},
                        quantity=1,
                    ),
                ]
            )
            assert await inventory_slots(session, character.id) == target

        if target == 60:
            with pytest.raises(WarehouseRejected) as rejected:
                await service.prepare_pending_claim(actor, pending_id)
            assert rejected.value.code == "INVENTORY_FULL"
            async with sessions() as session:
                character_id = await session.scalar(
                    select(Character.id).where(Character.telegram_id == actor)
                )
                pending = await session.get(PendingItem, pending_id)
                empty_stack = await session.scalar(
                    select(ConsumableStack).where(
                        ConsumableStack.character_id == character_id,
                        ConsumableStack.consumable_id == "consumable.vigor.tdo.i",
                    )
                )
                assert pending is not None and pending.quantity == 1
                assert empty_stack is not None and empty_stack.quantity == 0
            continue

        preview = await service.prepare_pending_claim(actor, pending_id)
        assert preview is not None and preview.quantity == 1
        assert (await service.confirm(actor, preview.operation_id)).status == "COMMITTED"
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            stack = await session.scalar(
                select(ConsumableStack).where(
                    ConsumableStack.character_id == character.id,
                    ConsumableStack.consumable_id == "consumable.vigor.tdo.i",
                )
            )
            assert await inventory_slots(session, character.id) == 60
            assert stack is not None and stack.quantity == 1
            assert await session.get(PendingItem, pending_id) is None


@pytest.mark.asyncio
async def test_two_confirmations_of_one_transfer_are_idempotent(database):
    actor, _ = await _seed_road(database, 781005)
    sessions = database[1]
    stack_id = uuid4()
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            MaterialStack(
                id=stack_id,
                character_id=character.id,
                material_id="material.tdo.residuo_ocaso",
                quantity=1,
                bound=False,
            )
        )
    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_transfer(actor, "deposit", "material", stack_id)
    assert preview is not None
    results = await asyncio.gather(
        service.confirm(actor, preview.operation_id),
        service.confirm(actor, preview.operation_id),
    )
    assert sorted(result.status for result in results) == ["ALREADY_COMMITTED", "COMMITTED"]
    async with sessions() as session:
        assert await session.get(WarehouseMaterialStack, stack_id) is not None
        assert await session.get(MaterialStack, stack_id) is None


@pytest.mark.asyncio
async def test_warehouse_capacity_99_to_100_and_inventory_withdraw_boundaries(database):
    actor, _ = await _seed_road(database, 781008)
    sessions = database[1]
    source_ids = (uuid4(), uuid4())
    filler_ids = [uuid4() for _ in range(59)]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add_all(
            WarehouseMaterialStack(
                id=uuid4(),
                character_id=character.id,
                material_id=f"material.test.warehouse.{index}",
                quantity=1,
                bound=False,
            )
            for index in range(99)
        )
        session.add_all(
            MaterialStack(
                id=source_id,
                character_id=character.id,
                material_id=f"material.test.deposit.{index}",
                quantity=2,
                bound=bool(index),
            )
            for index, source_id in enumerate(source_ids)
        )

    service = WarehouseService(sessions, "ocaso")
    previews = [
        await service.prepare_transfer(actor, "deposit", "material", source_id)
        for source_id in source_ids
    ]
    assert all(preview is not None for preview in previews)

    async def confirm_or_code(operation_id):
        try:
            result = await service.confirm(actor, operation_id)
        except WarehouseRejected as exc:
            return exc.code
        return result.status

    results = await asyncio.gather(
        *(confirm_or_code(preview.operation_id) for preview in previews)
    )
    assert sorted(results) == ["COMMITTED", "WAREHOUSE_FULL"]

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        stored_id = await session.scalar(
            select(WarehouseMaterialStack.id).where(
                WarehouseMaterialStack.character_id == character.id,
                WarehouseMaterialStack.id.in_(source_ids),
            )
        )
        assert stored_id in source_ids
        inventory_id = source_ids[0] if stored_id == source_ids[1] else source_ids[1]
        assert await inventory_slots(session, character.id) == 1
        session.add_all(
            EquipmentItem(
                id=filler_id,
                character_id=character.id,
                source_key=f"test:warehouse:inventory-full:{filler_id}",
                item_name=f"Item de teste {index}",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={},
            )
            for index, filler_id in enumerate(filler_ids)
        )

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await inventory_slots(session, character.id) == 60
        assert await warehouse_slots(session, character.id) == 100

    with pytest.raises(WarehouseRejected) as full:
        await service.prepare_transfer(actor, "deposit", "material", inventory_id)
    assert full.value.code == "WAREHOUSE_FULL"

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "withdraw", "material", stored_id)
    assert rejected.value.code == "INVENTORY_FULL"

    async with sessions.begin() as session:
        await session.delete(await session.get(EquipmentItem, filler_ids[0]))
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await inventory_slots(session, character.id) == 59

    preview = await service.prepare_transfer(actor, "withdraw", "material", stored_id)
    assert preview is not None
    assert (await service.confirm(actor, preview.operation_id)).status == "COMMITTED"
    assert (await service.confirm(actor, preview.operation_id)).status == "ALREADY_COMMITTED"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await inventory_slots(session, character.id) == 60
        assert await warehouse_slots(session, character.id) == 99
        restored = await session.get(MaterialStack, stored_id)
        assert restored is not None and restored.quantity == 2
        assert await session.get(WarehouseMaterialStack, stored_id) is None


@pytest.mark.asyncio
async def test_database_failure_rolls_back_inventory_warehouse_and_preview(database, monkeypatch):
    actor, _ = await _seed_road(database, 781009)
    sessions = database[1]
    stack_id = uuid4()
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            MaterialStack(
                id=stack_id,
                character_id=character.id,
                material_id="material.test.rollback",
                quantity=3,
                bound=True,
            )
        )

    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_transfer(actor, "deposit", "material", stack_id)
    assert preview is not None
    original_commit = service._commit_transfer

    async def fail_after_flush(session, character_id, operation):
        await original_commit(session, character_id, operation)
        await session.flush()
        raise RuntimeError("injected integration rollback")

    monkeypatch.setattr(service, "_commit_transfer", fail_after_flush)
    with pytest.raises(RuntimeError, match="injected integration rollback"):
        await service.confirm(actor, preview.operation_id)

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        source = await session.get(MaterialStack, stack_id)
        assert source is not None
        assert (source.quantity, source.bound) == (3, True)
        assert await session.get(WarehouseMaterialStack, stack_id) is None
        operation = await session.get(WarehouseOperation, preview.operation_id)
        assert operation is not None and operation.status == "preview"
        assert await inventory_slots(session, character.id) == 1
        assert await warehouse_slots(session, character.id) == 0


@pytest.mark.asyncio
async def test_doctrine_is_incomplete_only_while_its_item_is_in_warehouse(database):
    actor, _ = await _seed_road(database, 781010)
    sessions = database[1]
    item_id = uuid4()
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character.id,
                source_key="test:warehouse:doctrine",
                item_name="Peitoral da Doutrina",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={
                    "slot": "Torso",
                    "core": {"HP": 10},
                    "secondaries": [],
                    "enhancement": 0,
                    "rune": None,
                    "enchantment": None,
                },
            )
        )
        await session.flush()
        session.add(
            CharacterEquipmentSlot(
                character_id=character.id, slot="Torso", equipment_item_id=item_id
            )
        )
    doctrines = DoctrineService(sessions, "ocaso")
    initial = await doctrines.view(actor)
    created = await doctrines.create(actor, "Guarda do Armazém", initial.configuration_version)
    assert created is not None and created.doctrine_id is not None

    async def incomplete_reason():
        view = await doctrines.view(actor)
        return next(
            item.incomplete_reason
            for item in view.doctrines
            if item.doctrine_id == created.doctrine_id
        )

    assert await incomplete_reason() is None
    async with sessions.begin() as session:
        await session.execute(
            delete(CharacterEquipmentSlot).where(
                CharacterEquipmentSlot.equipment_item_id == item_id
            )
        )

    service = WarehouseService(sessions, "ocaso")
    deposit = await service.prepare_transfer(actor, "deposit", "equipment", item_id)
    assert (await service.confirm(actor, deposit.operation_id)).status == "COMMITTED"
    assert await incomplete_reason() == "item_unavailable"

    withdraw = await service.prepare_transfer(actor, "withdraw", "equipment", item_id)
    assert (await service.confirm(actor, withdraw.operation_id)).status == "COMMITTED"
    assert await incomplete_reason() is None


@pytest.mark.asyncio
async def test_page_buttons_open_later_items_with_player_names(database):
    actor, _ = await _seed_road(database, 781011)
    sessions = database[1]
    material_id = "material.tdo.ferro_de_fuligem"
    label = MATERIAL_LABELS[material_id]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        for model in (WarehouseMaterialStack, MaterialStack):
            session.add_all(
                model(
                    id=uuid4(),
                    character_id=character.id,
                    material_id=material_id,
                    quantity=5,
                    bound=False,
                )
                for _ in range(16)
            )

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            warehouse=WarehouseService(sessions, "ocaso"),
        )
    )

    await dispatcher.feed_raw_update(bot, callback_update("warehouse:page:1", actor=actor))
    root = bot.session.make_request.call_args.args[1]
    assert "Página 2/2" in root.text
    assert f"16. {label} · 5" in root.text
    assert material_id not in root.text

    await dispatcher.feed_raw_update(
        bot, callback_update("warehouse:inventory:material:1", update_id=3, actor=actor)
    )
    sources = bot.session.make_request.call_args.args[1]
    assert "Materiais disponíveis para guardar" in sources.text
    assert "Página 2/2" in sources.text
    assert f"16. {label} · 5" in sources.text


VIGOR_ID = "consumable.vigor.tdo.i"


async def _character_id(sessions, actor):
    async with sessions() as session:
        return await session.scalar(select(Character.id).where(Character.telegram_id == actor))


async def _fill_inventory(sessions, actor, target):
    async with sessions.begin() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == actor)
        )
        occupied = await inventory_slots(session, character_id)
        session.add_all(
            MaterialStack(
                character_id=character_id,
                material_id="material.tdo.couro_escoriado",
                quantity=1,
                bound=False,
            )
            for _ in range(target - occupied)
        )


async def _move(service, actor, direction, kind, source_id):
    preview = await service.prepare_transfer(actor, direction, kind, source_id)
    return await service.confirm(actor, preview.operation_id)


def _rune(model, character_id, *, quantity=4, potency="Menor", bound=True, row_id=None):
    return model(
        id=row_id or uuid4(),
        character_id=character_id,
        family="Brasa",
        rarity="Raro",
        grade=2,
        potency=potency,
        quantity=quantity,
        bound=bound,
    )


@pytest.mark.asyncio
async def test_consumable_round_trip_keeps_quantity_and_leaves_inventory(database):
    actor, _ = await _seed_road(database, 781020)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            ConsumableStack(
                id=stack_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=7
            )
        )
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "deposit", "consumable", stack_id)).status == "COMMITTED"
    async with sessions() as session:
        assert await session.get(ConsumableStack, stack_id) is None
        stored = await session.get(WarehouseConsumableStack, stack_id)
        assert (stored.consumable_id, stored.quantity) == (VIGOR_ID, 7)
        assert await warehouse_slots(session, character_id) == 1
    root = await service.root(actor)
    assert [(entry.kind, entry.quantity) for entry in root.entries] == [("consumable", 7)]
    assert root.entries[0].title != VIGOR_ID

    assert (await _move(service, actor, "withdraw", "consumable", stack_id)).status == "COMMITTED"
    async with sessions() as session:
        assert await session.get(WarehouseConsumableStack, stack_id) is None
        restored = await session.get(ConsumableStack, stack_id)
        assert restored.quantity == 7
        assert await warehouse_slots(session, character_id) == 0


@pytest.mark.asyncio
async def test_consumable_withdraw_merges_without_a_new_slot_when_inventory_is_full(database):
    actor, _ = await _seed_road(database, 781021)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    inventory_id, stored_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                ConsumableStack(
                    id=inventory_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=3
                ),
                WarehouseConsumableStack(
                    id=stored_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=5
                ),
            ]
        )
    await _fill_inventory(sessions, actor, 60)
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "withdraw", "consumable", stored_id)).status == "COMMITTED"
    async with sessions() as session:
        assert (await session.get(ConsumableStack, inventory_id)).quantity == 8
        assert await session.get(WarehouseConsumableStack, stored_id) is None
        assert await inventory_slots(session, character_id) == 60


@pytest.mark.asyncio
async def test_consumable_withdraw_over_99_is_rejected_without_moving_anything(database):
    actor, _ = await _seed_road(database, 781022)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    inventory_id, stored_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                ConsumableStack(
                    id=inventory_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=95
                ),
                WarehouseConsumableStack(
                    id=stored_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=10
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "withdraw", "consumable", stored_id)
    assert rejected.value.code == "STACK_FULL"
    async with sessions() as session:
        assert (await session.get(ConsumableStack, inventory_id)).quantity == 95
        assert (await session.get(WarehouseConsumableStack, stored_id)).quantity == 10


@pytest.mark.asyncio
async def test_confirm_rechecks_consumable_room_after_the_preview(database):
    actor, _ = await _seed_road(database, 781023)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    inventory_id, stored_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                ConsumableStack(
                    id=inventory_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=90
                ),
                WarehouseConsumableStack(
                    id=stored_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=9
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_transfer(actor, "withdraw", "consumable", stored_id)
    async with sessions.begin() as session:
        (await session.get(ConsumableStack, inventory_id)).quantity = 91

    with pytest.raises(WarehouseRejected) as rejected:
        await service.confirm(actor, preview.operation_id)
    assert rejected.value.code == "STACK_FULL"
    async with sessions() as session:
        assert (await session.get(ConsumableStack, inventory_id)).quantity == 91
        assert (await session.get(WarehouseConsumableStack, stored_id)).quantity == 9


@pytest.mark.asyncio
async def test_empty_consumable_row_still_needs_a_free_inventory_slot(database):
    actor, _ = await _seed_road(database, 781024)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    empty_id, stored_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                ConsumableStack(
                    id=empty_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=0
                ),
                WarehouseConsumableStack(
                    id=stored_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=2
                ),
            ]
        )
    await _fill_inventory(sessions, actor, 60)
    service = WarehouseService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "withdraw", "consumable", stored_id)
    assert rejected.value.code == "INVENTORY_FULL"

    async with sessions.begin() as session:
        spare = await session.scalar(
            select(MaterialStack).where(MaterialStack.character_id == character_id).limit(1)
        )
        await session.delete(spare)
    assert (await _move(service, actor, "withdraw", "consumable", stored_id)).status == "COMMITTED"
    async with sessions() as session:
        assert (await session.get(ConsumableStack, empty_id)).quantity == 2
        assert await inventory_slots(session, character_id) == 60


@pytest.mark.asyncio
async def test_rune_round_trip_preserves_every_economic_property(database):
    actor, _ = await _seed_road(database, 781025)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(_rune(RuneStack, character_id, row_id=stack_id))
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "deposit", "rune", stack_id)).status == "COMMITTED"
    async with sessions() as session:
        assert await session.get(RuneStack, stack_id) is None
        assert await warehouse_slots(session, character_id) == 1
    root = await service.root(actor)
    assert [(entry.kind, entry.grade, entry.bound) for entry in root.entries] == [
        ("rune", 2, True)
    ]

    assert (await _move(service, actor, "withdraw", "rune", stack_id)).status == "COMMITTED"
    async with sessions() as session:
        row = await session.get(RuneStack, stack_id)
        assert (row.family, row.rarity, row.grade, row.potency, row.quantity, row.bound) == (
            "Brasa",
            "Raro",
            2,
            "Menor",
            4,
            True,
        )


@pytest.mark.asyncio
async def test_rune_withdraw_merges_only_identical_stacks(database):
    actor, _ = await _seed_road(database, 781026)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    inventory_id, same_id, other_bind_id, other_potency_id = uuid4(), uuid4(), uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                _rune(RuneStack, character_id, row_id=inventory_id, quantity=2),
                _rune(WarehouseRuneStack, character_id, row_id=same_id, quantity=3),
                _rune(
                    WarehouseRuneStack,
                    character_id,
                    row_id=other_bind_id,
                    quantity=1,
                    bound=False,
                ),
                _rune(
                    WarehouseRuneStack,
                    character_id,
                    row_id=other_potency_id,
                    quantity=1,
                    potency="Maior",
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "withdraw", "rune", same_id)).status == "COMMITTED"
    assert (await _move(service, actor, "withdraw", "rune", other_bind_id)).status == "COMMITTED"
    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "withdraw", "rune", other_potency_id)
    assert rejected.value.code == "STACK_CONFLICT"

    async with sessions() as session:
        assert (await session.get(RuneStack, inventory_id)).quantity == 5
        separate = await session.get(RuneStack, other_bind_id)
        assert (separate.quantity, separate.bound) == (1, False)
        assert (await session.get(WarehouseRuneStack, other_potency_id)).quantity == 1


@pytest.mark.asyncio
async def test_consumables_and_runes_share_the_100_warehouse_slots(database):
    actor, _ = await _seed_road(database, 781027)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    rune_id, consumable_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            WarehouseMaterialStack(
                id=uuid4(),
                character_id=character_id,
                material_id="material.tdo.couro_escoriado",
                quantity=1,
                bound=False,
            )
            for _ in range(99)
        )
        session.add_all(
            [
                _rune(RuneStack, character_id, row_id=rune_id),
                ConsumableStack(
                    id=consumable_id,
                    character_id=character_id,
                    consumable_id=VIGOR_ID,
                    quantity=1,
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "deposit", "rune", rune_id)).status == "COMMITTED"
    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "deposit", "consumable", consumable_id)
    assert rejected.value.code == "WAREHOUSE_FULL"
    async with sessions() as session:
        assert await warehouse_slots(session, character_id) == 100


@pytest.mark.asyncio
async def test_stored_consumable_cannot_be_used_from_inventory(database):
    actor, _ = await _seed_road(database, 781028)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    async with sessions.begin() as session:
        session.add(
            WarehouseConsumableStack(
                id=uuid4(), character_id=character_id, consumable_id=VIGOR_ID, quantity=5
            )
        )

    view = await InventoryService(sessions, "ocaso").category(actor, "consumables")
    assert all(entry.key != VIGOR_ID for entry in view.entries)


@pytest.mark.asyncio
async def test_telegram_buttons_store_and_return_a_rune_from_inventory(database):
    actor, _ = await _seed_road(database, 781029)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(_rune(RuneStack, character_id, row_id=stack_id))

    inventory = await InventoryService(sessions, "ocaso").category(actor, "runes")
    screen = render_inventory(inventory)
    deposit = f"warehouse:deposit:rune:{stack_id.hex}"
    assert deposit in [
        button.callback_data for row in screen.keyboard.inline_keyboard for button in row
    ]

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            warehouse=WarehouseService(sessions, "ocaso"),
        )
    )
    update_id = 10

    async def click(data):
        nonlocal update_id
        update_id += 1
        await dispatcher.feed_raw_update(
            bot, callback_update(data, update_id=update_id, actor=actor)
        )
        return bot.session.make_request.call_args.args[1]

    def button(sent, prefix):
        return next(
            item.callback_data
            for row in sent.reply_markup.inline_keyboard
            for item in row
            if item.callback_data.startswith(prefix)
        )

    choice = await click(deposit)
    assert "Disponível · 4" in choice.text
    preview = await click(button(choice, "warehouse:go:"))
    assert "Runa de Brasa" in preview.text
    root = await click(button(preview, "warehouse:confirm:"))
    assert "Runa de Brasa · 4" in root.text and "Grau 2" in root.text

    choice = await click(button(root, "warehouse:withdraw:rune:"))
    preview = await click(button(choice, "warehouse:go:"))
    await click(button(preview, "warehouse:confirm:"))
    async with sessions() as session:
        assert (await session.get(RuneStack, stack_id)).quantity == 4
        assert await session.get(WarehouseRuneStack, stack_id) is None


@pytest.mark.asyncio
async def test_protected_equipment_can_be_stored_and_stays_protected(database):
    actor, _ = await _seed_road(database, 781030)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    item_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key="test:warehouse:protected",
                item_name="Lâmina Protegida",
                rarity="Raro",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={"locked": True, "favorite": True},
            )
        )
    service = WarehouseService(sessions, "ocaso")

    sources = await service.inventory_sources(actor, "equipment")
    entry = next(item for item in sources.entries if item.id == str(item_id))
    assert entry.eligible and entry.reason is None

    assert (await _move(service, actor, "deposit", "equipment", item_id)).status == "COMMITTED"
    async with sessions() as session:
        stored = await session.get(WarehouseEquipmentItem, item_id)
        assert stored.payload == {"locked": True, "favorite": True}
    root = await service.root(actor)
    assert "🔒 Protegido" in render_warehouse(root).text

    assert (await _move(service, actor, "withdraw", "equipment", item_id)).status == "COMMITTED"
    async with sessions() as session:
        restored = await session.get(EquipmentItem, item_id)
        assert restored.payload == {"locked": True, "favorite": True}


@pytest.mark.asyncio
async def test_equipped_protected_equipment_still_cannot_be_stored(database):
    actor, _ = await _seed_road(database, 781031)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    item_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key="test:warehouse:protected:equipped",
                item_name="Peitoral em uso",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={
                    "slot": "Torso",
                    "core": {"HP": 10},
                    "secondaries": [],
                    "enhancement": 0,
                    "rune": None,
                    "enchantment": None,
                    "locked": True,
                },
            )
        )
        await session.flush()
        session.add(
            CharacterEquipmentSlot(
                character_id=character_id, slot="Torso", equipment_item_id=item_id
            )
        )
    service = WarehouseService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "deposit", "equipment", item_id)
    assert rejected.value.code == "EQUIPPED"


COURO = "material.tdo.couro_escoriado"


def _material(model, character_id, *, quantity, row_id=None, bound=False, material_id=COURO):
    return model(
        id=row_id or uuid4(),
        character_id=character_id,
        material_id=material_id,
        quantity=quantity,
        bound=bound,
    )


async def _partial(service, actor, direction, kind, source_id, quantity):
    preview = await service.prepare_transfer(actor, direction, kind, source_id, quantity)
    assert preview.quantity == quantity
    return await service.confirm(actor, preview.operation_id)


async def _total(sessions, model, character_id):
    async with sessions() as session:
        rows = (
            await session.scalars(select(model).where(model.character_id == character_id))
        ).all()
        return sorted(row.quantity for row in rows)


@pytest.mark.asyncio
async def test_partial_deposit_and_withdraw_split_a_stack_exactly(database):
    actor, _ = await _seed_road(database, 781040)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(_material(MaterialStack, character_id, quantity=10, row_id=stack_id))
    service = WarehouseService(sessions, "ocaso")

    assert (
        await _partial(service, actor, "deposit", "material", stack_id, 4)
    ).status == "COMMITTED"
    assert await _total(sessions, MaterialStack, character_id) == [6]
    assert await _total(sessions, WarehouseMaterialStack, character_id) == [4]

    async with sessions() as session:
        stored_id = await session.scalar(
            select(WarehouseMaterialStack.id).where(
                WarehouseMaterialStack.character_id == character_id
            )
        )
    assert stored_id != stack_id

    assert (
        await _partial(service, actor, "withdraw", "material", stored_id, 3)
    ).status == "COMMITTED"
    assert await _total(sessions, MaterialStack, character_id) == [9]
    assert await _total(sessions, WarehouseMaterialStack, character_id) == [1]


@pytest.mark.asyncio
async def test_deposit_merges_identical_stacks_and_overflows_into_a_new_one(database):
    actor, _ = await _seed_road(database, 781041)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    source_id, nearly_full_id, bound_id = uuid4(), uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                _material(MaterialStack, character_id, quantity=5, row_id=source_id),
                _material(
                    WarehouseMaterialStack, character_id, quantity=998, row_id=nearly_full_id
                ),
                _material(
                    WarehouseMaterialStack, character_id, quantity=1, row_id=bound_id, bound=True
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "deposit", "material", source_id)).status == "COMMITTED"
    async with sessions() as session:
        assert (await session.get(WarehouseMaterialStack, nearly_full_id)).quantity == 999
        assert (await session.get(WarehouseMaterialStack, bound_id)).quantity == 1
        assert await session.get(MaterialStack, source_id) is None
    assert await _total(sessions, WarehouseMaterialStack, character_id) == [1, 4, 999]


@pytest.mark.asyncio
async def test_full_warehouse_still_accepts_what_fits_in_an_existing_stack(database):
    actor, _ = await _seed_road(database, 781042)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    source_id, other_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            _material(
                WarehouseMaterialStack,
                character_id,
                quantity=1,
                material_id=f"material.test.full.{index}",
            )
            for index in range(99)
        )
        session.add_all(
            [
                _material(WarehouseMaterialStack, character_id, quantity=990),
                _material(MaterialStack, character_id, quantity=20, row_id=source_id),
                _material(
                    MaterialStack,
                    character_id,
                    quantity=1,
                    row_id=other_id,
                    material_id="material.test.nova",
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "deposit", "material", source_id)
    assert rejected.value.code == "WAREHOUSE_FULL"
    with pytest.raises(WarehouseRejected) as different:
        await service.prepare_transfer(actor, "deposit", "material", other_id)
    assert different.value.code == "WAREHOUSE_FULL"

    assert (
        await _partial(service, actor, "deposit", "material", source_id, 9)
    ).status == "COMMITTED"
    async with sessions() as session:
        assert (await session.get(MaterialStack, source_id)).quantity == 11
        assert await warehouse_slots(session, character_id) == 100


@pytest.mark.asyncio
async def test_material_withdraw_tops_up_inventory_without_a_new_slot(database):
    actor, _ = await _seed_road(database, 781043)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    inventory_id, stored_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                _material(MaterialStack, character_id, quantity=3, row_id=inventory_id),
                _material(WarehouseMaterialStack, character_id, quantity=8, row_id=stored_id),
            ]
        )
    await _fill_inventory(sessions, actor, 60)
    before = sum(await _total(sessions, MaterialStack, character_id))
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "withdraw", "material", stored_id)).status == "COMMITTED"
    async with sessions() as session:
        assert await inventory_slots(session, character_id) == 60
        assert await session.get(WarehouseMaterialStack, stored_id) is None
    assert sum(await _total(sessions, MaterialStack, character_id)) == before + 8


@pytest.mark.asyncio
async def test_partial_withdraw_unlocks_a_consumable_stack_near_the_limit(database):
    actor, _ = await _seed_road(database, 781044)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    inventory_id, stored_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                ConsumableStack(
                    id=inventory_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=95
                ),
                WarehouseConsumableStack(
                    id=stored_id, character_id=character_id, consumable_id=VIGOR_ID, quantity=10
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "withdraw", "consumable", stored_id, 5)
    assert rejected.value.code == "STACK_FULL"

    assert (
        await _partial(service, actor, "withdraw", "consumable", stored_id, 4)
    ).status == "COMMITTED"
    async with sessions() as session:
        assert (await session.get(ConsumableStack, inventory_id)).quantity == 99
        assert (await session.get(WarehouseConsumableStack, stored_id)).quantity == 6


@pytest.mark.asyncio
async def test_rune_deposit_keeps_different_potency_in_a_separate_stack(database):
    actor, _ = await _seed_road(database, 781045)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    source_id, same_id, other_id = uuid4(), uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                _rune(RuneStack, character_id, row_id=source_id, quantity=6),
                _rune(WarehouseRuneStack, character_id, row_id=same_id, quantity=2),
                _rune(
                    WarehouseRuneStack,
                    character_id,
                    row_id=other_id,
                    quantity=1,
                    potency="Maior",
                ),
            ]
        )
    service = WarehouseService(sessions, "ocaso")

    assert (await _partial(service, actor, "deposit", "rune", source_id, 5)).status == "COMMITTED"
    async with sessions() as session:
        assert (await session.get(RuneStack, source_id)).quantity == 1
        assert (await session.get(WarehouseRuneStack, same_id)).quantity == 7
        assert (await session.get(WarehouseRuneStack, other_id)).quantity == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("quantity", [0, -1, 11])
async def test_invalid_stack_quantity_is_rejected(database, quantity):
    actor, _ = await _seed_road(database, 781046)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(_material(MaterialStack, character_id, quantity=10, row_id=stack_id))
    service = WarehouseService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "deposit", "material", stack_id, quantity)
    assert rejected.value.code == "INVALID_QUANTITY"
    assert await _total(sessions, MaterialStack, character_id) == [10]


@pytest.mark.asyncio
async def test_equipment_cannot_be_split(database):
    actor, _ = await _seed_road(database, 781047)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    item_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key="test:warehouse:split",
                item_name="Peitoral único",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={},
            )
        )
    service = WarehouseService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.prepare_transfer(actor, "deposit", "equipment", item_id, 2)
    assert rejected.value.code == "INVALID_QUANTITY"


@pytest.mark.asyncio
async def test_partial_preview_goes_stale_when_the_source_stack_changes(database):
    actor, _ = await _seed_road(database, 781048)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(_material(MaterialStack, character_id, quantity=10, row_id=stack_id))
    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_transfer(actor, "deposit", "material", stack_id, 4)
    async with sessions.begin() as session:
        (await session.get(MaterialStack, stack_id)).quantity = 9

    assert (await service.confirm(actor, preview.operation_id)).status == "STALE"
    assert await _total(sessions, MaterialStack, character_id) == [9]
    assert await _total(sessions, WarehouseMaterialStack, character_id) == []


@pytest.mark.asyncio
async def test_repeated_partial_moves_conserve_the_exact_total(database):
    actor, _ = await _seed_road(database, 781049)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(_material(MaterialStack, character_id, quantity=50, row_id=stack_id))
    service = WarehouseService(sessions, "ocaso")

    for amount in (7, 11, 1):
        await _partial(service, actor, "deposit", "material", stack_id, amount)
    assert await _total(sessions, WarehouseMaterialStack, character_id) == [19]
    assert await _total(sessions, MaterialStack, character_id) == [31]

    async with sessions() as session:
        stored_id = await session.scalar(
            select(WarehouseMaterialStack.id).where(
                WarehouseMaterialStack.character_id == character_id
            )
        )
    for amount in (5, 14):
        await _partial(service, actor, "withdraw", "material", stored_id, amount)
    assert await _total(sessions, WarehouseMaterialStack, character_id) == []
    assert await _total(sessions, MaterialStack, character_id) == [50]


@pytest.mark.asyncio
async def test_telegram_quantity_buttons_move_the_chosen_amount(database):
    actor, _ = await _seed_road(database, 781050)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id, single_id = uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                _material(MaterialStack, character_id, quantity=120, row_id=stack_id),
                _material(
                    MaterialStack,
                    character_id,
                    quantity=1,
                    row_id=single_id,
                    material_id="material.test.unico",
                ),
            ]
        )

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            warehouse=WarehouseService(sessions, "ocaso"),
        )
    )
    update_id = 20

    async def click(data):
        nonlocal update_id
        update_id += 1
        await dispatcher.feed_raw_update(
            bot, callback_update(data, update_id=update_id, actor=actor)
        )
        return bot.session.make_request.call_args.args[1]

    def button(sent, text):
        return next(
            item.callback_data
            for row in sent.reply_markup.inline_keyboard
            for item in row
            if item.text == text
        )

    choice = await click(f"warehouse:deposit:material:{stack_id.hex}")
    assert "Disponível · 120" in choice.text and "Quantidade · 120" in choice.text
    choice = await click(button(choice, "−100"))
    assert "Quantidade · 20" in choice.text
    choice = await click(button(choice, "+1"))
    assert "Quantidade · 21" in choice.text
    preview = await click(button(choice, "Continuar"))
    assert "Quantidade · 21" in preview.text
    await click(button(preview, "Confirmar"))
    assert await _total(sessions, WarehouseMaterialStack, character_id) == [21]

    single = await click(f"warehouse:deposit:material:{single_id.hex}")
    assert "Confirmar transferência" in single.text
    assert "Escolher quantidade" not in single.text

    rejected = await click("warehouse:go:d:m:nao-e-uuid:1")
    assert rejected is not None
    assert await _total(sessions, WarehouseMaterialStack, character_id) == [21]


@pytest.mark.asyncio
async def test_crafting_sees_a_delivered_item_that_moved_to_the_warehouse(database):
    actor, _ = await _seed_road(database, 781060)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    item_id = uuid4()
    source_key = "craft:warehouse-delivery:equipment"
    async with sessions.begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key=source_key,
                item_name="Lâmina forjada",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={},
            )
        )
    crafting = CraftingService(sessions, "ocaso")
    service = WarehouseService(sessions, "ocaso")

    assert (await _move(service, actor, "deposit", "equipment", item_id)).status == "COMMITTED"
    async with sessions() as session:
        assert await session.get(EquipmentItem, item_id) is None
        assert await crafting._delivery_exists(session, character_id, source_key)


@pytest.mark.asyncio
async def test_inventory_page_button_opens_the_next_page_in_telegram(database):
    actor, _ = await _seed_road(database, 781061)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    async with sessions.begin() as session:
        session.add_all(
            _material(MaterialStack, character_id, quantity=5) for _ in range(16)
        )

    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(sessions, "ocaso"),
            {},
            inventory=InventoryService(sessions, "ocaso"),
        )
    )

    await dispatcher.feed_raw_update(
        bot, callback_update("inventory:category:materials", actor=actor)
    )
    first = bot.session.make_request.call_args.args[1]
    assert "Página 1/2" in first.text

    await dispatcher.feed_raw_update(
        bot, callback_update("inventory:category:materials:1", update_id=3, actor=actor)
    )
    second = bot.session.make_request.call_args.args[1]
    assert "Página 2/2" in second.text


@pytest.mark.asyncio
async def test_cancel_still_works_while_an_activity_locks_transfers(database, monkeypatch):
    actor, _ = await _seed_road(database, 781090)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(_material(MaterialStack, character_id, quantity=5, row_id=stack_id))
    service = WarehouseService(sessions, "ocaso")
    preview = await service.prepare_transfer(actor, "deposit", "material", stack_id)

    monkeypatch.setattr(
        "asterion.application.warehouse.lock_for_combat_configuration_mutation",
        AsyncMock(side_effect=CombatConfigurationLocked(None)),
    )

    with pytest.raises(WarehouseRejected) as rejected:
        await service.confirm(actor, preview.operation_id)
    assert rejected.value.code == "FOREGROUND_LOCKED"
    assert await service.cancel(actor, preview.operation_id) == "CANCELLED"
    async with sessions() as session:
        operation = await session.get(WarehouseOperation, preview.operation_id)
        stack = await session.get(MaterialStack, stack_id)
    assert operation.status == "cancelled"
    assert stack.quantity == 5
