from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.services.pdf_parser import PageText, parse_pdf


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    for page_num in range(1, 4):
        page = doc.new_page()
        page.insert_text((50, 100), f"Page {page_num} content. " * 15)
    pdf_path = tmp_path / "sample.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    doc.new_page()
    pdf_path = tmp_path / "empty.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_parse_pdf_returns_page_texts(sample_pdf: Path) -> None:
    pages = parse_pdf(sample_pdf)
    assert len(pages) == 3


def test_parse_pdf_page_numbers_are_correct(sample_pdf: Path) -> None:
    pages = parse_pdf(sample_pdf)
    assert [p.page_number for p in pages] == [1, 2, 3]


def test_parse_pdf_text_contains_content(sample_pdf: Path) -> None:
    pages = parse_pdf(sample_pdf)
    assert all("content" in p.text.lower() for p in pages)


def test_parse_pdf_skips_empty_pages(empty_pdf: Path) -> None:
    pages = parse_pdf(empty_pdf)
    assert len(pages) == 0


def test_parse_pdf_returns_list_of_page_text(sample_pdf: Path) -> None:
    pages = parse_pdf(sample_pdf)
    assert all(isinstance(p, PageText) for p in pages)
