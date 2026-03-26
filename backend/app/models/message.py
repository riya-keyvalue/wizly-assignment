from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RoleEnum(enum.StrEnum):
    user = "user"
    assistant = "assistant"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (Index("ix_messages_conversation_id", "conversation_id"),)
