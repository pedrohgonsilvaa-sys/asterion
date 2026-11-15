"""Explorar das Terras do Ocaso v1.0.18 (fatia 2) against PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.progression import level_xp
from asterion.application.tdo_explore import (
    CAMARA_CODEX_ENTRY,
    TdoExploreService,
)
from asterion.domain.tdo_explore import (
    CAMARA_LOCATION_ID,
    CHARNECA_LOCATION_ID,
    EXPLORE_TARGETS,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterActionThrottle,
    CodexEntry,
    LocationDiscovery,
    RewardEvent,
    WorldState,
)

REFUGE = "Refúgio do Ocaso"
T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


async def _seed(database, actor, *, level=1, xp=0, location=REFUGE, discovered=()):
    character_id = uuid4()
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor))
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"E{suffix}",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.7.0-baseline-1.0",
                level=level,
                xp=xp,
                hp=Decimal("900"),
                max_hp=Decimal("900"),
                vigor=77,
                max_vigor=100,
                crowns=5,
            )
        )
        await session.flush()
        session.add(
            WorldState(character_id=character_id, region="Terras do Ocaso", location=location)
        )
        for location_id in discovered:
            session.add(LocationDiscovery(character_id=character_id, location_id=location_id))
    return character_id


def _service(database, clock):
    return TdoExploreService(database[1], "ocaso", clock=clock)


async def _discovered(database, character_id):
    async with database[1]() as session:
        return set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character_id
                    )
                )
            ).all()
        )


async def _character(database, character_id):
    async with database[1]() as session:
        return await session.get(Character, character_id)


@pytest.mark.asyncio
async def test_four_clicks_reveal_all_targets_once_with_xp_and_zero_vigor(database):
    actor = 910001
    cid = await _seed(database, actor)
    clock = Clock()
    service = _service(database, clock)
    seen = set()
    total = 0
    for _ in range(4):
        result = await service.explore(actor)
        assert result.status == "discovered"
        assert result.label and result.location_id not in seen
        assert result.xp == 120  # XP(1)=4800 * 2,5%
        seen.add(result.location_id)
        total += result.xp
        clock.advance(3)
    assert seen == {t.location_id for t in EXPLORE_TARGETS}
    assert total == 480
    assert (await service.explore(actor)).status == "unavailable"
    assert await service.remaining(actor) == ()
    character = await _character(database, cid)
    assert character.vigor == 77 and character.crowns == 5
    assert character.level == 1 and character.xp == 480
    assert await _discovered(database, cid) == seen
    async with database[1]() as session:
        world = await session.get(WorldState, cid)
        assert world.location == REFUGE
        events = await session.scalar(
            select(func.count()).select_from(RewardEvent).where(RewardEvent.character_id == cid)
        )
        assert events == 4


@pytest.mark.asyncio
async def test_xp_uses_min_of_reference_and_level_and_consolidates_level(database):
    actor = 910002
    cid = await _seed(database, actor, level=12, xp=level_xp(12) - 1)
    service = _service(database, Clock())
    result = await service.explore(actor)
    expected = {
        t.location_id: int(
            (Decimal(level_xp(min(t.reference_level, 12))) * Decimal("0.025")).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
        )
        for t in EXPLORE_TARGETS
    }[result.location_id]
    assert result.xp == expected
    character = await _character(database, cid)
    assert character.level == 13
    assert character.xp == expected - 1


@pytest.mark.asyncio
async def test_cooldown_is_persisted_and_does_not_reset_on_refusal(database):
    actor = 910003
    cid = await _seed(database, actor)
    clock = Clock()
    assert (await _service(database, clock).explore(actor)).status == "discovered"
    clock.advance(2)
    # novo serviço = mesmo banco; o horário vem do banco
    refused = await _service(database, clock).explore(actor)
    assert refused.status == "cooldown"
    assert 0.9 < refused.retry_after_seconds <= 1.0
    assert len(await _discovered(database, cid)) == 1
    clock.advance(1)  # 3 s desde o clique aceito (recusa não reiniciou)
    assert (await _service(database, clock).explore(actor)).status == "discovered"
    async with database[1]() as session:
        row = await session.get(CharacterActionThrottle, cid)
        assert row.last_click_at == clock.now and row.resolving is False


@pytest.mark.asyncio
async def test_one_in_resolution_blocks_even_after_cooldown(database):
    actor = 910004
    cid = await _seed(database, actor)
    clock = Clock()
    service = _service(database, clock)
    assert (await service.explore(actor)).status == "discovered"
    async with database[1].begin() as session:
        row = await session.get(CharacterActionThrottle, cid)
        row.resolving = True
    clock.advance(10)
    assert (await service.explore(actor)).status == "busy"
    assert len(await _discovered(database, cid)) == 1
    # Bloco C: flag orfa expira (RESOLVING_TIMEOUT), o jogador nao fica travado.
    clock.advance(31)
    assert (await service.explore(actor)).status == "discovered"
    assert len(await _discovered(database, cid)) == 2


@pytest.mark.asyncio
async def test_l10_existing_discoveries_keep_without_xp_and_leave_the_draw(database):
    actor = 910005
    cid = await _seed(database, actor, discovered=(CHARNECA_LOCATION_ID,))
    service = _service(database, Clock())
    remaining = await service.remaining(actor)
    assert CHARNECA_LOCATION_ID not in {t.location_id for t in remaining}
    assert len(remaining) == 3
    character = await _character(database, cid)
    assert character.xp == 0
    for _ in range(3):
        result = await service.explore(actor)
        assert result.status == "discovered" and result.location_id != CHARNECA_LOCATION_ID
        service.clock.advance(3)
    assert (await service.explore(actor)).status == "unavailable"
    assert (await _character(database, cid)).xp == 360  # só 3 Locais pagos
    async with database[1]() as session:
        paid = await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == cid,
                RewardEvent.source_id == "tdo.explore.discovery." + CHARNECA_LOCATION_ID,
            )
        )
        assert paid is None


@pytest.mark.asyncio
async def test_l11_character_standing_in_undiscovered_location_counts_it_without_xp(database):
    actor = 910006
    cid = await _seed(database, actor, location="Bosque Calcinado")
    service = _service(database, Clock())
    ids = {t.location_id for t in await service.remaining(actor)}
    assert "tdo.location.bosque_calcinado" not in ids  # leitura já conta, sem escrever
    assert await _discovered(database, cid) == set()
    result = await service.explore(actor)  # fora do Refúgio: recusa, mas grava L11
    assert result.status == "not_in_refuge"
    assert await _discovered(database, cid) == {"tdo.location.bosque_calcinado"}
    character = await _character(database, cid)
    assert character.xp == 0 and character.level == 1
    async with database[1]() as session:
        world = await session.get(WorldState, cid)
        assert world.location == "Bosque Calcinado"
        assert (
            await session.scalar(
                select(func.count()).select_from(RewardEvent).where(RewardEvent.character_id == cid)
            )
            == 0
        )


@pytest.mark.asyncio
async def test_camara_discovery_creates_codex_entry_once_other_locations_do_not(database):
    actor = 910007
    others = tuple(t.location_id for t in EXPLORE_TARGETS if t.location_id != CAMARA_LOCATION_ID)
    cid = await _seed(database, actor, discovered=others)
    result = await _service(database, Clock()).explore(actor)
    assert result.status == "discovered" and result.location_id == CAMARA_LOCATION_ID
    assert result.camara_codex and result.xp == 120
    async with database[1]() as session:
        entries = (
            await session.scalars(select(CodexEntry.entry_id).where(CodexEntry.character_id == cid))
        ).all()
    assert entries == [CAMARA_CODEX_ENTRY]

    other = await _seed(database, 910008)
    clock = Clock()
    service = _service(database, clock)
    for _ in range(3):
        res = await service.explore(910008)
        assert res.camara_codex == (res.location_id == CAMARA_LOCATION_ID)
        clock.advance(3)
    async with database[1]() as session:
        count = await session.scalar(
            select(func.count()).select_from(CodexEntry).where(CodexEntry.character_id == other)
        )
    assert count == (1 if CAMARA_LOCATION_ID in await _discovered(database, other) else 0)


@pytest.mark.asyncio
async def test_explore_is_individual_per_character(database):
    first = await _seed(database, 910009)
    second = await _seed(database, 910010)
    clock = Clock()
    service = _service(database, clock)
    assert (await service.explore(910009)).status == "discovered"
    assert len(await _discovered(database, first)) == 1
    assert await _discovered(database, second) == set()
    # anti-spam é por personagem: o outro clica no mesmo instante
    assert (await service.explore(910010)).status == "discovered"


@pytest.mark.asyncio
async def test_explore_outside_refuge_and_without_character(database):
    actor = 910011
    cid = await _seed(database, actor, location="Estrada das Cinzas")
    service = _service(database, Clock())
    assert (await service.explore(actor)).status == "not_in_refuge"
    assert (await service.explore(999999999)).status == "no_character"
    assert await _discovered(database, cid) == set()


@pytest.mark.asyncio
async def test_l14_reconcile_in_camara_creates_codex_entry_once_without_xp(database):
    actor = 910012
    cid = await _seed(database, actor, location="Câmara do Poente")
    service = _service(database, Clock())
    assert (await service.explore(actor)).status == "not_in_refuge"
    assert (await service.explore(actor)).status == "not_in_refuge"  # idempotente
    assert await _discovered(database, cid) == {CAMARA_LOCATION_ID}
    async with database[1]() as session:
        entries = (
            await session.scalars(select(CodexEntry.entry_id).where(CodexEntry.character_id == cid))
        ).all()
    assert entries == [CAMARA_CODEX_ENTRY]
    character = await _character(database, cid)
    assert character.xp == 0 and character.level == 1
