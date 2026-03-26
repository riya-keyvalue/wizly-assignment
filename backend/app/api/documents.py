from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_active_user
from app.models.document import VisibilityEnum
from app.models.user import User
from app.schemas.documents import DocumentListItem, DocumentUploadResponse
from app.services.document_service import delete_document, ingest_document, list_documents

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    visibility: VisibilityEnum = Form(VisibilityEnum.global_),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, DocumentUploadResponse]:
    document = await ingest_document(
        db=db,
        user_id=current_user.id,
        file=file,
        visibility=visibility,
    )
    return {"data": DocumentUploadResponse.model_validate(document)}


@router.get("/", status_code=status.HTTP_200_OK)
async def list_user_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, list[DocumentListItem]]:
    documents = await list_documents(db=db, user_id=current_user.id)
    return {"data": [DocumentListItem.model_validate(d) for d in documents]}


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_user_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    await delete_document(db=db, user_id=current_user.id, doc_id=doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
