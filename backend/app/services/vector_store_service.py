from __future__ import annotations

import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.services.chunking_service import Chunk

logger = logging.getLogger(__name__)

GLOBAL_COLLECTION = "global_docs"
PRIVATE_COLLECTION = "private_docs"

# Stable namespace for deterministic point IDs from (doc_id, chunk_index)
_POINT_ID_NAMESPACE = uuid.UUID("018e2d6e-8000-7000-8000-000000000001")

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        kwargs: dict = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        _client = QdrantClient(**kwargs)
        logger.info("Qdrant client initialised (url=%s)", settings.qdrant_url)
    return _client


def _stable_point_id(doc_id: uuid.UUID, chunk_index: int) -> uuid.UUID:
    return uuid.uuid5(_POINT_ID_NAMESPACE, f"{doc_id}_{chunk_index}")


class VectorStoreService:
    def __init__(self, client: QdrantClient | None = None) -> None:
        self._client = client or _get_client()

    def _ensure_collection(self, name: str) -> None:
        if self._client.collection_exists(name):
            return
        self._client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )
        self._client.create_payload_index(
            collection_name=name,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=name,
            field_name="user_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Created Qdrant collection %r with dim=%s", name, settings.embedding_dimensions)

    @staticmethod
    def _query_filter(visibility: str, user_id: str | None) -> Filter | None:
        if visibility == "private":
            if not user_id:
                return None
            return Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
        if visibility == "global" and user_id:
            return Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
        return None

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
            logger.warning("No chunks to upsert for doc %s — skipping Qdrant write", doc_id)
            return
        collection_name = GLOBAL_COLLECTION if visibility == "global" else PRIVATE_COLLECTION
        self._ensure_collection(collection_name)
        points = []
        for chunk, emb in zip(chunks, embeddings, strict=True):
            pid = _stable_point_id(doc_id, chunk.chunk_index)
            payload = {
                "doc_id": str(doc_id),
                "filename": filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "start_index": chunk.start_index,
                "end_index": chunk.end_index,
                "token_count": chunk.token_count,
                "visibility": visibility,
                "user_id": user_id,
                "text": chunk.text,
            }
            points.append(PointStruct(id=str(pid), vector=emb, payload=payload))
        self._client.upsert(collection_name=collection_name, points=points)
        logger.info("Upserted %s chunks for doc %s into %r", len(chunks), doc_id, collection_name)

    def delete_by_doc_id(self, doc_id: uuid.UUID, visibility: str) -> None:
        collection_name = GLOBAL_COLLECTION if visibility == "global" else PRIVATE_COLLECTION
        if not self._client.collection_exists(collection_name):
            return
        try:
            self._client.delete(
                collection_name=collection_name,
                points_selector=FilterSelector(
                    filter=Filter(
                        must=[FieldCondition(key="doc_id", match=MatchValue(value=str(doc_id)))]
                    )
                ),
            )
            logger.info("Deleted chunks for doc %s from %r", doc_id, collection_name)
        except Exception as exc:
            logger.warning("Could not delete chunks for doc %s: %s", doc_id, exc)

    def query(
        self,
        embedding: list[float],
        visibility: str,
        top_k: int = 20,
        user_id: str | None = None,
    ) -> list[dict]:
        collection_name = GLOBAL_COLLECTION if visibility == "global" else PRIVATE_COLLECTION
        if not self._client.collection_exists(collection_name):
            return []

        q_filter = self._query_filter(visibility, user_id)
        if visibility == "private" and q_filter is None:
            logger.warning("Private query attempted without user_id — returning empty result")
            return []

        total = self._client.count(collection_name=collection_name, exact=True).count
        if total == 0:
            return []

        if q_filter is not None:
            filtered = self._client.count(
                collection_name=collection_name,
                count_filter=q_filter,
                exact=True,
            ).count
            if filtered == 0:
                logger.info("No chunks match filter for %r — returning empty", collection_name)
                return []
            n = min(top_k, filtered)
        else:
            n = min(top_k, total)

        response = self._client.query_points(
            collection_name=collection_name,
            query=embedding,
            query_filter=q_filter,
            limit=n,
            with_payload=True,
        )

        chunks: list[dict] = []
        for point in response.points:
            if point.payload is None:
                continue
            payload = dict(point.payload)
            text = str(payload.pop("text", ""))
            chunks.append({**payload, "text": text, "score": float(point.score or 0.0)})
        return chunks

    def collection_point_count(self, collection_name: str) -> int:
        if not self._client.collection_exists(collection_name):
            return 0
        return self._client.count(collection_name=collection_name, exact=True).count

    def collection_sample_payloads(
        self, collection_name: str, limit: int = 5
    ) -> tuple[list[str], list[dict]]:
        if not self._client.collection_exists(collection_name):
            return [], []
        points, _cursor = self._client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        ids = [str(p.id) for p in points]
        metas = []
        for p in points:
            pl = dict(p.payload) if p.payload else {}
            pl.pop("text", None)
            metas.append(pl)
        return ids, metas
