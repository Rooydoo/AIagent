"""PubMed/PMC API client."""
import asyncio
from typing import Optional, List, Dict
import httpx
from xml.etree import ElementTree as ET

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


# Publication Type filters for PubMed
PUBLICATION_TYPES = {
    "review": "review[pt]",
    "systematic_review": "systematic review[pt]",
    "meta_analysis": "meta-analysis[pt]",
    "rct": "randomized controlled trial[pt]",
    "clinical_trial": "clinical trial[pt]",
    "case_report": "case reports[pt]",
    "guideline": "guideline[pt]",
    "observational": "observational study[pt]",
    "editorial": "editorial[pt]",
    "letter": "letter[pt]",
    "comment": "comment[pt]",
}

# All types that can be excluded
EXCLUDABLE_TYPES = {
    "case_report": "NOT case reports[pt]",
    "editorial": "NOT editorial[pt]",
    "letter": "NOT letter[pt]",
    "comment": "NOT comment[pt]",
    "retracted": "NOT retracted publication[pt]",
    "review": "NOT review[pt]",
    "systematic_review": "NOT systematic review[pt]",
    "meta_analysis": "NOT meta-analysis[pt]",
    "rct": "NOT randomized controlled trial[pt]",
    "clinical_trial": "NOT clinical trial[pt]",
    "guideline": "NOT guideline[pt]",
    "observational": "NOT observational study[pt]",
}


class PubMedClient:
    """Client for PubMed/PMC APIs."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    def build_query(
        self,
        query: str,
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
        free_fulltext_only: bool = False,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> str:
        """Build PubMed query with filters.

        Args:
            query: Base search query
            include_types: Publication types to include (review, systematic_review, rct, etc.)
            exclude_types: Publication types to exclude (case_report, editorial, etc.)
            free_fulltext_only: Only include free full text articles
            year_from: Start year filter
            year_to: End year filter

        Returns:
            Formatted query string
        """
        parts = [query]

        # Add publication type includes (OR between them)
        if include_types:
            type_filters = [PUBLICATION_TYPES[t] for t in include_types if t in PUBLICATION_TYPES]
            if type_filters:
                parts.append(f"({' OR '.join(type_filters)})")

        # Add publication type excludes
        if exclude_types:
            for t in exclude_types:
                if t in EXCLUDABLE_TYPES:
                    parts.append(EXCLUDABLE_TYPES[t])

        # Free full text filter
        if free_fulltext_only:
            parts.append("free full text[filter]")

        # Year range
        if year_from or year_to:
            start = year_from or 1900
            end = year_to or 2099
            parts.append(f"{start}:{end}[dp]")

        return " AND ".join(parts)

    async def search(
        self,
        query: str,
        max_results: int = 50,
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
        free_fulltext_only: bool = False,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> Dict:
        """Search PubMed for articles.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            include_types: Publication types to include
            exclude_types: Publication types to exclude
            free_fulltext_only: Only free full text
            year_from: Start year
            year_to: End year

        Returns:
            Dictionary with search results
        """
        # Build query with filters
        full_query = self.build_query(
            query, include_types, exclude_types, free_fulltext_only, year_from, year_to
        )

        params = {
            "db": "pubmed",
            "term": full_query,
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
