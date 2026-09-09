"""Проверки авторизации и служебного эндпоинта."""

from __future__ import annotations

import jwt

from app.config import settings
from app.db import SessionFactory
from app.models import Manager
from tests.conftest import MANAGER_FULL_NAME, MANAGER_LOGIN, MANAGER_PASSWORD


async def test_health_reports_database_up(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"


async def test_login_returns_token_and_manager(client, manager):
    response = await client.post(
        "/api/auth/login", json={"login": MANAGER_LOGIN, "password": MANAGER_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["manager"] == {"id": manager.id, "login": MANAGER_LOGIN, "full_name": MANAGER_FULL_NAME}
    payload = jwt.decode(body["access_token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == str(manager.id)
    assert payload["role"] == "manager"


async def test_login_trims_surrounding_spaces(client, manager):
    response = await client.post(
        "/api/auth/login", json={"login": f"  {MANAGER_LOGIN}  ", "password": MANAGER_PASSWORD}
    )
    assert response.status_code == 200


async def test_login_with_wrong_password_is_401(client, manager):
    response = await client.post(
        "/api/auth/login", json={"login": MANAGER_LOGIN, "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль"


async def test_login_with_unknown_manager_uses_same_message(client, manager):
    response = await client.post(
        "/api/auth/login", json={"login": "netakogo", "password": MANAGER_PASSWORD}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль"


async def test_login_with_empty_body_is_422(client, manager):
    response = await client.post("/api/auth/login", json={"login": "", "password": ""})
    assert response.status_code == 422


async def test_me_requires_valid_token(client, manager):
    missing = await client.get("/api/auth/me")
    assert missing.status_code == 401

    garbage = await client.get("/api/auth/me", headers={"Authorization": "Bearer abrakadabra"})
    assert garbage.status_code == 401

    forged = jwt.encode(
        {"sub": str(manager.id), "role": "manager"},
        "another-secret-key-with-enough-length-0123456789",
        algorithm="HS256",
    )
    foreign_signature = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert foreign_signature.status_code == 401

    token = (
        await client.post(
            "/api/auth/login", json={"login": MANAGER_LOGIN, "password": MANAGER_PASSWORD}
        )
    ).json()["access_token"]
    ok = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
    assert ok.json()["login"] == MANAGER_LOGIN


async def test_expired_token_is_rejected(client, manager):
    import datetime as dt

    expired = jwt.encode(
        {
            "sub": str(manager.id),
            "role": "manager",
            "iss": "corporate-crm",
            "exp": dt.datetime.now(dt.UTC) - dt.timedelta(seconds=60),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert "истёк" in response.json()["detail"]


async def test_disabled_manager_cannot_login(client, manager):
    async with SessionFactory() as session:
        stored = await session.get(Manager, manager.id)
        stored.is_active = False
        await session.commit()

    response = await client.post(
        "/api/auth/login", json={"login": MANAGER_LOGIN, "password": MANAGER_PASSWORD}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Учётная запись отключена"
