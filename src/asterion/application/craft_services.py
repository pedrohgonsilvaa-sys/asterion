"""Public Crafting Services: offer, order and delivery (GDD v1.6.0 §27.3, §49.10, §49.11).

A Service runs the artisan's Recipe on the client's materials. The client pays
the Service price plus the Recipe's Crafting fee; the artisan is never asked to
accept anything after publishing the offer. The order is a preview with the
exact terms and stacks; its confirmation is one atomic commit that revalidates
everything (§27.3) and either moves materials, Coroas and output together or
moves nothing. That single commit is the escrow: nothing stays held between
two transactions.

Lock order (every write follows it, which rules out deadlocks):
CraftServiceOffer -> Characters in ascending id order -> CraftServiceOrder ->
CharacterProfession -> material stacks. It matches CraftingService, which locks
the Character before its professions and materials, and MarketService, which
locks its own row before the Characters.

Author decisions for the GDD gaps are in domain/craft_services.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account import notification_enabled
from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.crafting import (
    CraftingErrorCode,
    CraftingRejected,
    CraftingService,
    IngredientPreview,
)
from asterion.application.guild_works import character_work_levels
from asterion.application.item_escrow import require_trading_character
from asterion.application.market import MarketService
from asterion.domain.craft_services import (
    SERVICE_DURATION,
    SERVICE_PREVIEW_TTL,
    SERVICE_SLOTS,
    guaranteed_secondaries,
    recipe_offerable,
    recipe_signature,
    service_title,
)
from asterion.domain.market import (
    BIGINT_MAX,
    MIN_UNIT_PRICE,
    fallback_shop_name,
    split_sale,
)
from asterion.domain.professions import (
    PROFESSION_BY_ID,
    RecipeDefinition,
    canonical_recipe,
    recipes_for,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterProfession,
    CraftServiceOffer,
    CraftServiceOrder,
    CraftServicePriceChange,
    PlayerShop,
    Unlock,
)

# Crafting reasons that mean "the client cannot take this order right now".
_CLIENT_REASONS = {
    CraftingErrorCode.CHARACTER_LEVEL: "client_level",
    CraftingErrorCode.MATERIALS: "materials",
    CraftingErrorCode.WRONG_LOCATION: "wrong_location",
    CraftingErrorCode.FOREGROUND: "foreground_locked",
    CraftingErrorCode.DELIVERY_BLOCKED: "delivery_blocked",
    CraftingErrorCode.INVENTORY_FULL: "inventory_full",
}


class CraftServiceError(ValueError):
    """A Service action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class OfferView:
    offer_id: UUID
    shop_id: UUID
    recipe_id: str
    recipe: RecipeDefinition | None
    title: str
    price: int
    revision: int
    status: str
    expires_at: datetime
    # None while the artisan still meets the Recipe; otherwise why it is suspended.
    suspended_reason: str | None
    executions: int

    @property
    def available(self) -> bool:
        return self.status == "active" and self.suspended_reason is None


@dataclass(frozen=True, slots=True)
class OfferableRecipe:
    recipe: RecipeDefinition
    reason: str | None


@dataclass(frozen=True, slots=True)
class MyServicesView:
    shop_id: UUID
    offers: tuple[OfferView, ...]
    expired: tuple[OfferView, ...]
    professions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ShopServicesView:
    shop_id: UUID
    shop_name: str
    is_owner: bool
    offers: tuple[OfferView, ...]


@dataclass(frozen=True, slots=True)
class OrderPreview:
    order_id: UUID
    offer_id: UUID
    recipe: RecipeDefinition
    title: str
    artisan_name: str
    price: int
    recipe_cost: int
    total: int
    item_level: int | None
    ingredients: tuple[IngredientPreview, ...]
    result_bound: bool
    secondaries: int | None
    delivery: str
    wallet: int


@dataclass(frozen=True, slots=True)
class OrderResult:
    order_id: UUID
    offer_id: UUID
    recipe: RecipeDefinition
    title: str
    client_name: str
    price: int
    recipe_cost: int
    fee: int
    net: int
    item_level: int | None
    delivery: str
    output_payload: dict
    artisan_telegram_id: int | None
    notify_artisan: bool
    already_committed: bool


