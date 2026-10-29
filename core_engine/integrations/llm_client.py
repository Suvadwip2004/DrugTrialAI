from __future__ import annotations

import json
import logging
import os

from ollama import AsyncClient

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

_client: AsyncClient | None = None


def _get_client() -> AsyncClient:
    """Lazily create a single shared Ollama async client."""
    global _client
    if _client is None:
        _client = AsyncClient(host=OLLAMA_HOST)
    return _client


async def call_llm(prompt: str, model: str | None = None) -> str:
    """
    Send a prompt to the local Ollama model and return the plain text response.

    No retry/backoff needed here — local inference has no rate limits, only
    the possibility of Ollama not running or the model not being pulled,
    which are configuration errors, not transient failures.
    """
    client = _get_client()
    model_name = model or DEFAULT_MODEL

    try:
        response = await client.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.error(
            "Ollama call failed (model='%s'). Is Ollama running and is the model "
            "pulled? Try: ollama pull %s -- Error: %s",
            model_name, model_name, e,
        )
        raise

    content = response.message.content
    if not content:
        logger.warning("Ollama returned an empty response for model '%s'", model_name)
        return ""

    return content


async def call_llm_json(prompt: str, model: str | None = None) -> dict | list | None:
    """
    Send a prompt to the local Ollama model and force a structured JSON response.

    Uses Ollama's format='json' mode, which constrains the model to emit
    valid JSON. Smaller local models (like phi3) are less reliable at strict
    JSON formatting than Gemini/GPT-class models, so a bad model choice here
    is the most likely cause of parse failures -- consider a larger model
    (e.g. llama3.1, mistral) if you see frequent JSON parse errors.
    """
    client = _get_client()
    model_name = model or DEFAULT_MODEL

    try:
        response = await client.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
    except Exception as e:
        logger.error(
            "Ollama JSON call failed (model='%s'). Is Ollama running and is the "
            "model pulled? Try: ollama pull %s -- Error: %s",
            model_name, model_name, e,
        )
        return None

    content = response.message.content
    if not content:
        logger.warning("Ollama returned an empty JSON response for model '%s'", model_name)
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Ollama JSON response: %s\nRaw text: %s", e, content)
        return None


# ---- standalone test ----
# Run directly with: uv run python -m core_engine.integrations.llm_client
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def _main():
        text = await call_llm("In one sentence, what is a drug-drug interaction?")
        print("Plain text response:\n", text)

        json_prompt = (
            "Return a JSON object with two fields: 'drug' (string) and "
            "'common_use' (string), for the drug Warfarin. "
            "Return ONLY valid JSON, no markdown fences, no extra text."
        )
        result = await call_llm_json(json_prompt)
        print("\nStructured JSON response:\n", result)

    asyncio.run(_main())