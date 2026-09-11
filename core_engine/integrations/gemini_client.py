from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default API configuration
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "text-embedding-004")
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_MAX_BACKOFF = 60.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GeminiError(Exception):
    """Base exception for Gemini API errors."""


class GeminiAuthError(GeminiError):
    """Raised when the Gemini API key is missing or invalid."""


class GeminiRateLimitError(GeminiError):
    """Raised when rate limits (HTTP 429) are exhausted after all retries."""


class GeminiAPIError(GeminiError):
    """Raised when the Gemini API returns an unhandled or server error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class GeminiUsage:
    """Token usage metadata returned by Gemini."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class GeminiResponse:
    """Structured response object containing text, metadata, and token stats."""

    text: str
    model: str
    finish_reason: str | None = None
    usage: GeminiUsage = field(default_factory=GeminiUsage)
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_api_key(explicit_key: str | None = None) -> str | None:
    """Resolve API key from parameter or environment variables."""
    return (
        explicit_key
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )


def _clean_model_name(model: str) -> str:
    """Ensure model name does not carry redundant 'models/' prefix."""
    return model.removeprefix("models/")


def _clean_json_text(text: str) -> str:
    """Strip markdown code fence wrappers from model JSON output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        match = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```$", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
    return cleaned


# ---------------------------------------------------------------------------
# Main Client
# ---------------------------------------------------------------------------

class GeminiClient:
    """Asynchronous HTTP client for Google's Gemini API with built-in

    rate-limit retries and exponential backoff designed for free-tier quotas.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
        default_embed_model: str = DEFAULT_EMBED_MODEL,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = _resolve_api_key(api_key)
        self.default_model = default_model
        self.default_embed_model = default_embed_model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff

        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(timeout=self.timeout)

    async def __aenter__(self) -> GeminiClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client if created internally."""
        if not self._external_client and not self._client.is_closed:
            await self._client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Prepare authentication and request headers."""
        if not self.api_key:
            raise GeminiAuthError(
                "Gemini API key is not configured. Set GEMINI_API_KEY environment variable "
                "or pass api_key to GeminiClient."
            )
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    async def _post_with_retry(
        self,
        endpoint: str,
        payload: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a POST request with exponential backoff on HTTP 429 and transient 5xx errors."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        for attempt in range(self.max_retries + 1):
            try:
                resp = await self._client.post(
                    url,
                    json=payload,
                    params=params,
                    headers=headers,
                )

                if resp.status_code == 429:
                    if attempt >= self.max_retries:
                        logger.error(
                            "Gemini rate limit (429) exceeded after %d retries.",
                            self.max_retries,
                        )
                        raise GeminiRateLimitError(
                            f"Gemini API rate limit exceeded after {self.max_retries} retries: {resp.text}"
                        )

                    # Determine sleep duration from Retry-After header or exponential backoff
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        try:
                            sleep_seconds = float(retry_after)
                        except ValueError:
                            sleep_seconds = min(
                                self.max_backoff,
                                (self.backoff_factor ** attempt) + random.uniform(0.5, 1.5),
                            )
                    else:
                        sleep_seconds = min(
                            self.max_backoff,
                            (self.backoff_factor ** attempt) + random.uniform(0.5, 1.5),
                        )

                    logger.warning(
                        "Gemini rate limit (429) hit. Backing off for %.2fs (attempt %d/%d)...",
                        sleep_seconds,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(sleep_seconds)
                    continue

                if resp.status_code in (500, 502, 503, 504):
                    if attempt >= self.max_retries:
                        resp.raise_for_status()

                    sleep_seconds = min(
                        self.max_backoff,
                        (self.backoff_factor ** attempt) + random.uniform(0.5, 1.5),
                    )
                    logger.warning(
                        "Gemini transient server error (%d). Retrying in %.2fs (attempt %d/%d)...",
                        resp.status_code,
                        sleep_seconds,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(sleep_seconds)
                    continue

                if resp.status_code in (401, 403):
                    logger.error("Gemini authentication failed (%d): %s", resp.status_code, resp.text)
                    raise GeminiAuthError(
                        f"Gemini authentication failed ({resp.status_code}): {resp.text}"
                    )

                resp.raise_for_status()
                return resp.json()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt >= self.max_retries:
                    logger.error("Gemini network error after %d retries: %s", self.max_retries, e)
                    raise GeminiAPIError(f"Network error communicating with Gemini API: {e}") from e

                sleep_seconds = min(
                    self.max_backoff,
                    (self.backoff_factor ** attempt) + random.uniform(0.5, 1.5),
                )
                logger.warning(
                    "Gemini network issue (%s). Retrying in %.2fs (attempt %d/%d)...",
                    type(e).__name__,
                    sleep_seconds,
                    attempt + 1,
                    self.max_retries,
                )
                await asyncio.sleep(sleep_seconds)

            except httpx.HTTPStatusError as e:
                logger.error(
                    "Gemini API request failed with status %d: %s",
                    e.response.status_code,
                    e.response.text,
                )
                raise GeminiAPIError(
                    f"Gemini API returned status {e.response.status_code}: {e.response.text}",
                    status_code=e.response.status_code,
                    response_data=e.response.text,
                ) from e

        raise GeminiAPIError("Exceeded max retries without a successful response.")

    async def generate_content(
        self,
        prompt: str | list[dict[str, Any]],
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        max_output_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
        response_mime_type: str | None = None,
        response_schema: dict[str, Any] | None = None,
        safety_settings: list[dict[str, Any]] | None = None,
    ) -> GeminiResponse:
        """Generate content from Gemini using the specified prompt and parameters."""
        target_model = _clean_model_name(model or self.default_model)
        endpoint = f"models/{target_model}:generateContent"

        # Build contents payload
        if isinstance(prompt, str):
            contents = [{"role": "user", "parts": [{"text": prompt}]}]
        else:
            contents = prompt

        payload: dict[str, Any] = {"contents": contents}

        # System instruction
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # Generation config
        gen_config: dict[str, Any] = {}
        if temperature is not None:
            gen_config["temperature"] = temperature
        if top_p is not None:
            gen_config["topP"] = top_p
        if top_k is not None:
            gen_config["topK"] = top_k
        if max_output_tokens is not None:
            gen_config["maxOutputTokens"] = max_output_tokens
        if stop_sequences is not None:
            gen_config["stopSequences"] = stop_sequences
        if response_mime_type is not None:
            gen_config["responseMimeType"] = response_mime_type
        if response_schema is not None:
            gen_config["responseSchema"] = response_schema

        if gen_config:
            payload["generationConfig"] = gen_config

        if safety_settings:
            payload["safetySettings"] = safety_settings

        data = await self._post_with_retry(endpoint, payload)

        candidates = data.get("candidates", [])
        text = ""
        finish_reason = None
        if candidates:
            first_candidate = candidates[0]
            finish_reason = first_candidate.get("finishReason")
            parts = first_candidate.get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts if "text" in part)

        usage_data = data.get("usageMetadata", {})
        usage = GeminiUsage(
            prompt_tokens=usage_data.get("promptTokenCount", 0),
            completion_tokens=usage_data.get("candidatesTokenCount", 0),
            total_tokens=usage_data.get("totalTokenCount", 0),
        )

        return GeminiResponse(
            text=text,
            model=target_model,
            finish_reason=finish_reason,
            usage=usage,
            raw=data,
        )

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        raise_on_error: bool = False,
    ) -> str | None:
        """Convenience method to generate plain text.

        Returns string output, or None on failure if raise_on_error is False.
        """
        try:
            res = await self.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            return res.text
        except Exception as e:
            logger.error("Gemini text generation failed: %s", e)
            if raise_on_error:
                raise
            return None

    async def generate_json(
        self,
        prompt: str,
        system_instruction: str | None = None,
        response_schema: dict[str, Any] | None = None,
        model: str | None = None,
        temperature: float | None = 0.0,
        max_output_tokens: int | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, Any] | list[Any] | None:
        """Generate structured output parsed as a JSON dict or list."""
        try:
            res = await self.generate_content(
                prompt=prompt,
                system_instruction=system_instruction,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
                response_schema=response_schema,
            )
            cleaned_text = _clean_json_text(res.text)
            if not cleaned_text:
                return None
            return json.loads(cleaned_text)
        except Exception as e:
            logger.error("Gemini JSON generation/parsing failed: %s", e)
            if raise_on_error:
                raise
            return None

    async def embed_content(
        self,
        text: str,
        model: str | None = None,
        task_type: str | None = None,
        title: str | None = None,
        output_dimensionality: int | None = None,
        raise_on_error: bool = False,
    ) -> list[float] | None:
        """Generate vector embedding for a single text chunk."""
        target_model = _clean_model_name(model or self.default_embed_model)
        endpoint = f"models/{target_model}:embedContent"

        payload: dict[str, Any] = {
            "model": f"models/{target_model}",
            "content": {
                "parts": [{"text": text}]
            },
        }
        if task_type:
            payload["taskType"] = task_type
        if title:
            payload["title"] = title
        if output_dimensionality:
            payload["outputDimensionality"] = output_dimensionality

        try:
            data = await self._post_with_retry(endpoint, payload)
            embedding = data.get("embedding", {}).get("values")
            return embedding
        except Exception as e:
            logger.error("Gemini embedding failed for text: %s", e)
            if raise_on_error:
                raise
            return None

    async def batch_embed_contents(
        self,
        texts: list[str],
        model: str | None = None,
        task_type: str | None = None,
        batch_size: int = 100,
        raise_on_error: bool = False,
    ) -> list[list[float]]:
        """Generate vector embeddings for a list of texts in batches (up to 100 per batch)."""
        if not texts:
            return []

        target_model = _clean_model_name(model or self.default_embed_model)
        endpoint = f"models/{target_model}:batchEmbedContents"
        results: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            requests = []
            for item in chunk:
                req: dict[str, Any] = {
                    "model": f"models/{target_model}",
                    "content": {"parts": [{"text": item}]},
                }
                if task_type:
                    req["taskType"] = task_type
                requests.append(req)

            payload = {"requests": requests}

            try:
                data = await self._post_with_retry(endpoint, payload)
                embeddings = data.get("embeddings", [])
                for emb in embeddings:
                    results.append(emb.get("values", []))
            except Exception as e:
                logger.error("Gemini batch embedding failed for chunk [%d:%d]: %s", i, i + len(chunk), e)
                if raise_on_error:
                    raise
                # Pad with empty lists on failure to maintain 1:1 index mapping
                results.extend([] for _ in chunk)

        return results

    async def count_tokens(
        self,
        text: str,
        model: str | None = None,
        raise_on_error: bool = False,
    ) -> int | None:
        """Count tokens for the given text to support context window and rate budgeting."""
        target_model = _clean_model_name(model or self.default_model)
        endpoint = f"models/{target_model}:countTokens"

        payload = {
            "contents": [{"parts": [{"text": text}]}]
        }

        try:
            data = await self._post_with_retry(endpoint, payload)
            return data.get("totalTokens")
        except Exception as e:
            logger.error("Gemini count_tokens failed: %s", e)
            if raise_on_error:
                raise
            return None


# ---------------------------------------------------------------------------
# Standalone Module Functions (Matching openfda_client and rxnav_client style)
# ---------------------------------------------------------------------------

async def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    api_key: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> str | None:
    """Generate text using Gemini.

    Returns generated string, or None on error.
    """
    async with GeminiClient(api_key=api_key, timeout=timeout) as client:
        return await client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            model=model,
            temperature=temperature,
            **kwargs,
        )


