from __future__ import annotations

import logging
import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError, FileTooLargeError, InvalidFileTypeError
from app.models.document import Document, VisibilityEnum
from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingService
from app.services.pdf_parser import parse_pdf
from app.services.storage_service import MAX_FILE_SIZE_BYTES, StorageService
from app.services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {"application/pdf"}
_ALLOWED_EXTENSIONS = {".pdf"}

# Lazy singletons — initialised on first use so tests can monkeypatch them.
_embedding_service: EmbeddingService | None = None
_vector_store: VectorStoreService | None = None
_storage: StorageService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def _get_vector_store() -> VectorStoreService:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store


def _get_storage() -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage


def _validate_file(file: UploadFile, content: bytes) -> None:
    ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    content_type = (file.content_type or "").lower().split(";")[0].strip()

    if ext not in _ALLOWED_EXTENSIONS or content_type not in _ALLOWED_CONTENT_TYPES:
        raise InvalidFileTypeError()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError()


async def ingest_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
    visibility: VisibilityEnum,
) -> Document:
    content = await file.read()

    _validate_file(file, content)

    filename = file.filename or "upload.pdf"

    # Upload to S3/LocalStack — returns the object key stored in PostgreSQL
    s3_key = _get_storage().save_file(user_id, filename, content)

    # Parse and embed from the in-memory bytes — no need to re-download from S3
    pages = parse_pdf(content)
    doc_id = uuid.uuid4()
    chunks = chunk_text(pages, doc_id)

    texts = [c.text for c in chunks]
    embeddings = _get_embedding_service().embed(texts)

    _get_vector_store().upsert(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        filename=filename,
        visibility=visibility.value,
        user_id=str(user_id),
    )

    document = Document(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        file_path=s3_key,  # S3 object key, not a filesystem path
        visibility=visibility,
        chunk_count=len(chunks),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    logger.info(f"Ingested document {doc_id} ({len(chunks)} chunks) for user {user_id}")
    return document


async def list_documents(db: AsyncSession, user_id: uuid.UUID) -> list[Document]:
    result = await db.execute(select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc()))
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, user_id: uuid.UUID, doc_id: uuid.UUID) -> None:
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise DocumentNotFoundError()

    _get_vector_store().delete_by_doc_id(doc_id, document.visibility.value)
    _get_storage().delete_file(document.file_path)  # file_path is the S3 object key

    await db.delete(document)
    await db.commit()
    logger.info(f"Deleted document {doc_id} for user {user_id}")
