from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RetrievedChunk(BaseModel):
    text: str
    doc_id: str
    filename: str
    page_number: int
    score: float


class SourceReference(BaseModel):
    doc_id: str
    filename: str
    page: int


class ChatRequest(BaseModel):
    query: str


class ChatStreamEvent(BaseModel):
    type: str  # "token" | "sources" | "done" | "error"
    content: str | None = None
    sources: list[SourceReference] | None = None


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    session_id: str
    summary: str | None = None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    sources: list[dict] | None = None
    created_at: datetime
