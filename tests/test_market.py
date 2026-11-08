"""PostgreSQL integration tests for Personal Shops (GDD v1.6.0 §28, §49.10, §55.4)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.market import MarketError, MarketService
from asterion.domain.market import LISTING_DURATION, PROMOTION_COOLDOWN
from asterion.infrastructure.db.models import (
    Account,
    AccountLink,
    AccountRiskFlag,
    BlockedDelivery,
    Character,
    CharacterEquipmentSlot,
    ConsumableStack,
    EquipmentItem,
    MarketListing,
    MarketPriceChange,
    MarketPurchase,
    MaterialStack,
    PendingItem,
    PlayerShop,
    RuneStack,
)

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
SELLER, BUYER, THIRD = 840001, 840002, 840003
MATERIAL = "material.tdo.ferro_fuligem"


async def _seed(database, crowns: int = 100_000) -> None:
    async with database[1].begin() as session:
        for actor, name in ((SELLER, "Vendedor"), (BUYER, "Comprador"), (THIRD, "Terceiro")):
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
                    crowns=crowns,
                )
            )


def _service(database) -> MarketService:
    return MarketService(database[1], "ocaso")


async def _code(awaitable) -> str:
    with pytest.raises(MarketError) as error:
        await awaitable
    return error.value.code


async def _char(session, actor: int) -> Character:
    return await session.scalar(select(Character).where(Character.telegram_id == actor))


async def _give_material(database, actor: int, quantity: int, bound: bool = False) -> UUID:
    async with database[1].begin() as session:
        character = await _char(session, actor)
        stack = MaterialStack(
            character_id=character.id, material_id=MATERIAL, quantity=quantity, bound=bound
        )
        session.add(stack)
        await session.flush()
        return stack.id


async def _give_equipment(database, actor: int, **overrides) -> UUID:
    payload = overrides.pop("payload", {"item_name": "Lâmina"})
    async with database[1].begin() as session:
        character = await _char(session, actor)
        item = EquipmentItem(
            id=uuid4(),
            character_id=character.id,
            source_key=f"test:{uuid4()}",
            item_name="Lâmina",
            rarity=overrides.pop("rarity", "Raro"),
            slot="Principal",
            item_level=5,
            bound=overrides.pop("bound", False),
            payload=payload,
        )
        session.add(item)
        await session.flush()
        return item.id


async def _material_total(database, actor: int) -> int:
    async with database[1]() as session:
        character = await _char(session, actor)
        total = await session.scalar(
            select(func.coalesce(func.sum(MaterialStack.quantity), 0)).where(
                MaterialStack.character_id == character.id
            )
        )
        return int(total)


async def _crowns(database, actor: int) -> int:
    async with database[1]() as session:
        return (await _char(session, actor)).crowns


async def _fill_inventory(database, actor: int, slots: int) -> None:
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


async def _listing(service, database, quantity=10, stock=10, price=20, now=NOW):
    source = await _give_material(database, SELLER, stock)
    return await service.create_listing(SELLER, "material", source, quantity, price, now=now)


async def _buy(service, actor, listing_id, quantity, now=NOW, **kwargs):
    preview = await service.prepare_purchase(actor, listing_id, quantity, now=now)
    return await service.confirm_purchase(actor, preview.purchase_id, now=now, **kwargs)


@pytest.mark.asyncio
async def test_shop_keeps_one_opaque_code_even_when_edited(database):
    await _seed(database)
    service = _service(database)
    first = await service.my_shop(SELLER, now=NOW)
    edited = await service.edit_shop(SELLER, name="Forja do Norte", description="Lâminas", now=NOW)
    assert edited.code == first.code and edited.shop_id == first.shop_id
    assert edited.name == "Forja do Norte" and edited.description == "Lâminas"
    cleared = await service.edit_shop(SELLER, clear_name=True, clear_description=True, now=NOW)
    assert cleared.name == "Loja de Vendedor" and cleared.description is None
    assert cleared.code == first.code


@pytest.mark.asyncio
async def test_market_is_closed_during_the_prologue(database):
    await _seed(database)
    async with database[1].begin() as session:
        (await _char(session, BUYER)).stage = "cinzas_na_estrada:intro"
    assert await _code(_service(database).my_shop(BUYER, now=NOW)) == "market_locked"


@pytest.mark.asyncio
async def test_search_finds_only_by_code_and_invalid_is_generic(database):
    await _seed(database)
    service = _service(database)
    shop = await service.my_shop(SELLER, now=NOW)
    found = await service.find_shop(BUYER, shop.code.lower(), now=NOW)
    assert found.shop_id == shop.shop_id and not found.is_owner
    later = NOW + timedelta(seconds=11)
    assert await _code(service.find_shop(BUYER, "Vendedor", now=later)) == "shop_unavailable"


@pytest.mark.asyncio
async def test_search_burst_of_five_in_ten_seconds(database):
    await _seed(database)
    service = _service(database)
    for index in range(5):
        moment = NOW + timedelta(seconds=index)
        assert await _code(service.find_shop(BUYER, "AAAAAAAA", now=moment)) == "shop_unavailable"
    moment = NOW + timedelta(seconds=5)
    assert await _code(service.find_shop(BUYER, "AAAAAAAA", now=moment)) == "search_rate_limited"
    moment = NOW + timedelta(seconds=11)
    assert await _code(service.find_shop(BUYER, "AAAAAAAA", now=moment)) == "shop_unavailable"


@pytest.mark.asyncio
async def test_search_limit_of_twenty_per_minute(database):
    await _seed(database)
    service = _service(database)
    for index in range(20):
        moment = NOW + timedelta(seconds=index * 2.9)
        await _code(service.find_shop(BUYER, "AAAAAAAA", now=moment))
    moment = NOW + timedelta(seconds=58)
    assert await _code(service.find_shop(BUYER, "AAAAAAAA", now=moment)) == "search_rate_limited"


@pytest.mark.asyncio
async def test_listing_puts_the_item_in_escrow_for_seven_days(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=4)
    assert await _material_total(database, SELLER) == 6
    assert listing.expires_at == NOW + LISTING_DURATION
    assert listing.remaining == listing.initial == 4


@pytest.mark.asyncio
async def test_seventh_listing_is_refused(database):
    await _seed(database)
    service = _service(database)
    source = await _give_material(database, SELLER, 10)
    for _ in range(6):
        await service.create_listing(SELLER, "material", source, 1, 5, now=NOW)
    code = await _code(service.create_listing(SELLER, "material", source, 1, 5, now=NOW))
    assert code == "listing_slots_full"
    assert await _material_total(database, SELLER) == 4


@pytest.mark.asyncio
async def test_price_must_be_a_positive_whole_crown(database):
    await _seed(database)
    service = _service(database)
    source = await _give_material(database, SELLER, 2)
    assert await _code(service.create_listing(SELLER, "material", source, 1, 0, now=NOW)) == (
        "invalid_price"
    )


@pytest.mark.asyncio
async def test_bound_items_cannot_be_listed(database):
    await _seed(database)
    service = _service(database)
    stack = await _give_material(database, SELLER, 5, bound=True)
    assert await _code(service.create_listing(SELLER, "material", stack, 1, 5, now=NOW)) == (
        "item_bound"
    )
    item = await _give_equipment(database, SELLER, bound=True)
    assert await _code(service.create_listing(SELLER, "equipment", item, 1, 5, now=NOW)) == (
        "item_bound"
    )


@pytest.mark.asyncio
async def test_locked_item_and_bound_component_cannot_be_listed(database):
    await _seed(database)
    service = _service(database)
    locked = await _give_equipment(database, SELLER, payload={"locked": True})
    assert await _code(service.create_listing(SELLER, "equipment", locked, 1, 5, now=NOW)) == (
        "item_locked"
    )
    rune = await _give_equipment(database, SELLER, payload={"rune": {"bound": True}})
    assert await _code(service.create_listing(SELLER, "equipment", rune, 1, 5, now=NOW)) == (
        "item_component_bound"
    )


@pytest.mark.asyncio
async def test_equipped_item_cannot_be_listed(database):
    await _seed(database)
    service = _service(database)
    item_id = await _give_equipment(database, SELLER)
    async with database[1].begin() as session:
        character = await _char(session, SELLER)
        session.add(
            CharacterEquipmentSlot(
                character_id=character.id, slot="Principal", equipment_item_id=item_id
            )
        )
    assert await _code(service.create_listing(SELLER, "equipment", item_id, 1, 5, now=NOW)) == (
        "item_equipped"
    )


@pytest.mark.asyncio
async def test_equipment_sale_moves_the_same_instance_and_applies_fee(database):
    await _seed(database)
    service = _service(database)
    item_id = await _give_equipment(database, SELLER, payload={"favorite": True, "note": "x"})
    listing = await service.create_listing(SELLER, "equipment", item_id, 1, 1000, now=NOW)
    result = await _buy(service, BUYER, listing.listing_id, 1)
    assert (result.gross, result.fee, result.net) == (1000, 50, 950)
    assert await _crowns(database, BUYER) == 99_000
    assert await _crowns(database, SELLER) == 100_950
    async with database[1]() as session:
        item = await session.get(EquipmentItem, item_id)
        buyer = await _char(session, BUYER)
        assert item.character_id == buyer.id
        assert "favorite" not in item.payload and item.payload["note"] == "x"
        closed = await session.get(MarketListing, listing.listing_id)
        assert closed.status == "sold_out"


@pytest.mark.asyncio
async def test_partial_purchases_use_cumulative_fee(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=10, price=19)
    fees = []
    for _ in range(10):
        fees.append((await _buy(service, BUYER, listing.listing_id, 1)).fee)
    assert sum(fees) == 9  # floor(190 * 5%)
    assert await _crowns(database, SELLER) == 100_000 + 190 - 9
    assert await _material_total(database, BUYER) == 10


@pytest.mark.asyncio
async def test_stack_is_conserved_across_buyer_seller_and_escrow(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=6, stock=10)
    await _buy(service, BUYER, listing.listing_id, 2)
    assert await service.remove_listing(SELLER, listing.listing_id, now=NOW) == "inventory"
    assert await _material_total(database, BUYER) == 2
    assert await _material_total(database, SELLER) == 8


@pytest.mark.asyncio
async def test_old_confirmation_never_buys_at_the_new_price(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, price=20)
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 1, now=NOW)
    edited = await service.edit_price(SELLER, listing.listing_id, 30, now=NOW)
    assert edited.terms_version == 2
    assert await _code(service.confirm_purchase(BUYER, preview.purchase_id, now=NOW)) == (
        "offer_updated"
    )
    assert await _crowns(database, BUYER) == 100_000
    assert await _material_total(database, BUYER) == 0
    async with database[1]() as session:
        change = await session.scalar(select(MarketPriceChange))
        assert (change.old_price, change.new_price, change.terms_version) == (20, 30, 2)


@pytest.mark.asyncio
async def test_earlier_partial_purchase_does_not_invalidate_a_confirmation(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=5)
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 2, now=NOW)
    await _buy(service, THIRD, listing.listing_id, 3)
    result = await service.confirm_purchase(BUYER, preview.purchase_id, now=NOW)
    assert result.remaining == 0


@pytest.mark.asyncio
async def test_insufficient_quantity_fails_safely(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=5)
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 4, now=NOW)
    await _buy(service, THIRD, listing.listing_id, 3)
    assert await _code(service.confirm_purchase(BUYER, preview.purchase_id, now=NOW)) == (
        "insufficient_quantity"
    )
    assert await _crowns(database, BUYER) == 100_000


@pytest.mark.asyncio
async def test_repeated_click_buys_once(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=5)
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 1, now=NOW)
    first = await service.confirm_purchase(BUYER, preview.purchase_id, now=NOW)
    second = await service.confirm_purchase(BUYER, preview.purchase_id, now=NOW)
    assert not first.already_committed and second.already_committed
    assert await _crowns(database, BUYER) == 100_000 - 20
    assert await _material_total(database, BUYER) == 1


@pytest.mark.asyncio
async def test_owner_cannot_buy_the_own_listing(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database)
    assert await _code(service.prepare_purchase(SELLER, listing.listing_id, 1, now=NOW)) == (
        "own_listing"
    )


@pytest.mark.asyncio
async def test_purchase_needs_crowns_and_inventory_space(database):
    await _seed(database, crowns=10)
    service = _service(database)
    listing = await _listing(service, database, quantity=5)
    assert await _code(_buy(service, BUYER, listing.listing_id, 1)) == "not_enough_crowns"
    async with database[1].begin() as session:
        (await _char(session, BUYER)).crowns = 1000
    await _fill_inventory(database, BUYER, 60)
    assert await _code(_buy(service, BUYER, listing.listing_id, 1)) == "inventory_full"
    assert await _crowns(database, BUYER) == 1000
    async with database[1]() as session:
        assert await session.scalar(select(func.count(PendingItem.id))) == 0


@pytest.mark.asyncio
async def test_purchase_merges_into_an_existing_stack_when_full(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=5)
    await _give_material(database, BUYER, 1)
    await _fill_inventory(database, BUYER, 59)
    await _buy(service, BUYER, listing.listing_id, 2)
    assert await _material_total(database, BUYER) == 1 + 2 + 59


@pytest.mark.asyncio
async def test_consumable_and_rune_listings_round_trip(database):
    await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        seller = await _char(session, SELLER)
        potion = ConsumableStack(
            character_id=seller.id, consumable_id="consumable.heal.1", quantity=3
        )
        rune = RuneStack(
            character_id=seller.id,
            family="ataque",
            rarity="Rara",
            grade=1,
            potency="1%",
            quantity=2,
            bound=False,
        )
        session.add_all([potion, rune])
        await session.flush()
        potion_id, rune_id = potion.id, rune.id
    potion_listing = await service.create_listing(SELLER, "consumable", potion_id, 2, 5, now=NOW)
    rune_listing = await service.create_listing(SELLER, "rune", rune_id, 1, 5, now=NOW)
    await _buy(service, BUYER, potion_listing.listing_id, 2)
    await _buy(service, BUYER, rune_listing.listing_id, 1)
    async with database[1]() as session:
        buyer = await _char(session, BUYER)
        assert (
            await session.scalar(
                select(ConsumableStack.quantity).where(ConsumableStack.character_id == buyer.id)
            )
            == 2
        )
        received = await session.scalar(select(RuneStack).where(RuneStack.character_id == buyer.id))
        assert (received.quantity, received.potency) == (1, "1%")


@pytest.mark.asyncio
async def test_mythic_requires_the_extra_confirmation(database):
    await _seed(database)
    service = _service(database)
    item = await _give_equipment(database, SELLER, rarity="Mítico")
    assert await _code(service.create_listing(SELLER, "equipment", item, 1, 100, now=NOW)) == (
        "mythic_confirmation_required"
    )
    listing = await service.create_listing(
        SELLER, "equipment", item, 1, 100, mythic_confirmed=True, now=NOW
    )
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 1, now=NOW)
    assert preview.mythic
    assert await _code(service.confirm_purchase(BUYER, preview.purchase_id, now=NOW)) == (
        "mythic_confirmation_required"
    )
    await service.confirm_purchase(BUYER, preview.purchase_id, mythic_confirmed=True, now=NOW)


@pytest.mark.asyncio
async def test_expired_listing_returns_and_cannot_be_bought(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=4)
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 1, now=NOW)
    later = NOW + LISTING_DURATION
    assert await _code(service.confirm_purchase(BUYER, preview.purchase_id, now=later)) == (
        "listing_unavailable"
    )
    assert await _material_total(database, SELLER) == 10
    async with database[1]() as session:
        assert (await session.get(MarketListing, listing.listing_id)).status == "expired"


@pytest.mark.asyncio
async def test_maintenance_returns_expired_listing_of_an_offline_seller(database):
    await _seed(database)
    service = _service(database)
    await _listing(service, database, quantity=4)
    assert await service.run_maintenance(now=NOW + timedelta(days=6)) == 0
    assert await service.run_maintenance(now=NOW + LISTING_DURATION) == 1
    assert await _material_total(database, SELLER) == 10


@pytest.mark.asyncio
async def test_return_uses_pending_then_blocked_delivery(database):
    await _seed(database)
    service = _service(database)
    first = await _listing(service, database, quantity=10, stock=10)
    second = await _listing(service, database, quantity=10, stock=10)
    await _fill_inventory(database, SELLER, 60)
    assert await service.remove_listing(SELLER, first.listing_id, now=NOW) == "pending"
    async with database[1].begin() as session:
        seller = await _char(session, SELLER)
        pending = await session.scalar(select(PendingItem))
        assert pending.source_key.startswith("market:") and pending.quantity == 10
        for index in range(19):
            session.add(
                PendingItem(
                    character_id=seller.id,
                    source_key=f"filler:{index}",
                    kind="material",
                    payload={"material_id": MATERIAL, "bound": False},
                    quantity=1,
                )
            )
    assert await service.remove_listing(SELLER, second.listing_id, now=NOW) == "blocked"
    async with database[1]() as session:
        assert (await _char(session, SELLER)).delivery_blocked
        assert (await session.scalar(select(BlockedDelivery))).quantity == 10


@pytest.mark.asyncio
async def test_only_the_owner_manages_a_listing(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database)
    assert await _code(service.edit_price(BUYER, listing.listing_id, 5, now=NOW)) == (
        "not_listing_owner"
    )
    assert await _code(service.remove_listing(BUYER, listing.listing_id, now=NOW)) == (
        "not_listing_owner"
    )


@pytest.mark.asyncio
async def test_concurrent_buyers_never_oversell(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=5)
    previews = [
        await service.prepare_purchase(actor, listing.listing_id, 3, now=NOW)
        for actor in (BUYER, THIRD)
    ]
    results = await asyncio.gather(
        *(
            service.confirm_purchase(actor, preview.purchase_id, now=NOW)
            for actor, preview in zip((BUYER, THIRD), previews, strict=True)
        ),
        return_exceptions=True,
    )
    assert sum(not isinstance(item, Exception) for item in results) == 1
    assert [item.code for item in results if isinstance(item, MarketError)] == [
        "insufficient_quantity"
    ]
    total = await _material_total(database, BUYER) + await _material_total(database, THIRD)
    assert total == 3


@pytest.mark.asyncio
async def test_purchase_and_price_edit_have_no_partial_order(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=5)
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 1, now=NOW)
    results = await asyncio.gather(
        service.confirm_purchase(BUYER, preview.purchase_id, now=NOW),
        service.edit_price(SELLER, listing.listing_id, 99, now=NOW),
        return_exceptions=True,
    )
    bought = not isinstance(results[0], Exception)
    assert await _crowns(database, BUYER) == (100_000 - 20 if bought else 100_000)
    assert await _material_total(database, BUYER) == (1 if bought else 0)


@pytest.mark.asyncio
async def test_remove_and_purchase_never_duplicate_the_stack(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database, quantity=5, stock=5)
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 5, now=NOW)
    await asyncio.gather(
        service.confirm_purchase(BUYER, preview.purchase_id, now=NOW),
        service.remove_listing(SELLER, listing.listing_id, now=NOW),
        return_exceptions=True,
    )
    assert await _material_total(database, BUYER) + await _material_total(database, SELLER) == 5


@pytest.mark.asyncio
async def test_promotion_has_thirty_minute_cooldown_and_revert(database):
    await _seed(database)
    service = _service(database)
    promotion = await service.promote(SELLER, now=NOW)
    assert promotion.previous_promoted_at is None
    assert await _code(service.promote(SELLER, now=NOW + timedelta(minutes=29))) == (
        "promotion_cooldown"
    )
    await service.revert_promotion(SELLER, promotion.previous_promoted_at)
    await service.promote(SELLER, now=NOW + timedelta(minutes=1))
    await service.promote(SELLER, now=NOW + timedelta(minutes=1) + PROMOTION_COOLDOWN)


@pytest.mark.asyncio
async def test_purchase_between_linked_accounts_is_flagged_only(database):
    await _seed(database)
    service = _service(database)
    async with database[1].begin() as session:
        session.add(AccountLink(account_a=SELLER, account_b=BUYER))
    listing = await _listing(service, database)
    result = await _buy(service, BUYER, listing.listing_id, 1)
    assert result.gross == 20
    async with database[1]() as session:
        flag = await session.scalar(select(AccountRiskFlag))
        assert flag.activity_kind == "market_purchase"


@pytest.mark.asyncio
async def test_deleted_owner_retires_the_code_and_closes_listings(database):
    await _seed(database)
    service = _service(database)
    listing = await _listing(service, database)
    code = (await service.my_shop(SELLER, now=NOW)).code
    preview = await service.prepare_purchase(BUYER, listing.listing_id, 1, now=NOW)
    async with database[1].begin() as session:
        await delete_character_owned_data(session, (await _char(session, SELLER)).id)
    assert await _code(service.confirm_purchase(BUYER, preview.purchase_id, now=NOW)) == (
        "listing_unavailable"
    )
    await service.run_maintenance(now=NOW)
    assert await _code(service.find_shop(BUYER, code, now=NOW)) == "shop_unavailable"
    async with database[1]() as session:
        shop = await session.scalar(select(PlayerShop).where(PlayerShop.code == code))
        assert shop is not None and shop.owner_character_id is None
        assert (await session.get(MarketListing, listing.listing_id)).status == "closed"
        assert (await session.get(MarketPurchase, preview.purchase_id)) is not None
