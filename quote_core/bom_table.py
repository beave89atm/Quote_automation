"""Table-first LIST OF MATERIAL / BOM grid parsing.

Time (and similar) weldment BOMs are a QTY | ITEM | PART NO. | DESCRIPTION
grid — not loose page text. Item balloons are one or two letters (A, Z, AA,
BB, BC) and skip I and O as letters, not as missing data.

This module reads **cells** (or positioned words clustered into cells). It
does not pad missing rows from drawing-library child files / sub-weldments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

# Time-style balloons skip I and O in every position (A–Z, AA–AZ, BA…).
_SKIP_ITEM_LETTERS = frozenset("IO")
_ITEM_TOKEN_RE = re.compile(r"^[A-Z]{1,2}$")
_QTY_TOKEN_RE = re.compile(r"^\d{1,3}$")
_DASH_COL_RE = re.compile(r"^\[?-([1-4])\]?$")
_BARE_DASH_RE = re.compile(r"^[-–—]?([1-4])$")
_EMPTY_QTY = frozenset({"-", "—", "–", ".", "·", "", "N/A", "NA"})

_TITLE_RE = re.compile(
    r"\b(?:LIST\s+OF\s+MATERIAL|PARTS\s+LIST|BILL\s+OF\s+MATERIALS?|\bBOM\b)\b",
    re.IGNORECASE,
)
_GRID_HEADER_RE = re.compile(
    r"(?:QTY|ITEM|TEM).{0,48}(?:PART\s*NO\.?|PART\s*NUMBER|P/?N).{0,40}DESC",
    re.IGNORECASE | re.DOTALL,
)
_MULTI_QTY_HEADER_RE = re.compile(
    r"-4.{0,16}-3.{0,16}-2.{0,16}-1.{0,24}ITEM.{0,24}PART",
    re.IGNORECASE | re.DOTALL,
)
_DASH_QTY_HEADER_RE = re.compile(
    r"-2.{0,20}-1.{0,24}ITEM.{0,24}PART",
    re.IGNORECASE | re.DOTALL,
)

_HEADER_QTY = frozenset({"QTY", "QTY.", "QUANTITY"})
_HEADER_ITEM = frozenset({"ITEM", "ITEM.", "BALLOON", "ID", "FIND"})
_HEADER_PART = frozenset(
    {"PART", "PART NO", "PART NO.", "PART NUMBER", "P/N", "PN", "PARTNO"}
)
_HEADER_DESC = frozenset({"DESC", "DESCRIPTION", "DESCR", "MATERIAL"})
_HEADER_SKIP = frozenset(
    {
        "LIST",
        "OF",
        "MATERIAL",
        "REV",
        "REMARKS",
        "WEIGHT",
        "WT",
        "LBM",
        "NOTES",
        "SHEET",
    }
)

# OCR / native lines with no pipes: ``2 BB 102727-4 TUBE, ROUND``
_ROW_BLOB_RE = re.compile(
    r"^(?:(?P<qty>\d{1,3})\s+)?"
    r"(?P<item>[A-Za-z]{1,2})\s+"
    r"(?P<part>\d{4,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?)\s*"
    r"(?P<desc>.*)$",
)
# finditer: harvest every qty/item/part even when OCR glues several rows together
_QTY_ITEM_PART_FIND_RE = re.compile(
    r"(?<!\d)(?P<qty>\d{1,3})\s+"
    r"(?P<item>[A-Za-z]{1,2})\s+"
    r"(?P<part>\d{4,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?)",
    re.IGNORECASE,
)
# Live page-1 strips often lose qty and glue leftover OCR onto the item:
# ``BBD 02727-4 TUBE, ROUND``  → BB + 102727-4
_STRIP_LEAD_RE = re.compile(
    r"^\s*(?:(?P<qty>\d{1,2})\s+)?"
    r"(?P<item>[A-Za-z]{1,3})"
    r"(?P<rest>.*)$"
)
_DASHED_PN_RE = re.compile(
    r"(?P<base>\d{4,7})\s*[-–—=]\s*(?P<suf>\d{1,3}[A-Za-z]?)"
)
_BARE_PN_RE = re.compile(r"(?<![\d])(?P<base>\d{5,7})(?![\d-])")
# Broken OCR: spaces in the stem, O/I as digits, missing dash.
_MANGLED_DASHED_PN_RE = re.compile(
    r"(?P<base>[\dOIl]{4,7}(?:\s+[\dOIl]{1,3})*)\s*[-–—=]\s*(?P<suf>[\dOIl]{1,3}[A-Za-z]?)",
    re.IGNORECASE,
)
_GLUED_ITEM_PN_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<item>[A-Za-z]{1,2})(?P<base>\d{5,7})"
    r"(?:\s*[-–—=]\s*(?P<suf>\d{1,3}[A-Za-z]?))?",
)
_KNOWN_BB_PART = "102727-4"
# Title-block weldment drawing numbers (P904225-1) — not item P + 904225-1.
_P_PREFIX_WELDMENT_PN_RE = re.compile(
    r"(?<![A-Za-z0-9])P\d{5,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?\b",
    re.IGNORECASE,
)
_ITEM_WORD_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z]{2}[2-9Dd]|[A-Za-z]{1,2}[2-9]|[A-Za-z]{1,3})(?![A-Za-z0-9])"
)
# Item (optional glued qty) then part on the same strip or adjacent bands.
_ITEM_PART_ANY_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<item>[A-Za-z]{1,2})(?P<glued>[2-9Dd])?"
    r"(?![A-Za-z])\s{0,16}"
    r"(?P<part>\d{4,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?)",
    re.IGNORECASE,
)
_BLEED_KIND_RE = re.compile(
    r"\b(PLATE|RAIL|TUBE|CAP|HOOK|GRATING|ICAP)\b", re.IGNORECASE
)
_PART_KIND_NOUN_RE = re.compile(
    r"\b(PLATE|RAIL|TUBE|CAP|HOOK|GRATING|ICAP|GATE|HOSE|SUPPORT|GUIDE|"
    r"ANGLE|CLIP|FABRICATION)\b",
    re.IGNORECASE,
)
_TUBE_ROUND_RE = re.compile(r"TUBE\s*,?\s*ROUND", re.IGNORECASE)
_STRIP_HEADER_WORDS = frozenset(
    {
        "QTY",
        "ITEM",
        "TEM",
        "PART",
        "NO",
        "DESC",
        "DESCRIPTION",
        "LIST",
        "OF",
        "MATERIAL",
        "REV",
        "SHEET",
    }
)
# Whole-word OCR leftovers — not balloons, even if the first 1–2 letters are.
_DESC_NOISE_WORDS = frozenset(
    {
        "CAP",
        "TOP",
        "END",
        "BAR",
        "LEG",
        "ARM",
        "PIN",
        "NUT",
        "BOW",
        "TUBE",
        "RAIL",
        "HOOK",
        "ICAP",
        "PLATE",
        "ROUND",
        "FRONT",
        "OUTER",
        "INNER",
        "CENTER",
        "BACK",
        "MIDDLE",
        "SUPPORT",
        "GRATING",
        "HORIZONTAL",
        "VERTICAL",
        "BOTTOM",
        "COMPONENT",
        "WELDMENT",
        "PLATFORM",
    }
)
_HEADER_FOUND_NOTE = (
    "LIST OF MATERIAL header found but no table rows parsed "
    "— flag review; do not use whole-page regex or pad from nested files"
)
# Time 102728-1 is 51 rows. A 3-row decoy LOM must not win.
TALL_TABLE_MIN_ROWS = 40
# Reject a nested 3-row LOM when another page rendered a taller grid.
SHORT_TABLE_REJECT = 10


def time_item_letters(*, through: str = "BC") -> list[str]:
    """A–Z skipping I/O, then AA–AZ skipping I/O, then BA, BB, BC, …"""
    last = (through or "Z").strip().upper()
    out: list[str] = []
    for token in _iter_item_letters():
        out.append(token)
        if token == last:
            return out
    return out


def _iter_item_letters() -> Iterable[str]:
    singles = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in _SKIP_ITEM_LETTERS]
    for c in singles:
        yield c
    for first in singles:
        for second in singles:
            yield first + second


def is_material_list_item(token: str | None) -> bool:
    """True for A, Z, AA, BB, BC — never I or O in any position."""
    text = str(token or "").strip().upper()
    if not _ITEM_TOKEN_RE.fullmatch(text):
        return False
    return all(ch not in _SKIP_ITEM_LETTERS for ch in text)


def item_sort_key(item: str) -> tuple[int, str]:
    text = str(item or "").strip().upper()
    return (len(text), text)


def text_has_material_list_grid(text: str | None) -> bool:
    blob = text or ""
    if _MULTI_QTY_HEADER_RE.search(blob):
        return True
    if _GRID_HEADER_RE.search(blob):
        return True
    if _TITLE_RE.search(blob) and re.search(
        r"\b(?:ITEM|TEM)\b.{0,40}\bPART\b", blob, flags=re.IGNORECASE | re.DOTALL
    ):
        return True
    return False


def time_balloon_set(*, through: str = "BC") -> set[str]:
    return set(time_item_letters(through=through))


def score_material_list(bom: Any) -> tuple:
    """
    Higher is better. Prefer many Time balloons (A, AA, BB), not a 3-row decoy.

    A complete cell table (51-ish + BB) beats a strip harvest that picked up
    title-block / page-bait PNs. Live OCR strips all score complete_cell=0,
    so first+retry union still wins on unique Time PNs.
    """
    rows = list(getattr(bom, "rows", None) or [])
    seq = time_balloon_set(through="BC")
    items = [str(r.item).upper() for r in rows if r.item]
    seq_hits = sum(1 for i in items if i in seq)
    two_letter = sum(1 for i in items if len(i) == 2 and i in seq)
    has_bb = 1 if "BB" in items else 0
    has_pn = 1 if any(str(r.part_no) == "102727-4" for r in rows) else 0
    pieces = int(getattr(bom, "piece_count", 0) or 0)
    cellish = sum(
        1
        for r in rows
        if "strip" not in str(getattr(r, "source", ""))
        and "harvest" not in str(getattr(r, "source", ""))
    )
    complete_cell = 1 if cellish >= TALL_TABLE_MIN_ROWS and has_bb and has_pn else 0
    return (complete_cell, seq_hits, two_letter, has_bb, has_pn, cellish, pieces)


def pick_best_material_list(candidates: Sequence[Any], *, min_rows: int = TALL_TABLE_MIN_ROWS):
    """
    Choose the tall Time grid over a short decoy LOM. Does not invent rows.

    A nested 3-row LIST OF MATERIAL (e.g. 102711-1 cable tube) must not win
    when another page's render has a taller QTY/ITEM/PART grid.
    """
    scored = [c for c in candidates if c is not None]
    if not scored:
        return None

    def parsed_n(c: Any) -> int:
        return len(getattr(c, "rows", None) or [])

    def grid_n(c: Any) -> int:
        return int(getattr(c, "grid_row_count", 0) or 0)

    tall = [c for c in scored if parsed_n(c) >= min_rows]
    if tall:
        tall.sort(key=score_material_list, reverse=True)
        return tall[0]

    max_grid = max(grid_n(c) for c in scored)
    if max_grid >= SHORT_TABLE_REJECT:
        grid_cands = [c for c in scored if grid_n(c) >= max(SHORT_TABLE_REJECT, max_grid)]
        if not grid_cands:
            grid_cands = [c for c in scored if grid_n(c) == max_grid]
        grid_cands.sort(key=lambda c: (grid_n(c), score_material_list(c)), reverse=True)
        chosen = grid_cands[0]
        short = [c for c in scored if 0 < parsed_n(c) < SHORT_TABLE_REJECT]
        if short and parsed_n(chosen) < SHORT_TABLE_REJECT:
            chosen.notes = list(chosen.notes) + [
                f"Rejected {parsed_n(short[0])}-row LOM (nested sheet) because "
                f"another page has a taller QTY/ITEM/PART grid "
                f"({max_grid} row bands) — flag review; do not invent rows"
            ]
        return chosen

    mid = [c for c in scored if parsed_n(c) >= SHORT_TABLE_REJECT]
    if mid:
        mid.sort(key=score_material_list, reverse=True)
        return mid[0]
    scored.sort(
        key=lambda c: (
            score_material_list(c),
            1 if material_list_header_seen(c) else 0,
            parsed_n(c),
            grid_n(c),
        ),
        reverse=True,
    )
    return scored[0]


def _split_glued_item_token(raw_item: str) -> tuple[str, str]:
    """``BBD`` / ``BB2`` → (``BB``, leftover). Prefer ``_split_glued_item_qty``."""
    item, _qty = _split_glued_item_qty(raw_item)
    token = str(raw_item or "").strip().upper()
    if not item:
        return "", ""
    leftover = token[len(item) :] if token.startswith(item) else ""
    if leftover in {"2", "3", "4", "5", "6", "7", "8", "9", "D"}:
        leftover = ""
    return item, leftover


def _split_glued_item_qty(raw_item: str) -> tuple[str, int | None]:
    """
    Glued item+qty: ``BB2`` → (BB, 2), ``BBD`` → (BB, 2).

    ``D`` is the live OCR of qty 2 on ``BBD 02727-4``. ``BD`` stays item BD
    (valid two-letter balloon), not B + D.
    """
    token = str(raw_item or "").strip().upper()
    if is_material_list_item(token):
        return token, None
    m = re.fullmatch(r"([A-Z]{1,2})([2-9])", token)
    if m and is_material_list_item(m.group(1)):
        qty = int(m.group(2))
        if qty <= 20:
            return m.group(1), qty
    m = re.fullmatch(r"([A-Z]{2})D", token)
    if m and is_material_list_item(m.group(1)):
        return m.group(1), 2
    if len(token) == 3 and is_material_list_item(token[:2]):
        return token[:2], None
    return "", None


def recover_time_part_no(raw: str | None, *, item: str | None = None) -> str | None:
    """
    Recover Time PNs from OCR: ``02727-4`` → ``102727-4``,
    ``1102726-1`` → ``102726-1``. Keep bare catalog numbers (``460330``).
    """
    from quote_core.bom import normalize_part_no

    text = str(raw or "").strip()
    if not text:
        return None
    dashed = _DASHED_PN_RE.search(text)
    if dashed:
        base = dashed.group("base")
        suf = dashed.group("suf").upper()
        part = f"{base}-{suf}"
        if len(base) == 5 and base.startswith("0"):
            prefixed = f"1{base}-{suf}"
            # Only when the result is a 6-digit 10xxxx Time PN (00177-2, 02727-4).
            if prefixed.startswith("10") and len(prefixed.split("-")[0]) == 6:
                part = prefixed
        elif len(base) == 7 and base.startswith("11") and base[1:].startswith("10"):
            # 1100373-2 → 100373-2; 1102726-1 → 102726-1 (extra leading 1)
            part = f"{base[1:]}-{suf}"
        elif len(base) == 6 and base.startswith("1") and not base.startswith("10"):
            # 133688-10 → 33688-10 (digits already complete; extra 1)
            part = f"{base[1:]}-{suf}"
        elif len(base) == 7 and base.startswith("1") and not base.startswith("10"):
            # 1432670-n — extra 1 on an already-complete 6-digit stem.
            part = f"{base[1:]}-{suf}"
        if item and str(item).upper() == "BB" and part in {_KNOWN_BB_PART, "02727-4"}:
            return _KNOWN_BB_PART
        return part
    bare = _BARE_PN_RE.search(text)
    if bare:
        base = bare.group("base")
        if len(base) == 7 and base.startswith("11") and base[1:].startswith("10"):
            return base[1:]
        if len(base) == 7 and base.startswith("1") and not base.startswith("10"):
            return base[1:]
        # Do not invent a dash on 460330 / 460320. Do not prefix complete stems.
        return base
    return normalize_part_no(text)


def is_glued_p_prefix_weldment_pn(raw: str | None) -> bool:
    """True for title-block ``P904225-1``, not item G + child ``P904226-1``."""
    text = str(raw or "")
    m = _P_PREFIX_WELDMENT_PN_RE.search(text)
    if m:
        if re.search(r"(?<![A-Za-z0-9])P\s+\d{5,7}", text, flags=re.IGNORECASE):
            m = None
        else:
            before = text[: m.start()]
            for token in re.findall(
                r"(?<![A-Za-z0-9])([A-Za-z]{1,2})(?![A-Za-z0-9])", before
            ):
                if is_material_list_item(token):
                    return False
            return True
    # Spaced title OCR ``P 904225-1 WELDMENT`` — not a real balloon.
    spaced = re.search(
        r"(?<![A-Za-z0-9])P\s+(\d{5,7}(?:\s*[-–—=]\s*\d{1,3})?)",
        text,
        flags=re.IGNORECASE,
    )
    if spaced and _TITLE_DRAWING_CTX_RE.search(text):
        return True
    return False


def _is_time_like_part(part: str | None) -> bool:
    text = str(part or "").strip()
    if re.search(r"\d{4,7}-\d", text):
        return True
    return bool(re.fullmatch(r"\d{5,7}", text))


def _is_five_digit_bare_pn(part: str | None) -> bool:
    """56657 / 73049 class — not a dashed Time PN (94560 GATE still has a noun)."""
    return bool(re.fullmatch(r"\d{5}", str(part or "").strip()))


def _is_dashed_time_pn(part: str | None) -> bool:
    """LOM part numbers like 1004806-1 / 28275-2 / 6993-1. Always keep these."""
    return bool(re.fullmatch(r"\d{4,7}-\d{1,3}", str(part or "").strip()))


def _looks_like_garbled_eco(text: str | None) -> bool:
    """OCR smash of ADDED CONFIGURATION / PROPERTY / FIRST RELEASE (73207 live)."""
    blob = re.sub(r"[^a-z]", "", str(text or "").lower())
    if len(blob) < 6:
        return False
    return any(
        needle in blob
        for needle in (
            "config",
            "conric",
            "confic",
            "curat",
            "uranon",
            "figur",
            "avoeos",
            "added",
            "releas",
            "proper",
        )
    )


def _is_eco_or_title_block_row(
    part: str | None,
    desc: str | None,
    raw: str = "",
    window: str = "",
) -> bool:
    """Drop 5-digit bare ECO/title-block junk. Dashed Time PNs always stay.

    Scope: this strip or a neighbor band only. Page-title PROPERTY OF TIME
    is on every Time drawing and must not wipe 1004806-1 / 28275-1.
    """
    if raw and _is_title_block_drawing_line(raw, raw):
        return True
    if _is_dashed_time_pn(part):
        return False
    if not _is_five_digit_bare_pn(part):
        return False
    same = f"{part or ''} {desc or ''} {raw}"
    has_kind = bool(_PART_KIND_NOUN_RE.search(same))
    # 97879 with no TUBE/GATE/… is title-block noise. 94560 GATE stays.
    if not has_kind:
        return True
    if _TITLE_ECO_NOISE_RE.search(same) or _looks_like_garbled_eco(same):
        return True
    if (
        window
        and not has_kind
        and (
            _TITLE_ECO_NOISE_RE.search(window) or _looks_like_garbled_eco(window)
        )
    ):
        return True
    return False


def _looks_like_column_index_qty(qty: int) -> bool:
    """2-digit qty 10–20 is dash-column / grid-index bleed unless glued item+qty."""
    return 10 <= int(qty) <= 20


_TITLE_BLOCK_CTX_RE = re.compile(
    r"\b(?:WELDMENT|SHEET|TIME\s+MANUFACTURING|DWG|DRAWING\s+NO)\b",
    re.IGNORECASE,
)
# SHEET sits next to the LOM (14149-1 / 103535-1). Do not treat it as the title.
_TITLE_DRAWING_CTX_RE = re.compile(
    r"\b(?:WELDMENT|TIME\s+MANUFACTURING|DWG|DRAWING\s+NO)\b",
    re.IGNORECASE,
)
# P904225-1 or spaced title OCR ``P 904225-1``.
_SPACED_P_PREFIX_PN_RE = re.compile(
    r"(?<![A-Za-z0-9])P\s*(\d{5,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?)\b",
    re.IGNORECASE,
)
# Title line: WELDMENT … PN … TIME / DWG — not a LOM desc that says WELDMENT.
_TITLE_WELDMENT_SHOP_PN_RE = re.compile(
    r"\bWELDMENT\b.{0,40}?(P?\d{5,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?)"
    r".{0,32}(?:TIME\s+MANUFACTURING|DWG(?:\s+NO)?)",
    re.IGNORECASE | re.DOTALL,
)
# Exact title drawing number — not every dashed PN on a titleish page blob.
_TITLE_DWG_NO_PN_RE = re.compile(
    r"(?:DWG(?:\s+NO)?\.?|DRAWING\s+NO\.?)\s*:?\s*"
    r"(P?\d{5,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?)",
    re.IGNORECASE,
)
_WELDMENT_TITLE_PN_RE = re.compile(
    r"\bWELDMENT\b.{0,48}?(P?\d{5,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?)",
    re.IGNORECASE | re.DOTALL,
)
_STANDALONE_DRAWING_PN_RE = re.compile(
    r"^P?\d{5,7}(?:\s*[-–—=]\s*\d{1,3}[A-Za-z]?)?$",
    re.IGNORECASE,
)
# `[3688-9` is OCR of 33688-9. Do not fire on `[25009-2` (5-digit stem).
_BRACKET_AS_THREE_RE = re.compile(r"\[(?=\d{4}\s*[-–—=]\s*\d)")
# ECO / revision / title-block notes — not weld parts (28106 C=72143, AN=89176-1).
_TITLE_ECO_NOISE_RE = re.compile(
    r"PROPERTY(?:\s+OF(?:\s+TIME)?)?"
    r"|THIS\s+DRAWING\s+IS\s+THE\s+PROPERTY"
    r"|FIRST\s+RELEASE"
    r"|ADDED\s+CONFIG(?:URATION)?"
    r"|ADDED\s+[—\-]*\s*4(?:\s+AND\s+ITEM)?"
    r"|ADDED\s+(?:AND\s+)?ITEM"
    r"|\bECO\b"
    r"|\bREV(?:ISION)?\b"
    r"|\bCONFIG(?:URATION)?\b",
    re.IGNORECASE,
)


def _is_title_block_drawing_line(raw: str, window: str = "") -> bool:
    """True for the drawing number in a title block — not a LOM row.

    ``102728-1`` between WELDMENT / TIME, or
    ``WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING``.
    A BOM description that merely says WELDMENT is kept.
    """
    text = str(raw or "").strip()
    if not re.search(r"P?\d{5,7}-\d{1,3}", text, flags=re.I):
        return False
    if re.fullmatch(r"P?\d{5,7}-\d{1,3}", text, flags=re.I):
        # Need WELDMENT and TIME/DWG. SHEET or a neighbor WELDMENT desc is not enough.
        ctx = window or text
        return bool(
            re.search(r"\bWELDMENT\b", ctx, flags=re.I)
            and re.search(r"\bTIME\s+MANUFACTURING\b|\bDWG(?:\s+NO)?\b", ctx, flags=re.I)
        )
    has_weldment = bool(re.search(r"\bWELDMENT\b", text, flags=re.I))
    has_shop = bool(
        re.search(r"\bTIME\s+MANUFACTURING\b|\bSHEET\s+\d|\bDWG(?:\s+NO)?\b", text, flags=re.I)
    )
    return has_weldment and has_shop


def _band_window(lines: Sequence[str], index: int, *, radius: int = 2) -> str:
    return " ".join(
        str(lines[j] or "")
        for j in range(max(0, index - radius), min(len(lines), index + radius + 1))
    )


def _expand_stamp_lines(lines: Sequence[str] | None) -> list[str]:
    """Split page.get_text blobs so a titleish page is not one mega-line."""
    out: list[str] = []
    for line in lines or []:
        text = str(line or "")
        out.extend(text.splitlines() if "\n" in text else [text])
    return out


def _normalize_drawing_pn_token(raw: str) -> str:
    token = re.sub(r"\s+", "", str(raw or "").upper())
    return re.sub(r"[=–—]", "-", token)


def _weldment_pn_reject_aliases(token: str) -> set[str]:
    """Exact weldment PN and its P-stripped form. Not 10047xx prefix siblings."""
    t = _normalize_drawing_pn_token(token)
    if not t or not re.fullmatch(r"P?\d{5,7}(?:-\d{1,3})?", t):
        return set()
    out = {t}
    if t.startswith("P") and re.match(r"P\d{5,7}", t):
        out.add(t[1:])
    stem = t[1:] if t.startswith("P") and len(t) > 1 and t[1].isdigit() else t
    if "-" in stem:
        base = stem.split("-", 1)[0]
        out.update({stem, f"P{stem}", base, f"P{base}"})
    else:
        # P904225 (no dash) still rejects 904225-1 — same title, not a sibling.
        out.update({stem, f"P{stem}", f"{stem}-1", f"P{stem}-1"})
    return {x for x in out if re.fullmatch(r"P?\d{5,7}(?:-\d{1,3})?", x)}


def _immediate_item_before(text: str, index: int) -> bool:
    """True for ``G P904226-1`` / ``G | P904226-1`` — a LOM balloon, not the title."""
    before = text[max(0, index - 12) : index]
    m = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,2})\s*[|:]?\s*$", before)
    return bool(m and is_material_list_item(m.group(1)))


def _standalone_is_title_drawing_pn(line_list: Sequence[str], index: int) -> bool:
    """True only for the title stack ``WELDMENT / 1007922-1 / TIME``, not LOM PNs."""
    text = str(line_list[index] or "").strip()
    if not _STANDALONE_DRAWING_PN_RE.fullmatch(text):
        return False
    prev = " ".join(str(line_list[j] or "") for j in range(max(0, index - 2), index))
    nxt = " ".join(
        str(line_list[j] or "")
        for j in range(index + 1, min(len(line_list), index + 3))
    )
    above_weldment = bool(re.search(r"\bWELDMENT\b|\bDWG(?:\s+NO)?\b", prev, flags=re.I))
    below_shop = bool(
        re.search(r"\bTIME\s+MANUFACTURING\b|\bDWG(?:\s+NO)?\b", nxt, flags=re.I)
    )
    above_shop = bool(
        re.search(r"\bTIME\s+MANUFACTURING\b|\bDWG(?:\s+NO)?\b", prev, flags=re.I)
    )
    below_weldment = bool(re.search(r"\bWELDMENT\b", nxt, flags=re.I))
    return (above_weldment and below_shop) or (above_shop and below_weldment)


def _title_drawing_tokens(text: str, window: str) -> list[str]:
    """The title drawing number only — never every dashed PN on the page."""
    found: list[str] = []
    for m in _TITLE_DWG_NO_PN_RE.finditer(text):
        found.append(m.group(1))
    shop_here = bool(
        re.search(r"\bTIME\s+MANUFACTURING\b|\bDWG(?:\s+NO)?\b", text, flags=re.I)
    )
    if shop_here:
        m = _TITLE_WELDMENT_SHOP_PN_RE.search(text) or _WELDMENT_TITLE_PN_RE.search(text)
        if m:
            found.append(m.group(1))
        for m in _SPACED_P_PREFIX_PN_RE.finditer(text):
            if _immediate_item_before(text, m.start()):
                continue
            found.append("P" + m.group(1))
    return found


def _drawing_numbers_to_reject(lines: Sequence[str] | None) -> set[str]:
    """Reject the exact title-block weldment PN (and its P-stripped form).

    A titleish page blob that also lists LOM children must not dump every
    ``\\d{5,7}-\\d`` into the reject set. ``14149-1`` / ``1007830-1`` are not
    weldment ``1007922-1``. Standalone PNs next to SHEET are LOM, not the title.
    """
    out: set[str] = set()
    line_list = _expand_stamp_lines(lines)
    blob = "\n".join(line_list)
    for index, line in enumerate(line_list):
        text = str(line or "").strip()
        if not text:
            continue
        window = _band_window(line_list, index)
        titleish = bool(
            _TITLE_DRAWING_CTX_RE.search(text)
            or _is_title_block_drawing_line(text, window)
        )
        standalone = _standalone_is_title_drawing_pn(line_list, index)
        if standalone:
            out.update(_weldment_pn_reject_aliases(text))
        if not titleish and not standalone:
            continue
        for token in _title_drawing_tokens(text, window):
            out.update(_weldment_pn_reject_aliases(token))
    for m in _TITLE_DWG_NO_PN_RE.finditer(blob):
        out.update(_weldment_pn_reject_aliases(m.group(1)))
    for m in _TITLE_WELDMENT_SHOP_PN_RE.finditer(blob):
        out.update(_weldment_pn_reject_aliases(m.group(1)))
    for m in _SPACED_P_PREFIX_PN_RE.finditer(blob):
        lo, hi = max(0, m.start() - 80), min(len(blob), m.end() + 80)
        local = blob[lo:hi]
        if not re.search(r"\b(?:WELDMENT|TIME\s+MANUFACTURING)\b", local, flags=re.I):
            continue
        if _immediate_item_before(blob, m.start()):
            continue
        out.update(_weldment_pn_reject_aliases("P" + m.group(1)))
    return out


def _drop_hyphenless_dupes(by_pn: dict) -> dict:
    """1035371 is 103537-1 with the hyphen missing — keep the dashed PN only."""
    dashed = {p for p in by_pn if "-" in str(p)}
    drop: set[str] = set()
    for p in by_pn:
        raw = str(p)
        if "-" in raw or not re.fullmatch(r"\d{6,8}", raw):
            continue
        for suf_len in (1, 2):
            cand = f"{raw[:-suf_len]}-{raw[-suf_len:]}"
            if cand in dashed:
                drop.add(p)
                break
    for p in drop:
        if "-" in str(p):
            continue
        by_pn.pop(p, None)
    return by_pn


def _find_time_like_pn_once(text: str) -> tuple[int, int, str] | None:
    from quote_core.bom import _ocr_digit_cleanup

    mangled = _MANGLED_DASHED_PN_RE.search(text)
    if mangled:
        base = _ocr_digit_cleanup(re.sub(r"\s+", "", mangled.group("base")))
        suf = _ocr_digit_cleanup(mangled.group("suf"))
        if base.isdigit() and 5 <= len(base) <= 7:
            part = recover_time_part_no(f"{base}-{suf}")
            if part:
                return mangled.start(), mangled.end(), part
    dashed = _DASHED_PN_RE.search(text)
    if dashed:
        part = recover_time_part_no(dashed.group(0))
        if part:
            return dashed.start(), dashed.end(), part
    glued = _GLUED_ITEM_PN_RE.search(text)
    if glued:
        base = glued.group("base")
        suf = glued.group("suf")
        token = f"{base}-{suf}" if suf else base
        part = recover_time_part_no(token) or (base if len(base) >= 5 else None)
        if part:
            return glued.start("base"), glued.end(), part
    bare = _BARE_PN_RE.search(text)
    if bare:
        part = recover_time_part_no(bare.group(0))
        if part:
            return bare.start(), bare.end(), part
    return None


def find_time_like_pn(raw: str | None) -> tuple[int, int, str] | None:
    """
    Find a Time-like PN even when the dash is broken or digits are glued.

    Does not invent a PN that is not in the strip. ``[3688-9`` is OCR of
    ``33688-9``; ``o4560 GATE`` is OCR of ``94560``. Do not turn
    ``[25009-2`` into ``325009-2`` — only ``[`` + 4-digit stem is a 3.
    """
    text = str(raw or "")
    if not text.strip():
        return None
    variants = [text]
    if "[" in text:
        bracket_three = _BRACKET_AS_THREE_RE.sub("3", text)
        if bracket_three != text:
            variants.append(bracket_three)
    o_as_nine = re.sub(r"(?<![A-Za-z0-9])[oO](\d{4})\b", r"9\1", text)
    if o_as_nine != text:
        variants.append(o_as_nine)
    hits = []
    for variant in variants:
        hit = _find_time_like_pn_once(variant)
        if hit:
            hits.append(hit)
    if not hits:
        return None
    # `[3688-9` is 33688-9, not the 4-digit 3688-9 the widened dash regex sees first.
    hits.sort(key=lambda h: (len(h[2]), h[2].count("-")), reverse=True)
    return hits[0]


def _looks_like_bb_tube(part: str | None, desc: str | None, raw: str = "") -> bool:
    """BB only. Do not swallow AY 102727-1 / AZ 102727-2 / BC 102727-5."""
    part_u = str(part or "").upper()
    if part_u in {_KNOWN_BB_PART, "02727-4"}:
        return True
    blob = f"{desc or ''} {raw}".upper()
    if _TUBE_ROUND_RE.search(blob) and (
        part_u.endswith("02727-4") or "02727-4" in blob or "102727-4" in blob
    ):
        return True
    return False


def _item_candidates(text: str) -> list[tuple[int, str, int | None]]:
    """Whole-word balloons, including glued ``BB2`` / ``BBD``."""
    out: list[tuple[int, str, int | None]] = []
    allowed = time_balloon_set(through="BZ")
    for m in _ITEM_WORD_RE.finditer(text or ""):
        raw = m.group(1).upper()
        if raw in _STRIP_HEADER_WORDS or raw in _DESC_NOISE_WORDS:
            continue
        item, glued_qty = _split_glued_item_qty(raw)
        if item and item in allowed:
            out.append((m.start(), item, glued_qty))
    return out


def _choose_item_for_part(
    raw: str, part_start: int, part: str, desc: str
) -> tuple[str | None, int | None]:
    if _looks_like_bb_tube(part, desc, raw):
        glued = None
        for pos, item, q in _item_candidates(raw):
            if item == "BB" and q is not None:
                glued = q
                break
        return "BB", glued
    cands = [c for c in _item_candidates(raw) if c[0] <= part_start]
    if not cands:
        cands = _item_candidates(raw)
    if not cands:
        return None, None
    close = [c for c in cands if part_start - c[0] <= 12]
    pool = close or cands
    # Two-letter balloons (AA–BC) beat a leaked single letter on the same part.
    pool.sort(key=lambda it: (abs(part_start - it[0]), -len(it[1])))
    _pos, item, glued = pool[0]
    return item, glued


def _split_lom_cells(raw: str) -> list[str] | None:
    """QTY | ITEM | PART NO | DESCRIPTION when the clip is cell-delimited."""
    text = str(raw or "")
    if "|" in text:
        return [c.strip() for c in text.split("|")]
    if "\t" in text:
        return [c.strip() for c in text.split("\t")]
    return None


def _qty_token_ok(n: int, *, glued: bool = False) -> bool:
    if n < 1 or n > 20:
        return False
    if glued:
        return True
    if n == 7 or _looks_like_column_index_qty(n):
        return False
    return True


def _qty_from_one_source(
    raw: str,
    part_start: int,
    *,
    item: str,
    part: str,
    desc: str,
    glued_qty: int | None,
) -> tuple[int | None, bool, str | None, bool]:
    """One qty source. Never default unread to 1. Real 4–8 stay (7 is bleed unless glued)."""
    is_bb = item == "BB" or _looks_like_bb_tube(part, desc, raw)
    cells = _split_lom_cells(raw)
    from_cells = False
    if cells:
        first = cells[0].strip()
        if re.fullmatch(r"[1-9]|1[0-9]|20", first):
            n = int(first)
            if _qty_token_ok(n):
                return n, True, None, True
            if n == 7 or _looks_like_column_index_qty(n):
                return None, False, (
                    f"{item or '?'} qty {n} looks like dimension/column-index bleed — "
                    f"not used as piece count, flag review"
                ), True
        elif first in _EMPTY_QTY:
            from_cells = True
    if glued_qty is not None:
        if _qty_token_ok(glued_qty, glued=True) and glued_qty <= 20:
            if glued_qty == 1:
                return 1, True, None, from_cells
            if 2 <= glued_qty <= 20:
                return glued_qty, True, f"{item} qty {glued_qty} from glued item+qty token", from_cells
    left = raw[: max(0, part_start)]
    # Digit immediately before the item balloon beats a stray later/earlier token.
    n_before_item: int | None = None
    if item:
        m_before = re.search(
            rf"(?<!\d)([1-9]|1[0-9]|20)\s+{re.escape(item)}\b",
            left + (item or ""),
            flags=re.IGNORECASE,
        )
        if m_before:
            n_before_item = int(m_before.group(1))
    tokens = [int(m.group(1)) for m in re.finditer(r"(?<!\d)([1-9]|1[0-9]|20)(?!\d)", left)]
    tokens = [n for n in tokens if n <= 20]
    if is_bb:
        if n_before_item == 2 or 2 in tokens:
            return 2, True, None, from_cells
        return 2, True, "BB qty 2 recovered (qty cell unread; known 102727-4 print)", from_cells
    n = n_before_item if n_before_item is not None else (tokens[-1] if tokens else None)
    if n is not None:
        # Qty 7 is dimension bleed; 2-digit 10–20 is column-index bleed.
        # Readable 2–6 / 8–9 (V=6, AA=5, AD=8, W=4) are piece counts.
        if n == 7 or _looks_like_column_index_qty(n):
            return None, False, (
                f"{item or '?'} qty {n} looks like dimension/column-index bleed — "
                f"not used as piece count, flag review"
            ), from_cells
        if 1 <= n <= 20:
            return n, True, None, from_cells
    return None, False, (
        f"{item or '?'} qty OCR unreadable — not defaulted to 1, re-read qty cell"
    ), from_cells


def _looks_like_dimension_qty(qty: int, desc: str | None, raw: str = "") -> bool:
    """qty>4 is bleed only when the cell looks like a dimension, not a real qty 2."""
    if qty <= 4:
        return False
    blob = f"{desc or ''} {raw}"
    if _BLEED_KIND_RE.search(blob):
        return True
    return bool(re.search(r"\d+\s*[xX×]\s*\d+", blob))


def parse_ocr_row_strip(line: str | None) -> dict[str, Any] | None:
    """
    Parse one live page-1 OCR strip.

    ``BBD 02727-4 TUBE, ROUND`` → item BB, part 102727-4, qty 2.
    ``H 102727-4 TUBE, ROUND`` → BB (do not steal H from a neighbor band).
    ``5 AA 460330 CAP, VERTICAL RAIL BOTTOM`` → AA / 460330 / qty 5.
    ``7 A 00177-2 PLATE`` → A / 100177-2 / qty unread (7 is bleed, not 1).
    Keep the band when OCR has a Time-like PN, dashed or not. Do not invent
    a PN that is not in the strip.
    """
    original = str(line or "").strip()
    raw = original.replace("|", " ").strip()
    if not raw:
        return None
    if is_glued_p_prefix_weldment_pn(raw):
        return None
    found = find_time_like_pn(raw)
    if found:
        part_start, part_end, part = found
    else:
        part_match = _DASHED_PN_RE.search(raw) or _BARE_PN_RE.search(raw)
        if not part_match:
            return None
        part_start, part_end = part_match.start(), part_match.end()
        part = recover_time_part_no(part_match.group(0), item=None)
    if not part or not re.search(r"\d{4,}", part):
        return None
    desc = raw[part_end:]
    desc = re.sub(r"^[\s,;:.-]+", "", desc).strip(" ,;|")
    desc = re.sub(r"\s+", " ", desc)
    if _looks_like_bb_tube(part, desc, raw):
        part = _KNOWN_BB_PART
    item, glued_qty = _choose_item_for_part(raw, part_start, part, desc)
    if not item:
        glued = _GLUED_ITEM_PN_RE.search(raw)
        if glued:
            letters, gqty = _split_glued_item_qty(glued.group("item").upper())
            if letters and is_material_list_item(letters):
                item = letters
                if glued_qty is None:
                    glued_qty = gqty
    if not item and not _is_time_like_part(part):
        return None
    if _looks_like_bb_tube(part, desc, raw):
        item = "BB"
        part = _KNOWN_BB_PART
    if _is_eco_or_title_block_row(part, desc, raw):
        return None
    qty, qty_clear, qty_note, from_cells = _qty_from_one_source(
        original or raw,
        part_start,
        item=item or "",
        part=part,
        desc=desc,
        glued_qty=glued_qty,
    )
    return {
        "item": item,
        "qty": 0 if qty is None else qty,
        "part_no": part,
        "description": desc,
        "qty_clear": qty_clear,
        "qty_note": qty_note,
        "unread_item": item is None,
        "from_cells": from_cells or bool(_split_lom_cells(raw)),
        "qty_unread": qty is None,
    }


def _parsed_to_row(parsed: dict[str, Any]):
    from quote_core.bom import BomRow

    cellish = bool(parsed.get("from_cells"))
    return BomRow(
        item=parsed["item"],
        qty=int(parsed["qty"] or 0),
        part_no=parsed["part_no"],
        description=parsed["description"],
        source="table_material_list_cell" if cellish else "table_material_list_strip",
        confidence=0.92 if (parsed.get("qty_clear") and cellish) else (
            0.88 if parsed.get("qty_clear") else 0.72
        ),
    )


def assign_items_from_sequence(
    slots: list[dict[str, Any] | None],
    notes: list[str] | None = None,
    lines: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Keep Time-like PN bands (dashed or not) with unread item letters;
    assign A–Z skip I/O, then AA–BC.

    Does not invent PNs. Does not create AI/AO (I/O are skipped as letters).
    Band order is top→bottom; 102728-1 has A at the bottom (header below).
    """
    notes = notes if notes is not None else []
    seq = time_item_letters(through="BC")
    seq_index = {tok: i for i, tok in enumerate(seq)}
    # Time LOM prints A at the bottom (header below). Do not flip to
    # top-down from two noisy OCR letters — that assigned A=460320 (Z).
    bottom_is_a = True
    header_idxs = _header_band_indexes(lines)
    expected = expected_letters_for_bands(
        len(slots), bottom_is_a=bottom_is_a, header_idxs=header_idxs
    )
    data_n = sum(
        1 for p in slots if p and _is_time_like_part(p.get("part_no"))
    )
    # Time LOM prints the header under the rows. Only then is band index
    # the letter (override a misread "A" on the top PN). A-first fixtures
    # without a bottom header keep a read item token.
    header_below = bool(header_idxs) and max(header_idxs) >= max(0, len(slots) - 4)
    force_grid = header_below and data_n >= SHORT_TABLE_REJECT
    used: set[str] = set()
    assigned = 0
    overridden = 0
    walk = range(len(slots) - 1, -1, -1)
    for i in walk:
        parsed = slots[i]
        if not parsed:
            continue
        if _looks_like_bb_tube(parsed.get("part_no"), parsed.get("description")):
            parsed["item"] = "BB"
            if not parsed.get("qty_clear") or int(parsed.get("qty") or 0) in {0, 7}:
                parsed["qty"] = 2
                parsed["qty_clear"] = True
            parsed["part_no"] = _KNOWN_BB_PART
            parsed["unread_item"] = False
            used.add("BB")
            continue
        if not _is_time_like_part(parsed.get("part_no")):
            continue
        ocr_item = str(parsed.get("item") or "").strip().upper()
        letter = expected[i]
        if force_grid and letter:
            if ocr_item and ocr_item != letter:
                overridden += 1
            parsed["item"] = letter
            parsed["unread_item"] = False
            used.add(letter)
            assigned += 1
            continue
        if ocr_item and ocr_item in seq_index:
            used.add(ocr_item)
            continue
        if not letter or letter in used:
            continue
        parsed["item"] = letter
        parsed["unread_item"] = False
        used.add(letter)
        assigned += 1
    if force_grid:
        notes.append(
            f"Assigned letters from grid bands (A at bottom; {data_n} PNs"
            f"{f', overrode {overridden} OCR letter(s)' if overridden else ''}"
            f"; not after PN set)"
        )
    elif assigned:
        notes.append(
            f"Assigned {assigned} unread item letter(s) from A–BC sequence "
            f"(Time-like PN kept, dashed or not; A at bottom)"
        )
    # Keep every Time-like PN. Letters are labels; do not delete a PN here.
    return [p for p in slots if p and _is_time_like_part(p.get("part_no"))]


def expected_letters_for_bands(
    n_bands: int,
    *,
    bottom_is_a: bool = True,
    header_idxs: set[int] | None = None,
) -> list[str | None]:
    """Map top→bottom band indexes to A–BC (skip I/O). Header bands stay None."""
    seq = time_item_letters(through="BC")
    skip = header_idxs or set()
    data_idxs = [i for i in range(n_bands) if i not in skip]
    out: list[str | None] = [None] * n_bands
    ordered = list(reversed(data_idxs)) if bottom_is_a else data_idxs
    for offset, idx in enumerate(ordered):
        if offset >= len(seq):
            break
        out[idx] = seq[offset]
    return out


def _header_band_indexes(lines: Sequence[str] | None) -> set[int]:
    found: set[int] = set()
    for i, raw in enumerate(lines or []):
        text = str(raw or "")
        if re.search(r"\bPART\b", text, flags=re.I) and re.search(
            r"\b(?:NO|DESC|TEM|ITEM)\b", text, flags=re.I
        ):
            found.add(i)
    return found


def _note_sequence_holes(
    slots: list[dict[str, Any] | None],
    lines: Sequence[str] | None,
    notes: list[str],
    *,
    bottom_is_a: bool,
) -> None:
    """Dump raw OCR for empty/unparsed bands (even if blank). Do not invent PNs."""
    header_idxs = _header_band_indexes(lines)
    expected = expected_letters_for_bands(
        len(slots), bottom_is_a=bottom_is_a, header_idxs=header_idxs
    )
    for i, parsed in enumerate(slots):
        if parsed and parsed.get("part_no"):
            continue
        raw = ""
        if lines is not None and i < len(lines):
            raw = re.sub(r"\s+", " ", str(lines[i] or "")).strip()
        letter = expected[i] or "?"
        notes.append(f"Hole band {i}: letter={letter} raw={raw or '(empty)'}")


def _keep_better_pn_row(old, new):
    """Same PN: prefer BB qty 2, then a cell-grid qty, then a valid item token."""
    if new.part_no == _KNOWN_BB_PART and old.part_no != _KNOWN_BB_PART:
        return new
    if old.part_no == _KNOWN_BB_PART and new.part_no != _KNOWN_BB_PART:
        return old
    if str(new.item).upper() == "BB" and str(old.item).upper() != "BB":
        return new
    if str(old.item).upper() == "BB" and str(new.item).upper() != "BB":
        return old
    old_cell = "cell" in str(getattr(old, "source", "") or "")
    new_cell = "cell" in str(getattr(new, "source", "") or "")
    old_q, new_q = int(old.qty or 0), int(new.qty or 0)
    old_clear = float(getattr(old, "confidence", 0) or 0) >= 0.88 and old_q > 0
    new_clear = float(getattr(new, "confidence", 0) or 0) >= 0.88 and new_q > 0
    # Isolated QTY/ITEM/PART/DESC cells beat a whole-row blob (live half-reads).
    if new_cell and new_clear and not old_cell:
        return new
    if old_cell and old_clear and not new_cell:
        return old
    if is_material_list_item(str(old.item or "")) and not is_material_list_item(str(new.item or "")):
        return old
    if is_material_list_item(str(new.item or "")) and not is_material_list_item(str(old.item or "")):
        return new
    # Prefer a readable qty digit (1–9 except 7) over unread 0 / defaulted 1.
    if new_clear and not old_clear and 1 <= new_q <= 9 and new_q != 7:
        return new
    if old_clear and not new_clear and 1 <= old_q <= 9 and old_q != 7:
        return old
    if new_cell and old_cell and new_clear and old_clear and new_q > old_q and new_q != 7:
        return new
    return old


def label_letters_after_pn_set(rows: list, notes: list[str] | None = None) -> list:
    """Letters are labels on a unique-PN set. Never drop a PN to resolve a clash."""
    notes = notes if notes is not None else []
    used: set[str] = set()
    for row in rows:
        if row.part_no == _KNOWN_BB_PART or _looks_like_bb_tube(row.part_no, row.description):
            row.item = "BB"
            row.qty = 2
            used.add("BB")
    for row in rows:
        if str(row.item or "").upper() == "BB":
            continue
        item = str(row.item or "").strip().upper()
        if item in {"AI", "AO"} or not is_material_list_item(item) or item in used:
            row.item = ""
            continue
        used.add(item)
        row.item = item
    # Do not invent A–BC from unique-PN dict order. That labeled live A=460320.
    # Band/grid assign already ran. Empty letters stay empty.
    notes.append(
        f"Kept {len(rows)} unique Time PNs "
        f"(grid letters; A at bottom; do not reletter after PN set)"
    )
    return rows


def union_sticky_harvest(primary, extra):
    """Union unique Time PNs. First harvest wins a PN; extra adds new PNs only."""
    from quote_core.bom import BomResult

    notes = list(getattr(primary, "notes", None) or [])
    by_pn: dict[str, Any] = {}
    for row in list(getattr(primary, "rows", None) or []):
        pn = str(row.part_no or "")
        if not _is_time_like_part(pn):
            continue
        by_pn[pn] = row
    added = 0
    for row in list(getattr(extra, "rows", None) or []):
        pn = str(row.part_no or "")
        if not _is_time_like_part(pn):
            continue
        if pn in by_pn:
            by_pn[pn] = _keep_better_pn_row(by_pn[pn], row)
            continue
        by_pn[pn] = row
        added += 1
    if added:
        notes.append(f"Unioned {added} unique Time PN(s) from retry (keyed by PN, not letter)")
    rows = label_letters_after_pn_set(list(by_pn.values()), notes)
    extra_notes = [
        n
        for n in (getattr(extra, "notes", None) or [])
        if n.startswith("Hole band") or n.startswith("Re-OCR") or n.startswith("Page re-clip")
    ]
    method = getattr(primary, "method", None) or getattr(extra, "method", None)
    result = BomResult(
        rows=rows,
        method=method,
        confidence=max(float(getattr(primary, "confidence", 0) or 0), float(getattr(extra, "confidence", 0) or 0)),
        notes=notes + extra_notes,
        grid_row_count=max(
            int(getattr(primary, "grid_row_count", 0) or 0),
            int(getattr(extra, "grid_row_count", 0) or 0),
        ),
    )
    return result


def _finalize_strip_rows(
    rows: list,
    notes: list[str],
    *,
    lines: Sequence[str] | None = None,
) -> list:
    from quote_core.bom import BomRow

    reject = _drawing_numbers_to_reject(lines)
    by_pn: dict[str, Any] = {}
    for row in rows:
        if _looks_like_bb_tube(row.part_no, row.description):
            if str(row.item).upper() != "BB":
                notes.append(
                    f"Item {row.item} had 102727-4 TUBE, ROUND — "
                    f"reassigned to BB (neighbor-band letter)"
                )
            row = BomRow(
                item="BB",
                qty=2,
                part_no=_KNOWN_BB_PART,
                description=row.description or "TUBE, ROUND",
                source=row.source,
                confidence=row.confidence,
            )
        if _is_eco_or_title_block_row(row.part_no, row.description):
            notes.append(
                f"Dropped ECO/title-block row {row.item} {row.part_no} — not a weld part"
            )
            continue
        qn = int(row.qty or 0)
        if (
            str(row.item).upper() != "BB"
            and (qn == 7 or _looks_like_column_index_qty(qn))
        ):
            notes.append(
                f"{row.item} qty {qn} is dimension/column-index bleed — "
                f"not used as piece count, flag review"
            )
            row = BomRow(
                item=row.item,
                qty=0,
                part_no=row.part_no,
                description=row.description,
                source=row.source,
                confidence=min(float(row.confidence or 0), 0.72),
            )
        pn = str(row.part_no or "")
        if not _is_time_like_part(pn):
            continue
        if pn in reject:
            notes.append(f"Dropped weldment drawing PN {pn} — not a BOM row")
            continue
        prev = by_pn.get(pn)
        by_pn[pn] = _keep_better_pn_row(prev, row) if prev else row
    dropped_dupes = [p for p in list(by_pn) if "-" not in str(p)]
    _drop_hyphenless_dupes(by_pn)
    for p in dropped_dupes:
        if p not in by_pn:
            notes.append(f"Dropped hyphen-less dupe {p} (dashed sibling kept)")
    return label_letters_after_pn_set(list(by_pn.values()), notes)


def harvest_ocr_row_strips(
    lines: Sequence[str] | None,
    *,
    bom_config: str | None = None,
    page_text: str | None = None,
):
    """Harvest every item+part pair on the strips. Does not invent missing items."""
    del bom_config
    from quote_core.bom import BomResult

    notes: list[str] = []
    slots: list[dict[str, Any] | None] = []
    line_list = list(lines or [])
    stamp_lines = list(line_list)
    if page_text:
        stamp_lines.append(str(page_text))
    reject = _drawing_numbers_to_reject(stamp_lines)
    for index, line in enumerate(line_list):
        if not str(line).strip():
            slots.append(None)
            continue
        raw_only = str(line).strip()
        window = _band_window(line_list, index)
        if _is_title_block_drawing_line(raw_only, window):
            slots.append(None)
            notes.append(f"Skipped title-block drawing number on: {raw_only[:48]}")
            continue
        parsed = parse_ocr_row_strip(line)
        if parsed and (
            str(parsed.get("part_no") or "") in reject
            or _is_eco_or_title_block_row(
                parsed.get("part_no"),
                parsed.get("description"),
                raw_only,
                window,
            )
        ):
            notes.append(
                f"Dropped ECO/title-block/weldment PN "
                f"{parsed.get('part_no')} on: {raw_only[:48]}"
            )
            slots.append(None)
            continue
        slots.append(parsed)
        if parsed is None:
            strip = re.sub(r"\s+", " ", str(line)).strip()
            itemish = strip.split(" ", 1)[0]
            notes.append(f"Skipped band {index}: item-ish={itemish} raw={strip}")
        elif parsed.get("qty_note"):
            notes.append(parsed["qty_note"])
    filled = assign_items_from_sequence(slots, notes, lines=lines)
    _note_sequence_holes(slots, lines or [], notes, bottom_is_a=True)
    found = [_parsed_to_row(p) for p in filled]
    # Same-line item+part only. Do not join bands — that copies a neighbor PN onto a hole.
    for index, line in enumerate(line_list):
        if not str(line).strip():
            continue
        window = _band_window(line_list, index)
        if _is_eco_or_title_block_row(None, None, str(line), window):
            continue
        for m in _ITEM_PART_ANY_RE.finditer(str(line)):
            if is_glued_p_prefix_weldment_pn(m.group(0)):
                continue
            glued = m.group("glued") or ""
            # Re-parse the whole strip so ECO/title-block text is not stripped off.
            parsed = parse_ocr_row_strip(str(line))
            if not parsed:
                parsed = parse_ocr_row_strip(f"{m.group('item')}{glued} {m.group('part')}")
            if not parsed or not is_material_list_item(str(parsed.get("item") or "")):
                continue
            pn = str(parsed.get("part_no") or "")
            if pn in reject or _is_eco_or_title_block_row(
                pn, parsed.get("description"), str(line), window
            ):
                continue
            found.append(_parsed_to_row(parsed))
    rows = _finalize_strip_rows(found, notes, lines=stamp_lines)
    if not rows:
        return BomResult(method=None, confidence=0.0, notes=["No item+part strips harvested"])
    rows.sort(key=lambda r: item_sort_key(str(r.item or "")))
    notes.insert(
        0,
        f"Harvested OCR row strips: {len(rows)} part numbers, "
        f"{sum(r.qty for r in rows)} pieces",
    )
    notes.extend(_incomplete_sequence_notes([str(r.item) for r in rows if r.item]))
    return BomResult(
        rows=rows,
        method="table_material_list",
        confidence=0.88,
        notes=notes,
    )


def harvest_material_list_lines(text: str | None, *, bom_config: str | None = None):
    """
    Line-by-line / finditer parse of ``2 BB 102727-4 TUBE, ROUND``.

    Also reads live page-1 strips (``BBD 02727-4``, ``AA 460330``) that have
    no qty token. ``bom_config`` is accepted for API symmetry.
    """
    from quote_core.bom import BomResult, BomRow, normalize_part_no

    if not text:
        return BomResult(method=None, confidence=0.0, notes=["No text to harvest"])
    if _MULTI_QTY_HEADER_RE.search(text) or _DASH_QTY_HEADER_RE.search(text):
        return BomResult(
            method=None,
            confidence=0.0,
            notes=["Multi-qty dash columns — leave to cell parser (do not strip-harvest)"],
        )
    blob = (
        str(text)
        .replace("|", " ")
        .replace("—", "-")
        .replace("–", "-")
        .replace("=", "-")
    )
    notes: list[str] = []
    strip_hit = harvest_ocr_row_strips(blob.splitlines(), bom_config=bom_config)
    collected = list(strip_hit.rows)
    notes.extend(n for n in strip_hit.notes if "qty" in n.lower() or "unreadable" in n.lower() or "recovered" in n.lower())

    for m in _QTY_ITEM_PART_FIND_RE.finditer(blob):
        item = m.group("item").upper()
        if not is_material_list_item(item):
            continue
        # Time balloons through BZ (A–Z skip I/O, AA–AZ, BA–BZ). Drops "SE TAS".
        if item not in time_balloon_set(through="BZ"):
            continue
        part_raw = re.sub(r"\s+", "", m.group("part"))
        part = recover_time_part_no(part_raw, item=item) or normalize_part_no(part_raw) or part_raw.upper()
        if not part or not re.search(r"\d{4,}", part):
            continue
        qty = max(1, int(m.group("qty")))
        if qty > 20:
            continue
        tail = blob[m.end() : m.end() + 48]
        desc_m = re.match(r"\s*([^|\n]{0,40})", tail)
        desc = (desc_m.group(1) if desc_m else "").strip(" ,;|")
        nxt = _QTY_ITEM_PART_FIND_RE.search(desc)
        if nxt:
            desc = desc[: nxt.start()].strip()
        if _is_eco_or_title_block_row(part, desc, m.group(0)):
            continue
        if _looks_like_bb_tube(part, desc, m.group(0)):
            item = "BB"
            part = _KNOWN_BB_PART
            qty = 2
        elif qty == 7 or _looks_like_column_index_qty(qty):
            notes.append(
                f"{item} qty {qty} looks like dimension bleed — "
                f"not used as piece count, flag review"
            )
            qty = 0
        collected.append(
            BomRow(
                item=item,
                qty=qty,
                part_no=part,
                description=desc,
                source="table_material_list_harvest",
                confidence=0.9,
            )
        )
    rows = _finalize_strip_rows(collected, notes, lines=blob.splitlines())
    if not rows:
        return BomResult(method=None, confidence=0.0, notes=["No qty/item/part lines harvested"])
    # Loose qty/item/part bait (page-0 regex leftovers) is not a table unless
    # a LOM header is present or the harvest is a tall Time list.
    if len(rows) < TALL_TABLE_MIN_ROWS and not text_has_material_list_grid(text):
        return BomResult(
            method=None,
            confidence=0.0,
            notes=["Harvested lines ignored — no LIST OF MATERIAL header and not a tall grid"],
        )
    rows.sort(key=lambda r: item_sort_key(str(r.item or "")))
    notes.insert(
        0,
        f"Harvested LIST OF MATERIAL lines: {len(rows)} part numbers, "
        f"{sum(r.qty for r in rows)} pieces",
    )
    notes.extend(_incomplete_sequence_notes([str(r.item) for r in rows if r.item]))
    return BomResult(
        rows=rows,
        method="table_material_list",
        confidence=0.9,
        notes=notes,
    )


@dataclass
class MaterialListLayout:
    """Column map for a LIST OF MATERIAL / PARTS LIST grid."""

    qty_cols: list[str] = field(default_factory=lambda: ["QTY"])
    qty_xs: list[float] = field(default_factory=list)
    item_x: float | None = None
    part_x: float | None = None
    desc_x: float | None = None
    header_y: float | None = None
    headers: list[str] = field(default_factory=list)

    @property
    def is_multi_qty(self) -> bool:
        dashes = [c for c in self.qty_cols if _DASH_COL_RE.match(c) or c.lstrip("-").isdigit()]
        return len(self.qty_cols) > 1 or bool(dashes)


def material_list_header_seen(bom: Any) -> bool:
    """True when a LOM / QTY+ITEM+PART grid header was found (even if 0 rows)."""
    if bom is None:
        return False
    method = getattr(bom, "method", None)
    if method and str(method).startswith("table_"):
        return True
    blob = " ".join(getattr(bom, "notes", None) or []).lower()
    if "header found" in blob and "list of material" in blob:
        return True
    if "qty/item/part header" in blob:
        return True
    return False


def detect_material_list_header(cells: Sequence[str]) -> MaterialListLayout | None:
    """
    Detect a header row such as ``QTY | ITEM | PART NO. | DESCRIPTION``
    or ``-4 | -3 | -2 | -1 | ITEM | PART NO. | DESCRIPTION``.
    """
    raw = [str(c or "").strip() for c in cells if str(c or "").strip()]
    if len(raw) == 1 and re.search(r"\bQTY\b", raw[0], re.I) and re.search(
        r"\bITEM\b", raw[0], re.I
    ):
        raw = raw[0].split()
    tokens = [_norm_header_token(c) for c in raw if c]
    if not tokens:
        return None
    joined = " ".join(tokens)
    has_item = any(t in _HEADER_ITEM for t in tokens)
    has_part = any(t in _HEADER_PART or t.startswith("PART") for t in tokens)
    if not (has_item and has_part):
        # Allow "LIST OF MATERIAL" title rows to fail (not a column header).
        return None
    qty_cols: list[str] = []
    for t in tokens:
        dash = _DASH_COL_RE.match(t) or (
            _BARE_DASH_RE.fullmatch(t) if t.lstrip("-").isdigit() and len(t) <= 3 else None
        )
        if dash and t not in _HEADER_ITEM:
            # Bare "1" in a header is usually ITEM index, not a dash column.
            if t.isdigit():
                continue
            qty_cols.append(f"-{dash.group(1)}")
        elif t in _HEADER_QTY:
            qty_cols.append("QTY")
    if not qty_cols and re.search(r"\bQTY\b", joined, re.I):
        qty_cols = ["QTY"]
    if not qty_cols and not _MULTI_QTY_HEADER_RE.search(joined):
        # Still accept ITEM + PART with an implicit single qty column.
        qty_cols = ["QTY"]
    # 102728-1 prints a lone ``-1`` above item BC — not a qty-column header.
    if qty_cols == ["-1"] and "QTY" not in joined and "DESC" not in joined:
        return None
    return MaterialListLayout(qty_cols=qty_cols, headers=tokens)


def _norm_header_token(raw: str) -> str:
    text = str(raw or "").strip().upper().replace(".", "")
    text = re.sub(r"\s+", " ", text)
    if text in {"PART NO", "PART NUMBER", "PART NUM"}:
        return "PART NO."
    if text in {"P/N", "PN"}:
        return "PART NO."
    if text == "PARTNO":
        return "PART NO."
    if _DASH_COL_RE.match(str(raw or "").strip()):
        return str(raw).strip()
    return text or str(raw or "").strip().upper()


def _parse_qty_cell(raw: str | None) -> int:
    token = str(raw or "").strip()
    if token in _EMPTY_QTY:
        return 0
    if not _QTY_TOKEN_RE.fullmatch(token):
        return 0
    return max(0, int(token))


def _selected_qty(
    cells: Sequence[str],
    layout: MaterialListLayout,
    *,
    bom_config: str | None,
    qty_start: int = 0,
) -> tuple[int, bool]:
    """
    Return (qty, keep_row).

    Multi-qty tables use only the dash column being quoted — never the sum.
    """
    from quote_core.bom_config import normalize_bom_config

    n_qty = len(layout.qty_cols)
    qty_cells = list(cells[qty_start : qty_start + n_qty])
    if layout.is_multi_qty and n_qty > 1:
        dash = normalize_bom_config(bom_config)
        if not dash:
            return 0, False
        want = f"-{dash.lstrip('-')}"
        idx = None
        for i, col in enumerate(layout.qty_cols):
            col_n = col if col.startswith("-") else f"-{col}" if col.isdigit() else col
            if col_n == want or col.lstrip("-") == dash.lstrip("-"):
                idx = i
                break
        if idx is None:
            return 0, False
        raw = qty_cells[idx] if idx < len(qty_cells) else ""
        qty = _parse_qty_cell(raw)
        if _looks_like_column_index_qty(qty):
            return 1, True
        return qty, qty > 0
    raw = qty_cells[0] if qty_cells else (cells[0] if cells else "")
    qty = _parse_qty_cell(raw)
    if _looks_like_column_index_qty(qty):
        qty = 1
    if qty <= 0 and len(cells) > n_qty:
        # Sometimes QTY is omitted and the first cell is the item letter.
        qty = 1
    return max(1, qty), True


def _tokenize_row_blob(blob: str) -> list[str]:
    """Split an undelimited OCR/native line into qty / item / part / description."""
    raw = str(blob or "").strip()
    if not raw:
        return []
    m = _ROW_BLOB_RE.match(raw)
    if not m:
        return raw.split()
    out: list[str] = []
    if m.group("qty"):
        out.append(m.group("qty"))
    out.append(m.group("item"))
    out.append(re.sub(r"\s+", "", m.group("part")))
    desc = (m.group("desc") or "").strip()
    if desc:
        out.append(desc)
    return out


def _split_row_fields(
    cells: Sequence[str],
    layout: MaterialListLayout,
) -> tuple[list[str], str, str, str]:
    """Return qty_cells, item, part, description from a data row."""
    tokens = [str(c or "").strip() for c in cells if str(c or "").strip()]
    if not tokens:
        return [], "", "", ""
    if len(tokens) == 1:
        tokens = _tokenize_row_blob(tokens[0])
        if not tokens:
            return [], "", "", ""

    from quote_core.bom import normalize_part_no

    # Prefer finding ITEM then PART, with qty cells to the left of ITEM.
    item_idx = None
    for i, tok in enumerate(tokens):
        if is_material_list_item(tok):
            item_idx = i
            break
    if item_idx is None:
        return [], "", "", ""

    item = tokens[item_idx].upper()
    rest = tokens[item_idx + 1 :]
    # OCR often splits BB into B | B before the part number.
    if (
        len(item) == 1
        and rest
        and is_material_list_item(rest[0])
        and len(str(rest[0])) == 1
        and len(rest) >= 2
        and (normalize_part_no(rest[1]) or re.match(r"^\d{4,7}", rest[1]))
    ):
        glued_item = item + str(rest[0]).upper()
        if is_material_list_item(glued_item):
            item = glued_item
            rest = rest[1:]
    qty_cells = tokens[:item_idx]
    part = ""
    desc_parts: list[str] = []
    if rest:
        # Do not invent a dash on 460200 / 460320. recover keeps 6-digit catalog PNs.
        part = recover_time_part_no(rest[0]) or rest[0]
        desc_parts = rest[1:]
        # PART NO sometimes split: 102727 / -4
        if len(rest) >= 2 and re.match(r"^[-–—=]\s*\d", str(rest[1])):
            glued = recover_time_part_no(rest[0] + rest[1]) or normalize_part_no(
                rest[0] + rest[1]
            )
            if glued:
                part = glued
                desc_parts = rest[2:]
    n_qty = len(layout.qty_cols)
    if not qty_cells and n_qty:
        qty_cells = ["1"]
    # Pad / trim qty cells to layout width when the row used explicit columns.
    if layout.is_multi_qty and n_qty > 1:
        if len(qty_cells) < n_qty:
            qty_cells = (["-"] * (n_qty - len(qty_cells))) + qty_cells
        elif len(qty_cells) > n_qty:
            qty_cells = qty_cells[-n_qty:]
    return qty_cells, item, part, " ".join(desc_parts).strip(" ,;|")


def parse_material_list_cells(
    rows: Sequence[Sequence[str]],
    *,
    bom_config: str | None = None,
    header: Sequence[str] | None = None,
) -> Any:
    """Parse already-segmented table cells into a BomResult. No library padding."""
    from quote_core.bom import BomResult, BomRow, normalize_part_no

    notes: list[str] = []
    layout = detect_material_list_header(header or []) if header is not None else None
    body: list[Sequence[str]] = list(rows)
    if layout is None and body:
        maybe = detect_material_list_header(body[0])
        if maybe:
            layout = maybe
            body = body[1:]
    if layout is None:
        layout = MaterialListLayout(qty_cols=["QTY"], headers=list(header or []))

    parsed: list[BomRow] = []
    seen_items: set[str] = set()
    for raw in body:
        cells = [str(c or "").strip() for c in raw]
        if not any(cells):
            continue
        if detect_material_list_header(cells):
            continue
        qty_cells, item, part_raw, desc = _split_row_fields(cells, layout)
        if not item or not is_material_list_item(item):
            continue
        if item in seen_items:
            continue
        work_cells = list(qty_cells) + [item, part_raw, desc]
        qty, keep = _selected_qty(work_cells, layout, bom_config=bom_config)
        if not keep:
            continue
        part = (
            recover_time_part_no(part_raw, item=item)
            or normalize_part_no(part_raw)
            or str(part_raw or "").upper()
        )
        if not part or part in {"-", "PART", "PART NO."}:
            continue
        if _is_eco_or_title_block_row(part, desc, " ".join(cells)):
            notes.append(f"Dropped ECO/title-block row {item} {part} — not a weld part")
            continue
        if _looks_like_column_index_qty(int(qty)):
            qty = 1
        seen_items.add(item)
        parsed.append(
            BomRow(
                item=item,
                qty=int(qty),
                part_no=part,
                description=desc,
                source="table_material_list",
                confidence=0.94,
            )
        )

    parsed.sort(key=lambda r: item_sort_key(str(r.item or "")))
    notes.extend(_incomplete_sequence_notes([str(r.item) for r in parsed if r.item]))
    method = (
        "table_material_list_multi_qty" if layout.is_multi_qty else "table_material_list"
    )
    if not parsed:
        return BomResult(
            method="table_material_list",
            confidence=0.0,
            notes=notes or [_HEADER_FOUND_NOTE],
        )
    from quote_core.bom_config import format_bom_config_label

    if layout.is_multi_qty and bom_config:
        notes.insert(
            0,
            f"Used BOM qty column {format_bom_config_label(bom_config)} "
            f"(table cells; not summed)",
        )
    notes.insert(
        0,
        f"Table LIST OF MATERIAL: {len(parsed)} part numbers, "
        f"{sum(r.qty for r in parsed)} pieces",
    )
    avg = sum(r.confidence for r in parsed) / max(1, len(parsed))
    return BomResult(rows=parsed, method=method, confidence=avg, notes=notes)


def _incomplete_sequence_notes(items: list[str]) -> list[str]:
    if not items:
        return []
    last = max(items, key=item_sort_key)
    expected = time_item_letters(through=last)
    found = {i.upper() for i in items}
    missing = [tok for tok in expected if tok not in found]
    if not missing:
        return []
    preview = ", ".join(missing[:16])
    extra = "…" if len(missing) > 16 else ""
    return [
        f"LIST OF MATERIAL table incomplete vs expected item sequence "
        f"A…{last} (skip I/O as letters): missing {preview}{extra} "
        f"({len(missing)} gap(s)) — flag review; do not pad from nested "
        f"drawing-library / sub-weldment files"
    ]


def _split_delimited_line(line: str) -> list[str]:
    raw = line.strip()
    if not raw:
        return []
    if "|" in raw:
        return [c.strip() for c in raw.strip("|").split("|")]
    if "\t" in raw:
        return [c.strip() for c in raw.split("\t")]
    # Two-or-more spaces as cell boundary (structured text fixture).
    if re.search(r"\s{2,}", raw):
        return [c.strip() for c in re.split(r"\s{2,}", raw) if c.strip()]
    blob = _tokenize_row_blob(raw)
    if len(blob) >= 3 and is_material_list_item(blob[0] if not blob[0].isdigit() else blob[1]):
        return blob
    return [raw]


def parse_material_list_text(text: str | None, *, bom_config: str | None = None) -> Any:
    """Parse pipe/tab/spaced LIST OF MATERIAL text into BomResult."""
    from quote_core.bom import BomResult

    if not text:
        return BomResult(method=None, confidence=0.0, notes=["No LIST OF MATERIAL grid header"])
    harvested_early = harvest_material_list_lines(text, bom_config=bom_config)
    if not text_has_material_list_grid(text):
        if len(harvested_early.rows) >= TALL_TABLE_MIN_ROWS:
            return harvested_early
        return BomResult(method=None, confidence=0.0, notes=["No LIST OF MATERIAL grid header"])

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cell_rows = [_split_delimited_line(ln) for ln in lines]
    cell_rows = [r for r in cell_rows if r and not _TITLE_RE.fullmatch(" ".join(r))]
    header_idx = None
    layout = None
    for i, row in enumerate(cell_rows):
        layout = detect_material_list_header(row)
        if layout:
            header_idx = i
            break
    harvested = harvest_material_list_lines(text, bom_config=bom_config)
    if layout is None or header_idx is None:
        if harvested.rows:
            return harvested
        return BomResult(
            method="table_material_list" if _TITLE_RE.search(text or "") else None,
            confidence=0.0,
            notes=["LIST OF MATERIAL title found but no QTY/ITEM/PART header row"],
        )
    above = cell_rows[:header_idx]
    below = cell_rows[header_idx + 1 :]
    parsed_below = parse_material_list_cells(below, bom_config=bom_config, header=cell_rows[header_idx])
    parsed_above = parse_material_list_cells(above, bom_config=bom_config, header=cell_rows[header_idx])
    structured = parsed_above if len(parsed_above.rows) > len(parsed_below.rows) else parsed_below
    _strip_junk_pns_from_result(structured, text.splitlines())
    _strip_junk_pns_from_result(harvested, text.splitlines())
    best = pick_best_material_list([structured, harvested])
    return best or structured


def _strip_junk_pns_from_result(bom: Any, lines: Sequence[str] | None) -> Any:
    """Drop weldment drawing PNs, ECO/title-block, and hyphen-less dupes."""
    if bom is None:
        return bom
    rows = list(getattr(bom, "rows", None) or [])
    if not rows:
        return bom
    reject = _drawing_numbers_to_reject(lines)
    kept = []
    for row in rows:
        pn = str(row.part_no or "")
        if pn in reject:
            continue
        desc = getattr(row, "description", "")
        if _is_eco_or_title_block_row(pn, desc, ""):
            continue
        kept.append(row)
    by_pn = {str(r.part_no): r for r in kept}
    _drop_hyphenless_dupes(by_pn)
    bom.rows = list(by_pn.values())
    return bom


def _merge_header_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join PART + NO. / PART + NUMBER into one header token."""
    ordered = sorted(words, key=lambda w: (w.get("x0", 0.0), w.get("y0", 0.0)))
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(ordered):
        cur = dict(ordered[i])
        text = str(cur.get("text") or "").strip().upper().rstrip(".")
        if text == "PART" and i + 1 < len(ordered):
            nxt = str(ordered[i + 1].get("text") or "").strip().upper().rstrip(".")
            if nxt in {"NO", "NUMBER", "NUM"}:
                cur["text"] = "PART NO."
                cur["x1"] = ordered[i + 1].get("x1", cur.get("x1"))
                out.append(cur)
                i += 2
                continue
        if text == "LIST" and i + 2 < len(ordered):
            a = str(ordered[i + 1].get("text") or "").strip().upper()
            b = str(ordered[i + 2].get("text") or "").strip().upper()
            if a == "OF" and b.startswith("MATERIAL"):
                i += 3
                continue
        out.append(cur)
        i += 1
    return out


def cluster_word_rows(
    words: list[dict[str, Any]],
    y_tol: float = 8.0,
) -> list[list[dict[str, Any]]]:
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (w["y0"], w["x0"]))
    rows: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = [ordered[0]]
    cur_y = float(ordered[0]["y0"])
    for w in ordered[1:]:
        if abs(float(w["y0"]) - cur_y) <= y_tol:
            cur.append(w)
            cur_y = (cur_y * (len(cur) - 1) + float(w["y0"])) / len(cur)
        else:
            rows.append(sorted(cur, key=lambda z: z["x0"]))
            cur = [w]
            cur_y = float(w["y0"])
    if cur:
        rows.append(sorted(cur, key=lambda z: z["x0"]))
    return rows


def _layout_from_header_words(row: list[dict[str, Any]]) -> MaterialListLayout | None:
    merged = _merge_header_words(row)
    cells = [str(w.get("text") or "") for w in merged]
    layout = detect_material_list_header(cells)
    if not layout:
        return None
    qty_xs: list[float] = []
    item_x = part_x = desc_x = None
    for w in merged:
        token = _norm_header_token(str(w.get("text") or ""))
        x = (float(w.get("x0", 0)) + float(w.get("x1", 0))) / 2.0
        dash = _DASH_COL_RE.match(str(w.get("text") or "").strip())
        if dash or token in _HEADER_QTY:
            qty_xs.append(x)
        elif token in _HEADER_ITEM:
            item_x = x
        elif token in _HEADER_PART or token.startswith("PART"):
            part_x = x
        elif token in _HEADER_DESC:
            desc_x = x
    ys = [float(w.get("y0", 0)) for w in merged]
    layout.qty_xs = qty_xs
    layout.item_x = item_x
    layout.part_x = part_x
    layout.desc_x = desc_x
    layout.header_y = sum(ys) / max(1, len(ys))
    return layout


def _assign_row_cells(
    row: list[dict[str, Any]],
    layout: MaterialListLayout,
) -> list[str]:
    """Map positioned words into [qty…, item, part, description] cells."""
    cols: list[tuple[str, float]] = []
    for i, x in enumerate(layout.qty_xs):
        name = layout.qty_cols[i] if i < len(layout.qty_cols) else f"QTY{i}"
        cols.append((name, x))
    if layout.item_x is not None:
        cols.append(("ITEM", layout.item_x))
    if layout.part_x is not None:
        cols.append(("PART", layout.part_x))
    if layout.desc_x is not None:
        cols.append(("DESC", layout.desc_x))
    if not cols:
        return [str(w.get("text") or "") for w in sorted(row, key=lambda z: z["x0"])]

    buckets: dict[str, list[str]] = {name: [] for name, _ in cols}
    # Fallback description bucket for words right of part.
    buckets.setdefault("DESC", [])
    max_gap = 40.0
    if len(cols) >= 2:
        xs = sorted(x for _, x in cols)
        gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
        if gaps:
            max_gap = max(24.0, min(gaps) * 0.65)

    for w in row:
        text = str(w.get("text") or "").strip()
        if not text:
            continue
        wx = (float(w.get("x0", 0)) + float(w.get("x1", 0))) / 2.0
        name, cx = min(cols, key=lambda c: abs(wx - c[1]))
        if abs(wx - cx) > max(max_gap, 36.0) and layout.desc_x is not None and wx > (layout.part_x or 0):
            buckets["DESC"].append(text)
            continue
        buckets[name].append(text)

    qty_cells = [" ".join(buckets.get(c, [])).strip() or "-" for c in layout.qty_cols]
    item = "".join(buckets.get("ITEM", [])).replace(" ", "").upper()
    # Two OCR words "B" "B" in the item column → BB.
    if not is_material_list_item(item) and buckets.get("ITEM"):
        glued = "".join(t.strip().upper() for t in buckets["ITEM"] if t.strip())
        if is_material_list_item(glued):
            item = glued
    part = " ".join(buckets.get("PART", [])).strip()
    desc = " ".join(buckets.get("DESC", [])).strip()
    return qty_cells + [item, part, desc]


def _find_header_in_word_rows(
    rows: list[list[dict[str, Any]]],
) -> tuple[int, MaterialListLayout, list[dict[str, Any]]] | None:
    for i, row in enumerate(rows):
        layout = _layout_from_header_words(row)
        if layout:
            return i, layout, row
    # Stacked Time headers can sit on two consecutive y-clusters.
    for i in range(len(rows) - 1):
        combined = list(rows[i]) + list(rows[i + 1])
        layout = _layout_from_header_words(combined)
        if layout:
            return i, layout, combined
    return None


def _table_band_words(
    words: list[dict[str, Any]],
    layout: MaterialListLayout,
) -> list[dict[str, Any]]:
    """Keep words in the QTY…DESCRIPTION x-range (right-side Time grid)."""
    xs = list(layout.qty_xs)
    for extra in (layout.item_x, layout.part_x, layout.desc_x):
        if extra is not None:
            xs.append(float(extra))
    if not xs:
        return words
    x_min = min(xs) - 36.0
    x_max = max(xs) + 220.0
    band = [
        w
        for w in words
        if x_min <= (float(w.get("x0", 0)) + float(w.get("x1", 0))) / 2.0 <= x_max
    ]
    return band or words


def _cells_from_word_row(
    row: list[dict[str, Any]],
    layout: MaterialListLayout,
) -> list[str]:
    assigned = _assign_row_cells(row, layout)
    qty_cells, item, part, desc = _split_row_fields(assigned, layout)
    if item and part:
        return list(qty_cells) + [item, part, desc]
    # Loose: ignore column x and read left-to-right tokens on this y-row.
    tokens = [str(w.get("text") or "").strip() for w in sorted(row, key=lambda z: z["x0"])]
    tokens = [t for t in tokens if t]
    qty_cells, item, part, desc = _split_row_fields(tokens, layout)
    if item:
        return list(qty_cells) + [item, part, desc]
    return tokens


def parse_material_list_words(
    words: list[dict[str, Any]],
    *,
    bom_config: str | None = None,
    y_tol: float = 8.0,
    layout: MaterialListLayout | None = None,
) -> Any:
    """Cluster positioned words into cells, then parse the grid."""
    from quote_core.bom import BomResult

    if not words:
        return BomResult(method=None, confidence=0.0, notes=["No words for LIST OF MATERIAL table"])

    rows = cluster_word_rows(words, y_tol=y_tol)
    line_blob = "\n".join(
        " ".join(str(w.get("text") or "") for w in row) for row in rows
    )
    harvested = harvest_material_list_lines(line_blob, bom_config=bom_config)
    header_idx = None
    header_words: list[dict[str, Any]] = []
    if layout is None:
        found = _find_header_in_word_rows(rows)
        if found:
            header_idx, layout, header_words = found
        else:
            if harvested.rows:
                return harvested
            return BomResult(
                method=None,
                confidence=0.0,
                notes=["No QTY/ITEM/PART header in word grid"],
            )
        band = _table_band_words(words, layout)
        if len(band) < len(words):
            # Dense 51-row Time grids need a tighter y cluster inside the band.
            rows = cluster_word_rows(band, y_tol=min(y_tol, 6.5))
            found = _find_header_in_word_rows(rows)
            if found:
                header_idx, layout, header_words = found
    else:
        header_idx = -1
        rows = cluster_word_rows(_table_band_words(words, layout), y_tol=min(y_tol, 6.5))

    header_cells = [str(w.get("text") or "") for w in _merge_header_words(header_words)]
    if not header_cells:
        header_cells = list(layout.headers) or ["QTY", "ITEM", "PART NO.", "DESCRIPTION"]
    data_rows = rows if header_idx < 0 else rows[:header_idx] + rows[header_idx + 1 :]
    if header_idx >= 0:
        above_cells = [_cells_from_word_row(r, layout) for r in rows[:header_idx]]
        below_cells = [_cells_from_word_row(r, layout) for r in rows[header_idx + 1 :]]
        parsed_below = parse_material_list_cells(
            below_cells, bom_config=bom_config, header=header_cells
        )
        parsed_above = parse_material_list_cells(
            above_cells, bom_config=bom_config, header=header_cells
        )
        chosen = parsed_above if len(parsed_above.rows) > len(parsed_below.rows) else parsed_below
    else:
        chosen = parse_material_list_cells(
            [_cells_from_word_row(r, layout) for r in data_rows],
            bom_config=bom_config,
            header=header_cells,
        )
    chosen = pick_best_material_list([chosen, harvested]) or chosen
    if chosen.rows:
        chosen.notes = [
            "Read LIST OF MATERIAL as table cells (not whole-page regex)",
            *list(chosen.notes),
        ]
        for row in chosen.rows:
            if row.source == "table_material_list":
                row.source = "table_material_list_cells"
    elif not chosen.notes:
        chosen.notes = [_HEADER_FOUND_NOTE]
    return chosen
