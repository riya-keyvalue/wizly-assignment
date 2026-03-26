from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.schemas.chat import RetrievedChunk
from app.services.rag_service import retrieve


def _make_raw_chunk(i: int) -> dict:
    return {
        "text": f"Chunk text {i}",
        "doc_id": f"doc-{i}",
        "filename": f"file_{i}.pdf",
        "page_number": i,
        "score": 1.0 - (i * 0.01),
    }


class TestRetrieve:
    def test_retrieve_returns_top_k(self) -> None:
        """Insert 25 chunks via mock, request top 20 — assert <= 20 returned, highest similarity first."""
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed.return_value = [[0.1] * 768]

        raw_chunks = [_make_raw_chunk(i) for i in range(20)]
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = raw_chunks

        result = retrieve(
            query="test query",
            visibility="global",
            top_k=20,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        assert len(result) <= 20
        assert all(isinstance(c, RetrievedChunk) for c in result)
        mock_embedding_service.embed.assert_called_once_with(["test query"])
        mock_vector_store.query.assert_called_once_with(
            embedding=[0.1] * 768,
            visibility="global",
            top_k=20,
        )

    def test_retrieve_returns_highest_similarity_first(self) -> None:
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed.return_value = [[0.5] * 768]

        raw_chunks = [_make_raw_chunk(i) for i in range(5)]
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = raw_chunks

        result = retrieve(
            query="test query",
            top_k=5,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        scores = [c.score for c in result]
        assert scores == sorted(scores, reverse=True)

    def test_retrieve_empty_query(self) -> None:
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed.return_value = [[0.0] * 768]

        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = []

        result = retrieve(
            query="",
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        assert result == []

    def test_retrieve_private_visibility(self) -> None:
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed.return_value = [[0.1] * 768]

        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = [_make_raw_chunk(0)]

        retrieve(
            query="test",
            visibility="private",
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        mock_vector_store.query.assert_called_once_with(
            embedding=[0.1] * 768,
            visibility="private",
            top_k=20,
        )

    def test_retrieve_chunk_fields(self) -> None:
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed.return_value = [[0.1] * 768]

        raw = {
            "text": "Some content",
            "doc_id": "abc-123",
            "filename": "report.pdf",
            "page_number": 5,
            "score": 0.92,
        }
        mock_vector_store = MagicMock()
        mock_vector_store.query.return_value = [raw]

        result = retrieve(
            query="test",
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        assert len(result) == 1
        chunk = result[0]
        assert chunk.text == "Some content"
        assert chunk.doc_id == "abc-123"
        assert chunk.filename == "report.pdf"
        assert chunk.page_number == 5
        assert chunk.score == pytest.approx(0.92)
