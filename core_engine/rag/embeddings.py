from __future__ import annotations

import logging
import os

from ollama import AsyncClient

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_DIM = 768  # nomic-embed-text's output dimension

_client: AsyncClient | None = None


def _get_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = AsyncClient(host=OLLAMA_HOST)
    return _client


def _check_dim(embedding: list[float]) -> None:
    """Warn if the vector size doesn't match what the vector store expects."""
    if len(embedding) != EMBEDDING_DIM:
        logger.warning(
            "Embedding dimension mismatch: got %d, expected %d (model='%s')",
            len(embedding),
            EMBEDDING_DIM,
            EMBEDDING_MODEL,
        )


async def embed_text(text: str) -> list[float] | None:
    client = _get_client()

    try:
        response = await client.embed(model=EMBEDDING_MODEL, input=text)
    except Exception as e:
        logger.error(
            "Embedding failed (model='%s'). Is Ollama running and is the model "
            "pulled? Try: ollama pull %s -- Error: %s",
            EMBEDDING_MODEL,
            EMBEDDING_MODEL,
            e,
        )
        return None
 
    if not response.embeddings or not response.embeddings[0]:
        logger.warning(
            "Ollama returned an empty embedding for model '%s'", EMBEDDING_MODEL
        )
        return None
 
    embedding = list(response.embeddings[0])
    _check_dim(embedding)
    return embedding
 



async def embed_texts(texts: list[str]) -> list[list[float] | None]:
    if not texts:
        return []
 
    client = _get_client()
 
    try:
        response = await client.embed(model=EMBEDDING_MODEL, input=texts)
        embeddings = [list(e) for e in response.embeddings]
 
        if len(embeddings) == len(texts) and all(embeddings):
            _check_dim(embeddings[0])
            return embeddings
 
        logger.warning(
            "Batch returned %d embeddings for %d texts (or some were empty). "
            "Falling back to per-item embedding.",
            len(embeddings),
            len(texts),
        )
    except Exception as e:
        logger.warning(
            "Batch embedding failed (model='%s'): %s. "
            "Falling back to per-item embedding.",
            EMBEDDING_MODEL,
            e,
        )
 
    # Fallback: sequential, so failures are isolated per text.
    results: list[list[float] | None] = []
    for text in texts:
        results.append(await embed_text(text))
    return results
 



# # ---- standalone test ----
# if __name__ == "__main__":
#     import asyncio
#     import json

#     logging.basicConfig(level=logging.INFO)

#     async def _main():
#         texts = [
#                 "What is diabetes?",
#                 "What is hypertension?",
#                 "What is insulin?",
#                 ]

#         vector = await embed_texts(texts)
#         if vector:
#             with open("embedding_response.json","w") as file:
#                 json.dump(vector, file, indent = 4)
#             print(f"Embedding length: {len(vector)}")
#             print(f"First 5 values: {vector[:5]}")
#         else:
#             print("Embedding failed — check Ollama is running and nomic-embed-text is pulled.")

#     asyncio.run(_main())