from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

ROOT = Path(__file__).resolve().parents[1]


def groq_api_key() -> str:
    load_dotenv(ROOT / ".env", override=True)
    return (os.getenv("GROQ_API_KEY") or "").strip()


def require_groq_key() -> str:
    key = groq_api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return key


def groq_client() -> Groq:
    return Groq(api_key=require_groq_key())


def chat_model() -> str:
    return os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")


def embedding_model() -> str:
    from pipeline.embeddings import LOCAL_EMBEDDING_MODEL

    return os.getenv("EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)


def with_retries(fn, *, attempts: int = 6):
    last_error = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            message = str(exc).lower()
            if attempt == attempts - 1 or not any(
                token in message for token in ("rate", "429", "timeout", "temporar")
            ):
                raise
            time.sleep(min(2 ** attempt, 20))
    raise last_error
