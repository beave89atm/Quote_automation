"""BOM configuration / dash selection for multi-option Time drawings.

Time weldments often print qty columns ``-4 | -3 | -2 | -1``. Quoting
``28106-1`` means use the ``-1`` column only.
"""

from __future__ import annotations

import re
from pathlib import Path

# Assembly option: 28106-1, PN 28106-1, folder "... - 28106-1"
_DASHED_PN_RE = re.compile(r"\b(\d{4,7})-(\d{1,3}[A-Za-z]?)\b", re.IGNORECASE)
_BARE_DASH_RE = re.compile(r"^\s*-?\s*(\d{1,3}[A-Za-z]?)\s*$", re.IGNORECASE)
# Title "1004747" (no -N) means dash -1 unless Kyle typed -2.
_BARE_ASSEMBLY_PN_RE = re.compile(
    r"\b(\d{4,7})(?!\s*-\s*\d{1,3}[A-Za-z]?\b)",
    re.IGNORECASE,
)


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


def title_defaults_to_dash_one(title: str | None) -> bool:
    """Bare Time title ``1004747`` (no ``-N``) means the ``-1`` qty column."""
    text = (title or "").strip()
    if not text:
        return False
    if extract_bom_config_from_names(title):
        return False
    return bool(_BARE_ASSEMBLY_PN_RE.search(text))


def resolve_bom_config(
    *,
    explicit: str | None = None,
    title: str | None = None,
    pdf_filename: str | None = None,
    library_folder: str | Path | None = None,
    part_key: str | None = None,
) -> str | None:
    """
    Resolve which BOM qty column to use.

    Priority: explicit form field → dashed title → bare title defaults to ``1``
    (folder ``-2`` must not override a bare ``1004747`` title) → PDF name →
    library folder name → dashed part_key.
    """
    explicit_n = normalize_bom_config(explicit)
    if explicit_n:
        return explicit_n
    title_n = extract_bom_config_from_names(title)
    if title_n:
        return title_n
    if title_defaults_to_dash_one(title):
        return "1"
    # Dashed job PN (1020249-1) beats folder -2 (live e21bc43 used LOM -2).
    part_key_n = normalize_bom_config(part_key)
    if part_key_n:
        return part_key_n
    for candidate in (
        extract_bom_config_from_names(pdf_filename),
        extract_bom_config_from_names(
            Path(library_folder).name if library_folder else None
        ),
    ):
        if candidate:
            return candidate
    return None


def format_bom_config_label(config: str | None) -> str:
    if not config:
        return ""
    return f"-{config.lstrip('-')}"
