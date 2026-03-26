from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConversationNotFoundError
from app.graph.graph import get_compiled_graph
from app.graph.nodes import generate_node_streaming
from app.graph.state import ChatMessage, ConversationState
from app.models.conversation import Conversation
from app.models.message import Message, RoleEnum
from app.services.rag_service import retrieve_global_for_owner

logger = logging.getLogger(__name__)


async def create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str | None = None,
) -> Conversation:
    session_id = str(uuid.uuid4())
    conversation = Conversation(
        user_id=user_id,
        title=title,
        session_id=session_id,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    logger.info(f"Created conversation {conversation.id} for user {user_id}")
    return conversation


async def list_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .options(selectinload(Conversation.messages))
    )
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise ConversationNotFoundError()
    return conversation


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[Message]:
    await get_conversation(db, conversation_id, user_id)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID) -> list[ChatMessage]:
    """Load existing messages for a conversation as ChatMessage dicts."""
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    messages: list[ChatMessage] = []
    for msg in result.scalars().all():
        messages.append({"role": msg.role.value, "content": msg.content})
    return messages


def _graph_config(session_id: str) -> dict:
    """Build the LangGraph config that keys checkpointer state by session_id."""
    return {"configurable": {"thread_id": session_id}}


async def stream_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    query: str,
) -> AsyncGenerator[str, None]:
    """Stream an SSE response for a chat query.

    Uses the compiled LangGraph to run retrieve + summarize nodes.
    The checkpointer (keyed by session_id) automatically restores prior
    conversation state (messages, summary, chunks) across turns.

    Yields SSE-formatted strings:
      data: {"type": "token", "content": "..."}\n\n
      data: {"type": "sources", "sources": [...]}\n\n
      data: {"type": "done"}\n\n
    """
    conversation = await get_conversation(db, conversation_id, user_id)

    user_message = Message(
        conversation_id=conversation.id,
        role=RoleEnum.user,
        content=query,
    )
    db.add(user_message)
    await db.commit()

    if conversation.title is None:
        conversation.title = query[:100]
        await db.commit()

    graph = get_compiled_graph()
    config = _graph_config(conversation.session_id)

    # Try to restore state from the checkpointer (previous turns).
    # If no checkpoint exists (first turn), seed from the DB.
    checkpoint_state = await graph.aget_state(config)
    if checkpoint_state.values and checkpoint_state.values.get("messages"):
        prior_messages: list[ChatMessage] = checkpoint_state.values["messages"]
        prior_messages.append({"role": "user", "content": query})
        input_state: ConversationState = {
            "messages": prior_messages,
            "query": query,
            "session_id": conversation.session_id,
            "user_id": str(user_id),
            "summary": checkpoint_state.values.get("summary", ""),
        }
    else:
        history = await _load_history(db, conversation.id)
        input_state = {
            "messages": history,
            "query": query,
            "session_id": conversation.session_id,
            "user_id": str(user_id),
            "summary": conversation.summary or "",
        }

    # Run the graph: retrieve -> summarize_check -> (summarize | end).
    # The checkpointer saves the resulting state for the next turn.
    graph_result = await graph.ainvoke(input_state, config)

    # Build the state for generation from the graph's output
    gen_state: ConversationState = {
        "messages": graph_result.get("messages", input_state.get("messages", [])),
        "retrieved_chunks": graph_result.get("retrieved_chunks", []),
        "summary": graph_result.get("summary", input_state.get("summary", "")),
        "query": query,
        "sources": graph_result.get("sources", []),
    }

    # Stream tokens from OpenAI
    full_response_tokens: list[str] = []
    try:
        async for token in generate_node_streaming(gen_state):
            full_response_tokens.append(token)
            event = json.dumps({"type": "token", "content": token})
            yield f"data: {event}\n\n"
    except Exception as exc:
        logger.error(f"Generation error: {exc}")
        error_event = json.dumps({"type": "error", "content": str(exc)})
        yield f"data: {error_event}\n\n"
        return

    sources = gen_state.get("sources", [])
    if sources:
        sources_event = json.dumps({"type": "sources", "sources": sources})
        yield f"data: {sources_event}\n\n"

    done_event = json.dumps({"type": "done"})
    yield f"data: {done_event}\n\n"

    # Persist the assistant message to PostgreSQL
    full_response = "".join(full_response_tokens)
    assistant_message = Message(
        conversation_id=conversation.id,
        role=RoleEnum.assistant,
        content=full_response,
        sources=sources if sources else None,
    )
    db.add(assistant_message)
    await db.commit()

    # Update the checkpoint with the assistant's response so the next turn
    # picks up the full conversation including this answer.
    updated_messages = list(gen_state.get("messages", []))
    updated_messages.append({"role": "assistant", "content": full_response})
    await graph.aupdate_state(
        config,
        {"messages": updated_messages, "generated_response": full_response},
    )

    # Persist summary to the DB if the graph produced one (summarize node ran)
    new_summary = graph_result.get("summary", "")
    if new_summary and new_summary != (conversation.summary or ""):
        conversation.summary = new_summary
        await db.commit()
        logger.info(f"Summarization persisted for conversation {conversation.id}")

    logger.info(f"Completed stream for conversation {conversation.id}")


