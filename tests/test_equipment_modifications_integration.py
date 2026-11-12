"""PostgreSQL coverage for transactional equipment modifications."""

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

import asterion.application.equipment_modifications as modifications_module
from asterion.application.equipment import EquipmentService
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.equipment_modifications import (
    EquipmentModificationRejected,
    EquipmentModificationService,
)
from asterion.domain.professions import CATALYST_I, FRAGMENT_I, IRON, RESIDUE
from asterion.infrastructure.db.models import (
    Character,
    CharacterEquipmentSlot,
    CharacterProfession,
    EquipmentItem,
    MaterialStack,
    RuneStack,
    Unlock,
)
from tests.test_equipment_integration import _add_item
from tests.test_road_integration import _seed_road


def _fixed_capacity(value: int):
    async def capacity(_session, _character_id) -> int:
        return value

    return capacity


async def _seed(database, actor: int, *, crowns: int = 5000) -> UUID:
    await _seed_road(database, actor=actor)
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 10
        character.crowns = crowns
        return character.id


async def _materials(database, character_id: UUID, amounts: dict[str, int], *, bound=False):
    async with database[1].begin() as session:
        session.add_all(
            MaterialStack(character_id=character_id, material_id=material_id,
                          quantity=quantity, bound=bound)
            for material_id, quantity in amounts.items()
        )


async def _rune(database, character_id: UUID, family: str, potency: str, *, bound=False):
    async with database[1].begin() as session:
        row = RuneStack(character_id=character_id, family=family, rarity="Rara",
                        grade=1, potency=potency, quantity=1, bound=bound)
        session.add(row)
        await session.flush()
        return row.id


async def _item(database, character_id: UUID, key: str, slot: str, *, rarity="Comum",
                payload=None, equipped=False):
    item_id = await _add_item(database, character_id, key, slot, rarity=rarity,
                              item_level=10, payload=payload)
    if equipped:
        async with database[1]() as session:
            actor = await session.scalar(
                select(Character.telegram_id).where(Character.id == character_id)
            )
        await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    return item_id


async def _state(database, character_id: UUID, item_id: UUID):
    async with database[1]() as session:
        character = await session.get(Character, character_id)
        item = await session.get(EquipmentItem, item_id)
        return character, item


@pytest.mark.asyncio
async def test_enhancement_consumes_once_and_updates_only_equipped_configuration(database):
    actor = 870101
    character_id = await _seed(database, actor)
    item_id = await _item(database, character_id, "c2:enhance:equipped", "Torso", equipped=True)
    spare_id = await _item(database, character_id, "c2:enhance:spare", "Cabeça")
    await _materials(database, character_id, {FRAGMENT_I: 20})
    service = EquipmentModificationService(database[1], "ocaso")

    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        before_snapshot = await load_equipment_configuration(session, character)
        character.max_hp = Decimal("1000")
        character.hp = Decimal("500")
    before = await service.enhancement_preview(actor, item_id)
    assert before is not None and before.available
    assert before.details["target_enhancement"] == 1
    await service.enhance(actor, item_id,
                          expected_item_version=before.item_version,
                          expected_configuration_version=before.combat_configuration_version)
    character, item = await _state(database, character_id, item_id)
    assert item.payload["enhancement"] == 1
    assert character.combat_configuration_version == before.combat_configuration_version + 1
    assert character.hp == Decimal("500") * character.max_hp // Decimal("1000")
    assert before_snapshot.items[0].enhancement == 0
    assert before_snapshot.contribution().hp < (
        await service.enhancement_preview(actor, item_id)
    ).details["current_contribution"].hp
    with pytest.raises(EquipmentModificationRejected, match="STALE"):
        await service.enhance(actor, item_id,
                              expected_item_version=before.item_version,
                              expected_configuration_version=before.combat_configuration_version)

    spare_preview = await service.enhancement_preview(actor, spare_id)
    assert spare_preview is not None and spare_preview.available
    await service.enhance(actor, spare_id,
                          expected_item_version=spare_preview.item_version,
                          expected_configuration_version=spare_preview.combat_configuration_version)
    character, spare = await _state(database, character_id, spare_id)
    assert spare.payload["enhancement"] == 1
    assert character.combat_configuration_version == before.combat_configuration_version + 1
    async with database[1]() as session:
        fragments = await session.scalar(select(MaterialStack).where(
            MaterialStack.character_id == character_id, MaterialStack.material_id == FRAGMENT_I))
        # Torso is SW2 and Head is SW1: +1 costs 2 + 1 fragments.
        assert fragments.quantity == 17


