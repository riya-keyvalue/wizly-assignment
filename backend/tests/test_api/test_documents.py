from __future__ import annotations

import io
import uuid
from unittest.mock import MagicMock, patch

import fitz
import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_pdf_bytes(pages: int = 2) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 100), f"Page {i + 1} test content " * 20)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _fake_embeddings(n: int, dim: int = 4) -> list[list[float]]:
    return [[0.1] * dim for _ in range(n)]


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pdf_upload(tmp_path: Path):
    """Returns (filename, bytes, content_type) for a valid PDF upload."""
    content = _make_pdf_bytes()
    return ("sample.pdf", content, "application/pdf")


@pytest.fixture
def auth_headers_and_user(db: AsyncSession):
    """Returns a coroutine fixture that registers a user and returns auth headers."""
    return None  # resolved inline below


# ---------------------------------------------------------------------------
# utility: register + login to get a token
# ---------------------------------------------------------------------------


async def _get_token(client: AsyncClient) -> tuple[str, str]:
    email = f"doc_test_{uuid.uuid4().hex[:6]}@example.com"
    pw = "StrongPass1!"
    await client.post("/auth/register", json={"email": email, "password": pw})
    r = await client.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"], email


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_valid_pdf(client: AsyncClient) -> None:
    token, _ = await _get_token(client)
    pdf_bytes = _make_pdf_bytes()

    mock_emb = MagicMock()
    mock_emb.embed.return_value = _fake_embeddings(5)
    mock_vs = MagicMock()
    mock_storage = MagicMock()
    mock_storage.save_file = MagicMock(return_value="test-user/abc12345_sample.pdf")

    with (
        patch("app.services.document_service._get_embedding_service", return_value=mock_emb),
        patch("app.services.document_service._get_vector_store", return_value=mock_vs),
        patch("app.services.document_service._get_storage", return_value=mock_storage),
    ):
        response = await client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            data={"visibility": "private"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    body = response.json()
    assert "data" in body
    assert body["data"]["filename"] == "sample.pdf"
    assert body["data"]["visibility"] == "private"
    assert body["data"]["chunk_count"] >= 0


@pytest.mark.asyncio
async def test_upload_non_pdf_returns_415(client: AsyncClient) -> None:
    token, _ = await _get_token(client)
    response = await client.post(
        "/documents/upload",
        files={"file": ("report.txt", b"hello world", "text/plain")},
        data={"visibility": "private"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_without_auth_returns_401(client: AsyncClient) -> None:
    pdf_bytes = _make_pdf_bytes()
    response = await client.post(
        "/documents/upload",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={"visibility": "private"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient) -> None:
    token, _ = await _get_token(client)
    response = await client.get(
        "/documents/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_list_documents_returns_own_docs(client: AsyncClient) -> None:
    token, _ = await _get_token(client)
    pdf_bytes = _make_pdf_bytes()

    mock_emb = MagicMock()
    mock_emb.embed.return_value = _fake_embeddings(5)
    mock_vs = MagicMock()
    mock_storage = MagicMock()
    mock_storage.save_file = MagicMock(return_value="test-user/abc12345_sample.pdf")

    with (
        patch("app.services.document_service._get_embedding_service", return_value=mock_emb),
        patch("app.services.document_service._get_vector_store", return_value=mock_vs),
        patch("app.services.document_service._get_storage", return_value=mock_storage),
    ):
        await client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            data={"visibility": "private"},
            headers={"Authorization": f"Bearer {token}"},
        )

    response = await client.get(
        "/documents/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient) -> None:
    token, _ = await _get_token(client)
    pdf_bytes = _make_pdf_bytes()

    mock_emb = MagicMock()
    mock_emb.embed.return_value = _fake_embeddings(5)
    mock_vs = MagicMock()
    mock_storage = MagicMock()
    mock_storage.save_file = MagicMock(return_value="test-user/abc12345_sample.pdf")

    with (
        patch("app.services.document_service._get_embedding_service", return_value=mock_emb),
        patch("app.services.document_service._get_vector_store", return_value=mock_vs),
        patch("app.services.document_service._get_storage", return_value=mock_storage),
    ):
        upload_resp = await client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            data={"visibility": "private"},
            headers={"Authorization": f"Bearer {token}"},
        )

        doc_id = upload_resp.json()["data"]["id"]

        delete_resp = await client.delete(
            f"/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_document_not_found(client: AsyncClient) -> None:
    token, _ = await _get_token(client)
    fake_id = uuid.uuid4()
    response = await client.delete(
        f"/documents/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_other_user_cannot_delete(client: AsyncClient) -> None:
    token1, _ = await _get_token(client)
    token2, _ = await _get_token(client)
    pdf_bytes = _make_pdf_bytes()

    mock_emb = MagicMock()
    mock_emb.embed.return_value = _fake_embeddings(5)
    mock_vs = MagicMock()
    mock_storage = MagicMock()
    mock_storage.save_file = MagicMock(return_value="test-user/abc12345_sample.pdf")

    with (
        patch("app.services.document_service._get_embedding_service", return_value=mock_emb),
        patch("app.services.document_service._get_vector_store", return_value=mock_vs),
        patch("app.services.document_service._get_storage", return_value=mock_storage),
    ):
        upload_resp = await client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            data={"visibility": "private"},
            headers={"Authorization": f"Bearer {token1}"},
        )

    doc_id = upload_resp.json()["data"]["id"]

    delete_resp = await client.delete(
        f"/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert delete_resp.status_code == 404
