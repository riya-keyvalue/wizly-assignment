from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import VisibilityEnum


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    visibility: VisibilityEnum
    chunk_count: int
    created_at: datetime


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    visibility: VisibilityEnum
    chunk_count: int
    created_at: datetime
