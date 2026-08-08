from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env", override=True)

from backend.rag import get_meta, recommend  # noqa: E402
from pipeline.llm import chat_model, embedding_model, groq_api_key  # noqa: E402

app = FastAPI(title="IU RAG Course Selector", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    term: str | None = None
    department: str | None = None
    level: str | None = None
    k: int = Field(default=12, ge=4, le=24)


@app.get("/health")
def health():
    meta = get_meta()
    return {
        "status": "ok",
        "model": chat_model(),
        "embedding_model": embedding_model(),
        **meta,
    }


@app.get("/api/meta")
def meta():
    return get_meta()


@app.post("/api/recommend")
def api_recommend(body: RecommendRequest):
    if not groq_api_key():
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")
    try:
        return recommend(
            query=body.query.strip(),
            term=body.term,
            department=body.department,
            level=body.level,
            k=body.k,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {exc}") from exc
