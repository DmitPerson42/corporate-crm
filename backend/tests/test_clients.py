"""Проверки карточек клиентов: создание, поиск, редактирование, комментарии, удаление."""

from __future__ import annotations

from tests.conftest import new_client_record

MINIMAL = {"last_name": "Ковалёв", "first_name": "Денис"}


async def test_list_requires_auth(client):
    response = await client.get("/api/clients")
    assert response.status_code == 401


async def test_create_client_normalizes_input(client, auth):
    created = await new_client_record(auth, client)

    assert created["email"] == "petrov@example.ru"  # приводим к нижнему регистру
    assert created["full_name"] == "Петров Сергей Алексеевич"
    assert created["comments_count"] == 0
    assert created["created_by_name"] == "Тестовый Менеджер Тестович"
    assert created["created_at"] and created["updated_at"]


async def test_create_client_with_only_required_fields(client, auth):
    response = await client.post("/api/clients", json=MINIMAL, headers=auth)
    assert response.status_code == 201
    body = response.json()
    assert body["middle_name"] is None
    assert body["phone"] is None
    assert body["property_info"] is None
    assert body["full_name"] == "Ковалёв Денис"


async def test_blank_strings_become_null(client, auth):
    response = await client.post(
        "/api/clients",
        json=MINIMAL | {"middle_name": "   ", "phone": "", "comment": "  \n "},
        headers=auth,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["middle_name"] is None
    assert body["phone"] is None
    assert body["comment"] is None


async def test_validation_errors(client, auth):
    cases = [
        ({"first_name": "Сергей"}, "нет фамилии"),
        ({"last_name": "П"}, "фамилия короче двух символов"),
        (MINIMAL | {"email": "не-почта"}, "некорректный e-mail"),
        (MINIMAL | {"phone": "+7-abc-999"}, "некорректный телефон"),
        ({}, "пустое тело"),
    ]
    for payload, reason in cases:
        response = await client.post("/api/clients", json=payload, headers=auth)
        assert response.status_code == 422, f"{reason}: получен {response.status_code}"


async def test_list_is_ordered_and_paginated(client, auth):
    for name in ("Петров", "Иванова", "Ковалёв", "Сидорова"):
        await new_client_record(auth, client, last_name=name, first_name="Тест")

    first_page = (await client.get("/api/clients?limit=2&offset=0", headers=auth)).json()
    assert first_page["total"] == 4
    assert first_page["limit"] == 2
    assert first_page["offset"] == 0
    assert [item["last_name"] for item in first_page["items"]] == ["Иванова", "Ковалёв"]

    second_page = (await client.get("/api/clients?limit=2&offset=2", headers=auth)).json()
    assert [item["last_name"] for item in second_page["items"]] == ["Петров", "Сидорова"]


async def test_search_matches_name_phone_email_and_property(client, auth):
    await new_client_record(auth, client)
    await new_client_record(
        auth,
        client,
        last_name="Иванова",
        first_name="Мария",
        middle_name="Дмитриевна",
        phone="+7 (921) 118-22-33",
        email="ivanova@example.com",
        property_info="Земельный участок 12 соток",
    )

    for query in ("петров", "Петров Сер", "921 118", "ivanova@example.com", "соток"):
        body = (await client.get(f"/api/clients?q={query}", headers=auth)).json()
        assert body["total"] == 1, f"запрос {query!r} вернул {body['total']} записей"

    nothing = (await client.get("/api/clients?q=несуществующийклиент", headers=auth)).json()
    assert nothing["items"] == []
    assert nothing["total"] == 0


async def test_search_is_case_insensitive_for_cyrillic(client, auth):
    await new_client_record(auth, client, last_name="Ковалёв")
    for query in ("ковалёв", "КОВАЛЁВ", "Ковалёв"):
        body = (await client.get(f"/api/clients?q={query}", headers=auth)).json()
        assert body["total"] == 1, f"запрос {query!r} не найден"


async def test_get_detail_and_404(client, auth):
    created = await new_client_record(auth, client)
    detail = await client.get(f"/api/clients/{created['id']}", headers=auth)
    assert detail.status_code == 200
    assert detail.json()["full_name"] == "Петров Сергей Алексеевич"
    assert detail.json()["comments"] == []

    missing = await client.get("/api/clients/999999", headers=auth)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Клиент не найден"


async def test_update_changes_only_given_fields(client, auth):
    created = await new_client_record(auth, client)
    response = await client.put(
        f"/api/clients/{created['id']}", json={"phone": "+7 (999) 000-11-22"}, headers=auth
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "+7 (999) 000-11-22"
    assert body["last_name"] == "Петров"
    assert body["email"] == "petrov@example.ru"
    assert body["property_info"] == "Квартира 68 м²"
    assert body["updated_at"] >= created["updated_at"]


async def test_update_can_clear_optional_field(client, auth):
    created = await new_client_record(auth, client)
    response = await client.put(
        f"/api/clients/{created['id']}", json={"comment": None}, headers=auth
    )
    assert response.status_code == 200
    assert response.json()["comment"] is None


async def test_update_rejects_invalid_and_empty_payloads(client, auth):
    created = await new_client_record(auth, client)
    bad = await client.put(f"/api/clients/{created['id']}", json={"email": "хрень"}, headers=auth)
    assert bad.status_code == 422

    empty = await client.put(f"/api/clients/{created['id']}", json={}, headers=auth)
    assert empty.status_code == 400

    missing = await client.put("/api/clients/424242", json={"phone": "+79001234567"}, headers=auth)
    assert missing.status_code == 404


async def test_comments_are_appended_and_counted(client, auth):
    created = await new_client_record(auth, client)

    first = await client.post(
        f"/api/clients/{created['id']}/comments",
        json={"text": "Позвонить после 18:00"},
        headers=auth,
    )
    assert first.status_code == 201
    assert first.json()["author_name"] == "Тестовый Менеджер Тестович"

    second = await client.post(
        f"/api/clients/{created['id']}/comments",
        json={"text": "Предложил расширить договор"},
        headers=auth,
    )
    assert second.status_code == 201

    detail = (await client.get(f"/api/clients/{created['id']}", headers=auth)).json()
    assert [c["text"] for c in detail["comments"]] == [
        "Позвонить после 18:00",
        "Предложил расширить договор",
    ]

    listed = (await client.get("/api/clients", headers=auth)).json()
    assert listed["items"][0]["comments_count"] == 2

    only_comments = await client.get(f"/api/clients/{created['id']}/comments", headers=auth)
    assert only_comments.status_code == 200
    assert len(only_comments.json()) == 2


async def test_comment_validation(client, auth):
    created = await new_client_record(auth, client)
    blank = await client.post(
        f"/api/clients/{created['id']}/comments", json={"text": "   "}, headers=auth
    )
    assert blank.status_code == 422

    too_long = await client.post(
        f"/api/clients/{created['id']}/comments", json={"text": "а" * 5000}, headers=auth
    )
    assert too_long.status_code == 422

    orphan = await client.post(
        "/api/clients/888888/comments", json={"text": "есть ли тут кто?"}, headers=auth
    )
    assert orphan.status_code == 404


async def test_comments_require_auth(client, auth):
    created = await new_client_record(auth, client)
    anonymous = await client.post(f"/api/clients/{created['id']}/comments", json={"text": "привет"})
    assert anonymous.status_code == 401


async def test_delete_client_removes_comments(client, auth):
    created = await new_client_record(auth, client)
    await client.post(
        f"/api/clients/{created['id']}/comments", json={"text": "Запись журнала"}, headers=auth
    )

    response = await client.delete(f"/api/clients/{created['id']}", headers=auth)
    assert response.status_code == 204

    gone = await client.get(f"/api/clients/{created['id']}", headers=auth)
    assert gone.status_code == 404

    remaining = (await client.get("/api/clients", headers=auth)).json()
    assert remaining["total"] == 0
