"""BOM dash from the upload UI — which LIST OF MATERIAL qty column to read.

Only a few customers (Time-style) print multiple dash qty columns on one
drawing (``-4 | -3 | -2 | -1``, or ``1004747-1 | 1004747-2``). Most
drawings are single-BOM with one QTY column — do not invent dash columns
there. 102728-1 is a single qty column.

A **blank** upload dash means the drawing is single-BOM — read the one
QTY column. Do not invent dash columns and do not require ``-1`` on
102728-style tables. A **filled** dash (``-1``, ``-2``, …) selects that
printed column only; blank / ``-`` cells in it are omitted. Do not sum
or mix columns.
"""

from __future__ import annotations

import re
from pathlib import Path

# Assembly option: 28106-1, PN 28106-1, folder "... - 28106-1"
_DASHED_PN_RE = re.compile(r"\b(\d{4,7})-(\d{1,3}[A-Za-z]?)\b", re.IGNORECASE)
_BARE_DASH_RE = re.compile(r"^\s*-?\s*(\d{1,3}[A-Za-z]?)\s*$", re.IGNORECASE)


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
    library_folder: str | Path | None = None,
    part_key: str | None = None,
) -> str | None:
    """
    The upload/typed dash field only.

    Blank means single-BOM (one QTY column). Title, filename, folder, and
    part_key must not invent a dash — 102728-1 in the title is not a
    second qty column.
    """
    return normalize_bom_config(explicit)


def format_bom_config_label(config: str | None) -> str:
    if not config:
        return ""
    return f"-{config.lstrip('-')}"
