from __future__ import annotations

from typing import TypedDict

from app.schemas.chat import RetrievedChunk


class ChatMessage(TypedDict):
    role: str  # "user" | "assistant" | "system"
    content: str


class ConversationState(TypedDict, total=False):
    messages: list[ChatMessage]
    retrieved_chunks: list[RetrievedChunk]
    session_id: str
    user_id: str
    summary: str
    query: str
    generated_response: str
    sources: list[dict]
    should_summarize: bool
