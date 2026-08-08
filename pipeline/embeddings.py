"""Local embeddings via Chroma's bundled ONNX MiniLM (no Groq/OpenAI embeddings)."""

from __future__ import annotations

from functools import lru_cache

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def embedding_fn() -> DefaultEmbeddingFunction:
    return DefaultEmbeddingFunction()


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = embedding_fn()(texts)
    return [list(map(float, vector)) for vector in vectors]
