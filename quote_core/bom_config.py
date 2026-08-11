"""BOM configuration / dash selection for multi-option Time drawings.

Time weldments often print qty columns ``-4 | -3 | -2 | -1``. Quoting
``28106-1`` means use the ``-1`` column only.
"""

from __future__ import annotations

import re
from pathlib import Path

# Assembly option: 28106-1, PN 28106-1, folder "... - 28106-1"
_DASHED_PN_RE = re.compile(r"\b(\d{4,7})-(\d{1,3}[A-Za-z]?)\b", re.IGNORECASE)
_BARE_PN_RE = re.compile(r"^(\d{4,7})$")
_STANDALONE_DASHED_PN_RE = re.compile(
    r"^(\d{4,7})-(\d{1,3}[A-Za-z]?)$", re.IGNORECASE
)
_BARE_DASH_RE = re.compile(r"^\s*-?\s*(\d{1,3}[A-Za-z]?)\s*$", re.IGNORECASE)
# Sheet/config title lines are followed by revision or note markers — not BOM qty.
_SHEET_LABEL_FOLLOW_RE = re.compile(r"(?i)^(REV\.?|NOTE:|NOTES?|ERCN)\b")


def normalize_bom_config(raw: str | None) -> str | None:
    """
    Return the dash suffix only (e.g. ``\"1\"``), or None.

    Accepts ``-1``, ``1``, ``28106-1``.
    """
    text = (raw or "").strip()
    if not text:
        return None
    m = _DASHED_PN_RE.search(text)
    if m:
        return m.group(2).upper()
    m2 = _BARE_DASH_RE.match(text)
    if m2:
        return m2.group(1).upper()
    return None


def extract_bom_config_from_names(*names: str | None) -> str | None:
    """Prefer the rightmost dashed PN in titles / filenames / folder names."""
    found: list[str] = []
    for raw in names:
        if not raw:
            continue
        # Prefer path folder name over full path noise
        stem = Path(str(raw)).name
        for m in _DASHED_PN_RE.finditer(stem):
            found.append(m.group(2).upper())
        if not found:
            for m in _DASHED_PN_RE.finditer(str(raw)):
                found.append(m.group(2).upper())
    return found[-1] if found else None


def resolve_bom_config(
    *,
    explicit: str | None = None,
    title: str | None = None,
    pdf_filename: str | None = None,
    drawing_number: str | None = None,
    library_folder: str | Path | None = None,
    part_key: str | None = None,
) -> str | None:
    """
    Resolve which BOM qty column to use.

    Priority: explicit form field → title → PDF name → title-block DRAWING
    NUMBER → library folder name → dashed part_key.
    """
    for candidate in (
        normalize_bom_config(explicit),
        extract_bom_config_from_names(title),
        extract_bom_config_from_names(pdf_filename),
        extract_bom_config_from_names(drawing_number),
        extract_bom_config_from_names(
            Path(library_folder).name if library_folder else None
        ),
        normalize_bom_config(part_key),
    ):
        if candidate:
            return candidate
    return None


def _base_hint_digits(*names: str | None) -> str | None:
    """Bare assembly base (e.g. ``1004715``) from title/filename hints."""
    for raw in names:
        if not raw:
            continue
        stem = Path(str(raw)).stem
        m = _DASHED_PN_RE.search(stem) or _DASHED_PN_RE.search(str(raw))
        if m:
            return m.group(1)
        m2 = _BARE_PN_RE.fullmatch(stem.strip())
        if m2:
            return m2.group(1)
    return None


def extract_bom_config_from_pdf_text(
    text: str, *, base_hint: str | None = None
) -> str | None:
    """
    Infer dash config from Time sheet labels like a standalone ``1004715-2``
    line followed by ``REV.`` / ``NOTE:``.

    BOM column headers (``1004715-1`` then ``1004715-2`` then a qty) are ignored.
    When several sheet labels exist, the last one wins (detail sheet).
    """
    if not text or not text.strip():
        return None
    base = (base_hint or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    found: list[str] = []
    for i, ln in enumerate(lines):
        m = _STANDALONE_DASHED_PN_RE.fullmatch(ln)
        if not m:
            continue
        if base and m.group(1) != base:
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if not _SHEET_LABEL_FOLLOW_RE.match(nxt):
            continue
        found.append(m.group(2).upper())
    return found[-1] if found else None


def infer_bom_config_from_pdf(
    pdf_path: Path | str | None,
    *,
    title: str | None = None,
    pdf_filename: str | None = None,
) -> str | None:
    """Read a PDF and infer dash config from sheet-style dashed PN labels."""
    if not pdf_path:
        return None
    path = Path(pdf_path)
    if not path.is_file():
        return None
    try:
        from quote_core.weight import _read_pdf_text

        text = _read_pdf_text(path)
    except Exception:  # noqa: BLE001
        return None
    base = _base_hint_digits(title, pdf_filename, path.name)
    return extract_bom_config_from_pdf_text(text, base_hint=base)


def format_bom_config_label(config: str | None) -> str:
    if not config:
        return ""
    return f"-{config.lstrip('-')}"
