"""
EmbeddingProvider — a clean abstraction over "text -> vector", so the
rest of the RAG layer never needs to know which embedding backend is
configured.

Two implementations ship here:
  - OpenAICompatibleEmbeddingProvider: any hosted provider exposing an
    OpenAI-style POST {base_url}/embeddings endpoint. Configured purely
    via env vars (app/config.py) — no keys hard-coded.
  - LocalHashingEmbeddingProvider: a deterministic, dependency-free
    fallback (a hashing-trick bag-of-words vector) used when no
    embedding API key is configured, so RAG works out of the box in
    dev/test without requiring an external credential. Lower semantic
    quality than a real embedding model, but keeps the retrieval
    pipeline fully exercised end-to-end.

get_embedding_provider() picks between them based on config.EMBEDDING_PROVIDER.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import List

from app import config


class EmbeddingError(RuntimeError):
    """Raised when an embedding call fails — callers must catch this and
    degrade gracefully (skip indexing/retrieval), never let it break a
    chat turn or profile save."""


class EmbeddingProvider(ABC):
    name: str
    dimensions: int

    @abstractmethod
    def embed_one(self, text: str) -> List[float]:
        ...

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        """Default: embed one at a time. Providers with a real batch API
        should override this for efficiency."""
        return [self.embed_one(t) for t in texts]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Targets any OpenAI-compatible /embeddings endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str, dimensions: int, timeout: float = 20.0):
        self.name = f"openai_compatible:{model}"
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.timeout = timeout

    def _request(self, texts: List[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": texts}
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise EmbeddingError(f"Embedding HTTP error ({exc.code}): {body}") from exc
        except urllib.error.URLError as exc:
            raise EmbeddingError(f"Unable to reach embedding endpoint: {exc}") from exc
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise EmbeddingError(f"Malformed embedding response: {exc}") from exc

        try:
            items = sorted(result["data"], key=lambda d: d.get("index", 0))
            return [item["embedding"] for item in items]
        except (KeyError, TypeError) as exc:
            raise EmbeddingError(f"Unexpected embedding response shape: {exc}") from exc

    def embed_one(self, text: str) -> List[float]:
        return self._request([text])[0]

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self._request(texts)


_TOKEN_RE = re.compile(r"[a-z0-9']+")


class LocalHashingEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, offline "embedding": a normalized hashing-trick
    bag-of-words vector. No network call, no API key, always available.

    This is intentionally simple — it captures lexical/token overlap,
    not deep semantics — but that's enough to make the retrieval
    pipeline (search, relevance evaluation, refinement) fully
    exercisable without any external dependency, and is a reasonable
    default for small/local deployments. Swap in a real embedding
    provider via EMBEDDING_API_KEY for better semantic recall.
    """

    def __init__(self, dimensions: int = 256):
        self.name = "local_hashing"
        self.dimensions = dimensions

    def _hash_index(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimensions

    def embed_one(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return vector
        for token in tokens:
            vector[self._hash_index(token)] += 1.0
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector


_provider_singleton: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """
    Lazily builds and caches the configured provider. Cached because the
    local provider is cheap to build anyway, and the API provider has no
    per-instance state worth re-creating on every call.
    """
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    choice = config.EMBEDDING_PROVIDER
    if choice == "auto":
        choice = "openai_compatible" if config.EMBEDDING_API_KEY else "local"

    if choice == "openai_compatible":
        if not config.EMBEDDING_API_KEY:
            raise EmbeddingError(
                "EMBEDDING_PROVIDER=openai_compatible but EMBEDDING_API_KEY is not set."
            )
        _provider_singleton = OpenAICompatibleEmbeddingProvider(
            base_url=config.EMBEDDING_API_BASE_URL,
            api_key=config.EMBEDDING_API_KEY,
            model=config.EMBEDDING_MODEL,
            dimensions=config.EMBEDDING_DIMENSIONS,
        )
    else:
        _provider_singleton = LocalHashingEmbeddingProvider(dimensions=config.LOCAL_EMBEDDING_DIMENSIONS)

    return _provider_singleton


def reset_embedding_provider() -> None:
    """Test hook — clears the cached singleton so tests can swap config."""
    global _provider_singleton
    _provider_singleton = None
