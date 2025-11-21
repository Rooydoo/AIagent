"""Papers API endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..database import get_session, Paper, ProjectPaper
from ..integrations.pubmed_client import PubMedClient
from ..services.paper_download import download_papers
from ..llm.summarizer import summarize_abstract
from ..llm.query_optimizer import optimize_query

router = APIRouter()


class PaperSearch(BaseModel):
    query: str
    max_results: int = 50
    optimize_query: bool = True
    # Publication type filters
    include_types: Optional[List[str]] = None  # review, systematic_review, meta_analysis, rct, clinical_trial, case_report, guideline, observational, editorial, letter, comment
    exclude_types: Optional[List[str]] = None  # All above + retracted
    # Other filters
    free_fulltext_only: bool = False
    year_from: Optional[int] = None
    year_to: Optional[int] = None


class PaperDownload(BaseModel):
    papers: List[dict]  # List of paper metadata with pmid, pmc_id, etc.
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
    """Search papers in PubMed/PMC."""
    client = PubMedClient()

    try:
        # Optimize query if requested
        query = search.query
        optimized_query = None
        if search.optimize_query:
            optimized_query = await optimize_query(search.query)
            query = optimized_query

        # Search PubMed with filters
        search_result = await client.search(
            query,
            search.max_results,
            include_types=search.include_types,
            exclude_types=search.exclude_types,
            free_fulltext_only=search.free_fulltext_only,
            year_from=search.year_from,
            year_to=search.year_to,
        )

        if "error" in search_result:
            return {
                "query": search.query,
                "optimized_query": optimized_query,
                "total_results": 0,
                "results": [],
                "error": search_result["error"]
            }

        # Fetch details for found PMIDs
        pmids = search_result.get("pmids", [])
        if not pmids:
            return {
                "query": search.query,
                "optimized_query": optimized_query,
                "total_results": 0,
                "results": [],
                "message": "検索結果が見つかりませんでした"
            }

        details = await client.fetch_details(pmids)

        # Generate summaries for abstracts (first 10 only for speed)
        results_with_summary = []
        for i, paper in enumerate(details):
            if "error" in paper:
                continue

            summary = ""
            if i < 10 and paper.get("abstract"):
                try:
                    summary = await summarize_abstract(paper["abstract"])
                except Exception:
                    summary = ""

            results_with_summary.append({
                **paper,
                "summary": summary,
                "can_download": paper.get("has_free_fulltext", False)
            })

        return {
            "query": search.query,
            "optimized_query": optimized_query,
            "total_results": search_result.get("total_count", len(results_with_summary)),
            "returned_count": len(results_with_summary),
            "results": results_with_summary
        }

    finally:
        await client.close()


@router.post("/download")
async def download_papers_endpoint(download: PaperDownload):
    """Download papers by PMID."""
    # Filter papers with PMC IDs (free access)
    downloadable = [p for p in download.papers if p.get("pmc_id")]

    if not downloadable:
        return {
            "requested": len(download.papers),
            "downloaded": [],
            "failed": [{"error": "ダウンロード可能な論文がありません（PMC IDが必要です）"}],
            "message": "フリーアクセスの論文のみダウンロード可能です"
        }

    # Download papers
    result = await download_papers(downloadable)

    # Save to database
    session = get_session()
    try:
        for item in result["downloaded"]:
            paper_data = next((p for p in download.papers if p.get("pmc_id") == item["pmc_id"]), {})

            existing = session.query(Paper).filter(Paper.pmid == paper_data.get("pmid")).first()
            if existing:
                existing.pdf_path = item["pdf_path"]
                existing.metadata_path = item["metadata_path"]
                existing.page_count = item["page_count"]
            else:
                new_paper = Paper(
                    pmid=paper_data.get("pmid", ""),
                    pmc_id=item["pmc_id"],
                    title=paper_data.get("title", ""),
                    authors=paper_data.get("authors"),
                    journal=paper_data.get("journal"),
                    year=paper_data.get("year"),
                    abstract=paper_data.get("abstract"),
                    summary=paper_data.get("summary"),
                    pdf_path=item["pdf_path"],
                    metadata_path=item["metadata_path"],
                    page_count=item["page_count"]
                )
                session.add(new_paper)

            # Link to project if specified
            if download.project_id and paper_data.get("pmid"):
                existing_link = session.query(ProjectPaper).filter(
                    ProjectPaper.project_id == download.project_id,
                    ProjectPaper.pmid == paper_data.get("pmid")
                ).first()
                if not existing_link:
                    session.add(ProjectPaper(
                        project_id=download.project_id,
                        pmid=paper_data.get("pmid")
                    ))

        session.commit()
    finally:
        session.close()

    return {
        "requested": len(download.papers),
        "downloaded": result["downloaded"],
        "failed": result["failed"]
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
