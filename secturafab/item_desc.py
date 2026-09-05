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
_NOUN_WORD_RE = re.compile(r"[A-Z]{3,}")
_NOUN_SKIP = frozenset({"NPT", "THE", "AND", "FOR", "WITH", "LG"})
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


def is_catalog_part_no(raw: str | None) -> bool:
    """True for a shop PN like ``50029-7`` / ``14500-1``, not ``1`` or ``3/4``."""
    token = normalize_part_token(raw).rstrip(".,;:")
    return bool(_PN_RE.fullmatch(token))


def _noun_key_words(text: str | None) -> frozenset[str]:
    words = _NOUN_WORD_RE.findall(str(text or "").upper())
    return frozenset(w for w in words if w not in _NOUN_SKIP)


def match_bom_part_no(
    description: str | None,
    bom_rows: list[dict[str, Any]] | None,
) -> str | None:
    """Return the dashed BOM PN for an ItemList Description (never a first-word guess)."""
    text = str(description or "").strip()
    rows = [r for r in (bom_rows or []) if isinstance(r, dict)]
    dashed: list[str] = []
    for row in rows:
        pn = str(row.get("part_no") or row.get("part_number") or "").strip()
        if is_catalog_part_no(pn):
            dashed.append(normalize_part_token(pn))

    first = text.split()[0].rstrip(".,;:") if text.split() else ""
    if is_catalog_part_no(first):
        from secturafab.qty_ops import normalize_part_key

        key = normalize_part_key(first)
        for pn in dashed:
            if normalize_part_key(pn) == key:
                return pn
        # FileName stem ``14500`` / GET ``14500`` → unique dashed BOM ``14500-1``.
        # Leave ambiguous bases (29860-3 and 29860-4) unmatched here.
        base_hits = [
            pn
            for pn in dashed
            if pn.rsplit("-", 1)[0].upper() == first.upper()
        ]
        if len(base_hits) == 1:
            return base_hits[0]
        return normalize_part_token(first)

    for pn in dashed:
        if re.search(rf"(?i)(?<!\d){re.escape(pn)}(?!\d)", text):
            return pn

    item_words = _noun_key_words(text)
    if not item_words:
        return None
    best_pn: str | None = None
    best_score = 0
    for row in rows:
        pn = str(row.get("part_no") or row.get("part_number") or "").strip()
        if not is_catalog_part_no(pn):
            continue
        words = _noun_key_words(str(row.get("description") or ""))
        if not words:
            continue
        overlap = words & item_words
        if not overlap:
            continue
        score = len(overlap)
        if words == item_words:
            score += 20
        elif words <= item_words:
            score += 10
        elif item_words <= words:
            score += 1
        if score > best_score:
            best_score = score
            best_pn = pn
    if best_score >= 2 or (best_score >= 1 and best_pn and len(item_words) == 1):
        return best_pn
    return None


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
    for sw, sl in _SHEET_PAIRS:
        lo, hi = (sw, sl) if sw <= sl else (sl, sw)
        if abs(a - lo) <= 0.6 and abs(b - hi) <= 0.6:
            return True
    return False


def looks_like_page_outline(width_in: float | None, length_in: float | None) -> bool:
    """True for PDF crop / SCALE 1:N artifacts (1×2, 1×16), not the child flat."""
    try:
        w = float(width_in or 0)
        l = float(length_in or 0)
    except (TypeError, ValueError):
        return False
    if w <= 0 or l <= 0:
        return False
    a, b = (w, l) if w <= l else (l, w)
    # Live 1007049-1: 1007013 landed 1×2 (drawing ~5.25×5.75); 1007012 landed 1×16
    # (drawing ~14.625×7.375). Min side ≈ 1 in is the page/scale outline.
    if 0.90 <= a <= 1.10:
        return True
    return False


def usable_cad_flats(width_in: float | None, length_in: float | None) -> bool:
    """True when L×W is a plate blank, not a sheet or 1×N page outline."""
    return _pair_ok(width_in, length_in)


_CAD_THK_RE = re.compile(r'(?P<thk>\d+\s*/\s*\d+|\d+(?:\.\d+)?)\s*"')
_CAD_GRADE_RE = re.compile(
    r"\b(?P<grade>A\s*572(?:\s+Grade\s+\d+)?|A\s*36|A\s*513|A\s*500|A\s*656(?:\s+Grade\s+\d+)?|100K|5052(?:-H32)?)\b",
    re.IGNORECASE,
)
_CAD_FLAT_RE = re.compile(
    r"(?P<w>\d+(?:\.\d+)?)\s*in\s*x\s*(?P<l>\d+(?:\.\d+)?)\s*in",
    re.IGNORECASE,
)


