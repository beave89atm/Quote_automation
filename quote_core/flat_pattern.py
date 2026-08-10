"""Extract sheet/plate flat-pattern Length × Width from drawing PDFs.

Shop rule: ItemList Length/Width must be the flat blank size (not formed
envelope, not raw stock plate like ``1/8 x 60 x 120``).
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

# Flat-view parentheticals: (26.85) … (8.49)
_PAREN_DIM_RE = re.compile(r"\(\s*(\d{1,3}(?:\.\d{1,4})?)\s*\)")

_FLAT_HEADING_RE = re.compile(r"FLAT\s+PATTERN", re.IGNORECASE)

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
    """Remove ``1/8 x 60 x 120`` style stock callouts so they are not blanks."""
    return _STOCK_THREE_RE.sub(" ", text or "")


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
    vals = [float(m.group(1)) for m in _PAREN_DIM_RE.finditer(text or "")]
    out: list[tuple[float, float]] = []
    # Consecutive parentheticals near each other form L×W.
    for i in range(len(vals) - 1):
        pair = _normalize_pair(vals[i], vals[i + 1])
        if pair:
            out.append(pair)
    return out


def extract_flat_pattern_dims_from_text(text: str) -> tuple[float, float] | None:
    """
    Return (length_in, width_in) with length >= width, or None.

    Preference order:
      1. Dims in a FLAT PATTERN section (paren callouts, then blank pairs)
      2. First non-stock blank pair anywhere on the drawing
    """
    if not (text or "").strip():
        return None

    flat_match = _FLAT_HEADING_RE.search(text)
    if flat_match:
        # Prefer the chunk around / after the flat-pattern heading.
        section = text[flat_match.start() : flat_match.start() + 2500]
        for pair in _pairs_from_paren_dims(section):
            return pair
        for pair in _pairs_from_blank_callouts(section):
            return pair
        # Whole-doc paren scan still biased by flat heading presence.
        for pair in _pairs_from_paren_dims(text):
            return pair

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
