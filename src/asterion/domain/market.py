"""Pure rules for Personal Shops and Direct Trade.

Sources: GDD Estrutural v1.6.0 §28, §29, §49.10, §49.18 and §55.4.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from dataclasses import dataclass
from datetime import timedelta

from asterion.domain.creation import PROLOGUE

LISTING_SLOTS = 6
LISTING_DURATION = timedelta(days=7)
MARKET_FEE_PERCENT = 5
MIN_UNIT_PRICE = 1

SHOP_NAME_MAX = 36
SHOP_DESCRIPTION_MAX = 240
PROMOTION_COOLDOWN = timedelta(minutes=30)
SEARCH_LIMIT_PER_MINUTE = 20
SEARCH_BURST_LIMIT = 5
SEARCH_BURST_WINDOW = timedelta(seconds=10)
SEARCH_LIMIT_WINDOW = timedelta(minutes=1)

TRADE_IDLE_TIMEOUT = timedelta(minutes=10)
TRADE_MAX_DURATION = timedelta(minutes=30)
TRADE_CONFIRMATION_STEPS = 2
TRADE_MYTHIC_CONFIRMATION_STEPS = 3

MYTHIC_RARITY = "Mítico"

# Not game values. §28.3 leaves the Code format to Implementation; §55.4 allows a
# storage limit against overflow, which is the range of the BIGINT columns.
PURCHASE_PREVIEW_TTL = timedelta(minutes=5)
SHOP_CODE_LENGTH = 8
SHOP_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
BIGINT_MAX = 2**63 - 1

_PROLOGUE_STAGE = PROLOGUE.split(":", 1)[0]
_LINK = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/|@\w{3,}|\b[\w-]+\.(com|net|org|gg|io)\b)", re.I
)
_SYSTEM_IMITATION = re.compile(
    r"^\W*(sistema|asterion|administra[cç][aã]o|admin|modera[cç][aã]o|suporte|aviso oficial)\b",
    re.I,
)


class MarketTextError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SaleSplit:
    fee: int
    net: int


def contains_link(text: str) -> bool:
    return _LINK.search(text) is not None


def market_unlocked(stage: str) -> bool:
    """Author decision 2026-11-08: available once the Prologue is over."""
    return stage.split(":", 1)[0] != _PROLOGUE_STAGE


MARKET_FEE_BPS = MARKET_FEE_PERCENT * 100


def cumulative_fee(gross_total: int, fee_bps: int = MARKET_FEE_BPS) -> int:
    """§49.10: floor(gross_sold_total × 5%), so split purchases cannot dodge rounding.

    ``fee_bps`` is fixed per listing when it is created; the Tesouraria Obra of
    the seller's Guilda can lower it (domain/guild_works.py).
    """
    return gross_total * fee_bps // 10_000


def split_sale(
    gross_sold_before: int, fee_charged_before: int, gross: int, fee_bps: int = MARKET_FEE_BPS
) -> SaleSplit:
    if gross <= 0:
        raise ValueError("gross must be positive")
    fee = cumulative_fee(gross_sold_before + gross, fee_bps) - fee_charged_before
    return SaleSplit(fee=fee, net=gross - fee)


def generate_shop_code() -> str:
    """Opaque, non-sequential, without look-alike characters (§28.3)."""
    return "".join(secrets.choice(SHOP_CODE_ALPHABET) for _ in range(SHOP_CODE_LENGTH))


def normalize_shop_code(raw: str) -> str | None:
    code = re.sub(r"[\s-]", "", raw).upper()
    if len(code) != SHOP_CODE_LENGTH or any(ch not in SHOP_CODE_ALPHABET for ch in code):
        return None
    return code


def fallback_shop_name(character_name: str) -> str:
    return f"Loja de {character_name}"


def promotion_summary(description: str | None, limit: int = 80) -> str | None:
    if not description:
        return None
    if len(description) <= limit:
        return description
    return description[: limit - 1].rstrip() + "…"


def _clean(raw: str) -> str:
    text = " ".join(raw.split())
    if any(unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Co", "Cn"} for ch in text):
        raise MarketTextError("text_invalid_characters")
    if "<" in text or ">" in text:
        raise MarketTextError("text_invalid_characters")
    if _LINK.search(text):
        raise MarketTextError("text_links_forbidden")
    if _SYSTEM_IMITATION.search(text):
        raise MarketTextError("text_imitates_system")
    return text


def validate_shop_name(raw: str) -> str:
    name = _clean(raw)
    if not name:
        raise MarketTextError("name_empty")
    if len(name) > SHOP_NAME_MAX:
        raise MarketTextError("name_too_long")
    return name


def validate_shop_description(raw: str) -> str:
    description = _clean(raw)
    if not description:
        raise MarketTextError("description_empty")
    if len(description) > SHOP_DESCRIPTION_MAX:
        raise MarketTextError("description_too_long")
    return description


def trade_steps_required(has_mythic: bool) -> int:
    """§29 two confirmation steps; a Mythic item adds the extra one."""
    return TRADE_MYTHIC_CONFIRMATION_STEPS if has_mythic else TRADE_CONFIRMATION_STEPS