async def stream_shared_response(
    db: AsyncSession,
    owner_id: uuid.UUID,
    conversation_id: uuid.UUID,
    link_token: str,
    query: str,
) -> AsyncGenerator[str, None]:
    """Stream an SSE response for a share-link guest chat session.

    RAG retrieval is scoped exclusively to the owner's global (published) documents.
    The conversation must belong to the provided link_token to prevent cross-link access.

    Yields SSE-formatted strings identical to stream_response.
    """
    from app.services.share_service import get_shared_conversation

    conversation = await get_shared_conversation(db, conversation_id, link_token)

    user_message = Message(
        conversation_id=conversation.id,
        role=RoleEnum.user,
        content=query,
    )
    db.add(user_message)
    await db.commit()

    # Retrieve only the owner's globally-published chunks — no private docs, no other users' docs.
    logger.info(f"stream_shared_response: owner_id raw={owner_id!r} str={str(owner_id)!r}")
    chunks = retrieve_global_for_owner(query=query, owner_id=str(owner_id), top_k=5)
    logger.info(f"stream_shared_response: retrieved {len(chunks)} chunks for owner {str(owner_id)!r}")
    sources = [{"doc_id": c.doc_id, "filename": c.filename, "page": c.page_number} for c in chunks]

    history = await _load_history(db, conversation.id)
    gen_state: ConversationState = {
        "messages": history,
        "retrieved_chunks": chunks,
        "query": query,
        "session_id": conversation.session_id,
        "user_id": str(owner_id),
        "summary": conversation.summary or "",
        "sources": sources,
    }

    full_response_tokens: list[str] = []
    try:
        async for token in generate_node_streaming(gen_state):
            full_response_tokens.append(token)
            event = json.dumps({"type": "token", "content": token})
            yield f"data: {event}\n\n"
    except Exception as exc:
        logger.error(f"Shared generation error: {exc}")
        error_event = json.dumps({"type": "error", "content": str(exc)})
        yield f"data: {error_event}\n\n"
        return

    if sources:
        sources_event = json.dumps({"type": "sources", "sources": sources})
        yield f"data: {sources_event}\n\n"

    done_event = json.dumps({"type": "done"})
    yield f"data: {done_event}\n\n"

    full_response = "".join(full_response_tokens)
    assistant_message = Message(
        conversation_id=conversation.id,
        role=RoleEnum.assistant,
        content=full_response,
        sources=sources if sources else None,
    )
    db.add(assistant_message)
    await db.commit()

    logger.info(f"Completed shared stream for conversation {conversation.id}")
