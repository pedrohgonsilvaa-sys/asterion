from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.domain.arts import FIRST_CLASS_ART_IDS, SENTINEL_ART_IDS
from asterion.domain.combat_math import resolve_combat_stats
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActiveArtSlot,
    GameActivity,
    HuntRound,
)


async def _seed_character(database, actor: int, *, level: int = 10, cls: str = "sentinela"):
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
    character_id, sessions = await _seed_character(database, actor)
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
    _, sessions = await _seed_character(database, actor, level=1)
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
    await service.equip_art(actor, 1, SENTINEL_ART_IDS["golpe_de_guarda"])

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
