"""Paid products: orders, confirmation, delivery and refunds (GDD §35, §35.1, §35.2).

Flow:

1. ``create_order`` stores the order, then asks the provider for a checkout link.
2. The provider's webhook calls ``record_notice``. It only stores the notice and
   queues a ``payments.confirm`` Outbox message, so the webhook answers fast.
3. The Outbox runs ``confirm``: it asks the provider (``/payment_check``) from the
   server, checks the amount and the order, and in one transaction marks the
   order paid, delivers the benefit and queues the player's Telegram notice.

Idempotency: ``transaction_nsu`` (the provider's payment id) is unique, and only
``created``/``expired`` orders can become ``paid``, so a repeated webhook never
delivers twice. Orders and their events are never deleted; a refund changes the
status, revokes exactly what the order recorded in ``grant`` and is audited.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.chronicle import (
    ChronicleError,
    grant_pass_in,
    pass_active,
    pass_open,
    revoke_pass_in,
)
from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.application.outbox import OUTBOX_HANDLERS, PermanentOutboxError
from asterion.domain.chronicle import TIMEZONE
from asterion.domain.payments import (
    CHRONICLE_PASS,
    CONFIRMABLE,
    CREATED,
    EXPIRED,
    PAID,
    PATRON,
    PATRON_COSMETIC_IDS,
    PATRON_COSMETIC_SOURCE,
    PATRON_DAYS,
    PRODUCTS,
    REFUND_FLAG_THRESHOLD,
    REFUNDED,
    REVERSED,
    TERMS_VERSION,
    extend_patron,
    new_order_nsu,
    parse_order_nsu,
    patron_active,
    patron_cosmetics_for,
    prestige_names,
    refund_allowed,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterCosmetic,
    OutboxMessage,
    PatronAccount,
    PaymentOrder,
    PaymentOrderEvent,
)
from asterion.infrastructure.infinitepay import PaymentProvider, PaymentProviderError

logger = logging.getLogger(__name__)

CONFIRM_TOPIC = "payments.confirm"
TELEGRAM_TOPIC = "telegram.send_message"
# An open link is reused while it still has this long left.
REUSE_MARGIN = timedelta(minutes=5)
ORDERS_SHOWN = 10


class PaymentError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class PaymentConfig:
    prices: Mapping[str, int | None]
    webhook_url: str | None
    link_minutes: int = 60

    @property
    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def price(self, product_id: str) -> int | None:
        return self.prices.get(product_id) if self.enabled else None


def payment_config(settings: Any) -> PaymentConfig:
    webhook_url = None
    if settings.payments_enabled:
        base = settings.payments_public_url.rstrip("/")
        webhook_url = f"{base}/payments/infinitepay/webhook?token={settings.payments_webhook_token}"
    return PaymentConfig(
        prices={product: settings.product_price_cents(product) for product in PRODUCTS},
        webhook_url=webhook_url,
        link_minutes=settings.payment_link_minutes,
    )


def build_provider(settings: Any) -> PaymentProvider | None:
    if not settings.infinitepay_handle:
        return None
    from asterion.infrastructure.infinitepay import InfinitePayClient

    return InfinitePayClient(
        settings.infinitepay_handle,
        api_key=settings.infinitepay_api_key,
        base_url=settings.infinitepay_api_url,
    )


@dataclass(frozen=True, slots=True)
class OrderView:
    id: UUID
    order_nsu: str
    product: str
    product_name: str
    amount_cents: int
    status: str
    created_at: datetime
    expires_at: datetime | None
    paid_at: datetime | None
    checkout_url: str | None
    grant_error: str | None


@dataclass(frozen=True, slots=True)
class ShopView:
    enabled: bool
    prices: Mapping[str, int | None]
    patron_until: datetime | None
    patron_active: bool
    patron_paid_days: int
    patron_prestige: tuple[str, ...]
    pass_active: bool
    pass_open: bool


@dataclass(frozen=True, slots=True)
class RefundResult:
    order: OrderView
    revoked: dict[str, Any] = field(default_factory=dict)
    refunds_of_account: int = 0
    flagged: bool = False


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _view(order: PaymentOrder) -> OrderView:
    return OrderView(
        order.id,
        order.order_nsu,
        order.product,
        PRODUCTS[order.product].name,
        order.amount_cents,
        order.status,
        order.created_at,
        order.expires_at,
        order.paid_at,
        order.checkout_url,
        order.grant_error,
    )


def _local_date(moment: datetime) -> str:
    return moment.astimezone(TIMEZONE).strftime("%d/%m/%Y %H:%M")


def _event(session, order: PaymentOrder, kind: str, actor: str, now, data=None, note=None):
    session.add(
        PaymentOrderEvent(
            order_id=order.id,
            kind=kind,
            actor=actor[:64],
            data=data or {},
            note=None if note is None else note.strip()[:500],
            created_at=now,
        )
    )


def _notify(session, order: PaymentOrder, suffix: str, text: str) -> None:
    """Player notice in the same transaction as the state it reports (Outbox)."""
    session.add(
        OutboxMessage(
            topic=TELEGRAM_TOPIC,
            dedup_key=f"payment:{order.id}:{suffix}",
            aggregate_key=f"telegram:{order.account_id}",
            payload={"chat_id": order.account_id, "text": text, "parse_mode": None},
        )
    )


async def _patron_row(session: AsyncSession, account_id: int, now: datetime) -> PatronAccount:
    await session.execute(
        insert(PatronAccount)
        .values(account_id=account_id, paid_days=0, temporary_granted=False, updated_at=now)
        .on_conflict_do_nothing()
    )
    row = await session.get(PatronAccount, account_id, with_for_update=True)
    assert row is not None
    return row


async def sync_patron_cosmetics(session: AsyncSession, row: PatronAccount, now: datetime) -> None:
    """Make every character of the account own exactly the Patrono cosmetics due now.

    Removing a cosmetic also drops its selection (FK cascade), so the category
    falls back to the default (§35.1, §33.4)."""
    due = set(patron_cosmetics_for(now, row.active_until, row.paid_days))
    characters = (
        await session.scalars(select(Character.id).where(Character.telegram_id == row.account_id))
    ).all()
    for character_id in characters:
        for cosmetic_id in sorted(due):
            await session.execute(
                insert(CharacterCosmetic)
                .values(
                    character_id=character_id,
                    cosmetic_id=cosmetic_id,
                    cosmetic_type=COSMETICS_BY_ID[cosmetic_id].cosmetic_type,
                    source_achievement_id=PATRON_COSMETIC_SOURCE,
                    acquired_at=now,
                )
                .on_conflict_do_nothing()
            )
    stale = PATRON_COSMETIC_IDS - due
    if characters and stale:
        await session.execute(
            delete(CharacterCosmetic).where(
                CharacterCosmetic.character_id.in_(characters),
                CharacterCosmetic.source_achievement_id == PATRON_COSMETIC_SOURCE,
                CharacterCosmetic.cosmetic_id.in_(sorted(stale)),
            )
        )
    row.temporary_granted = patron_active(now, row.active_until)
    row.updated_at = now


class PaymentService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        config: PaymentConfig,
        provider: PaymentProvider | None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.config = config
        self.provider = provider

    # ------------------------------------------------------------ player

    async def shop(self, actor: int, *, now: datetime | None = None) -> ShopView:
        now = _now(now)
        async with self.sessions.begin() as session:
            row = await session.get(PatronAccount, actor, with_for_update=True)
            if row is not None:
                # Characters created after the purchase receive the cosmetics here.
                await sync_patron_cosmetics(session, row, now)
            premium = await pass_active(session, self.server_id, actor)
            open_ = await pass_open(session, self.server_id, now)
        return ShopView(
            enabled=self.config.enabled and self.provider is not None,
            prices={product: self.config.price(product) for product in PRODUCTS},
            patron_until=None if row is None else row.active_until,
            patron_active=row is not None and patron_active(now, row.active_until),
            patron_paid_days=0 if row is None else row.paid_days,
            patron_prestige=() if row is None else prestige_names(row.paid_days),
            pass_active=premium,
            pass_open=open_,
        )

    async def orders(self, actor: int, *, limit: int = ORDERS_SHOWN) -> list[OrderView]:
        async with self.sessions() as session:
            rows = (
                await session.scalars(
                    select(PaymentOrder)
                    .where(PaymentOrder.account_id == actor)
                    .order_by(PaymentOrder.created_at.desc())
                    .limit(limit)
                )
            ).all()
        return [_view(row) for row in rows]

    async def create_order(
        self,
        actor: int,
        product_id: str,
        terms_version: str,
        *,
        now: datetime | None = None,
    ) -> OrderView:
        """Order + checkout link. The terms shown to the player must be the current ones."""
        now = _now(now)
        product = PRODUCTS.get(product_id)
        if product is None:
            raise PaymentError("unknown_product")
        price = self.config.price(product_id)
        if price is None or self.provider is None or self.config.webhook_url is None:
            raise PaymentError("payments_disabled")
        if terms_version != TERMS_VERSION:
            raise PaymentError("terms_outdated")
        async with self.sessions.begin() as session:
            if product_id == CHRONICLE_PASS:
                if not await pass_open(session, self.server_id, now):
                    raise PaymentError("chronicle_pass_closed")
                if await pass_active(session, self.server_id, actor):
                    raise PaymentError("chronicle_pass_active")
            reusable = await session.scalar(
                select(PaymentOrder)
                .where(
                    PaymentOrder.account_id == actor,
                    PaymentOrder.server_id == self.server_id,
                    PaymentOrder.product == product_id,
                    PaymentOrder.status == CREATED,
                    PaymentOrder.amount_cents == price,
                    PaymentOrder.checkout_url.is_not(None),
                    PaymentOrder.expires_at > now + REUSE_MARGIN,
                )
                .order_by(PaymentOrder.created_at.desc())
                .limit(1)
            )
            if reusable is not None:
                return _view(reusable)
            order = PaymentOrder(
                provider=self.provider.name,
                order_nsu=new_order_nsu(product_id, actor, self.server_id),
                account_id=actor,
                server_id=self.server_id,
                product=product_id,
                amount_cents=price,
                status=CREATED,
                recovered=False,
                terms_version=terms_version,
                terms_accepted_at=now,
                created_at=now,
                expires_at=now + timedelta(minutes=self.config.link_minutes),
                updated_at=now,
            )
            session.add(order)
            await session.flush()
            _event(session, order, "created", f"player:{actor}", now, {"amount": price})
            order_id, order_nsu, expires_at = order.id, order.order_nsu, order.expires_at
        # The order exists before the provider ever sees its id.
        try:
            url = await self.provider.create_link(
                order_nsu=order_nsu,
                amount_cents=price,
                description=product.name,
                webhook_url=self.config.webhook_url,
                valid_until=expires_at,
            )
        except PaymentProviderError as error:
            logger.warning("checkout link for %s failed: %s", order_nsu, error)
            async with self.sessions.begin() as session:
                order = await session.get(PaymentOrder, order_id, with_for_update=True)
                assert order is not None
                order.status = EXPIRED
                order.updated_at = now
                _event(session, order, "link_failed", "system", now, {"error": str(error)[:300]})
            raise PaymentError("provider_unavailable") from error
        async with self.sessions.begin() as session:
            order = await session.get(PaymentOrder, order_id, with_for_update=True)
            assert order is not None
            order.checkout_url = url
            order.updated_at = now
            _event(session, order, "link_created", "system", now)
            return _view(order)

    # ------------------------------------------------------------ webhook

    async def record_notice(
        self, payload: Mapping[str, Any], *, actor: str = "webhook", now: datetime | None = None
    ) -> str:
        """Store a provider notice and queue its server-side check. Never trusts it.

        Raises ``PaymentError("bad_notice")`` for a malformed or foreign notice."""
        now = _now(now)
        order_nsu = payload.get("order_nsu")
        transaction_nsu = payload.get("transaction_nsu")
        slug = payload.get("invoice_slug") or payload.get("slug")
        reference = parse_order_nsu(order_nsu)
        if (
            reference is None
            or reference.server_id != self.server_id
            or not isinstance(transaction_nsu, str)
            or not isinstance(slug, str)
            or not 0 < len(transaction_nsu) <= 128
            or not 0 < len(slug) <= 128
        ):
            raise PaymentError("bad_notice")
        amount = payload.get("amount")
        evidence = {
            key: payload.get(key)
            for key in ("amount", "paid_amount", "capture_method", "receipt_url")
            if payload.get(key) is not None
        } | {"transaction_nsu": transaction_nsu, "invoice_slug": slug}
        async with self.sessions.begin() as session:
            order = await session.scalar(
                select(PaymentOrder).where(PaymentOrder.order_nsu == order_nsu).with_for_update()
            )
            if order is None:
                # Lost by a backup restore: rebuild it from the self-describing id.
                if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                    raise PaymentError("bad_notice")
                order = PaymentOrder(
                    provider="infinitepay",
                    order_nsu=order_nsu,
                    account_id=reference.account_id,
                    server_id=reference.server_id,
                    product=reference.product.product_id,
                    amount_cents=amount,
                    status=CREATED,
                    recovered=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(order)
                await session.flush()
                _event(session, order, "recovered", actor, now, evidence)
            if (
                order.status not in CONFIRMABLE
                and order.transaction_nsu is not None
                and order.transaction_nsu != transaction_nsu
            ):
                # A second payment on a paid order: never a second delivery, refund by
                # hand. Before payment a newer notice replaces the older one (a forged
                # cheap payment must not lock the order); the events keep both.
                _event(session, order, "duplicate_payment", actor, now, evidence)
                return "duplicate"
            taken = await session.scalar(
                select(PaymentOrder.id).where(
                    PaymentOrder.transaction_nsu == transaction_nsu,
                    PaymentOrder.id != order.id,
                )
            )
            if taken is not None:
                raise PaymentError("bad_notice")
            _event(session, order, "notice", actor, now, evidence)
            if order.status not in CONFIRMABLE:
                return "already_" + order.status
            order.transaction_nsu = transaction_nsu
            order.invoice_slug = slug
            order.updated_at = now
            await session.execute(
                insert(OutboxMessage)
                .values(
                    topic=CONFIRM_TOPIC,
                    dedup_key=f"{CONFIRM_TOPIC}:{order.id}:{transaction_nsu}"[:200],
                    aggregate_key=f"payment:{order.id}",
                    payload={"order_id": str(order.id)},
                )
                .on_conflict_do_nothing(index_elements=["dedup_key"])
            )
            return "queued"

    # ------------------------------------------------------------ confirmation

    async def confirm(
        self, order_id: UUID, *, actor: str = "system", now: datetime | None = None
    ) -> str:
        """Ask the provider and, when everything matches, pay and deliver once.

        Returns ``paid``, ``already_<status>``, ``unpaid``, ``mismatch`` or
        ``missing_notice``. Provider failures raise ``PaymentProviderError``."""
        now = _now(now)
        async with self.sessions() as session:
            order = await session.get(PaymentOrder, order_id)
            if order is None:
                raise PaymentError("unknown_order")
            if order.status not in CONFIRMABLE:
                return "already_" + order.status
            if not order.transaction_nsu or not order.invoice_slug:
                return "missing_notice"
            ask = (order.order_nsu, order.transaction_nsu, order.invoice_slug)
        if self.provider is None:
            raise PaymentProviderError("payment provider not configured")
        check = await self.provider.check(order_nsu=ask[0], transaction_nsu=ask[1], slug=ask[2])
        async with self.sessions.begin() as session:
            order = await session.get(PaymentOrder, order_id, with_for_update=True)
            assert order is not None
            if order.status not in CONFIRMABLE:
                return "already_" + order.status
            evidence = {
                "success": check.success,
                "paid": check.paid,
                "amount": check.amount_cents,
                "paid_amount": check.paid_amount_cents,
                "capture_method": check.capture_method,
            }
            if not (check.success and check.paid):
                _event(session, order, "check_unpaid", actor, now, evidence)
                return "unpaid"
            if not self._amount_ok(order, check.amount_cents):
                _event(session, order, "amount_mismatch", actor, now, evidence)
                return "mismatch"
            order.status = PAID
            order.paid_at = now
            order.paid_amount_cents = check.paid_amount_cents
            order.capture_method = check.capture_method
            order.updated_at = now
            _event(session, order, "paid", actor, now, evidence)
            await self._deliver(session, order, actor, now)
            return "paid"

    def _amount_ok(self, order: PaymentOrder, amount: int | None) -> bool:
        """The charge must be exactly this order's amount. A rebuilt order must also
        cost at least today's price: anyone can create a link on a public handle."""
        if amount is None or amount != order.amount_cents:
            return False
        if order.recovered:
            price = self.config.prices.get(order.product)
            return price is not None and amount >= price
        return True

    async def _deliver(self, session: AsyncSession, order: PaymentOrder, actor: str, now) -> None:
        product = PRODUCTS[order.product]
        try:
            async with session.begin_nested():
                if order.product == PATRON:
                    row = await _patron_row(session, order.account_id, now)
                    before = row.active_until
                    row.active_until = extend_patron(now, before)
                    row.paid_days += PATRON_DAYS
                    await sync_patron_cosmetics(session, row, now)
                    order.grant = {
                        "kind": PATRON,
                        "days": PATRON_DAYS,
                        "until_before": None if before is None else before.isoformat(),
                        "until_after": row.active_until.isoformat(),
                    }
                    text = (
                        f"✅ Pagamento confirmado: {product.name}.\n\n"
                        f"Patrono ativo até {_local_date(row.active_until)}."
                    )
                else:
                    premium_at, activated = await grant_pass_in(
                        session, order.server_id, order.account_id, self._source(order), now
                    )
                    order.grant = {
                        "kind": CHRONICLE_PASS,
                        "activated": activated,
                        "premium_at": premium_at.isoformat(),
                    }
                    text = (
                        f"✅ Pagamento confirmado: {product.name}.\n\n"
                        "A camada Premium da Trilha está liberada, inclusive nos Marcos já "
                        "alcançados. Resgate em Benefícios › Trilha da Crônica."
                    )
        except ChronicleError as error:
            order.grant_error = error.args[0][:64] if error.args else "grant_failed"
            order.updated_at = now
            _event(session, order, "grant_failed", actor, now, {"error": order.grant_error})
            _notify(
                session,
                order,
                "grant_failed",
                f"✅ Pagamento recebido: {product.name}.\n\n"
                "Não foi possível liberar o benefício agora. A equipe vai resolver ou "
                "reembolsar o valor.",
            )
            return
        order.granted_at = now
        order.updated_at = now
        _event(session, order, "granted", actor, now, dict(order.grant))
        _notify(session, order, "paid", text)

    @staticmethod
    def _source(order: PaymentOrder) -> str:
        return f"order:{order.id.hex[:24]}"

    # ------------------------------------------------------------ maintenance

    async def run_maintenance(self, *, now: datetime | None = None) -> None:
        await self.expire_due(now=now)
        await self.expire_patrons(now=now)

    async def expire_due(self, *, now: datetime | None = None) -> int:
        """Unpaid orders past their link time become ``expired`` (a late Pix still wins)."""
        now = _now(now)
        async with self.sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(PaymentOrder)
                    .where(PaymentOrder.status == CREATED, PaymentOrder.expires_at <= now)
                    .with_for_update(skip_locked=True)
                    .limit(200)
                )
            ).all()
            for order in rows:
                order.status = EXPIRED
                order.updated_at = now
                _event(session, order, "expired", "system", now)
        return len(rows)

    async def expire_patrons(self, *, now: datetime | None = None) -> int:
        """Remove the temporary Patrono Title/Frame once the entitlement ends."""
        now = _now(now)
        async with self.sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(PatronAccount)
                    .where(
                        PatronAccount.temporary_granted.is_(True),
                        PatronAccount.active_until <= now,
                    )
                    .with_for_update(skip_locked=True)
                    .limit(200)
                )
            ).all()
            for row in rows:
                await sync_patron_cosmetics(session, row, now)
        return len(rows)

    # ------------------------------------------------------------ operator

    async def find(self, reference: str) -> OrderView | None:
        async with self.sessions() as session:
            order = await self._find(session, reference)
            return None if order is None else _view(order)

    async def _find(self, session, reference: str, *, lock: bool = False):
        statement = select(PaymentOrder)
        try:
            statement = statement.where(PaymentOrder.id == UUID(reference))
        except ValueError:
            statement = statement.where(
                (PaymentOrder.order_nsu == reference) | (PaymentOrder.transaction_nsu == reference)
            )
        if lock:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    async def list_orders(
        self, *, status: str | None = None, account_id: int | None = None, limit: int = 50
    ) -> list[OrderView]:
        statement = select(PaymentOrder).order_by(PaymentOrder.created_at.desc()).limit(limit)
        if status:
            statement = statement.where(PaymentOrder.status == status)
        if account_id is not None:
            statement = statement.where(PaymentOrder.account_id == account_id)
        async with self.sessions() as session:
            return [_view(row) for row in (await session.scalars(statement)).all()]

    async def events(self, order_id: UUID) -> list[PaymentOrderEvent]:
        async with self.sessions() as session:
            return list(
                (
                    await session.scalars(
                        select(PaymentOrderEvent)
                        .where(PaymentOrderEvent.order_id == order_id)
                        .order_by(PaymentOrderEvent.created_at, PaymentOrderEvent.id)
                    )
                ).all()
            )

    async def attach_notice(
        self,
        order_nsu: str,
        transaction_nsu: str,
        slug: str,
        *,
        amount_cents: int | None = None,
        operator: str,
        now: datetime | None = None,
    ) -> str:
        """Operator path after a restore: the ids come from the InfinitePay app."""
        payload: dict[str, Any] = {
            "order_nsu": order_nsu,
            "transaction_nsu": transaction_nsu,
            "invoice_slug": slug,
        }
        if amount_cents is not None:
            payload["amount"] = amount_cents
        return await self.record_notice(payload, actor=f"operator:{operator}", now=now)

    async def reconcile(
        self, *, operator: str, now: datetime | None = None
    ) -> list[tuple[OrderView, str]]:
        """Check again every unpaid order that already has a provider notice."""
        async with self.sessions() as session:
            ids = (
                await session.scalars(
                    select(PaymentOrder.id)
                    .where(
                        PaymentOrder.status.in_(sorted(CONFIRMABLE)),
                        PaymentOrder.transaction_nsu.is_not(None),
                        PaymentOrder.invoice_slug.is_not(None),
                    )
                    .order_by(PaymentOrder.created_at)
                )
            ).all()
        results = []
        for order_id in ids:
            try:
                outcome = await self.confirm(order_id, actor=f"operator:{operator}", now=now)
            except PaymentProviderError as error:
                outcome = f"provider_error: {error}"
            async with self.sessions() as session:
                order = await session.get(PaymentOrder, order_id)
                assert order is not None
                results.append((_view(order), outcome))
        return results

    async def refund(
        self,
        reference: str,
        *,
        status: str = REFUNDED,
        note: str,
        operator: str,
        our_error: bool = False,
        now: datetime | None = None,
    ) -> RefundResult:
        """Record a refund (or a reversal/chargeback) made at the provider, revoke what
        this order granted and keep the audit trail (§35.1, §35.2)."""
        now = _now(now)
        if status not in (REFUNDED, REVERSED):
            raise PaymentError("bad_refund_status")
        if not note.strip():
            raise PaymentError("note_required")
        actor = f"operator:{operator}"
        async with self.sessions.begin() as session:
            order = await self._find(session, reference, lock=True)
            if order is None:
                raise PaymentError("unknown_order")
            if order.status != PAID:
                raise PaymentError("order_not_paid")
            if (
                status == REFUNDED
                and order.paid_at is not None
                and not refund_allowed(now, order.paid_at, our_error=our_error)
            ):
                raise PaymentError("refund_window_closed")
            revoked = await self._revoke(session, order, now)
            order.status = status
            order.revoked_at = now
            order.updated_at = now
            _event(
                session,
                order,
                status,
                actor,
                now,
                {"our_error": our_error},
                note,
            )
            _event(session, order, "revoked", actor, now, revoked)
            refunds = int(
                await session.scalar(
                    select(func.count()).where(
                        PaymentOrder.account_id == order.account_id,
                        PaymentOrder.status.in_((REFUNDED, REVERSED)),
                    )
                )
                or 0
            )
            flagged = refunds >= REFUND_FLAG_THRESHOLD
            if flagged:
                _event(session, order, "refund_flag", "system", now, {"refunds": refunds})
            _notify(
                session,
                order,
                status,
                f"↩️ {PRODUCTS[order.product].name}: pagamento estornado.\n\n"
                "O benefício desta compra foi removido.",
            )
            return RefundResult(_view(order), revoked, refunds, flagged)

    async def _revoke(self, session, order: PaymentOrder, now) -> dict[str, Any]:
        grant = order.grant or {}
        if order.granted_at is None:
            return {"nothing": "not_granted"}
        if order.product == PATRON:
            days = int(grant.get("days", 0))
            row = await _patron_row(session, order.account_id, now)
            if row.active_until is not None:
                row.active_until = row.active_until - timedelta(days=days)
            row.paid_days = max(0, row.paid_days - days)
            await sync_patron_cosmetics(session, row, now)
            return {
                "kind": PATRON,
                "days": days,
                "until_now": None if row.active_until is None else row.active_until.isoformat(),
                "paid_days_now": row.paid_days,
            }
        if not grant.get("activated"):
            return {"kind": CHRONICLE_PASS, "nothing": "pass_was_already_active"}
        milestones = await revoke_pass_in(
            session, order.server_id, order.account_id, self._source(order)
        )
        return {
            "kind": CHRONICLE_PASS,
            "premium_revoked": milestones is not None,
            "premium_milestones": list(milestones or ()),
        }


def register_outbox_handler(service: PaymentService) -> None:
    """The Outbox runs the server-side check with retry (GDD §43.5)."""

    async def handle(payload: Mapping[str, Any]) -> None:
        outcome = await service.confirm(UUID(str(payload["order_id"])))
        if outcome == "unpaid":
            raise RuntimeError("provider does not confirm the payment yet")
        if outcome in ("mismatch", "missing_notice"):
            raise PermanentOutboxError(f"payment {payload['order_id']}: {outcome}")

    OUTBOX_HANDLERS[CONFIRM_TOPIC] = handle
