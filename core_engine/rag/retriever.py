from __future__ import annotations

import logging

from core_engine.rag.embeddings import embed_text
from core_engine.rag.vector_store import ensure_collection, search_similar

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 5


async def retrieve(
    query: str,
    limit: int = DEFAULT_LIMIT,
    source_filter: str | None = None,
    min_score: float = 0.0,
    drug_names: list[str] | None = None,
) -> list[dict]:
    if not query or not query.strip():
        logger.warning("retrieve() called with an empty query")
        return []

    search_text = query.strip()
    if drug_names:
        search_text = f"{search_text} ({', '.join(drug_names)})"

    query_embedding = await embed_text(search_text)
    if not query_embedding:
        logger.error("Could not embed query, cannot retrieve: '%s'", query)
        return []

    await ensure_collection()

    results = await search_similar(
        query_embedding,
        limit=limit,
        source_filter=source_filter,
    )

    if not results and source_filter:
        logger.warning(
            "No results for source_filter='%s'. The stored 'source' label may "
            "differ (it is an exact, case-sensitive match), or nothing with "
            "that source has been ingested yet.",
            source_filter,
        )

    filtered = [r for r in results if r["score"] >= min_score]
    dropped = len(results) - len(filtered)
    if dropped:
        logger.info("Dropped %d result(s) below min_score=%.2f", dropped, min_score)

    return filtered


def format_context(chunks: list[dict]) -> str:
    if not chunks:
        return ""

    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        header = f"[{i}] {chunk['title']} ({chunk['url']})"
        blocks.append(f"{header}\n{chunk['text']}")
    return "\n\n".join(blocks)


# if __name__ == "__main__":
#     import asyncio

#     logging.basicConfig(level=logging.INFO)

#     async def _main():
#         question = "Does amoxicillin increase bleeding risk in patients taking warfarin?"

#         chunks = await retrieve(question, limit=3, source_filter="text" or None)
#         if not chunks:
#             print("No results with source_filter='pubmed'. Retrying without a filter...\n")
#             chunks = await retrieve(question, limit=3)

#         print(f"Retrieved {len(chunks)} chunk(s)\n")
#         for c in chunks:
#             print(f"[{c['score']:.3f}] ({c['source']}) {c['title']}")
#             print(f"  {c['url']}")
#             print(f"  {c['text'][:150]}...\n")

#         print("=== Formatted context for an LLM prompt ===")
#         print(format_context(chunks))

#     asyncio.run(_main())