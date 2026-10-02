from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import asterion.application.crafting as crafting_module
from asterion.application.crafting import CraftingRejected, CraftingService
from asterion.application.inventory import InventoryService
from asterion.application.professions import (
    ProfessionMutationRejected,
    ProfessionService,
)
from asterion.domain.professions import (
    FRAGMENT_I,
    IRON,
    RESIDUE,
)
from asterion.infrastructure.db.models import (
    BlockedDelivery,
    Character,
    CharacterProfession,
    ConsumableStack,
    CraftingReceipt,
    EquipmentItem,
    GameActivity,
    MaterialStack,
    RuneStack,
    Unlock,
)
from tests.test_road_integration import _seed_road


async def _seed_character(database, actor: int, *, level: int = 10, crowns: int = 5000):
    actor, _road = await _seed_road(database, actor=actor)
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = level
        suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor))
        character.name = f"Craft{suffix}"
        character.crowns = crowns
        character.hp = Decimal("527")
        character.max_hp = Decimal("702")
        character.combat_configuration_version = 0
        character.delivery_blocked = False
        return character.id


async def _seed_active_professions(database, actor: int, primary: str, secondary: str):
    character_id = await _seed_character(database, actor)
    service = ProfessionService(database[1], "ocaso")
    result = await service.initial_selection(actor, primary, secondary)
    assert result is not None
    return character_id


async def _add_materials(database, character_id, amounts, *, bound=False):
    async with database[1].begin() as session:
        session.add_all(
            [
                MaterialStack(
                    character_id=character_id,
                    material_id=material_id,
                    quantity=quantity,
                    bound=bound,
                )
                for material_id, quantity in amounts.items()
            ]
        )


async def _set_profession_level(database, character_id, profession_id, level, pxp=0):
    async with database[1].begin() as session:
        row = await session.scalar(
            select(CharacterProfession).where(
                CharacterProfession.character_id == character_id,
                CharacterProfession.profession_id == profession_id,
            )
        )
        row.level = level
        row.pxp = pxp


@pytest.mark.asyncio
async def test_profession_selection_swap_truncation_and_replacement_reset(database):
    actor = 840101
    character_id = await _seed_character(database, actor, level=10, crowns=5000)
    service = ProfessionService(database[1], "ocaso")
    with pytest.raises(ProfessionMutationRejected):
        await service.initial_selection(actor, "blacksmith", "blacksmith")
    assert await service.view(actor) is not None
    assert not (await service.view(actor)).configured

    selected = await service.initial_selection(actor, "blacksmith", "alchemist")
    assert selected is not None
    assert selected.primary.level == selected.secondary.level == 1
    await _set_profession_level(database, character_id, "blacksmith", 20, 145)
    await _set_profession_level(database, character_id, "alchemist", 5, 21)

    preview = await service.change_preview(actor, "swap")
    assert preview is not None and preview.valid and preview.cost == 120
    assert preview.lost_level == 5
    assert preview.lost_pxp == 145
    swapped = await service.confirm_change(actor, preview.token, "swap")
    assert swapped is not None
    assert (swapped.primary.profession_id, swapped.primary.level, swapped.primary.pxp) == (
        "alchemist",
        5,
        21,
    )
    assert (swapped.secondary.profession_id, swapped.secondary.level, swapped.secondary.pxp) == (
        "blacksmith",
        15,
        0,
    )

    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(Unlock(character_id=character.id, unlock_id="recipe.tdo.vigia_partido.eco"))
    replacement_preview = await service.change_preview(
        actor, "replace", slot="primary", profession_id="jeweler"
    )
    assert replacement_preview is not None and replacement_preview.valid
    assert replacement_preview.lost_level == 4
    assert replacement_preview.lost_pxp == 21
    replaced = await service.confirm_change(
        actor,
        replacement_preview.token,
        "replace",
        slot="primary",
        profession_id="jeweler",
    )
    assert replaced is not None
    assert replaced.primary.profession_id == "jeweler"
    assert replaced.primary.level == 1 and replaced.primary.pxp == 0
    async with database[1]() as session:
        assert (
            await session.scalar(
                select(CharacterProfession).where(
                    CharacterProfession.character_id == character_id,
                    CharacterProfession.profession_id == "alchemist",
                )
            )
            is None
        )
        assert (
            await session.scalar(
                select(CharacterProfession).where(
                    CharacterProfession.character_id == character_id,
                    CharacterProfession.profession_id == "jeweler",
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == "recipe.tdo.vigia_partido.eco",
                )
            )
            is not None
        )
        character = await session.get(Character, character_id)
        assert character.crowns == 4630
        assert character.combat_configuration_version == 0


@pytest.mark.asyncio
async def test_swap_preview_blocks_insufficient_crowns(database):
    actor = 840109
    await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.crowns = 0
    preview = await ProfessionService(database[1], "ocaso").change_preview(actor, "swap")
    assert preview is not None
    assert preview.valid is False
    assert preview.reason == "insufficient_crowns"


