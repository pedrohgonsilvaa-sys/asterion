"""Proficiências de Armas v1.0.0 against PostgreSQL: seed, Treinador, Equipment Validator."""

import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select

from alembic import command
from asterion.application.creation import CreationService
from asterion.application.equipment import (
    EquipmentMutationCode,
    EquipmentMutationRejected,
    EquipmentService,
)
from asterion.application.weapon_proficiency import (
    TrainingRejected,
    WeaponTrainerService,
    owned_families,
)
from asterion.domain.creation import CLASSES
from asterion.domain.road import materialize_equipment
from asterion.domain.weapon_proficiency import (
    INITIAL_PROFICIENCY,
    STARTING_WEAPON_TYPE_IDS,
    ProficiencyFamily,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterEquipmentSlot,
    CharacterWeaponProficiency,
    EquipmentItem,
    WorldState,
)

F = ProficiencyFamily
REFUGE = "Refúgio do Ocaso"


async def _seed(
    database,
    actor: int,
    character_class: str,
    *,
    families: tuple[ProficiencyFamily, ...] = (),
    level: int = 60,
    crowns: int = 0,
    location: str = REFUGE,
):
    sessions = database[1]
    character_id = uuid4()
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor))
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"P{suffix}",
                race="remanescente",
                character_class=character_class,
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
        for ordinal, family in enumerate(families, start=1):
            session.add(
                CharacterWeaponProficiency(
                    character_id=character_id,
                    family=family.value,
                    ordinal=ordinal,
                    source="initial" if ordinal == 1 else "trainer",
                    cost_crowns=0,
                )
            )
    return character_id


async def _weapon(database, character_id, weapon_type_id: str | None, *, slot=None, level=1):
    item_id = uuid4()
    if weapon_type_id is None:
        payload = materialize_equipment(f"t:{item_id}", "Comum", level, forced_slot=slot)
        payload.pop("weapon_type_id", None)
        payload["item_name"] = "Arma Antiga"
    else:
        payload = materialize_equipment(
            f"t:{item_id}", "Comum", level, weapon_type_id=weapon_type_id
        )
    payload["item_instance_id"] = str(item_id)
    async with database[1].begin() as session:
        session.add(
            EquipmentItem(
                id=item_id,
                character_id=character_id,
                source_key=f"test:proficiency:{item_id}",
                item_name=payload["item_name"],
                rarity="Comum",
                slot=payload["slot"],
                item_level=level,
                bound=False,
                payload=payload,
            )
        )
    return item_id


async def _owned(database, character_id):
    async with database[1]() as session:
        return await owned_families(session, character_id)


async def _crowns(database, character_id):
    async with database[1]() as session:
        return await session.scalar(select(Character.crowns).where(Character.id == character_id))


# --- Seed inicial -------------------------------------------------------------


async def _create(service: CreationService, actor: int, class_index: int):
    state = await service.start(actor)
    state = await service.name(actor, f"Heroi{chr(ord('a') + class_index)}", 1)
    for action in ("g0", "r0", "choose", f"c{class_index}", "choose", "confirm"):
        state = await service.callback(actor, state.id, state.version, action)
    return state


async def test_every_class_starts_with_one_proficiency_and_only_its_weapon(database):
    service = CreationService(database[1], "ocaso")
    for index, character_class in enumerate(CLASSES):
        state = await _create(service, 9100 + index, index)
        async with database[1]() as session:
            character = await session.get(Character, state.id)
            assert character.character_class == character_class
            rows = (
                await session.scalars(
                    select(CharacterWeaponProficiency).where(
                        CharacterWeaponProficiency.character_id == state.id
                    )
                )
            ).all()
            assert [(row.family, row.ordinal, row.source, row.cost_crowns) for row in rows] == [
                (INITIAL_PROFICIENCY[character_class].value, 1, "initial", 0)
            ]
            slots = (
                await session.execute(
                    select(CharacterEquipmentSlot.slot, EquipmentItem)
                    .join(
                        EquipmentItem,
                        EquipmentItem.id == CharacterEquipmentSlot.equipment_item_id,
                    )
                    .where(CharacterEquipmentSlot.character_id == state.id)
                )
            ).all()
            assert len(slots) == 1
            slot, item = slots[0]
            assert slot == "Principal"
            assert item.payload["weapon_type_id"] == STARTING_WEAPON_TYPE_IDS[character_class]
            assert (item.rarity, item.item_level, item.payload["enhancement"]) == ("Comum", 1, 0)
            assert item.payload["rune"] is None and item.payload["enchantment"] is None
            assert await session.scalar(
                select(func.count()).select_from(EquipmentItem).where(
                    EquipmentItem.character_id == state.id
                )
            ) == 1


