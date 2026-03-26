from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded")
    return _model


class EmbeddingService:
    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            model = _get_model()
            vectors = model.encode(texts, convert_to_numpy=True)
            return [v.tolist() for v in vectors]
        except Exception as exc:
            logger.error(f"Embedding failed: {exc}")
            raise EmbeddingError() from exc
