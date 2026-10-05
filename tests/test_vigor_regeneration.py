import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

import asterion.application.vigor as vigor_module
from asterion.application.consumables import ConsumableService
from asterion.application.dungeons import DungeonService
from asterion.domain.tdo_galleries import GALLERIES_FAMILY_ID
from asterion.infrastructure.db.models import (
    Account,
    Character,
    ConsumableStack,
    DungeonRun,
    DungeonRunMember,
    Unlock,
    WorldState,
)
from tests.test_road_integration import _seed_road

INTERVAL = timedelta(seconds=vigor_module.REGEN_INTERVAL_SECONDS)


def _vigor_state(vigor: int, anchor: datetime):
    return SimpleNamespace(vigor=vigor, max_vigor=100, vigor_regen_at=anchor)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    ((0, 0), (863, 0), (864, 1), (1728, 2)),
)
def test_regeneration_ticks_at_exact_interval(seconds, expected):
    anchor = datetime(2026, 10, 5, tzinfo=UTC)
    character = _vigor_state(10, anchor)

    gained = vigor_module.reconcile_vigor_state(
        character, now=anchor + timedelta(seconds=seconds)
    )

    assert gained == expected
    assert character.vigor == 10 + expected


def test_regeneration_preserves_fractional_remainder():
    anchor = datetime(2026, 10, 5, tzinfo=UTC)
    character = _vigor_state(10, anchor)

    assert vigor_module.reconcile_vigor_state(
        character, now=anchor + INTERVAL + timedelta(minutes=5)
    ) == 1
    assert character.vigor_regen_at == anchor + INTERVAL

    assert vigor_module.reconcile_vigor_state(
        character, now=anchor + INTERVAL * 2
    ) == 1
    assert character.vigor == 12


def test_twenty_four_hours_fills_to_cap_without_overflow():
    anchor = datetime(2026, 10, 5, tzinfo=UTC)
    character = _vigor_state(0, anchor)

    assert vigor_module.reconcile_vigor_state(
        character, now=anchor + timedelta(hours=24)
    ) == 100
    assert character.vigor == 100


def test_cap_discards_banked_ticks_and_spend_starts_new_window():
    anchor = datetime(2026, 10, 5, tzinfo=UTC)
    full = _vigor_state(100, anchor)
    at_cap = anchor + timedelta(days=4)

    assert vigor_module.reconcile_vigor_state(full, now=at_cap) == 0
    assert full.vigor_regen_at == at_cap
    full.vigor -= 1

    assert vigor_module.reconcile_vigor_state(full, now=at_cap + timedelta(seconds=863)) == 0
    assert full.vigor == 99
    assert vigor_module.reconcile_vigor_state(full, now=at_cap + INTERVAL) == 1
    assert full.vigor == 100


def test_external_gain_that_reaches_cap_resets_regeneration_anchor():
    anchor = datetime(2026, 10, 5, tzinfo=UTC)
    character = _vigor_state(95, anchor)
    now = anchor + timedelta(days=1)

    assert vigor_module.add_vigor_state(character, 20, now=now) == 5
    assert character.vigor == 100
    assert character.vigor_regen_at == now


def test_future_anchor_is_reset_without_negative_or_duplicate_gain():
    now = datetime(2026, 10, 5, tzinfo=UTC)
    character = _vigor_state(0, now + INTERVAL * 5)

    assert vigor_module.reconcile_vigor_state(character, now=now) == 0
    assert character.vigor == 0
    assert character.vigor_regen_at == now


@pytest.mark.asyncio
async def test_potion_reconciles_natural_regeneration_before_usage_gate(database):
    actor = 772801
    _actor, _service = await _seed_road(database, actor=actor, vigor=79)
    sessions = database[1]
    anchor = datetime.now(UTC)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor)
            .with_for_update()
        )
        character.vigor = 79
        character.vigor_regen_at = anchor
        session.add(
            ConsumableStack(
                character_id=character.id,
                consumable_id="consumable.vigor.tdo.i",
                quantity=1,
            )
        )

    result = await ConsumableService(sessions, "ocaso").use_vigor_potion(
        actor,
        "consumable.vigor.tdo.i",
        now=anchor + INTERVAL * 2,
    )

    assert result is None
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == "consumable.vigor.tdo.i",
            )
        )
        assert character.vigor == 81
        assert stack.quantity == 1


