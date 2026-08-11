"""Extract sheet/plate flat-pattern Length × Width from drawing PDFs.

Shop rule: ItemList Length/Width must be the flat blank size (not formed
envelope, not raw stock plate like ``1/8 x 60 x 120`` or ``60" x 120" SHEET``).
"""

from __future__ import annotations

import re
from pathlib import Path

# Parts-list / title-block blank: 26.85 x 8.49  (or with inch marks)
_BLANK_PAIR_RE = re.compile(
    r"(?<![\d./])(\d{1,3}(?:\.\d{1,4})?)\s*[\"″']?\s*[Xx×]\s*"
    r"(\d{1,3}(?:\.\d{1,4})?)\s*[\"″']?(?![\d./])",
)

# Stock plate: thickness × stock-L × stock-W  (e.g. 1/8 x 60 x 120)
_STOCK_THREE_RE = re.compile(
    r"(?:\d+/\d+|\d+(?:\.\d+)?)\s*[Xx×]\s*"
    r"\d+(?:\.\d+)?\s*[Xx×]\s*\d+(?:\.\d+)?",
)

# Stock sheet two-number callout: 60" x 120" SHEET
_STOCK_SHEET_RE = re.compile(
    r"(?<![\d./])\d{1,3}(?:\.\d{1,4})?\s*[\"″']?\s*[Xx×]\s*"
    r"\d{1,3}(?:\.\d{1,4})?\s*[\"″']?\s*SHEET\b",
    re.IGNORECASE,
)

# Flat-view parentheticals: (26.85) … (8.49)
_PAREN_DIM_RE = re.compile(r"\(\s*(\d{1,3}(?:\.\d{1,4})?)\s*\)")

_FLAT_HEADING_RE = re.compile(r"FLAT\s+PATTERN", re.IGNORECASE)

# Consecutive paren callouts farther apart than this are unrelated dims.
_PAREN_PAIR_MAX_GAP = 80

# Reasonable plate blank envelope (inches). Upper bound is generous for long
# rails; lower bound skips hole/radius noise.
_MIN_SIDE = 0.5
_MAX_SIDE = 240.0


def _normalize_pair(a: float, b: float) -> tuple[float, float] | None:
    if a <= 0 or b <= 0:
        return None
    if not (_MIN_SIDE <= a <= _MAX_SIDE and _MIN_SIDE <= b <= _MAX_SIDE):
        return None
    # Reject near-square noise that is almost certainly a thickness/radius.
    if max(a, b) < 1.0:
        return None
    return (max(a, b), min(a, b))


def _scrub_stock_plates(text: str) -> str:
    """Remove stock callouts so they are not mistaken for part blanks."""
    t = _STOCK_THREE_RE.sub(" ", text or "")
    t = _STOCK_SHEET_RE.sub(" ", t)
    return t


def _pairs_from_blank_callouts(text: str) -> list[tuple[float, float]]:
    scrubbed = _scrub_stock_plates(text)
    out: list[tuple[float, float]] = []
    for m in _BLANK_PAIR_RE.finditer(scrubbed):
        try:
            a = float(m.group(1))
            b = float(m.group(2))
        except ValueError:
            continue
        pair = _normalize_pair(a, b)
        if pair:
            out.append(pair)
    return out


def _pairs_from_paren_dims(text: str) -> list[tuple[float, float]]:
    """Pair nearby parenthetical dims; skip unrelated hole callouts farther away."""
    matches = list(_PAREN_DIM_RE.finditer(text or ""))
    out: list[tuple[float, float]] = []
    for i in range(len(matches) - 1):
        m1, m2 = matches[i], matches[i + 1]
        if m2.start() - m1.end() > _PAREN_PAIR_MAX_GAP:
            continue
        pair = _normalize_pair(float(m1.group(1)), float(m2.group(1)))
        if pair:
            out.append(pair)
    return out


def _best_pair(pairs: list[tuple[float, float]]) -> tuple[float, float] | None:
    """Prefer the largest-area blank (overall flat) over small feature pairs."""
    if not pairs:
        return None
    return max(pairs, key=lambda p: p[0] * p[1])


def extract_flat_pattern_dims_from_text(text: str) -> tuple[float, float] | None:
    """
    Return (length_in, width_in) with length >= width, or None.

    Preference order:
      1. Nearby paren callouts after a FLAT PATTERN heading (largest area)
      2. Non-stock blank pairs after FLAT PATTERN
      3. First non-stock blank pair anywhere on the drawing
    """
    if not (text or "").strip():
        return None

    flat_match = _FLAT_HEADING_RE.search(text)
    if flat_match:
        # Full remainder — flat overall dims can sit thousands of chars later
        # (title block / notes between heading and view callouts).
        after = text[flat_match.start() :]
        best = _best_pair(_pairs_from_paren_dims(after))
        if best:
            return best
        best = _best_pair(_pairs_from_blank_callouts(after))
        if best:
            return best

    pairs = _pairs_from_blank_callouts(text)
    if pairs:
        return pairs[0]
    return None


def extract_flat_pattern_dims(pdf_path: Path | str) -> tuple[float, float] | None:
    """Read PDF text and return flat-pattern (L, W) inches, or None."""
    from quote_core.weight import _read_pdf_text

    path = Path(pdf_path)
    if not path.is_file():
        return None
    try:
        text = _read_pdf_text(path)
    except Exception:  # noqa: BLE001
        return None
    return extract_flat_pattern_dims_from_text(text)
