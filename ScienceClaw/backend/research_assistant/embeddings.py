from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from backend.research_assistant.models import IngestionResult


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class EmbeddingProvider(Protocol):
    model_name: str

    def embed_text(self, text: str) -> list[float]:
        ...


class HashingEmbeddingProvider:
    def __init__(self, *, dimensions: int = 1536, model_name: str = "local-hashing-v1") -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions
        self.model_name = model_name

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def build_chunk_embeddings(
    result: IngestionResult,
    provider: EmbeddingProvider,
) -> list[tuple[str, list[float]]]:
    return [(chunk.chunk_id, provider.embed_text(chunk.text)) for chunk in result.chunks]
