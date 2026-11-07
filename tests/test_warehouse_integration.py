import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.inventory_capacity import (
    inventory_slot_counts,
    inventory_slots,
    warehouse_slots,
)
from asterion.application.warehouse import WarehouseRejected, WarehouseService
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    ConsumableStack,
    EquipmentItem,
    MaterialStack,
    PendingItem,
    WarehouseEquipmentItem,
    WarehouseMaterialStack,
    WarehouseOperation,
    WorldState,
)
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