async def test_starting_weapon_and_proficiency_survive_restart(database):
    state = await _create(CreationService(database[1], "ocaso"), 9200, 4)
    restarted = WeaponTrainerService(database[1], "ocaso")
    view = await restarted.view(9200)
    assert [entry.family for entry in view.entries if entry.owned] == [F.ARCANE_FOCI]
    assert view.next_terms.ordinal == 2
    assert await _owned(database, state.id) == {F.ARCANE_FOCI}


# --- Matriz + Equipment Validator ---------------------------------------------


@pytest.mark.parametrize(
    ("character_class", "families", "weapon_type_id", "expected"),
    [
        ("sentinela", (F.SWORDS,), "weapon.type.base.espada_de_guerra", None),
        ("errante", (F.BLADES, F.SWORDS), "weapon.type.base.espada", None),
        (
            "errante",
            (F.BLADES, F.SWORDS),
            "weapon.type.base.espada_de_guerra",
            EquipmentMutationCode.WEAPON_CLASS_FORBIDDEN,
        ),
        ("vigia", (F.BOWS, F.CROSSBOWS), "weapon.type.base.besta_pesada", None),
        ("tecelao", (F.ARCANE_FOCI, F.SWORDS), "weapon.type.base.espada", None),
        ("oraculo", (F.ARCANE_FOCI, F.SHIELD), "weapon.type.base.escudo", None),
        (
            "oraculo",
            (F.ARCANE_FOCI, F.SWORDS),
            "weapon.type.base.espada",
            EquipmentMutationCode.WEAPON_CLASS_FORBIDDEN,
        ),
        ("luminar", (F.ARCANE_FOCI, F.AXES), "weapon.type.base.machado", None),
        (
            "luminar",
            (F.ARCANE_FOCI, F.AXES),
            "weapon.type.base.machado_de_guerra",
            EquipmentMutationCode.WEAPON_CLASS_FORBIDDEN,
        ),
        # Allowed by the Classe but not trained.
        (
            "tecelao",
            (F.ARCANE_FOCI,),
            "weapon.type.base.espada",
            EquipmentMutationCode.WEAPON_PROFICIENCY_REQUIRED,
        ),
        # Published regional weapons use their explicit identity.
        ("luminar", (F.ARCANE_FOCI, F.BLUNT), "weapon.type.altos.arma_contrapeso", None),
        (
            "sentinela",
            (F.SWORDS,),
            "weapon.type.tdo.arma_pesada_caminhante",
            EquipmentMutationCode.WEAPON_PROFICIENCY_REQUIRED,
        ),
    ],
)
async def test_equipment_validator_applies_proficiency_then_class_whitelist(
    database, character_class, families, weapon_type_id, expected
):
    actor = 9300
    character_id = await _seed(database, actor, character_class, families=families)
    item_id = await _weapon(database, character_id, weapon_type_id)
    service = EquipmentService(database[1], "ocaso")
    if expected is None:
        assert (await service.equip_item(actor, item_id)).changed
        return
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await service.equip_item(actor, item_id)
    assert rejected.value.code == expected
    async with database[1]() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(CharacterEquipmentSlot).where(
                    CharacterEquipmentSlot.character_id == character_id
                )
            )
            == 0
        )
        character = await session.get(Character, character_id)
        assert character.combat_configuration_version == 0


async def test_level_is_checked_before_proficiency(database):
    character_id = await _seed(database, 9901, "sentinela", families=(F.SWORDS,), level=1)
    item_id = await _weapon(database, character_id, "weapon.type.base.espada", level=5)
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await EquipmentService(database[1], "ocaso").equip_item(9901, item_id)
    assert rejected.value.code == EquipmentMutationCode.ITEM_LEVEL_REQUIRED


async def test_weapon_without_identity_cannot_be_equipped_but_armor_can(database):
    character_id = await _seed(database, 9902, "sentinela", families=tuple(F))
    legacy = await _weapon(database, character_id, None, slot="Principal")
    helm = await _weapon(database, character_id, None, slot="Cabeça")
    service = EquipmentService(database[1], "ocaso")
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await service.equip_item(9902, legacy)
    assert rejected.value.code == EquipmentMutationCode.WEAPON_UNMAPPED
    assert (await service.equip_item(9902, helm)).changed


