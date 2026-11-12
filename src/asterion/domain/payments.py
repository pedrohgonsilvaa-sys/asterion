"""Pure rules for paid products (GDD v1.6.0 §35, §35.1, §35.2, §49.19).

Paid products only grant cosmetics and prestige. Nothing here touches XP,
Coroas, combat or progression. Prices are commercial configuration (environment
variables), never constants of this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

PATRON = "patron"
CHRONICLE_PASS = "chronicle_pass"


@dataclass(frozen=True, slots=True)
class Product:
    product_id: str
    code: str  # short form used inside order_nsu
    name: str


PRODUCTS: dict[str, Product] = {
    PATRON: Product(PATRON, "p", "Patrono de Asterion"),
    CHRONICLE_PASS: Product(CHRONICLE_PASS, "c", "Passe da Crônica"),
}
_PRODUCT_BY_CODE = {product.code: product for product in PRODUCTS.values()}

# Order states. `paid`, `refunded` and `reversed` are preserved forever (§35.2).
CREATED = "created"
PAID = "paid"
EXPIRED = "expired"
REFUNDED = "refunded"
REVERSED = "reversed"
ORDER_STATUSES = (CREATED, PAID, EXPIRED, REFUNDED, REVERSED)
# States from which a confirmed payment is still accepted (a late Pix wins).
CONFIRMABLE = frozenset({CREATED, EXPIRED})

# §49.19: one support level, 30 days per purchase, stacked from max(now, until).
PATRON_DAYS = 30
PATRON_COSMETIC_SOURCE = "patrono_de_asterion"
PATRON_TEMPORARY_COSMETICS = (
    ("cosmetic.title.patrono.patrono_das_cinzas", "title", "Patrono das Cinzas"),
    ("cosmetic.frame.patrono.vigilia_do_patrono", "frame", "Vigília do Patrono"),
)
# §49.19: permanent prestige by accumulated valid paid support, in days.
PATRON_PRESTIGE = (
    (30, ("cosmetic.title.patrono.aliado_do_refugio", "title", "Aliado do Refúgio")),
    (90, ("cosmetic.title.patrono.guardiao_da_chama", "title", "Guardião da Chama")),
    (180, ("cosmetic.frame.patrono.luz_do_refugio", "frame", "Luz do Refúgio")),
    (270, ("cosmetic.frame.patrono.chama_perene", "frame", "Chama Perene")),
    (360, ("cosmetic.appearance.patrono.manto_do_patrono", "appearance", "Manto do Patrono")),
)
PATRON_COSMETICS = (
    *PATRON_TEMPORARY_COSMETICS,
    *(cosmetic for _, cosmetic in PATRON_PRESTIGE),
)
PATRON_COSMETIC_IDS = frozenset(cosmetic_id for cosmetic_id, _, _ in PATRON_COSMETICS)

# Refund policy (commercial, approved by the author on 2026-11-11): 7 days after
# payment with no questions; later only for our own error. Repeated refunds of
# one account open a review flag; they never block anything.
REFUND_WINDOW = timedelta(days=7)
REFUND_FLAG_THRESHOLD = 2

TERMS_VERSION = "2026-11-11"

_NSU_PREFIX = "ast1"
_SERVER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def extend_patron(now: datetime, active_until: datetime | None) -> datetime:
    """§49.19: 30 days added to the later of now and the current end."""
    start = now if active_until is None or active_until < now else active_until
    return start + timedelta(days=PATRON_DAYS)


def patron_active(now: datetime, active_until: datetime | None) -> bool:
    return active_until is not None and active_until > now


def patron_cosmetics_for(now: datetime, active_until: datetime | None, paid_days: int):
    """Cosmetic ids a Patrono account must own right now."""
    owned = []
    if patron_active(now, active_until):
        owned.extend(cosmetic_id for cosmetic_id, _, _ in PATRON_TEMPORARY_COSMETICS)
    owned.extend(cosmetic[0] for days, cosmetic in PATRON_PRESTIGE if paid_days >= days)
    return tuple(owned)


def prestige_names(paid_days: int) -> tuple[str, ...]:
    return tuple(cosmetic[2] for days, cosmetic in PATRON_PRESTIGE if paid_days >= days)


@dataclass(frozen=True, slots=True)
class OrderReference:
    product: Product
    account_id: int
    server_id: str
    token: str


def new_order_nsu(product_id: str, account_id: int, server_id: str) -> str:
    """Self-describing order id: after a backup restore a lost order can be rebuilt."""
    if not _SERVER.match(server_id):
        raise ValueError("server id cannot be encoded in an order")
    return f"{_NSU_PREFIX}:{PRODUCTS[product_id].code}:{account_id}:{server_id}:{uuid4().hex}"


def parse_order_nsu(value: object) -> OrderReference | None:
    if not isinstance(value, str) or len(value) > 160:
        return None
    parts = value.split(":")
    if len(parts) != 5 or parts[0] != _NSU_PREFIX:
        return None
    _, code, account, server_id, token = parts
    product = _PRODUCT_BY_CODE.get(code)
    if (
        product is None
        or not account.isdigit()
        or not _SERVER.match(server_id)
        or not re.fullmatch(r"[0-9a-f]{32}", token)
    ):
        return None
    return OrderReference(product, int(account), server_id, token)


def refund_allowed(now: datetime, paid_at: datetime, *, our_error: bool) -> bool:
    return our_error or now <= paid_at + REFUND_WINDOW


def format_brl(cents: int) -> str:
    reais, centavos = divmod(cents, 100)
    return f"R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"