@pytest.mark.asyncio
async def test_persisted_secondary_profession_cap_is_enforced(database):
    actor = 840110
    character_id = await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    with pytest.raises(IntegrityError):
        async with database[1].begin() as session:
            row = await session.scalar(
                select(CharacterProfession).where(
                    CharacterProfession.character_id == character_id,
                    CharacterProfession.slot == "secondary",
                )
            )
            row.level = 16


@pytest.mark.asyncio
async def test_equipment_craft_uses_previewed_stacks_and_is_idempotent(database):
    actor = 840102
    character_id = await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    await _add_materials(
        database,
        character_id,
        {IRON: 7, RESIDUE: 3},
        bound=True,
    )
    service = CraftingService(database[1], "ocaso")
    recipe_id = "recipe.tdo.blacksmith.walker_weapon.comum"
    preview = await service.preview(actor, recipe_id)
    assert preview is not None
    assert preview.item_level == 10
    assert preview.crown_cost == 120
    assert preview.result_bound is True
    assert all(item.required == item.owned for item in preview.ingredients)

    committed = await service.commit(actor, preview.receipt_id)
    repeated = await service.commit(actor, preview.receipt_id)
    assert committed is not None and repeated is not None
    assert (
        committed.output_payload["equipment_item_id"]
        == repeated.output_payload["equipment_item_id"]
    )
    item_id = UUID(committed.output_payload["equipment_item_id"])
    assert committed.output_payload["equipment"]["enhancement"] == 0
    assert committed.output_payload["equipment"]["rune"] is None
    assert committed.output_payload["equipment"]["enchantment"] is None

    async with database[1]() as session:
        character = await session.get(Character, character_id)
        equipment = await session.get(EquipmentItem, item_id)
        receipt = await session.get(CraftingReceipt, preview.receipt_id)
        mats = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character_id)
            )
        ).all()
        profession = await session.scalar(
            select(CharacterProfession).where(
                CharacterProfession.character_id == character_id,
                CharacterProfession.profession_id == "blacksmith",
            )
        )
        assert character.crowns == 4880
        assert equipment.item_name == "Arma do Caminhante"
        assert equipment.slot == "Principal" and equipment.item_level == 10
        assert equipment.bound is True
        assert not mats
        assert receipt.status == "committed"
        assert (profession.level, profession.pxp) == (1, 100)
        assert (
            await session.scalar(
                select(EquipmentItem.id).where(
                    EquipmentItem.character_id == character_id,
                    EquipmentItem.source_key.like("craft:%:equipment"),
                )
            )
            == item_id
        )


@pytest.mark.asyncio
async def test_stale_material_preview_consumes_nothing(database):
    actor = 840103
    character_id = await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    await _add_materials(database, character_id, {IRON: 7, RESIDUE: 3})
    service = CraftingService(database[1], "ocaso")
    preview = await service.preview(actor, "recipe.tdo.blacksmith.walker_weapon.comum")
    assert preview is not None
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        character.crowns -= 1
    with pytest.raises(CraftingRejected, match="stale_preview"):
        await service.commit(actor, preview.receipt_id)
    async with database[1]() as session:
        character = await session.get(Character, character_id)
        receipt = await session.get(CraftingReceipt, preview.receipt_id)
        items = (
            await session.scalars(
                select(EquipmentItem).where(EquipmentItem.character_id == character_id)
            )
        ).all()
        mats = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character_id)
            )
        ).all()
        assert character.crowns == 4999
        assert receipt.status == "preview"
        assert not items
        assert {row.material_id: row.quantity for row in mats} == {IRON: 7, RESIDUE: 3}


@pytest.mark.asyncio
async def test_alchemy_and_tdo_rune_crafts_use_existing_stack_models(database):
    actor = 840104
    character_id = await _seed_active_professions(database, actor, "alchemist", "artificer")
    await _add_materials(
        database,
        character_id,
        {
            "material.tdo.erva_cinzenta": 3,
            RESIDUE: 5,
            IRON: 2,
            FRAGMENT_I: 2,
        },
    )
    await _set_profession_level(database, character_id, "artificer", 5)
    service = CraftingService(database[1], "ocaso")

    potion = await service.preview(actor, "recipe.tdo.alchemist.heal")
    assert potion is not None and potion.crown_cost == 20
    await service.commit(actor, potion.receipt_id)

    rune = await service.preview(actor, "recipe.tdo.artificer.rune.brasa.rara")
    assert rune is not None and rune.crown_cost == 80
    assert rune.result_bound is False
    await service.commit(actor, rune.receipt_id)

    async with database[1]() as session:
        consumable = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.heal",
            )
        )
        rune_stack = await session.scalar(
            select(RuneStack).where(
                RuneStack.character_id == character_id,
                RuneStack.family == "Brasa",
                RuneStack.rarity == "Rara",
                RuneStack.grade == 1,
            )
        )
        assert consumable is not None and consumable.quantity == 1
        assert rune_stack is not None and rune_stack.quantity == 1
        assert rune_stack.potency == "0.35%"
        assert rune_stack.bound is False


