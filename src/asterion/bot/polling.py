import asyncio

from asterion.bot.round_scheduler import build_round_scheduler
from asterion.bot.runtime import get_bot_runtime
from asterion.config import get_settings


async def _run() -> None:
    settings = get_settings()
    if not settings.telegram_bot_enabled:
        raise RuntimeError("Enable ASTERION_TELEGRAM_BOT_ENABLED before starting polling")
    if settings.telegram_mode != "polling":
        raise RuntimeError("Polling process can only run when ASTERION_TELEGRAM_MODE=polling")

    runtime = get_bot_runtime()
    scheduler = build_round_scheduler()
    scheduler.start()
    try:
        await runtime.dispatcher.start_polling(runtime.bot)
    finally:
        scheduler.shutdown(wait=False)
        await runtime.bot.session.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
