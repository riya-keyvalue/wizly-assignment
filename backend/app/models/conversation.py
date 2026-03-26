from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Nullable to support anonymous shared conversations (no logged-in user)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set only for shared (anonymous) conversations
    link_token: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("shareable_links.token", ondelete="CASCADE"), nullable=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped[User | None] = relationship(back_populates="conversations", foreign_keys="[Conversation.user_id]")  # type: ignore[name-defined]  # noqa: F821
    share_link: Mapped[ShareableLink | None] = relationship(back_populates="conversations", foreign_keys="[Conversation.link_token]")  # type: ignore[name-defined]  # noqa: F821
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_session_id", "session_id"),
        Index("ix_conversations_link_token", "link_token"),
    )