async def test_two_handed_still_clears_secondary_atomically_with_proficiency(database):
    character_id = await _seed(database, 9903, "sentinela", families=(F.SWORDS, F.SHIELD))
    shield = await _weapon(database, character_id, "weapon.type.base.escudo")
    war_sword = await _weapon(database, character_id, "weapon.type.base.espada_de_guerra")
    service = EquipmentService(database[1], "ocaso")
    assert (await service.equip_item(9903, shield)).changed
    assert (await service.equip_item(9903, war_sword, expected_configuration_version=1)).changed
    async with database[1]() as session:
        slots = (
            await session.scalars(
                select(CharacterEquipmentSlot.slot).where(
                    CharacterEquipmentSlot.character_id == character_id
                )
            )
        ).all()
    assert slots == ["Principal"]
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await service.equip_item(9903, shield, expected_configuration_version=2)
    assert rejected.value.code == EquipmentMutationCode.SECONDARY_BLOCKED_BY_TWO_HANDED


# --- Treinador de Armas -------------------------------------------------------


async def test_trainer_charges_progression_and_has_no_cap(database):
    character_id = await _seed(
        database, 9910, "sentinela", families=(F.SWORDS,), level=60, crowns=100_000
    )
    trainer = WeaponTrainerService(database[1], "ocaso")
    paid = []
    for family in (F.BLADES, F.BLUNT, F.AXES, F.POLEARMS, F.SHIELD):
        before = await _crowns(database, character_id)
        outcome = await trainer.learn(9910, family.value)
        assert outcome.learned and outcome.reason is None
        paid.append(before - await _crowns(database, character_id))
    assert paid == [1_000, 2_500, 5_000, 10_000, 20_000]
    assert await _owned(database, character_id) == {
        F.SWORDS, F.BLADES, F.BLUNT, F.AXES, F.POLEARMS, F.SHIELD,
    }
    async with database[1]() as session:
        ordinals = (
            await session.scalars(
                select(CharacterWeaponProficiency.ordinal)
                .where(CharacterWeaponProficiency.character_id == character_id)
                .order_by(CharacterWeaponProficiency.ordinal)
            )
        ).all()
    assert ordinals == [1, 2, 3, 4, 5, 6]


async def test_trainer_level_crowns_location_and_class_rules(database):
    trainer = WeaponTrainerService(database[1], "ocaso")
    low = await _seed(database, 9911, "errante", families=(F.BLADES,), level=9, crowns=50_000)
    outcome = await trainer.learn(9911, F.SWORDS.value)
    assert outcome.reason == TrainingRejected.LEVEL_REQUIRED
    poor = await _seed(database, 9912, "errante", families=(F.BLADES,), level=10, crowns=999)
    outcome = await trainer.learn(9912, F.SWORDS.value)
    assert outcome.reason == TrainingRejected.NOT_ENOUGH_CROWNS
    away = await _seed(
        database, 9913, "errante", families=(F.BLADES,), crowns=5_000, location="Estrada"
    )
    outcome = await trainer.learn(9913, F.SWORDS.value)
    assert outcome.reason == TrainingRejected.LOCATION_REQUIRED
    assert not outcome.view.at_trainer
    wrong = await _seed(database, 9914, "errante", families=(F.BLADES,), crowns=5_000)
    outcome = await trainer.learn(9914, F.BLUNT.value)
    assert outcome.reason == TrainingRejected.NOT_LEARNABLE
    assert F.BLUNT not in {entry.family for entry in outcome.view.entries}
    outcome = await trainer.learn(9914, "proficiency.dual_wield")
    assert outcome.reason == TrainingRejected.UNKNOWN_FAMILY
    for character_id, crowns in ((low, 50_000), (poor, 999), (away, 5_000), (wrong, 5_000)):
        assert await _owned(database, character_id) == {F.BLADES}
        assert await _crowns(database, character_id) == crowns


async def test_errante_learns_swords_but_still_cannot_equip_war_sword(database):
    character_id = await _seed(
        database, 9915, "errante", families=(F.BLADES,), level=10, crowns=1_000
    )
    outcome = await WeaponTrainerService(database[1], "ocaso").learn(9915, F.SWORDS.value)
    assert outcome.learned
    sword = await _weapon(database, character_id, "weapon.type.base.espada")
    war_sword = await _weapon(database, character_id, "weapon.type.base.espada_de_guerra")
    service = EquipmentService(database[1], "ocaso")
    assert (await service.equip_item(9915, sword)).changed
    with pytest.raises(EquipmentMutationRejected) as rejected:
        await service.equip_item(9915, war_sword)
    assert rejected.value.code == EquipmentMutationCode.WEAPON_CLASS_FORBIDDEN


