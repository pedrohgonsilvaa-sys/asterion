import hmac
import json
import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from asterion.application.outbox import outbox_stats
from asterion.application.payments import (
    PaymentError,
    PaymentService,
    build_provider,
    payment_config,
)
from asterion.bot.round_scheduler import build_round_scheduler
from asterion.bot.runtime import get_bot_runtime
from asterion.config import get_settings
from asterion.infrastructure.db.session import SessionFactory, engine
from asterion.infrastructure.metrics import CONTENT_TYPE, authorized, render_metrics

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="Asterion", version="0.1.0")
round_scheduler = (
    build_round_scheduler()
    if settings.telegram_bot_enabled and settings.telegram_mode == "webhook"
    else None
)


@app.on_event("startup")
async def start_round_scheduler() -> None:
    if round_scheduler is not None and not round_scheduler.running:
        round_scheduler.start()


@app.on_event("shutdown")
async def stop_round_scheduler() -> None:
    if round_scheduler is not None and round_scheduler.running:
        round_scheduler.shutdown(wait=False)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "asterion"}


@app.get("/health/outbox")
async def outbox_health() -> dict[str, object]:
    stats = await outbox_stats(SessionFactory)
    return {
        "counts": stats.counts,
        "oldest_open_age_seconds": stats.oldest_open_age_seconds,
    }


@app.get("/metrics", include_in_schema=False)
async def metrics(authorization: Annotated[str | None, Header()] = None) -> Response:
    if not authorized(authorization, settings.metrics_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    body = await render_metrics(engine, SessionFactory)
    return Response(content=body, media_type=CONTENT_TYPE)


@app.get("/ready")
async def ready() -> dict[str, str]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        redis = Redis.from_url(settings.redis_url)
        try:
            await redis.ping()
        finally:
            await redis.aclose()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dependencies are not ready",
        ) from exc
    return {"status": "ready"}


@app.post("/telegram/webhook", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    if not settings.telegram_bot_enabled or settings.telegram_mode != "webhook":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    runtime = get_bot_runtime()
    update = await request.json()
    await runtime.dispatcher.feed_raw_update(runtime.bot, update)
    return {"ok": True}


@lru_cache
def get_payment_service() -> PaymentService:
    return PaymentService(
        SessionFactory, settings.server_id, payment_config(settings), build_provider(settings)
    )


def _webhook_token() -> str | None:
    return settings.payments_webhook_token


@app.post("/payments/infinitepay/webhook", include_in_schema=False)
async def infinitepay_webhook(
    request: Request,
    payments: Annotated[PaymentService, Depends(get_payment_service)],
    expected: Annotated[str | None, Depends(_webhook_token)],
    token: Annotated[str, Query()] = "",
) -> JSONResponse:
    """GDD §35.2. The notice has no signature: it is only stored and queued; the
    Outbox confirms it with /payment_check before anything is delivered.
    200 = stored (or already known); 400 = rejected, the provider retries."""
    if not expected or not hmac.compare_digest(token, expected):
        return JSONResponse({"ok": False}, status_code=status.HTTP_400_BAD_REQUEST)
    try:
        body = json.loads(await request.body())
    except ValueError:
        return JSONResponse({"ok": False}, status_code=status.HTTP_400_BAD_REQUEST)
    if not isinstance(body, dict):
        return JSONResponse({"ok": False}, status_code=status.HTTP_400_BAD_REQUEST)
    try:
        outcome = await payments.record_notice(body)
    except PaymentError:
        logger.warning("payment notice rejected: %s", str(body.get("order_nsu"))[:160])
        return JSONResponse({"ok": False}, status_code=status.HTTP_400_BAD_REQUEST)
    return JSONResponse({"ok": True, "result": outcome})