async def generate_json(
    prompt: str,
    system_instruction: str | None = None,
    response_schema: dict[str, Any] | None = None,
    model: str | None = None,
    temperature: float | None = 0.0,
    api_key: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> dict[str, Any] | list[Any] | None:
    """Generate structured JSON using Gemini.

    Returns parsed dict/list, or None on error.
    """
    async with GeminiClient(api_key=api_key, timeout=timeout) as client:
        return await client.generate_json(
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema=response_schema,
            model=model,
            temperature=temperature,
            **kwargs,
        )


async def embed_text(
    text: str,
    model: str | None = None,
    task_type: str | None = None,
    api_key: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> list[float] | None:
    """Compute embedding vector for a single text string."""
    async with GeminiClient(api_key=api_key, timeout=timeout) as client:
        return await client.embed_content(
            text=text,
            model=model,
            task_type=task_type,
            **kwargs,
        )


async def embed_texts(
    texts: list[str],
    model: str | None = None,
    task_type: str | None = None,
    api_key: str | None = None,
    batch_size: int = 100,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> list[list[float]]:
    """Compute embedding vectors for a list of text strings in batches."""
    async with GeminiClient(api_key=api_key, timeout=timeout) as client:
        return await client.batch_embed_contents(
            texts=texts,
            model=model,
            task_type=task_type,
            batch_size=batch_size,
            **kwargs,
        )


async def count_tokens(
    text: str,
    model: str | None = None,
    api_key: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> int | None:
    """Count tokens for text."""
    async with GeminiClient(api_key=api_key, timeout=timeout) as client:
        return await client.count_tokens(
            text=text,
            model=model,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# CLI / Quick Test Example
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def _main() -> None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("[INFO] No GEMINI_API_KEY or GOOGLE_API_KEY detected in environment.")
            print("[INFO] Client is ready for use once an API key is provided.")
            return

        print("[INFO] Testing Gemini client connection...")
        async with GeminiClient() as client:
            # 1. Simple generation
            res = await client.generate_content("In one sentence, explain what a clinical trial is.")
            print(f"\nResponse ({res.model}):\n{res.text}")
            print(f"Token usage: {res.usage}")

            # 2. JSON generation
            json_res = await client.generate_json(
                "Return a JSON object with 'drug_name': 'Warfarin' and 'target': 'VKORC1'"
            )
            print(f"\nJSON Output:\n{json_res}")

    asyncio.run(_main())
