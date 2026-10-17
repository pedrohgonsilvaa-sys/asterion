from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtConfigurationError,
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.equipment import (
    EquipmentMutationCode,
    EquipmentMutationRejected,
    EquipmentService,
    equipment_instance_payload,
)
from asterion.application.equipment_view import EquipmentViewService
from asterion.application.weapon_metadata import resolve_equipment_weapon
from asterion.domain.arts import VIGIA_ART_IDS
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    CraftingReceipt,
    EquipmentItem,
)


async def _seed_character(database, actor: int, character_class: str = "vigia"):
    _, sessions = database
    character_id = uuid4()
    name_suffix = str(actor % 10000).translate(
        str.maketrans("0123456789", "abcdefghij")
    )
    stats = resolve_combat_stats(character_class, 10, "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Weapon{name_suffix}",
                race="remanescente",
                character_class=character_class,
                stage="menu:ready",
                ruleset_version="gdd-1.6.0-baseline-1.0",
                level=10,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
    return character_id, sessions


async def _add_equipment(
    sessions,
    character_id,
    actor: int,
    *,
    weapon_type_id: str | None = None,
    item_name: str | None = None,
    item_slot: str | None = None,
    source_key: str | None = None,
    craft_recipe_id: str | None = None,
    equip: bool = True,
):
    if weapon_type_id is not None:
        payload = materialize_equipment(
            f"weapon-integration:{actor}:{source_key or weapon_type_id}",
            "Comum",
            1,
            weapon_type_id=weapon_type_id,
        )
    else:
        payload = materialize_equipment(
            f"weapon-integration:{actor}:{source_key or 'legacy'}",
            "Comum",
            1,
            forced_name=item_name or "Arco legado desconhecido",
            forced_slot=item_slot or "Principal",
        )
    item_id, payload = equipment_instance_payload(payload)
    exact_source = source_key or f"weapon-integration:{actor}:{item_id.hex}"
    item = EquipmentItem(
        id=item_id,
        character_id=character_id,
        source_key=exact_source,
        item_name=item_name or payload["item_name"],
        rarity=payload["rarity"],
        slot=payload["slot"],
        item_level=payload["item_level"],
        bound=False,
        payload=payload,
    )
    async with sessions.begin() as session:
        if craft_recipe_id is not None:
            receipt_source_key = exact_source.removesuffix(":equipment")
            session.add(
                CraftingReceipt(
                    character_id=character_id,
                    recipe_id=craft_recipe_id,
                    source_key=receipt_source_key,
                    status="committed",
                    preview_fingerprint="f" * 64,
                    seed=f"legacy-craft:{actor}",
                )
            )
        session.add(item)
        if equip:
            await session.flush()
            slot = "Principal" if payload["slot"] == "2H" else payload["slot"]
            session.add(
                CharacterEquipmentSlot(
                    character_id=character_id,
                    slot=slot,
                    equipment_item_id=item_id,
                )
            )
    return item_id


@pytest.mark.asyncio
async def test_exact_crafting_receipt_resolves_legacy_item_without_name_inference(database):
    actor = 771301
    character_id, sessions = await _seed_character(database, actor)
    source_key = f"craft:known-{actor}:equipment"
    item_id = await _add_equipment(
        sessions,
        character_id,
        actor,
        item_name="Nome de exibição alterado",
        item_slot="Principal",
        source_key=source_key,
        craft_recipe_id="recipe.tdo.blacksmith.walker_weapon.comum",
        equip=False,
    )

    async with sessions() as session:
        item = await session.get(EquipmentItem, item_id)
        definition = await resolve_equipment_weapon(session, item)

    assert definition is not None
    assert definition.weapon_type_id == "weapon.type.tdo.arma_caminhante"
    assert definition.compatibility_tags == frozenset({"weapon.compat.melee"})


@pytest.mark.asyncio
async def test_unmapped_legacy_name_does_not_satisfy_vigia_art_requirement(database):
    actor = 771302
    character_id, sessions = await _seed_character(database, actor)
    await _add_equipment(
        sessions,
        character_id,
        actor,
        item_name="Arco antigo",
        item_slot="Principal",
        source_key=f"unknown-legacy:{actor}",
    )

    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await ActiveArtService(sessions, "ocaso").equip_art(
            actor, 1, VIGIA_ART_IDS["disparo_preciso"]
        )
    assert rejected.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT


@pytest.mark.asyncio
async def test_canonical_crossbow_satisfies_vigia_art_requirement(database):
    actor = 771303
    character_id, sessions = await _seed_character(database, actor)
    await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )

    result = await ActiveArtService(sessions, "ocaso").equip_art(
        actor, 1, VIGIA_ART_IDS["disparo_preciso"]
    )
    assert result is not None and result.changed


