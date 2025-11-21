"""PubMed/PMC API client."""
import asyncio
from typing import Optional, List, Dict
import httpx
from xml.etree import ElementTree as ET

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


class PubMedClient:
    """Client for PubMed/PMC APIs."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, max_results: int = 50) -> Dict:
        """Search PubMed for articles.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            Dictionary with search results
        """
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = await self.client.get(PUBMED_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()

            id_list = data.get("esearchresult", {}).get("idlist", [])
            total_count = int(data.get("esearchresult", {}).get("count", 0))

            return {
                "pmids": id_list,
                "total_count": total_count,
                "returned_count": len(id_list)
            }
        except Exception as e:
            return {"error": str(e), "pmids": [], "total_count": 0}

    async def fetch_details(self, pmids: List[str]) -> List[Dict]:
        """Fetch detailed information for given PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of article details
        """
        if not pmids:
            return []

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract"
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = await self.client.get(PUBMED_FETCH_URL, params=params)
            response.raise_for_status()
            return self._parse_pubmed_xml(response.text)
        except Exception as e:
            return [{"error": str(e)}]

    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict]:
        """Parse PubMed XML response."""
        articles = []
        try:
            root = ET.fromstring(xml_text)
            for article in root.findall(".//PubmedArticle"):
                medline = article.find(".//MedlineCitation")
                if medline is None:
                    continue

                pmid_elem = medline.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""

                article_elem = medline.find(".//Article")
                if article_elem is None:
                    continue

                # Title
                title_elem = article_elem.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else ""

                # Abstract
                abstract_parts = []
                abstract_elem = article_elem.find(".//Abstract")
                if abstract_elem is not None:
                    for text in abstract_elem.findall(".//AbstractText"):
                        if text.text:
                            label = text.get("Label", "")
                            if label:
                                abstract_parts.append(f"{label}: {text.text}")
                            else:
                                abstract_parts.append(text.text)
                abstract = " ".join(abstract_parts)

                # Authors
                authors = []
                author_list = article_elem.find(".//AuthorList")
                if author_list is not None:
                    for author in author_list.findall(".//Author"):
                        lastname = author.find("LastName")
                        forename = author.find("ForeName")
                        if lastname is not None:
                            name = lastname.text
                            if forename is not None:
                                name = f"{lastname.text} {forename.text}"
                            authors.append(name)

                # Journal
                journal_elem = article_elem.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else ""

                # Year
                year = None
                pub_date = article_elem.find(".//PubDate/Year")
                if pub_date is not None:
                    year = int(pub_date.text)
                else:
                    medline_date = article_elem.find(".//PubDate/MedlineDate")
                    if medline_date is not None and medline_date.text:
                        year = int(medline_date.text[:4])

                # PMC ID
                pmc_id = None
                for article_id in article.findall(".//ArticleIdList/ArticleId"):
                    if article_id.get("IdType") == "pmc":
                        pmc_id = article_id.text
                        break

                articles.append({
                    "pmid": pmid,
                    "pmc_id": pmc_id,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "journal": journal,
                    "year": year,
                    "has_free_fulltext": pmc_id is not None
                })

        except ET.ParseError as e:
            return [{"error": f"XML parse error: {str(e)}"}]

        return articles

    async def search_pmc(self, query: str, max_results: int = 50) -> Dict:
        """Search PMC for free full-text articles.

        Args:
            query: Search query string
            max_results: Maximum number of results

        Returns:
            Dictionary with PMC IDs
        """
        params = {
            "db": "pmc",
            "term": f"{query} AND free fulltext[filter]",
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = await self.client.get(PMC_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()

            id_list = data.get("esearchresult", {}).get("idlist", [])
            return {
                "pmc_ids": [f"PMC{pid}" for pid in id_list],
                "total_count": int(data.get("esearchresult", {}).get("count", 0))
            }
        except Exception as e:
            return {"error": str(e), "pmc_ids": []}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