@pytest.mark.asyncio
async def test_rune_install_replace_remove_preserves_identity_and_stale_guard(database):
    actor = 870102
    character_id = await _seed(database, actor)
    item_id = await _item(database, character_id, "c2:rune:main", "Principal", equipped=True)
    brasa = await _rune(database, character_id, "Brasa", "0.35%", bound=True)
    fresta = await _rune(database, character_id, "Fresta", "0.25 p.p.")
    service = EquipmentModificationService(database[1], "ocaso")

    first = await service.rune_preview(actor, item_id, "A", brasa)
    assert first is not None and first.available and not first.details["replacement"]
    await service.install_rune(actor, item_id, "A", brasa,
                               expected_item_version=first.item_version,
                               expected_configuration_version=first.combat_configuration_version)
    character, item = await _state(database, character_id, item_id)
    assert item.payload["rune"]["family"] == "Brasa"
    assert item.payload["rune"]["bound"] is True
    assert character.combat_configuration_version == first.combat_configuration_version + 1
    with pytest.raises(EquipmentModificationRejected, match="STALE"):
        await service.install_rune(actor, item_id, "A", fresta,
                                   expected_item_version=first.item_version,
                                   expected_configuration_version=first.combat_configuration_version)

    replacement = await service.rune_preview(actor, item_id, "A", fresta)
    assert replacement is not None and replacement.available and replacement.details["replacement"]
    await service.install_rune(actor, item_id, "A", fresta,
                               expected_item_version=replacement.item_version,
                               expected_configuration_version=replacement.combat_configuration_version)
    character, item = await _state(database, character_id, item_id)
    assert item.payload["rune"]["family"] == "Fresta"
    assert item.bound is False  # A bound Rune does not permanently bind its host.
    async with database[1]() as session:
        returned = await session.scalar(select(RuneStack).where(
            RuneStack.character_id == character_id, RuneStack.family == "Brasa"))
        assert returned is not None and returned.quantity == 1 and returned.bound is True
    current = await service.runes(actor, item_id)
    assert current is not None and current.details["can_remove"]
    await service.remove_rune(actor, item_id, "A",
                              expected_item_version=current.item_version,
                              expected_configuration_version=current.combat_configuration_version)
    character, item = await _state(database, character_id, item_id)
    assert item.payload["rune"] is None
    assert character.combat_configuration_version == first.combat_configuration_version + 3


@pytest.mark.asyncio
async def test_two_handed_rune_affinities_and_unequipped_no_version_change(database):
    actor = 870103
    character_id = await _seed(database, actor)
    item_id = await _item(database, character_id, "c2:rune:2h", "2H")
    brasa = await _rune(database, character_id, "Brasa", "0.35%")
    guarda = await _rune(database, character_id, "Guarda", "0.25 p.p.")
    service = EquipmentModificationService(database[1], "ocaso")

    incompatible = await service.rune_preview(actor, item_id, "A", guarda)
    assert incompatible is not None and incompatible.reason == "RUNE_UNAVAILABLE"
    for affinity, rune_id in (("A", brasa), ("B", guarda)):
        preview = await service.rune_preview(actor, item_id, affinity, rune_id)
        assert preview is not None and preview.available
        await service.install_rune(actor, item_id, affinity, rune_id,
                                   expected_item_version=preview.item_version,
                                   expected_configuration_version=preview.combat_configuration_version)
    character, item = await _state(database, character_id, item_id)
    assert set(item.payload["runes"]) == {"A", "B"}
    assert item.payload["rune"] is None
    assert character.combat_configuration_version == 0
    await EquipmentService(database[1], "ocaso").equip_item(actor, item_id)
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_equipment_configuration(session, character)
    assert {affinity for affinity, _ in snapshot.items[0].runes} == {"A", "B"}
    assert snapshot.contribution().rune_percent[1] > 0  # ATQ
    assert snapshot.contribution().rune_points[7] > 0  # Bloqueio


