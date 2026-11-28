from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.item_discard import DiscardService
from asterion.application.warehouse import WarehouseRejected
from asterion.bot.inventory_ui import render_discard_confirm
from asterion.infrastructure.db.models import (
    Character,
    EquipmentItem,
    MaterialStack,
    WarehouseMaterialStack,
)
from tests.test_road_integration import _seed_road


async def _character_id(sessions, actor):
    async with sessions() as session:
        return await session.scalar(select(Character.id).where(Character.telegram_id == actor))


@pytest.mark.asyncio
async def test_discarding_a_material_stack_removes_every_unit_and_never_stores_it(database):
    actor, _ = await _seed_road(database, 790101)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            MaterialStack(
                id=stack_id,
                character_id=character_id,
                material_id="material.tdo.couro_escoriado",
                quantity=3,
                bound=False,
            )
        )
    service = DiscardService(sessions, "ocaso")

    view = await service.preview(actor, "material", stack_id)
    assert view.quantity == 3
    assert view.key == "material.tdo.couro_escoriado"

    result = await service.confirm(actor, "material", stack_id, 3)
    assert result.status == "DISCARDED"
    assert result.quantity == 3

    async with sessions() as session:
        assert await session.get(MaterialStack, stack_id) is None
        stored = await session.scalar(
            select(WarehouseMaterialStack).where(
                WarehouseMaterialStack.character_id == character_id
            )
        )
        assert stored is None


@pytest.mark.asyncio
async def test_discard_rejects_a_stale_quantity_without_deleting(database):
    actor, _ = await _seed_road(database, 790102)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    stack_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            MaterialStack(
                id=stack_id,
                character_id=character_id,
                material_id="material.tdo.couro_escoriado",
                quantity=2,
                bound=True,
            )
        )
    service = DiscardService(sessions, "ocaso")

    with pytest.raises(WarehouseRejected) as rejected:
        await service.confirm(actor, "material", stack_id, 5)
    assert rejected.value.code == "STALE_PREVIEW"

    async with sessions() as session:
        assert await session.get(MaterialStack, stack_id) is not None


@pytest.mark.asyncio
async def test_discard_refuses_equipped_equipment_and_removes_unequipped(database):
    actor, _ = await _seed_road(database, 790103)
    sessions = database[1]
    character_id = await _character_id(sessions, actor)
    item_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key="test:discard:equipment",
                item_name="Peitoral de teste",
                rarity="Comum",
                slot="Torso",
                item_level=1,
                bound=False,
                payload={"enhancement": 0},
            )
        )
    service = DiscardService(sessions, "ocaso")

    view = await service.preview(actor, "equipment", item_id)
    assert view.quantity == 1
    assert view.title == "Peitoral de teste"

    result = await service.confirm(actor, "equipment", item_id, 1)
    assert result.status == "DISCARDED"
    async with sessions() as session:
        assert await session.get(EquipmentItem, item_id) is None


def test_discard_confirmation_is_standard_and_never_offers_guardar():
    from asterion.application.item_discard import DiscardView

    view = DiscardView(
        kind="material",
        item_id=uuid4(),
        title="Couro Escoriado",
        quantity=3,
        inventory_used=4,
        inventory_capacity=60,
        warehouse_used=0,
        warehouse_capacity=100,
        key="material.tdo.couro_escoriado",
    )
    screen = render_discard_confirm(view)
    assert "<b>Item</b> · <code>Couro Escoriado</code>" in screen.text
    assert "<code>3</code>" in screen.text
    assert "<b>Inventário</b> · <code>4/60</code>" in screen.text
    assert "<b>Armazém</b> · <code>0/100</code>" in screen.text
    labels = [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert "✅ Confirmar" in labels and "❌ Cancelar" in labels and "↩️ Retornar" in labels
    assert not any("Guardar" in label for label in labels)


def test_discard_button_targets_the_stack_and_never_the_warehouse_flow():
    from asterion.bot.inventory_ui import discard_button

    item_hex = uuid4().hex
    button = discard_button("material", item_hex)
    assert button.callback_data == f"discard:ask:material:{item_hex}"
    assert "Descartar" in button.text
