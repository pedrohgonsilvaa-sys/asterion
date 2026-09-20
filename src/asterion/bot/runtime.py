from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher

from asterion.application.creation import CreationService
from asterion.bot.creation_handlers import creation_router
from asterion.config import get_settings
from asterion.domain.creation import NamePolicy
from asterion.infrastructure.db.session import SessionFactory


@dataclass(frozen=True, slots=True)
class BotRuntime:
    bot: Bot
    dispatcher: Dispatcher


@lru_cache
def get_bot_runtime() -> BotRuntime:
    settings = get_settings()
    if not settings.telegram_bot_enabled or not settings.telegram_bot_token:
        raise RuntimeError("Telegram bot is disabled or has no token configured")

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        creation_router(
            CreationService(
                SessionFactory,
                settings.server_id,
                NamePolicy(settings.blocked_character_names),
            ),
            settings.creation_images,
        )
    )
    return BotRuntime(
        bot=Bot(token=settings.telegram_bot_token),
        dispatcher=dispatcher,
    )
