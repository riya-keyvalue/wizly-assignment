from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    page_number: int
    text: str


def parse_pdf(source: Path | bytes) -> list[PageText]:
    """Parse a PDF from a filesystem path or raw bytes.

    Accepts a ``Path`` (local file) or ``bytes`` (in-memory content, e.g.
    directly from an UploadFile without writing to disk first).
    """
    doc = fitz.open(stream=source, filetype="pdf") if isinstance(source, bytes) else fitz.open(str(source))

    pages: list[PageText] = []
    with doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if text:
                pages.append(PageText(page_number=i, text=text))

    label = f"<bytes {len(source)}>" if isinstance(source, bytes) else source.name
    logger.info(f"Parsed {len(pages)} non-empty pages from {label}")
    return pages
