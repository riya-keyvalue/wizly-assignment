from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.conversation import Conversation
from app.models.message import Message, RoleEnum
from app.services.chat_service import create_conversation
from tests.factories import UserFactory


@pytest.fixture
async def user(db: AsyncSession) -> object:
    user = UserFactory()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def auth_headers(user: object) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def conversation(db: AsyncSession, user: object) -> Conversation:
    conv = await create_conversation(db=db, user_id=user.id, title="Test")
    return conv


@pytest.fixture
async def conversation_ai_twin(db: AsyncSession, user: object) -> Conversation:
    conv = await create_conversation(
        db=db, user_id=user.id, title="Twin", chat_mode="ai_twin"
    )
    return conv


class TestCreateConversation:
    async def test_create_success(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.post(
            "/conversations/",
            json={"title": "New Chat"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "New Chat"
        assert data["chat_mode"] == "playground"
        assert "session_id" in data
        assert "id" in data

    async def test_create_with_ai_twin_mode(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.post(
            "/conversations/",
            json={"chat_mode": "ai_twin"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["data"]["chat_mode"] == "ai_twin"

    async def test_create_without_title(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.post(
            "/conversations/",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["data"]["title"] is None

    async def test_create_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.post("/conversations/", json={})
        assert response.status_code == 403


class TestListConversations:
    async def test_list_success(self, client: AsyncClient, auth_headers: dict, conversation: Conversation) -> None:
        response = await client.get("/conversations/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1
        assert data[0]["id"] == str(conversation.id)

    async def test_list_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.get("/conversations/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"] == []

    async def test_list_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/conversations/")
        assert response.status_code == 403


class TestGetConversationDetail:
    async def test_get_success(
        self, client: AsyncClient, auth_headers: dict, conversation: Conversation
    ) -> None:
        response = await client.get(
            f"/conversations/{conversation.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(conversation.id)
        assert data["chat_mode"] == "playground"

    async def test_get_ai_twin_mode(
        self, client: AsyncClient, auth_headers: dict, conversation_ai_twin: Conversation
    ) -> None:
        response = await client.get(
            f"/conversations/{conversation_ai_twin.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["chat_mode"] == "ai_twin"

    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.get(
            f"/conversations/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestGetMessages:
    async def test_get_messages_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession,
        conversation: Conversation,
    ) -> None:
        msg = Message(
            conversation_id=conversation.id,
            role=RoleEnum.user,
            content="Hello",
        )
        db.add(msg)
        await db.commit()

        response = await client.get(
            f"/conversations/{conversation.id}/messages",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["content"] == "Hello"
        assert data[0]["role"] == "user"

    async def test_get_messages_not_found(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.get(
            f"/conversations/{uuid.uuid4()}/messages",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_messages_unauthenticated(self, client: AsyncClient, conversation: Conversation) -> None:
        response = await client.get(f"/conversations/{conversation.id}/messages")
        assert response.status_code == 403


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


class TestStreamChat:
    async def test_stream_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        conversation: Conversation,
    ) -> None:
        """Mock graph + OpenAI stream; verify SSE events."""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=" there"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_g = _mock_graph()

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_g),
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client_inst = AsyncMock()
            mock_openai_cls.return_value = mock_client_inst
            mock_client_inst.chat.completions.create = AsyncMock(return_value=mock_stream())

            response = await client.get(
                f"/conversations/{conversation.id}/stream",
                params={"query": "What is AI?"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data: ")]
        assert len(data_lines) >= 3

        parsed = [json.loads(l.removeprefix("data: ")) for l in data_lines]

        token_events = [e for e in parsed if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "Hello"
        assert token_events[1]["content"] == " there"

        done_events = [e for e in parsed if e["type"] == "done"]
        assert len(done_events) == 1

    async def test_stream_global_docs_only_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        conversation_ai_twin: Conversation,
    ) -> None:
        """Global-docs-only path skips full graph retrieve; uses retrieve_global_for_owner + streaming."""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hi"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_g = _mock_graph()

        fake_chunk = MagicMock()
        fake_chunk.doc_id = "d1"
        fake_chunk.filename = "pub.pdf"
        fake_chunk.page_number = 1
        fake_chunk.text = "ctx"

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_g),
            patch(
                "app.services.chat_service.retrieve_global_for_owner",
                return_value=[fake_chunk],
            ),
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client_inst = AsyncMock()
            mock_openai_cls.return_value = mock_client_inst
            mock_client_inst.chat.completions.create = AsyncMock(return_value=mock_stream())

            response = await client.get(
                f"/conversations/{conversation_ai_twin.id}/stream",
                params={"query": "Hello", "global_docs_only": "true"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        mock_g.ainvoke.assert_not_called()
        mock_g.aupdate_state.assert_called_once()

    async def test_stream_playground_global_docs_only_narrows_retrieval(
        self,
        client: AsyncClient,
        auth_headers: dict,
        conversation: Conversation,
    ) -> None:
        """Playground + global_docs_only uses owner global scope (no private RAG)."""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Ok"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_g = _mock_graph()

        fake_chunk = MagicMock()
        fake_chunk.doc_id = "d1"
        fake_chunk.filename = "pub.pdf"
        fake_chunk.page_number = 1
        fake_chunk.text = "ctx"

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_g),
            patch(
                "app.services.chat_service.retrieve_global_for_owner",
                return_value=[fake_chunk],
            ) as mock_retrieve,
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client_inst = AsyncMock()
            mock_openai_cls.return_value = mock_client_inst
            mock_client_inst.chat.completions.create = AsyncMock(return_value=mock_stream())

            response = await client.get(
                f"/conversations/{conversation.id}/stream",
                params={"query": "Hi", "global_docs_only": "true"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        mock_retrieve.assert_called_once()
        mock_g.ainvoke.assert_not_called()
        mock_g.aupdate_state.assert_called_once()

    async def test_stream_ai_twin_without_global_docs_query_param(
        self,
        client: AsyncClient,
        auth_headers: dict,
        conversation_ai_twin: Conversation,
    ) -> None:
        """AI Twin scope comes from conversation.chat_mode, not the query string."""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hi"))]),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_g = _mock_graph()

        fake_chunk = MagicMock()
        fake_chunk.doc_id = "d1"
        fake_chunk.filename = "pub.pdf"
        fake_chunk.page_number = 1
        fake_chunk.text = "ctx"

        with (
            patch("app.services.chat_service.get_compiled_graph", return_value=mock_g),
            patch(
                "app.services.chat_service.retrieve_global_for_owner",
                return_value=[fake_chunk],
            ),
            patch("app.graph.nodes.AsyncOpenAI") as mock_openai_cls,
        ):
            mock_client_inst = AsyncMock()
            mock_openai_cls.return_value = mock_client_inst
            mock_client_inst.chat.completions.create = AsyncMock(return_value=mock_stream())

            response = await client.get(
                f"/conversations/{conversation_ai_twin.id}/stream",
                params={"query": "Hi"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        mock_g.ainvoke.assert_not_called()
        mock_g.aupdate_state.assert_called_once()

    async def test_stream_unauthenticated(self, client: AsyncClient, conversation: Conversation) -> None:
        response = await client.get(
            f"/conversations/{conversation.id}/stream",
            params={"query": "test"},
        )
        assert response.status_code == 403

    async def test_stream_conversation_not_found(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.get(
            f"/conversations/{uuid.uuid4()}/stream",
            params={"query": "test"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_stream_empty_query(
        self, client: AsyncClient, auth_headers: dict, conversation: Conversation
    ) -> None:
        response = await client.get(
            f"/conversations/{conversation.id}/stream",
            params={"query": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422
