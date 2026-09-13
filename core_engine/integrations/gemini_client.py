from __future__ import annotations

import json
import logging
import os

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """
    Lazily create a single shared Gemini client.
    Reads the API key from the GEMINI_API_KEY env var automatically
    (set it in your .env / config.py loads it into the environment).
    """
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and add it to your .env"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _is_rate_limit_error(exception: BaseException) -> bool:
    """Only retry on rate-limit (429) errors — fail fast on everything else."""
    return "429" in str(exception) or "RESOURCE_EXHAUSTED" in str(exception)


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def call_llm(prompt: str, model: str | None = None) -> str:
    """
    Send a prompt to Gemini and return the plain text response.
    Retries with exponential backoff on free-tier rate-limit (429) errors.
    """
    client = _get_client()
    model_name = model or DEFAULT_MODEL

    response = await client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    if not response.text:
        logger.warning("Gemini returned an empty response for model '%s'", model_name)
        return ""

    return response.text


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def call_llm_json(prompt: str, model: str | None = None) -> dict | list | None:
    """
    Send a prompt to Gemini and force a structured JSON response.

    Use this for extraction tasks (e.g. turning FDA label prose into
    {drug_a, drug_b, severity, mechanism, description} dicts) instead of
    parsing free text yourself.

    Returns the parsed JSON (dict or list), or None if parsing fails.
    """
    client = _get_client()
    model_name = model or DEFAULT_MODEL

    response = await client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    if not response.text:
        logger.warning("Gemini returned an empty JSON response for model '%s'", model_name)
        return None

    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini JSON response: %s\nRaw text: %s", e, response.text)
        return None


# ---- standalone test ----
# Run directly with: uv run python gemini_client.py
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def _main():
        # Plain text test
        text = await call_llm("In one sentence, what is a drug-drug interaction?")
        print("Plain text response:\n", text)

        # Structured JSON test
        json_prompt = (
            "Return a JSON object with two fields: 'drug' (string) and "
            "'common_use' (string), for the drug Warfarin. "
            "Return ONLY valid JSON, no markdown fences, no extra text."
        )
        result = await call_llm_json(json_prompt)
        print("\nStructured JSON response:\n", result)

    asyncio.run(_main())