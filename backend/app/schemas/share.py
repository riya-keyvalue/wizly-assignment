from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShareableLinkCreate(BaseModel):
    label: str | None = None
    expires_at: datetime | None = None


class ShareableLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token: str
    label: str | None
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ShareableLinkUpdate(BaseModel):
    label: str | None = None
    is_active: bool | None = None


class ShareTokenInfo(BaseModel):
    """Returned to the guest when they validate a share link token."""

    owner_email: str
    label: str | None


class SharedConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: str
    created_at: datetime
