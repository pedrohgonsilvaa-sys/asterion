"""Personal Shops, listings in escrow and purchases.

Sources: GDD Estrutural v1.6.0 §28, §43.2, §49.10, §49.18 and §55.4.

Lock order (every write follows it, which rules out deadlocks):
MarketListing -> Characters in ascending id order -> MarketPurchase.
A flow that creates a listing locks only its Character, because the new row has
no competitor; the count of active listings is serialised by that lock.

Character deletion needs no hook here. The owner FK is ON DELETE SET NULL, so
the Shop keeps its Code forever (§28.3) and `run_maintenance` closes the listings
of a Shop without owner. Escrowed items of a deleted character end with it.

Upkeep (listings past their 7 days) runs in its own transaction before each
action, because a rejected action rolls its transaction back.

Author decisions (2026-11-08) for points the GDD leaves open:
- no Crowns wallet cap yet, so a sale always credits the seller in full and
  Crédito Financeiro Pendente waits for that number;
- Market is available after the Prologue;
- public Services (§27.3) are a later stage.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account import notification_enabled
from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.guild_works import character_work_levels
from asterion.application.item_escrow import (
    EscrowError,
    NegotiableEntry,
    deliver_to_inventory,
    is_mythic,
    negotiable_entries,
    require_trading_character,
    return_to_owner,
    take_from_inventory,
)
from asterion.application.legacy_mark_effects import listing_slots, promotion_cooldown
from asterion.domain.market import (
    BIGINT_MAX,
    LISTING_DURATION,
    LISTING_SLOTS,
    MIN_UNIT_PRICE,
    PURCHASE_PREVIEW_TTL,
    SEARCH_BURST_LIMIT,
    SEARCH_BURST_WINDOW,
    SEARCH_LIMIT_PER_MINUTE,
    SEARCH_LIMIT_WINDOW,
    MarketTextError,
    fallback_shop_name,
    generate_shop_code,
    normalize_shop_code,
    promotion_summary,
    split_sale,
    validate_shop_description,
    validate_shop_name,
)
from asterion.infrastructure.db.models import (
    Character,
    MarketListing,
    MarketPriceChange,
    MarketPurchase,
    PlayerShop,
    ShopSearchAttempt,
)

_CODE_ATTEMPTS = 8


class MarketError(ValueError):
    """A Market action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ListingView:
    listing_id: UUID
    kind: str
    title: str
    rarity: str | None
    remaining: int
    initial: int
    unit_price: int
    terms_version: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ShopView:
    shop_id: UUID
    code: str
    name: str
    has_custom_name: bool
    description: str | None
    is_owner: bool
    listings: tuple[ListingView, ...]
    promotion_available_at: datetime | None
    listing_slots: int = LISTING_SLOTS


@dataclass(frozen=True, slots=True)
class PurchasePreview:
    purchase_id: UUID
    listing_id: UUID
    title: str
    quantity: int
    unit_price: int
    total: int
    mythic: bool
    wallet: int


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    purchase_id: UUID
    listing_id: UUID
    title: str
    quantity: int
    unit_price: int
    gross: int
    fee: int
    net: int
    remaining: int
    seller_telegram_id: int | None
    notify_seller: bool
    already_committed: bool


@dataclass(frozen=True, slots=True)
class Promotion:
    shop_name: str
    owner_name: str
    code: str
    offers: int
    summary: str | None
    previous_promoted_at: datetime | None


