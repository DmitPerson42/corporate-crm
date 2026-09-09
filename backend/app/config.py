"""Параметры запуска, читаются из переменных окружения и файла .env в корне проекта."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

_DURATION = re.compile(r"^(\d+)\s*([smhdm]?)$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(value: str) -> int:
    """'12h' -> 43200. Голое число трактуется как секунды."""
    match = _DURATION.match(value.strip())
    if not match:
        raise ValueError(f"Некорректный срок действия токена: {value!r}")
    number, unit = int(match.group(1)), (match.group(2) or "s").lower()
    return number * _UNIT_SECONDS[unit]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://crm_user:crm_password@127.0.0.1:5432/crm_db"

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_expires_in: str = "12h"
    jwt_algorithm: str = "HS256"

    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    seed_manager_login: str = "manager"
    seed_manager_password: str = "manager123"
    seed_manager_name: str = "Иванова Ирина Ивановна"

    @field_validator("database_url")
    @classmethod
    def _ensure_asyncpg_driver(cls, value: str) -> str:
        # В .env Convenient-формат postgresql://..., SQLAlchemy ждёт postgresql+asyncpg://
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        return value

    @property
    def token_lifetime_seconds(self) -> int:
        return parse_duration(self.jwt_expires_in)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