@pytest.mark.asyncio
async def test_enchantment_consumes_materials_and_replaces_existing_component(database):
    actor = 870104
    character_id = await _seed(database, actor)
    item_id = await _item(database, character_id, "c2:enchant:head", "Cabeça", equipped=True)
    await _materials(database, character_id, {RESIDUE: 12, IRON: 5, CATALYST_I: 2})
    async with database[1].begin() as session:
        session.add(CharacterProfession(character_id=character_id, slot="primary",
                                        profession_id="artificer", level=10, pxp=0))
    service = EquipmentModificationService(database[1], "ocaso")
    rare_id = "recipe.tdo.artificer.enchantment.pele_de_pedra.raro"
    epic_id = "recipe.tdo.artificer.enchantment.sopro_persistente.epico"

    preview = await service.enchantment_preview(actor, item_id, rare_id)
    assert preview is not None and preview.available
    assert preview.details["crown_cost"] == 50
    await service.apply_enchantment(actor, item_id, rare_id,
                                    expected_item_version=preview.item_version,
                                    expected_configuration_version=preview.combat_configuration_version,
                                    expected_preview_token=preview.details["token"])
    _, item = await _state(database, character_id, item_id)
    assert item.payload["enchantment"]["family"] == "Pele de Pedra"
    with pytest.raises(EquipmentModificationRejected, match="STALE"):
        await service.apply_enchantment(actor, item_id, rare_id,
                                        expected_item_version=preview.item_version,
                                        expected_configuration_version=preview.combat_configuration_version,
                                        expected_preview_token=preview.details["token"])

    replacement = await service.enchantment_preview(actor, item_id, epic_id)
    assert replacement is not None and replacement.available
    assert replacement.details["current"] is not None
    await service.apply_enchantment(actor, item_id, epic_id,
                                    expected_item_version=replacement.item_version,
                                    expected_configuration_version=replacement.combat_configuration_version,
                                    expected_preview_token=replacement.details["token"])
    character, item = await _state(database, character_id, item_id)
    assert item.payload["enchantment"]["family"] == "Sopro Persistente"
    assert item.payload["enchantment"]["potency"] == "0.20%"
    assert character.crowns == 4850
    assert character.combat_configuration_version == preview.combat_configuration_version + 2


@pytest.mark.asyncio
async def test_echo_enchantment_requires_unlock_and_consumes_boss_core_once(database):
    actor = 870105
    character_id = await _seed(database, actor)
    item_id = await _item(database, character_id, "c2:enchant:echo", "Acessório")
    await _materials(database, character_id, {
        RESIDUE: 5, IRON: 2, CATALYST_I: 1,
        "material.tdo.nucleo_vigia_partido": 1,
    })
    async with database[1].begin() as session:
        session.add(CharacterProfession(character_id=character_id, slot="primary",
                                        profession_id="artificer", level=10, pxp=0))
    service = EquipmentModificationService(database[1], "ocaso")
    recipe_id = "recipe.tdo.vigia_partido.eco"
    unavailable = await service.enchantment_preview(actor, item_id, recipe_id)
    assert unavailable is not None and unavailable.reason == "RECIPE"
    async with database[1].begin() as session:
        session.add(Unlock(character_id=character_id, unlock_id=recipe_id))
    available = await service.enchantment_preview(actor, item_id, recipe_id)
    assert available is not None and available.available
    assert available.details["crown_cost"] == 100
    await service.apply_enchantment(actor, item_id, recipe_id,
                                    expected_item_version=available.item_version,
                                    expected_configuration_version=available.combat_configuration_version,
                                    expected_preview_token=available.details["token"])
    _, item = await _state(database, character_id, item_id)
    assert item.payload["enchantment"]["enchantment_id"] == recipe_id
    assert item.payload["enchantment"]["potency"] == "0.25 p.p."
    with pytest.raises(EquipmentModificationRejected, match="STALE"):
        await service.apply_enchantment(actor, item_id, recipe_id,
                                        expected_item_version=available.item_version,
                                        expected_configuration_version=available.combat_configuration_version,
                                        expected_preview_token=available.details["token"])
    async with database[1]() as session:
        core = await session.scalar(select(MaterialStack).where(
            MaterialStack.character_id == character_id,
            MaterialStack.material_id == "material.tdo.nucleo_vigia_partido"))
        assert core is None


@pytest.mark.asyncio
async def test_reroll_changes_only_one_secondary_and_costs_once(database):
    actor = 870106
    character_id = await _seed(database, actor)
    payload = {"slot": "Mãos", "core": {"ATQ": 10},
               "secondaries": [{"attribute": "AGI", "value": "3"},
                               {"attribute": "PER", "value": "0.5"}],
               "enhancement": 0, "rune": None, "enchantment": None}
    item_id = await _item(database, character_id, "c2:reroll", "Mãos", rarity="Épico",
                          payload=payload, equipped=True)
    service = EquipmentModificationService(database[1], "ocaso")
    preview = await service.reroll_preview(actor, item_id, 0)
    assert preview is not None and preview.available
    assert preview.details["crown_cost"] > 0
    before_crowns = (await _state(database, character_id, item_id))[0].crowns
    await service.reroll(actor, item_id, 0,
                         expected_item_version=preview.item_version,
                         expected_configuration_version=preview.combat_configuration_version)
    character, item = await _state(database, character_id, item_id)
    assert item.payload["reroll_count"] == 1
    assert item.payload["secondaries"][0]["attribute"] not in {"AGI", "PER"}
    assert item.payload["secondaries"][1] == payload["secondaries"][1]
    assert character.crowns == before_crowns - preview.details["crown_cost"]
    assert character.combat_configuration_version == preview.combat_configuration_version + 1
    with pytest.raises(EquipmentModificationRejected, match="STALE"):
        await service.reroll(actor, item_id, 0,
                             expected_item_version=preview.item_version,
                             expected_configuration_version=preview.combat_configuration_version)


