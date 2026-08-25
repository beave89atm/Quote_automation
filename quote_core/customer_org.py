"""Map drawing brands (title-block / logo text) to SecturaFAB Organizations."""

from __future__ import annotations

import re
from pathlib import Path

from quote_core.weight import _read_pdf_text

# First matching pattern wins. Detect via PDF text (logo OCR is unreliable).
_DRAWING_TO_ORGANIZATION: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bTYCROP\b", re.IGNORECASE), "Propell"),
    (
        re.compile(r"\bCUMMINS\s+CLEAN\s+FUEL\b", re.IGNORECASE),
        "Cummins Clean Fuel Technologies",
    ),
    (
        re.compile(r"\bNATURAL\s+GAS\s+FUEL\s+SYSTEMS\b", re.IGNORECASE),
        "Cummins Clean Fuel Technologies",
    ),
    (
        re.compile(r"\bTIME\s+MANUFACTURING\b", re.IGNORECASE),
        "Time Manufacturing Waco",
    ),
]

# Library folder path segments → Organization (when PDF text is thin).
_FOLDER_TO_ORGANIZATION: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"Cummins\s+Clean\s+Fuel\s+Technologies", re.IGNORECASE),
        "Cummins Clean Fuel Technologies",
    ),
    (re.compile(r"\bTYCROP\b", re.IGNORECASE), "Propell"),
    (
        re.compile(
            r"(?:Customer\s+Drawings|\bEngineering\b)[\\/]+Time\b|[\\/]Time[\\/]",
            re.IGNORECASE,
        ),
        "Time Manufacturing Waco",
    ),
    (
        re.compile(r"\bTIME\s+MANUFACTURING\b", re.IGNORECASE),
        "Time Manufacturing Waco",
    ),
]


def detect_organization_from_text(text: str | None) -> str | None:
    """Return SecturaFAB Organization display name for known drawing brands."""
    if not text or not text.strip():
        return None
    for pattern, org_name in _DRAWING_TO_ORGANIZATION:
        if pattern.search(text):
            return org_name
    return None


def detect_organization_from_folder(folder: Path | str | None) -> str | None:
    """Return Organization when the drawing-library folder path names a known customer."""
    if not folder:
        return None
    blob = str(folder)
    for pattern, org_name in _FOLDER_TO_ORGANIZATION:
        if pattern.search(blob):
            return org_name
    return None


def detect_organization_from_pdf(path: Path | str | None) -> str | None:
    """Read a PDF and return Organization name when a known brand is present."""
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        text = _read_pdf_text(p)
    except Exception:  # noqa: BLE001
        return None
    return detect_organization_from_text(text)


def detect_organization(
    *,
    pdf_path: Path | str | None = None,
    library_folder: Path | str | None = None,
) -> str | None:
    """Prefer PDF brand text; fall back to drawing-library folder path."""
    return detect_organization_from_pdf(pdf_path) or detect_organization_from_folder(
        library_folder
    )
