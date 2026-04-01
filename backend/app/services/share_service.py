from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ShareLinkForbiddenError, ShareLinkNotFoundError
from app.models.conversation import Conversation
from app.models.message import Message, RoleEnum
from app.models.shareable_link import ShareableLink
from app.models.user import User
from app.schemas.share import ShareableLinkCreate, ShareableLinkUpdate

logger = logging.getLogger(__name__)


async def create_link(
    db: AsyncSession,
    owner_id: uuid.UUID,
    data: ShareableLinkCreate,
) -> ShareableLink:
    token = secrets.token_urlsafe(32)
    link = ShareableLink(
        owner_id=owner_id,
        token=token,
        label=data.label,
        expires_at=data.expires_at,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    logger.info(f"Created share link {token} for owner {owner_id}")
    return link


async def list_links(
    db: AsyncSession,
    owner_id: uuid.UUID,
) -> list[ShareableLink]:
    result = await db.execute(
        select(ShareableLink)
        .where(ShareableLink.owner_id == owner_id)
        .order_by(ShareableLink.created_at.desc())
    )
    return list(result.scalars().all())


async def update_link(
    db: AsyncSession,
    owner_id: uuid.UUID,
    token: str,
    data: ShareableLinkUpdate,
) -> ShareableLink:
    result = await db.execute(
        select(ShareableLink).where(ShareableLink.token == token)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise ShareLinkNotFoundError()
    if link.owner_id != owner_id:
        raise ShareLinkForbiddenError()

    if data.label is not None:
        link.label = data.label
    if data.is_active is not None:
        link.is_active = data.is_active

    await db.commit()
    await db.refresh(link)
    logger.info(f"Updated share link {token} (owner={owner_id})")
    return link


async def delete_link(
    db: AsyncSession,
    owner_id: uuid.UUID,
    token: str,
) -> None:
    result = await db.execute(
        select(ShareableLink).where(ShareableLink.token == token)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise ShareLinkNotFoundError()
    if link.owner_id != owner_id:
        raise ShareLinkForbiddenError()

    await db.delete(link)
    await db.commit()
    logger.info(f"Deleted share link {token} (owner={owner_id})")


async def get_active_link(db: AsyncSession, token: str) -> ShareableLink:
    """Validate a share token and return the link if active and not expired.

    Always raises HTTP 404 on failure to avoid leaking information about
    whether a token exists.
    """
    result = await db.execute(
        select(ShareableLink)
        .where(ShareableLink.token == token)
        .options(selectinload(ShareableLink.owner))
    )
    link = result.scalar_one_or_none()

    if link is None or not link.is_active:
        raise ShareLinkNotFoundError()

    if link.expires_at is not None and link.expires_at < datetime.now(UTC):
        raise ShareLinkNotFoundError()

    return link


async def create_shared_conversation(
    db: AsyncSession,
    link: ShareableLink,
) -> Conversation:
    """Create an anonymous conversation scoped to the link owner."""
    session_id = str(uuid.uuid4())
    conversation = Conversation(
        user_id=None,
        link_token=link.token,
        owner_id=link.owner_id,
        session_id=session_id,
        title=f"Shared chat via {link.label or link.token[:8]}",
        chat_mode="ai_twin",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    logger.info(
        f"Created shared conversation {conversation.id} for link {link.token}"
    )
    return conversation


async def get_shared_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    link_token: str,
) -> Conversation:
    """Load a shared conversation and verify it belongs to the given link token."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.link_token == link_token,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        from app.core.exceptions import ConversationNotFoundError
        raise ConversationNotFoundError()
    return conversation


async def get_shared_conversation_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    link_token: str,
) -> list[Message]:
    await get_shared_conversation(db, conversation_id, link_token)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())
