from __future__ import annotations
import logging
import os
import uuid
from qdrant_client import AsyncQdrantClient,models
from dotenv import load_dotenv
load_dotenv()

logger  = logging.getLogger(__name__)
QDRANT_URL = os.get_env("QDRANT_URL","http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "clinical_documents")
VECTOR_SIZE = 768

_client : AsyncQdrantClient | None = None

def _get_client() -> AsyncQdrantClient :
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=QDRANT_URL)
    return _client


async def ensure_collection() -> None:
    client  = _get_client()
    exists  = client.collection_exists(COLLECTION_NAME)
    if exists :
        logger.info("Collection '%s' already exists", COLLECTION_NAME)
        return


    await client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
    )
    logger.info("Created collection '%s' (size=%d, distance=COSINE)", COLLECTION_NAME, VECTOR_SIZE)
 
async def upsert_chunks(chunks: list[dict]) -> int:
    client = _get_client()
    await ensure_collection()
    points = []
    for chunk in chunks:
        embedding = chunk.get("embedding")
        if not embedding:
            logger.warning("Skipping chunk with no embedding: %s", chunk.get("title", "untitled"))
            continue
        points.append(
            models.PointStruct(
                id = str(uuid.uuid4()),
                vector= embedding,
                payload={
                    "text": chunk.get("text", ""),
                    "source": chunk.get("source", "unknown"),
                    "title": chunk.get("title", ""),
                    "url": chunk.get("url", ""),
                    "drug_names": chunk.get("drug_names", []),
                },
            )
        )
    if not points:
        logger.warning("No valid chunks to upsert (all missing embeddings)")
        return 0

    await client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info("Upserted %d chunk(s) into '%s'", len(points), COLLECTION_NAME)

    return len(points)

async def search_similar(query_embedding: list[float],limit: int = 5,source_filter: str | None = None,) -> list[dict]:
    client = _get_client()
    query_filter = None
    if source_filter:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="source", match=models.MatchValue(value=source_filter))]
        )
