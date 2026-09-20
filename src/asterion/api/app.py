from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import text

from asterion.bot.runtime import get_bot_runtime
from asterion.config import get_settings
from asterion.infrastructure.db.session import engine

settings = get_settings()
app = FastAPI(title="Asterion", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "asterion"}


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
