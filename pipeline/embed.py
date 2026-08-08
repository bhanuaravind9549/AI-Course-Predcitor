"""Chunk cleaned courses, embed locally, and persist to Chroma."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.config import CHROMA_DIR, CHUNKS_PATH, COLLECTION_NAME, COURSES_PATH
from pipeline.embeddings import LOCAL_EMBEDDING_MODEL, embed_texts

CHUNK_CHARS = 1600
CHUNK_OVERLAP = 250


def chunk_text(text: str, header: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks: list[str] = []
    start = 0
    body = text
    prefix = header.rstrip() + "\n"
    usable = CHUNK_CHARS - len(prefix)
    usable = max(usable, 600)
    while start < len(body):
        end = min(len(body), start + usable)
        if end < len(body):
            split_at = body.rfind(" ", start, end)
            if split_at > start + 200:
                end = split_at
        piece = prefix + body[start:end].strip()
        chunks.append(piece)
        if end >= len(body):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def build_chunks(courses: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for course in courses:
        header = f"Course: {course['course_code']} {course['title']}"
        texts = chunk_text(course.get("retrieval_text", ""), header)
        for index, text in enumerate(texts):
            chunks.append(
                {
                    "id": (
                        f"{course['term_code']}-"
                        f"{hashlib.md5(f'{course['course_code']}|{course['title']}'.encode()).hexdigest()[:10]}-"
                        f"{index}"
                    ),
                    "text": text,
                    "metadata": {
                        "course_code": course["course_code"],
                        "title": course["title"][:300],
                        "department": course["department"],
                        "department_name": course["department_name"][:200],
                        "credits": str(course.get("credits") or ""),
                        "level": course["level"],
                        "term": course["term"],
                        "term_code": course["term_code"],
                        "prerequisites": (course.get("prerequisites") or "")[:400],
                        "description": (course.get("description") or "")[:900],
                        "meetings": "; ".join(course.get("meetings") or [])[:400],
                        "instructors": "; ".join(course.get("instructors") or [])[:400],
                        "campus": course.get("campus") or "IU Bloomington",
                    },
                }
            )
    return chunks


def batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main() -> None:
    load_dotenv(ROOT / ".env", override=True)
    if not COURSES_PATH.exists():
        raise SystemExit("Run `python -m pipeline.ingest` first.")

    courses = json.loads(COURSES_PATH.read_text(encoding="utf-8"))
    chunks = build_chunks(courses)
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"Prepared {len(chunks):,} chunks from {len(courses):,} courses")
    print(f"Embedding locally with {LOCAL_EMBEDDING_MODEL}...")

    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        chroma.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    embedded = 0
    for batch in batched(chunks, 64):
        vectors = embed_texts([item["text"] for item in batch])
        collection.upsert(
            ids=[item["id"] for item in batch],
            documents=[item["text"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
            embeddings=vectors,
        )
        embedded += len(batch)
        print(f"  indexed {embedded:,}/{len(chunks):,}")

    print(f"Chroma collection `{COLLECTION_NAME}` ready at {CHROMA_DIR}")


if __name__ == "__main__":
    main()
