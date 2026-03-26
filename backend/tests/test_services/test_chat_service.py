from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message, RoleEnum
from app.services.chat_service import (
    create_conversation,
    get_conversation,
    get_conversation_messages,
    list_conversations,
    stream_response,
)
from tests.factories import UserFactory


@pytest.fixture
async def user(db: AsyncSession) -> object:
    user = UserFactory()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def conversation(db: AsyncSession, user: object) -> Conversation:
    conv = await create_conversation(db=db, user_id=user.id, title="Test Chat")
    return conv


def _mock_graph() -> MagicMock:
    """Build a mock compiled graph with ainvoke / aget_state / aupdate_state."""
    mock = MagicMock()

    empty_checkpoint = MagicMock()
    empty_checkpoint.values = {}
    mock.aget_state = AsyncMock(return_value=empty_checkpoint)

    mock.ainvoke = AsyncMock(
        return_value={
            "messages": [{"role": "user", "content": "test"}],
            "retrieved_chunks": [],
            "sources": [],
            "summary": "",
        }
    )

    mock.aupdate_state = AsyncMock(return_value=None)
    return mock


class TestCreateConversation:
    async def test_creates_conversation(self, db: AsyncSession, user: object) -> None:
        conv = await create_conversation(db=db, user_id=user.id, title="Hello")
        assert conv.id is not None
        assert conv.user_id == user.id
        assert conv.title == "Hello"
        assert conv.session_id is not None

    async def test_creates_conversation_without_title(self, db: AsyncSession, user: object) -> None:
        conv = await create_conversation(db=db, user_id=user.id)
        assert conv.title is None


class TestListConversations:
    async def test_lists_user_conversations(self, db: AsyncSession, user: object) -> None:
        await create_conversation(db=db, user_id=user.id, title="First")
        await create_conversation(db=db, user_id=user.id, title="Second")

        convs = await list_conversations(db=db, user_id=user.id)
        assert len(convs) == 2

    async def test_empty_list(self, db: AsyncSession, user: object) -> None:
        convs = await list_conversations(db=db, user_id=user.id)
        assert convs == []


class TestGetConversation:
    async def test_get_existing(self, db: AsyncSession, user: object, conversation: Conversation) -> None:
        result = await get_conversation(db=db, conversation_id=conversation.id, user_id=user.id)
        assert result.id == conversation.id

    async def test_get_nonexistent(self, db: AsyncSession, user: object) -> None:
        from app.core.exceptions import ConversationNotFoundError

        with pytest.raises(ConversationNotFoundError):
            await get_conversation(db=db, conversation_id=uuid.uuid4(), user_id=user.id)


class TestGetConversationMessages:
    async def test_returns_messages_in_order(self, db: AsyncSession, user: object, conversation: Conversation) -> None:
        msg1 = Message(conversation_id=conversation.id, role=RoleEnum.user, content="Hello")
        msg2 = Message(conversation_id=conversation.id, role=RoleEnum.assistant, content="Hi there")
        db.add(msg1)
        db.add(msg2)
        await db.commit()

        messages = await get_conversation_messages(db=db, conversation_id=conversation.id, user_id=user.id)
        assert len(messages) == 2
        assert messages[0].role == RoleEnum.user
        assert messages[1].role == RoleEnum.assistant


class TestStreamResponse:
    async def test_stream_chat_success(self, db: AsyncSession, user: object, conversation: Conversation) -> None:
        """Mock graph + OpenAI stream; assert SSE events received in correct order."""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_graph = _mock_graph()

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_graph),
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client = AsyncMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

            events: list[str] = []
            async for event in stream_response(
                db=db,
                user_id=user.id,
                conversation_id=conversation.id,
                query="test question",
            ):
                events.append(event)

        assert len(events) >= 3

        token_events = [e for e in events if '"type": "token"' in e]
        assert len(token_events) == 2

        done_events = [e for e in events if '"type": "done"' in e]
        assert len(done_events) == 1

        assert events[-1] == done_events[0]

        mock_graph.ainvoke.assert_awaited_once()
        mock_graph.aupdate_state.assert_awaited_once()

    async def test_conversation_persisted(self, db: AsyncSession, user: object, conversation: Conversation) -> None:
        """After stream, messages should be in DB."""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Response"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_graph = _mock_graph()

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_graph),
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client = AsyncMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

            async for _ in stream_response(
                db=db,
                user_id=user.id,
                conversation_id=conversation.id,
                query="test question",
            ):
                pass

        result = await db.execute(select(Message).where(Message.conversation_id == conversation.id))
        messages = list(result.scalars().all())
        assert len(messages) == 2
        assert messages[0].role == RoleEnum.user
        assert messages[0].content == "test question"
        assert messages[1].role == RoleEnum.assistant
        assert messages[1].content == "Response"

    async def test_title_set_from_first_query(self, db: AsyncSession, user: object) -> None:
        """Conversation title should be set from the first user query if None."""
        conv = await create_conversation(db=db, user_id=user.id, title=None)

        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="OK"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_graph = _mock_graph()

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_graph),
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client = AsyncMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

            async for _ in stream_response(
                db=db,
                user_id=user.id,
                conversation_id=conv.id,
                query="What is machine learning?",
            ):
                pass

        await db.refresh(conv)
        assert conv.title == "What is machine learning?"

    async def test_checkpoint_restored_on_second_turn(
        self, db: AsyncSession, user: object, conversation: Conversation
    ) -> None:
        """On the second turn, aget_state should return prior messages from checkpointer."""
        prior_messages = [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ]

        checkpoint_with_history = MagicMock()
        checkpoint_with_history.values = {
            "messages": prior_messages,
            "summary": "A summary of turn 1",
        }

        mock_graph = _mock_graph()
        mock_graph.aget_state = AsyncMock(return_value=checkpoint_with_history)

        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="second answer"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_graph),
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client = AsyncMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

            async for _ in stream_response(
                db=db,
                user_id=user.id,
                conversation_id=conversation.id,
                query="second question",
            ):
                pass

        # Verify the graph was invoked with messages from checkpoint + new query
        call_args = mock_graph.ainvoke.call_args
        input_state = call_args[0][0]
        assert len(input_state["messages"]) == 3  # 2 prior + 1 new user msg
        assert input_state["messages"][-1] == {"role": "user", "content": "second question"}
        assert input_state["summary"] == "A summary of turn 1"
