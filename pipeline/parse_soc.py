"""Parse IU Registrar Schedule of Classes HTML research dumps."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup

COURSE_HEADER_RE = re.compile(
    r"<B>\s*([A-Z]{2,5}-[A-Z]{1,4})\s+(\d{3,5}[A-Z]?)\s+(.+?)\s+\("
    r"(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)\s*CR\)\s*</B>",
    re.I,
)
PLAIN_HEADER_RE = re.compile(
    r"^\s*([A-Z]{2,5}-[A-Z]{1,4})\s+(\d{3,5}[A-Z]?)\s{2,}(.+?)\s+\("
    r"(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)\s*CR\)\s*$"
)
SECTION_RE = re.compile(
    r"^\s*(CLSD\s+)?(\d{4,5})\b(.*?)(\d+)\s+(\d+)\s+(\d+)\s*$"
)
TIME_RE = re.compile(r"\d{1,2}:\d{2}[AP]-\d{1,2}:\d{2}[AP]|ARR")
DAYS_RE = re.compile(r"\b([MTWRFSU]{1,6}|ARR)\b")
ROOM_RE = re.compile(
    r"^(ARR|WB WEB|HD TBA|FA WEB|ONLINE|[A-Z]{1,5}\s+\d{1,5}[A-Z]?)\s*(.*)$"
)
VT_RE = re.compile(r"^\s*VT:\s*(.+?)\s*$")
PREREQ_RE = re.compile(
    r"(?:P\s*[-:]|Prerequisites?\s*:\s*)(.{8,220})",
    re.I,
)
COMPONENT_RE = re.compile(
    r"^\s*(?:<B>)?(Laboratory|Discussion|Lecture|Studio|Recitation|Seminar)"
    r"\s*\(([A-Z]+)\)(?:</B>)?\s*$",
    re.I,
)
SKIP_LINE_RE = re.compile(r"^\s*(Max\s+Avl\s+W/L|\*\*\s*ERROR)", re.I)


def clean_text(value: str) -> str:
    text = html.unescape(value or "")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ").replace("\u0000", "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" \t-–—:")
    return text


def course_level(number: str) -> str:
    match = re.match(r"(\d+)", number)
    n = int(match.group(1)) if match else 0
    return "graduate" if n >= 500 else "undergraduate"


def parse_meeting(rest: str) -> dict[str, str]:
    cleaned = re.sub(r"\b(PERM|RSTR|NON|\dW\d|12W|NS\d)\b", " ", rest)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    time_match = TIME_RE.search(cleaned)
    time = time_match.group(0) if time_match else ""
    search_from = cleaned[time_match.end() :] if time_match else cleaned
    days_match = DAYS_RE.search(search_from)
    days = days_match.group(1) if days_match else ""
    after = search_from[days_match.end() :] if days_match else search_from
    after = re.sub(r"\d+\s+\d+\s+\d+\s*$", "", after).strip()
    room_match = ROOM_RE.match(after)
    if room_match:
        room, instructor = room_match.group(1), room_match.group(2).strip()
    else:
        room, instructor = "", after
    if days and time:
        meeting = f"{days} {time}"
    elif time:
        meeting = time
    else:
        meeting = "ARR"
    if room and room not in {"ARR", meeting}:
        meeting = f"{meeting} ({room})"
    return {"meeting": meeting, "instructor": clean_text(instructor)}


def _new_course(
    dept_code: str,
    dept_name: str,
    subject: str,
    number: str,
    title: str,
    credits: str,
    term_code: str,
    term_name: str,
) -> dict[str, Any]:
    code = f"{subject} {number}"
    return {
        "course_code": code,
        "subject": subject,
        "number": number,
        "title": clean_text(title),
        "variable_title": "",
        "department": dept_code,
        "department_name": dept_name,
        "credits": credits,
        "level": course_level(number),
        "term": term_name,
        "term_code": term_code,
        "campus": "IU Bloomington",
        "prerequisites": "",
        "gened_or_attributes": [],
        "notes": [],
        "instructors": [],
        "meetings": [],
        "section_count": 0,
    }


def _extract_prereq(notes: list[str]) -> str:
    blob = " ".join(notes)
    match = PREREQ_RE.search(blob)
    return clean_text(match.group(1)) if match else ""


def _extract_attributes(notes: list[str]) -> list[str]:
    attrs: list[str] = []
    for note in notes:
        if re.search(r"GenEd|CASE|credit|Gen Ed", note, re.I):
            cleaned = clean_text(note)
            if cleaned and cleaned not in attrs:
                attrs.append(cleaned)
    return attrs[:8]


def parse_department_pre(
    pre_html: str,
    dept_code: str,
    dept_name: str,
    term_code: str,
    term_name: str,
) -> list[dict[str, Any]]:
    current: dict[str, Any] | None = None
    courses: list[dict[str, Any]] = []

    for raw_line in pre_html.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or SKIP_LINE_RE.search(line):
            continue

        header = COURSE_HEADER_RE.search(line) or PLAIN_HEADER_RE.search(
            re.sub(r"<[^>]+>", "", line)
        )
        if header:
            if current:
                courses.append(current)
            subject, number, title, credits = header.groups()
            current = _new_course(
                dept_code,
                dept_name,
                subject.upper(),
                number.upper(),
                title,
                credits,
                term_code,
                term_name,
            )
            continue

        if current is None:
            continue

        vt = VT_RE.match(re.sub(r"<[^>]+>", "", line))
        if vt:
            current["variable_title"] = clean_text(vt.group(1))
            continue

        if COMPONENT_RE.match(line):
            continue

        section = SECTION_RE.match(re.sub(r"</?B>", "", line))
        if section:
            _clsd, class_nbr, rest, _mx, _avl, _wl = section.groups()
            parsed = parse_meeting(rest)
            current["section_count"] += 1
            if parsed["meeting"] and parsed["meeting"] not in current["meetings"]:
                current["meetings"].append(parsed["meeting"])
            if parsed["instructor"] and parsed["instructor"] not in current["instructors"]:
                current["instructors"].append(parsed["instructor"])
            continue

        note = clean_text(line)
        if note and note not in current["notes"]:
            current["notes"].append(note)

    if current:
        courses.append(current)

    for course in courses:
        if course["variable_title"]:
            course["title"] = f"{course['title']}: {course['variable_title']}"
        course["prerequisites"] = _extract_prereq(course["notes"])
        course["gened_or_attributes"] = _extract_attributes(course["notes"])
        course["description"] = " ".join(course["notes"]).strip()[:2500]
    return courses


def parse_soc_html(html_text: str, term_code: str, term_name: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html_text, "lxml")
    all_courses: list[dict[str, Any]] = []

    for heading in soup.find_all("h3"):
        anchor = heading.find("a", attrs={"name": True})
        if not anchor:
            continue
        dept_code = anchor.get("name", "").strip().upper()
        dept_name = clean_text(heading.get_text(" ", strip=True))
        pre = heading.find_next_sibling("pre")
        if not dept_code or pre is None:
            continue
        # Keep <B> tags for reliable course-header detection.
        pre_html = "".join(str(part) for part in pre.contents)
        all_courses.extend(
            parse_department_pre(pre_html, dept_code, dept_name, term_code, term_name)
        )
    return all_courses


def dedupe_courses(courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for course in courses:
        key = (course["term_code"], course["course_code"], course["title"].lower())
        if key not in merged:
            merged[key] = course
            continue
        existing = merged[key]
        existing["section_count"] += course["section_count"]
        for field in ("meetings", "instructors", "notes", "gened_or_attributes"):
            for item in course[field]:
                if item not in existing[field]:
                    existing[field].append(item)
        if len(course.get("description", "")) > len(existing.get("description", "")):
            existing["description"] = course["description"]
        if course["prerequisites"] and not existing["prerequisites"]:
            existing["prerequisites"] = course["prerequisites"]
    return list(merged.values())


def build_retrieval_text(course: dict[str, Any]) -> str:
    parts = [
        f"Course: {course['course_code']} {course['title']}",
        f"Department: {course['department_name']}",
        f"Campus: {course['campus']}",
        f"Term: {course['term']}",
        f"Credits: {course['credits']}",
        f"Level: {course['level']}",
    ]
    if course.get("prerequisites"):
        parts.append(f"Prerequisites: {course['prerequisites']}")
    if course.get("gened_or_attributes"):
        parts.append("Attributes: " + "; ".join(course["gened_or_attributes"][:5]))
    if course.get("description"):
        parts.append(f"Description: {course['description']}")
    if course.get("meetings"):
        parts.append("Meetings: " + "; ".join(course["meetings"][:8]))
    if course.get("instructors"):
        parts.append("Instructors: " + "; ".join(course["instructors"][:8]))
    return "\n".join(parts)