class CraftServiceService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id
        self.crafting = CraftingService(sessions, server_id)
        self.market = MarketService(sessions, server_id)

    # ---------------------------------------------------------------- upkeep

    async def run_maintenance(self, *, now: datetime | None = None, limit: int = 200) -> int:
        """Close offers past their 7 days or without owner; drop stale previews."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            due = (
                await session.scalars(
                    select(CraftServiceOffer)
                    .join(PlayerShop, PlayerShop.id == CraftServiceOffer.shop_id)
                    .where(
                        CraftServiceOffer.server_id == self.server_id,
                        CraftServiceOffer.status == "active",
                        (CraftServiceOffer.expires_at <= now)
                        | PlayerShop.owner_character_id.is_(None),
                    )
                    .order_by(CraftServiceOffer.expires_at)
                    .limit(limit)
                    .with_for_update(of=CraftServiceOffer, skip_locked=True)
                )
            ).all()
            for offer in due:
                await self._close_if_due(session, offer, now)
            await session.execute(
                delete(CraftServiceOrder).where(
                    CraftServiceOrder.status == "preview", CraftServiceOrder.expires_at <= now
                )
            )
        return len(due)

    async def _close_if_due(self, session, offer: CraftServiceOffer, now: datetime) -> None:
        if offer.status != "active":
            return
        shop = await session.get(PlayerShop, offer.shop_id)
        if shop is None or shop.owner_character_id is None:
            offer.status = "closed"
            offer.closed_at = now
        elif offer.expires_at <= now:
            offer.status = "expired"
            offer.closed_at = now

    async def _settle_offer(self, offer_id: UUID, now: datetime) -> None:
        async with self.sessions.begin() as session:
            offer = await self._lock_offer(session, offer_id)
            if offer is not None:
                await self._close_if_due(session, offer, now)

    async def _settle_shop(self, shop_id: UUID, now: datetime) -> None:
        async with self.sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(CraftServiceOffer)
                    .where(
                        CraftServiceOffer.shop_id == shop_id,
                        CraftServiceOffer.status == "active",
                        CraftServiceOffer.expires_at <= now,
                    )
                    .with_for_update()
                )
            ).all()
            for offer in rows:
                await self._close_if_due(session, offer, now)

    # ---------------------------------------------------------------- artisan

    async def my_services(self, actor: int, *, now: datetime | None = None) -> MyServicesView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, lock=True)
            shop = await self.market._ensure_shop(session, character, now)
            shop_id = shop.id
        await self._settle_shop(shop_id, now)
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            active = (
                await session.scalars(
                    select(CraftServiceOffer)
                    .where(
                        CraftServiceOffer.shop_id == shop_id,
                        CraftServiceOffer.status == "active",
                    )
                    .order_by(CraftServiceOffer.created_at, CraftServiceOffer.id)
                )
            ).all()
            # An expired offer stays offered for republishing until it is republished;
            # the screen lists only the latest ones (a display limit, not a rule).
            expired = (
                await session.scalars(
                    select(CraftServiceOffer)
                    .where(
                        CraftServiceOffer.shop_id == shop_id,
                        CraftServiceOffer.status == "expired",
                    )
                    .order_by(CraftServiceOffer.expires_at.desc(), CraftServiceOffer.id)
                    .limit(SERVICE_SLOTS)
                )
            ).all()
            professions = tuple(
                row.profession_id for row in await self._profession_rows(session, character.id)
            )
            return MyServicesView(
                shop_id=shop_id,
                offers=tuple(
                    [await self._offer_view(session, row, character.id) for row in active]
                ),
                expired=tuple(
                    [await self._offer_view(session, row, character.id) for row in expired]
                ),
                professions=professions,
            )

    async def offerable_recipes(
        self, actor: int, profession_id: str
    ) -> tuple[OfferableRecipe, ...]:
        """Recipes the artisan could publish now; known special Recipes only."""
        if profession_id not in PROFESSION_BY_ID:
            raise CraftServiceError("unknown_profession")
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            rows = await self._profession_rows(session, character.id)
            row = next((item for item in rows if item.profession_id == profession_id), None)
            known = await self._known_unlocks(session, character.id)
            result = []
            for recipe in recipes_for(profession_id):
                if not recipe_offerable(recipe):
                    continue
                if recipe.unlock_id and recipe.unlock_id not in known:
                    continue
                result.append(OfferableRecipe(recipe, _artisan_reason(recipe, row, known)))
            return tuple(result)

    async def create_offer(
        self, actor: int, recipe_id: str, price: int, *, now: datetime | None = None
    ) -> OfferView:
        """§27.3: an offer exists only while Ofício, Receita and level are valid."""
        now = _utcnow(now)
        _check_price(price)
        recipe = canonical_recipe(recipe_id)
        if recipe is None or not recipe_offerable(recipe):
            raise CraftServiceError("recipe_unavailable")
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            shop_id = await session.scalar(
                select(PlayerShop.id).where(PlayerShop.owner_character_id == character.id)
            )
        if shop_id is not None:
            await self._settle_shop(shop_id, now)
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, lock=True)
            return await self._create_offer_locked(session, character, recipe, price, now)

    async def _create_offer_locked(self, session, character, recipe, price, now) -> OfferView:
        """The caller holds the Character lock, which serialises the slot count."""
        shop = await self.market._ensure_shop(session, character, now)
        rows = await self._profession_rows(session, character.id)
        row = next((item for item in rows if item.profession_id == recipe.profession_id), None)
        reason = _artisan_reason(recipe, row, await self._known_unlocks(session, character.id))
        if reason is not None:
            raise CraftServiceError(reason)
        active = await session.scalar(
            select(func.count(CraftServiceOffer.id)).where(
                CraftServiceOffer.shop_id == shop.id,
                CraftServiceOffer.status == "active",
                CraftServiceOffer.expires_at > now,
            )
        )
        if int(active or 0) >= SERVICE_SLOTS:
            raise CraftServiceError("service_slots_full")
        offer = CraftServiceOffer(
            shop_id=shop.id,
            server_id=self.server_id,
            recipe_id=recipe.recipe_id,
            profession_id=recipe.profession_id,
            recipe_signature=recipe_signature(recipe),
            price=price,
            service_offer_revision=1,
            gross_total=0,
            fee_total=0,
            executions=0,
            fee_bps=(await character_work_levels(session, character.id)).market_fee_bps,
            status="active",
            created_at=now,
            expires_at=now + SERVICE_DURATION,
        )
        session.add(offer)
        await session.flush()
        return await self._offer_view(session, offer, character.id)

    async def republish(
        self, actor: int, offer_id: UUID, *, now: datetime | None = None
    ) -> OfferView:
        """§27.3: an expired offer comes back only as a new 7-day offer."""
        now = _utcnow(now)
        await self._settle_offer(offer_id, now)
        async with self.sessions.begin() as session:
            offer = await self._lock_offer(session, offer_id)
            await self._require_owner(session, actor, offer)
            character = await self._require_character(session, actor, lock=True)
            if offer.status != "expired":
                raise CraftServiceError("offer_unavailable")
            recipe = canonical_recipe(offer.recipe_id)
            if recipe is None or not recipe_offerable(recipe):
                raise CraftServiceError("recipe_unavailable")
            view = await self._create_offer_locked(session, character, recipe, offer.price, now)
            offer.status = "republished"
            return view

    async def edit_price(
        self, actor: int, offer_id: UUID, new_price: int, *, now: datetime | None = None
    ) -> OfferView:
        """§27.3: new revision; previews of an older revision stop working.

        The offer row lock also waits for any order commit in progress.
        """
        now = _utcnow(now)
        _check_price(new_price)
        await self._settle_offer(offer_id, now)
        async with self.sessions.begin() as session:
            offer = await self._lock_offer(session, offer_id)
            character = await self._require_owner(session, actor, offer)
            if offer.status != "active":
                raise CraftServiceError("offer_unavailable")
            if new_price == offer.price:
                raise CraftServiceError("price_unchanged")
            old_price = offer.price
            offer.price = new_price
            offer.service_offer_revision += 1
            session.add(
                CraftServicePriceChange(
                    offer_id=offer.id,
                    owner_character_id=character.id,
                    old_price=old_price,
                    new_price=new_price,
                    service_offer_revision=offer.service_offer_revision,
                    changed_at=now,
                )
            )
            await session.flush()
            return await self._offer_view(session, offer, character.id)

    async def cancel_offer(
        self, actor: int, offer_id: UUID, *, now: datetime | None = None
    ) -> None:
        now = _utcnow(now)
        await self._settle_offer(offer_id, now)
        async with self.sessions.begin() as session:
            offer = await self._lock_offer(session, offer_id)
            await self._require_owner(session, actor, offer)
            if offer.status != "active":
                raise CraftServiceError("offer_unavailable")
            offer.status = "cancelled"
            offer.closed_at = now

    # ----------------------------------------------------------------- client

    async def shop_services(
        self, actor: int, shop_id: UUID, *, now: datetime | None = None
    ) -> ShopServicesView:
        """§27.3: Services are found only inside the artisan's Shop."""
        now = _utcnow(now)
        await self._settle_shop(shop_id, now)
        async with self.sessions() as session:
            viewer = await self._require_character(session, actor)
            shop = await session.get(PlayerShop, shop_id)
            if shop is None or shop.server_id != self.server_id or shop.owner_character_id is None:
                raise CraftServiceError("shop_unavailable")
            owner = await session.get(Character, shop.owner_character_id)
            rows = (
                await session.scalars(
                    select(CraftServiceOffer)
                    .where(
                        CraftServiceOffer.shop_id == shop.id,
                        CraftServiceOffer.status == "active",
                        CraftServiceOffer.expires_at > now,
                    )
                    .order_by(CraftServiceOffer.created_at, CraftServiceOffer.id)
                )
            ).all()
            views = [await self._offer_view(session, row, owner.id) for row in rows]
            is_owner = owner.id == viewer.id
            return ShopServicesView(
                shop_id=shop.id,
                shop_name=shop.public_name or fallback_shop_name(owner.name),
                is_owner=is_owner,
                # A suspended offer stays in the owner's list but not in the public one.
                offers=tuple(view for view in views if is_owner or view.available),
            )

    async def offer(self, actor: int, offer_id: UUID) -> OfferView:
        async with self.sessions() as session:
            await self._require_character(session, actor)
            offer = await session.get(CraftServiceOffer, offer_id)
            if offer is None or offer.server_id != self.server_id:
                raise CraftServiceError("offer_unavailable")
            shop = await session.get(PlayerShop, offer.shop_id)
            if shop is None or shop.owner_character_id is None:
                raise CraftServiceError("offer_unavailable")
            return await self._offer_view(session, offer, shop.owner_character_id)

    async def order_offer(self, actor: int, order_id: UUID) -> UUID:
        """The offer behind a preview, so a stale screen can show current terms."""
        async with self.sessions() as session:
            client = await self._require_character(session, actor)
            order = await session.get(CraftServiceOrder, order_id)
            if order is None or order.client_character_id != client.id:
                raise CraftServiceError("order_unavailable")
            return order.offer_id

    async def prepare_order(
        self, actor: int, offer_id: UUID, *, now: datetime | None = None
    ) -> OrderPreview:
        """Records the exact terms and stacks shown to the client. Moves nothing yet."""
        now = _utcnow(now)
        await self._settle_offer(offer_id, now)
        async with self.sessions.begin() as session:
            client = await self._require_character(session, actor)
            offer = await session.get(CraftServiceOffer, offer_id)
            if offer is None or offer.server_id != self.server_id or offer.status != "active":
                raise CraftServiceError("offer_unavailable")
            shop = await session.get(PlayerShop, offer.shop_id)
            if shop is None or shop.owner_character_id is None:
                raise CraftServiceError("offer_unavailable")
            if shop.owner_character_id == client.id:
                # §27.3: the artisan uses the normal Craft instead.
                raise CraftServiceError("own_service")
            artisan = await session.get(Character, shop.owner_character_id)
            recipe = await self._require_artisan(session, offer, artisan.id, lock=False)
            view = await self._client_view(session, client, artisan.id, recipe)
            self._require_client_ready(view)
            if client.crowns < offer.price + view.crown_cost:
                raise CraftServiceError("not_enough_crowns")
            order_id = uuid4()
            order = CraftServiceOrder(
                id=order_id,
                offer_id=offer.id,
                client_character_id=client.id,
                artisan_character_id=artisan.id,
                recipe_id=recipe.recipe_id,
                service_offer_revision=offer.service_offer_revision,
                price=offer.price,
                recipe_cost=view.crown_cost,
                item_level=view.item_level,
                preview_fingerprint=_fingerprint(client, offer, recipe, view),
                source_key=f"service:{order_id.hex}",
                seed=f"service:{order_id.hex}:materialization",
                status="preview",
                created_at=now,
                expires_at=now + SERVICE_PREVIEW_TTL,
            )
            session.add(order)
            await session.flush()
            return OrderPreview(
                order_id=order.id,
                offer_id=offer.id,
                recipe=recipe,
                title=service_title(recipe),
                artisan_name=artisan.name,
                price=offer.price,
                recipe_cost=view.crown_cost,
                total=offer.price + view.crown_cost,
                item_level=view.item_level,
                ingredients=view.ingredients,
                result_bound=view.result_bound,
                secondaries=guaranteed_secondaries(recipe),
                delivery=view.delivery,
                wallet=client.crowns,
            )

    async def confirm_order(
        self, actor: int, order_id: UUID, *, now: datetime | None = None
    ) -> OrderResult:
        """§27.3 commit. A repeated click returns the first result."""
        now = _utcnow(now)
        async with self.sessions() as session:
            client_id = await session.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            reference = await session.get(CraftServiceOrder, order_id)
            if reference is None or reference.client_character_id != client_id:
                raise CraftServiceError("order_unavailable")
            offer_id = reference.offer_id
            artisan_id = reference.artisan_character_id
        await self._settle_offer(offer_id, now)
        try:
            async with self.sessions.begin() as session:
                return await self._commit_order(
                    session, order_id, offer_id, client_id, artisan_id, now
                )
        except CraftingRejected as exc:
            raise CraftServiceError(_CLIENT_REASONS.get(exc.code, "order_stale")) from exc

    async def _commit_order(self, session, order_id, offer_id, client_id, artisan_id, now):
        offer = await self._lock_offer(session, offer_id)
        characters = await self._lock_characters(
            session, [item for item in (client_id, artisan_id) if item is not None]
        )
        order = await session.scalar(
            select(CraftServiceOrder)
            .where(CraftServiceOrder.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if order is None:
            raise CraftServiceError("order_unavailable")
        client = characters.get(client_id)
        artisan = characters.get(artisan_id)
        if order.status == "committed":
            return _order_result(order, client, artisan, False, already=True)
        if offer is None or offer.status != "active" or client is None or artisan is None:
            raise CraftServiceError("offer_unavailable")
        shop = await session.get(PlayerShop, offer.shop_id)
        if shop is None or shop.owner_character_id != artisan.id:
            raise CraftServiceError("offer_unavailable")
        if order.expires_at <= now:
            raise CraftServiceError("preview_expired")
        # §27.3: a preview of an older revision is never reread at the new price.
        if (
            order.service_offer_revision != offer.service_offer_revision
            or order.price != offer.price
        ):
            raise CraftServiceError("offer_updated")
        if await self.crafting._has_foreground(session, client.id):
            raise CraftServiceError("foreground_locked")
        # §27.3: Ofício, level and Receita of the artisan, revalidated under lock.
        recipe = await self._require_artisan(session, offer, artisan.id, lock=True)
        view = await self._client_view(session, client, artisan.id, recipe, lock=True)
        self._require_client_ready(view)
        if view.crown_cost != order.recipe_cost or view.item_level != order.item_level:
            raise CraftServiceError("offer_updated")
        if _fingerprint(client, offer, recipe, view) != order.preview_fingerprint:
            raise CraftServiceError("order_stale")
        total = order.price + order.recipe_cost
        if client.crowns < total:
            raise CraftServiceError("not_enough_crowns")
        split = split_sale(offer.gross_total, offer.fee_total, order.price, offer.fee_bps)
        if artisan.crowns + split.net > BIGINT_MAX:
            raise CraftServiceError("artisan_wallet_limit")

        client.crowns -= total
        material_rows = await self.crafting._material_rows(session, client.id, lock=True)
        await self.crafting._consume_materials(session, material_rows, view.ingredients)
        # Output, byproducts and leftovers all belong to the client (§27.3).
        output = await self.crafting._materialize_and_deliver(session, client, recipe, order, view)
        progress = await self.crafting.professions.progress_after_craft(
            session, artisan, recipe.profession_id, recipe.required_level, recipe.grade
        )
        artisan.crowns += split.net
        offer.gross_total += order.price
        offer.fee_total += split.fee
        offer.executions += 1
        output["service_details"] = {
            "artisan_character_id": str(artisan.id),
            "recipe_cost": order.recipe_cost,
            "item_level": order.item_level,
            "result_bound": view.result_bound,
            "pxp_gained": progress[2] if progress is not None else 0,
            "ingredients": [
                {
                    "material_id": item.material_id,
                    "required": item.required,
                    "consumed_stacks": [list(stack) for stack in item.consumed_stacks],
                }
                for item in view.ingredients
            ],
        }
        order.status = "committed"
        order.gross = order.price
        order.fee = split.fee
        order.net = split.net
        order.output_payload = output
        order.committed_at = now
        await record_linked_cooccurrence(
            session,
            server_id=self.server_id,
            activity_kind="craft_service",
            activity_reference=str(order.id),
            characters=[client, artisan],
            now=now,
        )
        notify = await notification_enabled(session, artisan.id, "market")
        await session.flush()
        return _order_result(order, client, artisan, notify, already=False)

    # ---------------------------------------------------------------- helpers

    async def _client_view(self, session, client, artisan_id, recipe, *, lock: bool = False):
        """The Craft view with the client's level, materials and place and the
        artisan's Ofício row; the Arquivo do Véu discount is the artisan's."""
        rows = await self._profession_rows(session, artisan_id, lock=lock)
        artisan_row = next(
            (item for item in rows if item.profession_id == recipe.profession_id), None
        )
        material_rows = await self.crafting._material_rows(session, client.id, lock=lock)
        location = await self.crafting._location(session, client.id, lock=lock)
        foreground = await self.crafting._has_foreground(session, client.id)
        discount = (await character_work_levels(session, artisan_id)).recipe_discount
        view = self.crafting._recipe_view(
            client, recipe, artisan_row, material_rows, location, foreground, discount
        )
        delivery = await self.crafting._delivery_destination(
            session, client, recipe, view.result_bound
        )
        if view.reason is None and delivery != "Inventário":
            view = replace(view, available=False, reason=CraftingErrorCode.INVENTORY_FULL)
        return replace(view, delivery=delivery)

    @staticmethod
    def _require_client_ready(view) -> None:
        if view.reason in (None, CraftingErrorCode.CROWNS):
            return  # Coroas are checked against price + Recipe fee by the caller.
        raise CraftServiceError(_CLIENT_REASONS.get(view.reason, "artisan_unavailable"))

    async def _require_artisan(self, session, offer, artisan_id, *, lock: bool):
        recipe = canonical_recipe(offer.recipe_id)
        if recipe is None or recipe_signature(recipe) != offer.recipe_signature:
            raise CraftServiceError("artisan_unavailable")
        rows = await self._profession_rows(session, artisan_id, lock=lock)
        row = next((item for item in rows if item.profession_id == recipe.profession_id), None)
        known = await self._known_unlocks(session, artisan_id)
        if _artisan_reason(recipe, row, known) is not None:
            raise CraftServiceError("artisan_unavailable")
        return recipe

    async def _offer_view(self, session, offer: CraftServiceOffer, artisan_id) -> OfferView:
        recipe = canonical_recipe(offer.recipe_id)
        reason = None
        if recipe is None or recipe_signature(recipe) != offer.recipe_signature:
            reason = "recipe_changed"
        else:
            rows = await self._profession_rows(session, artisan_id)
            row = next((item for item in rows if item.profession_id == recipe.profession_id), None)
            reason = _artisan_reason(recipe, row, await self._known_unlocks(session, artisan_id))
        return OfferView(
            offer_id=offer.id,
            shop_id=offer.shop_id,
            recipe_id=offer.recipe_id,
            recipe=recipe,
            title=service_title(recipe) if recipe is not None else offer.recipe_id,
            price=offer.price,
            revision=offer.service_offer_revision,
            status=offer.status,
            expires_at=offer.expires_at,
            suspended_reason=reason,
            executions=offer.executions,
        )

    async def _lock_offer(self, session, offer_id: UUID) -> CraftServiceOffer | None:
        return await session.scalar(
            select(CraftServiceOffer)
            .where(CraftServiceOffer.id == offer_id, CraftServiceOffer.server_id == self.server_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def _require_owner(self, session, actor: int, offer) -> Character:
        if offer is None or offer.server_id != self.server_id:
            raise CraftServiceError("offer_unavailable")
        character = await self._require_character(session, actor)
        shop = await session.get(PlayerShop, offer.shop_id)
        if shop is None or shop.owner_character_id != character.id:
            raise CraftServiceError("not_offer_owner")
        return character

    async def _lock_characters(
        self, session, character_ids: Sequence[UUID]
    ) -> dict[UUID | None, Character]:
        rows = (
            await session.scalars(
                select(Character)
                .where(Character.id.in_(character_ids))
                .order_by(Character.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        return {row.id: row for row in rows}

    @staticmethod
    async def _profession_rows(session, character_id, *, lock: bool = False):
        statement = (
            select(CharacterProfession)
            .where(CharacterProfession.character_id == character_id)
            .order_by(CharacterProfession.slot)
        )
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return list((await session.scalars(statement)).all())

    @staticmethod
    async def _known_unlocks(session, character_id) -> set[str]:
        return set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character_id)
                )
            ).all()
        )

    async def _require_character(self, session, actor: int, *, lock: bool = False) -> Character:
        return await require_trading_character(
            session, actor, self.server_id, lock=lock, error=CraftServiceError
        )


def _artisan_reason(recipe: RecipeDefinition, row, known: set[str]) -> str | None:
    if not recipe_offerable(recipe):
        return "recipe_unavailable"
    if recipe.unlock_id and recipe.unlock_id not in known:
        return "recipe_not_known"
    if row is None:
        return "profession_inactive"
    if row.level < recipe.required_level:
        return "profession_level"
    return None


def _check_price(price: int) -> None:
    if price < MIN_UNIT_PRICE:
        raise CraftServiceError("invalid_price")
    if price > BIGINT_MAX // 2:
        raise CraftServiceError("price_out_of_range")


def _fingerprint(client, offer, recipe, view) -> str:
    """What the client saw. Coroas are checked directly, and the artisan's PXP is
    left out on purpose: another client's order must not stale this preview."""
    relevant = {item.material_id for item in view.ingredients}
    payload = {
        "client": str(client.id),
        "level": client.level,
        "delivery_blocked": bool(client.delivery_blocked),
        "offer": str(offer.id),
        "revision": offer.service_offer_revision,
        "price": offer.price,
        "recipe": recipe.recipe_id,
        "recipe_cost": view.crown_cost,
        "item_level": view.item_level,
        "result_bound": view.result_bound,
        "ingredients": [
            (item.material_id, item.required, [list(stack) for stack in item.consumed_stacks])
            for item in view.ingredients
            if item.material_id in relevant
        ],
    }
    return sha256(dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _order_result(order, client, artisan, notify: bool, *, already: bool) -> OrderResult:
    recipe = canonical_recipe(order.recipe_id)
    payload = dict(order.output_payload or {})
    return OrderResult(
        order_id=order.id,
        offer_id=order.offer_id,
        recipe=recipe,
        title=service_title(recipe) if recipe is not None else order.recipe_id,
        client_name=client.name if client is not None else "",
        price=order.price,
        recipe_cost=order.recipe_cost,
        fee=order.fee or 0,
        net=order.net or 0,
        item_level=order.item_level,
        delivery=str(payload.get("delivery", "Inventário")),
        output_payload=payload,
        artisan_telegram_id=artisan.telegram_id if artisan is not None else None,
        notify_artisan=notify,
        already_committed=already,
    )


def _utcnow(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)
