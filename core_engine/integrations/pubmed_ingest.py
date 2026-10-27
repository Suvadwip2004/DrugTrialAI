from __future__ import annotations
import argparse
import asyncio
import logging
import uuid

from core_engine.integrations.pubmed_client import search_and_fetch
from core_engine.rag.chunking import chunk_document
from core_engine.rag.embeddings import embed_text
from core_engine.rag.vector_store import upsert_chunks

logger  = logging.getLogger(__name__)
UPSERT_BATCH_SIZE  = 32

def _chunk_id(pmid:str,chunk_index: int) -> str :
    return str(uuid.uuid5(uuid.NAMESPACE_URL,f"{pmid}:{chunk_index}"))

async def ingest_query(query:str,drug_names : list[str] | None = None,max_results : int  = 10,) -> dict :
    stats = {"articles": 0, "chunks": 0, "embedded": 0, "upserted": 0}
    articles  = await search_and_fetch(query,max_results = max_results)
    stats["articles"] = len(articles) 

    if not articles :
        logger.warning("No articles to ingest for query: '%s'", query)
        return stats
    all_chunks  : list[dict] = []
    for article in articles:
        full_text = f"{article['title']}. {article['abstract']}"
        chunks  = chunk_document(full_text,title=article["title"],source="pubmed",url=article["url"],drug_names=drug_names or [],)
        



# s = _chunk_id("dftd",4)
# print(s)
# print(type(s))