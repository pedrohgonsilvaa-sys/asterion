"""Proficiência de Armadura (spec Classes de Armadura v1.0.0) against PostgreSQL."""

import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.armor_proficiency import (
    ArmorTrainerService,
    ArmorTrainingRejected,
    owned_armor_classes,
)
from asterion.application.equipment import (
    EquipmentMutationCode,
    EquipmentMutationRejected,
    EquipmentService,
)
from asterion.domain.regional_equipment import REGIONAL_ARMOR_TEMPLATES
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterArmorProficiency,
    CharacterEquipmentSlot,
    EquipmentItem,
    WorldState,
)

REFUGE = "Refúgio do Ocaso"


async def _seed(database, actor, *, level=60, crowns=0, location=REFUGE, owned=()):
    character_id = uuid4()
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor))
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"A{suffix}",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.7.0-baseline-1.0",
                level=level,
                xp=0,
                hp=Decimal("900"),
                max_hp=Decimal("900"),
                vigor=100,
                max_vigor=100,
                crowns=crowns,
            )
        )
        await session.flush()
        session.add(
            WorldState(character_id=character_id, region="Terras do Ocaso", location=location)
        )
        for armor_class in owned:
            session.add(
                CharacterArmorProficiency(
                    character_id=character_id, armor_class=armor_class, cost_crowns=0
                )
            )
    return character_id


async def _armor(database, character_id, armor_class, slot="Cabeça", *, level=1, legacy=None):
    template = next(
        t for t in REGIONAL_ARMOR_TEMPLATES
        if t.region_key == "tdo" and t.slot == slot and t.armor_class == armor_class
    )
    item_id = uuid4()
    if legacy is None:
        payload = materialize_equipment(
            f"a:{item_id}", "Comum", level, region_key="tdo", forced_slot=slot
        )
        payload["template_id"] = template.template_id
        payload["item_name"] = template.display_name
    else:
        payload = materialize_equipment(f"a:{item_id}", "Comum", level, forced_slot=slot)
        payload.pop("template_id", None)
        payload["item_name"] = legacy
    payload["item_instance_id"] = str(item_id)
    async with database[1].begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key=f"test:armor:{item_id}",
                item_name=payload["item_name"],
                rarity="Comum",
                slot=slot,
                item_level=level,
                bound=False,
                payload=payload,
            )
        )
    return item_id


async def _crowns(database, character_id):
    async with database[1]() as session:
        return await session.scalar(select(Character.crowns).where(Character.id == character_id))


async def _owned(database, character_id):
    async with database[1]() as session:
        return await owned_armor_classes(session, character_id)


@pytest.mark.parametrize(
    ("armor_class", "owned", "code"),
    [
        ("veste", (), None),
        ("leve", (), EquipmentMutationCode.ARMOR_PROFICIENCY_LEVE),
        ("media", (), EquipmentMutationCode.ARMOR_PROFICIENCY_MEDIA),
        ("pesada", (), EquipmentMutationCode.ARMOR_PROFICIENCY_PESADA),
        ("leve", ("leve",), None),
        ("media", ("media",), None),
        ("pesada", ("pesada",), None),
        ("pesada", ("leve", "media"), EquipmentMutationCode.ARMOR_PROFICIENCY_PESADA),
    ],
)
async def test_equip_requires_matching_armor_proficiency(database, armor_class, owned, code):
    actor = 9400 + len(owned) * 10 + ["veste", "leve", "media", "pesada"].index(armor_class)
    character_id = await _seed(database, actor, owned=owned)
    item_id = await _armor(database, character_id, armor_class)
    service = EquipmentService(database[1], "ocaso")
    if code is None:
        assert (await service.equip_item(actor, item_id)).changed
        return
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await service.equip_item(actor, item_id)
    assert rejected.value.code == code
    async with database[1]() as session:
        count = await session.scalar(
            select(func.count()).select_from(CharacterEquipmentSlot).where(
                CharacterEquipmentSlot.character_id == character_id
            )
        )
        assert count == 0
        assert (await session.get(Character, character_id)).combat_configuration_version == 0


