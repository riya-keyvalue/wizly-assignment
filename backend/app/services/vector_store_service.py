from __future__ import annotations

import logging
import uuid

import chromadb
from chromadb import Collection

from app.core.config import settings
from app.services.chunking_service import Chunk

logger = logging.getLogger(__name__)

GLOBAL_COLLECTION = "global_docs"
PRIVATE_COLLECTION = "private_docs"

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        logger.info(f"ChromaDB client initialised at {settings.chroma_persist_dir}")
    return _client


class VectorStoreService:
    def __init__(self, client: chromadb.ClientAPI | None = None) -> None:
        self._client = client or _get_client()

    def _collection(self, name: str) -> Collection:
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        doc_id: uuid.UUID,
        filename: str,
        visibility: str,
        user_id: str,
    ) -> None:
        if not chunks:
            logger.warning(f"No chunks to upsert for doc {doc_id} — skipping ChromaDB write")
            return
        collection_name = GLOBAL_COLLECTION if visibility == "global" else PRIVATE_COLLECTION
        col = self._collection(collection_name)
        ids = [f"{doc_id}_{c.chunk_index}" for c in chunks]
        metadatas = [
            {
                "doc_id": str(doc_id),
                "filename": filename,
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
                "visibility": visibility,
                "user_id": user_id,
            }
            for c in chunks
        ]
        documents = [c.text for c in chunks]
        col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        logger.info(f"Upserted {len(chunks)} chunks for doc {doc_id} into '{collection_name}'")

    def delete_by_doc_id(self, doc_id: uuid.UUID, visibility: str) -> None:
        collection_name = GLOBAL_COLLECTION if visibility == "global" else PRIVATE_COLLECTION
        try:
            col = self._collection(collection_name)
            col.delete(where={"doc_id": str(doc_id)})
            logger.info(f"Deleted chunks for doc {doc_id} from '{collection_name}'")
        except Exception as exc:
            logger.warning(f"Could not delete chunks for doc {doc_id}: {exc}")

    def query(
        self,
        embedding: list[float],
        visibility: str,
        top_k: int = 20,
        user_id: str | None = None,
    ) -> list[dict]:
        collection_name = GLOBAL_COLLECTION if visibility == "global" else PRIVATE_COLLECTION
        col = self._collection(collection_name)

        # Private collection: always filtered by owner user_id.
        # Global collection: unfiltered by default; optionally scoped to a specific owner
        # (used by share-link sessions to restrict retrieval to that owner's global docs).
        where: dict | None = None
        if visibility == "private":
            if not user_id:
                logger.warning("Private query attempted without user_id — returning empty result")
                return []
            where = {"user_id": user_id}
        elif visibility == "global" and user_id:
            where = {"user_id": user_id}

        count = col.count()
        if count == 0:
            return []

        # When a where filter is applied, col.count() returns the total collection
        # size (all users), not the filtered count. ChromaDB 0.5.x raises
        # InvalidArgumentError if n_results > number of matching documents.
        # Pre-fetch the filtered IDs to get the true upper bound.
        if where:
            filtered_ids = col.get(where=where, include=[], limit=count)["ids"]
            effective_count = len(filtered_ids)
            logger.info(
                f"Filtered query: where={where}, total_docs={count}, "
                f"matching_docs={effective_count}, requested_top_k={top_k}"
            )
            if effective_count == 0:
                logger.info(f"No chunks match filter {where} — returning empty")
                return []
            n = min(top_k, effective_count)
        else:
            effective_count = count
            n = min(top_k, effective_count)

        results = col.query(
            query_embeddings=[embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
            where=where,
        )
        chunks = []
        if results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                strict=True,
            ):
                chunks.append({**meta, "text": doc, "score": 1.0 - dist})
        return chunks