class MarketService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    # ---------------------------------------------------------------- upkeep

    async def run_maintenance(self, *, now: datetime | None = None, limit: int = 100) -> int:
        """Close listings past their term or without owner; safe to call often."""
        now = _utcnow(now)
        async with self.sessions() as session:
            due = (
                await session.scalars(
                    select(MarketListing.id)
                    .join(PlayerShop, PlayerShop.id == MarketListing.shop_id)
                    .where(
                        MarketListing.server_id == self.server_id,
                        MarketListing.status == "active",
                        (MarketListing.expires_at <= now) | PlayerShop.owner_character_id.is_(None),
                    )
                    .order_by(MarketListing.expires_at)
                    .limit(limit)
                )
            ).all()
        for listing_id in due:
            await self._settle_listing(listing_id, now)
        async with self.sessions.begin() as session:
            await session.execute(
                delete(MarketPurchase).where(
                    MarketPurchase.status == "preview", MarketPurchase.expires_at <= now
                )
            )
        return len(due)

    async def _settle_listing(self, listing_id: UUID, now: datetime) -> None:
        async with self.sessions.begin() as session:
            listing = await self._lock_listing(session, listing_id)
            if listing is None or listing.status != "active":
                return
            shop = await session.get(PlayerShop, listing.shop_id)
            if shop is None or shop.owner_character_id is None:
                listing.status = "closed"
                listing.closed_at = now
                return
            if listing.expires_at > now:
                return
            owner = await self._lock_character_id(session, shop.owner_character_id)
            await self._return_listing(session, listing, owner, "expired", now)

    async def _settle_shop(self, shop_id: UUID, now: datetime) -> None:
        async with self.sessions() as session:
            due = (
                await session.scalars(
                    select(MarketListing.id).where(
                        MarketListing.shop_id == shop_id,
                        MarketListing.status == "active",
                        MarketListing.expires_at <= now,
                    )
                )
            ).all()
        for listing_id in due:
            await self._settle_listing(listing_id, now)

    async def _return_listing(self, session, listing, owner, status, now) -> None:
        if listing.remaining_quantity > 0:
            await return_to_owner(
                session,
                owner,
                listing.item_kind,
                listing.item_snapshot,
                listing.remaining_quantity,
                f"market:return:{listing.id}",
            )
        listing.status = status
        listing.closed_at = now

    # ------------------------------------------------------------------ shops

    async def my_shop(self, actor: int, *, now: datetime | None = None) -> ShopView:
        """§28.7 Minha Loja; the Shop exists from the first time it is needed."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, lock=True)
            shop = await self._ensure_shop(session, character, now)
            shop_id = shop.id
        await self._settle_shop(shop_id, now)
        return await self._read_shop(shop_id, actor, now)

    async def find_shop(
        self, actor: int, raw_code: str, *, now: datetime | None = None
    ) -> ShopView:
        """§28.4 Buscar Loja. The Code only locates and shows a public Shop."""
        now = _utcnow(now)
        code = normalize_shop_code(raw_code)
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, lock=True)
            await self._consume_search_quota(session, character.id, now)
            shop_id = None
            if code is not None:
                shop_id = await session.scalar(
                    select(PlayerShop.id).where(
                        PlayerShop.code == code,
                        PlayerShop.server_id == self.server_id,
                        PlayerShop.owner_character_id.is_not(None),
                    )
                )
        if shop_id is None:
            raise MarketError("shop_unavailable")
        await self._settle_shop(shop_id, now)
        return await self._read_shop(shop_id, actor, now)

    async def open_shop(
        self, actor: int, shop_id: UUID, *, now: datetime | None = None
    ) -> ShopView:
        now = _utcnow(now)
        await self._settle_shop(shop_id, now)
        return await self._read_shop(shop_id, actor, now)

    async def _read_shop(self, shop_id: UUID, actor: int, now: datetime) -> ShopView:
        async with self.sessions() as session:
            viewer = await self._require_character(session, actor)
            shop = await session.get(PlayerShop, shop_id)
            if shop is None or shop.server_id != self.server_id or shop.owner_character_id is None:
                raise MarketError("shop_unavailable")
            owner_name = await session.scalar(
                select(Character.name).where(Character.id == shop.owner_character_id)
            )
            rows = (
                await session.scalars(
                    select(MarketListing)
                    .where(
                        MarketListing.shop_id == shop.id,
                        MarketListing.status == "active",
                        MarketListing.expires_at > now,
                    )
                    .order_by(MarketListing.created_at, MarketListing.id)
                )
            ).all()
            is_owner = shop.owner_character_id == viewer.id
            available_at = None
            if is_owner and shop.last_promoted_at is not None:
                cooldown = await promotion_cooldown(session, viewer.id)
                ready = shop.last_promoted_at + cooldown
                available_at = ready if ready > now else None
            return ShopView(
                shop_id=shop.id,
                code=shop.code,
                name=shop.public_name or fallback_shop_name(owner_name or ""),
                has_custom_name=shop.public_name is not None,
                description=shop.description,
                is_owner=is_owner,
                listings=tuple(_listing_view(row) for row in rows),
                promotion_available_at=available_at,
                listing_slots=await listing_slots(session, shop.owner_character_id),
            )

    async def edit_shop(
        self,
        actor: int,
        *,
        name: str | None = None,
        description: str | None = None,
        clear_name: bool = False,
        clear_description: bool = False,
        now: datetime | None = None,
    ) -> ShopView:
        """§28.5 changes only the public presentation; Code and id never move."""
        now = _utcnow(now)
        try:
            clean_name = validate_shop_name(name) if name is not None else None
            clean_description = (
                validate_shop_description(description) if description is not None else None
            )
        except MarketTextError as exc:
            raise MarketError(exc.code) from exc
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, lock=True)
            shop = await self._ensure_shop(session, character, now)
            if clean_name is not None:
                shop.public_name = clean_name
            elif clear_name:
                shop.public_name = None
            if clean_description is not None:
                shop.description = clean_description
            elif clear_description:
                shop.description = None
            shop_id = shop.id
        return await self._read_shop(shop_id, actor, now)

    async def promote(self, actor: int, *, now: datetime | None = None) -> Promotion:
        """§28.8 snapshot for the Community, under the §49.18 cooldown."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, lock=True)
            shop = await self._ensure_shop(session, character, now)
            previous = shop.last_promoted_at
            cooldown = await promotion_cooldown(session, character.id)
            if previous is not None and previous + cooldown > now:
                raise MarketError("promotion_cooldown")
            shop.last_promoted_at = now
            offers = await self._active_listings(session, shop.id, now)
            return Promotion(
                shop_name=shop.public_name or fallback_shop_name(character.name),
                owner_name=character.name,
                code=shop.code,
                offers=offers,
                summary=promotion_summary(shop.description),
                previous_promoted_at=previous,
            )

    async def revert_promotion(self, actor: int, previous: datetime | None) -> None:
        """A post Telegram refused must not cost the player the cooldown."""
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, lock=True)
            shop = await self._ensure_shop(session, character, _utcnow(None))
            shop.last_promoted_at = previous

    # --------------------------------------------------------------- listings

    async def sources(self, actor: int, kind: str) -> tuple[NegotiableEntry, ...]:
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            try:
                return await negotiable_entries(session, character.id, kind)
            except EscrowError as exc:
                raise MarketError(exc.code) from exc

    async def create_listing(
        self,
        actor: int,
        kind: str,
        source_id: UUID,
        quantity: int,
        unit_price: int,
        *,
        mythic_confirmed: bool = False,
        now: datetime | None = None,
    ) -> ListingView:
        """§28.10: the item enters escrow in the same commit that creates the listing."""
        now = _utcnow(now)
        _check_price(unit_price, quantity)
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            shop_id = await session.scalar(
                select(PlayerShop.id).where(PlayerShop.owner_character_id == character.id)
            )
        if shop_id is not None:
            await self._settle_shop(shop_id, now)
        async with self.sessions.begin() as session:
            character = await self._require_character(session, actor, guard=True)
            shop = await self._ensure_shop(session, character, now)
            slots = await listing_slots(session, character.id)
            if await self._active_listings(session, shop.id, now) >= slots:
                raise MarketError("listing_slots_full")
            try:
                taken = await take_from_inventory(session, character.id, kind, source_id, quantity)
            except EscrowError as exc:
                raise MarketError(exc.code) from exc
            if is_mythic(taken.rarity) and not mythic_confirmed:
                raise MarketError("mythic_confirmation_required")
            listing = MarketListing(
                shop_id=shop.id,
                server_id=self.server_id,
                item_kind=taken.kind,
                title=taken.title,
                rarity=taken.rarity,
                item_snapshot=taken.snapshot,
                initial_quantity=taken.quantity,
                remaining_quantity=taken.quantity,
                unit_price=unit_price,
                terms_version=1,
                gross_sold_total=0,
                fee_charged_total=0,
                fee_bps=(await character_work_levels(session, character.id)).market_fee_bps,
                status="active",
                created_at=now,
                expires_at=now + LISTING_DURATION,
            )
            session.add(listing)
            await session.flush()
            return _listing_view(listing)

    async def listing(self, actor: int, listing_id: UUID) -> ListingView:
        async with self.sessions() as session:
            await self._require_character(session, actor)
            listing = await session.get(MarketListing, listing_id)
            if listing is None or listing.server_id != self.server_id or listing.status != "active":
                raise MarketError("listing_unavailable")
            return _listing_view(listing)

    async def edit_price(
        self, actor: int, listing_id: UUID, new_price: int, *, now: datetime | None = None
    ) -> ListingView:
        """§28.11: new terms version; confirmations of the old one stop working."""
        now = _utcnow(now)
        await self._settle_listing(listing_id, now)
        async with self.sessions.begin() as session:
            listing = await self._lock_listing(session, listing_id)
            character = await self._require_owner(session, actor, listing)
            if listing.status != "active":
                raise MarketError("listing_unavailable")
            _check_price(new_price, listing.remaining_quantity)
            if new_price == listing.unit_price:
                raise MarketError("price_unchanged")
            old_price = listing.unit_price
            listing.unit_price = new_price
            listing.terms_version += 1
            session.add(
                MarketPriceChange(
                    listing_id=listing.id,
                    owner_character_id=character.id,
                    old_price=old_price,
                    new_price=new_price,
                    terms_version=listing.terms_version,
                    changed_at=now,
                )
            )
            await session.flush()
            return _listing_view(listing)

    async def remove_listing(
        self, actor: int, listing_id: UUID, *, now: datetime | None = None
    ) -> str:
        """§28.13: returns only what remains. Answers where the item went."""
        now = _utcnow(now)
        await self._settle_listing(listing_id, now)
        async with self.sessions.begin() as session:
            listing = await self._lock_listing(session, listing_id)
            await self._require_owner(session, actor, listing)
            if listing.status != "active":
                raise MarketError("listing_unavailable")
            owner = await self._lock_character_for_actor(session, actor)
            destination = await return_to_owner(
                session,
                owner,
                listing.item_kind,
                listing.item_snapshot,
                listing.remaining_quantity,
                f"market:return:{listing.id}",
            )
            listing.status = "removed"
            listing.closed_at = now
            return destination

    # -------------------------------------------------------------- purchases

    async def purchase_listing(self, actor: int, purchase_id: UUID) -> UUID:
        """The listing behind a preview, so a stale screen can show current terms."""
        async with self.sessions() as session:
            buyer = await self._require_character(session, actor)
            purchase = await session.get(MarketPurchase, purchase_id)
            if purchase is None or purchase.buyer_character_id != buyer.id:
                raise MarketError("purchase_unavailable")
            return purchase.listing_id

    async def prepare_purchase(
        self, actor: int, listing_id: UUID, quantity: int, *, now: datetime | None = None
    ) -> PurchasePreview:
        """Records the terms shown to the buyer. Moves nothing yet."""
        now = _utcnow(now)
        await self._settle_listing(listing_id, now)
        async with self.sessions.begin() as session:
            buyer = await self._require_character(session, actor)
            listing = await session.get(MarketListing, listing_id)
            if listing is None or listing.server_id != self.server_id or listing.status != "active":
                raise MarketError("listing_unavailable")
            shop = await session.get(PlayerShop, listing.shop_id)
            if shop is None or shop.owner_character_id is None:
                raise MarketError("listing_unavailable")
            if shop.owner_character_id == buyer.id:
                raise MarketError("own_listing")
            if not 1 <= quantity <= listing.remaining_quantity:
                raise MarketError("insufficient_quantity")
            purchase = MarketPurchase(
                listing_id=listing.id,
                buyer_character_id=buyer.id,
                seller_character_id=shop.owner_character_id,
                terms_version=listing.terms_version,
                unit_price=listing.unit_price,
                quantity=quantity,
                status="preview",
                created_at=now,
                expires_at=now + PURCHASE_PREVIEW_TTL,
            )
            session.add(purchase)
            await session.flush()
            return PurchasePreview(
                purchase_id=purchase.id,
                listing_id=listing.id,
                title=listing.title,
                quantity=quantity,
                unit_price=listing.unit_price,
                total=listing.unit_price * quantity,
                mythic=is_mythic(listing.rarity),
                wallet=buyer.crowns,
            )

    async def confirm_purchase(
        self,
        actor: int,
        purchase_id: UUID,
        *,
        mythic_confirmed: bool = False,
        now: datetime | None = None,
    ) -> PurchaseResult:
        """§28.11-§28.14 commit. A repeated click returns the first result."""
        now = _utcnow(now)
        async with self.sessions() as session:
            buyer_id = await session.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            reference = await session.get(MarketPurchase, purchase_id)
            if reference is None or reference.buyer_character_id != buyer_id:
                raise MarketError("purchase_unavailable")
            listing_id = reference.listing_id
            seller_id = reference.seller_character_id
        await self._settle_listing(listing_id, now)
        async with self.sessions.begin() as session:
            listing = await self._lock_listing(session, listing_id)
            characters = await self._lock_characters(
                session, [item for item in (buyer_id, seller_id) if item is not None]
            )
            purchase = await session.scalar(
                select(MarketPurchase).where(MarketPurchase.id == purchase_id).with_for_update()
            )
            if purchase is None:
                raise MarketError("purchase_unavailable")
            seller = characters.get(seller_id)
            if purchase.status == "committed":
                return _purchase_result(purchase, listing, seller, False, already=True)
            buyer = characters.get(buyer_id)
            if buyer is None or seller is None or listing is None or listing.status != "active":
                raise MarketError("listing_unavailable")
            if purchase.expires_at <= now:
                raise MarketError("preview_expired")
            # §28.11: an old confirmation is never reread at a new price.
            if (
                purchase.terms_version != listing.terms_version
                or purchase.unit_price != listing.unit_price
            ):
                raise MarketError("offer_updated")
            if purchase.quantity > listing.remaining_quantity:
                raise MarketError("insufficient_quantity")
            if is_mythic(listing.rarity) and not mythic_confirmed:
                raise MarketError("mythic_confirmation_required")
            gross = purchase.unit_price * purchase.quantity
            if buyer.crowns < gross:
                raise MarketError("not_enough_crowns")
            split = split_sale(
                listing.gross_sold_total, listing.fee_charged_total, gross, listing.fee_bps
            )
            if seller.crowns + split.net > BIGINT_MAX:
                raise MarketError("seller_wallet_limit")
            undelivered = await deliver_to_inventory(
                session,
                buyer.id,
                listing.item_kind,
                listing.item_snapshot,
                purchase.quantity,
                new_owner=True,
            )
            if undelivered:
                # §23.2: a voluntary purchase needs a real destination, never Pending.
                raise MarketError("inventory_full")
            buyer.crowns -= gross
            seller.crowns += split.net
            listing.remaining_quantity -= purchase.quantity
            listing.gross_sold_total += gross
            listing.fee_charged_total += split.fee
            if listing.remaining_quantity == 0:
                listing.status = "sold_out"
                listing.closed_at = now
            purchase.status = "committed"
            purchase.gross = gross
            purchase.fee = split.fee
            purchase.net = split.net
            purchase.committed_at = now
            await record_linked_cooccurrence(
                session,
                server_id=self.server_id,
                activity_kind="market_purchase",
                activity_reference=str(purchase.id),
                characters=[buyer, seller],
                now=now,
            )
            notify = await notification_enabled(session, seller.id, "market")
            return _purchase_result(purchase, listing, seller, notify, already=False)

    # ---------------------------------------------------------------- helpers

    async def _active_listings(self, session, shop_id: UUID, now: datetime) -> int:
        count = await session.scalar(
            select(func.count(MarketListing.id)).where(
                MarketListing.shop_id == shop_id,
                MarketListing.status == "active",
                MarketListing.expires_at > now,
            )
        )
        return int(count or 0)

    async def _consume_search_quota(self, session, character_id: UUID, now: datetime) -> None:
        window_start = now - SEARCH_LIMIT_WINDOW
        await session.execute(
            delete(ShopSearchAttempt).where(
                ShopSearchAttempt.character_id == character_id,
                ShopSearchAttempt.attempted_at <= window_start,
            )
        )
        recent = (
            await session.scalars(
                select(ShopSearchAttempt.attempted_at).where(
                    ShopSearchAttempt.character_id == character_id
                )
            )
        ).all()
        burst = sum(1 for moment in recent if moment > now - SEARCH_BURST_WINDOW)
        if len(recent) >= SEARCH_LIMIT_PER_MINUTE or burst >= SEARCH_BURST_LIMIT:
            raise MarketError("search_rate_limited")
        session.add(ShopSearchAttempt(character_id=character_id, attempted_at=now))

    async def _ensure_shop(self, session, character: Character, now: datetime) -> PlayerShop:
        """The caller holds the Character lock, so only the Code can collide."""
        shop = await session.scalar(
            select(PlayerShop).where(PlayerShop.owner_character_id == character.id)
        )
        if shop is not None:
            return shop
        for _ in range(_CODE_ATTEMPTS):
            shop_id = await session.scalar(
                insert(PlayerShop)
                .values(
                    owner_character_id=character.id,
                    server_id=self.server_id,
                    code=generate_shop_code(),
                    created_at=now,
                )
                .on_conflict_do_nothing(constraint="uq_player_shop_code")
                .returning(PlayerShop.id)
            )
            if shop_id is not None:
                return await session.get(PlayerShop, shop_id)
        raise MarketError("shop_code_unavailable")

    async def _lock_listing(self, session, listing_id: UUID) -> MarketListing | None:
        return await session.scalar(
            select(MarketListing)
            .where(MarketListing.id == listing_id, MarketListing.server_id == self.server_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def _require_owner(self, session, actor: int, listing) -> Character:
        """§28.7: ownership is shop + character + server, never the Code."""
        if listing is None:
            raise MarketError("listing_unavailable")
        character = await self._require_character(session, actor)
        shop = await session.get(PlayerShop, listing.shop_id)
        if (
            shop is None
            or shop.owner_character_id != character.id
            or shop.server_id != self.server_id
        ):
            raise MarketError("not_listing_owner")
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

    async def _lock_character_id(self, session, character_id: UUID) -> Character:
        return (await self._lock_characters(session, [character_id]))[character_id]

    async def _lock_character_for_actor(self, session, actor: int) -> Character:
        character = await self._require_character(session, actor, lock=True)
        return character

    async def _require_character(
        self, session, actor: int, *, lock: bool = False, guard: bool = False
    ) -> Character:
        return await require_trading_character(
            session, actor, self.server_id, lock=lock, guard=guard, error=MarketError
        )


def _check_price(unit_price: int, quantity: int) -> None:
    if unit_price < MIN_UNIT_PRICE:
        raise MarketError("invalid_price")
    if unit_price * max(quantity, 1) > BIGINT_MAX:
        raise MarketError("price_out_of_range")


def _listing_view(row: MarketListing) -> ListingView:
    return ListingView(
        listing_id=row.id,
        kind=row.item_kind,
        title=row.title,
        rarity=row.rarity,
        remaining=row.remaining_quantity,
        initial=row.initial_quantity,
        unit_price=row.unit_price,
        terms_version=row.terms_version,
        expires_at=row.expires_at,
    )


def _purchase_result(purchase, listing, seller, notify: bool, *, already: bool) -> PurchaseResult:
    return PurchaseResult(
        purchase_id=purchase.id,
        listing_id=purchase.listing_id,
        title=listing.title if listing else "",
        quantity=purchase.quantity,
        unit_price=purchase.unit_price,
        gross=purchase.gross or 0,
        fee=purchase.fee or 0,
        net=purchase.net or 0,
        remaining=listing.remaining_quantity if listing else 0,
        seller_telegram_id=seller.telegram_id if seller else None,
        notify_seller=notify,
        already_committed=already,
    )


def _utcnow(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)
