from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.embedding_service import EmbeddingService


def _make_fake_model(dim: int = 768) -> MagicMock:
    import numpy as np

    model = MagicMock()
    model.encode.side_effect = lambda texts, **kwargs: np.random.rand(len(texts), dim).astype("float32")
    return model


@pytest.fixture
def service_with_mock_model(monkeypatch: pytest.MonkeyPatch) -> EmbeddingService:
    fake_model = _make_fake_model()
    # Patch the module-level singleton so no real model is loaded
    import app.services.embedding_service as es_module

    monkeypatch.setattr(es_module, "_model", fake_model)
    return EmbeddingService()


def test_embed_returns_correct_count(service_with_mock_model: EmbeddingService) -> None:
    texts = ["hello", "world", "foo bar"]
    result = service_with_mock_model.embed(texts)
    assert len(result) == 3


def test_embed_returns_768_dim_vectors(service_with_mock_model: EmbeddingService) -> None:
    texts = ["test sentence"]
    result = service_with_mock_model.embed(texts)
    assert len(result[0]) == 768


def test_embed_returns_list_of_floats(service_with_mock_model: EmbeddingService) -> None:
    texts = ["abc"]
    result = service_with_mock_model.embed(texts)
    assert all(isinstance(v, float) for v in result[0])


def test_embed_empty_input_returns_empty(service_with_mock_model: EmbeddingService) -> None:
    assert service_with_mock_model.embed([]) == []


def test_embed_raises_embedding_error_on_model_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.embedding_service as es_module
    from app.core.exceptions import EmbeddingError

    broken_model = MagicMock()
    broken_model.encode.side_effect = RuntimeError("GPU OOM")
    monkeypatch.setattr(es_module, "_model", broken_model)

    svc = EmbeddingService()
    with pytest.raises(EmbeddingError):
        svc.embed(["test"])
