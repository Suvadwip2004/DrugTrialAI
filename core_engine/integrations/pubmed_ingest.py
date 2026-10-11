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
    