@pytest.mark.asyncio
async def test_dismantle_protection_and_equipped_validator_flow(database):
    actor = 870107
    character_id = await _seed(database, actor)
    item_id = await _item(database, character_id, "c2:dismantle", "Torso",
                          rarity="Épico", equipped=True)
    service = EquipmentModificationService(database[1], "ocaso")
    first = await service.dismantle_preview(actor, item_id)
    assert first is not None and first.available
    assert sum(entry["quantity"] for entry in first.details["materials"]) == 11
    await service.set_favorite(actor, item_id, True,
                               expected_item_version=first.item_version,
                               expected_configuration_version=first.combat_configuration_version)
    favorite = await service.dismantle_preview(actor, item_id)
    assert favorite is not None and favorite.reason == "FAVORITE"
    await service.set_favorite(actor, item_id, False,
                               expected_item_version=favorite.item_version,
                               expected_configuration_version=favorite.combat_configuration_version)
    unlocked = await service.dismantle_preview(actor, item_id)
    await service.set_locked(actor, item_id, True,
                             expected_item_version=unlocked.item_version,
                             expected_configuration_version=unlocked.combat_configuration_version)
    locked = await service.dismantle_preview(actor, item_id)
    assert locked is not None and locked.reason == "LOCKED"
    await service.set_locked(actor, item_id, False,
                             expected_item_version=locked.item_version,
                             expected_configuration_version=locked.combat_configuration_version)
    ready = await service.dismantle_preview(actor, item_id)
    assert ready is not None and ready.available
    await service.dismantle(actor, item_id,
                            expected_item_version=ready.item_version,
                            expected_configuration_version=ready.combat_configuration_version)
    character, item = await _state(database, character_id, item_id)
    assert item is None
    assert character.combat_configuration_version == first.combat_configuration_version + 1
    async with database[1]() as session:
        equipped = await session.scalar(select(CharacterEquipmentSlot).where(
            CharacterEquipmentSlot.character_id == character_id))
        assert equipped is None
        mats = (await session.scalars(select(MaterialStack).where(
            MaterialStack.character_id == character_id))).all()
        assert sum(row.quantity for row in mats) == 11
    with pytest.raises(EquipmentModificationRejected, match="ITEM_UNAVAILABLE"):
        await service.dismantle(actor, item_id,
                                expected_item_version=ready.item_version,
                                expected_configuration_version=ready.combat_configuration_version)


@pytest.mark.asyncio
async def test_voluntary_dismantle_and_rune_extraction_block_on_inventory_capacity(
    database, monkeypatch
):
    actor = 870108
    character_id = await _seed(database, actor)
    item_id = await _item(
        database, character_id, "c2:capacity:salvage", "Torso", rarity="Raro"
    )
    rune_item_id = await _item(database, character_id, "c2:capacity:rune", "Principal")
    rune_id = await _rune(database, character_id, "Brasa", "0.35%")
    service = EquipmentModificationService(database[1], "ocaso")
    install = await service.rune_preview(actor, rune_item_id, "A", rune_id)
    await service.install_rune(actor, rune_item_id, "A", rune_id,
                               expected_item_version=install.item_version,
                               expected_configuration_version=install.combat_configuration_version)
    monkeypatch.setattr(modifications_module, "inventory_capacity", _fixed_capacity(2))
    blocked = await service.runes(actor, rune_item_id)
    assert blocked is not None and blocked.details["can_remove"] is False
    with pytest.raises(EquipmentModificationRejected, match="INVENTORY_FULL"):
        await service.remove_rune(actor, rune_item_id, "A",
                                  expected_item_version=blocked.item_version,
                                  expected_configuration_version=blocked.combat_configuration_version)
    blocked_salvage = await service.dismantle_preview(actor, item_id)
    assert blocked_salvage is not None and blocked_salvage.reason == "INVENTORY_FULL"
    with pytest.raises(EquipmentModificationRejected, match="INVENTORY_FULL"):
        await service.dismantle(actor, item_id,
                                expected_item_version=blocked_salvage.item_version,
                                expected_configuration_version=blocked_salvage.combat_configuration_version)
    _, item = await _state(database, character_id, item_id)
    assert item is not None
