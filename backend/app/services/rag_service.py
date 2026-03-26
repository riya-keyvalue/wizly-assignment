from __future__ import annotations

import logging

from app.schemas.chat import RetrievedChunk
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)

_embedding_service: EmbeddingService | None = None
_vector_store: VectorStoreService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def _get_vector_store() -> VectorStoreService:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store


def retrieve(
    query: str,
    visibility: str = "global",
    top_k: int = 20,
    user_id: str | None = None,
    *,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStoreService | None = None,
) -> list[RetrievedChunk]:
    """Embed the query and retrieve top-k similar chunks from a single collection.

    For global visibility: all users' global docs are searched (no user filter).
    For private visibility: only the requesting user's private docs are searched.
    """
    if visibility == "private" and not user_id:
        logger.warning("retrieve() called with visibility=private but no user_id — returning empty")
        return []

    emb_svc = embedding_service or _get_embedding_service()
    vs = vector_store or _get_vector_store()

    query_embedding = emb_svc.embed([query])[0]

    raw_chunks = vs.query(
        embedding=query_embedding,
        visibility=visibility,
        top_k=top_k,
        user_id=user_id,
    )

    chunks = [
        RetrievedChunk(
            text=c["text"],
            doc_id=c["doc_id"],
            filename=c["filename"],
            page_number=c["page_number"],
            score=c["score"],
        )
        for c in raw_chunks
    ]

    logger.info(f"Retrieved {len(chunks)} chunks for query (visibility={visibility}, user_id={user_id}, top_k={top_k})")
    return chunks


def retrieve_global_for_owner(
    query: str,
    owner_id: str,
    top_k: int = 5,
    *,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStoreService | None = None,
) -> list[RetrievedChunk]:
    """Retrieve the owner's published (global) documents for share-link sessions.

    Queries the global_docs collection filtered by the owner's user_id metadata field.
    Private documents are never included. Global documents from other users are excluded.
    Used exclusively by anonymous share-link chat sessions.
    """
    if not owner_id:
        logger.warning("retrieve_global_for_owner() called without owner_id — returning empty")
        return []

    logger.info(f"retrieve_global_for_owner: owner_id={owner_id!r} query={query[:60]!r}")

    emb_svc = embedding_service or _get_embedding_service()
    vs = vector_store or _get_vector_store()

    query_embedding = emb_svc.embed([query])[0]

    raw_chunks = vs.query(
        embedding=query_embedding,
        visibility="global",
        top_k=top_k,
        user_id=owner_id,
    )

    chunks = [
        RetrievedChunk(
            text=c["text"],
            doc_id=c["doc_id"],
            filename=c["filename"],
            page_number=c["page_number"],
            score=c["score"],
        )
        for c in raw_chunks
    ]

    logger.info(
        f"retrieve_global_for_owner: {len(chunks)} chunks (owner_id={owner_id}, top_k={top_k})"
    )
    return chunks


def retrieve_for_user(
    query: str,
    user_id: str,
    top_k: int = 20,
    *,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStoreService | None = None,
) -> list[RetrievedChunk]:
    """Retrieve relevant chunks from both global docs and the user's own private docs.

    Queries both collections with the same embedding, merges the results, and
    returns the top-k chunks sorted by relevance score (highest first).

    - Global collection: no user filter — visible to everyone.
    - Private collection: filtered strictly to the requesting user_id.
    """
    emb_svc = embedding_service or _get_embedding_service()
    vs = vector_store or _get_vector_store()

    query_embedding = emb_svc.embed([query])[0]

    global_raw = vs.query(embedding=query_embedding, visibility="global", top_k=top_k, user_id=None)
    private_raw = vs.query(embedding=query_embedding, visibility="private", top_k=top_k, user_id=user_id)

    seen: set[str] = set()
    merged: list[RetrievedChunk] = []

    for c in global_raw + private_raw:
        key = f"{c['doc_id']}_{c['page_number']}_{c['text'][:40]}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            RetrievedChunk(
                text=c["text"],
                doc_id=c["doc_id"],
                filename=c["filename"],
                page_number=c["page_number"],
                score=c["score"],
            )
        )

    merged.sort(key=lambda x: x.score, reverse=True)
    result = merged[:top_k]

    logger.info(
        f"retrieve_for_user: {len(global_raw)} global + {len(private_raw)} private → "
        f"{len(result)} merged (user_id={user_id})"
    )
    return result
