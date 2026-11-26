"""
Central Configuration for DrugTrialAI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Ollama settings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    OLLAMA_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

    # Qdrant Vector DB settings
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "clinical_documents")
    VECTOR_SIZE: int = 768

    # NCBI E-Utilities settings
    NCBI_API_KEY: str | None = os.getenv("NCBI_API_KEY")
    NCBI_EMAIL: str = os.getenv("NCBI_EMAIL", "")

    # External APIs
    RXNAV_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    OPENFDA_BASE_URL: str = "https://api.fda.gov/drug/label.json"
    CLINICALTRIALS_BASE_URL: str = "https://clinicaltrials.gov/api/v2/studies"
    DAILYMED_BASE_URL: str = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

    # API Gateway settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
