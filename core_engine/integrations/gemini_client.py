from __future__ import annotations
import json
import logging
import os
from typing import Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
_client: Any | None = None


def _get_client() -> Any:

    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "AI Connection Problem"
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

    client = _get_client()
    model_name = model or DEFAULT_MODEL

    response = await client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    if not response.text:
        logger.warning("AI returned an empty response for model '%s'", model_name)
        return ""

    return response.text


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def call_llm_json(prompt: str, model: str | None = None) -> dict | list | None:

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
        logger.warning("AI returned an empty JSON response for model '%s'", model_name)
        return None

    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI JSON response: %s\nRaw text: %s", e, response.text)
        return None


# if __name__ == "__main__":
#     import asyncio

#     logging.basicConfig(level=logging.INFO)

#     async def _main():
#         text = await call_llm("In one sentence, what is a drug-drug interaction?")
#         print("Plain text response:\n", text)

#         json_prompt = (
#             "Return a JSON object with two fields: 'drug' (string) and "
#             "'common_use' (string), for the drug Warfarin. "
#             "Return ONLY valid JSON, no markdown fences, no extra text."
#         )
#         result = await call_llm_json(json_prompt)
#         print("\nStructured JSON response:\n", result)
#         with open("gemini_clint.json","w") as f:
#             json.dump(result,f)

#     asyncio.run(_main())