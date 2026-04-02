from __future__ import annotations

import uuid

import pytest
from qdrant_client import QdrantClient

from app.core.config import settings
from app.services.chunking_service import Chunk
from app.services.vector_store_service import (
    GLOBAL_COLLECTION,
    PRIVATE_COLLECTION,
    VectorStoreService,
)


def _make_chunks(doc_id: uuid.UUID, n: int = 3) -> list[Chunk]:
    return [
        Chunk(
            text=f"chunk text {i}",
            page_number=1,
            doc_id=doc_id,
            chunk_index=i,
            start_index=i * 20,
            end_index=i * 20 + 12,
            token_count=3,
        )
        for i in range(n)
    ]


def _make_embeddings(n: int = 3, dim: int = 4) -> list[list[float]]:
    import random

    return [[random.random() for _ in range(dim)] for _ in range(n)]


@pytest.fixture(autouse=True)
def _use_small_embedding_dim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embedding_dimensions", 4)


@pytest.fixture
def in_memory_store() -> VectorStoreService:
    client = QdrantClient(":memory:")
    return VectorStoreService(client=client)


def test_upsert_and_count(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    user_id = str(uuid.uuid4())
    chunks = _make_chunks(doc_id)
    embeddings = _make_embeddings(len(chunks))

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="test.pdf",
        visibility="private",
        user_id=user_id,
    )

    assert in_memory_store.collection_point_count(PRIVATE_COLLECTION) == 3


def test_upsert_global_collection(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    user_id = str(uuid.uuid4())
    chunks = _make_chunks(doc_id, n=2)
    embeddings = _make_embeddings(2)

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="global.pdf",
        visibility="global",
        user_id=user_id,
    )

    assert in_memory_store.collection_point_count(GLOBAL_COLLECTION) == 2


def test_delete_by_doc_id(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    user_id = str(uuid.uuid4())
    chunks = _make_chunks(doc_id)
    embeddings = _make_embeddings(len(chunks))

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="del.pdf",
        visibility="private",
        user_id=user_id,
    )

    in_memory_store.delete_by_doc_id(doc_id, "private")

    assert in_memory_store.collection_point_count(PRIVATE_COLLECTION) == 0


def test_upsert_payload_has_semantic_metadata(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    user_id = str(uuid.uuid4())
    chunks = _make_chunks(doc_id, n=1)
    embeddings = _make_embeddings(1)

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="meta.pdf",
        visibility="private",
        user_id=user_id,
    )

    points, _ = in_memory_store._client.scroll(
        collection_name=PRIVATE_COLLECTION,
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    assert len(points) == 1
    payload = dict(points[0].payload or {})
    for key in ("doc_id", "start_index", "end_index", "token_count", "text"):
        assert key in payload
    assert payload["start_index"] == 0
    assert payload["end_index"] == 12
    assert payload["token_count"] == 3


def test_upsert_idempotent(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    user_id = str(uuid.uuid4())
    chunks = _make_chunks(doc_id, n=2)
    embeddings = _make_embeddings(2)

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="f.pdf",
        visibility="private",
        user_id=user_id,
    )
    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="f.pdf",
        visibility="private",
        user_id=user_id,
    )

    assert in_memory_store.collection_point_count(PRIVATE_COLLECTION) == 2
