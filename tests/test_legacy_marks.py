"""Marcas de Legado (GDD §16.1): slots via Ascensão, activation, effects and respec."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from asterion.application.inventory_capacity import (
    INVENTORY_CAPACITY,
    PENDING_CAPACITY,
    WAREHOUSE_CAPACITY,
    inventory_capacity,
    pending_capacity,
    warehouse_capacity,
)
from asterion.application.legacy import REFUGE, REFUGE_BRAZIER, REFUGE_REGION
from asterion.application.legacy_mark_effects import (
    BASE_DOCTRINES,
    doctrine_limit,
    listing_slots,
    promotion_cooldown,
)
from asterion.application.legacy_marks import LegacyMarkRejected, LegacyMarksService
from asterion.bot.legacy_marks_ui import (
    render_legacy_mark_detail,
    render_legacy_mark_removal,
    render_legacy_marks,
)
from asterion.domain.legacy_marks import (
    LEGACY_MARKS,
    MAX_ACTIVE_MARKS,
    RESPEC_COOLDOWN,
    RESPEC_COST_CROWNS,
    LegacyMarkId,
    mark_slots,
)
from asterion.domain.market import LISTING_SLOTS, PROMOTION_COOLDOWN
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    Character,
    CharacterDoctrine,
    CharacterLegacyMark,
    MaterialStack,
    WorldState,
)

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def test_catalog_has_ten_horizontal_marks_and_one_slot_per_legacy_rank():
    assert len(LEGACY_MARKS) == 10
    assert {mark.id for mark in LEGACY_MARKS} == set(LegacyMarkId)
    assert [mark_slots(level) for level in range(6)] == [0, 1, 2, 3, 4, 5]
    assert MAX_ACTIVE_MARKS == 5
    assert RESPEC_COST_CROWNS == 5_000
    assert RESPEC_COOLDOWN == timedelta(days=7)
    with pytest.raises(ValueError):
        mark_slots(6)
    available = {mark.id for mark in LEGACY_MARKS if mark.available}
    assert available == {
        LegacyMarkId.BOLSA_FUNDA,
        LegacyMarkId.ARMAZEM_AMPLO,
        LegacyMarkId.ENTREGAS_GUARDADAS,
        LegacyMarkId.BANCA_EXTRA,
        LegacyMarkId.SEXTA_DOUTRINA,
        LegacyMarkId.PREGAO_CONSTANTE,
    }


async def _seed(database, actor: int, *, legacy_level: int, crowns: int = 20_000, safe=True):
    _, sessions = database
    character_id = uuid4()
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Mrk" + "".join(chr(ord("a") + int(c)) for c in str(actor)[-5:]),
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.6.0",
                level=1,
                legacy_level=legacy_level,
                hp=100,
                max_hp=100,
                crowns=crowns,
            )
        )
        await session.flush()
        location = REFUGE if safe else "Estrada das Cinzas"
        session.add(WorldState(character_id=character_id, region=REFUGE_REGION, location=location))
        session.add(Brazier(character_id=character_id, brazier_id=REFUGE_BRAZIER))
    return character_id


@pytest.mark.asyncio
async def test_slots_come_from_ascension_and_unavailable_marks_cannot_be_activated(database):
    _, sessions = database
    service = LegacyMarksService(sessions, "ocaso")
    await _seed(database, 7101, legacy_level=0)
    outcome = await service.activate(7101, "bolsa_funda", now=NOW)
    assert outcome.reason is LegacyMarkRejected.NO_FREE_SLOT

    await _seed(database, 7102, legacy_level=1)
    first = await service.activate(7102, "bolsa_funda", now=NOW)
    assert first.succeeded and first.view.active_count == 1 and first.view.free_slots == 0
    again = await service.activate(7102, "bolsa_funda", now=NOW)
    assert again.reason is LegacyMarkRejected.ALREADY_ACTIVE
    second = await service.activate(7102, "banca_extra", now=NOW)
    assert second.reason is LegacyMarkRejected.NO_FREE_SLOT

    await _seed(database, 7103, legacy_level=2)
    soon = await service.activate(7103, "chamado_do_braseiro", now=NOW)
    assert soon.reason is LegacyMarkRejected.UNAVAILABLE
    unknown = await service.activate(7103, "forca_bruta", now=NOW)
    assert unknown.reason is LegacyMarkRejected.UNKNOWN


@pytest.mark.asyncio
async def test_active_marks_raise_capacities_listing_slots_doctrines_and_shorten_divulgar(
    database,
):
    _, sessions = database
    service = LegacyMarksService(sessions, "ocaso")
    character_id = await _seed(database, 7201, legacy_level=5)
    async with sessions() as session:
        assert await inventory_capacity(session, character_id) == INVENTORY_CAPACITY
        assert await listing_slots(session, character_id) == LISTING_SLOTS
        assert await promotion_cooldown(session, character_id) == PROMOTION_COOLDOWN
    for mark in (
        "bolsa_funda",
        "armazem_amplo",
        "entregas_guardadas",
        "banca_extra",
        "sexta_doutrina",
    ):
        assert (await service.activate(7201, mark, now=NOW)).succeeded
    full = await service.activate(7201, "pregao_constante", now=NOW)
    assert full.reason is LegacyMarkRejected.NO_FREE_SLOT
    async with sessions() as session:
        assert await inventory_capacity(session, character_id) == 70
        assert await warehouse_capacity(session, character_id) == WAREHOUSE_CAPACITY + 25
        assert await pending_capacity(session, character_id) == PENDING_CAPACITY + 10
        assert await listing_slots(session, character_id) == 8
        assert await doctrine_limit(session, character_id) == BASE_DOCTRINES + 1

    other = await _seed(database, 7202, legacy_level=1)
    assert (await service.activate(7202, "pregao_constante", now=NOW)).succeeded
    async with sessions() as session:
        assert await promotion_cooldown(session, other) == timedelta(minutes=22, seconds=30)


@pytest.mark.asyncio
async def test_redistribution_costs_crowns_needs_safe_place_and_waits_seven_days(database):
    _, sessions = database
    service = LegacyMarksService(sessions, "ocaso")
    await _seed(database, 7301, legacy_level=1, safe=False)
    assert (await service.activate(7301, "pregao_constante", now=NOW)).succeeded
    away = await service.remove(7301, "pregao_constante", now=NOW)
    assert away.reason is LegacyMarkRejected.SAFE_LOCATION_REQUIRED

    await _seed(database, 7302, legacy_level=1, crowns=RESPEC_COST_CROWNS - 1)
    assert (await service.activate(7302, "pregao_constante", now=NOW)).succeeded
    poor = await service.remove(7302, "pregao_constante", now=NOW)
    assert poor.reason is LegacyMarkRejected.NOT_ENOUGH_CROWNS

    character_id = await _seed(database, 7303, legacy_level=1, crowns=12_000)
    assert (await service.activate(7303, "pregao_constante", now=NOW)).succeeded
    removed = await service.remove(7303, "pregao_constante", now=NOW)
    assert removed.succeeded
    assert removed.view.crowns == 7_000 and removed.view.active_count == 0
    assert removed.view.respec_available_at == NOW + RESPEC_COOLDOWN
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.legacy_mark_respec_at == NOW

    # The freed slot is refilled for free; the next removal waits the Recarga.
    swapped = await service.activate(7303, "banca_extra", now=NOW)
    assert swapped.succeeded and swapped.view.crowns == 7_000
    early = await service.remove(7303, "banca_extra", now=NOW + timedelta(days=6))
    assert early.reason is LegacyMarkRejected.RESPEC_COOLDOWN
    later = await service.remove(7303, "banca_extra", now=NOW + RESPEC_COOLDOWN)
    assert later.succeeded and later.view.crowns == 2_000
    missing = await service.remove(7303, "banca_extra", now=NOW + timedelta(days=30))
    assert missing.reason is LegacyMarkRejected.NOT_ACTIVE


@pytest.mark.asyncio
async def test_removal_never_leaves_use_above_the_remaining_capacity(database):
    _, sessions = database
    service = LegacyMarksService(sessions, "ocaso")
    character_id = await _seed(database, 7401, legacy_level=2)
    assert (await service.activate(7401, "sexta_doutrina", now=NOW)).succeeded
    assert (await service.activate(7401, "bolsa_funda", now=NOW)).succeeded
    async with sessions.begin() as session:
        for index in range(BASE_DOCTRINES + 1):
            session.add(
                CharacterDoctrine(
                    character_id=character_id,
                    name=f"Doutrina {index}",
                    configuration={},
                    revision=0,
                )
            )
        for index in range(INVENTORY_CAPACITY + 1):
            session.add(
                MaterialStack(
                    character_id=character_id, material_id=f"material.test.{index}", quantity=1
                )
            )
    doctrines = await service.remove(7401, "sexta_doutrina", now=NOW)
    assert doctrines.reason is LegacyMarkRejected.DOCTRINES_IN_USE
    inventory = await service.remove(7401, "bolsa_funda", now=NOW)
    assert inventory.reason is LegacyMarkRejected.INVENTORY_IN_USE
    async with sessions() as session:
        rows = (
            await session.scalars(
                CharacterLegacyMark.__table__.select().where(
                    CharacterLegacyMark.character_id == character_id
                )
            )
        ).all()
        character = await session.get(Character, character_id)
    assert len(rows) == 2 and character.crowns == 20_000


@pytest.mark.asyncio
async def test_screens_follow_ui_decisions_33_3(database):
    _, sessions = database
    service = LegacyMarksService(sessions, "ocaso")
    await _seed(database, 7501, legacy_level=1)
    view = await service.view(7501, now=NOW)
    root = render_legacy_marks(view)
    assert "Marcas Ativas · 0/5" in root.text and "Vagas livres · 1" in root.text
    labels = [row[0].text for row in root.keyboard.inline_keyboard]
    assert "Bolsa Funda · Capacidade" in labels
    assert "Chamado do Braseiro · Retorno · Em breve" in labels

    detail = render_legacy_mark_detail(view, "bolsa_funda")
    assert "🚫 Marca Inativa" in detail.text
    assert detail.keyboard.inline_keyboard[0][0].callback_data == "lmk:on:bolsa_funda"
    soon = render_legacy_mark_detail(view, "chamado_do_braseiro")
    assert all(
        not button.callback_data.startswith("lmk:on:")
        for row in soon.keyboard.inline_keyboard
        for button in row
    )

    active = (await service.activate(7501, "bolsa_funda", now=NOW)).view
    detail = render_legacy_mark_detail(active, "bolsa_funda")
    assert "✅ Marca Ativa" in detail.text and "Custo · 5.000 Coroas" in detail.text
    assert detail.keyboard.inline_keyboard[0][0].callback_data == "lmk:off:bolsa_funda"
    confirm = render_legacy_mark_removal(active, "bolsa_funda")
    assert f"Local · {REFUGE}" in confirm.text
    assert confirm.keyboard.inline_keyboard[0][0].callback_data == "lmk:offok:bolsa_funda"
    assert "✅ Bolsa Funda · Capacidade" in [
        row[0].text for row in render_legacy_marks(active).keyboard.inline_keyboard
    ]
