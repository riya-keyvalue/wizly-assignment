from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.graph.state import ChatMessage, ConversationState
from app.schemas.chat import RetrievedChunk
from app.services.rag_service import retrieve_for_user

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI Twin — a knowledgeable assistant that answers questions "
    "based on uploaded documents. Ground your answers in the provided context. "
    "If the context does not contain enough information, say so clearly. "
    "Cite specific document sources when possible."
)

SUMMARIZE_PROMPT = (
    "Summarize the following conversation concisely, preserving all key facts, "
    "decisions, and context that would be needed to continue the conversation. "
    "Retain any document references or source citations."
)

MESSAGE_COUNT_THRESHOLD = 15
TOKEN_ESTIMATE_THRESHOLD = 3000


def _estimate_tokens(messages: list[ChatMessage]) -> int:
    """Rough token estimate: ~4 chars per token."""
    return sum(len(m["content"]) for m in messages) // 4


def _build_context_block(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant document context found."
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[Source {i}: {c.filename}, page {c.page_number}]\n{c.text}")
    return "\n\n".join(parts)


def retrieve_node(state: ConversationState) -> dict[str, Any]:
    """Retrieve relevant chunks for the user's query.

    Queries both the global collection (visible to all users) and the requesting
    user's private collection, merges the results by relevance score, and returns
    the top-k combined chunks. Private chunks from other users are never included.
    """
    query = state.get("query", "")
    if not query:
        return {"retrieved_chunks": [], "sources": []}

    user_id = state.get("user_id", "")
    if not user_id:
        logger.warning("retrieve_node: user_id missing in state — falling back to global only")
        chunks = retrieve_for_user(query=query, user_id="__no_user__", top_k=5)
    else:
        chunks = retrieve_for_user(query=query, user_id=user_id, top_k=5)

    sources = [{"doc_id": c.doc_id, "filename": c.filename, "page": c.page_number} for c in chunks]

    return {"retrieved_chunks": chunks, "sources": sources}


def _build_openai_messages(state: ConversationState) -> list[dict[str, str]]:
    """Build the message list sent to OpenAI, including system prompt, summary, context, and history."""
    openai_messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    summary = state.get("summary", "")
    if summary:
        openai_messages.append(
            {
                "role": "system",
                "content": f"Conversation summary so far:\n{summary}",
            }
        )

    chunks = state.get("retrieved_chunks", [])
    context_block = _build_context_block(chunks)
    openai_messages.append(
        {
            "role": "system",
            "content": f"Relevant document context:\n\n{context_block}",
        }
    )

    for msg in state.get("messages", []):
        if msg["role"] in ("user", "assistant"):
            openai_messages.append({"role": msg["role"], "content": msg["content"]})

    return openai_messages


async def generate_node_streaming(state: ConversationState) -> AsyncIterator[str]:
    """Stream tokens from GPT-4o-mini. Yields individual token strings."""
    openai_messages = _build_openai_messages(state)

    client = AsyncOpenAI(api_key=settings.LITELLM_API_KEY, base_url=settings.LITELLM_BASE_URL)

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=openai_messages,  # type: ignore[arg-type]
        stream=True,
        temperature=0.7,
        max_tokens=2048,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content


def check_summarize(state: ConversationState) -> bool:
    """Return True if the conversation needs summarization."""
    messages = state.get("messages", [])
    if len(messages) > MESSAGE_COUNT_THRESHOLD:
        return True
    if _estimate_tokens(messages) > TOKEN_ESTIMATE_THRESHOLD:
        return True
    return False


async def summarize_node(state: ConversationState) -> dict[str, Any]:
    """Summarize the conversation history, keeping only the last 3 messages."""
    messages = state.get("messages", [])
    if len(messages) <= 3:
        return {"summary": state.get("summary", ""), "should_summarize": False}

    conversation_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)

    client = AsyncOpenAI(api_key=settings.LITELLM_API_KEY, base_url=settings.LITELLM_BASE_URL)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": conversation_text},
        ],
        temperature=0.3,
        max_tokens=512,
    )

    summary_text = response.choices[0].message.content or ""

    last_messages = messages[-3:]

    return {
        "summary": summary_text,
        "messages": last_messages,
        "should_summarize": False,
    }
