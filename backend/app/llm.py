"""The only place that talks to Gemini.

Everything else calls `LLM.generate`, `LLM.embed_documents` and `LLM.embed_query`,
so swapping providers later only touches this file.
"""

import math
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

T = TypeVar("T")

DEFAULT_CHAT_MODEL = "gemini-flash-latest"
DEFAULT_FALLBACK_MODEL = "gemini-flash-lite-latest"
DEFAULT_EMBED_MODEL = "gemini-embedding-001"
DEFAULT_EMBED_DIM = 768  # small enough for a pgvector HNSW index
EMBED_BATCH_SIZE = 100  # Gemini's per-request limit


class LLMError(RuntimeError):
    pass


def _is_retryable(error: errors.APIError) -> bool:
    """Rate limits and server overloads are temporary; bad requests are not."""
    return isinstance(error, errors.ServerError) or error.code == 429


class LLM:
    def __init__(
        self,
        client: Any,
        chat_model: str = DEFAULT_CHAT_MODEL,
        fallback_model: str | None = DEFAULT_FALLBACK_MODEL,
        embed_model: str = DEFAULT_EMBED_MODEL,
        embed_dim: int = DEFAULT_EMBED_DIM,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.client = client
        self.chat_model = chat_model
        self.fallback_model = fallback_model
        self.embed_model = embed_model
        self.embed_dim = embed_dim
        self.embed_batch_size = EMBED_BATCH_SIZE
        self.max_retries = max_retries
        self._sleep = sleep

    @classmethod
    def from_env(cls) -> "LLM":
        load_dotenv(".env")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LLMError("GEMINI_API_KEY is not set")
        return cls(
            client=genai.Client(api_key=api_key),
            chat_model=os.environ.get("GEMINI_CHAT_MODEL", DEFAULT_CHAT_MODEL),
            fallback_model=os.environ.get("GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL) or None,
            embed_model=os.environ.get("GEMINI_EMBED_MODEL", DEFAULT_EMBED_MODEL),
        )

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        json_output: bool = False,
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json" if json_output else None,
        )
        models = [self.chat_model] + ([self.fallback_model] if self.fallback_model else [])

        last_error: errors.APIError | None = None
        for model in models:
            try:
                response = self._with_retry(
                    lambda: self.client.models.generate_content(model=model, contents=prompt, config=config)
                )
                return response.text or ""
            except errors.APIError as e:
                if not _is_retryable(e):
                    raise LLMError(f"Gemini rejected the request: {e}") from e
                last_error = e
        raise LLMError(f"Gemini is unavailable, try again shortly: {last_error}") from last_error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.embed_batch_size):
            vectors.extend(self._embed(texts[start : start + self.embed_batch_size], "RETRIEVAL_DOCUMENT"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.embed_dim)
        try:
            response = self._with_retry(
                lambda: self.client.models.embed_content(model=self.embed_model, contents=texts, config=config)
            )
        except errors.APIError as e:
            raise LLMError(f"Embedding failed: {e}") from e
        return [_unit_length(e.values) for e in response.embeddings]

    def _with_retry(self, call: Callable[[], T]) -> T:
        for attempt in range(self.max_retries):
            try:
                return call()
            except errors.APIError as e:
                if not _is_retryable(e) or attempt == self.max_retries - 1:
                    raise
                self._sleep(2**attempt)
        raise AssertionError("unreachable")


def _unit_length(vector: list[float]) -> list[float]:
    """Gemini only pre-normalizes full-size embeddings; reduced ones need it for cosine search."""
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else list(vector)
