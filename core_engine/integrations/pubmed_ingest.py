from __future__ import annotations
import argparse
import asyncio
import logging
import uuid
import json

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
        for i ,chunk in enumerate(chunks) :
            chunk["id"] = _chunk_id(article["pmid"],i)
        all_chunks.extend(chunks)

    stats["chunks"] = len(all_chunks)
    logger.info("Chunked %d article(s) into %d chunk(s)", len(articles), len(all_chunks))

    for n, chunk in enumerate(all_chunks, start=1):
        chunk["embedding"] = await embed_text(chunk["text"])
        if chunk["embedding"]:
            stats["embedded"] += 1

        if n % 10 == 0:
            logger.info("Embedded %d/%d chunks", n, len(all_chunks))

    for start in range(0, len(all_chunks), UPSERT_BATCH_SIZE):
        batch = all_chunks[start : start + UPSERT_BATCH_SIZE]
        stats["upserted"] += await upsert_chunks(batch)

    logger.info("Ingestion complete for '%s': %s", query, stats)
    return stats


# async def _main() -> None:
#     parser = argparse.ArgumentParser(description="Ingest PubMed abstracts into Qdrant")
#     parser.add_argument("--query",required=True)
#     parser.add_argument("--drugs",nargs="*",default=[])
#     parser.add_argument("--max-results",type=int,default=10)
#     args = parser.parse_args()

#     stats = await ingest_query(args.query,drug_names=args.drugs,max_results=args.max_results)
#     print(f"\nDone: {stats}")
#     with open("pubmed_ingest.json","w") as f:
#         json.dump(stats,f)



# if __name__ == "__main__" :
#     logging.basicConfig(level=logging.INFO,filename="app.log")
#     asyncio.run(_main())