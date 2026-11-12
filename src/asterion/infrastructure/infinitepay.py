"""InfinitePay checkout API client (https://www.infinitepay.io/checkout-documentacao).

Only two calls exist: create a checkout link and check a payment. The webhook
has no signature, so a notice is never trusted alone: the server always asks
``/payment_check`` before marking an order paid. There is no sandbox and no
refund API (refunds are made in the InfinitePay app).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import aiohttp

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=15)


class PaymentProviderError(RuntimeError):
    """The provider could not be reached or answered something unusable."""


@dataclass(frozen=True, slots=True)
class PaymentCheck:
    success: bool
    paid: bool
    amount_cents: int | None
    paid_amount_cents: int | None
    capture_method: str | None


class PaymentProvider(Protocol):
    name: str

    async def create_link(
        self,
        *,
        order_nsu: str,
        amount_cents: int,
        description: str,
        webhook_url: str,
        valid_until: datetime,
    ) -> str: ...

    async def check(self, *, order_nsu: str, transaction_nsu: str, slug: str) -> PaymentCheck: ...


def _link_url(body: Any) -> str | None:
    """The documentation does not name the response field; accept the usual ones."""
    if isinstance(body, dict):
        for key in ("url", "link", "checkout_url", "payment_url"):
            value = body.get(key)
            if isinstance(value, str) and value.startswith("https://"):
                return value
        for value in body.values():
            found = _link_url(value)
            if found:
                return found
    return None


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class InfinitePayClient:
    name = "infinitepay"

    def __init__(self, handle: str, *, api_key: str | None = None, base_url: str):
        self.handle = handle.removeprefix("$")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        try:
            async with aiohttp.ClientSession(timeout=TIMEOUT) as client:
                async with client.post(
                    f"{self.base_url}{path}", json=body, headers=self._headers()
                ) as response:
                    if response.status >= 400:
                        text = (await response.text())[:300]
                        raise PaymentProviderError(f"{path} HTTP {response.status}: {text}")
                    return await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as error:
            raise PaymentProviderError(f"{path}: {type(error).__name__}: {error}") from error

    async def create_link(
        self,
        *,
        order_nsu: str,
        amount_cents: int,
        description: str,
        webhook_url: str,
        valid_until: datetime,
    ) -> str:
        body: dict[str, Any] = {
            "handle": self.handle,
            "order_nsu": order_nsu,
            "webhook_url": webhook_url,
            "items": [{"quantity": 1, "price": amount_cents, "description": description}],
        }
        if self.api_key:
            # `options` needs the API key: one payment per link, link expiry.
            body["options"] = {
                "single_payment": True,
                "valid_until": valid_until.isoformat(),
            }
        answer = await self._post("/links", body)
        url = _link_url(answer)
        if url is None:
            raise PaymentProviderError("checkout link missing in the provider answer")
        return url

    async def check(self, *, order_nsu: str, transaction_nsu: str, slug: str) -> PaymentCheck:
        answer = await self._post(
            "/payment_check",
            {
                "handle": self.handle,
                "order_nsu": order_nsu,
                "transaction_nsu": transaction_nsu,
                "slug": slug,
            },
        )
        if not isinstance(answer, dict):
            raise PaymentProviderError("payment_check answer is not an object")
        method = answer.get("capture_method")
        return PaymentCheck(
            success=answer.get("success") is True,
            paid=answer.get("paid") is True,
            amount_cents=_int(answer.get("amount")),
            paid_amount_cents=_int(answer.get("paid_amount")),
            capture_method=method if isinstance(method, str) else None,
        )