def parse_cad_desc_fields(description: str | None) -> dict[str, Any]:
    """Read thk / grade / flats already on a Kyle Cad Description onto item fields."""
    text = str(description or "")
    out: dict[str, Any] = {}
    m = _CAD_THK_RE.search(text)
    if m:
        out["thickness"] = re.sub(r"\s+", "", m.group("thk"))
    g = _CAD_GRADE_RE.search(text)
    if g:
        out["material"] = re.sub(r"\s+", " ", g.group("grade")).strip()
    flat = _CAD_FLAT_RE.search(text)
    if flat:
        try:
            w = float(flat.group("w"))
            length = float(flat.group("l"))
        except (TypeError, ValueError):
            w = length = 0.0
        if w > 0 and length > 0 and _pair_ok(w, length):
            out["width_in"] = w
            out["length_in"] = length
    return out


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
        and _pair_ok(width_in, length_in)
    )
    extra = ""
    if (noun or "").strip() and not is_bare_part_number(noun, pn):
        extra = format_component_description(noun, part_no=pn) or noun.strip()
    if use_flat:
        mid.append(f"{_fmt_in(float(width_in))} in x {_fmt_in(float(length_in))} in")
        if extra and extra.upper() not in " ".join(mid).upper():
            mid.append(extra)
    elif extra:
        mid.append(extra)
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
    """Purchased noun only — strip plate dims and refuse a bare PN."""
    text = _PLATE_DIM_RE.sub("", (name or "")).strip(" -,\t")
    text = re.sub(r"\s+", " ", text).strip()
    if is_bare_part_number(text):
        return ""
    # Drop a leading PN token so ``50115-7 1 1/4 NPT NIPPLE`` → name.
    parts = text.split(None, 1)
    if len(parts) == 2 and is_bare_part_number(parts[0]):
        return parts[1].strip(" -,")
    pn = normalize_part_token(part_no)
    # Only strip a real catalog PN — never a leading ``1`` from ``1 1/4 …``.
    if pn and is_catalog_part_no(pn) and text.upper().startswith(pn.upper()):
        rest = text[len(pn) :].strip(" -")
        return rest
    return text


def format_component_line(part_no: str, name: str) -> str:
    """Kyle Component line: ``{PN} - {noun}``."""
    pn = normalize_part_token(part_no)
    noun = format_component_description(name, part_no=pn)
    if pn and is_catalog_part_no(pn) and noun:
        return f"{pn} - {noun}"
    return noun or (pn if is_catalog_part_no(pn) else "")


def format_quote_header_description(title: str | None, *, part_key: str | None = None) -> str:
    """Quote Description is the weldment title only — never the part number."""
    from quote_core.drawing_title import (
        is_drawing_boilerplate_title,
        is_material_callout_title,
    )

    noun = (title or "").strip()
    pn = normalize_part_token(part_key)
    if (
        not noun
        or is_bare_part_number(noun, pn)
        or is_drawing_boilerplate_title(noun)
        or is_material_callout_title(noun)
    ):
        return ""
    if pn and noun.upper().startswith(pn.upper()):
        noun = noun[len(pn) :].strip(" -")
    noun = re.sub(r"\s+", " ", noun).strip(" -")
    if not noun or is_bare_part_number(noun, pn) or is_drawing_boilerplate_title(noun):
        return ""
    return noun


def format_assembly_description(part_key: str, title: str | None) -> str:
    from quote_core.drawing_title import is_drawing_boilerplate_title

    pn = normalize_part_token(part_key)
    noun = (title or "").strip()
    if noun and (is_bare_part_number(noun, pn) or is_drawing_boilerplate_title(noun)):
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
    from quote_core.drawing_title import is_drawing_boilerplate_title

    text = (title or "").strip()
    if not text or is_bare_part_number(text, part_key) or is_drawing_boilerplate_title(text):
        return None
    key = normalize_part_token(part_key)
    if key and text.upper().startswith(key.upper()):
        rest = text[len(key) :].strip(" -")
        if not rest or is_drawing_boilerplate_title(rest):
            return None
        return rest.upper()
    return text


_GENERIC_BOM_LEAD = {
    "PLATE",
    "TUBE",
    "ANGLE",
    "BAR",
    "PIPE",
    "NUT",
    "BOLT",
    "WASHER",
    "CAP",
    "PIN",
    "RAIL",
    "ARM",
    "GUARD",
    "BRACKET",
    "CHANNEL",
    "SHEET",
    "GUSSET",
    "STIFFENER",
}


