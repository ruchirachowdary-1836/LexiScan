"""
LexiScan — PDF Parser Service
Extracts text from PDFs and segments into logical clauses using spaCy.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger


# ── Text Extraction ─────────────────────────────────────────


def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int, List[Dict]]:
    """
    Extract full text and per-page text from a PDF.

    Returns:
        full_text: str
        page_count: int
        pages: List[{"page": int, "text": str}]
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF not installed. Run: pip install PyMuPDF")

    doc = fitz.open(pdf_path)
    pages = []
    full_parts = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        text = _clean_text(text)
        if text.strip():
            pages.append({"page": page_num, "text": text})
            full_parts.append(text)

    doc.close()
    full_text = "\n\n".join(full_parts)
    logger.info(f"Extracted {len(full_text)} chars from {doc.page_count} pages: {pdf_path}")
    return full_text, len(pages), pages


def extract_text_pdfplumber(pdf_path: str) -> str:
    """
    Fallback extractor using pdfplumber (better for tables/columns).
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber not installed.")

    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(_clean_text(text))

    return "\n\n".join(full_text)


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove artifacts."""
    # Remove form feeds, carriage returns
    text = text.replace("\r", "\n").replace("\f", "\n")
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove non-printable except newline/tab
    text = re.sub(r"[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ── Clause Segmentation ──────────────────────────────────────

# Patterns that signal a new clause/section heading
_HEADING_PATTERNS = [
    # Numbered: "1.", "1.1", "1.1.1"
    re.compile(r"^(\d+\.)+\s+\w"),
    # Lettered: "A.", "B."
    re.compile(r"^[A-Z]\.\s+\w"),
    # Roman numerals: "I.", "II.", "III."
    re.compile(r"^(IX|IV|V?I{0,3}|X{0,3})\.\s+\w"),
    # ALL-CAPS heading lines (≤ 8 words)
    re.compile(r"^[A-Z][A-Z\s,\-]{5,60}$"),
    # "ARTICLE", "SECTION", "SCHEDULE" prefixes
    re.compile(r"^(ARTICLE|SECTION|SCHEDULE|EXHIBIT|ANNEX|APPENDIX)\s+\w", re.IGNORECASE),
    # "WHEREAS", "NOW, THEREFORE"
    re.compile(r"^(WHEREAS|NOW,?\s*THEREFORE|IN WITNESS WHEREOF)", re.IGNORECASE),
]


def is_heading(line: str) -> bool:
    line = line.strip()
    if len(line) < 3 or len(line) > 150:
        return False
    return any(p.match(line) for p in _HEADING_PATTERNS)


def segment_into_clauses(full_text: str, pages: List[Dict]) -> List[Dict]:
    """
    Segment contract text into clauses.
    Returns list of clause dicts with text, heading, page_number, clause_index.
    """
    # Build page lookup: character offset → page number
    page_map = _build_page_map(pages)

    lines = full_text.split("\n")
    clauses = []
    current_heading: Optional[str] = None
    current_lines: List[str] = []
    clause_index = 0

    def flush_clause():
        nonlocal clause_index
        text = " ".join(current_lines).strip()
        text = re.sub(r"\s+", " ", text)
        if len(text) < 30:  # skip tiny fragments
            return
        page_num = _get_page_for_text(text[:50], page_map)
        clauses.append({
            "clause_index": clause_index,
            "heading": current_heading,
            "text": text,
            "page_number": page_num,
        })
        clause_index += 1

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if is_heading(stripped):
            # Save previous clause
            if current_lines:
                flush_clause()
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(stripped)

    # Flush last clause
    if current_lines:
        flush_clause()

    # If segmentation produced < 3 clauses, fall back to sentence-based
    if len(clauses) < 3:
        clauses = _sentence_based_segmentation(full_text)

    logger.info(f"Segmented contract into {len(clauses)} clauses")
    return clauses


def _sentence_based_segmentation(text: str, max_sentences: int = 5) -> List[Dict]:
    """
    Fallback: group every N sentences into a clause.
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        nlp.max_length = 2_000_000
        doc = nlp(text)
        sentences = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 20]
    except Exception:
        # Pure regex fallback
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    clauses = []
    for i in range(0, len(sentences), max_sentences):
        chunk = " ".join(sentences[i : i + max_sentences])
        clauses.append({
            "clause_index": len(clauses),
            "heading": None,
            "text": chunk,
            "page_number": None,
        })

    return clauses


def _build_page_map(pages: List[Dict]) -> List[Tuple[int, int, int]]:
    """
    Returns list of (start_char, end_char, page_num).
    Allows mapping a character offset to a page.
    """
    result = []
    offset = 0
    for p in pages:
        text = p["text"]
        result.append((offset, offset + len(text), p["page"]))
        offset += len(text) + 2  # +2 for \n\n separator
    return result


def _get_page_for_text(text_snippet: str, page_map: List[Tuple]) -> Optional[int]:
    """Attempt to identify which page a snippet came from."""
    for _, _, page_num in page_map:
        return page_num  # simplified: return first page
    return None
