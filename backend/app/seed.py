"""Создание учётной записи менеджера (и, по желанию, демонстрационных карточек).

Запуск из каталога backend:
    python -m app.seed            # только менеджер из .env
    python -m app.seed --demo     # + три клиента для показа системы
    python -m app.seed --demo --reset
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete, func, select

from app.config import settings
from app.db import SessionFactory, engine
from app.models import Client, ClientComment, Manager
from app.security import hash_password

DEMO_CLIENTS: list[dict] = [
    {
        "last_name": "Петров",
        "first_name": "Сергей",
        "middle_name": "Алексеевич",
        "phone": "+7 (912) 345-67-89",
        "email": "petrov@example.ru",
        "property_info": "Квартира 68 м² (Москвская обл.), автомобиль Skoda Octavia 2021 г.",
        "comment": "Ключевой клиент, договор №104 от 12.02.2025.",
        "comments": [
            "Продлил обслуживание на год, запрашивал второй комплект документов.",
            "Перезвонить после 18:00 — daytime недоступен.",
        ],
    },
    {
        "last_name": "Иванова",
        "first_name": "Мария",
        "middle_name": "Дмитриевна",
        "phone": "+7 (921) 118-22-33",
        "email": "ivanova.md@example.com",
        "property_info": "Земельный участок 12 соток, жилой дом 145 м².",
        "comment": "Ведёт юрист отдела сопровождения.",
        "comments": ["Уточнить статус оценки имущества у подрядчика."],
    },
    {
        "last_name": "Ковалёв",
        "first_name": "Денис",
        "middle_name": None,
        "phone": None,
        "email": "kovalyov@example.ru",
        "property_info": None,
        "comment": "Новая заявка, сведения об имуществе собираются.",
        "comments": [],
    },
]


async def seed(*, demo: bool, reset: bool) -> None:
    if reset:
        async with SessionFactory() as session:
            await session.execute(delete(ClientComment))
            await session.execute(delete(Client))
            await session.execute(delete(Manager))
            await session.commit()
        print("Таблицы очищены.")

    async with SessionFactory() as session:
        manager = await session.scalar(select(Manager).where(Manager.login == settings.seed_manager_login))
        if manager is None:
            manager = Manager(
                login=settings.seed_manager_login,
                password_hash=hash_password(settings.seed_manager_password),
                full_name=settings.seed_manager_name,
            )
            session.add(manager)
            await session.commit()
            print(f"Создан менеджер: {manager.login} ({manager.full_name})")
        else:
            await session.commit()
            print(f"Менеджер {manager.login} уже существует — пропускаю.")

        if not demo:
            return

        existing = await session.scalar(select(func.count(Client.id)))
        if existing:
            print(f"В таблице уже {existing} клиентов — демонстрационные записи не добавляю.")
            return

        for data in DEMO_CLIENTS:
            payload = {key: value for key, value in data.items() if key != "comments"}
            client = Client(**payload, created_by_id=manager.id)
            session.add(client)
            await session.flush()
            for text in data["comments"]:
                session.add(
                    ClientComment(
                        client_id=client.id,
                        author_id=manager.id,
                        author_name=manager.full_name,
                        text=text,
                    )
                )
        await session.commit()
        print(f"Добавлено демонстрационных клиентов: {len(DEMO_CLIENTS)}.")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнение базы данных КИС")
    parser.add_argument("--demo", action="store_true", help="добавить примеры клиентов")
    parser.add_argument("--reset", action="store_true", help="очистить таблицы перед заполнением")
    args = parser.parse_args()
    asyncio.run(seed(demo=args.demo, reset=args.reset))


if __name__ == "__main__":
    main()