def title_from_bom_family(bom_rows: list[dict] | None) -> str | None:
    """PEDESTAL TOP PLATE / PEDESTAL TUBE / … → ``PEDESTAL WELDMENT``."""
    leads: list[str] = []
    for row in bom_rows or []:
        noun = str(row.get("description") or "").strip()
        if not noun:
            continue
        if re.search(r"\bWELDMENT\b", noun, re.IGNORECASE):
            cleaned = re.sub(r"\s+", " ", noun).strip()
            return cleaned.upper()
        first = noun.split()[0].upper().strip("-,")
        if (
            first
            and first not in _GENERIC_BOM_LEAD
            and not is_bare_part_number(first)
            and first.isalpha()
        ):
            leads.append(first)
    if len(leads) < 3:
        return None
    from collections import Counter

    word, n = Counter(leads).most_common(1)[0]
    if n < 3:
        return None
    return f"{word} WELDMENT"


_LXW_NUM = r"(\d+\s+\d+/\d+|\d+-\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
_LXW_RE = re.compile(
    rf"(?<![\d.]){_LXW_NUM}\s*[\"″']?\s*(?:in(?:ch(?:es)?)?)?\s*[xX×]\s*"
    rf"{_LXW_NUM}\s*[\"″']?(?:\s*in(?:ch(?:es)?)?)?",
)
_LXW_TRIPLE_RE = re.compile(
    rf"(?<![\d.]){_LXW_NUM}\s*[\"″']?\s*[xX×]\s*"
    rf"{_LXW_NUM}\s*[\"″']?\s*[xX×]\s*{_LXW_NUM}",
)
_LXW_LABELED_RE = re.compile(
    rf"(?:OVERALL|BLANK|PLATE\s*SIZE|FINISHED\s*SIZE)[^\n]{{0,40}}?"
    rf"{_LXW_NUM}\s*[\"″']?\s*[xX×]\s*{_LXW_NUM}",
    re.IGNORECASE,
)


def _as_flat(val: Any) -> float | None:
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if num <= 0.05:
        return None
    return num


