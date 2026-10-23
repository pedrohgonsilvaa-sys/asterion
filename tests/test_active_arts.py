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
from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.equipment import equipment_instance_payload
from asterion.domain.arts import (
    ACTIVE_ART_IDS_BY_CLASS,
    ATIRADOR_ART_IDS,
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    CONJURADOR_ART_IDS,
    DEVASTADOR_ART_IDS,
    ERRANTE_ART_IDS,
    FIRST_CLASS_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    SABOTADOR_ART_IDS,
    SENTINEL_ART_IDS,
    VIGIA_ART_IDS,
)
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    EquipmentItem,
    GameActivity,
    HuntRound,
)


async def _seed_character(
    database,
    actor: int,
    *,
    level: int = 10,
    cls: str = "sentinela",
    selected_path: str | None = None,
    weapon_type_id: str | None = None,
):
    _, sessions = database
    stats = resolve_combat_stats(cls, level, "remanescente")
    character_id = uuid4()
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor)[-5:])
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Art{suffix}"[:16],
                race="remanescente",
                character_class=cls,
                selected_path=selected_path,
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
        if weapon_type_id is not None:
            weapon_payload = materialize_equipment(
                f"active-art-test:{actor}",
                "Comum",
                1,
                weapon_type_id=weapon_type_id,
            )
            weapon_id, weapon_payload = equipment_instance_payload(weapon_payload)
            session.add(
                EquipmentItem(
                    id=weapon_id,
                    character_id=character_id,
                    source_key=f"active-art-test:{actor}:weapon",
                    item_name=weapon_payload["item_name"],
                    rarity=weapon_payload["rarity"],
                    slot=weapon_payload["slot"],
                    item_level=weapon_payload["item_level"],
                    bound=False,
                    payload=weapon_payload,
                )
            )
            await session.flush()
            session.add(
                CharacterEquipmentSlot(
                    character_id=character_id,
                    slot="Principal",
                    equipment_item_id=weapon_id,
                )
            )
    return character_id, sessions


@pytest.mark.asyncio
async def test_empty_active_art_configuration_is_valid(database):
    actor = 771001
    character_id, sessions = await _seed_character(database, actor)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_active_art_configuration(session, character)

    assert snapshot.combat_configuration_version == 0
    assert snapshot.slots == ()
    assert snapshot.art_ids == ()


