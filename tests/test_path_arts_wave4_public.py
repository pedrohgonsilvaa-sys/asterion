from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.equipment import equipment_instance_payload
from asterion.domain.arts import (
    AGOUREIRO_ART_IDS,
    ATIRADOR_ART_IDS,
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    CONJURADOR_ART_IDS,
    DEVASTADOR_ART_IDS,
    GUARDIAO_ART_IDS,
    INQUISIDOR_ART_IDS,
    INVOCADOR_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    SABOTADOR_ART_IDS,
)
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    EquipmentItem,
)

CASES = (
    (BASTIAO_ART_IDS["ultima_muralha"], "sentinela", "bastiao", None, "devastador"),
    (
        DEVASTADOR_ART_IDS["ruptor"],
        "sentinela",
        "devastador",
        "weapon.type.tdo.arma_caminhante",
        "bastiao",
    ),
    (
        CARRASCO_ART_IDS["ceifa"],
        "errante",
        "carrasco",
        "weapon.type.tdo.arma_caminhante",
        "sabotador",
    ),
    (
        SABOTADOR_ART_IDS["colapso_preparado"],
        "errante",
        "sabotador",
        "weapon.type.vde.arma_vale",
        "carrasco",
    ),
    (
        ATIRADOR_ART_IDS["disparo_terminal"],
        "vigia",
        "atirador",
        "weapon.type.tdo.arma_pesada_caminhante",
        "rastreador",
    ),
    (
        RASTREADOR_ART_IDS["predacao_persistente"],
        "vigia",
        "rastreador",
        "weapon.type.vde.arma_pesada_lacos",
        "atirador",
    ),
    (CONJURADOR_ART_IDS["rasgo_conjurado"], "tecelao", "conjurador", None, "runico"),
    (RUNICO_ART_IDS["circulo_runico"], "tecelao", "runico", None, "conjurador"),
    (AGOUREIRO_ART_IDS["eclipse_previsto"], "oraculo", "agoureiro", None, "invocador"),
    (INVOCADOR_ART_IDS["triade_encarnada"], "oraculo", "invocador", None, "agoureiro"),
    (GUARDIAO_ART_IDS["aurora_guardia"], "luminar", "guardiao", None, "inquisidor"),
    (INQUISIDOR_ART_IDS["veredito"], "luminar", "inquisidor", None, "guardiao"),
)


async def _seed(
    database,
    actor: int,
    *,
    level: int,
    cls: str,
    path: str,
    weapon: str | None,
):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(cls, level, "remanescente")
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
                selected_path=path,
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
        if weapon is not None:
            payload = materialize_equipment(
                f"wave4-art:{actor}", "Comum", 1, weapon_type_id=weapon
            )
            weapon_id, payload = equipment_instance_payload(payload)
            session.add(
                EquipmentItem(
                    id=weapon_id,
                    character_id=character_id,
                    source_key=f"wave4-art:{actor}:weapon",
                    item_name=payload["item_name"],
                    rarity=payload["rarity"],
                    slot=payload["slot"],
                    item_level=payload["item_level"],
                    bound=False,
                    payload=payload,
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
    return character_id


@pytest.mark.asyncio
async def test_all_wave4_arts_are_publicly_level_gated_and_persisted(database):
    service = ActiveArtService(database[1], "ocaso")
    for index, (art_id, cls, path, weapon, other_path) in enumerate(CASES):
        actor = 980_000 + index * 10
        await _seed(database, actor, level=51, cls=cls, path=path, weapon=weapon)
        locked = await service.view(actor)
        assert locked is not None and art_id not in locked.available_art_ids
        with pytest.raises(ActiveArtMutationRejected) as level_error:
            await service.equip_art(actor, 1, art_id)
        assert level_error.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

        await _seed(database, actor + 1, level=52, cls=cls, path=other_path, weapon=weapon)
        with pytest.raises(ActiveArtMutationRejected) as path_error:
            await service.equip_art(actor + 1, 1, art_id)
        assert path_error.value.code == ActiveArtMutationCode.PATH_REQUIRED

        wrong_class = "errante" if cls != "errante" else "sentinela"
        await _seed(
            database,
            actor + 2,
            level=52,
            cls=wrong_class,
            path=path,
            weapon=weapon,
        )
        with pytest.raises(ActiveArtMutationRejected) as class_error:
            await service.equip_art(actor + 2, 1, art_id)
        assert class_error.value.code == ActiveArtMutationCode.WRONG_CLASS

        if weapon is not None:
            await _seed(
                database,
                actor + 4,
                level=52,
                cls=cls,
                path=path,
                weapon=None,
            )
            with pytest.raises(ActiveArtMutationRejected) as weapon_error:
                await service.equip_art(actor + 4, 1, art_id)
            assert weapon_error.value.code == ActiveArtMutationCode.WEAPON_REQUIREMENT

        valid_actor = actor + 3
        character_id = await _seed(
            database, valid_actor, level=52, cls=cls, path=path, weapon=weapon
        )
        view = await service.view(valid_actor)
        assert view is not None and art_id in view.available_art_ids
        assert art_id not in view.weapon_incompatible_art_ids
        equipped = await service.equip_art(valid_actor, 2, art_id)
        assert equipped is not None and equipped.changed
        async with database[1].begin() as session:
            character = await session.get(Character, character_id)
            config = await load_active_art_configuration(session, character)
            assert config.art_ids == (art_id,)
            assert config.slots[0].slot == 2
            row = await session.scalar(
                select(CharacterActiveArtSlot).where(
                    CharacterActiveArtSlot.character_id == character_id
                )
            )
            assert row is not None and row.art_id == art_id
