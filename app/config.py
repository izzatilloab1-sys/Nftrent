"""Ilova sozlamalari — .env dan o'qiladi (pydantic-settings)."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Umumiy
    app_name: str = "NFT Rent"
    env: str = "development"
    debug: bool = True

    # Xavfsizlik
    secret_key: str = "dev-insecure-key-change-me"
    session_expire_minutes: int = 10080
    login_max_attempts: int = 5
    login_attempt_window_seconds: int = 300

    # Telegram
    bot_token: str = ""
    bot_username: str = "NftRentBot"
    webapp_url: str = "https://example.com"
    bot_banner_url: str = ""  # ixtiyoriy: boshlanish sahifasi uchun banner rasm URL

    # Admin
    admin_telegram_ids: str = ""

    # Support
    default_support_username: str = "NftRentSupport"

    # DB
    database_url: str = "sqlite+aiosqlite:///./nft_rent.db"

    # TON kursi
    default_ton_uzs_rate: float = 40000.0

    # Marketapp integratsiyasi
    marketapp_integration_enabled: bool = False
    marketapp_api_base: str = ""
    marketapp_api_key: str = ""

    @field_validator("admin_telegram_ids")
    @classmethod
    def _strip_ids(cls, v: str) -> str:
        return v.strip()

    @property
    def admin_ids(self) -> List[int]:
        """Admin Telegram ID lari ro'yxati."""
        if not self.admin_telegram_ids:
            return []
        out: List[int] = []
        for part in self.admin_telegram_ids.split(","):
            part = part.strip()
            if part.isdigit():
                out.append(int(part))
        return out

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