@pytest.mark.asyncio
async def test_weapon_change_preserves_but_invalidates_incompatible_active_art(database):
    actor = 771304
    character_id, sessions = await _seed_character(database, actor)
    await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
        source_key=f"weapon-integration:{actor}:bow",
    )
    melee_id = await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.arma_caminhante",
        source_key=f"weapon-integration:{actor}:melee",
        equip=False,
    )
    arts = ActiveArtService(sessions, "ocaso")
    equipped = await arts.equip_art(actor, 1, VIGIA_ART_IDS["disparo_preciso"])
    assert equipped is not None and equipped.changed

    changed_weapon = await EquipmentService(sessions, "ocaso").equip_item(actor, melee_id)
    assert changed_weapon is not None and changed_weapon.changed

    view = await arts.view(actor)
    assert view is not None
    assert any(entry.art_id == VIGIA_ART_IDS["disparo_preciso"] for entry in view.slots)
    assert VIGIA_ART_IDS["disparo_preciso"] in view.weapon_incompatible_art_ids
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        with pytest.raises(ActiveArtConfigurationError, match="weapon requirement"):
            await load_active_art_configuration(session, character)
        rows = list(
            (
                await session.scalars(
                    select(CharacterActiveArtSlot).where(
                        CharacterActiveArtSlot.character_id == character_id
                    )
                )
            ).all()
        )
    assert [(row.slot, row.art_id) for row in rows] == [
        (1, VIGIA_ART_IDS["disparo_preciso"])
    ]


@pytest.mark.asyncio
async def test_equipment_detail_exposes_approved_player_facing_metadata(database):
    actor = 771305
    character_id, sessions = await _seed_character(database, actor)
    item_id = await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )

    view = await EquipmentViewService(sessions, "ocaso").detail(actor, item_id)

    assert view is not None
    assert view.item.weapon_form_label == "Arco"
    assert view.item.weapon_handedness_label == "2 mãos"
    assert view.item.weapon_slot_label == "Duas Mãos"
    assert view.item.weapon_compatibility_label == "Arco"


@pytest.mark.asyncio
async def test_canonical_secondary_weapon_uses_only_its_declared_slot(database):
    actor = 771306
    character_id, sessions = await _seed_character(database, actor)
    main_id = await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.arma_caminhante",
        source_key=f"weapon-integration:{actor}:main",
    )
    secondary_id = await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.guarda_caminhante",
        source_key=f"weapon-integration:{actor}:secondary",
        equip=False,
    )
    result = await EquipmentService(sessions, "ocaso").equip_item(actor, secondary_id)

    assert result is not None and result.changed
    async with sessions() as session:
        rows = list(
            (
                await session.scalars(
                    select(CharacterEquipmentSlot)
                    .where(CharacterEquipmentSlot.character_id == character_id)
                    .order_by(CharacterEquipmentSlot.slot)
                )
            ).all()
        )
    assert [(row.slot, row.equipment_item_id) for row in rows] == [
        ("Principal", main_id),
        ("Secundária", secondary_id),
    ]


@pytest.mark.asyncio
async def test_two_handed_weapon_blocks_secondary_until_main_weapon_replaces_it(database):
    actor = 771307
    character_id, sessions = await _seed_character(database, actor)
    await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
        source_key=f"weapon-integration:{actor}:two-handed",
    )
    secondary_id = await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.guarda_caminhante",
        source_key=f"weapon-integration:{actor}:secondary",
        equip=False,
    )
    equipment = EquipmentService(sessions, "ocaso")

    with pytest.raises(EquipmentMutationRejected) as blocked:
        await equipment.equip_item(actor, secondary_id)
    assert blocked.value.code == EquipmentMutationCode.SECONDARY_BLOCKED_BY_TWO_HANDED

    main_only_id = await _add_equipment(
        sessions,
        character_id,
        actor,
        weapon_type_id="weapon.type.tdo.arma_caminhante",
        source_key=f"weapon-integration:{actor}:replacement",
        equip=False,
    )
    replaced = await equipment.equip_item(actor, main_only_id)
    assert replaced is not None and replaced.changed
    equipped_secondary = await equipment.equip_item(actor, secondary_id)
    assert equipped_secondary is not None and equipped_secondary.changed
    async with sessions() as session:
        slots = list(
            (
                await session.scalars(
                    select(CharacterEquipmentSlot)
                    .where(CharacterEquipmentSlot.character_id == character_id)
                    .order_by(CharacterEquipmentSlot.slot)
                )
            ).all()
        )
    assert [(row.slot, row.equipment_item_id) for row in slots] == [
        ("Principal", main_only_id),
        ("Secundária", secondary_id),
    ]
