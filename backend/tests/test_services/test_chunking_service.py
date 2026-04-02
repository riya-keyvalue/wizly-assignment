from __future__ import annotations

import uuid
from pathlib import Path

import fitz
import pytest

from app.core.config import settings
from app.services.chunking_service import (
    MIN_SENTENCES_PER_CHUNK,
    Chunk as AppChunk,
    chunk_documents_batch,
    chunk_text as semantic_chunk_text,
    get_semantic_chunker,
    reset_semantic_chunker,
)
from app.services.pdf_parser import PageText, parse_pdf


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    for page_num in range(1, 4):
        page = doc.new_page()
        paragraph = (
            f"Page {page_num} introduces solar panel efficiency studies. "
            f"Further measurements were taken in controlled environments. "
            f"The results suggest notable improvements over prior work. " * 3
        )
        page.insert_text((50, 100), paragraph)
    pdf_path = tmp_path / "fixture.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def fast_chunker_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
    monkeypatch.setattr(settings, "chunk_max_tokens", 512)
    monkeypatch.setattr(settings, "chunk_similarity_threshold", 0.75)
    reset_semantic_chunker()
    yield
    reset_semantic_chunker()


def test_semantic_chunker_singleton(fast_chunker_settings: None) -> None:
    a = get_semantic_chunker()
    b = get_semantic_chunker()
    assert a is b


def test_chunk_text_returns_chunks(fast_chunker_settings: None) -> None:
    doc_id = uuid.uuid4()
    pages = [PageText(page_number=1, text=("Sentence one. Sentence two. " * 40).strip())]
    chunks = semantic_chunk_text(pages, doc_id)
    assert len(chunks) > 0


def test_chunks_respect_max_token_budget(fast_chunker_settings: None) -> None:
    doc_id = uuid.uuid4()
    pages = [PageText(page_number=1, text=("Paragraph alpha. " * 200).strip())]
    chunks = semantic_chunk_text(pages, doc_id)
    tokenizer = get_semantic_chunker().tokenizer
    for chunk in chunks:
        assert len(tokenizer.encode(chunk.text)) <= settings.chunk_max_tokens


def test_chunks_not_empty_or_tiny(fast_chunker_settings: None) -> None:
    doc_id = uuid.uuid4()
    pages = [PageText(page_number=1, text=("Well formed sentence one. " * 30).strip())]
    chunks = semantic_chunk_text(pages, doc_id)
    for chunk in chunks:
        assert len(chunk.text.strip()) >= 24


def test_chunk_documents_batch_multi(fast_chunker_settings: None) -> None:
    d1 = uuid.uuid4()
    d2 = uuid.uuid4()
    p1 = [PageText(page_number=1, text=("First doc sentence. " * 25).strip())]
    p2 = [PageText(page_number=1, text=("Second doc sentence. " * 25).strip())]
    out = chunk_documents_batch([(d1, p1), (d2, p2)])
    assert len(out) == 2
    assert len(out[0]) >= 1 and len(out[1]) >= 1
    assert all(c.doc_id == d1 for c in out[0])
    assert all(c.doc_id == d2 for c in out[1])


def test_chunk_text_preserves_doc_id(fast_chunker_settings: None) -> None:
    doc_id = uuid.uuid4()
    pages = [
        PageText(page_number=1, text=("A short text. " * 25).strip()),
        PageText(page_number=2, text=("Another block. " * 25).strip()),
    ]
    chunks = semantic_chunk_text(pages, doc_id)
    assert all(c.doc_id == doc_id for c in chunks)


def test_chunk_text_indices_and_metadata(fast_chunker_settings: None) -> None:
    doc_id = uuid.uuid4()
    pages = [PageText(page_number=1, text=("One. Two. Three. Four. Five. Six. " * 15).strip())]
    chunks = semantic_chunk_text(pages, doc_id)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert isinstance(c, AppChunk)
        assert c.end_index >= c.start_index
        assert c.token_count > 0


def test_chunk_text_full_document_from_pdf(fast_chunker_settings: None, sample_pdf: Path) -> None:
    doc_id = uuid.uuid4()
    pages = parse_pdf(sample_pdf)
    chunks = semantic_chunk_text(pages, doc_id)
    assert len(chunks) >= 1
    tokenizer = get_semantic_chunker().tokenizer
    for c in chunks:
        assert len(tokenizer.encode(c.text)) <= settings.chunk_max_tokens
        assert len(c.text.strip()) >= 24


def test_min_sentences_per_chunk_matches_config() -> None:
    assert MIN_SENTENCES_PER_CHUNK == 2


def test_chunk_text_empty_pages_returns_empty(fast_chunker_settings: None) -> None:
    doc_id = uuid.uuid4()
    assert semantic_chunk_text([], doc_id) == []
