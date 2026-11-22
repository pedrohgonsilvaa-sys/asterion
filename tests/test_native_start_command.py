from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from asterion.bot import polling
from asterion.bot.polling import BOT_COMMANDS, register_bot_commands


def test_start_is_the_only_native_command_with_friendly_description():
    assert [(c.command, c.description) for c in BOT_COMMANDS] == [
        ("start", "Abrir o Asterion")
    ]


async def test_register_bot_commands_publishes_start_to_native_menu():
    bot = MagicMock()
    bot.set_my_commands = AsyncMock()

    await register_bot_commands(bot)

    bot.set_my_commands.assert_awaited_once_with(BOT_COMMANDS)


async def test_polling_registers_native_commands_before_starting_polling(monkeypatch):
    calls: list[str] = []
    bot = MagicMock()
    bot.session.close = AsyncMock()

    async def set_my_commands(commands):
        calls.append("set_my_commands")

    async def start_polling(_bot):
        calls.append("start_polling")

    bot.set_my_commands = set_my_commands
    dispatcher = SimpleNamespace(start_polling=start_polling)
    runtime = SimpleNamespace(bot=bot, dispatcher=dispatcher)
    settings = SimpleNamespace(
        telegram_bot_enabled=True, telegram_mode="polling", metrics_port=None
    )
    scheduler = MagicMock()

    monkeypatch.setattr(polling, "get_settings", lambda: settings)
    monkeypatch.setattr(polling, "get_bot_runtime", lambda: runtime)
    monkeypatch.setattr(polling, "warm_photo_file_ids", AsyncMock())
    monkeypatch.setattr(polling, "build_round_scheduler", lambda: scheduler)

    await polling._run()

    assert calls == ["set_my_commands", "start_polling"]
