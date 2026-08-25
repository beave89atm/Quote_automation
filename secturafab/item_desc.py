"""Kyle-format SecturaFAB ItemList Descriptions.

Cad:     ``{PN} - {thk}\" {grade} {W} in x {L} in``
Linear:  ``{PN} - {SKU} - {length}``
Component: purchased name only (no plate dims, not bare PN)
Assembly: ``{PN} - {title}``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PN_RE = re.compile(r"^\d{4,}(?:-\d+[A-Za-z]?)?$", re.IGNORECASE)
_PLATE_DIM_RE = re.compile(
    r"(?i)\b\d+(?:\.\d+)?\s*(?:in|\"|″)?\s*[x×]\s*\d+(?:\.\d+)?\s*(?:in|\"|″)?"
)
_THK_LABELS = (
    (0.125, "1/8"),
    (0.1875, "3/16"),
    (0.25, "1/4"),
    (0.3125, "5/16"),
    (0.375, "3/8"),
    (0.4375, "7/16"),
    (0.5, "1/2"),
    (0.5625, "9/16"),
    (0.625, "5/8"),
    (0.75, "3/4"),
    (0.875, "7/8"),
    (1.0, "1"),
)


def normalize_part_token(raw: str | None) -> str:
    text = (raw or "").strip()
    if text.upper().startswith("PN "):
        text = text[3:].strip()
    return text


def is_bare_part_number(text: str | None, part_key: str | None = None) -> bool:
    token = normalize_part_token(text)
    if not token:
        return True
    if _PN_RE.fullmatch(token):
        return True
    key = normalize_part_token(part_key)
    if key and token.replace("-", "").upper() == key.replace("-", "").upper():
        return True
    return False


def thickness_label(raw: str | float | None) -> str:
    if raw is None or raw == "":
        return ""
    if isinstance(raw, (int, float)):
        val = float(raw)
    else:
        text = str(raw).strip().replace('"', "").replace("″", "")
        text = re.sub(r"(?i)\s*(inches|inch|in)\s*$", "", text).strip()
        if not text:
            return ""
        if re.fullmatch(r"\d+\s*/\s*\d+", text):
            return re.sub(r"\s+", "", text)
        try:
            val = float(text)
        except ValueError:
            return text
    for target, label in _THK_LABELS:
        if abs(val - target) <= 0.012:
            return label
    text = f"{val:.4f}".rstrip("0").rstrip(".")
    return text


def _fmt_in(val: float) -> str:
    text = f"{val:.3f}".rstrip("0").rstrip(".")
    return text or "0"


# Drawing-sheet outlines from quickAddCAD PDF page size (live 1001898-1: 22×28.5).
_SHEET_PAIRS = (
    (8.5, 11.0),
    (11.0, 17.0),
    (17.0, 22.0),
    (18.0, 24.0),
    (22.0, 28.0),
    (22.0, 28.5),
    (22.0, 29.0),
    (22.0, 29.3),
    (22.0, 34.0),
    (24.0, 36.0),
    (34.0, 44.0),
)


def looks_like_drawing_sheet(width_in: float | None, length_in: float | None) -> bool:
    """True when L×W is the PDF page / title-block sheet, not the part flat."""
    try:
        w = float(width_in or 0)
        l = float(length_in or 0)
    except (TypeError, ValueError):
        return False
    if w <= 0 or l <= 0:
        return False
    a, b = (w, l) if w <= l else (l, w)
    if max(w, l) >= 20.0:
        return True
    for sw, sl in _SHEET_PAIRS:
        lo, hi = (sw, sl) if sw <= sl else (sl, sw)
        if abs(a - lo) <= 0.6 and abs(b - hi) <= 0.6:
            return True
    return False


def format_cad_description(
    part_no: str,
    *,
    thickness: str | float | None = None,
    grade: str | None = None,
    width_in: float | None = None,
    length_in: float | None = None,
    noun: str | None = None,
) -> str:
    pn = normalize_part_token(part_no)
    bits = [pn] if pn else []
    mid: list[str] = []
    thk = thickness_label(thickness)
    if thk:
        mid.append(f'{thk}"')
    grade_s = (grade or "").strip()
    if grade_s:
        mid.append(grade_s)
    use_flat = (
        width_in
        and length_in
        and width_in > 0
        and length_in > 0
        and not looks_like_drawing_sheet(width_in, length_in)
    )
    if use_flat:
        mid.append(f"{_fmt_in(float(width_in))} in x {_fmt_in(float(length_in))} in")
    elif (noun or "").strip() and not is_bare_part_number(noun, pn):
        mid.append(format_component_description(noun, part_no=pn) or noun.strip())
    if mid:
        bits.append(" ".join(mid))
    return " - ".join(bits)


def format_linear_description(
    part_no: str,
    *,
    sku: str | None = None,
    length_in: float | None = None,
    noun: str | None = None,
) -> str:
    pn = normalize_part_token(part_no)
    mid = (sku or "").strip()
    if not mid and (noun or "").strip():
        mid = format_component_description(noun, part_no=pn) or noun.strip()
        if is_bare_part_number(mid, pn):
            mid = ""
    parts = [p for p in (pn, mid) if p]
    if length_in and length_in > 0:
        parts.append(_fmt_in(length_in))
    return " - ".join(parts) if parts else ""


def format_component_description(name: str, *, part_no: str | None = None) -> str:
    """Purchased name only — strip plate dims and refuse a bare PN."""
    del part_no
    text = _PLATE_DIM_RE.sub("", (name or "")).strip(" -,\t")
    text = re.sub(r"\s+", " ", text).strip()
    if is_bare_part_number(text):
        return ""
    # Drop a leading PN token so ``50115-7 1 1/4 NPT NIPPLE`` → name.
    parts = text.split(None, 1)
    if len(parts) == 2 and is_bare_part_number(parts[0]):
        return parts[1].strip(" -,")
    return text


def format_assembly_description(part_key: str, title: str | None) -> str:
    pn = normalize_part_token(part_key)
    noun = (title or "").strip()
    if noun and is_bare_part_number(noun, pn):
        noun = ""
    if pn and noun.upper().startswith(pn.upper()):
        rest = noun[len(pn) :].strip(" -")
        if rest:
            return f"{pn} - {rest}"
        return pn
    if pn and noun:
        return f"{pn} - {noun}"
    return pn or noun


def title_from_library_folder(
    folder: Path | str | None,
    *,
    part_key: str | None = None,
) -> str | None:
    from quote_core.drawing_title import title_from_library_folder as _from_folder

    return _from_folder(folder, part_key=part_key)


def title_from_job_title(title: str | None, *, part_key: str | None = None) -> str | None:
    text = (title or "").strip()
    if not text or is_bare_part_number(text, part_key):
        return None
    key = normalize_part_token(part_key)
    if key and text.upper().startswith(key.upper()):
        rest = text[len(key) :].strip(" -")
        return rest.upper() if rest else None
    return text


def item_flat_dims(item: dict[str, Any] | None) -> tuple[float | None, float | None]:
    item = item or {}
    nums: list[float] = []
    for key in ("Width", "FlatWidth", "Length", "FlatLength", "Dim1", "Dim2"):
        raw = item.get(key)
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val > 0.05:
            nums.append(val)
    if len(nums) >= 2:
        w, l = nums[0], nums[1]
        if looks_like_drawing_sheet(w, l):
            return None, None
        return w, l
    return None, None


def item_length_in(item: dict[str, Any] | None) -> float | None:
    item = item or {}
    for key in ("Length", "FlatLength", "LinearLength", "Dim1"):
        try:
            val = float(item.get(key))
        except (TypeError, ValueError):
            continue
        if val > 0.05:
            return val
    return None
