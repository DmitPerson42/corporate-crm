"""ORM-модели предметной области: менеджер, клиент, комментарии к карточке клиента."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Manager(Base, TimestampMixin):
    """Единственная роль в системе — менеджер. Отдельной таблицы ролей не заводим:
    доступ к приложению имеют только менеджеры, их перечень ведёт администратор через seed."""

    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clients: Mapped[list[Client]] = relationship(back_populates="created_by")
    comments: Mapped[list[ClientComment]] = relationship(back_populates="author")

    def __repr__(self) -> str:  # pragma: no cover - служебное представление
        return f"<Manager id={self.id} login={self.login!r}>"


class Client(Base, TimestampMixin):
    """Карточка клиента компании."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(255))
    property_info: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("managers.id", ondelete="SET NULL")
    )

    created_by: Mapped[Manager | None] = relationship(back_populates="clients")
    comments: Mapped[list[ClientComment]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ClientComment.created_at",
    )

    __table_args__ = (
        Index("ix_clients_fio", "last_name", "first_name", "middle_name"),
        Index("ix_clients_email", "email"),
    )

    @property
    def full_name(self) -> str:
        parts = (self.last_name, self.first_name, self.middle_name)
        return " ".join(part for part in parts if part)

    def __repr__(self) -> str:  # pragma: no cover - служебное представление
        return f"<Client id={self.id} {self.full_name!r}>"


class ClientComment(Base):
    """Запись журнала: чем менеджер дополняет карточку клиента со временем."""

    __tablename__ = "client_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("managers.id", ondelete="SET NULL"), index=True
    )
    author_name: Mapped[str] = mapped_column(String(160), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    client: Mapped[Client] = relationship(back_populates="comments")
    author: Mapped[Manager | None] = relationship(back_populates="comments")

    def __repr__(self) -> str:  # pragma: no cover - служебное представление
        return f"<ClientComment id={self.id} client_id={self.client_id}>"
