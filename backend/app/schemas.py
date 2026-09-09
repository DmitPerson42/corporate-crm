"""Pydantic-схемы: контракты запросов и ответов REST API."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[\d][\d\s()\-]{4,19}$")


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=64, examples=["manager"])
    password: str = Field(min_length=1, max_length=128, examples=["manager123"])


class ManagerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    full_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Срок жизни токена в секундах")
    manager: ManagerOut


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000, description="Текст дополнения к карточке")

    @field_validator("text")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Текст комментария не может быть пустым")
        return cleaned


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    author_name: str
    created_at: datetime


class ClientBase(BaseModel):
    """Поля карточки клиента. Обязательны фамилия и имя — остальное менеджер
    заполняет по мере поступления сведений."""

    last_name: str = Field(min_length=2, max_length=120, examples=["Петров"])
    first_name: str = Field(min_length=2, max_length=120, examples=["Сергей"])
    middle_name: str | None = Field(default=None, max_length=120, examples=["Алексеевич"])
    phone: str | None = Field(default=None, max_length=64, examples=["+7 (912) 345-67-89"])
    email: str | None = Field(default=None, max_length=255, examples=["petrov@example.ru"])
    property_info: str | None = Field(
        default=None, max_length=8000, examples=["Квартира 68 м², земельный участок 12 соток"]
    )
    comment: str | None = Field(default=None, max_length=8000, examples=["Ключевой клиент"])

    @field_validator("last_name", "first_name", "middle_name", "phone", "email", "property_info", "comment")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        if value and not PHONE_RE.match(value):
            raise ValueError("Телефон должен содержать только цифры, +, скобки, дефис или пробел")
        return value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        if value and not EMAIL_RE.match(value):
            raise ValueError("Некорректный адрес электронной почты")
        return value.lower() if value else value


class ClientCreate(ClientBase):
    """Первичная комментарий можно передать сразу — она попадёт в поле `comment` карточки,
    а история дополнений будет в отдельной таблице."""


class ClientUpdate(BaseModel):
    """Частичное обновление: приходит только то поле, которое менеджер изменил."""

    last_name: str | None = Field(default=None, min_length=2, max_length=120)
    first_name: str | None = Field(default=None, min_length=2, max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    property_info: str | None = Field(default=None, max_length=8000)
    comment: str | None = Field(default=None, max_length=8000)

    @field_validator("last_name", "first_name", "middle_name", "phone", "email", "property_info", "comment")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value: str | None) -> str | None:
        if value and not PHONE_RE.match(value):
            raise ValueError("Телефон должен содержать только цифры, +, скобки, дефис или пробел")
        return value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        if value and not EMAIL_RE.match(value):
            raise ValueError("Некорректный адрес электронной почты")
        return value.lower() if value else value

    @field_validator("last_name", "first_name")
    @classmethod
    def _require_non_blank(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 2:
            raise ValueError("Минимальная длина — 2 символа")
        return value


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str = Field(description="ФИО одной строкой")
    comments_count: int = 0
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ClientDetail(ClientOut):
    comments: list[CommentOut] = Field(default_factory=list)


class ClientList(BaseModel):
    items: list[ClientOut]
    total: int
    limit: int
    offset: int


class ErrorOut(BaseModel):
    detail: str


class HealthOut(BaseModel):
    status: str
    database: str
