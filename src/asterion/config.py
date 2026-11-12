from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASTERION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+asyncpg://asterion:asterion@localhost:5432/asterion"
    redis_url: str = "redis://localhost:6379/0"

    server_id: str = Field(default="asterion", min_length=1, max_length=64)
    blocked_character_names: frozenset[str] = frozenset()
    # Official Telegram file_ids or file: paths, keyed by screen ID. No bundled artwork.
    creation_images: dict[str, str] = {}

    telegram_bot_enabled: bool = False
    telegram_bot_token: str | None = None
    telegram_mode: Literal["polling", "webhook"] = "polling"
    telegram_webhook_secret: str | None = None
    # Technical flood guard per player (not a game rule): burst size and refill per second.
    rate_limit_burst: int = Field(default=12, ge=1)
    rate_limit_per_second: float = Field(default=4.0, gt=0)
    # Community supergroup and its Mercado topic; unset means Divulgar shows copy text.
    community_chat_id: int | None = None
    community_market_topic_id: int | None = None
    # Relatos topic of the same supergroup; unset means Compartilhar História is off.
    community_relatos_topic_id: int | None = None
    # §32.3 public invite link of the Comunidade Oficial; never hardcoded.
    community_url: str | None = None
    # Operation metrics and alerts (B6). Not game rules: technical thresholds.
    # Port of the /metrics server inside the polling bot; unset means no server.
    metrics_port: int | None = Field(default=None, ge=1, le=65535)
    # When set, /metrics requires "Authorization: Bearer <token>".
    metrics_token: str | None = None
    # Telegram chat that receives operator alerts; unset means alerts are off.
    alert_chat_id: int | None = None
    alert_job_failures: int = Field(default=3, ge=1)
    alert_outbox_backlog: int = Field(default=500, ge=1)
    alert_outbox_age_seconds: int = Field(default=1800, ge=60)
    alert_cooldown_seconds: int = Field(default=1800, ge=60)

    @field_validator(
        "community_chat_id",
        "community_market_topic_id",
        "community_relatos_topic_id",
        "metrics_port",
        "alert_chat_id",
        mode="before",
    )
    @classmethod
    def blank_is_none(cls, value: object) -> object:
        # .env.example leaves these blank ("VAR="); blank means unset, not an error.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_telegram(self) -> Self:
        if self.telegram_bot_enabled and not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required when the Telegram bot is enabled")
        if (
            self.telegram_bot_enabled
            and self.telegram_mode == "webhook"
            and not self.telegram_webhook_secret
        ):
            raise ValueError("TELEGRAM_WEBHOOK_SECRET is required in webhook mode")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
