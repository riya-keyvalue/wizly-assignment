from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import rate_limit
from app.core.permissions import get_current_active_user
from app.models.user import User
from app.schemas.chat import MessageRead
from app.schemas.share import (
    ShareableLinkCreate,
    ShareableLinkRead,
    ShareableLinkUpdate,
    ShareTokenInfo,
    SharedConversationRead,
)
from app.services.share_service import (
    create_link,
    create_shared_conversation,
    delete_link,
    get_active_link,
    get_shared_conversation_messages,
    list_links,
    update_link,
)
from app.services.chat_service import stream_shared_response

router = APIRouter(prefix="/share", tags=["share"])

_public_rl = Depends(rate_limit(max_requests=30, window_seconds=60))


# ---------------------------------------------------------------------------
# Authenticated owner endpoints
# ---------------------------------------------------------------------------


@router.post("/links", status_code=status.HTTP_201_CREATED)
async def create_share_link(
    data: ShareableLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, ShareableLinkRead]:
    link = await create_link(db=db, owner_id=current_user.id, data=data)
    return {"data": ShareableLinkRead.model_validate(link)}


@router.get("/links", status_code=status.HTTP_200_OK)
async def list_share_links(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, list[ShareableLinkRead]]:
    links = await list_links(db=db, owner_id=current_user.id)
    return {"data": [ShareableLinkRead.model_validate(lnk) for lnk in links]}


@router.patch("/links/{token}", status_code=status.HTTP_200_OK)
async def update_share_link(
    token: str,
    data: ShareableLinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, ShareableLinkRead]:
    link = await update_link(db=db, owner_id=current_user.id, token=token, data=data)
    return {"data": ShareableLinkRead.model_validate(link)}


@router.delete("/links/{token}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_share_link(
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    await delete_link(db=db, owner_id=current_user.id, token=token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Public guest endpoints (no authentication required)
# ---------------------------------------------------------------------------


@router.get("/{token}", status_code=status.HTTP_200_OK)
async def get_share_token_info(
    token: str,
    db: AsyncSession = Depends(get_db),
    _rl: None = _public_rl,
) -> dict[str, ShareTokenInfo]:
    link = await get_active_link(db=db, token=token)
    return {
        "data": ShareTokenInfo(
            owner_email=link.owner.email,
            label=link.label,
        )
    }


@router.post("/{token}/conversations", status_code=status.HTTP_201_CREATED)
async def create_guest_conversation(
    token: str,
    db: AsyncSession = Depends(get_db),
    _rl: None = _public_rl,
) -> dict[str, SharedConversationRead]:
    link = await get_active_link(db=db, token=token)
    conversation = await create_shared_conversation(db=db, link=link)
    return {"data": SharedConversationRead.model_validate(conversation)}


@router.get("/{token}/conversations/{conversation_id}/messages", status_code=status.HTTP_200_OK)
async def get_guest_messages(
    token: str,
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _rl: None = _public_rl,
) -> dict[str, list[MessageRead]]:
    await get_active_link(db=db, token=token)
    messages = await get_shared_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        link_token=token,
    )
    return {"data": [MessageRead.model_validate(m) for m in messages]}


@router.get("/{token}/conversations/{conversation_id}/stream")
async def stream_guest_chat(
    token: str,
    conversation_id: uuid.UUID,
    query: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    _rl: None = _public_rl,
) -> StreamingResponse:
    link = await get_active_link(db=db, token=token)

    return StreamingResponse(
        stream_shared_response(
            db=db,
            owner_id=link.owner_id,
            conversation_id=conversation_id,
            link_token=token,
            query=query,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