@pytest.mark.asyncio
async def test_crafting_requires_inventory_space_before_preview(database, monkeypatch):
    actor = 840105
    character_id = await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    await _add_materials(database, character_id, {IRON: 7, RESIDUE: 3})
    monkeypatch.setattr(crafting_module, "INVENTORY_CAPACITY", 0)
    service = CraftingService(database[1], "ocaso")

    with pytest.raises(CraftingRejected, match="inventory_full"):
        await service.preview(actor, "recipe.tdo.blacksmith.walker_weapon.comum")

    async with database[1]() as session:
        character = await session.get(Character, character_id)
        mats = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character_id)
            )
        ).all()
        receipts = (
            await session.scalars(
                select(CraftingReceipt).where(CraftingReceipt.character_id == character_id)
            )
        ).all()
        assert character.crowns == 5000
        assert {row.material_id: row.quantity for row in mats} == {IRON: 7, RESIDUE: 3}
        assert receipts == []


@pytest.mark.asyncio
async def test_pending_and_blocked_delivery_recover_capacity_race_after_preview(
    database, monkeypatch
):
    service = CraftingService(database[1], "ocaso")

    actor = 840106
    character_id = await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    await _add_materials(database, character_id, {IRON: 7, RESIDUE: 3})
    preview = await service.preview(actor, "recipe.tdo.blacksmith.walker_weapon.comum")
    assert preview is not None and preview.delivery == "Inventário"

    monkeypatch.setattr(crafting_module, "INVENTORY_CAPACITY", 0)
    result = await service.commit(actor, preview.receipt_id)
    assert result is not None and result.delivery == "Pending"
    pending_view = await InventoryService(database[1], "ocaso").pending(actor)
    assert pending_view is not None and pending_view.pending_count == 1
    assert pending_view.entries[0].title == "Arma do Caminhante"

    actor = 840109
    character_id = await _seed_active_professions(database, actor, "blacksmith", "alchemist")
    await _add_materials(database, character_id, {IRON: 7, RESIDUE: 3})
    monkeypatch.setattr(crafting_module, "INVENTORY_CAPACITY", 60)
    preview = await service.preview(actor, "recipe.tdo.blacksmith.walker_weapon.comum")
    assert preview is not None and preview.delivery == "Inventário"

    monkeypatch.setattr(crafting_module, "INVENTORY_CAPACITY", 0)
    monkeypatch.setattr(crafting_module, "PENDING_CAPACITY", 0)
    result = await service.commit(actor, preview.receipt_id)
    assert result is not None and result.delivery == "Pending"
    async with database[1]() as session:
        held = await session.scalar(
            select(BlockedDelivery).where(BlockedDelivery.character_id == character_id)
        )
        character = await session.get(Character, character_id)
        assert held is not None and held.kind == "equipment"
        assert character.delivery_blocked is True


@pytest.mark.asyncio
async def test_known_eco_recipe_is_listed_but_unavailable_in_c1(database):
    actor = 840107
    character_id = await _seed_active_professions(database, actor, "blacksmith", "artificer")
    await _set_profession_level(database, character_id, "artificer", 10)
    async with database[1].begin() as session:
        session.add(Unlock(character_id=character_id, unlock_id="recipe.tdo.vigia_partido.eco"))
    service = CraftingService(database[1], "ocaso")
    view = await service.recipes(actor, "artificer")
    assert view is not None
    echo = next(
        row for row in view.recipes if row.recipe.unlock_id == "recipe.tdo.vigia_partido.eco"
    )
    assert echo.known is True
    assert echo.available is False
    assert echo.reason == "unavailable_in_c1"
    with pytest.raises(CraftingRejected, match="unavailable_in_c1"):
        await service.preview(actor, echo.recipe.recipe_id)


@pytest.mark.asyncio
async def test_recipe_list_hides_unknown_specials_and_foreground_blocks_mutations(database):
    actor = 840108
    character_id = await _seed_active_professions(database, actor, "jeweler", "alchemist")
    service = CraftingService(database[1], "ocaso")
    recipes = await service.recipes(actor, "jeweler")
    assert recipes is not None
    assert all(row.recipe.unlock_id is None for row in recipes.recipes)
    assert all(
        row.recipe.recipe_id != "recipe.tdo.cripta.relicario_sem_nome" for row in recipes.recipes
    )

    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        session.add(
            GameActivity(
                character_id=character.id,
                content_id="test:crafting-lock",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    blocked_swap = await ProfessionService(database[1], "ocaso").change_preview(actor, "swap")
    assert blocked_swap is not None
    assert blocked_swap.valid is False and blocked_swap.reason == "foreground"
    with pytest.raises(CraftingRejected, match="foreground"):
        await service.preview(actor, "recipe.tdo.jeweler.blackened_seal.comum")
