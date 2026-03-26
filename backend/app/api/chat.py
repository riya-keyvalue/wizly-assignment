from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_active_user
from app.models.user import User
from app.schemas.chat import ConversationCreate, ConversationRead, MessageRead
from app.services.chat_service import (
    create_conversation,
    get_conversation,
    get_conversation_messages,
    list_conversations,
    stream_response,
)

router = APIRouter(prefix="/conversations", tags=["chat"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, ConversationRead]:
    conversation = await create_conversation(
        db=db,
        user_id=current_user.id,
        title=data.title,
    )
    return {"data": ConversationRead.model_validate(conversation)}


@router.get("/", status_code=status.HTTP_200_OK)
async def list_user_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, list[ConversationRead]]:
    conversations = await list_conversations(db=db, user_id=current_user.id)
    return {"data": [ConversationRead.model_validate(c) for c in conversations]}


@router.get("/{conversation_id}/messages", status_code=status.HTTP_200_OK)
async def get_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, list[MessageRead]]:
    messages = await get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    return {"data": [MessageRead.model_validate(m) for m in messages]}


@router.get("/{conversation_id}/stream")
async def stream_chat(
    conversation_id: uuid.UUID,
    query: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    await get_conversation(db=db, conversation_id=conversation_id, user_id=current_user.id)

    return StreamingResponse(
        stream_response(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation_id,
            query=query,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
