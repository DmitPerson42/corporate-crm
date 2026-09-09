"""Сквозная проверка уже запущенной системы.

В отличие от pytest-тестов, которые вызывают FastAPI напрямую, этот скрипт идёт
через dev-сервер Vite (http://127.0.0.1:5173/api/...) и потому проверяет ещё и
связку «прокси + backend + PostgreSQL», с которой работает браузер.

Запуск (предварительно должны работать backend и frontend — например, scripts\\start.cmd):
    backend\\.venv\\Scripts\\python.exe scripts\\smoke-test.py
    backend\\.venv\\Scripts\\python.exe scripts\\smoke-test.py --base-url http://127.0.0.1:5173
"""

from __future__ import annotations

import argparse
import sys
import uuid

import httpx

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, details: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  OK   {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL {name} {('— ' + details) if details else ''}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Сквозная проверка КИС")
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--login", default="manager")
    parser.add_argument("--password", default="manager123")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    print(f"Проверяю {base}\n")

    with httpx.Client(timeout=15.0) as client:
        print("[0] Доступность страницы и API")
        try:
            page = client.get(f"{base}/")
            check("отдаётся HTML одностраничного приложения", page.status_code == 200 and 'id="root"' in page.text, f"код {page.status_code}")
        except httpx.HTTPError as exc:
            check("frontend доступен", False, str(exc))
            print("\nFrontend не отвечает — запустите scripts\\start.cmd")
            return 1

        try:
            health = client.get(f"{base}/api/health")
            body = health.json()
            check("backend отвечает через прокси", health.status_code == 200, f"код {health.status_code}")
            check("PostgreSQL подключён", body.get("database") == "up", str(body))
        except httpx.HTTPError as exc:
            check("backend доступен", False, str(exc))
            print("\nBackend не отвечает — проверьте окно «CIS backend» и .env")
            return 1

        print("\n[1] Авторизация")
        bad = client.post(f"{base}/api/auth/login", json={"login": args.login, "password": "не-тот-пароль"})
        check("неверный пароль отклоняётся (401)", bad.status_code == 401, f"код {bad.status_code}")

        anonymous = client.get(f"{base}/api/clients")
        check("список клиентов без токена закрыт (401)", anonymous.status_code == 401, f"код {anonymous.status_code}")

        logged_in = client.post(
            f"{base}/api/auth/login", json={"login": args.login, "password": args.password}
        )
        check("вход manager/manager123 успешен", logged_in.status_code == 200, logged_in.text[:120])
        if logged_in.status_code != 200:
            print("\nНе удалось войти — дальше тесты не имеют смысла.")
            return 1
        token = logged_in.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        check("в ответе есть срок жизни токена", logged_in.json()["expires_in"] > 0)

        me = client.get(f"{base}/api/auth/me", headers=headers)
        check("эндпоинт /auth/me возвращает менеджера", me.status_code == 200 and me.json()["login"] == args.login, me.text[:120])

        print("\n[2] Жизненный цикл карточки клиента")
        tag = uuid.uuid4().hex[:6]
        surname = f"Тестовый{tag}"
        created = client.post(
            f"{base}/api/clients",
            headers=headers,
            json={
                "last_name": surname,
                "first_name": "Игнат",
                "middle_name": "Панкратович",
                "phone": "+7 (900) 123-45-67",
                "email": f"smoke-{tag}@example.ru",
                "property_info": "Гараж 24 м² и вклад в банке",
                "comment": "Запись создана проверкой smoke-test",
            },
        )
        check("клиент заведён (201)", created.status_code == 201, created.text[:160])
        if created.status_code != 201:
            return 1
        client_id = created.json()["id"]

        invalid = client.post(f"{base}/api/clients", headers=headers, json={"first_name": "Без фамилии"})
        check("клиент без фамилии не проходит валидацию (422)", invalid.status_code == 422, f"код {invalid.status_code}")

        bad_email = client.post(
            f"{base}/api/clients",
            headers=headers,
            json={"last_name": "Плохая", "first_name": "Почта", "email": "не-адрес"},
        )
        check("некорректный e-mail отклоняется (422)", bad_email.status_code == 422, f"код {bad_email.status_code}")

        searched = client.get(f"{base}/api/clients", headers=headers, params={"q": surname})
        check("новый клиент находится поиском по фамилии", searched.json()["total"] == 1, str(searched.json()["total"]))

        by_phone = client.get(f"{base}/api/clients", headers=headers, params={"q": "900 123"})
        found_ids = [item["id"] for item in by_phone.json()["items"]]
        check("поиск по фрагменту телефона находит карточку", client_id in found_ids, str(found_ids))

        edited = client.put(
            f"{base}/api/clients/{client_id}",
            headers=headers,
            json={"phone": "+7 (900) 999-00-11", "property_info": "Гараж 24 м², вклад, добавлен телескоп"},
        )
        check("карточка отредактирована", edited.status_code == 200, edited.text[:160])
        check(
            "изменилось только переданное поле",
            edited.json()["email"] == f"smoke-{tag}@example.ru" and edited.json()["phone"] == "+7 (900) 999-00-11",
            edited.text[:160],
        )

        comment = client.post(
            f"{base}/api/clients/{client_id}/comments",
            headers=headers,
            json={"text": "Позвонил, обсудили продление — ждём второй документ"},
        )
        check("комментарий добавлен (201)", comment.status_code == 201, comment.text[:160])
        check("в комментарии указан автор", bool(comment.json().get("author_name")), comment.text[:120])

        detail = client.get(f"{base}/api/clients/{client_id}", headers=headers)
        check("в карточке виден комментарий", len(detail.json()["comments"]) == 1, str(len(detail.json()["comments"])))

        listed = client.get(f"{base}/api/clients", headers=headers, params={"q": surname})
        check("счётчик комментариев отображается в списке", listed.json()["items"][0]["comments_count"] == 1)

        print("\n[3] Удаление и проверка документации")
        removed = client.delete(f"{base}/api/clients/{client_id}", headers=headers)
        check("клиент удалён (204)", removed.status_code == 204, f"код {removed.status_code}")
        gone = client.get(f"{base}/api/clients/{client_id}", headers=headers)
        check("удалённый клиент недоступен (404)", gone.status_code == 404, f"код {gone.status_code}")

        docs = client.get(f"{base.replace(':5173', ':8000')}/docs")
        check("Swagger-документация доступна на :8000", docs.status_code == 200, f"код {docs.status_code}")

    print(f"\nИтого: пройдено {len(PASSED)}, провалено {len(FAILED)}.")
    if FAILED:
        print("Проваленные проверки: " + "; ".join(FAILED))
        return 1
    print("Система работает: вход, реестр клиентов, редактирование, комментарии.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
