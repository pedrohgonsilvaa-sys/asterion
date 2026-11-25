"""O Despertar dos Flagelos — Bind dos 54 equipamentos regionais: Vinculado ao Adquirir
(decisão do autor, 2026-11-25), pelo mecanismo global de Bind (``EquipmentItem.bound``)."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from asterion.application.flagelos import FlageloService
from asterion.application.inventory_capacity import INVENTORY_CAPACITY
from asterion.application.item_escrow import equipment_block_reason
from asterion.application.warehouse import WarehouseService
from asterion.domain import flagelo_catalog as cat
from asterion.domain import flagelos as fl
from asterion.domain.professions import RECIPE_BY_ID
from asterion.infrastructure.db.models import (
    Character,
    EquipmentItem,
    FlageloEvent,
    PendingItem,
    Unlock,
)
from tests.test_flagelos_service import SERVER, FakeSimulator, _spawn
from tests.test_road_integration import _seed_road


def test_the_54_recipes_pay_with_a_bound_only_flagelo_fragment_that_transmits_bind():
    assert len(cat.TEMPLATES) == 54
    for template in cat.TEMPLATES:
        assert template.recipe_id in RECIPE_BY_ID
        lines = {material: bind for material, _, bind in cat.recipe_cost_lines(template)}
        fragment = cat.FLAGELO_FRAGMENT_IDS[template.region]
        assert lines[fragment] is True  # o Fragmento do Flagelo transmite Bind ao resultado


def test_crafting_marks_every_flagelo_recipe_bound_independent_of_the_ingredients():
    from asterion.application.crafting import CraftingService

    for template in cat.TEMPLATES:
        recipe = RECIPE_BY_ID[template.recipe_id]
        # Mesmo com ingredientes sem Bind, o resultado do Flagelo é Vinculado.
        assert CraftingService._result_bound(recipe, False) is True
    other = next(
        r
        for r in RECIPE_BY_ID.values()
        if r.output_kind == "equipment" and r.recipe_id not in cat.TEMPLATES_BY_RECIPE
    )
    assert CraftingService._result_bound(other, False) is False  # regra global preservada
    assert CraftingService._result_bound(other, True) is True


async def _event_and_character(database, actor=781_900):
    await _seed_road(database, actor)
    async with database[1]() as session:
        character_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == actor)
        )
    service = FlageloService(database[1], SERVER, FakeSimulator())
    await _spawn(database, service)
    async with database[1]() as session:
        event = (await session.scalars(select(FlageloEvent))).first()
    return actor, character_id, event


async def _grant_equipment(database, character_id, event):
    region = fl.REGIONS[0]
    service = FlageloService(database[1], SERVER, FakeSimulator())
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        return await service._equipment(session, event, character, region, region.flagelo)


async def test_death_drop_is_bound_on_acquire_in_the_inventory(database):
    _, character_id, event = await _event_and_character(database)
    granted = await _grant_equipment(database, character_id, event)
    assert granted is not None
    async with database[1]() as session:
        item = await session.scalar(
            select(EquipmentItem).where(EquipmentItem.character_id == character_id)
        )
        assert item is not None and item.bound is True and item.payload["bound"] is True
        assert item.payload["template_id"] in fl.FLAGELO_EQUIPMENT_TEMPLATES["varkhenn"]
        # Não pode ir a Loja/Troca/Mercado: a mesma porta global recusa por Bind.
        assert equipment_block_reason(item, equipped=False) == "item_bound"


async def test_death_drop_through_pending_stays_bound_after_the_claim(database):
    actor, character_id, event = await _event_and_character(database, actor=781_910)
    async with database[1].begin() as session:
        for index in range(INVENTORY_CAPACITY):
            session.add(
                EquipmentItem(
                    character_id=character_id,
                    source_key=f"filler:{index}",
                    item_name=f"Peça {index}",
                    rarity="Comum",
                    slot="Cabeça",
                    item_level=1,
                    bound=False,
                    payload={"item_name": f"Peça {index}"},
                )
            )
    assert await _grant_equipment(database, character_id, event) is not None
    async with database[1]() as session:
        pending = await session.scalar(
            select(PendingItem).where(PendingItem.character_id == character_id)
        )
        assert pending is not None and pending.kind == "equipment"
        assert pending.payload["bound"] is True
        assert pending.source_key.startswith("flagelo:")
        pending_id = pending.id
        flagelo_items = (
            await session.scalars(
                select(EquipmentItem).where(EquipmentItem.source_key.like("flagelo:%"))
            )
        ).all()
        assert flagelo_items == []  # ainda nos Pendentes
        filler = await session.scalar(
            select(EquipmentItem).where(EquipmentItem.character_id == character_id).limit(1)
        )
        filler_id = filler.id
    async with database[1].begin() as session:
        await session.delete(await session.get(EquipmentItem, filler_id))
    warehouse = WarehouseService(database[1], "ocaso")
    preview = await warehouse.prepare_pending_claim(actor, pending_id)
    assert preview is not None
    assert (await warehouse.confirm(actor, preview.operation_id)).status == "COMMITTED"
    async with database[1]() as session:
        assert await session.get(PendingItem, pending_id) is None
        item = await session.scalar(
            select(EquipmentItem).where(EquipmentItem.source_key.like("flagelo:%"))
        )
        assert item is not None and item.character_id == character_id
        assert item.bound is True and item.payload["bound"] is True
        assert equipment_block_reason(item, equipped=False) == "item_bound"


@pytest.mark.parametrize(
    "recipe_id",
    [
        "recipe.flagelo.vde.luvas.estrangulamento",  # Raro
        "recipe.flagelo.tdo.lamina_ultima_brasa",  # Épico
        "recipe.flagelo.confins.arco.protocolo_incompativel",  # Lendário
    ],
)
async def test_crafted_flagelo_equipment_is_bound_even_with_unbound_ingredients(
    database, recipe_id
):
    from asterion.application.crafting import CraftingService
    from asterion.domain.professions import recipe_materials
    from tests.test_professions_crafting_integration import (
        _add_materials,
        _seed_active_professions,
        _set_profession_level,
    )

    template = cat.TEMPLATES_BY_RECIPE[recipe_id]
    recipe = RECIPE_BY_ID[recipe_id]
    actor = 993_300 + template.number
    character_id = await _seed_active_professions(
        database, actor, template.profession_id, "alchemist"
    )
    await _set_profession_level(database, character_id, template.profession_id, 30)
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        character.level = 60
        character.crowns = 100_000
        session.add(Unlock(character_id=character_id, unlock_id=recipe_id))
    materials = {m.material_id: m.quantity for m in recipe_materials(recipe, 60)}
    await _add_materials(database, character_id, materials)  # tudo SEM Bind
    service = CraftingService(database[1], "ocaso")
    preview = await service.preview(actor, recipe_id)
    assert preview is not None and preview.result_bound is True
    crafted = await service.commit(actor, preview.receipt_id)
    assert crafted.output_payload["equipment"]["bound"] is True
    async with database[1]() as session:
        item = await session.get(EquipmentItem, UUID(crafted.output_payload["equipment_item_id"]))
        assert item is not None and item.bound is True
        assert equipment_block_reason(item, equipped=False) == "item_bound"
