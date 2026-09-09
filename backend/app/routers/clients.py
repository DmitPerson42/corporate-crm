"""CRUD карточек клиента и журнал дополнений."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db import get_session
from app.deps import current_manager
from app.models import Client, ClientComment, Manager
from app.schemas import (
    ClientCreate,
    ClientDetail,
    ClientList,
    ClientOut,
    ClientUpdate,
    CommentCreate,
    CommentOut,
)

router = APIRouter(prefix="/api/clients", tags=["Клиенты"])


def _search_conditions(query: str | None) -> list:
    """Условие «поиск по любому из реквизитов клиента».

    Ищем и по отдельным полям (телефон, e-mail, имущество), и по склеенному ФИО,
    чтобы запрос «Петров Сер» тоже находил карточку. Телефон сравнивается по одним
    цифрам: менеджер набирает «921 118», а в базе «+7 (921) 118-22-33».
    """
    if not query or not query.strip():
        return []
    normalized = " ".join(query.strip().split())
    pattern = f"%{normalized}%"
    fio = func.concat(
        Client.last_name, " ", Client.first_name, " ", func.coalesce(Client.middle_name, "")
    )
    terms = [
        fio.ilike(pattern),
        Client.last_name.ilike(pattern),
        Client.first_name.ilike(pattern),
        Client.middle_name.ilike(pattern),
        Client.phone.ilike(pattern),
        Client.email.ilike(pattern),
        Client.property_info.ilike(pattern),
        Client.comment.ilike(pattern),
    ]

    digits = re.sub(r"\D", "", normalized)
    if len(digits) >= 3 and not re.search(r"[^\d+\-()\s.]", normalized):
        phone_digits = func.regexp_replace(Client.phone, "[^0-9]+", "", "g")
        terms.append(phone_digits.ilike(f"%{digits}%"))

    return [or_(*terms)]


async def _comment_counts(session: AsyncSession, clients: list[Client]) -> dict[int, int]:
    if not clients:
        return {}
    ids = [client.id for client in clients]
    rows = await session.execute(
        select(ClientComment.client_id, func.count(ClientComment.id))
        .where(ClientComment.client_id.in_(ids))
        .group_by(ClientComment.client_id)
    )
    return dict(rows.all())


def _to_out(client: Client, comments_count: int) -> ClientOut:
    return ClientOut.model_validate(client).model_copy(
        update={
            "comments_count": comments_count,
            "created_by_name": client.created_by.full_name if client.created_by else None,
        }
    )


async def _get_client(session: AsyncSession, client_id: int, *, with_comments: bool = False):
    stmt: Select = select(Client).where(Client.id == client_id)
    if with_comments:
        stmt = stmt.options(
            selectinload(Client.comments).joinedload(ClientComment.author),
            joinedload(Client.created_by),
        )
    else:
        stmt = stmt.options(joinedload(Client.created_by))
    client = await session.scalar(stmt)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден")
    return client


@router.get("", response_model=ClientList, summary="Список клиентов с поиском и пагинацией")
async def list_clients(
    q: str | None = Query(default=None, description="Строка поиска по ФИО, телефону, e-mail, имуществу"),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    manager: Manager = Depends(current_manager),
    session: AsyncSession = Depends(get_session),
):
    conditions = _search_conditions(q)
    total = await session.scalar(select(func.count(Client.id)).where(*conditions)) or 0
    stmt = (
        select(Client)
        .where(*conditions)
        .options(joinedload(Client.created_by))
        .order_by(Client.last_name, Client.first_name, Client.id)
        .limit(limit)
        .offset(offset)
    )
    clients = list((await session.scalars(stmt)).unique())
    counts = await _comment_counts(session, clients)
    return ClientList(
        items=[_to_out(client, counts.get(client.id, 0)) for client in clients],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED, summary="Завести клиента")
async def create_client(
    payload: ClientCreate,
    manager: Manager = Depends(current_manager),
    session: AsyncSession = Depends(get_session),
):
    client = Client(**payload.model_dump(), created_by_id=manager.id)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return _to_out(client, 0)


@router.get("/{client_id}", response_model=ClientDetail, summary="Карточка клиента вместе с историей")
async def get_client(
    client_id: int,
    manager: Manager = Depends(current_manager),
    session: AsyncSession = Depends(get_session),
):
    client = await _get_client(session, client_id, with_comments=True)
    counts = await _comment_counts(session, [client])
    detail = ClientDetail.model_validate(
        _to_out(client, counts.get(client.id, 0)).model_dump()
        | {"comments": [CommentOut.model_validate(c) for c in client.comments]}
    )
    return detail


@router.put("/{client_id}", response_model=ClientOut, summary="Редактировать карточку клиента")
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    manager: Manager = Depends(current_manager),
    session: AsyncSession = Depends(get_session),
):
    client = await _get_client(session, client_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не передано ни одного поля для изменения",
        )
    for field, value in changes.items():
        setattr(client, field, value)
    await session.commit()
    await session.refresh(client)
    counts = await _comment_counts(session, [client])
    return _to_out(client, counts.get(client.id, 0))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить клиента")
async def delete_client(
    client_id: int,
    manager: Manager = Depends(current_manager),
    session: AsyncSession = Depends(get_session),
):
    client = await _get_client(session, client_id)
    await session.delete(client)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/comments", response_model=list[CommentOut], summary="История дополнений")
async def list_comments(
    client_id: int,
    manager: Manager = Depends(current_manager),
    session: AsyncSession = Depends(get_session),
):
    await _get_client(session, client_id)
    rows = await session.scalars(
        select(ClientComment)
        .where(ClientComment.client_id == client_id)
        .order_by(ClientComment.created_at, ClientComment.id)
    )
    return list(rows)


@router.post(
    "/{client_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Дополнить карточку комментарием",
)
async def add_comment(
    client_id: int,
    payload: CommentCreate,
    manager: Manager = Depends(current_manager),
    session: AsyncSession = Depends(get_session),
):
    await _get_client(session, client_id)
    comment = ClientComment(
        client_id=client_id, author_id=manager.id, author_name=manager.full_name, text=payload.text
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment
