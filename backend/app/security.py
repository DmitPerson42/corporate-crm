"""Хеширование паролей и JWT-токены.

Только стандартная библиотека + PyJWT: ни bcrypt, ни argon2 не требуют сборки
нативных расширений, что важно для переносимости проекта между машинами.
Пароль хранится как PBKDF2-HMAC-SHA256 с индивидуальной солью.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import settings

_PBKDF2_ROUNDS = 390_000  # рекомендация OWASP для PBKDF2-HMAC-SHA256 (2023)
_ALGORITHM_NAME = "pbkdf2_sha256"


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"{_ALGORITHM_NAME}${_PBKDF2_ROUNDS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Сравнение с постоянным временем, чтобы не светить длину/содержимое хеша."""
    try:
        algorithm, rounds, salt_b64, digest_b64 = stored.split("$")
        if algorithm != _ALGORITHM_NAME:
            return False
        expected = _unb64(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _unb64(salt_b64), int(rounds)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, actual)


def create_access_token(subject: int | str, lifetime_seconds: int | None = None) -> tuple[str, int]:
    """Возвращает (токен, сколько секунд он живёт)."""
    now = datetime.now(UTC)
    lifetime = lifetime_seconds if lifetime_seconds is not None else settings.token_lifetime_seconds
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": "manager",  # роль одна, но поле держим: JWT самодостаточен
        "iss": "corporate-crm",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=lifetime)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, lifetime


def decode_access_token(token: str) -> dict[str, Any]:
    """Бросает jwt.PyJWTError, если токен повреждён, просрочен или подписан другим секретом."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer="corporate-crm",
        options={"require": ["exp", "sub"]},
    )
