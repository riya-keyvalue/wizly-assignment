from __future__ import annotations

import uuid

import chromadb
import pytest

from app.services.chunking_service import Chunk
from app.services.vector_store_service import VectorStoreService


def _make_chunks(doc_id: uuid.UUID, n: int = 3) -> list[Chunk]:
    return [Chunk(text=f"chunk text {i}", page_number=1, doc_id=doc_id, chunk_index=i) for i in range(n)]


def _make_embeddings(n: int = 3, dim: int = 4) -> list[list[float]]:
    import random

    return [[random.random() for _ in range(dim)] for _ in range(n)]


@pytest.fixture
def in_memory_store() -> VectorStoreService:
    client = chromadb.EphemeralClient()
    return VectorStoreService(client=client)


def test_upsert_and_count(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    chunks = _make_chunks(doc_id)
    embeddings = _make_embeddings(len(chunks))

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="test.pdf",
        visibility="private",
    )

    col = in_memory_store._collection("private_docs")
    assert col.count() == 3


def test_upsert_global_collection(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    chunks = _make_chunks(doc_id, n=2)
    embeddings = _make_embeddings(2)

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="global.pdf",
        visibility="global",
    )

    col = in_memory_store._collection("global_docs")
    assert col.count() == 2


def test_delete_by_doc_id(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    chunks = _make_chunks(doc_id)
    embeddings = _make_embeddings(len(chunks))

    in_memory_store.upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename="del.pdf",
        visibility="private",
    )

    in_memory_store.delete_by_doc_id(doc_id, "private")

    col = in_memory_store._collection("private_docs")
    remaining = col.get(ids=[f"{doc_id}_{c.chunk_index}" for c in chunks])
    assert len(remaining["ids"]) == 0


def test_upsert_idempotent(in_memory_store: VectorStoreService) -> None:
    doc_id = uuid.uuid4()
    chunks = _make_chunks(doc_id, n=2)
    embeddings = _make_embeddings(2)
    ids = [f"{doc_id}_{c.chunk_index}" for c in chunks]

    in_memory_store.upsert(chunks=chunks, embeddings=embeddings, doc_id=doc_id, filename="f.pdf", visibility="private")
    in_memory_store.upsert(chunks=chunks, embeddings=embeddings, doc_id=doc_id, filename="f.pdf", visibility="private")

    col = in_memory_store._collection("private_docs")
    result = col.get(ids=ids)
    assert len(result["ids"]) == 2  # upsert should not duplicate
