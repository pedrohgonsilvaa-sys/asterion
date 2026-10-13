import pytest
from sqlalchemy import select

from asterion.application.crafting import CraftingService
from asterion.application.professions import ProfessionService
from asterion.domain.professions import (
    VDE_FRAGMENT_II,
    VDE_HERB,
    VDE_IRON,
    VDE_RESIN,
)
from asterion.infrastructure.db.models import ConsumableStack, EquipmentItem, RuneStack
from tests.test_professions_crafting_integration import (
    _add_materials,
    _seed_character,
    _set_profession_level,
)


@pytest.mark.asyncio
async def test_vde_grade_ii_equipment_crafts_at_grade_two_item_level(database):
    actor = 840130
    character_id = await _seed_character(database, actor, level=20, crowns=5000)
    professions = ProfessionService(database[1], "ocaso")
    await professions.initial_selection(actor, "blacksmith", "alchemist")
    await _set_profession_level(database, character_id, "blacksmith", 3)
    await _add_materials(database, character_id, {VDE_IRON: 7, VDE_RESIN: 3})

    service = CraftingService(database[1], "ocaso")
    preview = await service.preview(actor, "recipe.vde.blacksmith.vale_weapon.comum")
    assert preview is not None
    assert preview.item_level == 20
    assert {item.material_id: item.required for item in preview.ingredients} == {
        VDE_IRON: 7,
        VDE_RESIN: 3,
    }

    committed = await service.commit(actor, preview.receipt_id)
    assert committed is not None
    assert committed.output_payload is not None
    async with database[1]() as session:
        item = await session.scalar(
            select(EquipmentItem).where(EquipmentItem.character_id == character_id)
        )
        assert item is not None
        assert item.item_name == "Arma do Vale"
        assert item.item_level == 20
        assert item.slot == "Principal"


@pytest.mark.asyncio
async def test_vde_grade_ii_alchemy_and_rune_use_existing_delivery_models(database):
    actor = 840131
    character_id = await _seed_character(database, actor, level=20, crowns=5000)
    professions = ProfessionService(database[1], "ocaso")
    await professions.initial_selection(actor, "alchemist", "artificer")
    await _set_profession_level(database, character_id, "alchemist", 3)
    await _set_profession_level(database, character_id, "artificer", 5)
    await _add_materials(
        database,
        character_id,
        {
            VDE_HERB: 3,
            VDE_RESIN: 5,
            VDE_IRON: 2,
            VDE_FRAGMENT_II: 2,
        },
    )

    service = CraftingService(database[1], "ocaso")
    potion = await service.preview(actor, "recipe.vde.alchemist.heal.vde.ii")
    assert potion is not None and potion.crown_cost == 40
    await service.commit(actor, potion.receipt_id)

    rune = await service.preview(actor, "recipe.vde.artificer.rune.espinho.rara")
    assert rune is not None and rune.crown_cost == 120
    committed = await service.commit(actor, rune.receipt_id)
    assert committed is not None
    assert committed.output_payload is not None
    assert committed.output_payload["rune"] == {
        "family": "Espinho",
        "rarity": "Rara",
        "grade": 2,
        "potency": "0.40%",
        "bound": False,
    }

    async with database[1]() as session:
        potion_stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.heal.vde.ii",
            )
        )
        rune_stack = await session.scalar(
            select(RuneStack).where(
                RuneStack.character_id == character_id,
                RuneStack.family == "Espinho",
                RuneStack.rarity == "Rara",
                RuneStack.grade == 2,
            )
        )
        assert potion_stack is not None and potion_stack.quantity == 1
        assert rune_stack is not None and rune_stack.quantity == 1
        assert rune_stack.potency == "0.40%"
