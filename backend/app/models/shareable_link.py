from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ShareableLink(Base, TimestampMixin):
    __tablename__ = "shareable_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[User] = relationship(back_populates="shareable_links")  # type: ignore[name-defined]  # noqa: F821
    conversations: Mapped[list[Conversation]] = relationship(back_populates="share_link", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_shareable_links_owner_id", "owner_id"),
        Index("ix_shareable_links_token", "token"),
    )
