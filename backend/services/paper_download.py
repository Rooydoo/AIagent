"""Paper download service."""
import json
from pathlib import Path
from typing import Optional, Dict
import httpx

from ..config import settings

PMC_PDF_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
PMC_OA_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"


class PaperDownloader:
    """Service for downloading papers from PMC."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        self.papers_dir = Path(settings.papers_directory)
        self.papers_dir.mkdir(parents=True, exist_ok=True)

    async def download_from_pmc(self, pmc_id: str, metadata: Dict) -> Dict:
        """Download PDF from PMC.

        Args:
            pmc_id: PMC ID (e.g., 'PMC1234567')
            metadata: Paper metadata dictionary

        Returns:
            Dictionary with download result
        """
        # Normalize PMC ID
        if not pmc_id.startswith("PMC"):
            pmc_id = f"PMC{pmc_id}"

        # Create paper directory
        year = metadata.get("year", "unknown")
        first_author = ""
        if metadata.get("authors"):
            first_author = metadata["authors"][0].split()[0].lower()
        folder_name = f"{first_author}_{year}" if first_author else pmc_id.lower()
        paper_dir = self.papers_dir / str(year) / folder_name
        paper_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = paper_dir / "paper.pdf"
        metadata_path = paper_dir / "metadata.json"

        try:
            # Try to get PDF URL from OA service
            pdf_url = await self._get_oa_pdf_url(pmc_id)

            if not pdf_url:
                # Fallback to direct URL
                pdf_url = PMC_PDF_URL.format(pmc_id=pmc_id)

            # Download PDF
            response = await self.client.get(pdf_url)

            if response.status_code == 200 and b"%PDF" in response.content[:10]:
                # Save PDF
                pdf_path.write_bytes(response.content)

                # Check page count
                page_count = self._estimate_page_count(response.content)
                if page_count > settings.max_paper_pages:
                    pdf_path.unlink()
                    return {
                        "success": False,
                        "error": f"論文が{page_count}ページあり、制限（{settings.max_paper_pages}ページ）を超えています",
                        "pmc_id": pmc_id
                    }

                # Save metadata
                metadata["pdf_path"] = str(pdf_path)
                metadata["page_count"] = page_count
                metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))

                return {
                    "success": True,
                    "pdf_path": str(pdf_path),
                    "metadata_path": str(metadata_path),
                    "page_count": page_count,
                    "pmc_id": pmc_id
                }
            else:
                return {
                    "success": False,
                    "error": "PDFのダウンロードに失敗しました（フリーアクセスでない可能性があります）",
                    "pmc_id": pmc_id
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pmc_id": pmc_id
            }

    async def _get_oa_pdf_url(self, pmc_id: str) -> Optional[str]:
        """Get PDF URL from PMC Open Access service."""
        try:
            params = {"id": pmc_id, "format": "pdf"}
            response = await self.client.get(PMC_OA_URL, params=params)

            if response.status_code == 200:
                # Parse XML response for PDF link
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.text)
                link = root.find(".//link[@format='pdf']")
                if link is not None:
                    return link.get("href")
        except Exception:
            pass
        return None

    def _estimate_page_count(self, pdf_content: bytes) -> int:
        """Estimate page count from PDF content."""
        try:
            # Simple estimation by counting /Page objects
            count = pdf_content.count(b"/Type /Page")
            # Also try /Type/Page (no space)
            count += pdf_content.count(b"/Type/Page")
            return max(count, 1)
        except Exception:
            return 1

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def download_papers(pmids_with_metadata: list) -> Dict:
    """Download multiple papers.

    Args:
        pmids_with_metadata: List of dicts with pmid, pmc_id, and metadata

    Returns:
        Summary of download results
    """
    downloader = PaperDownloader()
    results = {
        "downloaded": [],
        "failed": []
    }

    try:
        for item in pmids_with_metadata:
            pmc_id = item.get("pmc_id")
            if not pmc_id:
                results["failed"].append({
                    "pmid": item.get("pmid"),
                    "error": "PMC IDがありません（フリーアクセスではない可能性）"
                })
                continue

            result = await downloader.download_from_pmc(pmc_id, item)
            if result["success"]:
                results["downloaded"].append(result)
            else:
                results["failed"].append({
                    "pmid": item.get("pmid"),
                    "pmc_id": pmc_id,
                    "error": result["error"]
                })
    finally:
        await downloader.close()

    return results