async def test_duplicate_and_concurrent_purchases_charge_once(database):
    character_id = await _seed(
        database, 9916, "vigia", families=(F.BOWS,), level=60, crowns=10_000
    )
    trainers = [WeaponTrainerService(database[1], "ocaso") for _ in range(6)]
    outcomes = await asyncio.gather(
        *(trainer.learn(9916, F.CROSSBOWS.value) for trainer in trainers)
    )
    assert sum(outcome.learned for outcome in outcomes) == 1
    assert sum(outcome.already_owned for outcome in outcomes) == 5
    assert await _crowns(database, character_id) == 9_000
    again = await trainers[0].learn(9916, F.CROSSBOWS.value)
    assert again.already_owned and not again.learned
    assert await _crowns(database, character_id) == 9_000


async def test_concurrent_purchases_of_different_families_use_sequential_prices(database):
    character_id = await _seed(
        database, 9917, "vigia", families=(F.BOWS,), level=60, crowns=10_000
    )
    trainer = WeaponTrainerService(database[1], "ocaso")
    outcomes = await asyncio.gather(
        trainer.learn(9917, F.CROSSBOWS.value),
        trainer.learn(9917, F.SWORDS.value),
        trainer.learn(9917, F.BLADES.value),
    )
    assert all(outcome.learned for outcome in outcomes)
    assert await _crowns(database, character_id) == 10_000 - 1_000 - 2_500 - 5_000


async def test_concurrent_purchase_and_equip_never_leave_partial_state(database):
    character_id = await _seed(
        database, 9918, "tecelao", families=(F.ARCANE_FOCI,), level=10, crowns=1_000
    )
    sword = await _weapon(database, character_id, "weapon.type.base.espada")
    equipment = EquipmentService(database[1], "ocaso")

    async def equip():
        try:
            return await equipment.equip_item(9918, sword)
        except EquipmentMutationRejected as exc:
            return exc

    learned, equipped = await asyncio.gather(
        WeaponTrainerService(database[1], "ocaso").learn(9918, F.SWORDS.value), equip()
    )
    assert learned.learned
    if isinstance(equipped, EquipmentMutationRejected):
        assert equipped.code == EquipmentMutationCode.WEAPON_PROFICIENCY_REQUIRED
        assert (await equipment.equip_item(9918, sword)).changed
    assert await _owned(database, character_id) == {F.ARCANE_FOCI, F.SWORDS}
    assert await _crowns(database, character_id) == 0


async def test_trainer_restores_a_missing_initial_proficiency_before_pricing(database):
    character_id = await _seed(database, 9919, "luminar", level=10, crowns=1_000)
    outcome = await WeaponTrainerService(database[1], "ocaso").learn(9919, F.SHIELD.value)
    assert outcome.learned
    assert await _owned(database, character_id) == {F.ARCANE_FOCI, F.SHIELD}
    assert await _crowns(database, character_id) == 0


# --- Migração -----------------------------------------------------------------


async def test_migration_seeds_initial_proficiency_and_binds_legacy_drops(database):
    def migrate(target):
        def run(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.downgrade(config, target) if target != "head" else command.upgrade(
                config, "head"
            )

        return run

    async with database[0].begin() as connection:
        await connection.run_sync(migrate("20261113_0052"))
    character_id = uuid4()
    async with database[1].begin() as session:
        session.add(Account(telegram_id=9930))
        session.add(
            Character(
                id=character_id,
                telegram_id=9930,
                server_id="ocaso",
                name="Antigo",
                race="remanescente",
                character_class="oraculo",
                stage="menu:ready",
                ruleset_version="gdd-1.4.3-baseline-1.0",
                level=5,
                xp=0,
                hp=Decimal("700"),
                max_hp=Decimal("700"),
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
        await session.flush()
        for key, name, slot in (
            ("legacy:1", "Arma Pesada do Caminhante", "2H"),
            ("legacy:2", "Arma Estranha", "Principal"),
        ):
            session.add(
                EquipmentItem(
                    character_id=character_id,
                    source_key=key,
                    item_name=name,
                    rarity="Comum",
                    slot=slot,
                    item_level=1,
                    bound=False,
                    payload={"item_name": name, "slot": slot},
                )
            )
    async with database[0].begin() as connection:
        await connection.run_sync(migrate("head"))
    async with database[1]() as session:
        assert await owned_families(session, character_id) == {F.ARCANE_FOCI}
        payloads = {
            item.source_key: item.payload
            for item in (
                await session.scalars(
                    select(EquipmentItem).where(EquipmentItem.character_id == character_id)
                )
            ).all()
        }
    assert payloads["legacy:1"]["weapon_type_id"] == "weapon.type.tdo.arma_pesada_caminhante"
    assert "weapon_type_id" not in payloads["legacy:2"]
