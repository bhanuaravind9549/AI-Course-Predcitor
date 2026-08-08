from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
COURSES_PATH = DATA_PROCESSED / "courses.json"
CHUNKS_PATH = DATA_PROCESSED / "chunks.json"
CHROMA_DIR = ROOT / "chroma"
COLLECTION_NAME = "iu_courses"

SOC_BASE = "https://utilities.registrar.indiana.edu/course-browser/browser/research"

# Public research dumps (no IU login). Fall/Summer 2026 Excel/HTML
# via retrieve.shtml require CAS, so we ingest the latest public terms.
TERMS = [
    {"code": "4268", "name": "Fall 2026"},
    {"code": "4265", "name": "Summer 2026"},
    {"code": "4262", "name": "Spring 2026"},
    {"code": "4258", "name": "Fall 2025"},
    {"code": "4255", "name": "Summer 2025"},
]

USER_AGENT = (
    "IU-RAG-Course-Selector/1.0 (student academic project; polite catalog ingest)"
)
