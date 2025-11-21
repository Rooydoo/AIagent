"""Papers API endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import get_session, Paper, ProjectPaper
from ..llm.summarizer import summarize_abstract

router = APIRouter()


class PaperSearch(BaseModel):
    query: str
    max_results: int = 50


class PaperDownload(BaseModel):
    pmids: List[str]
    project_id: Optional[str] = None


class PaperUpdate(BaseModel):
    is_favorite: Optional[bool] = None
    tags: Optional[List[str]] = None


class PaperResponse(BaseModel):
    pmid: str
    pmc_id: Optional[str] = None
    title: str
    authors: Optional[list] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    summary: Optional[str] = None
    pdf_path: Optional[str] = None
    is_favorite: bool = False
    tags: Optional[list] = None

    class Config:
        from_attributes = True


@router.post("/search")
async def search_papers(search: PaperSearch):
    """Search papers in PubMed/PMC.

    Note: This is a placeholder. Actual PubMed API integration
    will be implemented in Phase 2.
    """
    # TODO: Implement actual PubMed API search
    # For now, return mock data structure
    return {
        "query": search.query,
        "total_results": 0,
        "results": [],
        "message": "PubMed検索はPhase 2で実装予定です"
    }


@router.post("/download")
async def download_papers(download: PaperDownload):
    """Download papers by PMID.

    Note: This is a placeholder. Actual download logic
    will be implemented in Phase 2.
    """
    return {
        "requested": download.pmids,
        "downloaded": [],
        "failed": [],
        "message": "論文ダウンロードはPhase 2で実装予定です"
    }


@router.get("/")
async def list_papers(
    project_id: Optional[str] = None,
    favorite_only: bool = False,
    tag: Optional[str] = None
):
    """List papers, optionally filtered."""
    session = get_session()
    try:
        query = session.query(Paper)

        if project_id:
            query = query.join(ProjectPaper).filter(ProjectPaper.project_id == project_id)

        if favorite_only:
            query = query.filter(Paper.is_favorite == True)

        papers = query.all()
        return [PaperResponse.model_validate(p) for p in papers]
    finally:
        session.close()


@router.get("/{pmid}", response_model=PaperResponse)
async def get_paper(pmid: str):
    """Get paper details."""
    session = get_session()
    try:
        paper = session.query(Paper).filter(Paper.pmid == pmid).first()
        if not paper:
            raise HTTPException(status_code=404, detail="論文が見つかりません")
        return paper
    finally:
        session.close()


@router.put("/{pmid}", response_model=PaperResponse)
async def update_paper(pmid: str, update: PaperUpdate):
    """Update paper metadata (tags, favorite)."""
    session = get_session()
    try:
        paper = session.query(Paper).filter(Paper.pmid == pmid).first()
        if not paper:
            raise HTTPException(status_code=404, detail="論文が見つかりません")

        if update.is_favorite is not None:
            paper.is_favorite = update.is_favorite
        if update.tags is not None:
            paper.tags = update.tags

        session.commit()
        session.refresh(paper)
        return paper
    finally:
        session.close()


@router.delete("/{pmid}")
async def delete_paper(pmid: str):
    """Delete a paper."""
    session = get_session()
    try:
        paper = session.query(Paper).filter(Paper.pmid == pmid).first()
        if not paper:
            raise HTTPException(status_code=404, detail="論文が見つかりません")

        session.delete(paper)
        session.commit()
        return {"message": "論文を削除しました", "pmid": pmid}
    finally:
        session.close()