@pytest.mark.asyncio
async def test_equip_three_slots_order_duplicate_noop_and_unequip(database):
    actor = 771002
    character_id, sessions = await _seed_character(
        database,
        actor,
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    arts = (
        SENTINEL_ART_IDS["golpe_de_guarda"],
        SENTINEL_ART_IDS["quebra_postura"],
        SENTINEL_ART_IDS["muralha_breve"],
    )

    third = await service.equip_art(actor, 3, arts[2], expected_configuration_version=0)
    assert third is not None and third.changed and third.combat_configuration_version == 1
    first = await service.equip_art(actor, 1, arts[0], expected_configuration_version=1)
    assert first is not None and first.changed and first.combat_configuration_version == 2
    second = await service.equip_art(actor, 2, arts[1], expected_configuration_version=2)
    assert second is not None and second.changed and second.combat_configuration_version == 3

    repeat = await service.equip_art(actor, 2, arts[1], expected_configuration_version=3)
    assert repeat is not None and not repeat.changed
    assert repeat.combat_configuration_version == 3

    with pytest.raises(ActiveArtMutationRejected) as duplicate:
        await service.equip_art(actor, 2, arts[0], expected_configuration_version=3)
    assert duplicate.value.code == ActiveArtMutationCode.DUPLICATE_ART

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_active_art_configuration(session, character)
    assert [(row.slot, row.art_id) for row in snapshot.slots] == [
        (1, arts[0]),
        (2, arts[1]),
        (3, arts[2]),
    ]
    assert snapshot.combat_configuration_version == 3

    removed = await service.unequip_slot(actor, 2, expected_configuration_version=3)
    assert removed is not None and removed.changed
    assert removed.combat_configuration_version == 4
    empty = await service.unequip_slot(actor, 2, expected_configuration_version=4)
    assert empty is not None and not empty.changed
    assert empty.combat_configuration_version == 4


@pytest.mark.asyncio
async def test_active_art_mutation_rejects_invalid_slot_wrong_class_level_and_stale_version(
    database,
):
    actor = 771003
    _, sessions = await _seed_character(
        database,
        actor,
        level=1,
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")

    with pytest.raises(ActiveArtMutationRejected) as bad_slot:
        await service.equip_art(actor, 4, SENTINEL_ART_IDS["golpe_de_guarda"])
    assert bad_slot.value.code == ActiveArtMutationCode.INVALID_SLOT

    with pytest.raises(ActiveArtMutationRejected) as unknown:
        await service.equip_art(actor, 1, "class_art.sentinela.inexistente")
    assert unknown.value.code == ActiveArtMutationCode.UNKNOWN_ART

    with pytest.raises(ActiveArtMutationRejected) as wrong_class:
        await service.equip_art(actor, 1, FIRST_CLASS_ART_IDS["errante"])
    assert wrong_class.value.code == ActiveArtMutationCode.WRONG_CLASS

    with pytest.raises(ActiveArtMutationRejected) as level_required:
        await service.equip_art(actor, 1, SENTINEL_ART_IDS["impacto_resoluto"])
    assert level_required.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    equipped = await service.equip_art(actor, 1, SENTINEL_ART_IDS["golpe_de_guarda"])
    assert equipped is not None and equipped.combat_configuration_version == 1
    with pytest.raises(ActiveArtMutationRejected) as stale:
        await service.unequip_slot(actor, 1, expected_configuration_version=0)
    assert stale.value.code == ActiveArtMutationCode.STALE_CONFIGURATION


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("blocker", "status"),
    [("activity", "active"), ("round", "active"), ("round", "interrupted")],
)
async def test_active_art_mutation_uses_shared_combat_configuration_guard(
    database, blocker, status
):
    actor = 771010 + (0 if blocker == "activity" else 1 if status == "active" else 2)
    character_id, sessions = await _seed_character(database, actor)
    async with sessions.begin() as session:
        if blocker == "activity":
            session.add(
                GameActivity(
                    id=uuid4(),
                    character_id=character_id,
                    content_id="test.blocker",
                    status=status,
                    state_version=0,
                    ruleset_version="test",
                )
            )
        else:
            session.add(
                HuntRound(
                    id=uuid4(),
                    character_id=character_id,
                    status=status,
                    batch_size=5,
                    seed=f"active-art-{status}",
                )
            )

    service = ActiveArtService(sessions, "ocaso")
    with pytest.raises(CombatConfigurationLocked):
        await service.equip_art(actor, 1, SENTINEL_ART_IDS["golpe_de_guarda"])


@pytest.mark.asyncio
async def test_active_art_rows_cascade_with_character(database):
    actor = 771020
    character_id, sessions = await _seed_character(database, actor)
    service = ActiveArtService(sessions, "ocaso")
    await service.equip_art(actor, 1, SENTINEL_ART_IDS["muralha_breve"])

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        await session.delete(character)

    async with sessions() as session:
        rows = list(
            (
                await session.scalars(
                    select(CharacterActiveArtSlot).where(
                        CharacterActiveArtSlot.character_id == character_id
                    )
                )
            ).all()
        )
    assert rows == []


@pytest.mark.asyncio
async def test_devastador_ariete_unlock_path_class_and_weapon_gates(database):
    ariete = DEVASTADOR_ART_IDS["ariete"]
    service = ActiveArtService(database[1], "ocaso")

    low_actor = 771030
    await _seed_character(
        database,
        low_actor,
        level=11,
        selected_path="devastador",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    low_view = await service.view(low_actor)
    assert low_view is not None and ariete not in low_view.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as low_level:
        await service.equip_art(low_actor, 1, ariete)
    assert low_level.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    bastion_actor = 771031
    await _seed_character(
        database,
        bastion_actor,
        level=20,
        selected_path="bastiao",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    bastion_view = await service.view(bastion_actor)
    assert bastion_view is not None and ariete not in bastion_view.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as wrong_path:
        await service.equip_art(bastion_actor, 1, ariete)
    assert wrong_path.value.code == ActiveArtMutationCode.PATH_REQUIRED

    other_class_actor = 771032
    await _seed_character(
        database,
        other_class_actor,
        level=20,
        cls="vigia",
        selected_path="atirador",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    with pytest.raises(ActiveArtMutationRejected) as wrong_class:
        await service.equip_art(other_class_actor, 1, ariete)
    assert wrong_class.value.code == ActiveArtMutationCode.WRONG_CLASS

    unarmed_actor = 771033
    await _seed_character(
        database, unarmed_actor, level=12, selected_path="devastador"
    )
    unarmed_view = await service.view(unarmed_actor)
    assert unarmed_view is not None and ariete in unarmed_view.available_art_ids
    assert ariete in unarmed_view.weapon_incompatible_art_ids
    with pytest.raises(ActiveArtMutationRejected) as no_weapon:
        await service.equip_art(unarmed_actor, 1, ariete)
    assert no_weapon.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    bow_actor = 771034
    await _seed_character(
        database,
        bow_actor,
        level=12,
        selected_path="devastador",
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    bow_view = await service.view(bow_actor)
    assert bow_view is not None and ariete in bow_view.weapon_incompatible_art_ids
    with pytest.raises(ActiveArtMutationRejected) as incompatible:
        await service.equip_art(bow_actor, 1, ariete)
    assert incompatible.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    melee_actor = 771035
    _, melee_sessions = await _seed_character(
        database,
        melee_actor,
        level=12,
        selected_path="devastador",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    melee_view = await service.view(melee_actor)
    assert melee_view is not None and ariete in melee_view.available_art_ids
    assert ariete not in melee_view.weapon_incompatible_art_ids
    equipped = await service.equip_art(
        melee_actor, 2, ariete, expected_configuration_version=0
    )
    assert equipped is not None and equipped.changed
    async with melee_sessions.begin() as session:
        character = await session.get(Character, melee_view.character_id)
        active = await load_active_art_configuration(session, character)
    assert active.art_ids == (ariete,)
    assert ariete in ACTIVE_ART_IDS_BY_CLASS["sentinela"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "art_id", "character_class", "actor", "weapon_type_id"),
    [
        (
            "bastiao",
            BASTIAO_ART_IDS["escudo_de_cinzas"],
            "sentinela",
            771036,
            None,
        ),
        (
            "carrasco",
            CARRASCO_ART_IDS["corte_de_execucao"],
            "errante",
            771037,
            "weapon.type.tdo.arma_caminhante",
        ),
        (
            "sabotador",
            SABOTADOR_ART_IDS["veneno_velado"],
            "errante",
            771038,
            "weapon.type.vde.arma_vale",
        ),
        (
            "atirador",
            ATIRADOR_ART_IDS["tiro_perfurante"],
            "vigia",
            772040,
            "weapon.type.tdo.arma_pesada_caminhante",
        ),
        (
            "rastreador",
            RASTREADOR_ART_IDS["flecha_serrilhada"],
            "vigia",
            772041,
            "weapon.type.vde.arma_pesada_lacos",
        ),
        (
            "conjurador",
            CONJURADOR_ART_IDS["estilhaco_do_veu"],
            "tecelao",
            772042,
            None,
        ),
        (
            "runico",
            RUNICO_ART_IDS["runa_de_guarda"],
            "tecelao",
            772043,
            None,
        ),
    ],
)
async def test_first_wave_path_arts_unlock_at_12_and_persist(
    database, path, art_id, character_class, actor, weapon_type_id
):
    service = ActiveArtService(database[1], "ocaso")
    await _seed_character(
        database,
        actor,
        level=11,
        cls=character_class,
        selected_path=path,
        weapon_type_id=weapon_type_id,
    )

    with pytest.raises(ActiveArtMutationRejected) as level_gate:
        await service.equip_art(actor, 1, art_id)
    assert level_gate.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    wrong_path_actor = actor + 10
    wrong_path = {
        "bastiao": "devastador",
        "carrasco": "sabotador",
        "sabotador": "carrasco",
        "atirador": "rastreador",
        "rastreador": "atirador",
        "conjurador": "runico",
        "runico": "conjurador",
    }[path]
    await _seed_character(
        database,
        wrong_path_actor,
        level=12,
        cls=character_class,
        selected_path=wrong_path,
        weapon_type_id=weapon_type_id,
    )
    with pytest.raises(ActiveArtMutationRejected) as path_gate:
        await service.equip_art(wrong_path_actor, 1, art_id)
    assert path_gate.value.code == ActiveArtMutationCode.PATH_REQUIRED

    wrong_class_actor = actor + 20
    wrong_class = "vigia" if character_class == "tecelao" else "tecelao"
    await _seed_character(
        database,
        wrong_class_actor,
        level=12,
        cls=wrong_class,
        selected_path="conjurador" if wrong_class == "tecelao" else "atirador",
    )
    with pytest.raises(ActiveArtMutationRejected) as class_gate:
        await service.equip_art(wrong_class_actor, 1, art_id)
    assert class_gate.value.code == ActiveArtMutationCode.WRONG_CLASS

    if weapon_type_id is not None:
        unarmed_actor = actor + 21
        await _seed_character(
            database,
            unarmed_actor,
            level=12,
            cls=character_class,
            selected_path=path,
        )
        with pytest.raises(ActiveArtMutationRejected) as weapon_gate:
            await service.equip_art(unarmed_actor, 1, art_id)
        assert weapon_gate.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    correct_actor = actor + 30
    character_id, sessions = await _seed_character(
        database,
        correct_actor,
        level=12,
        cls=character_class,
        selected_path=path,
        weapon_type_id=weapon_type_id,
    )

    available = await service.view(correct_actor)
    assert available is not None and art_id in available.available_art_ids
    equipped = await service.equip_art(correct_actor, 1, art_id)
    assert equipped is not None and equipped.changed

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        configuration = await load_active_art_configuration(session, character)
    assert configuration.art_ids == (art_id,)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "weapon_type_id"),
    [
        ("carrasco", "weapon.type.tdo.arma_caminhante"),
        ("sabotador", "weapon.type.vde.arma_vale"),
    ],
)
async def test_errante_corte_duplo_unlocks_at_18_for_both_paths_and_persists(
    database, path, weapon_type_id
):
    art_id = ERRANTE_ART_IDS["corte_duplo"]
    sessions = database[1]
    service = ActiveArtService(sessions, "ocaso")
    actor = 771040 if path == "carrasco" else 771041

    await _seed_character(
        database,
        actor,
        level=17,
        cls="errante",
        selected_path=path,
        weapon_type_id=weapon_type_id,
    )
    locked = await service.view(actor)
    assert locked is not None and art_id not in locked.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as below_level:
        await service.equip_art(actor, 1, art_id)
    assert below_level.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    actor += 10
    character_id, _ = await _seed_character(
        database,
        actor,
        level=18,
        cls="errante",
        selected_path=path,
        weapon_type_id=weapon_type_id,
    )
    available = await service.view(actor)
    assert available is not None and art_id in available.available_art_ids
    assert art_id not in available.weapon_incompatible_art_ids
    equipped = await service.equip_art(actor, 3, art_id)
    assert equipped is not None and equipped.art_id == art_id

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        configuration = await load_active_art_configuration(session, character)
    assert configuration.art_ids == (art_id,)
    assert configuration.slots[0].slot == 3


@pytest.mark.asyncio
async def test_errante_corte_duplo_requires_explicit_melee_weapon_metadata(database):
    art_id = ERRANTE_ART_IDS["corte_duplo"]
    sessions = database[1]
    service = ActiveArtService(sessions, "ocaso")

    unarmed_actor = 771050
    await _seed_character(
        database, unarmed_actor, level=18, cls="errante", selected_path="carrasco"
    )
    unarmed = await service.view(unarmed_actor)
    assert unarmed is not None and art_id in unarmed.weapon_incompatible_art_ids
    with pytest.raises(ActiveArtMutationRejected) as no_weapon:
        await service.equip_art(unarmed_actor, 1, art_id)
    assert no_weapon.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

    bow_actor = 771051
    await _seed_character(
        database,
        bow_actor,
        level=18,
        cls="errante",
        selected_path="sabotador",
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    bow = await service.view(bow_actor)
    assert bow is not None and art_id in bow.weapon_incompatible_art_ids
    with pytest.raises(ActiveArtMutationRejected) as wrong_weapon:
        await service.equip_art(bow_actor, 1, art_id)
    assert wrong_weapon.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT


@pytest.mark.asyncio
async def test_errante_corte_duplo_revalidates_class_and_level_gates(database):
    art_id = ERRANTE_ART_IDS["corte_duplo"]
    sessions = database[1]
    service = ActiveArtService(sessions, "ocaso")

    other_class_actor = 771060
    await _seed_character(
        database,
        other_class_actor,
        level=18,
        cls="vigia",
        selected_path="atirador",
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    with pytest.raises(ActiveArtMutationRejected) as wrong_class:
        await service.equip_art(other_class_actor, 1, art_id)
    assert wrong_class.value.code == ActiveArtMutationCode.WRONG_CLASS

    actor = 771061
    character_id, _ = await _seed_character(
        database,
        actor,
        level=18,
        cls="errante",
        selected_path="carrasco",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    await service.equip_art(actor, 1, art_id)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 17

    view = await service.view(actor)
    assert view is not None and view.ineligible_art_ids == (art_id,)
    with pytest.raises(ActiveArtConfigurationError, match="level requirement"):
        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            await load_active_art_configuration(session, character)
    with pytest.raises(ActiveArtMutationRejected) as level_gate:
        await service.equip_art(actor, 2, art_id)
    assert level_gate.value.code == ActiveArtMutationCode.LEVEL_REQUIRED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "weapon_type_id", "actor", "available_level"),
    [
        ("atirador", "weapon.type.tdo.arma_pesada_caminhante", 771070, 18),
        ("rastreador", "weapon.type.vde.arma_pesada_lacos", 771071, 20),
        (None, "weapon.type.tdo.arma_pesada_caminhante", 771072, 20),
    ],
)
async def test_vigia_tiro_calculado_unlocks_at_18_and_persists_for_both_paths(
    database, path, weapon_type_id, actor, available_level
):
    art_id = VIGIA_ART_IDS["tiro_calculado"]
    sessions = database[1]
    service = ActiveArtService(sessions, "ocaso")

    await _seed_character(
        database,
        actor,
        level=17,
        cls="vigia",
        selected_path=path,
        weapon_type_id=weapon_type_id,
    )
    locked = await service.view(actor)
    assert locked is not None and art_id not in locked.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as level_gate:
        await service.equip_art(actor, 1, art_id)
    assert level_gate.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    actor += 1_000
    character_id, _ = await _seed_character(
        database,
        actor,
        level=available_level,
        cls="vigia",
        selected_path=path,
        weapon_type_id=weapon_type_id,
    )
    available = await service.view(actor)
    assert available is not None and art_id in available.available_art_ids
    assert art_id not in available.weapon_incompatible_art_ids
    equipped = await service.equip_art(actor, 3, art_id)
    assert equipped is not None and equipped.art_id == art_id

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        configuration = await load_active_art_configuration(session, character)
    assert configuration.art_ids == (art_id,)
    assert configuration.slots[0].slot == 3


@pytest.mark.asyncio
async def test_vigia_tiro_calculado_rejects_other_classes_and_non_ranged_metadata(database):
    art_id = VIGIA_ART_IDS["tiro_calculado"]
    sessions = database[1]
    service = ActiveArtService(sessions, "ocaso")

    other_class = 771080
    await _seed_character(
        database,
        other_class,
        level=20,
        cls="errante",
        selected_path="carrasco",
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    assert art_id not in (await service.view(other_class)).available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as wrong_class:
        await service.equip_art(other_class, 1, art_id)
    assert wrong_class.value.code == ActiveArtMutationCode.WRONG_CLASS

    for actor, weapon_type_id in (
        (771081, None),
        (771082, "weapon.type.tdo.arma_caminhante"),
    ):
        await _seed_character(
            database,
            actor,
            level=20,
            cls="vigia",
            selected_path="atirador",
            weapon_type_id=weapon_type_id,
        )
        view = await service.view(actor)
        assert view is not None and art_id in view.weapon_incompatible_art_ids
        with pytest.raises(ActiveArtMutationRejected) as incompatible:
            await service.equip_art(actor, 1, art_id)
        assert incompatible.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT


@pytest.mark.asyncio
async def test_path_art_configuration_is_revalidated_after_level_change_and_repairable(
    database,
):
    actor = 771036
    ariete = DEVASTADOR_ART_IDS["ariete"]
    character_id, sessions = await _seed_character(
        database,
        actor,
        level=12,
        selected_path="devastador",
        weapon_type_id="weapon.type.tdo.arma_caminhante",
    )
    service = ActiveArtService(sessions, "ocaso")
    await service.equip_art(actor, 1, ariete)

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 11
    view = await service.view(actor)
    assert view is not None and view.ineligible_art_ids == (ariete,)
    with pytest.raises(ActiveArtConfigurationError, match="level requirement"):
        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            await load_active_art_configuration(session, character)

    removed = await service.unequip_slot(actor, 1, expected_configuration_version=1)
    assert removed is not None and removed.changed
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        active = await load_active_art_configuration(session, character)
    assert active.slots == ()
