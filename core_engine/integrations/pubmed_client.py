from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT = 20.0
NCBI_API_KEY = os.getenv("NCBI_API_KEY")
TOOL_NAME = "DrugTrialAI"
TOOL_EMAIL = os.getenv("NCBI_EMAIL", "")  


def _base_params() -> dict:
    params = {"tool": TOOL_NAME}
    if TOOL_EMAIL:
        params["email"] = TOOL_EMAIL
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


async def search_pubmed(query: str, max_results: int = 10) -> list[str]:
    """
    Search PubMed and return a list of matching PMIDs (as strings).
    Returns [] on no results or API failure.

    Example query: "warfarin amoxicillin interaction"
    """
    params = {
        **_base_params(),
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(f"{BASE_URL}/esearch.fcgi", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("PubMed search failed (%s): %s", e.response.status_code, e.response.text[:300])
            return []
        except httpx.HTTPError as e:
            logger.error("PubMed search request error: %s", e)
            return []

    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def _element_text(element: ET.Element | None) -> str:
    """Get all text inside an XML element, including text inside nested tags like <i> or <sub>."""
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _parse_article(article: ET.Element) -> dict | None:
    """Parse one <PubmedArticle> XML element into a clean dict. Returns None if unusable."""
    pmid = _element_text(article.find(".//MedlineCitation/PMID"))
    title = _element_text(article.find(".//Article/ArticleTitle"))


    abstract_parts = []
    for node in article.findall(".//Article/Abstract/AbstractText"):
        text = _element_text(node)
        if not text:
            continue
        label = node.get("Label")
        abstract_parts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abstract_parts)

    if not pmid or not abstract:
        return None

    journal = _element_text(article.find(".//Article/Journal/Title"))
    year = _element_text(article.find(".//Article/Journal/JournalIssue/PubDate/Year"))

    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "year": year,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    }


async def fetch_abstracts(pmids: list[str]) -> list[dict]:
    """
    Fetch full records for a list of PMIDs.

    Returns a list of dicts: {pmid, title, abstract, journal, year, url}.
    Articles without an abstract are skipped (nothing to embed).
    """
    if not pmids:
        return []

    params = {
        **_base_params(),
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(f"{BASE_URL}/efetch.fcgi", params=params)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("PubMed fetch failed (%s): %s", e.response.status_code, e.response.text[:300])
            return []
        except httpx.HTTPError as e:
            logger.error("PubMed fetch request error: %s", e)
            return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        logger.error("Could not parse PubMed XML response: %s", e)
        return []

    results = []
    for article in root.findall(".//PubmedArticle"):
        parsed = _parse_article(article)
        if parsed:
            results.append(parsed)

    skipped = len(pmids) - len(results)
    if skipped:
        logger.info("Skipped %d article(s) with no abstract", skipped)

    return results


async def search_and_fetch(query: str, max_results: int = 10) -> list[dict]:
    """Convenience wrapper: search, then fetch the matching abstracts."""
    pmids = await search_pubmed(query, max_results)
    if not pmids:
        logger.info("No PubMed results for query: '%s'", query)
        return []
    return await fetch_abstracts(pmids)



# if __name__ == "__main__":
#     import asyncio
#     import json

#     logging.basicConfig(level=logging.INFO)

#     async def _main():
#         articles = await search_and_fetch("warfarin amoxicillin interaction", max_results=3)
#         with open("pubmed_clientresponse.json","w") as f:
#             json.dump(articles,f)
#         print(f"Fetched {len(articles)} article(s)\n")
#         for a in articles:
#             print(f"[{a['pmid']}] {a['title']} ({a['journal']}, {a['year']})")
#             print(f"  {a['url']}")
#             print(f"  {a['abstract'][:200]}...\n")
#             print(articles)
#             print(type(articles))

#     asyncio.run(_main())