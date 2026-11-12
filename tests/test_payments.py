"""Paid products: orders, webhook, server-side check, delivery and refunds (GDD §35)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select

from asterion.api import app as api
from asterion.application.chronicle import ChronicleAdmin, ChronicleService
from asterion.application.outbox import OUTBOX_HANDLERS, OutboxDispatcher
from asterion.application.payments import (
    CONFIRM_TOPIC,
    PaymentConfig,
    PaymentError,
    PaymentService,
    register_outbox_handler,
)
from asterion.bot.shop_ui import render_orders, render_shop, render_terms, terms_text
from asterion.domain.payments import (
    CHRONICLE_PASS,
    PATRON,
    TERMS_VERSION,
    extend_patron,
    format_brl,
    new_order_nsu,
    parse_order_nsu,
    patron_cosmetics_for,
    refund_allowed,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterCosmetic,
    CharacterCosmeticSelection,
    ChronicleAccount,
    OutboxMessage,
    PatronAccount,
    PaymentOrder,
    PaymentOrderEvent,
)
from asterion.infrastructure.infinitepay import (
    PaymentCheck,
    PaymentProviderError,
    _link_url,
)
from tests.test_chronicle import (
    ANA,
    BEA,
    SERVER,
    WEEK1,
    _conclude_all,
    _make,
    _schedule,
)

PRICES = {PATRON: 1490, CHRONICLE_PASS: 2490}
NOW = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
TEMP_TITLE = "cosmetic.title.patrono.patrono_das_cinzas"
TEMP_FRAME = "cosmetic.frame.patrono.vigilia_do_patrono"
ALIADO = "cosmetic.title.patrono.aliado_do_refugio"


class FakeProvider:
    name = "infinitepay"

    def __init__(self):
        self.links: list[dict] = []
        self.checks: list[dict] = []
        self.paid = True
        self.amount: int | None = None  # None: the order's own amount
        self.down = False

    async def create_link(self, **kwargs) -> str:
        if self.down:
            raise PaymentProviderError("down")
        self.links.append(kwargs)
        return f"https://checkout.example/{len(self.links)}"

    async def check(self, *, order_nsu, transaction_nsu, slug) -> PaymentCheck:
        self.checks.append({"order_nsu": order_nsu, "transaction_nsu": transaction_nsu})
        amount = self.amount
        if amount is None:
            amount = next(
                (link["amount_cents"] for link in self.links if link["order_nsu"] == order_nsu),
                None,
            )
        return PaymentCheck(True, self.paid, amount, amount, "pix")


def _service(database, provider=None) -> PaymentService:
    config = PaymentConfig(PRICES, "https://pay.example/payments/infinitepay/webhook?token=t")
    return PaymentService(database[1], SERVER, config, provider or FakeProvider())


def _notice(order, transaction="tx-1", **extra):
    return {
        "order_nsu": order.order_nsu,
        "transaction_nsu": transaction,
        "invoice_slug": "slug-" + transaction,
        "amount": order.amount_cents,
        **extra,
    }


async def _buy(service, actor, product=PATRON, *, now=NOW, transaction="tx-1"):
    order = await service.create_order(actor, product, TERMS_VERSION, now=now)
    assert await service.record_notice(_notice(order, transaction), now=now) == "queued"
    assert await service.confirm(order.id, now=now) == "paid"
    return order


async def _cosmetics(database, actor) -> set[str]:
    async with database[1]() as session:
        return set(
            (
                await session.scalars(
                    select(CharacterCosmetic.cosmetic_id)
                    .join(Character, Character.id == CharacterCosmetic.character_id)
                    .where(Character.telegram_id == actor)
                )
            ).all()
        )


async def _count(database, model, *where) -> int:
    async with database[1]() as session:
        return int(await session.scalar(select(func.count()).select_from(model).where(*where)))


# ---------------------------------------------------------------- pure rules


def test_order_nsu_roundtrip_and_rejects_junk():
    nsu = new_order_nsu(PATRON, 123, "ocaso")
    reference = parse_order_nsu(nsu)
    assert reference is not None
    assert (reference.product.product_id, reference.account_id, reference.server_id) == (
        PATRON,
        123,
        "ocaso",
    )
    for junk in (None, 5, "", "ast1:p:12:ocaso", "ast1:x:1:ocaso:" + "a" * 32, nsu + "z"):
        assert parse_order_nsu(junk) is None


def test_patron_stacks_from_the_later_of_now_and_until():
    assert extend_patron(NOW, None) == NOW + timedelta(days=30)
    assert extend_patron(NOW, NOW - timedelta(days=3)) == NOW + timedelta(days=30)
    assert extend_patron(NOW, NOW + timedelta(days=10)) == NOW + timedelta(days=40)


def test_patron_cosmetics_by_state():
    assert patron_cosmetics_for(NOW, None, 0) == ()
    active = patron_cosmetics_for(NOW, NOW + timedelta(days=1), 30)
    assert active == (TEMP_TITLE, TEMP_FRAME, ALIADO)
    assert len(patron_cosmetics_for(NOW, None, 360)) == 5


def test_refund_window_and_money_format():
    assert refund_allowed(NOW, NOW - timedelta(days=7), our_error=False)
    assert not refund_allowed(NOW, NOW - timedelta(days=7, seconds=1), our_error=False)
    assert refund_allowed(NOW, NOW - timedelta(days=90), our_error=True)
    assert format_brl(1490) == "R$ 14,90"
    assert format_brl(123456) == "R$ 1.234,56"


def test_link_url_from_unknown_response_shape():
    assert _link_url({"url": "https://a"}) == "https://a"
    assert _link_url({"data": {"link": "https://b"}}) == "https://b"
    assert _link_url({"url": "http://insecure"}) is None


def test_terms_and_buttons():
    text = terms_text(PATRON, 1490, 60)
    assert TERMS_VERSION in text and "R$ 14,90" in text and "7 dias" in text
    screen = render_terms(CHRONICLE_PASS, 2490, 60)
    buttons = [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]
    assert f"pay:b:{CHRONICLE_PASS}:{TERMS_VERSION}" in buttons
    assert all(len((data or "").encode()) <= 64 for data in buttons)


# ---------------------------------------------------------------- orders


async def test_repeated_webhook_delivers_once_and_shows_in_orders(database):
    await _make(database, ANA, "Ana")
    provider = FakeProvider()
    service = _service(database, provider)
    order = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    assert order.checkout_url == "https://checkout.example/1"
    assert provider.links[0]["amount_cents"] == 1490
    # A second tap reuses the open link instead of creating another order.
    again = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    assert again.id == order.id and len(provider.links) == 1

    assert await service.record_notice(_notice(order), now=NOW) == "queued"
    assert await service.record_notice(_notice(order), now=NOW) == "queued"
    assert await _count(database, OutboxMessage, OutboxMessage.topic == CONFIRM_TOPIC) == 1
    assert await service.confirm(order.id, now=NOW) == "paid"
    assert await service.confirm(order.id, now=NOW) == "already_paid"
    assert await service.record_notice(_notice(order), now=NOW) == "already_paid"
    assert len(provider.checks) == 1

    async with database[1]() as session:
        patron = await session.get(PatronAccount, ANA)
    assert patron.active_until == NOW + timedelta(days=30) and patron.paid_days == 30
    assert await _cosmetics(database, ANA) == {TEMP_TITLE, TEMP_FRAME, ALIADO}
    notices = await _count(
        database,
        OutboxMessage,
        OutboxMessage.topic == "telegram.send_message",
        OutboxMessage.aggregate_key == f"telegram:{ANA}",
    )
    assert notices == 1

    orders = await service.orders(ANA)
    assert [(o.status, o.product) for o in orders] == [("paid", PATRON)]
    assert "✅ Pago" in render_orders(orders, NOW).text
    shop = await service.shop(ANA, now=NOW)
    assert shop.patron_active and shop.patron_prestige == ("Aliado do Refúgio",)
    assert "ativo até" in render_shop(shop).text


async def test_terms_and_availability_are_checked(database):
    service = _service(database)
    with pytest.raises(PaymentError) as error:
        await service.create_order(ANA, PATRON, "2020-01-01", now=NOW)
    assert error.value.code == "terms_outdated"
    closed = PaymentService(database[1], SERVER, PaymentConfig(PRICES, None), FakeProvider())
    with pytest.raises(PaymentError) as error:
        await closed.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    assert error.value.code == "payments_disabled"
    assert not (await closed.shop(ANA, now=NOW)).enabled
    with pytest.raises(PaymentError) as error:
        await service.create_order(ANA, CHRONICLE_PASS, TERMS_VERSION, now=NOW)
    assert error.value.code == "chronicle_pass_closed"


async def test_provider_down_expires_the_order(database):
    provider = FakeProvider()
    provider.down = True
    service = _service(database, provider)
    with pytest.raises(PaymentError) as error:
        await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    assert error.value.code == "provider_unavailable"
    assert [o.status for o in await service.orders(ANA)] == ["expired"]


async def test_unconfirmed_or_wrong_amount_never_delivers(database):
    await _make(database, ANA, "Ana")
    provider = FakeProvider()
    service = _service(database, provider)
    order = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    await service.record_notice(_notice(order), now=NOW)
    provider.paid = False
    assert await service.confirm(order.id, now=NOW) == "unpaid"
    provider.paid, provider.amount = True, 100
    assert await service.confirm(order.id, now=NOW) == "mismatch"
    assert await _cosmetics(database, ANA) == set()
    # A forged cheap payment must not lock the order: the genuine notice replaces it.
    assert await service.record_notice(_notice(order, "tx-real"), now=NOW) == "queued"
    provider.amount = None
    assert await service.confirm(order.id, now=NOW) == "paid"
    assert provider.checks[-1]["transaction_nsu"] == "tx-real"
    kinds = [event.kind for event in await service.events(order.id)]
    assert kinds.count("check_unpaid") == 1 and kinds.count("amount_mismatch") == 1


async def test_malformed_and_duplicate_notices(database):
    service = _service(database)
    order = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    for bad in (
        {},
        {"order_nsu": "x", "transaction_nsu": "t", "invoice_slug": "s"},
        {**_notice(order), "transaction_nsu": 7},
        {**_notice(order), "order_nsu": new_order_nsu(PATRON, ANA, "outro")},
    ):
        with pytest.raises(PaymentError):
            await service.record_notice(bad, now=NOW)
    await service.record_notice(_notice(order, "tx-1"), now=NOW)
    assert await service.confirm(order.id, now=NOW) == "paid"
    # A second payment on a paid order is recorded for a manual refund only.
    assert await service.record_notice(_notice(order, "tx-2"), now=NOW) == "duplicate"
    other = await service.create_order(BEA, PATRON, TERMS_VERSION, now=NOW)
    with pytest.raises(PaymentError):
        await service.record_notice(_notice(other, "tx-1"), now=NOW)


async def test_lost_order_is_rebuilt_but_cheap_forgeries_are_refused(database):
    await _make(database, ANA, "Ana")
    provider = FakeProvider()
    service = _service(database, provider)
    # Anyone can create a R$ 1,00 link on a public handle with a crafted order id.
    forged = new_order_nsu(PATRON, ANA, SERVER)
    payload = {"order_nsu": forged, "transaction_nsu": "f1", "invoice_slug": "s", "amount": 100}
    assert await service.record_notice(payload, now=NOW) == "queued"
    provider.amount = 100
    lost = await service.find(forged)
    assert await service.confirm(lost.id, now=NOW) == "mismatch"
    # A real order lost in a restore: rebuilt from its id and confirmed at full price.
    real = new_order_nsu(PATRON, ANA, SERVER)
    provider.amount = 1490
    assert (
        await service.attach_notice(real, "r1", "s2", amount_cents=1490, operator="op", now=NOW)
        == "queued"
    )
    rebuilt = await service.find(real)
    assert await service.confirm(rebuilt.id, now=NOW) == "paid"
    assert await service.confirm(rebuilt.id, now=NOW) == "already_paid"
    async with database[1]() as session:
        assert (await session.get(PatronAccount, ANA)).paid_days == 30


async def test_reconcile_confirms_pending_notices_once(database):
    provider = FakeProvider()
    service = _service(database, provider)
    order = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    await service.record_notice(_notice(order), now=NOW)
    first = await service.reconcile(operator="op", now=NOW)
    assert [outcome for _, outcome in first] == ["paid"]
    assert await service.reconcile(operator="op", now=NOW) == []


async def test_outbox_runs_the_server_side_check(database):
    service = _service(database)
    register_outbox_handler(service)
    order = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    await service.record_notice(_notice(order))
    dispatcher = OutboxDispatcher(database[1], {CONFIRM_TOPIC: OUTBOX_HANDLERS[CONFIRM_TOPIC]})
    report = await dispatcher.run_maintenance()
    assert report.delivered == 1
    assert (await service.find(order.order_nsu)).status == "paid"


async def test_expired_order_still_accepts_a_late_payment(database):
    service = _service(database)
    order = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    assert await service.expire_due(now=NOW + timedelta(hours=2)) == 1
    assert (await service.find(order.order_nsu)).status == "expired"
    await service.record_notice(_notice(order), now=NOW + timedelta(hours=2))
    assert await service.confirm(order.id, now=NOW + timedelta(hours=2)) == "paid"


async def test_patron_expiry_keeps_permanent_prestige(database):
    await _make(database, ANA, "Ana")
    service = _service(database)
    await _buy(service, ANA)
    async with database[1].begin() as session:
        character = await session.scalar(select(Character.id).where(Character.telegram_id == ANA))
        session.add(
            CharacterCosmeticSelection(
                character_id=character, cosmetic_type="title", cosmetic_id=TEMP_TITLE
            )
        )
    assert await service.expire_patrons(now=NOW + timedelta(days=29)) == 0
    assert await service.expire_patrons(now=NOW + timedelta(days=31)) == 1
    assert await _cosmetics(database, ANA) == {ALIADO}
    assert await _count(database, CharacterCosmeticSelection) == 0
    # A new purchase after expiry starts again from now and stacks the support days.
    later = NOW + timedelta(days=40)
    await _buy(service, ANA, now=later, transaction="tx-2")
    async with database[1]() as session:
        patron = await session.get(PatronAccount, ANA)
    assert patron.active_until == later + timedelta(days=30) and patron.paid_days == 60


async def test_refund_revokes_only_that_order_and_flags_repeats(database):
    await _make(database, ANA, "Ana")
    service = _service(database)
    first = await _buy(service, ANA, transaction="tx-1")
    second = await _buy(service, ANA, transaction="tx-2")
    async with database[1]() as session:
        assert (await session.get(PatronAccount, ANA)).active_until == NOW + timedelta(days=60)

    result = await service.refund(
        second.order_nsu, note="pediu", operator="op", now=NOW + timedelta(days=1)
    )
    assert result.order.status == "refunded" and not result.flagged
    async with database[1]() as session:
        patron = await session.get(PatronAccount, ANA)
    assert patron.active_until == NOW + timedelta(days=30) and patron.paid_days == 30
    assert await _cosmetics(database, ANA) == {TEMP_TITLE, TEMP_FRAME, ALIADO}

    with pytest.raises(PaymentError) as error:
        await service.refund(first.order_nsu, note="tarde", operator="op", now=NOW + timedelta(8))
    assert error.value.code == "refund_window_closed"
    result = await service.refund(
        first.order_nsu, note="erro nosso", operator="op", our_error=True, now=NOW + timedelta(8)
    )
    assert result.flagged and result.refunds_of_account == 2
    assert await _cosmetics(database, ANA) == set()
    with pytest.raises(PaymentError) as error:
        await service.refund(first.order_nsu, note="de novo", operator="op", now=NOW)
    assert error.value.code == "order_not_paid"
    # Orders and their history are never deleted.
    assert await _count(database, PaymentOrder) == 2
    kinds = [event.kind for event in await service.events(first.id)]
    assert "refunded" in kinds and "revoked" in kinds and "refund_flag" in kinds


async def test_pass_purchase_unlocks_premium_and_refund_revokes_it(database):
    await _schedule(database)
    await _make(database, ANA, "Ana")
    chronicle = ChronicleService(database[1], SERVER)
    await _conclude_all(database, ANA, [1], WEEK1)
    await chronicle.claim(ANA, now=WEEK1)
    free = await _cosmetics(database, ANA)

    service = _service(database)
    order = await _buy(service, ANA, CHRONICLE_PASS, now=WEEK1)
    with pytest.raises(PaymentError) as error:
        await service.create_order(ANA, CHRONICLE_PASS, TERMS_VERSION, now=WEEK1)
    assert error.value.code == "chronicle_pass_active"
    result = await chronicle.claim(ANA, now=WEEK1)
    assert result.milestones == (("premium", 4),)
    assert len(await _cosmetics(database, ANA)) == len(free) + 1

    refund = await service.refund(order.order_nsu, note="pediu", operator="op", now=WEEK1)
    assert refund.revoked["premium_milestones"] == [4]
    assert await _cosmetics(database, ANA) == free
    async with database[1]() as session:
        account = await session.get(ChronicleAccount, (ANA, SERVER, "cr01"))
    assert account.premium_at is None


async def test_manual_pass_is_not_revoked_by_a_refund(database):
    await _schedule(database)
    service = _service(database)
    order = await service.create_order(BEA, CHRONICLE_PASS, TERMS_VERSION, now=WEEK1)
    await service.record_notice(_notice(order), now=WEEK1)
    # The operator grants the Passe by hand before the payment is confirmed.
    await ChronicleAdmin(database[1], SERVER).grant_pass(BEA, "manual", now=WEEK1)
    assert await service.confirm(order.id, now=WEEK1) == "paid"
    refund = await service.refund(order.id.hex, note="x", operator="op", now=WEEK1)
    assert refund.revoked.get("nothing") == "pass_was_already_active"
    async with database[1]() as session:
        assert (await session.get(ChronicleAccount, (BEA, SERVER, "cr01"))).premium_at


# ---------------------------------------------------------------- webhook endpoint


async def test_webhook_endpoint_checks_token_and_answers_fast(database):
    service = _service(database)
    order = await service.create_order(ANA, PATRON, TERMS_VERSION, now=NOW)
    api.app.dependency_overrides[api.get_payment_service] = lambda: service
    api.app.dependency_overrides[api._webhook_token] = lambda: "segredo"
    try:
        transport = httpx.ASGITransport(app=api.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            path = "/payments/infinitepay/webhook"
            wrong = await client.post(path, params={"token": "x"}, json=_notice(order))
            assert wrong.status_code == 400
            broken = await client.post(path, params={"token": "segredo"}, content=b"{nope")
            assert broken.status_code == 400
            foreign = await client.post(path, params={"token": "segredo"}, json={"a": 1})
            assert foreign.status_code == 400
            ok = await client.post(path, params={"token": "segredo"}, json=_notice(order))
            assert ok.status_code == 200 and ok.json()["result"] == "queued"
    finally:
        api.app.dependency_overrides.clear()
    # The webhook itself never delivers: it only queues the server-side check.
    assert (await service.find(order.order_nsu)).status == "created"
    assert await _count(database, PaymentOrderEvent, PaymentOrderEvent.kind == "notice") == 1
