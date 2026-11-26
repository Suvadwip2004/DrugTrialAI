"""
RAG Agent.

Answers a question using ONLY literature retrieved from the vector store:

    question -> retrieve chunks -> numbered context -> LLM answers + cites [n]

Grounding rules enforced here:
  1. No retrieved chunks  -> no LLM call, no answer (nothing to ground on).
  2. The prompt tells the model to use only the provided sources and to say
     so when they are insufficient.
  3. Citations in the answer are checked against the real source list, so a
     made-up "[9]" is caught instead of trusted.
"""

from __future__ import annotations

import logging
import re

from core_engine.integrations.llm_client import call_llm
from core_engine.rag.retriever import format_context, retrieve

logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """You are a clinical literature assistant. Answer the question using ONLY the numbered sources below. Do not use any outside knowledge.

Rules:
- Cite the sources that support each statement like [1] or [2].
- If the sources do not contain enough information to answer, reply exactly: "The retrieved literature does not contain enough information to answer this."
- Do not invent studies, numbers, or recommendations that are not in the sources.
- Keep the answer to 3-5 sentences.

Sources:
{context}

Question: {question}

Answer:"""

INSUFFICIENT_MARKER = "does not contain enough information"


def _extract_citations(answer: str, num_sources: int) -> tuple[list[int], list[int]]:
    """
    Find [n] citations in the answer.
    Returns (valid_citations, invalid_citations) where invalid means the
    number doesn't correspond to any retrieved source.
    """
    found = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    valid = sorted(n for n in found if 1 <= n <= num_sources)
    invalid = sorted(n for n in found if n < 1 or n > num_sources)
    return valid, invalid


async def answer_question(
    question: str,
    drug_names: list[str] | None = None,
    limit: int = 5,
    min_score: float = 0.0,
    source_filter: str | None = "pubmed",
) -> dict:
    """
    Answer `question` from retrieved literature.

    Returns:
        {
            "question": str,
            "answer": str,
            "grounded": bool,          # True only if answered from sources with valid citations
            "cited_sources": [ {title, url, score}, ... ],
            "all_sources": [ {title, url, score}, ... ],   # everything retrieved
            "invalid_citations": [int],
        }
    """
    chunks = await retrieve(
        question,
        limit=limit,
        source_filter=source_filter,
        min_score=min_score,
        drug_names=drug_names,
    )

    result = {
        "question": question,
        "answer": "",
        "grounded": False,
        "cited_sources": [],
        "all_sources": [{"title": c["title"], "url": c["url"], "score": c["score"]} for c in chunks],
        "invalid_citations": [],
    }

    if not chunks:
        result["answer"] = "No relevant literature was found in the knowledge base."
        return result

    prompt = RAG_PROMPT_TEMPLATE.format(context=format_context(chunks), question=question)

    try:
        answer = (await call_llm(prompt)).strip()
    except Exception as e:
        logger.error("RAG answer generation failed: %s", e)
        result["answer"] = "Answer generation failed."
        return result

    result["answer"] = answer

    if INSUFFICIENT_MARKER in answer.lower():
        # The model correctly refused -- honest, but not a grounded answer.
        return result

    valid, invalid = _extract_citations(answer, len(chunks))
    result["invalid_citations"] = invalid
    result["cited_sources"] = [
        {"title": chunks[n - 1]["title"], "url": chunks[n - 1]["url"], "score": chunks[n - 1]["score"]}
        for n in valid
    ]

    # Grounded = at least one valid citation and no fabricated ones.
    result["grounded"] = bool(valid) and not invalid
    if not result["grounded"]:
        logger.warning(
            "Answer not grounded (valid citations=%s, invalid=%s). Treat with caution.",
            valid, invalid,
        )

    return result


async def check_interaction_literature(drug_a: str, drug_b: str, limit: int = 5) -> dict:
    """
    Literature fallback for the interaction agent: ask what the literature
    says about the interaction between two drugs.
    """
    question = (
        f"What is known about the interaction between {drug_a} and {drug_b}, "
        f"including mechanism and clinical significance?"
    )
    return await answer_question(question, drug_names=[drug_a, drug_b], limit=limit)


# ---- standalone test ----
# Run directly with: uv run python -m core_engine.agents.rag_agent
if __name__ == "__main__":
    import asyncio
    import json

    logging.basicConfig(level=logging.INFO)

    async def _main():
        result = await check_interaction_literature("Warfarin", "Amoxicillin")
        print(json.dumps(result, indent=2))

    asyncio.run(_main())