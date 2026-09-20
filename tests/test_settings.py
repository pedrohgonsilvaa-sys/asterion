import pytest
from pydantic import ValidationError

from asterion.config import Settings


def test_bot_can_be_disabled_without_token() -> None:
    settings = Settings(_env_file=None, telegram_bot_enabled=False)
    assert settings.telegram_bot_token is None


def test_enabled_bot_requires_token() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, telegram_bot_enabled=True, telegram_bot_token=None)


def test_webhook_mode_requires_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            telegram_bot_enabled=True,
            telegram_bot_token="test-token",
            telegram_mode="webhook",
            telegram_webhook_secret=None,
        )