def _lxw_num(raw: str | None) -> float | None:
    text = str(raw or "").strip().replace("-", " ")
    if not text:
        return None
    try:
        if " " in text and "/" in text:
            whole, frac = text.split(None, 1)
            num, den = frac.split("/", 1)
            return float(whole) + float(num) / float(den)
        if "/" in text:
            num, den = text.split("/", 1)
            den_f = float(den)
            if den_f == 0:
                return None
            return float(num) / den_f
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _pair_ok(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    if a <= 0.25 or b <= 0.25 or max(a, b) > 240:
        return False
    if looks_like_drawing_sheet(a, b) or looks_like_page_outline(a, b):
        return False
    return True


def _best_flat_pair(pairs: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not pairs:
        return None
    return max(pairs, key=lambda p: float(p[0]) * float(p[1]))


def parse_plate_flats(text: str | None) -> tuple[float | None, float | None]:
    """L×W from takeoff / LOM / drawing text. Reject PDF sheet / 1×N outlines."""
    blob = str(text or "")
    labeled: list[tuple[float, float]] = []
    for match in _LXW_LABELED_RE.finditer(blob):
        a = _lxw_num(match.group(1))
        b = _lxw_num(match.group(2))
        if _pair_ok(a, b):
            labeled.append((float(a), float(b)))
    hit = _best_flat_pair(labeled)
    if hit:
        return hit
    triples: list[tuple[float, float]] = []
    for match in _LXW_TRIPLE_RE.finditer(blob):
        thk = _lxw_num(match.group(1))
        a = _lxw_num(match.group(2))
        b = _lxw_num(match.group(3))
        if thk is not None and thk <= 1.5 and _pair_ok(a, b):
            triples.append((float(a), float(b)))
    hit = _best_flat_pair(triples)
    if hit:
        return hit
    unlabeled: list[tuple[float, float]] = []
    for match in _LXW_RE.finditer(blob):
        a = _lxw_num(match.group(1))
        b = _lxw_num(match.group(2))
        if not _pair_ok(a, b):
            continue
        unlabeled.append((float(a), float(b)))
    hit = _best_flat_pair(unlabeled)
    if not hit:
        return None, None
    return hit


def flats_from_mapping(row: dict[str, Any] | None) -> tuple[float | None, float | None]:
    """Takeoff / LOM / FileList row dims (not a 1001898-only lock)."""
    row = row or {}
    pairs = (
        ("width_in", "length_in"),
        ("Width", "Length"),
        ("width", "length"),
        ("W", "L"),
        ("Stock_X", "Stock_Y"),
        ("FlatWidth", "FlatLength"),
        ("blank_width", "blank_length"),
    )
    for wk, lk in pairs:
        w = _as_flat(row.get(wk))
        length = _as_flat(row.get(lk))
        if w and length and _pair_ok(w, length):
            return w, length
    blank = row.get("blank") or row.get("Blank") or []
    if isinstance(blank, (list, tuple)) and len(blank) >= 2:
        a = _as_flat(blank[0])
        b = _as_flat(blank[1])
        if a and b and _pair_ok(a, b):
            return b, a
    parsed = parse_plate_flats(
        " ".join(
            str(row.get(k) or "")
            for k in (
                "description",
                "Description",
                "joint_notes",
                "notes",
                "noun",
                "size",
                "Size",
                "blank_size",
                "overall",
            )
        )
    )
    if parsed[0] and parsed[1]:
        return parsed
    return item_flat_dims(row)


def _takeoff_row_matches(part_no: str, row: dict[str, Any]) -> bool:
    want = normalize_part_token(part_no)
    if not want:
        return False
    token = " ".join(
        str(row.get(k) or "")
        for k in (
            "part_no",
            "part_number",
            "name",
            "Name",
            "Description",
            "description",
        )
    )
    if want in token or normalize_part_token(token) == want:
        return True
    row_pn = normalize_part_token(
        str(row.get("part_no") or row.get("part_number") or row.get("name") or "")
    )
    if not row_pn:
        return False
    if want == row_pn:
        return True
    want_base = want.rsplit("-", 1)[0] if "-" in want else want
    row_base = row_pn.rsplit("-", 1)[0] if "-" in row_pn else row_pn
    if want_base and row_base and want_base == row_base:
        return True
    return want == row_base or row_pn == want_base


def iter_takeoff_plate_rows(takeoff: dict[str, Any] | None) -> list[dict[str, Any]]:
    """LOM / takeoff Cad plate rows (top-level and fitup_drivers)."""
    if not isinstance(takeoff, dict):
        return []
    bags: list[Any] = []
    for key in ("items", "sizes", "gussets", "plates", "components"):
        inner = takeoff.get(key)
        if isinstance(inner, list):
            bags.extend(inner)
    fitup = takeoff.get("fitup_drivers")
    if isinstance(fitup, dict):
        for key in ("plates", "components"):
            inner = fitup.get(key)
            if isinstance(inner, list):
                bags.extend(inner)
    return [it for it in bags if isinstance(it, dict)]


def takeoff_plate_row(
    takeoff: dict[str, Any] | None,
    part_no: str,
) -> dict[str, Any] | None:
    """Matching LOM/takeoff plate for a Cad PN (dashed or bare)."""
    pn = normalize_part_token(part_no)
    if not pn:
        return None
    for it in iter_takeoff_plate_rows(takeoff):
        if _takeoff_row_matches(pn, it):
            return it
    return None


def flats_from_takeoff(
    takeoff: dict[str, Any] | None,
    part_no: str,
) -> tuple[float | None, float | None]:
    pn = normalize_part_token(part_no)
    if not pn or not isinstance(takeoff, dict):
        return None, None
    for it in iter_takeoff_plate_rows(takeoff):
        if not _takeoff_row_matches(pn, it):
            continue
        got = flats_from_mapping(it)
        if got[0] and got[1]:
            return got
    return None, None


def flats_from_drawing(pdf_path: Path | None) -> tuple[float | None, float | None]:
    if pdf_path is None or not Path(pdf_path).is_file():
        return None, None
    try:
        from quote_core.weight import _read_pdf_text

        return parse_plate_flats(_read_pdf_text(Path(pdf_path)))
    except Exception:  # noqa: BLE001 — drawing OCR is optional
        return None, None


def resolve_cad_plate_flats(
    part_no: str,
    *,
    bom_row: dict[str, Any] | None = None,
    takeoff: dict[str, Any] | None = None,
    pdf_path: Path | None = None,
    noun: str = "",
    locked: dict[str, Any] | None = None,
) -> tuple[float | None, float | None]:
    """L×W for Image Files. Lock table is optional, never the only source."""
    for source in (
        flats_from_mapping(bom_row),
        flats_from_takeoff(takeoff, part_no),
        flats_from_drawing(pdf_path),
        parse_plate_flats(noun),
        flats_from_mapping(locked),
    ):
        if source[0] and source[1]:
            return source
    return None, None


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
        if not _pair_ok(w, l):
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
