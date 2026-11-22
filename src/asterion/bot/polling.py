import asyncio

from aiogram.types import BotCommand

from asterion.bot.creation_handlers import warm_photo_file_ids
from asterion.bot.metrics_server import start_metrics_server
from asterion.bot.round_scheduler import build_round_scheduler
from asterion.bot.runtime import get_bot_runtime
from asterion.config import get_settings
from asterion.infrastructure.db.session import SessionFactory, engine

# Commands shown in Telegram's native Menu button. /start resumes the player's current
# persistent state (menu, combat, PvP, dungeon...); it never forces the main menu.
BOT_COMMANDS = [
    BotCommand(command="start", description="Abrir o Asterion"),
]


async def register_bot_commands(bot) -> None:
    await bot.set_my_commands(BOT_COMMANDS)


async def _run() -> None:
    settings = get_settings()
    if not settings.telegram_bot_enabled:
        raise RuntimeError("Enable ASTERION_TELEGRAM_BOT_ENABLED before starting polling")
    if settings.telegram_mode != "polling":
        raise RuntimeError("Polling process can only run when ASTERION_TELEGRAM_MODE=polling")

    runtime = get_bot_runtime()
    await warm_photo_file_ids()
    metrics_runner = None
    if settings.metrics_port is not None:
        metrics_runner = await start_metrics_server(
            engine, SessionFactory, port=settings.metrics_port, token=settings.metrics_token
        )
    scheduler = build_round_scheduler()
    scheduler.start()
    try:
        await register_bot_commands(runtime.bot)
        await runtime.dispatcher.start_polling(runtime.bot)
    finally:
        scheduler.shutdown(wait=False)
        if metrics_runner is not None:
            await metrics_runner.cleanup()
        await runtime.bot.session.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
