"""Documents API endpoints."""
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from ..database import get_session, Document
from ..config import settings

router = APIRouter()


class DocumentCreate(BaseModel):
    project_id: str
    file_type: str = "docx"  # docx, pdf, xlsx
    citation_style: str = "Vancouver"
    language: str = "ja"


class DocumentUpdate(BaseModel):
    section: str
    new_content: str


class DocumentResponse(BaseModel):
    document_id: str
    project_id: str
    file_path: str
    file_type: str
    citation_style: str
    language: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=DocumentResponse)
async def create_document(doc: DocumentCreate):
    """Start document generation.

    Note: Full document generation will be implemented in Phase 3.
    """
    session = get_session()
    try:
        document_id = str(uuid.uuid4())
        file_name = f"{doc.project_id}_{document_id[:8]}.{doc.file_type}"
        file_path = str(Path(settings.outputs_directory) / file_name)

        new_doc = Document(
            document_id=document_id,
            project_id=doc.project_id,
            file_path=file_path,
            file_type=doc.file_type,
            citation_style=doc.citation_style,
            language=doc.language
        )
        session.add(new_doc)
        session.commit()
        session.refresh(new_doc)

        return new_doc
    finally:
        session.close()


@router.get("/{project_id}")
async def list_documents(project_id: str):
    """List documents for a project."""
    session = get_session()
    try:
        docs = session.query(Document).filter(
            Document.project_id == project_id
        ).all()
        return [DocumentResponse.model_validate(d) for d in docs]
    finally:
        session.close()


@router.get("/{document_id}/download")
async def download_document(document_id: str):
    """Download a document."""
    session = get_session()
    try:
        doc = session.query(Document).filter(
            Document.document_id == document_id
        ).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文書が見つかりません")

        file_path = Path(doc.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="ファイルが見つかりません")

        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/octet-stream"
        )
    finally:
        session.close()


@router.put("/{document_id}")
async def update_document(document_id: str, update: DocumentUpdate):
    """Update a document section.

    Note: Section editing will be implemented in Phase 3.
    """
    return {
        "document_id": document_id,
        "section": update.section,
        "message": "セクション更新はPhase 3で実装予定です"
    }
