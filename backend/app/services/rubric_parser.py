"""
Rubric Document Parser Service.
Extracts structured rubric components, marks, and model answers
from uploaded rubric files (PDF, TXT) or raw strings.
"""
import os
import re
from typing import Optional


KNOWN_TITLES = [
    "Problem understanding and graph modeling",
    "Choice of algorithm",
    "Initialization of distance matrix",
    "Conversion of train data into graph edges",
    "Floyd-Warshall recurrence relation",
    "Pseudocode correctness",
    "Example execution/output",
    "Time complexity/space complexity",
    "Time complexity / space complexity",
    "Correctness",
    "Completeness",
    "Clarity & Diagrams",
    "Clarity",
    "Approach and Methodology",
    "Optimization and Constraints",
]

DEFAULT_FALLBACK_COMPONENTS = [
    {
        "name": "1. Problem understanding and graph modeling",
        "marks": 1.0,
        "model_answer": "States that cities are represented as nodes and train routes/costs as weighted edges",
    },
    {
        "name": "2. Choice of algorithm",
        "marks": 1.0,
        "model_answer": "Correctly identifies Floyd-Warshall as an all-pairs shortest path approach",
    },
    {
        "name": "3. Initialization of distance matrix",
        "marks": 1.0,
        "model_answer": "Distance matrix created properly, diagonal = 0, infinity elsewhere",
    },
    {
        "name": "4. Conversion of train data into graph edges",
        "marks": 2.0,
        "model_answer": "Correct handling of train ranges (Li, Ri, Wi) into graph representation",
    },
    {
        "name": "5. Floyd-Warshall recurrence relation",
        "marks": 1.0,
        "model_answer": "Correct formula used: D^(k)[i][j] = min(D^(k-1)[i][j], D^(k-1)[i][k] + D^(k-1)[k][j])",
    },
    {
        "name": "6. Pseudocode correctness",
        "marks": 2.0,
        "model_answer": "Proper nested loops (k, i, j) and state distance update step",
    },
    {
        "name": "7. Example execution/output",
        "marks": 1.0,
        "model_answer": "Shows state matrix evolution with meaningful trace",
    },
    {
        "name": "8. Time complexity/space complexity",
        "marks": 1.0,
        "model_answer": "Mentions O(N^3) time and O(N^2) space with analytical rationale",
    },
]


def parse_rubric_text(text: str) -> list[dict]:
    """Parse raw text from a rubric file into structured components."""
    if not text:
        return []

    raw_lines = [l.strip() for l in text.replace("\r", "").split("\n") if l.strip()]
    merged = []

    for l in raw_lines:
        if re.match(r"^\d+[\.\)]", l):
            merged.append(l)
        elif merged and not l.lower().startswith("total") and not l.lower().startswith("rubric") and not l.lower().startswith("component"):
            merged[-1] += " " + l

    components = []
    for item in merged:
        m_num = re.match(r"^(\d+[\.\)])\s*(.*)$", item)
        if not m_num:
            continue
        num_str, rest = m_num.groups()
        m_marks = re.search(r"(\d+(?:\.\d+)?)\s*(?:marks?|pts?)?\s*$", rest, re.IGNORECASE)
        marks = float(m_marks.group(1)) if m_marks else 1.0
        body = rest[:m_marks.start()].strip() if m_marks else rest

        title = body
        content = body

        # Try matching known titles or delimiters
        matched_kt = False
        for kt in KNOWN_TITLES:
            pattern = re.escape(kt).replace(r"\ ", r"\s+").replace("-", ".")
            m_kt = re.search(pattern, body, re.IGNORECASE)
            if m_kt:
                title = body[:m_kt.end()].strip()
                content = body[m_kt.end():].strip()
                if not content:
                    content = title
                matched_kt = True
                break

        if not matched_kt:
            # Check for colon or hyphen separator
            parts = re.split(r"[:\-–—]\s+", body, maxsplit=1)
            if len(parts) == 2:
                title = parts[0].strip()
                content = parts[1].strip()

        components.append({
            "name": f"{num_str} {title}" if not title.startswith(num_str) else title,
            "marks": marks,
            "model_answer": content,
        })

    return components


def parse_rubric_file(file_path: str) -> list[dict]:
    """Extract and parse structured rubric components from a local file."""
    if not os.path.exists(file_path):
        return []

    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == ".pdf":
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_path)
            text = "\n".join(p.get_textpage().get_text_range() for p in pdf)
        except Exception as e:
            print(f"[RubricParser] PDF extraction error: {e}")
            return []
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            print(f"[RubricParser] Text read error: {e}")
            return []

    return parse_rubric_text(text)
