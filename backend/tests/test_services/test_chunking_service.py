from __future__ import annotations

import uuid

from app.services.chunking_service import CHUNK_SIZE, Chunk, chunk_text
from app.services.pdf_parser import PageText


def _make_pages(n_pages: int = 2, words_per_page: int = 200) -> list[PageText]:
    return [PageText(page_number=i + 1, text=("word " * words_per_page).strip()) for i in range(n_pages)]


def test_chunk_text_returns_chunks() -> None:
    doc_id = uuid.uuid4()
    pages = _make_pages(1, 300)
    chunks = chunk_text(pages, doc_id)
    assert len(chunks) > 0


def test_chunk_text_respects_chunk_size() -> None:
    doc_id = uuid.uuid4()
    pages = _make_pages(1, 500)
    chunks = chunk_text(pages, doc_id)
    for chunk in chunks:
        assert len(chunk.text) <= CHUNK_SIZE * 1.1  # allow small splitter overshoot


def test_chunk_text_preserves_doc_id() -> None:
    doc_id = uuid.uuid4()
    pages = _make_pages(2)
    chunks = chunk_text(pages, doc_id)
    assert all(c.doc_id == doc_id for c in chunks)


def test_chunk_text_indices_are_sequential() -> None:
    doc_id = uuid.uuid4()
    pages = _make_pages(2, 300)
    chunks = chunk_text(pages, doc_id)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_text_returns_dataclass_chunks() -> None:
    doc_id = uuid.uuid4()
    pages = _make_pages(1)
    chunks = chunk_text(pages, doc_id)
    assert all(isinstance(c, Chunk) for c in chunks)


def test_chunk_text_empty_pages_returns_empty() -> None:
    doc_id = uuid.uuid4()
    chunks = chunk_text([], doc_id)
    assert chunks == []
