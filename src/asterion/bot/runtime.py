from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher

from asterion.config import get_settings


@dataclass(frozen=True, slots=True)
class BotRuntime:
    bot: Bot
    dispatcher: Dispatcher


@lru_cache
def get_bot_runtime() -> BotRuntime:
    settings = get_settings()
    if not settings.telegram_bot_enabled or not settings.telegram_bot_token:
        raise RuntimeError("Telegram bot is disabled or has no token configured")

    return BotRuntime(
        bot=Bot(token=settings.telegram_bot_token),
        dispatcher=Dispatcher(),
    )
