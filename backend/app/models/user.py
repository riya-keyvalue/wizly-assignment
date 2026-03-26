from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents: Mapped[list[Document]] = relationship(back_populates="user", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    conversations: Mapped[list[Conversation]] = relationship(back_populates="user", foreign_keys="[Conversation.user_id]", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821
    shareable_links: Mapped[list[ShareableLink]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (Index("ix_users_email", "email"),)
