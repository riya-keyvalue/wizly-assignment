from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VisibilityEnum(enum.StrEnum):
    global_ = "global"
    private = "private"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    visibility: Mapped[VisibilityEnum] = mapped_column(
        Enum(VisibilityEnum, values_callable=lambda e: [m.value for m in e]),
        default=VisibilityEnum.global_,
        nullable=False,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="documents")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (Index("ix_documents_user_id", "user_id"),)