@pytest.mark.asyncio
async def test_reconciled_vigor_survives_a_later_reconnect_read(database, monkeypatch):
    actor = 772802
    _actor, _service = await _seed_road(database, actor=actor, vigor=0)
    sessions = database[1]
    anchor = datetime.now(UTC)
    target = anchor + INTERVAL
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor)
            .with_for_update()
        )
        character.vigor = 0
        character.vigor_regen_at = anchor

    monkeypatch.setattr(vigor_module, "utcnow", lambda: target)
    view = await DungeonService(sessions, "ocaso").known(actor)
    assert view is not None and view.vigor == 1

    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.vigor == 1


@pytest.mark.asyncio
async def test_concurrent_reconciliation_cannot_grant_same_tick_twice(database):
    actor = 772803
    _actor, _service = await _seed_road(database, actor=actor, vigor=0)
    sessions = database[1]
    anchor = datetime.now(UTC)
    target = anchor + INTERVAL
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor)
            .with_for_update()
        )
        character.vigor = 0
        character.vigor_regen_at = anchor

    async def reconcile_once():
        async with sessions.begin() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            return await vigor_module.reconcile_character_vigor(
                session, character, now=target
            )

    gains = await asyncio.gather(reconcile_once(), reconcile_once())

    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert sorted(gains) == [0, 1]
        assert character.vigor == 1


async def _seed_galleries(database, actor: int, vigor: int):
    sessions = database[1]
    character_id = uuid4()
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Heroa",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=8,
                xp=0,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
                vigor=vigor,
                max_vigor=100,
                crowns=0,
            )
        )
        session.add_all(
            (
                WorldState(
                    character_id=character_id,
                    region="Terras do Ocaso",
                    location="Ruínas do Vigia",
                ),
                Unlock(character_id=character_id, unlock_id=GALLERIES_FAMILY_ID),
            )
        )
    return character_id, sessions


@pytest.mark.asyncio
async def test_galleries_entry_reconciles_exact_24_to_25_tick_and_reconnects(
    database, monkeypatch
):
    actor = 772804
    character_id, sessions = await _seed_galleries(database, actor, vigor=24)
    anchor = datetime(2026, 10, 5, tzinfo=UTC)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.vigor_regen_at = anchor

    clock = {"now": anchor + INTERVAL - timedelta(microseconds=1)}
    monkeypatch.setattr(vigor_module, "utcnow", lambda: clock["now"])
    service = DungeonService(sessions, "ocaso")

    blocked = await service.start_solo(actor, "stable", GALLERIES_FAMILY_ID)
    assert blocked is not None and blocked.reason == "vigor"
    async with sessions() as session:
        assert await session.scalar(select(DungeonRun.id)) is None
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.vigor == 24

    clock["now"] = anchor + INTERVAL
    started = await service.start_solo(actor, "stable", GALLERIES_FAMILY_ID)
    assert started is not None and started.kind == "ready"
    run_id = started.run_id
    assert run_id is not None
    assert started.vigor == 0

    async with sessions() as session:
        run_count = await session.scalar(
            select(func.count(DungeonRun.id)).where(DungeonRun.id == run_id)
        )
        member = await session.scalar(
            select(DungeonRunMember).where(DungeonRunMember.run_id == run_id)
        )
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert run_count == 1
        assert member.vigor_reserved == 25
        assert character.vigor == 0

    resumed = await DungeonService(sessions, "ocaso").resume(actor)
    assert resumed is not None and resumed.run_id == run_id


@pytest.mark.asyncio
async def test_zero_vigor_can_reach_gallery_cost_through_offline_regeneration(
    database, monkeypatch
):
    actor = 772805
    character_id, sessions = await _seed_galleries(database, actor, vigor=0)
    anchor = datetime(2026, 10, 5, tzinfo=UTC)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.vigor_regen_at = anchor

    monkeypatch.setattr(vigor_module, "utcnow", lambda: anchor + INTERVAL * 25)
    view = await DungeonService(sessions, "ocaso").start_solo(
        actor, "stable", GALLERIES_FAMILY_ID
    )

    assert view is not None and view.kind == "ready"
    assert view.vigor == 0
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        run_count = await session.scalar(
            select(func.count(DungeonRun.id)).where(
                DungeonRun.dungeon_family_id == GALLERIES_FAMILY_ID,
                DungeonRun.status == "active",
            )
        )
        assert character.vigor == 0
        assert run_count == 1