"""PostgreSQL integration tests for public Crafting Services (GDD v1.6.0 §27.3, §49.10)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.craft_services import CraftServiceError, CraftServiceService
from asterion.domain.craft_services import SERVICE_DURATION
from asterion.domain.professions import canonical_recipe, recipe_materials
from asterion.infrastructure.db.models import (
    Account,
    AccountLink,
    AccountRiskFlag,
    Character,
    CharacterProfession,
    ConsumableStack,
    CraftServiceOffer,
    CraftServiceOrder,
    CraftServicePriceChange,
    EquipmentItem,
    MaterialStack,
    WorldState,
)

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
ARTISAN, CLIENT, OTHER = 841001, 841002, 841003
HEAL = "recipe.tdo.alchemist.heal"
WEAPON = "recipe.tdo.blacksmith.walker_weapon.comum"
CROWNS = 10_000


async def _seed(database) -> None:
    async with database[1].begin() as session:
        for actor, name, level in (
            (ARTISAN, "Artesao", 20),
            (CLIENT, "Cliente", 7),
            (OTHER, "Outro", 12),
        ):
            session.add(Account(telegram_id=actor))
            character = Character(
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
                crowns=CROWNS,
                level=level,
            )
            session.add(character)
            await session.flush()
            session.add(
                WorldState(
                    character_id=character.id, region="Terras do Ocaso", location="Refúgio do Ocaso"
                )
            )
        artisan = await _char(session, ARTISAN)
        session.add_all(
            [
                CharacterProfession(
                    character_id=artisan.id, slot="primary", profession_id="alchemist", level=5
                ),
                CharacterProfession(
                    character_id=artisan.id, slot="secondary", profession_id="blacksmith", level=3
                ),
            ]
        )


async def _char(session, actor: int) -> Character:
    return await session.scalar(select(Character).where(Character.telegram_id == actor))


async def _give_recipe_materials(database, actor: int, recipe_id: str, times: int = 1) -> None:
    recipe = canonical_recipe(recipe_id)
    async with database[1].begin() as session:
        character = await _char(session, actor)
        for requirement in recipe_materials(recipe, character.level):
            session.add(
                MaterialStack(
                    character_id=character.id,
                    material_id=requirement.material_id,
                    quantity=requirement.quantity * times,
                    bound=False,
                )
            )


def _service(database) -> CraftServiceService:
    return CraftServiceService(database[1], "ocaso")


async def _code(awaitable) -> str:
    with pytest.raises(CraftServiceError) as error:
        await awaitable
    return error.value.code


async def _crowns(database, actor: int) -> int:
    async with database[1]() as session:
        return (await _char(session, actor)).crowns


@pytest.mark.asyncio
async def test_service_runs_on_client_materials_and_pays_artisan_once(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 100, now=NOW)
    assert offer.available and offer.revision == 1

    shop = await service.shop_services(CLIENT, offer.shop_id, now=NOW)
    assert [row.offer_id for row in shop.offers] == [offer.offer_id]
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    assert preview.price == 100 and preview.total == 100 + preview.recipe_cost
    assert preview.recipe_cost > 0 and preview.delivery == "Inventário"

    result = await service.confirm_order(CLIENT, preview.order_id, now=NOW)
    again = await service.confirm_order(CLIENT, preview.order_id, now=NOW)
    assert not result.already_committed and again.already_committed
    # §49.10: 5% of the payment to the artisan; the Recipe fee is the client's.
    assert (result.fee, result.net) == (5, 95)
    assert await _crowns(database, CLIENT) == CROWNS - 100 - preview.recipe_cost
    assert await _crowns(database, ARTISAN) == CROWNS + 95
    async with database[1]() as session:
        client = await _char(session, CLIENT)
        artisan = await _char(session, ARTISAN)
        stack = await session.scalar(
            select(ConsumableStack).where(ConsumableStack.character_id == client.id)
        )
        assert stack is not None and stack.quantity == 1
        left = await session.scalar(
            select(func.coalesce(func.sum(MaterialStack.quantity), 0)).where(
                MaterialStack.character_id == client.id
            )
        )
        assert left == 0
        row = await session.scalar(
            select(CharacterProfession).where(
                CharacterProfession.character_id == artisan.id,
                CharacterProfession.profession_id == "alchemist",
            )
        )
        assert row.pxp > 0
        stored = await session.get(CraftServiceOffer, offer.offer_id)
        assert (stored.gross_total, stored.fee_total, stored.executions) == (100, 5, 1)


@pytest.mark.asyncio
async def test_two_clients_racing_each_get_one_execution_and_fees_accumulate(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL)
    await _give_recipe_materials(database, OTHER, HEAL)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 30, now=NOW)
    first = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    second = await service.prepare_order(OTHER, offer.offer_id, now=NOW)
    results = await asyncio.gather(
        service.confirm_order(CLIENT, first.order_id, now=NOW),
        service.confirm_order(OTHER, second.order_id, now=NOW),
    )
    # floor(30×5%)=1, then floor(60×5%)−1=2: splitting never dodges the rounding.
    assert sorted(item.fee for item in results) == [1, 2]
    assert await _crowns(database, ARTISAN) == CROWNS + 57
    async with database[1]() as session:
        stored = await session.get(CraftServiceOffer, offer.offer_id)
        assert (stored.gross_total, stored.fee_total, stored.executions) == (60, 3, 2)


@pytest.mark.asyncio
async def test_double_confirm_of_one_order_executes_once(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL, times=2)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 40, now=NOW)
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    results = await asyncio.gather(
        service.confirm_order(CLIENT, preview.order_id, now=NOW),
        service.confirm_order(CLIENT, preview.order_id, now=NOW),
    )
    assert sorted(item.already_committed for item in results) == [False, True]
    assert await _crowns(database, CLIENT) == CROWNS - 40 - preview.recipe_cost
    async with database[1]() as session:
        client = await _char(session, CLIENT)
        stack = await session.scalar(
            select(ConsumableStack).where(ConsumableStack.character_id == client.id)
        )
        assert stack.quantity == 1


@pytest.mark.asyncio
async def test_price_edit_bumps_revision_and_invalidates_old_previews(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 50, now=NOW)
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    edited = await service.edit_price(ARTISAN, offer.offer_id, 80, now=NOW)
    assert (edited.price, edited.revision) == (80, 2)
    assert await _code(service.confirm_order(CLIENT, preview.order_id, now=NOW)) == (
        "offer_updated"
    )
    assert await _crowns(database, CLIENT) == CROWNS
    assert await _code(service.edit_price(CLIENT, offer.offer_id, 10, now=NOW)) == (
        "not_offer_owner"
    )
    fresh = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    assert (await service.confirm_order(CLIENT, fresh.order_id, now=NOW)).price == 80
    async with database[1]() as session:
        change = await session.scalar(select(CraftServicePriceChange))
        assert (change.old_price, change.new_price, change.service_offer_revision) == (50, 80, 2)


@pytest.mark.asyncio
async def test_commit_revalidates_artisan_materials_and_offer(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 20, now=NOW)

    # The artisan loses the Ofício level after the preview.
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    async with database[1].begin() as session:
        artisan = await _char(session, ARTISAN)
        row = await session.scalar(
            select(CharacterProfession).where(
                CharacterProfession.character_id == artisan.id,
                CharacterProfession.profession_id == "alchemist",
            )
        )
        row.profession_id = "jeweler"
    assert await _code(service.confirm_order(CLIENT, preview.order_id, now=NOW)) == (
        "artisan_unavailable"
    )
    shop = await service.shop_services(CLIENT, offer.shop_id, now=NOW)
    assert shop.offers == ()  # suspended offers leave the public list
    async with database[1].begin() as session:
        artisan = await _char(session, ARTISAN)
        row = await session.scalar(
            select(CharacterProfession).where(
                CharacterProfession.character_id == artisan.id,
                CharacterProfession.profession_id == "jeweler",
            )
        )
        row.profession_id = "alchemist"

    # The client's materials change after the preview.
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    async with database[1].begin() as session:
        client = await _char(session, CLIENT)
        stack = await session.scalar(
            select(MaterialStack).where(MaterialStack.character_id == client.id).limit(1)
        )
        stack.quantity -= 1
    assert await _code(service.confirm_order(CLIENT, preview.order_id, now=NOW)) in {
        "materials",
        "order_stale",
    }

    # The offer is cancelled after the preview.
    await _give_recipe_materials(database, CLIENT, HEAL)
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    await service.cancel_offer(ARTISAN, offer.offer_id, now=NOW)
    assert await _code(service.confirm_order(CLIENT, preview.order_id, now=NOW)) == (
        "offer_unavailable"
    )
    assert await _crowns(database, CLIENT) == CROWNS
    assert await _crowns(database, ARTISAN) == CROWNS


@pytest.mark.asyncio
async def test_offer_rules_slots_own_service_and_artisan_requirements(database):
    await _seed(database)
    service = _service(database)
    assert await _code(service.create_offer(OTHER, HEAL, 10, now=NOW)) == "profession_inactive"
    assert await _code(service.create_offer(ARTISAN, HEAL, 0, now=NOW)) == "invalid_price"
    first = await service.create_offer(ARTISAN, HEAL, 10, now=NOW)
    await service.create_offer(ARTISAN, HEAL, 11, now=NOW)
    await service.create_offer(ARTISAN, WEAPON, 12, now=NOW)
    # §49.10: 3 Service offers, apart from the 6 item listings.
    assert await _code(service.create_offer(ARTISAN, WEAPON, 13, now=NOW)) == ("service_slots_full")
    await _give_recipe_materials(database, ARTISAN, HEAL)
    assert await _code(service.prepare_order(ARTISAN, first.offer_id, now=NOW)) == "own_service"
    mine = await service.my_services(ARTISAN, now=NOW)
    assert len(mine.offers) == 3 and set(mine.professions) == {"alchemist", "blacksmith"}


@pytest.mark.asyncio
async def test_client_must_be_at_a_safe_crafting_location(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 10, now=NOW)
    async with database[1].begin() as session:
        client = await _char(session, CLIENT)
        world = await session.get(WorldState, client.id)
        world.location = "Diques Rubros"
    assert await _code(service.prepare_order(CLIENT, offer.offer_id, now=NOW)) == ("wrong_location")


@pytest.mark.asyncio
async def test_offer_expires_after_seven_days_and_can_be_republished(database):
    await _seed(database)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 10, now=NOW)
    later = NOW + SERVICE_DURATION
    assert (await service.shop_services(CLIENT, offer.shop_id, now=later)).offers == ()
    mine = await service.my_services(ARTISAN, now=later)
    assert mine.offers == () and [row.offer_id for row in mine.expired] == [offer.offer_id]
    renewed = await service.republish(ARTISAN, offer.offer_id, now=later)
    assert renewed.offer_id != offer.offer_id and renewed.expires_at == later + SERVICE_DURATION
    assert await _code(service.republish(ARTISAN, offer.offer_id, now=later)) == (
        "offer_unavailable"
    )
    async with database[1]() as session:
        assert (await session.get(CraftServiceOffer, offer.offer_id)).status == "republished"


@pytest.mark.asyncio
async def test_equipment_service_uses_client_level_and_shows_guarantees(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, WEAPON)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, WEAPON, 25, now=NOW)
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    # §49.11: in a Service the recipient is the client (level 7, Grade I cap 10).
    assert preview.item_level == 7 and preview.secondaries == 0
    await service.confirm_order(CLIENT, preview.order_id, now=NOW)
    async with database[1]() as session:
        client = await _char(session, CLIENT)
        item = await session.scalar(
            select(EquipmentItem).where(EquipmentItem.character_id == client.id)
        )
        assert item is not None and item.item_level == 7


@pytest.mark.asyncio
async def test_linked_accounts_are_flagged_by_service(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL)
    async with database[1].begin() as session:
        session.add(AccountLink(account_a=ARTISAN, account_b=CLIENT))
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 10, now=NOW)
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    await service.confirm_order(CLIENT, preview.order_id, now=NOW)
    async with database[1]() as session:
        flag = await session.scalar(select(AccountRiskFlag))
        assert flag is not None and flag.activity_kind == "craft_service"


@pytest.mark.asyncio
async def test_deleted_artisan_closes_offers_and_keeps_orders(database):
    await _seed(database)
    await _give_recipe_materials(database, CLIENT, HEAL)
    service = _service(database)
    offer = await service.create_offer(ARTISAN, HEAL, 10, now=NOW)
    preview = await service.prepare_order(CLIENT, offer.offer_id, now=NOW)
    await service.confirm_order(CLIENT, preview.order_id, now=NOW)
    async with database[1].begin() as session:
        artisan = await _char(session, ARTISAN)
        await delete_character_owned_data(session, artisan.id)
    assert await service.run_maintenance(now=NOW + timedelta(minutes=1)) == 1
    async with database[1]() as session:
        assert (await session.get(CraftServiceOffer, offer.offer_id)).status == "closed"
        order = await session.get(CraftServiceOrder, preview.order_id)
        assert order.status == "committed" and order.artisan_character_id is None