async def test_item_level_is_checked_before_armor_proficiency(database):
    character_id = await _seed(database, 9450, level=1)
    item_id = await _armor(database, character_id, "pesada", level=5)
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await EquipmentService(database[1], "ocaso").equip_item(9450, item_id)
    assert rejected.value.code == EquipmentMutationCode.ITEM_LEVEL_REQUIRED


async def test_legacy_pieces_keep_their_class_and_equipped_piece_stays(database):
    character_id = await _seed(database, 9451)
    hood = await _armor(database, character_id, "veste", legacy="Capuz das Cinzas")
    elmo = await _armor(database, character_id, "leve", legacy="Elmo de Fuligem")
    service = EquipmentService(database[1], "ocaso")
    assert (await service.equip_item(9451, hood)).changed
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await service.equip_item(9451, elmo, expected_configuration_version=1)
    assert rejected.value.code == EquipmentMutationCode.ARMOR_PROFICIENCY_LEVE


async def test_trainer_charges_once_and_rejects_without_spending(database):
    trainer = ArmorTrainerService(database[1], "ocaso")
    low = await _seed(database, 9460, level=9, crowns=50_000)
    outcome = await trainer.learn(9460, "leve")
    assert outcome.reason == ArmorTrainingRejected.LEVEL_REQUIRED
    poor = await _seed(database, 9461, level=10, crowns=999)
    outcome = await trainer.learn(9461, "leve")
    assert outcome.reason == ArmorTrainingRejected.NOT_ENOUGH_CROWNS
    away = await _seed(database, 9462, crowns=5_000, location="Estrada")
    outcome = await trainer.learn(9462, "leve")
    assert outcome.reason == ArmorTrainingRejected.LOCATION_REQUIRED
    assert (await trainer.learn(9462, "ferro")).reason == ArmorTrainingRejected.UNKNOWN_CLASS
    for character_id, crowns in ((low, 50_000), (poor, 999), (away, 5_000)):
        assert await _owned(database, character_id) == {"veste"}
        assert await _crowns(database, character_id) == crowns


async def test_trainer_prices_levels_and_veste_is_free(database):
    trainer = ArmorTrainerService(database[1], "ocaso")
    for actor, armor_class, min_level, cost in (
        (9470, "leve", 10, 1_000),
        (9471, "media", 20, 4_000),
        (9472, "pesada", 30, 10_000),
    ):
        too_low = await _seed(database, actor, level=min_level - 1, crowns=cost)
        assert (await trainer.learn(actor, armor_class)).reason == (
            ArmorTrainingRejected.LEVEL_REQUIRED
        )
        assert await _crowns(database, too_low) == cost
        ok = await _seed(database, actor + 10, level=min_level, crowns=cost + 7)
        assert (await trainer.learn(actor + 10, armor_class)).learned
        assert await _crowns(database, ok) == 7
        assert await _owned(database, ok) == {"veste", armor_class}
    free = await _seed(database, 9490, crowns=3)
    outcome = await trainer.learn(9490, "veste")
    assert outcome.already_owned and not outcome.learned
    assert await _crowns(database, free) == 3


async def test_duplicate_and_concurrent_purchases_charge_once(database):
    character_id = await _seed(database, 9491, crowns=5_000)
    trainers = [ArmorTrainerService(database[1], "ocaso") for _ in range(6)]
    outcomes = await asyncio.gather(*(t.learn(9491, "media") for t in trainers))
    assert sum(o.learned for o in outcomes) == 1
    assert sum(o.already_owned for o in outcomes) == 5
    assert await _crowns(database, character_id) == 1_000
    assert (await trainers[0].learn(9491, "media")).already_owned
    assert await _crowns(database, character_id) == 1_000


async def test_armor_proficiency_is_independent_and_weapons_are_unaffected(database):
    character_id = await _seed(database, 9492, crowns=20_000, owned=("pesada",))
    assert await _owned(database, character_id) == {"veste", "pesada"}
    trainer = ArmorTrainerService(database[1], "ocaso")
    assert (await trainer.learn(9492, "leve")).learned
    assert await _owned(database, character_id) == {"veste", "leve", "pesada"}
    assert await _crowns(database, character_id) == 19_000
