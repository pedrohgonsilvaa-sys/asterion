"""PostgreSQL integration tests for Direct Trade (GDD v1.6.0 §29, §49.18)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.trades import TradeError, TradeService
from asterion.domain.market import TRADE_IDLE_TIMEOUT, TRADE_MAX_DURATION
from asterion.infrastructure.db.models import (
    Account,
    AccountLink,
    AccountRiskFlag,
    Character,
    EquipmentItem,
    MaterialStack,
    PendingItem,
    TradeItem,
    TradeSession,
)

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
ANA, BEA, CAI = 850001, 850002, 850003
MATERIAL = "material.tdo.ferro_fuligem"


async def _seed(database) -> None:
    async with database[1].begin() as session:
        for actor, name in ((ANA, "Ana"), (BEA, "Bea"), (CAI, "Cai")):
            session.add(Account(telegram_id=actor))
            session.add(
                Character(
                    telegram_id=actor,
                    server_id="ocaso",
                    name=name,
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu",
                    ruleset_version="tdo-1.0.15",
                    hp=Decimal("100"),
                    max_hp=Decimal("100"),
                    vigor=100,
                    max_vigor=100,
                    crowns=500,
                )
            )


def _service(database) -> TradeService:
    return TradeService(database[1], "ocaso")


async def _code(awaitable) -> str:
    with pytest.raises(TradeError) as error:
        await awaitable
    return error.value.code


async def _char(session, actor: int) -> Character:
    return await session.scalar(select(Character).where(Character.telegram_id == actor))


async def _material(database, actor, quantity, material_id=MATERIAL, bound=False) -> UUID:
    async with database[1].begin() as session:
        character = await _char(session, actor)
        stack = MaterialStack(
            character_id=character.id, material_id=material_id, quantity=quantity, bound=bound
        )
        session.add(stack)
        await session.flush()
        return stack.id


async def _equipment(database, actor, rarity="Raro") -> UUID:
    async with database[1].begin() as session:
        character = await _char(session, actor)
        item = EquipmentItem(
            id=uuid4(),
            character_id=character.id,
            source_key=f"test:{uuid4()}",
            item_name="Elmo",
            rarity=rarity,
            slot="Cabeca",
            item_level=5,
            bound=False,
            payload={"item_name": "Elmo"},
        )
        session.add(item)
        await session.flush()
        return item.id


async def _total(database, actor, material_id=MATERIAL) -> int:
    async with database[1]() as session:
        character = await _char(session, actor)
        value = await session.scalar(
            select(func.coalesce(func.sum(MaterialStack.quantity), 0)).where(
                MaterialStack.character_id == character.id,
                MaterialStack.material_id == material_id,
            )
        )
        return int(value)


async def _slots(database, actor) -> int:
    async with database[1]() as session:
        character = await _char(session, actor)
        value = await session.scalar(
            select(func.count(MaterialStack.id)).where(
                MaterialStack.character_id == character.id, MaterialStack.quantity > 0
            )
        )
        return int(value)


async def _fill(database, actor, slots) -> None:
    async with database[1].begin() as session:
        character = await _char(session, actor)
        for index in range(slots):
            session.add(
                MaterialStack(
                    character_id=character.id,
                    material_id=f"material.fill.{index}",
                    quantity=1,
                    bound=True,
                )
            )


async def _open(service, now=NOW):
    invite = await service.invite(ANA, "bea", now=now)
    await service.respond(BEA, invite.trade_id, accept=True, now=now)
    return invite.trade_id


async def _confirm_all(service, trade_id, steps=2, now=NOW):
    revision = (await service.current(ANA, now=now)).revision
    outcome = None
    for _ in range(steps):
        await service.confirm(ANA, trade_id, revision, now=now)
        outcome = await service.confirm(BEA, trade_id, revision, now=now)
    return outcome


@pytest.mark.asyncio
async def test_swap_commits_after_two_confirmations_of_both(database):
    await _seed(database)
    service = _service(database)
    a = await _material(database, ANA, 10)
    b = await _equipment(database, BEA)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", a, 4, now=NOW)
    await service.add_item(BEA, trade_id, "equipment", b, 1, now=NOW)
    assert await _total(database, ANA) == 6
    outcome = await _confirm_all(service, trade_id)
    assert outcome.status == "committed"
    assert await _total(database, BEA) == 4
    async with database[1]() as session:
        item = await session.get(EquipmentItem, b)
        assert item.character_id == (await _char(session, ANA)).id
        assert {row.status for row in await session.scalars(select(TradeItem))} == {"delivered"}


@pytest.mark.asyncio
async def test_unilateral_gift_is_allowed_and_empty_trade_is_not(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 2)
    trade_id = await _open(service)
    assert await _code(service.confirm(ANA, trade_id, 0, now=NOW)) == "trade_empty"
    await service.add_item(ANA, trade_id, "material", source, 2, now=NOW)
    assert (await _confirm_all(service, trade_id)).status == "committed"
    assert await _total(database, BEA) == 2


@pytest.mark.asyncio
async def test_crowns_never_move(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 2)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 1, now=NOW)
    await _confirm_all(service, trade_id)
    async with database[1]() as session:
        assert (await _char(session, ANA)).crowns == 500
        assert (await _char(session, BEA)).crowns == 500


@pytest.mark.asyncio
async def test_a_change_resets_confirmations_and_old_buttons(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    view = await service.add_item(ANA, trade_id, "material", source, 1, now=NOW)
    await service.confirm(ANA, trade_id, view.revision, now=NOW)
    await service.confirm(BEA, trade_id, view.revision, now=NOW)
    changed = await service.add_item(ANA, trade_id, "material", source, 1, now=NOW)
    assert (changed.my_steps, changed.their_steps) == (0, 0)
    assert await _code(service.confirm(BEA, trade_id, view.revision, now=NOW)) == "trade_changed"


@pytest.mark.asyncio
async def test_second_step_waits_for_the_other_side(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    view = await service.add_item(ANA, trade_id, "material", source, 1, now=NOW)
    await service.confirm(ANA, trade_id, view.revision, now=NOW)
    assert await _code(service.confirm(ANA, trade_id, view.revision, now=NOW)) == (
        "waiting_partner"
    )


@pytest.mark.asyncio
async def test_mythic_needs_a_third_step(database):
    await _seed(database)
    service = _service(database)
    item = await _equipment(database, ANA, rarity="Mítico")
    trade_id = await _open(service)
    view = await service.add_item(ANA, trade_id, "equipment", item, 1, now=NOW)
    assert view.steps_required == 3
    assert (await _confirm_all(service, trade_id, steps=2)).status == "waiting"
    assert (await _confirm_all(service, trade_id, steps=1)).status == "committed"


@pytest.mark.asyncio
async def test_bound_items_are_refused(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5, bound=True)
    trade_id = await _open(service)
    assert await _code(service.add_item(ANA, trade_id, "material", source, 1, now=NOW)) == (
        "item_bound"
    )


@pytest.mark.asyncio
async def test_full_to_full_swap_fits_the_final_state(database):
    await _seed(database)
    service = _service(database)
    a = await _material(database, ANA, 1, "material.a")
    b = await _material(database, BEA, 1, "material.b")
    await _fill(database, ANA, 59)
    await _fill(database, BEA, 59)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", a, 1, now=NOW)
    await service.add_item(BEA, trade_id, "material", b, 1, now=NOW)
    assert (await _confirm_all(service, trade_id)).status == "committed"
    assert await _total(database, ANA, "material.b") == 1
    assert await _total(database, BEA, "material.a") == 1


@pytest.mark.asyncio
async def test_no_space_keeps_everything_and_resets_confirmations(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 1, "material.a")
    await _fill(database, BEA, 60)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 1, now=NOW)
    outcome = await _confirm_all(service, trade_id)
    assert outcome.status == "no_space"
    assert (outcome.view.my_steps, outcome.view.their_steps) == (0, 0)
    assert outcome.view.status == "open"
    assert await _total(database, BEA, "material.a") == 0
    await service.cancel(ANA, trade_id, now=NOW)
    assert await _total(database, ANA, "material.a") == 1


@pytest.mark.asyncio
async def test_cancel_returns_items_to_their_owners(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 3, now=NOW)
    await service.cancel(BEA, trade_id, now=NOW)
    assert await _total(database, ANA) == 5
    assert await service.current(ANA, now=NOW) is None


@pytest.mark.asyncio
async def test_withdrawing_an_item_returns_it(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    view = await service.add_item(ANA, trade_id, "material", source, 3, now=NOW)
    assert await _code(service.remove_item(BEA, trade_id, view.my_items[0].item_id, now=NOW)) == (
        "item_unavailable"
    )
    updated = await service.remove_item(ANA, trade_id, view.my_items[0].item_id, now=NOW)
    assert updated.my_items == ()
    assert await _total(database, ANA) == 5


@pytest.mark.asyncio
async def test_idle_timeout_is_ten_minutes(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 3, now=NOW)
    almost = NOW + TRADE_IDLE_TIMEOUT - timedelta(seconds=1)
    assert await service.current(ANA, now=almost) is not None
    assert await service.current(ANA, now=NOW + TRADE_IDLE_TIMEOUT) is None
    assert await _total(database, ANA) == 5


@pytest.mark.asyncio
async def test_absolute_limit_is_thirty_minutes_despite_activity(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    for minutes in (9, 18, 27):
        await service.add_item(
            ANA, trade_id, "material", source, 1, now=NOW + timedelta(minutes=minutes)
        )
    moment = NOW + TRADE_MAX_DURATION
    assert await _code(service.add_item(ANA, trade_id, "material", source, 1, now=moment)) == (
        "trade_unavailable"
    )
    assert await _total(database, ANA) == 5


@pytest.mark.asyncio
async def test_maintenance_closes_abandoned_trades(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 3, now=NOW)
    assert await service.run_maintenance(now=NOW + timedelta(minutes=9)) == 0
    assert await service.run_maintenance(now=NOW + TRADE_IDLE_TIMEOUT) == 1
    assert await _total(database, ANA) == 5


@pytest.mark.asyncio
async def test_expiry_with_a_full_inventory_goes_to_pending(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5, "material.a")
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 5, now=NOW)
    await _fill(database, ANA, 60)
    await service.run_maintenance(now=NOW + TRADE_IDLE_TIMEOUT)
    async with database[1]() as session:
        pending = await session.scalar(select(PendingItem))
        assert pending.quantity == 5 and pending.source_key.startswith("market:")


@pytest.mark.asyncio
async def test_invite_rules(database):
    await _seed(database)
    service = _service(database)
    assert await _code(service.invite(ANA, "ana", now=NOW)) == "self_trade"
    assert await _code(service.invite(ANA, "ninguem", now=NOW)) == "partner_unavailable"
    await service.invite(ANA, "bea", now=NOW)
    assert await _code(service.invite(CAI, "bea", now=NOW)) == "trade_busy"
    assert await _code(service.invite(BEA, "cai", now=NOW)) == "trade_busy"


@pytest.mark.asyncio
async def test_only_the_invited_character_answers(database):
    await _seed(database)
    service = _service(database)
    invite = await service.invite(ANA, "bea", now=NOW)
    assert await _code(service.respond(ANA, invite.trade_id, accept=True, now=NOW)) == (
        "not_invited"
    )
    declined = await service.respond(BEA, invite.trade_id, accept=False, now=NOW)
    assert declined.status == "declined"


@pytest.mark.asyncio
async def test_third_character_cannot_touch_a_trade(database):
    await _seed(database)
    service = _service(database)
    trade_id = await _open(service)
    assert await _code(service.cancel(CAI, trade_id, now=NOW)) == "not_a_party"
    assert await _code(service.confirm(CAI, trade_id, 0, now=NOW)) == "not_a_party"


@pytest.mark.asyncio
async def test_concurrent_invites_keep_one_live_trade_each(database):
    await _seed(database)
    service = _service(database)
    await asyncio.gather(
        service.invite(ANA, "bea", now=NOW),
        service.invite(CAI, "bea", now=NOW),
        return_exceptions=True,
    )
    async with database[1]() as session:
        assert await session.scalar(select(func.count(TradeSession.id))) == 1


@pytest.mark.asyncio
async def test_concurrent_final_confirmations_commit_once(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    view = await service.add_item(ANA, trade_id, "material", source, 2, now=NOW)
    await service.confirm(ANA, trade_id, view.revision, now=NOW)
    await service.confirm(BEA, trade_id, view.revision, now=NOW)
    await asyncio.gather(
        service.confirm(ANA, trade_id, view.revision, now=NOW),
        service.confirm(BEA, trade_id, view.revision, now=NOW),
    )
    assert await _total(database, BEA) == 2
    assert await _total(database, ANA) == 3


@pytest.mark.asyncio
async def test_concurrent_add_of_one_stack_never_duplicates(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 3)
    trade_id = await _open(service)
    await asyncio.gather(
        *(service.add_item(ANA, trade_id, "material", source, 2, now=NOW) for _ in range(3)),
        return_exceptions=True,
    )
    async with database[1]() as session:
        escrow = await session.scalar(
            select(func.coalesce(func.sum(TradeItem.quantity), 0)).where(
                TradeItem.status == "escrow"
            )
        )
    assert int(escrow) + await _total(database, ANA) == 3


@pytest.mark.asyncio
async def test_deleted_party_returns_the_other_side(database):
    await _seed(database)
    service = _service(database)
    source = await _material(database, ANA, 5)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 3, now=NOW)
    async with database[1].begin() as session:
        await delete_character_owned_data(session, (await _char(session, BEA)).id)
    assert await service.run_maintenance(now=NOW) == 1
    assert await _total(database, ANA) == 5


@pytest.mark.asyncio
async def test_trade_between_linked_accounts_is_flagged_only(database):
    await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        session.add(AccountLink(account_a=ANA, account_b=BEA))
    source = await _material(database, ANA, 2)
    trade_id = await _open(service)
    await service.add_item(ANA, trade_id, "material", source, 1, now=NOW)
    assert (await _confirm_all(service, trade_id)).status == "committed"
    async with database[1]() as session:
        assert (await session.scalar(select(AccountRiskFlag))).activity_kind == "direct_trade"
