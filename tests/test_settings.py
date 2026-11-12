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


def test_empty_env_values_fall_back_to_defaults(monkeypatch) -> None:
    for name in (
        "ASTERION_COMMUNITY_CHAT_ID",
        "ASTERION_COMMUNITY_MARKET_TOPIC_ID",
        "ASTERION_COMMUNITY_RELATOS_TOPIC_ID",
        "ASTERION_PATRON_PRICE_CENTS",
        "ASTERION_PAYMENTS_WEBHOOK_TOKEN",
        "ASTERION_TELEGRAM_BOT_TOKEN",
    ):
        monkeypatch.setenv(name, "")
    settings = Settings(_env_file=None, telegram_bot_enabled=False)
    assert settings.community_chat_id is None
    assert settings.community_market_topic_id is None
    assert settings.community_relatos_topic_id is None
    assert settings.patron_price_cents is None
    assert settings.payments_webhook_token is None
    assert settings.telegram_bot_token is None
