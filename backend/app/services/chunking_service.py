from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from chonkie import SemanticChunker
from chonkie.tokenizer import TokenizerProtocol
from chonkie.types import Chunk as ChonkieChunk

from app.core.config import settings
from app.services.pdf_parser import PageText

logger = logging.getLogger(__name__)

_semantic_chunker: SemanticChunker | None = None

SIMILARITY_WINDOW = 3
SKIP_WINDOW = 0
MIN_SENTENCES_PER_CHUNK = 2
OVERLAP_TOKENS = 50

CHUNK_SIZE = 512
CHUNK_OVERLAP = OVERLAP_TOKENS


@dataclass
class Chunk:
    """One RAG chunk aligned to the original PDF text."""

    text: str
    page_number: int
    doc_id: uuid.UUID
    chunk_index: int = field(default=0)
    start_index: int = field(default=0)
    end_index: int = field(default=0)
    token_count: int = field(default=0)


def reset_semantic_chunker() -> None:
    """Reset the chunker singleton (tests)."""
    global _semantic_chunker
    _semantic_chunker = None


def get_semantic_chunker() -> SemanticChunker:
    global _semantic_chunker
    if _semantic_chunker is None:
        logger.info(
            "Initialising SemanticChunker model=%s threshold=%s chunk_size=%s",
            settings.embedding_model,
            settings.chunk_similarity_threshold,
            settings.chunk_max_tokens,
        )
        _semantic_chunker = SemanticChunker(
            embedding_model=settings.embedding_model,
            threshold=settings.chunk_similarity_threshold,
            chunk_size=settings.chunk_max_tokens,
            similarity_window=SIMILARITY_WINDOW,
            min_sentences_per_chunk=MIN_SENTENCES_PER_CHUNK,
            skip_window=SKIP_WINDOW,
        )
    return _semantic_chunker


def _join_pages_full_text(pages: list[PageText]) -> str:
    return "\n\n".join(p.text for p in pages)


def _page_spans(pages: list[PageText]) -> list[tuple[int, int, int]]:
    spans: list[tuple[int, int, int]] = []
    offset = 0
    for i, p in enumerate(pages):
        if i > 0:
            offset += 2
        start = offset
        offset += len(p.text)
        spans.append((start, offset, p.page_number))
    return spans


def _page_for_offset(spans: list[tuple[int, int, int]], char_offset: int) -> int:
    if not spans:
        return 1
    for start, end, pn in spans:
        if char_offset < end:
            return pn
    return spans[-1][2]


def _locate_core_chunks_in_full_text(full_text: str, chonkie_chunks: list[ChonkieChunk]) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    pos = 0
    for cc in chonkie_chunks:
        if full_text.startswith(cc.text, pos):
            start = pos
        else:
            found = full_text.find(cc.text, pos)
            if found == -1:
                msg = f"Semantic chunk not found in document near offset {pos}"
                raise ValueError(msg)
            start = found
        end = start + len(cc.text)
        positions.append((start, end))
        pos = end
    return positions


def _apply_overlap_and_truncate(
    core_texts: list[str],
    tokenizer: TokenizerProtocol,
    *,
    overlap_tokens: int,
    max_tokens: int,
) -> tuple[list[str], list[int]]:
    """Overlap each chunk with the tail of the previous *refined* chunk, then cap at max_tokens."""
    if not core_texts:
        return [], []

    final_texts: list[str] = []
    token_counts: list[int] = []

    first = core_texts[0]
    ids = tokenizer.encode(first)
    if len(ids) > max_tokens:
        ids = ids[:max_tokens]
        first = tokenizer.decode(ids)
    final_texts.append(first)
    token_counts.append(len(ids))

    for i in range(1, len(core_texts)):
        prev_ids = tokenizer.encode(final_texts[-1])
        tail = prev_ids[-overlap_tokens:] if len(prev_ids) > overlap_tokens else prev_ids
        curr_ids = tokenizer.encode(core_texts[i])
        merged = tokenizer.decode(tail + curr_ids)
        ids = tokenizer.encode(merged)
        if len(ids) > max_tokens:
            ids = ids[:max_tokens]
            merged = tokenizer.decode(ids)
        final_texts.append(merged)
        token_counts.append(len(ids))

    return final_texts, token_counts


def _finalize_semantic_chunks(
    full_text: str,
    pages: list[PageText],
    doc_id: uuid.UUID,
    chonkie_chunks: list[ChonkieChunk],
    chunker: SemanticChunker,
) -> list[Chunk]:
    if not chonkie_chunks:
        return []
    spans = _page_spans(pages)
    positions = _locate_core_chunks_in_full_text(full_text, chonkie_chunks)
    core_texts = [c.text for c in chonkie_chunks]
    refined_texts, token_counts = _apply_overlap_and_truncate(
        core_texts,
        chunker.tokenizer,
        overlap_tokens=OVERLAP_TOKENS,
        max_tokens=settings.chunk_max_tokens,
    )
    chunks: list[Chunk] = []
    for i, ((start, end), rt, tc) in enumerate(
        zip(positions, refined_texts, token_counts, strict=True),
    ):
        pn = _page_for_offset(spans, start)
        chunks.append(
            Chunk(
                text=rt,
                page_number=pn,
                doc_id=doc_id,
                chunk_index=i,
                start_index=start,
                end_index=end,
                token_count=tc,
            ),
        )
    return chunks


def chunk_text(pages: list[PageText], doc_id: uuid.UUID) -> list[Chunk]:
    """Semantic-chunk full-document text (pages joined). Uses ``chunker.chunk()`` for a single document."""
    if not pages:
        return []
    full_text = _join_pages_full_text(pages)
    if not full_text.strip():
        return []

    chunker = get_semantic_chunker()
    ch_chunks = chunker.chunk(full_text)
    chunks = _finalize_semantic_chunks(full_text, pages, doc_id, ch_chunks, chunker)
    logger.info("Produced %s semantic chunks for doc %s", len(chunks), doc_id)
    return chunks


def chunk_documents_batch(items: list[tuple[uuid.UUID, list[PageText]]]) -> list[list[Chunk]]:
    """Chunk multiple PDFs using ``chunker.chunk_batch()`` (single-doc path still uses one batch of size 1)."""
    if not items:
        return []
    prepared: list[tuple[uuid.UUID, list[PageText], str]] = []
    for doc_id, pages in items:
        joined = _join_pages_full_text(pages) if pages else ""
        prepared.append((doc_id, pages, joined))

    texts = [ft for _, _, ft in prepared]
    chunker = get_semantic_chunker()
    if len(texts) == 1:
        ch_batches = [chunker.chunk(texts[0])]
    else:
        ch_batches = chunker.chunk_batch(texts, show_progress=False)

    result: list[list[Chunk]] = []
    for (doc_id, pages, full_text), ch_list in zip(prepared, ch_batches, strict=True):
        if not full_text.strip():
            result.append([])
            continue
        if not ch_list:
            result.append([])
            continue
        chunks = _finalize_semantic_chunks(full_text, pages, doc_id, ch_list, chunker)
        logger.info("Produced %s semantic chunks for doc %s", len(chunks), doc_id)
        result.append(chunks)
    return result
