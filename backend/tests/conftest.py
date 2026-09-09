"""Интеграционные тесты работают с настоящим PostgreSQL в базе crm_test.

Переменная DATABASE_URL подменяется до импорта приложения, поэтому тесты
ни при каких условиях не могут задеть рабочую базу crm_db.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

# Порядок приоритета: переменная окружения процесса -> значение из .env -> известное имя по умолчанию.
_ENV_FILE_VALUES = dotenv_values(Path(__file__).resolve().parents[2] / ".env")


def _setting(name: str, default: str) -> str:
    """Переменная процесса важнее значения из .env, а .env важнее значения по умолчанию."""
    return os.environ.get(name) or _ENV_FILE_VALUES.get(name) or default


# Тесты всегда ходят в отдельную базу: рабочие данные crm_db не пострадают.
os.environ["DATABASE_URL"] = _setting(
    "TEST_DATABASE_URL", "postgresql+asyncpg://crm_user:crm_password@127.0.0.1:5432/crm_test"
)
os.environ["JWT_SECRET"] = "test-secret-only-for-pytest-0123456789abcdef"
os.environ["JWT_EXPIRES_IN"] = "1h"

import httpx
import pytest

from app.db import Base, SessionFactory, engine
from app.main import create_app
from app.models import Manager
from app.security import hash_password

MANAGER_LOGIN = "manager"
MANAGER_PASSWORD = "manager123"
MANAGER_FULL_NAME = "Тестовый Менеджер Тестович"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
async def clean_database():
    """Создаёт схему при первом запуске и очищает таблицы перед каждым тестом."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
    yield


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http_client:
            yield http_client


@pytest.fixture
async def manager() -> Manager:
    async with SessionFactory() as session:
        created = Manager(
            login=MANAGER_LOGIN,
            password_hash=hash_password(MANAGER_PASSWORD),
            full_name=MANAGER_FULL_NAME,
        )
        session.add(created)
        await session.commit()
        await session.refresh(created)
        return created


@pytest.fixture
async def auth(client, manager) -> dict[str, str]:
    """Логинит тестового менеджера и возвращает заголовок с Bearer-токеном."""
    response = await client.post(
        "/api/auth/login", json={"login": MANAGER_LOGIN, "password": MANAGER_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def new_client_record(auth, http_client, **overrides):
    """Создаёт клиента через API и возвращает тело ответа."""
    payload = {
        "last_name": "Петров",
        "first_name": "Сергей",
        "middle_name": "Алексеевич",
        "phone": "+7 (912) 345-67-89",
        "email": "Petrov@Example.ru",
        "property_info": "Квартира 68 м²",
        "comment": "Ключевой клиент",
    } | overrides
    response = await http_client.post("/api/clients", json=payload, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()
