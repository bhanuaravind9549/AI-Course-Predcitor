"""Download official IU Schedule of Classes dumps, clean, and write catalog JSON."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.config import DATA_PROCESSED, DATA_RAW, COURSES_PATH, SOC_BASE, TERMS, USER_AGENT
from pipeline.parse_soc import build_retrieval_text, dedupe_courses, parse_soc_html


def soc_url(term_code: str) -> str:
    return f"{SOC_BASE}/soc{term_code}fac.html"


def download_term(term_code: str, term_name: str) -> Path | None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    dest = DATA_RAW / f"soc{term_code}fac.html"
    if dest.exists() and dest.stat().st_size > 50_000:
        print(f"  cache hit {dest.name}")
        return dest

    url = soc_url(term_code)
    print(f"  downloading {term_name} ({term_code}) -> {url}")
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        timeout=120,
        allow_redirects=True,
    )
    if response.status_code != 200 or "login" in response.url.lower():
        print(f"  skip {term_name}: HTTP {response.status_code} (not a public dump)")
        return None
    if len(response.content) < 50_000:
        print(f"  skip {term_name}: response too small ({len(response.content)} bytes)")
        return None
    dest.write_bytes(response.content)
    print(f"  saved {dest.name} ({len(response.content):,} bytes)")
    time.sleep(1.5)
    return dest


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    parsed = []
    downloaded = []

    print("Ingesting IU Bloomington Schedule of Classes dumps...")
    for term in TERMS:
        path = download_term(term["code"], term["name"])
        if not path:
            continue
        downloaded.append(term["name"])
        html_text = path.read_text(encoding="latin-1", errors="replace")
        courses = parse_soc_html(html_text, term["code"], term["name"])
        print(f"  parsed {len(courses):,} section-rows for {term['name']}")
        parsed.extend(courses)

    if not parsed:
        raise SystemExit("No public dumps could be downloaded. Check network access.")

    courses = dedupe_courses(parsed)
    for course in courses:
        course["retrieval_text"] = build_retrieval_text(course)
        # notes can be long; keep a short copy for the API payload
        course["notes"] = course["notes"][:12]

    courses.sort(key=lambda c: (c["term_code"], c["department"], c["course_code"], c["title"]))
    COURSES_PATH.write_text(json.dumps(courses, indent=2), encoding="utf-8")

    depts = sorted({c["department"] for c in courses})
    terms = sorted({c["term"] for c in courses})
    print(
        f"Wrote {len(courses):,} unique courses from {', '.join(downloaded)}\n"
        f"  terms: {', '.join(terms)}\n"
        f"  departments: {len(depts)}\n"
        f"  output: {COURSES_PATH}"
    )


if __name__ == "__main__":
    main()
