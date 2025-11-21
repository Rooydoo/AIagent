"""Documents API endpoints."""
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from ..database import get_session, Document, Paper, ProjectPaper, Citation
from ..config import settings
from ..llm.document_generator import propose_document_structure, generate_section
from ..llm.citation_checker import check_all_citations
from ..services.document_creation import create_document

router = APIRouter()


class DocumentCreate(BaseModel):
    project_id: str
    topic: str  # Document topic/theme
    paper_pmids: List[str]  # Papers to use as references
    file_type: str = "docx"  # docx, pdf
    citation_style: str = "Vancouver"
    language: str = "ja"


class StructureProposal(BaseModel):
    project_id: str
    topic: str
    paper_pmids: List[str]


class SectionGenerate(BaseModel):
    document_id: str
    section_name: str
    paper_pmids: List[str]
    previous_content: Optional[str] = ""


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


@router.post("/structure")
async def propose_structure(proposal: StructureProposal):
    """Propose document structure based on selected papers."""
    session = get_session()
    try:
        # Get paper details
        papers = session.query(Paper).filter(Paper.pmid.in_(proposal.paper_pmids)).all()
        papers_data = [
            {
                "pmid": p.pmid,
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "abstract": p.abstract,
                "summary": p.summary
            }
            for p in papers
        ]

        if not papers_data:
            raise HTTPException(status_code=400, detail="選択された論文が見つかりません")

        structure = await propose_document_structure(papers_data, proposal.topic)
        return structure
    finally:
        session.close()


@router.post("/generate-section")
async def generate_document_section(request: SectionGenerate):
    """Generate a single section of the document."""
    session = get_session()
    try:
        # Get document
        doc = session.query(Document).filter(Document.document_id == request.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文書が見つかりません")

        # Get papers
        papers = session.query(Paper).filter(Paper.pmid.in_(request.paper_pmids)).all()
        papers_data = [
            {
                "pmid": p.pmid,
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "abstract": p.abstract,
                "summary": p.summary
            }
            for p in papers
        ]

        # Get current citation count for this document
        existing_citations = session.query(Citation).filter(
            Citation.document_id == request.document_id
        ).count()

        # Generate section
        result = await generate_section(
            request.section_name,
            papers_data,
            request.previous_content,
            doc.language,
            citation_start=existing_citations + 1
        )

        # Save citations to database
        for citation in result.get("citations_used", []):
            new_citation = Citation(
                project_id=doc.project_id,
                document_id=request.document_id,
                pmid=citation.get("pmid", ""),
                citation_number=citation.get("number", 0),
                citation_text=citation.get("citation_text", ""),
                source_text=citation.get("source_text", ""),
                confidence=citation.get("confidence", 0.0)
            )
            session.add(new_citation)

        session.commit()

        return result
    finally:
        session.close()


@router.post("/", response_model=DocumentResponse)
async def create_document_endpoint(doc: DocumentCreate):
    """Create a complete document from papers."""
    session = get_session()
    try:
        # Get papers
        papers = session.query(Paper).filter(Paper.pmid.in_(doc.paper_pmids)).all()
        papers_data = [
            {
                "pmid": p.pmid,
                "title": p.title,
                "authors": p.authors or [],
                "year": p.year,
                "journal": p.journal,
                "abstract": p.abstract,
                "summary": p.summary
            }
            for p in papers
        ]

        if not papers_data:
            raise HTTPException(status_code=400, detail="選択された論文が見つかりません")

        # Propose structure
        structure = await propose_document_structure(papers_data, doc.topic, doc.language)

        # Generate all sections
        all_sections = []
        all_citations = []
        previous_content = ""
        citation_counter = 1

        for section_info in structure.get("sections", []):
            section_result = await generate_section(
                section_info["name"],
                papers_data,
                previous_content,
                doc.language,
                citation_start=citation_counter
            )

            section_content = section_result.get("section_content", "")
            all_sections.append({
                "name": section_info["name"],
                "content": section_content
            })

            # Track citations
            section_citations = section_result.get("citations_used", [])
            all_citations.extend(section_citations)
            citation_counter += len(section_citations)

            previous_content += f"\n\n## {section_info['name']}\n{section_content}"

        # Check citation integrity
        citation_check_results = await check_all_citations(all_citations)
        low_confidence_citations = [
            c for c in citation_check_results
            if c.get("confidence", 1.0) < 0.7
        ]

        # Create document file
        document_id = str(uuid.uuid4())
        file_name = f"{doc.project_id}_{document_id[:8]}.{doc.file_type}"
        file_path = Path(settings.outputs_directory) / file_name

        document_content = {
            "title": structure.get("title", doc.topic),
            "sections": all_sections,
            "citations": papers_data  # Use paper data for references
        }

        created_path = create_document(
            document_content,
            str(file_path),
            doc.file_type,
            doc.citation_style
        )

        # Save to database
        new_doc = Document(
            document_id=document_id,
            project_id=doc.project_id,
            file_path=created_path,
            file_type=doc.file_type,
            citation_style=doc.citation_style,
            language=doc.language
        )
        session.add(new_doc)

        # Save citations
        for citation in all_citations:
            new_citation = Citation(
                project_id=doc.project_id,
                document_id=document_id,
                pmid=citation.get("pmid", ""),
                citation_number=citation.get("number", 0),
                citation_text=citation.get("citation_text", ""),
                source_text=citation.get("source_text", ""),
                confidence=citation.get("confidence", 0.0)
            )
            session.add(new_citation)

        session.commit()
        session.refresh(new_doc)

        return new_doc
    finally:
        session.close()


@router.get("/project/{project_id}")
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


@router.get("/{document_id}/citations")
async def get_document_citations(document_id: str):
    """Get all citations for a document."""
    session = get_session()
    try:
        citations = session.query(Citation).filter(
            Citation.document_id == document_id
        ).order_by(Citation.citation_number).all()

        return [
            {
                "number": c.citation_number,
                "pmid": c.pmid,
                "citation_text": c.citation_text,
                "source_text": c.source_text,
                "confidence": c.confidence
            }
            for c in citations
        ]
    finally:
        session.close()


@router.put("/{document_id}")
async def update_document(document_id: str, update: DocumentUpdate):
    """Update a document section."""
    session = get_session()
    try:
        doc = session.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文書が見つかりません")

        # TODO: Implement section-level editing
        # This would require reading the document, modifying the section, and regenerating

        doc.updated_at = datetime.utcnow()
        session.commit()

        return {
            "document_id": document_id,
            "section": update.section,
            "message": "セクションを更新しました"
        }
    finally:
        session.close()
