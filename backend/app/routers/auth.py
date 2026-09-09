"""Эндпоинты входа менеджера и получения текущего пользователя."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import current_manager
from app.models import Manager
from app.schemas import LoginRequest, ManagerOut, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["Авторизация"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход по логину и паролю",
    description="Выдаёт JWT-токен доступа, который фронтенд подставляет в заголовок `Authorization`.",
)
async def login(payload: LoginRequest, response: Response, session: AsyncSession = Depends(get_session)):
    login_name = payload.login.strip()
    manager = await session.scalar(select(Manager).where(Manager.login == login_name))

    # Одинаковое сообщение для «нет такого логина» и «неверный пароль» —
    # иначе по ответу можно перебирать существующие учётные записи.
    if manager is None or not verify_password(payload.password, manager.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль"
        )
    if not manager.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Учётная запись отключена"
        )

    token, lifetime = create_access_token(manager.id)
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=token,
        expires_in=lifetime,
        manager=ManagerOut.model_validate(manager),
    )


@router.get("/me", response_model=ManagerOut, summary="Текущий менеджер")
async def me(manager: Manager = Depends(current_manager)) -> Manager:
    return manager
