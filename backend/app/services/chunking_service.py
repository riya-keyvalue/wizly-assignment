from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.pdf_parser import PageText

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


@dataclass
class Chunk:
    text: str
    page_number: int
    doc_id: uuid.UUID
    chunk_index: int = field(default=0)


def chunk_text(pages: list[PageText], doc_id: uuid.UUID) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    chunks: list[Chunk] = []
    for page in pages:
        splits = splitter.split_text(page.text)
        for _i, text in enumerate(splits):
            chunks.append(
                Chunk(
                    text=text,
                    page_number=page.page_number,
                    doc_id=doc_id,
                    chunk_index=len(chunks),
                )
            )
    logger.info(f"Produced {len(chunks)} chunks for doc {doc_id}")
    return chunks
