from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from pipeline.embeddings import embed_texts
from pipeline.llm import chat_model, groq_client, with_retries

ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = ROOT / "chroma"
COURSES_PATH = ROOT / "data" / "processed" / "courses.json"
COLLECTION_NAME = "iu_courses"

SYSTEM_PROMPT = """You are an academic advisor for Indiana University Bloomington.
You recommend courses using ONLY the retrieved catalog records provided.
Never invent a course code, title, prerequisite, meeting time, or credit hour.
If the retrieved set is a weak match, say so and recommend the closest real options.
Prefer 3-6 courses. Explain each pick in 1-3 sentences tied to the student's goals.
Write in a clear, encouraging tone without hype."""


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    if not COURSES_PATH.exists():
        return []
    return json.loads(COURSES_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def catalog_index() -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for course in load_catalog():
        index[(course["term_code"], course["course_code"], course["title"])] = course
        index.setdefault((course["term_code"], course["course_code"], ""), course)
    return index


def get_meta() -> dict[str, Any]:
    courses = load_catalog()
    terms = sorted({c["term"] for c in courses}, key=lambda t: t)
    departments = sorted(
        {
            (c["department"], c["department_name"])
            for c in courses
            if c.get("department")
        },
        key=lambda item: item[0],
    )
    return {
        "course_count": len(courses),
        "terms": terms,
        "departments": [
            {"code": code, "name": name} for code, name in departments
        ],
        "levels": ["undergraduate", "graduate"],
        "index_ready": any(CHROMA_DIR.rglob("*")) and any(
            p.suffix in {".sqlite3", ".bin", ".pickle"} or p.name == "chroma.sqlite3"
            for p in CHROMA_DIR.rglob("*")
            if p.is_file()
        ),
    }


def _collection():
    if not CHROMA_DIR.exists():
        raise FileNotFoundError("Chroma index missing. Run `python -m pipeline.embed`.")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def _where(term: str | None, department: str | None, level: str | None) -> dict | None:
    clauses: list[dict] = []
    if term:
        clauses.append({"term": {"$eq": term}})
    if department:
        clauses.append({"department": {"$eq": department.upper()}})
    if level:
        clauses.append({"level": {"$eq": level.lower()}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def retrieve(
    query: str,
    term: str | None = None,
    department: str | None = None,
    level: str | None = None,
    k: int = 12,
) -> list[dict[str, Any]]:
    vector = embed_texts([query])[0]
    collection = _collection()
    kwargs: dict[str, Any] = {
        "query_embeddings": [vector],
        "n_results": max(4, min(k, 24)),
        "include": ["documents", "metadatas", "distances"],
    }
    where = _where(term, department, level)
    if where:
        kwargs["where"] = where
    result = collection.query(**kwargs)

    seen: set[tuple[str, str, str]] = set()
    hits: list[dict[str, Any]] = []
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]
    for meta, distance in zip(metadatas[0], distances[0]):
        key = (meta.get("term_code", ""), meta.get("course_code", ""), meta.get("title", ""))
        if key in seen:
            continue
        seen.add(key)
        score = round(max(0.0, 1.0 - float(distance)), 3)
        full = catalog_index().get(key) or catalog_index().get((key[0], key[1], "")) or {}
        hits.append(
            {
                "code": meta.get("course_code", ""),
                "title": meta.get("title", ""),
                "department": meta.get("department", ""),
                "department_name": meta.get("department_name", ""),
                "credits": meta.get("credits", ""),
                "level": meta.get("level", ""),
                "term": meta.get("term", ""),
                "term_code": meta.get("term_code", ""),
                "prerequisites": full.get("prerequisites") or meta.get("prerequisites") or "",
                "description": full.get("description") or meta.get("description") or "",
                "meetings": full.get("meetings")
                or [m for m in (meta.get("meetings") or "").split("; ") if m],
                "instructors": full.get("instructors")
                or [i for i in (meta.get("instructors") or "").split("; ") if i],
                "score": score,
            }
        )
    return hits


def recommend(
    query: str,
    term: str | None = None,
    department: str | None = None,
    level: str | None = None,
    k: int = 12,
) -> dict[str, Any]:
    retrieved = retrieve(query, term=term, department=department, level=level, k=k)
    if not retrieved:
        return {
            "summary": "No catalog courses matched those filters. Try a broader query or clear a filter.",
            "courses": [],
        }

    compact = [
        {
            "code": c["code"],
            "title": c["title"],
            "department": c["department_name"] or c["department"],
            "credits": c["credits"],
            "level": c["level"],
            "term": c["term"],
            "prerequisites": c["prerequisites"],
            "description": (c["description"] or "")[:700],
            "meetings": c["meetings"][:6],
            "score": c["score"],
        }
        for c in retrieved
    ]
    client = groq_client()
    model_name = chat_model()
    completion = with_retries(
        lambda: client.chat.completions.create(
            model=model_name,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Student query:\n{query}\n\n"
                        f"Retrieved IU Bloomington courses (JSON):\n{json.dumps(compact, indent=2)}\n\n"
                        "Return JSON with this shape:\n"
                        '{"summary": "short advisor overview",'
                        '"picks": [{"code": "CSCI-B 455", "term": "Spring 2026",'
                        '"reason": "why this course fits"}]}'
                    ),
                },
            ],
        )
    )
    raw = completion.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"summary": "Here are the closest catalog matches.", "picks": []}

    by_code_term = {(c["code"], c["term"]): c for c in retrieved}
    recommended: list[dict[str, Any]] = []
    for pick in parsed.get("picks") or []:
        code = str(pick.get("code") or "").strip()
        pick_term = str(pick.get("term") or "").strip()
        match = by_code_term.get((code, pick_term))
        if not match:
            match = next((c for c in retrieved if c["code"] == code), None)
        if not match:
            continue
        item = dict(match)
        item["reason"] = str(pick.get("reason") or "").strip()
        recommended.append(item)

    if not recommended:
        # Fall back to top retrieved hits with a generic grounded note.
        for course in retrieved[:5]:
            item = dict(course)
            item["reason"] = (
                f"This catalog course is semantically close to your query "
                f"({course['title']})."
            )
            recommended.append(item)

    return {
        "summary": parsed.get("summary")
        or "Here are IU Bloomington courses grounded in the catalog.",
        "courses": recommended[:6],
    }
