"""Dependency-и FastAPI: проверка заголовка Authorization и получение текущего менеджера."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Manager
from app.security import decode_access_token

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Токен, полученный в POST /api/auth/login. Заголовок: `Authorization: Bearer <токен>`",
)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Требуется авторизация",
    headers={"WWW-Authenticate": "Bearer"},
)


async def current_manager(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Manager:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия сессии истёк, войдите заново",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise CREDENTIALS_ERROR from None

    try:
        manager_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise CREDENTIALS_ERROR from None

    if payload.get("role") != "manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    manager = await session.scalar(select(Manager).where(Manager.id == manager_id))
    if manager is None or not manager.is_active:
        raise CREDENTIALS_ERROR
    return manager
