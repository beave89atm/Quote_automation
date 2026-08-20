"""Bill of materials extraction: native text tables + OCR for vector CAD sheets."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_PART_NO_RE = re.compile(
    r"(?<![\d])(\d{4,7})\s*[-–—=]\s*(\d{1,3}[A-Za-z]?)\b",
    re.IGNORECASE,
)
_ITEM_LETTER_RE = re.compile(r"^[A-Z]$")
_QTY_RE = re.compile(r"^\d{1,3}$")

# qty | item | part  (dash required so 35122 is not split into 3512-2)
# Item balloons are A–Z (Time often skips I); previously A–G only dropped H+.
_LINE_QTY_ITEM_PART = re.compile(
    r"(?<!\d)(\d{1,2})\s*[|Il/]?\s*([A-Za-z])\s*[|Il/]?\s*"
    r"(\d{4,7})\s*[-–—=]\s*(\d{1,3}[A-Za-z]?)",
    re.IGNORECASE,
)
# item glued to part: G435144-1 (letter immediately before digits)
_LINE_ITEM_GLUED_PART = re.compile(
    r"(?<!\d)(\d{1,2})\s*[|Il/]?\s*([A-Za-z])(\d{4,7})\s*[-–—=]\s*(\d{1,2})",
    re.IGNORECASE,
)
# item | part without qty
_LINE_ITEM_PART = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z])\s*[|Il/]?\s*"
    r"(\d{4,7})\s*[-–—=]\s*(\d{1,2}[A-Za-z]?)",
    re.IGNORECASE,
)
# qty | item with truncated part base only
_LINE_QTY_ITEM_PARTBASE = re.compile(
    r"(?<!\d)(\d{1,2})\s*[|Il/]?\s*([A-Za-z])\s*[|Il/]?\s*(\d{4,7})\s*[-–—=]?",
    re.IGNORECASE,
)
# qty | item | truncated part base (no qty, no suffix) — common on dense Time BOMs
_LINE_ITEM_PARTBASE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z])\s*[|Il/]?\s*(\d{4,7})\s*[-–—=]?(?!\d)",
    re.IGNORECASE,
)

# Multi-option Time BOM: qty(-4) | qty(-3) | qty(-2) | qty(-1) | ITEM | PART
# Example OCR: ``| - | - | - | 1 | A |16697-2 |Lower BOOM TUBE``
_MULTI_QTY_LINE_RE = re.compile(
    r"(?<!\d)(-|\d{1,2})\s*[|\]Il/]\s*(-|\d{1,2})\s*[|\]Il/]\s*"
    r"(-|\d{1,2})\s*[|\]Il/]\s*(-|\d{1,2})\s*[|\]Il/]\s*"
    r"([A-Za-z])\s*[|\]Il/]?\s*"
    r"(\d{4,7})\s*[-–—=]?\s*(\d{1,3}[A-Za-z]?)",
    re.IGNORECASE,
)
_MULTI_QTY_HEADERS_RE = re.compile(
    r"(?:\[?-4\]?[^\n]{0,20}\[?-3\]?[^\n]{0,20}\[?-2\]?[^\n]{0,20}\[?-1\]?)"
    r"|(?:-4\s*[|\]]\s*-3\s*[|\]]\s*-2\s*[|\]]\s*-1)",
    re.IGNORECASE,
)

@dataclass
class BomRow:
    item: str | int | None
    qty: int
    part_no: str
    description: str = ""
    unit_weight_lb: float | None = None
    source: str = "unknown"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BomResult:
    rows: list[BomRow] = field(default_factory=list)
    method: str | None = None
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)
    assembly_weight_lb: float | None = None

    @property
    def piece_count(self) -> int:
        """Physical pieces: sum of positive BOM qtys (qty 0 / OCR-I rows do not count)."""
        return sum(int(r.qty) for r in self.rows if int(r.qty) > 0)

    @property
    def part_number_count(self) -> int:
        return len({r.part_no for r in self.rows if r.part_no})

    def component_weights_lb(self) -> list[float]:
        """One entry per physical piece when unit weights are known."""
        out: list[float] = []
        for row in self.rows:
            if row.unit_weight_lb is None:
                continue
            out.extend([float(row.unit_weight_lb)] * max(1, int(row.qty)))
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "method": self.method,
            "confidence": self.confidence,
            "notes": self.notes,
            "assembly_weight_lb": self.assembly_weight_lb,
            "piece_count": self.piece_count,
            "part_number_count": self.part_number_count,
            "component_weights_lb": self.component_weights_lb(),
            "bom_rows": [
                {
                    "item": r.item,
                    "qty": r.qty,
                    "part_no": r.part_no,
                    "description": r.description,
                    "unit_weight_lb": r.unit_weight_lb,
                }
                for r in self.rows
            ],
        }


def _ocr_digit_cleanup(token: str) -> str:
    """Map common OCR letter/digit confusions inside part-number digit runs."""
    table = str.maketrans(
        {
            "O": "0",
            "Q": "0",
            "I": "1",
            "L": "1",
            "Z": "2",
            "S": "5",
            "¢": "9",
        }
    )
    # lowercase i/l often appear mid-number (35i21)
    return token.upper().replace("I", "1").translate(table).replace("L", "1")


def normalize_part_no(raw: str) -> str | None:
    if not raw:
        return None
    cleaned = (
        str(raw)
        .upper()
        .replace("—", "-")
        .replace("–", "-")
        .replace("=", "-")
        .replace(" ", "")
    )
    cleaned = re.sub(r"[^0-9A-Z-]", "", cleaned)
    # If dash missing but looks like ###### + suffix (351211 → 35121-1)
    m = re.match(r"^(\d{4,7})-(\d{1,3}[A-Z]?)$", cleaned)
    if not m:
        # Letter stuck in digits: 35I21-1
        soft = _ocr_digit_cleanup(cleaned)
        m = re.match(r"^(\d{4,7})-(\d{1,3}[A-Z]?)$", soft)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
        m2 = re.match(r"^(\d{4,7})(\d{1,2})$", soft)
        if m2 and len(soft) >= 5:
            # Prefer 5-digit bases (351211 → 35121-1) over 4+2.
            if len(soft) == 6:
                return f"{soft[:5]}-{soft[5:]}"
            if len(soft) == 7:
                return f"{soft[:5]}-{soft[5:]}"
            return f"{m2.group(1)}-{m2.group(2)}"
        m = _PART_NO_RE.search(_ocr_digit_cleanup(str(raw).upper()))
        if not m:
            return None
        return f"{m.group(1)}-{m.group(2).upper()}"
    return f"{m.group(1)}-{m.group(2)}"


def _base_from_pdf_stem(stem: str) -> str | None:
    stem_u = stem.upper().strip()
    if stem_u in {"CT", "PL", "BOM", "NOTES", "RD"}:
        return None
    m = re.match(r"^(\d{4,7})(?:-\d+)?(?:\b|$)", stem_u)
    return m.group(1) if m else None


def _iter_library_pdfs(folder: Path, *, max_depth: int = 2) -> list[Path]:
    """PDFs in a weldment folder and one child packet folder (Time layout)."""
    found: list[Path] = []
    if not folder or not folder.exists():
        return found

    def walk(cur: Path, depth: int) -> None:
        try:
            entries = list(cur.iterdir())
        except OSError:
            return
        for p in entries:
            if p.is_file() and p.suffix.lower() == ".pdf":
                found.append(p)
            elif p.is_dir() and depth < max_depth:
                walk(p, depth + 1)

    walk(folder, 0)
    return found


def _collapse_truncated_bases(bases: set[str]) -> set[str]:
    """Drop stems that are prefixes of a longer sibling (100433 vs 1004335)."""
    if len(bases) < 2:
        return set(bases)
    return {
        b
        for b in bases
        if not any(other != b and other.startswith(b) and other[len(b) :].isdigit() for other in bases)
    }


def library_part_bases(
    folder: Path | None,
    related_pdf_names: list[str] | None = None,
) -> set[str]:
    """Part number bases from sibling/child drawing PDFs (e.g. 35121.pdf → 35121)."""
    bases: set[str] = set()
    if folder and folder.exists():
        for p in _iter_library_pdfs(Path(folder)):
            base = _base_from_pdf_stem(p.stem)
            if base:
                bases.add(base)
    for name in related_pdf_names or []:
        stem = Path(str(name)).stem
        base = _base_from_pdf_stem(stem)
        if base:
            bases.add(base)
    return _collapse_truncated_bases(bases)


def _correct_part_with_library(part_no: str, bases: set[str]) -> str:
    """Fix common OCR digit errors using known library part bases.

    Only snaps to a library base when exactly one neighbor is Hamming-distance 1.
    Dense Time families (21684/21688/21689) are otherwise left as OCR-read —
    rewriting 21689→21684 was dropping a real hose-guard line.
    """
    norm = normalize_part_no(part_no)
    if not norm:
        return part_no
    base, _, suffix = norm.partition("-")
    if not bases or base in bases:
        return norm
    near = [
        lib
        for lib in bases
        if len(lib) == len(base) and sum(a != b for a, b in zip(lib, base)) == 1
    ]
    if len(near) == 1:
        return f"{near[0]}-{suffix}"
    return norm


def _fix_leading_digit_glue(base: str, bases: set[str]) -> str:
    """OCR sometimes prefixes item letter as digit (G435144 → 435144)."""
    if base in bases:
        return base
    if len(base) >= 5 and base[1:] in bases:
        return base[1:]
    if bases:
        for lib in bases:
            if base.endswith(lib) and len(base) - len(lib) <= 1:
                return lib
    return base


_TIME_BOM_HINT_RE = re.compile(
    r"LIST\s+OF\s+MATERIAL|\bPART\s*NO\.?\b|\bITEM\b.*\bQTY\b|\bQTY\b.*\bITEM\b",
    re.IGNORECASE,
)
_TIME_HEADER_SKIP = {
    "QTY",
    "ITEM",
    "PART",
    "NO",
    "NO.",
    "DESCRIPTION",
    "LIST",
    "OF",
    "MATERIAL",
    "REV",
    "WEIGHT",
    "STAMP",
    "SHEET",
}


def _is_garbage_time_part(part_no: str, bases: set[str] | None = None) -> bool:
    """OCR junk: leading-zero bases (004556-2), empty, or unknown when library is known."""
    if not part_no or str(part_no).endswith("-?"):
        return True
    norm = normalize_part_no(part_no) or str(part_no).upper()
    base, _, _suf = norm.partition("-")
    if not base.isdigit():
        return True
    if base.startswith("0"):
        return True
    if len(base) < 4:
        return True
    return False


def _looks_like_time_bom_text(text: str) -> bool:
    if not text or not text.strip():
        return False
    if _TIME_BOM_HINT_RE.search(text):
        return True
    # Lettered Time rows: ``1 A 1004335-1`` or ``| 2 | E |1004067-1``
    hits = list(_LINE_QTY_ITEM_PART.finditer(text)) + list(_LINE_ITEM_PART.finditer(text))
    return len(hits) >= 3


def _parse_stacked_time_hits(text: str, bases: set[str]) -> list[dict[str, Any]]:
    """CAD native text often emits QTY / ITEM / PART as consecutive tokens."""
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z0-9./\-]+", text)
    hits: list[dict[str, Any]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.upper().rstrip(".") in _TIME_HEADER_SKIP:
            i += 1
            continue
        if (
            i + 2 < len(tokens)
            and _QTY_RE.match(tok)
            and _ITEM_LETTER_RE.match(tokens[i + 1].upper())
        ):
            part = normalize_part_no(tokens[i + 2])
            if part and not _is_garbage_time_part(part, bases):
                hits.append(
                    {
                        "qty": int(tok),
                        "item": tokens[i + 1].upper(),
                        "part_no": _correct_part_with_library(part, bases),
                        "has_qty": True,
                        "has_suffix": True,
                        "raw": " ".join(tokens[i : i + 3]),
                    }
                )
                i += 3
                continue
        if i + 1 < len(tokens) and _ITEM_LETTER_RE.match(tok.upper()):
            part = normalize_part_no(tokens[i + 1])
            if part and not _is_garbage_time_part(part, bases):
                hits.append(
                    {
                        "qty": None,
                        "item": tok.upper(),
                        "part_no": _correct_part_with_library(part, bases),
                        "has_qty": False,
                        "has_suffix": True,
                        "raw": " ".join(tokens[i : i + 2]),
                    }
                )
                i += 2
                continue
        i += 1
    return hits


def _drop_invalid_time_rows(rows: list[BomRow], bases: set[str]) -> list[BomRow]:
    """Drop qty-0 I rows and OCR garbage PNs (Time skips letter I)."""
    kept: list[BomRow] = []
    for row in rows:
        qty = int(row.qty or 0)
        part = str(row.part_no or "")
        item = row.item.upper() if isinstance(row.item, str) else row.item
        if qty <= 0:
            continue
        if _is_garbage_time_part(part, bases):
            continue
        if item == "I" and (qty <= 0 or _is_garbage_time_part(part, bases)):
            continue
        if item == "I" and bases and part.partition("-")[0] not in bases:
            # Time almost never uses I; keep only a library-confirmed PN.
            continue
        kept.append(row)
    return kept


def _supplement_library_children(
    rows: list[BomRow],
    bases: set[str],
    *,
    primary_base: str | None = None,
    zero_parts: set[str] | None = None,
) -> list[str]:
    """
    Completeness backstop: missing library stems become qty-1 review rows.

    Does not replace a BOM that already covers the library. Adds only stems
    that are absent, and flags the gap for review.
    """
    notes: list[str] = []
    if not bases:
        return notes
    skip = {b for b in (primary_base,) if b}
    zero_parts = zero_parts or set()
    present = {r.part_no.partition("-")[0] for r in rows if r.part_no}
    component_bases = sorted(b for b in bases if b not in skip)
    if len(component_bases) < 3:
        return notes
    missing = [b for b in component_bases if b not in present]
    if not missing:
        return notes
    if len(present) >= len(component_bases):
        return notes

    added = 0
    existing_parts = {r.part_no for r in rows}
    for base in missing:
        part = f"{base}-1"
        if part in existing_parts or part in zero_parts:
            continue
        if any(pn.startswith(base + "-") for pn in existing_parts):
            continue
        rows.append(
            BomRow(
                item=None,
                qty=1,
                part_no=part,
                description="",
                unit_weight_lb=None,
                source="library_child",
                confidence=0.6,
            )
        )
        existing_parts.add(part)
        added += 1

    if added:
        notes.append(
            f"BOM incomplete vs library ({len(present)} parts on drawing vs "
            f"{len(component_bases)} files); added {added} missing stem(s) at "
            f"qty 1 — review"
        )
    elif missing:
        notes.append(
            f"BOM incomplete vs library ({len(present)} parts on drawing vs "
            f"{len(component_bases)} files)"
        )
    return notes


def parse_time_style_bom_texts(
    texts: list[str],
    bases: set[str] | None = None,
    *,
    bom_config: str | None = None,
    primary_base: str | None = None,
    source: str = "native_time",
) -> BomResult:
    """
    Shared Time LIST OF MATERIAL parser for native PDF text and OCR strings.

    Drops qty-0 / letter-I OCR ghosts and leading-zero junk PNs. ``bom_config``
    only selects a dash column when multi-qty headers are actually present.
    """
    from quote_core.bom_config import format_bom_config_label, normalize_bom_config

    bases = set(bases or [])
    config = normalize_bom_config(bom_config)
    blob_list = [t for t in (texts or []) if t and str(t).strip()]
    if not blob_list:
        return BomResult(notes=["No Time-style BOM text"], confidence=0.0)

    has_headers = texts_have_multi_qty_headers(blob_list)
    multi_raw = (
        _parse_multi_qty_time_hits(blob_list, bases, bom_config=config) if config else []
    )
    used_multi = bool(config and has_headers and multi_raw)
    zero_parts: set[str] = set()
    if used_multi:
        zero_parts = _zero_qty_parts_for_config(blob_list, bases, bom_config=config)
        hits = [h for h in multi_raw if int(h.get("qty") or 0) > 0]
        for h in _parse_qty_item_part_hits(blob_list, bases):
            part = str(h.get("part_no") or "")
            if part and part not in zero_parts:
                hits.append(h)
    else:
        hits = _parse_qty_item_part_hits(blob_list, bases)

    for blob in blob_list:
        hits.extend(_parse_stacked_time_hits(blob, bases))

    rows = _vote_bom_rows(hits, bases)
    if used_multi:
        for row in rows:
            row.source = "ocr_time_multi_qty" if source.startswith("ocr") else "native_time_multi_qty"
    rows = _drop_invalid_time_rows(rows, bases)
    _repair_suffix_ocr(rows, hits, bases)

    notes: list[str] = []
    if used_multi and config:
        notes.append(
            f"Used BOM qty column {format_bom_config_label(config)} "
            f"(multi-option Time drawing)"
        )
        supp_bases = {b for b in bases if b != primary_base}
        notes.extend(
            _supplement_multi_config_bom(
                rows, blob_list, supp_bases, bom_config=config or ""
            )
        )
    elif config and not used_multi:
        notes.append(
            f"BOM config {format_bom_config_label(config)} set but multi-qty columns "
            f"not detected — used single-qty parse (did not drop other dashes)"
        )

    if not used_multi:
        notes.extend(
            _supplement_library_children(
                rows,
                bases,
                primary_base=primary_base,
                zero_parts=zero_parts,
            )
        )

    dedup: dict[str, BomRow] = {}
    for r in rows:
        prev = dedup.get(r.part_no)
        if prev is None or (r.item and not prev.item) or r.qty > prev.qty:
            dedup[r.part_no] = r
    rows = list(dedup.values())

    def sort_key(r: BomRow):
        if isinstance(r.item, str) and r.item.isalpha():
            return (0, r.item)
        return (1, str(r.part_no))

    rows.sort(key=sort_key)
    if not rows:
        return BomResult(notes=notes or ["Time-style BOM found no part rows"], confidence=0.0)

    avg_conf = sum(r.confidence for r in rows) / max(1, len(rows))
    notes.insert(
        0,
        f"{'OCR' if source.startswith('ocr') else 'Native'} Time-style BOM: "
        f"{len(rows)} part numbers, {sum(int(r.qty) for r in rows if int(r.qty) > 0)} pieces",
    )
    method = source
    if used_multi and not method.endswith("multi_qty"):
        method = f"{source}_multi_qty"
    return BomResult(rows=rows, method=method, confidence=avg_conf, notes=notes)


def extract_bom_from_native_mac(pdf_path: Path | str | None, text: str | None = None) -> BomResult:
    """Existing MAC-style ITEM/QTY/PART/WEIGHT lbm block parser."""
    from quote_core.weight import extract_pdf_bom_weights

    bom = extract_pdf_bom_weights(pdf_path=pdf_path, text=text)
    rows_raw = list(bom.get("bom_rows") or [])
    if not rows_raw:
        return BomResult(method=None, confidence=0.0, notes=["No native MAC-style BOM rows"])
    rows: list[BomRow] = []
    for r in rows_raw:
        part = normalize_part_no(str(r.get("part_no") or "")) or str(r.get("part_no") or "")
        rows.append(
            BomRow(
                item=r.get("item"),
                qty=max(1, int(r.get("qty") or 1)),
                part_no=part,
                description=str(r.get("description") or ""),
                unit_weight_lb=(
                    float(r["unit_weight_lb"]) if r.get("unit_weight_lb") is not None else None
                ),
                source="native_mac",
                confidence=0.95,
            )
        )
    return BomResult(
        rows=rows,
        method="pdf_bom_qty",
        confidence=0.95,
        notes=["Parsed native PDF BOM text blocks"],
        assembly_weight_lb=bom.get("assembly_weight_lb"),
    )


_PARTS_LIST_PN_RE = re.compile(r"^[A-Z]{1,3}\d{2}-\d{3,5}$", re.IGNORECASE)
_PARTS_LIST_HEADER_RE = re.compile(r"\bPARTS\s+LIST\b", re.IGNORECASE)
_PARTS_LIST_STOP_RE = re.compile(
    r"^(?:NOTES?:|DO NOT SCALE|SHEET\s+\d|DRAWN|TITLE|DWG\s+NO|CONFIDENTIAL)\b",
    re.IGNORECASE,
)


def extract_bom_from_parts_list(
    pdf_path: Path | str | None = None,
    text: str | None = None,
) -> BomResult:
    """
    Cummins / NGFS native PARTS LIST blocks:

      DESCRIPTION / PART NUMBER / QTY / ITEM
      PLATE - GUSSET, ...
      MD04-2482
      1
      1
    """
    if text is None:
        if not pdf_path:
            return BomResult(method=None, confidence=0.0, notes=["No PDF text for PARTS LIST"])
        from quote_core.weight import _read_pdf_text

        text = _read_pdf_text(Path(pdf_path))
    if not text or not _PARTS_LIST_HEADER_RE.search(text):
        return BomResult(method=None, confidence=0.0, notes=["No PARTS LIST header in PDF text"])

    m = _PARTS_LIST_HEADER_RE.search(text)
    assert m is not None
    section = text[m.end() :]
    lines = [ln.strip() for ln in section.splitlines()]
    # Drop column headers
    skip = {"DESCRIPTION", "PART NUMBER", "PART NO", "PART NO.", "QTY", "ITEM", "REV"}
    body: list[str] = []
    for ln in lines:
        if not ln:
            continue
        if _PARTS_LIST_STOP_RE.match(ln):
            break
        if ln.upper() in skip:
            continue
        # Balloon duplicates like lone "1" / "A" after the list are ignored once we
        # have finished collecting rows — stop if we hit a long run of single tokens
        # after already parsing rows (handled below).
        body.append(ln)

    rows: list[BomRow] = []
    i = 0
    while i < len(body):
        # Description may wrap across lines until a part number.
        desc_parts: list[str] = []
        while i < len(body) and not _PARTS_LIST_PN_RE.match(body[i]):
            # Ignore stray balloon numbers before the first real description.
            if desc_parts or not re.fullmatch(r"\d{1,2}|[A-Z]", body[i], re.I):
                desc_parts.append(body[i])
            i += 1
            # Safety: descriptions shouldn't be endless
            if len(desc_parts) > 6:
                break
        if i >= len(body) or not _PARTS_LIST_PN_RE.match(body[i]):
            break
        part_no = body[i].upper()
        i += 1
        qty = 1
        item: str | int | None = None
        if i < len(body) and re.fullmatch(r"\d{1,3}", body[i]):
            qty = int(body[i])
            i += 1
        if i < len(body) and re.fullmatch(r"\d{1,3}|[A-Z]", body[i], re.I):
            item_raw = body[i]
            item = int(item_raw) if item_raw.isdigit() else item_raw.upper()
            i += 1
        # After a complete BOM, trailing sheet balloons (1..8 / A..D) look like
        # tiny descriptions — stop if next tokens aren't a real description.
        rows.append(
            BomRow(
                item=item,
                qty=max(1, qty),
                part_no=part_no,
                description=" ".join(desc_parts).strip(),
                source="native_parts_list",
                confidence=0.96,
            )
        )
        # Detect balloon tail: next few lines are only short tokens and no PN soon
        look = body[i : i + 8]
        if look and all(re.fullmatch(r"\d{1,2}|[A-Z]", x, re.I) for x in look):
            break
        if look and not any(_PARTS_LIST_PN_RE.match(x) for x in look) and all(
            len(x) <= 2 for x in look[:4]
        ):
            break

    if not rows:
        return BomResult(
            method=None,
            confidence=0.0,
            notes=["PARTS LIST header found but no rows parsed"],
        )
    return BomResult(
        rows=rows,
        method="native_parts_list",
        confidence=0.96,
        notes=[f"Parsed native PARTS LIST ({len(rows)} part numbers)"],
    )


def _render_clip_images(page, clip, dpi: int) -> list[tuple[str, Any]]:
    """Return labeled preprocessed PIL images for a page clip."""
    import fitz
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0), clip=clip, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    gray = ImageOps.autocontrast(ImageOps.grayscale(img))
    gray = ImageEnhance.Contrast(gray).enhance(2.5).filter(ImageFilter.SHARPEN)
    bw = gray.point(lambda x: 0 if x < 140 else 255)
    return [("gray", gray), ("bw", bw)]


def _ocr_strings(images: list[tuple[str, Any]], *, psms: tuple[int, ...] = (4, 6, 11)) -> list[str]:
    import pytesseract

    from quote_core.ocr import tesseract_cmd

    cmd = tesseract_cmd()
    if not cmd:
        return []
    pytesseract.pytesseract.tesseract_cmd = cmd

    texts: list[str] = []
    whitelist = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz|-—– "
    for _label, im in images:
        for psm in psms:
            for cfg in (
                f"--oem 3 --psm {psm}",
                f"--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}",
            ):
                try:
                    texts.append(pytesseract.image_to_string(im, config=cfg) or "")
                except Exception:  # noqa: BLE001
                    continue
    return texts


def _ocr_words_in_clip(page, clip, *, dpi: int = 400) -> list[dict[str, Any]]:
    import pytesseract

    from quote_core.ocr import tesseract_cmd

    cmd = tesseract_cmd()
    if not cmd:
        return []
    pytesseract.pytesseract.tesseract_cmd = cmd

    images = _render_clip_images(page, clip, dpi)
    # Prefer bw for word boxes on CAD linework.
    im = dict(images).get("bw") or images[0][1]
    data = pytesseract.image_to_data(im, config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT)
    scale = dpi / 72.0
    words: list[dict[str, Any]] = []
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        if not text:
            continue
        try:
            conf = int(float(data["conf"][i]))
        except ValueError:
            conf = -1
        if conf < 15:
            continue
        x0 = clip.x0 + data["left"][i] / scale
        y0 = clip.y0 + data["top"][i] / scale
        words.append(
            {
                "text": text,
                "x0": x0,
                "y0": y0,
                "x1": x0 + data["width"][i] / scale,
                "y1": y0 + data["height"][i] / scale,
                "conf": conf,
            }
        )
    return words


def _cluster_rows(words: list[dict[str, Any]], y_tol: float = 8.0) -> list[list[dict[str, Any]]]:
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (w["y0"], w["x0"]))
    rows: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = [ordered[0]]
    cur_y = ordered[0]["y0"]
    for w in ordered[1:]:
        if abs(w["y0"] - cur_y) <= y_tol:
            cur.append(w)
            cur_y = (cur_y * (len(cur) - 1) + w["y0"]) / len(cur)
        else:
            rows.append(sorted(cur, key=lambda z: z["x0"]))
            cur = [w]
            cur_y = w["y0"]
    if cur:
        rows.append(sorted(cur, key=lambda z: z["x0"]))
    return rows


def _parse_multi_qty_cell(raw: str) -> int:
    token = (raw or "").strip()
    if not token or token in {"-", "—", "–", ".", "·"}:
        return 0
    try:
        return max(0, int(token))
    except ValueError:
        return 0


def _parse_multi_qty_time_hits(
    texts: list[str],
    bases: set[str],
    *,
    bom_config: str,
) -> list[dict[str, Any]]:
    """
    Parse Time multi-column qty tables (``-4 | -3 | -2 | -1 | ITEM | PART``).

    ``bom_config`` is the dash suffix to keep (e.g. ``\"1\"`` → use the ``-1`` column).
    """
    dash = str(bom_config or "").strip().lstrip("-").upper()
    try:
        dash_n = int(re.sub(r"[^0-9]", "", dash) or "0")
    except ValueError:
        dash_n = 0
    if dash_n < 1 or dash_n > 4:
        return []

    # Capture groups are left→right -4,-3,-2,-1 → index 0..3; dash 1 → index 3.
    col_index = 4 - dash_n
    hits: list[dict[str, Any]] = []
    for blob in texts:
        for raw_line in blob.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            norm = (
                line.replace("—", "-")
                .replace("–", "-")
                .replace("=", "-")
                .replace("{", "|")
                .replace("}", "|")
                .replace("[", "|")
                .replace("]", "|")
            )
            soft = re.sub(
                r"(\d[0-9A-Za-z]*\d|\d+)",
                lambda m: _ocr_digit_cleanup(m.group(0).upper()),
                norm,
            )
            for variant in (norm, soft):
                for m in _MULTI_QTY_LINE_RE.finditer(variant):
                    qtys = [
                        _parse_multi_qty_cell(m.group(1)),
                        _parse_multi_qty_cell(m.group(2)),
                        _parse_multi_qty_cell(m.group(3)),
                        _parse_multi_qty_cell(m.group(4)),
                    ]
                    qty = qtys[col_index]
                    item = m.group(5).upper()
                    base = _fix_leading_digit_glue(m.group(6), bases)
                    suffix = re.sub(r"[^0-9A-Z]", "", m.group(7).upper())
                    if not suffix:
                        continue
                    part = _correct_part_with_library(f"{base}-{suffix}", bases)
                    hits.append(
                        {
                            "qty": qty,
                            "item": item,
                            "part_no": part,
                            "has_qty": True,
                            "has_suffix": True,
                            "raw": line,
                            "multi_qty": qtys,
                            "bom_config": dash,
                        }
                    )
    return hits


def texts_have_multi_qty_headers(texts: list[str]) -> bool:
    blob = "\n".join(texts or [])
    return bool(_MULTI_QTY_HEADERS_RE.search(blob))


def _zero_qty_parts_for_config(
    texts: list[str],
    bases: set[str],
    *,
    bom_config: str,
) -> set[str]:
    """Part numbers with qty 0 in the selected dash column (excluded configs)."""
    hits = _parse_multi_qty_time_hits(texts, bases, bom_config=bom_config)
    return {str(h["part_no"]) for h in hits if int(h.get("qty") or 0) <= 0 and h.get("has_suffix")}


def _supplement_multi_config_bom(
    rows: list[BomRow],
    texts: list[str],
    bases: set[str],
    *,
    bom_config: str,
) -> list[str]:
    """
    Recover BOM rows OCR missed on multi-qty tables.

    Dense Time sheets often drop qty columns for some lines (hose guard, end cap,
    cutout stiffener). If the part/item appears in OCR and is not qty-0 for this
    dash, add it at qty 1 (or the multi-qty value when known).
    """
    from quote_core.bom_config import format_bom_config_label

    notes: list[str] = []
    if not bom_config or not bases:
        return notes

    multi_all = _parse_multi_qty_time_hits(texts, bases, bom_config=bom_config)
    multi_by_item = {
        str(h["item"]): h for h in multi_all if h.get("item") and int(h.get("qty") or 0) > 0
    }
    multi_by_part = {
        str(h["part_no"]): h for h in multi_all if h.get("has_suffix") and int(h.get("qty") or 0) > 0
    }
    zero_parts = _zero_qty_parts_for_config(texts, bases, bom_config=bom_config)

    # Item + part hits without requiring qty columns.
    loose_hits = _parse_qty_item_part_hits(texts, bases)
    # Also harvest bare library part numbers from OCR (E/F/H rows often lose item+qty).
    blob = "\n".join(texts)
    soft = re.sub(
        r"(\d[0-9A-Za-z]*\d|\d+)",
        lambda m: _ocr_digit_cleanup(m.group(0).upper()),
        blob.replace("—", "-").replace("–", "-").replace("=", "-"),
    )
    for base in sorted(bases):
        if len(base) < 4:
            continue
        for m in re.finditer(
            rf"(?<!\d)({base})\s*[-–—=]?\s*(\d{{1,2}}[A-Za-z]?)\b",
            soft,
            flags=re.IGNORECASE,
        ):
            suffix = re.sub(r"[^0-9A-Z]", "", m.group(2).upper())
            if not suffix:
                continue
            part = _correct_part_with_library(f"{base}-{suffix}", bases)
            loose_hits.append(
                {
                    "qty": None,
                    "item": None,
                    "part_no": part,
                    "has_qty": False,
                    "has_suffix": True,
                    "raw": m.group(0),
                }
            )

    existing_items = {r.item for r in rows if isinstance(r.item, str)}
    existing_parts = {r.part_no for r in rows}
    existing_bases_with_suffix: dict[str, set[str]] = defaultdict(set)
    for pn in existing_parts:
        b, _, s = pn.partition("-")
        if s:
            existing_bases_with_suffix[b].add(s)

    added = 0
    for h in loose_hits:
        if not h.get("has_suffix"):
            continue
        part = str(h.get("part_no") or "")
        if not part or part.endswith("-?") or part in existing_parts:
            continue
        base, _, suf = part.partition("-")
        if bases and base not in bases:
            continue
        # Skip parts that multi-qty marks empty for this dash (other boom tubes).
        if part in zero_parts:
            continue
        # If another suffix of this base is already selected (16697-2), skip siblings.
        if suf and existing_bases_with_suffix.get(base) and suf not in existing_bases_with_suffix[base]:
            continue
        item = h.get("item")
        if isinstance(item, str) and item in existing_items:
            continue

        qty = 1
        if part in multi_by_part:
            qty = max(1, int(multi_by_part[part]["qty"]))
            item = item or multi_by_part[part].get("item")
        elif isinstance(item, str) and item in multi_by_item:
            qty = max(1, int(multi_by_item[item]["qty"]))
            part = str(multi_by_item[item]["part_no"])
            if part in existing_parts:
                continue

        # Heuristic: hose-guard / stiffener boom pivot often qty 2 when OCR lost columns.
        # Prefer explicit multi-qty; only guess when description/name hints and qty still 1
        # from a lone part sighting — use multi text ``2 | 2 | 2 | 2`` near the part.
        if qty == 1 and part not in multi_by_part:
            near = ""
            for blob2 in texts:
                if base in blob2.replace(" ", ""):
                    near += "\n" + blob2
            if re.search(
                rf"(?:\|\s*)?2\s*[|\]]\s*2\s*[|\]]\s*2\s*[|\]]\s*2\s*[|\]][^\n]{{0,40}}{base}",
                near.replace("—", "-"),
                flags=re.I,
            ):
                qty = 2

        rows.append(
            BomRow(
                item=item if isinstance(item, str) else None,
                qty=qty,
                part_no=part,
                description="",
                unit_weight_lb=None,
                source="ocr_time_multi_qty_supp",
                confidence=0.8,
            )
        )
        existing_parts.add(part)
        if isinstance(item, str):
            existing_items.add(item)
        if suf:
            existing_bases_with_suffix[base].add(suf)
        added += 1

    if added:
        notes.append(
            f"Supplemented {added} BOM part(s) from OCR + library stems "
            f"(multi-qty column {format_bom_config_label(bom_config)})"
        )

    # Dedicated weldment folders (few PDFs) may still miss a garbled PN in OCR
    # (e.g. 10187 → \"rote7\"). If almost all library stems are already on the BOM,
    # add the remaining stem(s) at qty 1 with suffix -1.
    present_bases = {r.part_no.partition("-")[0] for r in rows}
    missing_bases = sorted(b for b in bases if b not in present_bases)
    if (
        5 <= len(rows) <= 20
        and 1 <= len(missing_bases) <= 3
        and len(bases) <= 16
    ):
        for base in missing_bases:
            part = f"{base}-1"
            if part in zero_parts:
                continue
            # Prefer a suffix actually seen in OCR for this base.
            for h in loose_hits:
                pn = str(h.get("part_no") or "")
                if pn.startswith(base + "-") and h.get("has_suffix"):
                    if pn not in zero_parts:
                        part = pn
                        break
            if any(r.part_no == part for r in rows):
                continue
            rows.append(
                BomRow(
                    item=None,
                    qty=1,
                    part_no=part,
                    description="",
                    unit_weight_lb=None,
                    source="ocr_time_multi_qty_lib",
                    confidence=0.72,
                )
            )
            notes.append(
                f"Added library component {part} (OCR missed PN; folder stem present)"
            )
    return notes


def _parse_qty_item_part_hits(texts: list[str], bases: set[str]) -> list[dict[str, Any]]:
    """Parse OCR strings into candidate BOM hits."""
    hits: list[dict[str, Any]] = []
    for blob in texts:
        for raw_line in blob.splitlines():
            line = raw_line.strip()
            if not line or "PART" in line.upper() and "NO" in line.upper():
                continue
            if "LIST OF MATERIAL" in line.upper() or "STAMP" in line.upper():
                continue
            # Normalize fancy dashes / pipes; fix OCR letters inside digit runs later.
            norm = (
                line.replace("—", "-")
                .replace("–", "-")
                .replace("=", "-")
                .replace("¢", "9")
                .replace("“", "")
                .replace("”", "")
                .replace("{", "|")
                .replace("}", "|")
                .replace("[", "|")
                .replace("]", "|")
            )
            # Soft-clean only the digit-ish tokens for matching (keep item letters).
            soft = re.sub(
                r"(\d[0-9A-Za-z]*\d|\d+)",
                lambda m: _ocr_digit_cleanup(m.group(0).upper()),
                norm,
            )
            variants = [norm, soft, re.sub(r"\s+", "", soft)]

            for variant in variants:
                for rx in (_LINE_QTY_ITEM_PART, _LINE_ITEM_GLUED_PART):
                    for m in rx.finditer(variant):
                        qty = int(m.group(1))
                        item = m.group(2).upper()
                        base = _fix_leading_digit_glue(m.group(3), bases)
                        suffix = re.sub(r"[^0-9A-Z]", "", m.group(4).upper())
                        if not suffix:
                            continue
                        part = _correct_part_with_library(f"{base}-{suffix}", bases)
                        hits.append(
                            {
                                "qty": qty,
                                "item": item,
                                "part_no": part,
                                "has_qty": True,
                                "has_suffix": True,
                                "raw": line,
                            }
                        )

                for m in _LINE_ITEM_PART.finditer(variant):
                    item = m.group(1).upper()
                    base = _fix_leading_digit_glue(m.group(2), bases)
                    suffix = re.sub(r"[^0-9A-Z]", "", m.group(3).upper())
                    if not suffix:
                        continue
                    part = _correct_part_with_library(f"{base}-{suffix}", bases)
                    hits.append(
                        {
                            "qty": None,
                            "item": item,
                            "part_no": part,
                            "has_qty": False,
                            "has_suffix": True,
                            "raw": line,
                        }
                    )

                for m in _LINE_QTY_ITEM_PARTBASE.finditer(variant):
                    qty = int(m.group(1))
                    item = m.group(2).upper()
                    base = _fix_leading_digit_glue(m.group(3), bases)
                    if bases and base not in bases:
                        if not any(
                            b.isdigit() and abs(int(base) - int(b)) <= 2 for b in bases
                        ):
                            continue
                    hits.append(
                        {
                            "qty": qty,
                            "item": item,
                            "part_no": f"{base}-?",
                            "has_qty": True,
                            "has_suffix": False,
                            "raw": line,
                            "part_base": base,
                        }
                    )

                for m in _LINE_ITEM_PARTBASE.finditer(variant):
                    item = m.group(1).upper()
                    base = _fix_leading_digit_glue(m.group(2), bases)
                    if bases and base not in bases:
                        if not any(
                            b.isdigit() and abs(int(base) - int(b)) <= 2 for b in bases
                        ):
                            continue
                    hits.append(
                        {
                            "qty": None,
                            "item": item,
                            "part_no": f"{base}-?",
                            "has_qty": False,
                            "has_suffix": False,
                            "raw": line,
                            "part_base": base,
                        }
                    )
    return hits


def _vote_bom_rows(hits: list[dict[str, Any]], bases: set[str]) -> list[BomRow]:
    """Collapse OCR hits into one row per item letter (or part number)."""
    by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    no_item: list[dict[str, Any]] = []
    for h in hits:
        item = h.get("item")
        if item and isinstance(item, str) and item.isalpha():
            by_item[item].append(h)
        else:
            no_item.append(h)

    rows: list[BomRow] = []
    used_parts: set[str] = set()

    for item in sorted(by_item.keys()):
        group = by_item[item]
        qty_votes = [int(h["qty"]) for h in group if h.get("has_qty") and h.get("qty") is not None]
        qty = Counter(qty_votes).most_common(1)[0][0] if qty_votes else 1
        if int(qty) <= 0:
            continue

        part_votes = [
            h["part_no"]
            for h in group
            if h.get("has_suffix") and h.get("part_no") and not str(h["part_no"]).endswith("-?")
        ]
        part = None
        if part_votes:
            # Prefer library-base matches, then majority
            scored: list[tuple[int, str]] = []
            for pn, n in Counter(part_votes).items():
                base = pn.split("-")[0]
                bonus = 10 if base in bases else 0
                # Prefer suffixes that aren't OCR-confused 7 when 1 also seen
                scored.append((n + bonus, pn))
            scored.sort(reverse=True)
            part = scored[0][1]
            # If top part suffix is 7 and a -1 sibling exists for same base, prefer -1
            base, _, suf = part.partition("-")
            if suf == "7":
                ones = [p for p in part_votes if p == f"{base}-1"]
                if ones:
                    part = f"{base}-1"
        else:
            bases_only = [h.get("part_base") for h in group if h.get("part_base")]
            if bases_only:
                base = Counter(bases_only).most_common(1)[0][0]
                # Try to recover suffix from other hits sharing base
                sibling_suffixes = [
                    h["part_no"].split("-", 1)[1]
                    for h in hits
                    if h.get("has_suffix")
                    and str(h.get("part_no", "")).startswith(base + "-")
                    and not str(h["part_no"]).endswith("-?")
                ]
                if sibling_suffixes:
                    part = f"{base}-{Counter(sibling_suffixes).most_common(1)[0][0]}"
                else:
                    # Default suffix 1 is common for primary detail; mark lower conf later
                    part = f"{base}-1"
            else:
                continue

        part = _correct_part_with_library(part, bases)
        # Prefer library bases when available, but keep strong OCR hits even if
        # the shared folder is incomplete (e.g. missing 21689.pdf beside the STP).
        if bases and part.split("-")[0] not in bases:
            recovered = None
            for h in group:
                pb = h.get("part_base")
                if pb and pb in bases:
                    recovered = pb
                    break
            if recovered:
                suf = part.split("-", 1)[1] if "-" in part else "1"
                if suf in {"7", "?", ""}:
                    suf = "1"
                part = f"{recovered}-{suf}"
            elif not part_votes:
                continue
        if part in used_parts:
            continue
        used_parts.add(part)
        conf = 0.92 if qty_votes and part_votes else 0.75
        rows.append(
            BomRow(
                item=item,
                qty=int(qty),
                part_no=part,
                description="",
                unit_weight_lb=None,
                source="ocr_time",
                confidence=conf,
            )
        )

    # Orphan part hits without item letters (rare)
    for h in no_item:
        if not h.get("has_suffix"):
            continue
        part = _correct_part_with_library(str(h["part_no"]), bases)
        if part in used_parts:
            continue
        used_parts.add(part)
        rows.append(
            BomRow(
                item=None,
                qty=int(h["qty"] or 1),
                part_no=part,
                description="",
                unit_weight_lb=None,
                source="ocr_time",
                confidence=0.55,
            )
        )

    return rows


def _attach_descriptions(
    rows: list[BomRow],
    page,
    clip,
) -> None:
    """Fill descriptions from a wider OCR pass near known part numbers."""
    words = _ocr_words_in_clip(page, clip, dpi=380)
    if not words:
        return
    row_clusters = _cluster_rows(words, y_tol=8.0)
    for bom in rows:
        base = bom.part_no.split("-")[0]
        for cluster in row_clusters:
            joined = " ".join(w["text"] for w in cluster)
            if base not in joined.replace(" ", ""):
                continue
            # Words to the right of the part token
            part_x = None
            for w in cluster:
                if base in w["text"].replace(" ", "") or normalize_part_no(w["text"]):
                    part_x = w["x1"]
                    break
            if part_x is None:
                continue
            desc = []
            for w in cluster:
                if w["x0"] < part_x - 2:
                    continue
                t = w["text"]
                if normalize_part_no(t) or _QTY_RE.match(t) or _ITEM_LETTER_RE.match(t.upper()):
                    continue
                desc.append(t)
            if desc:
                bom.description = re.sub(r"\s+", " ", " ".join(desc)).strip(" ,;|")
                break


def _repair_suffix_ocr(rows: list[BomRow], hits: list[dict[str, Any]], bases: set[str]) -> None:
    """When suffix looks like OCR confusion, prefer alternate seen on same item/base."""
    for row in rows:
        base, _, suf = row.part_no.partition("-")
        if not suf:
            continue
        alts = []
        for h in hits:
            pn = str(h.get("part_no") or "")
            if not h.get("has_suffix") or not pn.startswith(base + "-"):
                continue
            if h.get("item") and row.item and h["item"] != row.item:
                continue
            alts.append(pn)
        if not alts:
            continue
        # If current suffix is 7 and -1 appears for this base+item, swap
        if suf == "7" and f"{base}-1" in alts:
            row.part_no = f"{base}-1"
            continue
        # Majority among same-item hits
        if row.item:
            item_alts = [
                str(h["part_no"])
                for h in hits
                if h.get("item") == row.item and h.get("has_suffix") and str(h.get("part_no", "")).startswith(base)
            ]
            if item_alts:
                best = Counter(item_alts).most_common(1)[0][0]
                row.part_no = _correct_part_with_library(best, bases)


def extract_bom_from_ocr_time_style(
    pdf_path: Path | str,
    *,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
    page_index: int = 0,
    bom_config: str | None = None,
) -> BomResult:
    """
    Parse Time Manufacturing LIST OF MATERIAL tables.

    These tables often have column headers at the *bottom* of the grid
    (QTY | ITEM | PART NO. | DESCRIPTION) with data rows stacked above.
    Multi-option sheets use ``-4 | -3 | -2 | -1`` qty columns — pass
    ``bom_config=\"1\"`` to keep only the ``-1`` column.
    Uses multi-pass OCR + voting for qty/item/part accuracy on vector CAD.
    """
    import fitz

    from quote_core.bom_config import normalize_bom_config
    from quote_core.ocr import ocr_available

    pdf_path = Path(pdf_path)
    if not ocr_available():
        return BomResult(notes=["OCR unavailable for Time-style BOM"], confidence=0.0)

    config = normalize_bom_config(bom_config)
    bases = library_part_bases(
        Path(library_folder) if library_folder else None,
        related_pdf_names=related_pdf_names,
    )
    used_multi = False
    supp_notes: list[str] = []
    bom_rows: list[BomRow] = []
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[min(page_index, len(doc) - 1)]
        rect = page.rect
        # Qty/Item/Part columns — right-side crops. 16-row Time tables start
        # well above mid-page; keep a short clip for 7-row sheets plus a tall one.
        left_clip = fitz.Rect(
            rect.width * 0.70,
            rect.height * 0.62,
            rect.width * 0.82,
            rect.height * 0.87,
        )
        mid_clip = fitz.Rect(
            rect.width * 0.695,
            rect.height * 0.615,
            rect.width * 0.835,
            rect.height * 0.875,
        )
        tall_clip = fitz.Rect(
            rect.width * 0.68,
            rect.height * 0.22,
            rect.width * 0.88,
            rect.height * 0.92,
        )
        wide_clip = fitz.Rect(
            rect.width * 0.58,
            rect.height * 0.16,
            rect.width * 0.995,
            rect.height * 0.94,
        )
        desc_clip = fitz.Rect(
            rect.width * 0.68,
            rect.height * 0.40,
            rect.width * 0.995,
            rect.height * 0.90,
        )

        texts: list[str] = []
        for clip, dpi in (
            (left_clip, 500),
            (mid_clip, 500),
            (tall_clip, 480),
            (wide_clip, 420),
            (left_clip, 420),
        ):
            images = _render_clip_images(page, clip, dpi)
            texts.extend(_ocr_strings(images, psms=(4, 6, 11)))

        primary_base = None
        m_pri = re.match(r"^(\d{4,7})", pdf_path.stem.upper().replace(" ", ""))
        if m_pri:
            primary_base = m_pri.group(1)
        parsed = parse_time_style_bom_texts(
            texts,
            bases,
            bom_config=config,
            primary_base=primary_base,
            source="ocr_time",
        )
        bom_rows = list(parsed.rows)
        used_multi = bool(parsed.method and "multi_qty" in parsed.method)
        if bom_rows:
            _attach_descriptions(bom_rows, page, desc_clip)
    finally:
        doc.close()

    if not bom_rows:
        return BomResult(notes=["OCR Time-style BOM found no part rows"], confidence=0.0)

    notes = list(parsed.notes)
    if bases:
        notes.append(f"Validated part bases against library folder ({len(bases)} PDF stems)")
    method = parsed.method or ("ocr_time_multi_qty" if used_multi else "ocr_time")
    avg_conf = parsed.confidence
    if used_multi:
        avg_conf = min(0.96, avg_conf + 0.03)
    return BomResult(rows=bom_rows, method=method, confidence=avg_conf, notes=notes)


def extract_bom_from_native_time_style(
    pdf_path: Path | str | None = None,
    text: str | None = None,
    *,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
    bom_config: str | None = None,
) -> BomResult:
    """Parse Time LIST OF MATERIAL from extractable PDF text (before OCR)."""
    if text is None:
        if not pdf_path:
            return BomResult(method=None, confidence=0.0, notes=["No PDF text for Time BOM"])
        from quote_core.weight import _read_pdf_text

        text = _read_pdf_text(Path(pdf_path))
    if not _looks_like_time_bom_text(text or ""):
        return BomResult(method=None, confidence=0.0, notes=["No native Time-style BOM text"])

    bases = library_part_bases(
        Path(library_folder) if library_folder else None,
        related_pdf_names=related_pdf_names,
    )
    primary_base = None
    if pdf_path:
        m_pri = re.match(r"^(\d{4,7})", Path(pdf_path).stem.upper().replace(" ", ""))
        if m_pri:
            primary_base = m_pri.group(1)
    return parse_time_style_bom_texts(
        [text or ""],
        bases,
        bom_config=bom_config,
        primary_base=primary_base,
        source="native_time",
    )


def extract_bom(
    pdf_path: Path | str | None = None,
    *,
    text: str | None = None,
    library_folder: Path | str | None = None,
    related_pdf_names: list[str] | None = None,
    bom_config: str | None = None,
) -> BomResult:
    """
    Multi-strategy BOM extraction.

    1) Native MAC text/blocks (high confidence when present)
    2) Native PARTS LIST (Cummins / NGFS style)
    3) Native Time-style LIST OF MATERIAL (prefer text before OCR)
    4) OCR Time-style LIST OF MATERIAL (vector CAD drawings)
    """
    notes: list[str] = []
    native = extract_bom_from_native_mac(pdf_path, text=text)
    if native.rows and native.piece_count > 0 and native.confidence >= 0.9:
        return native
    if native.notes:
        notes.extend(native.notes)

    parts_list = extract_bom_from_parts_list(pdf_path, text=text)
    if parts_list.rows and parts_list.piece_count > 0:
        parts_list.notes = notes + list(parts_list.notes)
        return parts_list
    if parts_list.notes:
        notes.extend(parts_list.notes)

    native_time = extract_bom_from_native_time_style(
        pdf_path,
        text=text,
        library_folder=library_folder,
        related_pdf_names=related_pdf_names,
        bom_config=bom_config,
    )
    if native_time.rows and native_time.piece_count > 0:
        native_time.notes = notes + list(native_time.notes)
        return native_time
    if native_time.notes:
        notes.extend(native_time.notes)

    if pdf_path:
        ocr = extract_bom_from_ocr_time_style(
            pdf_path,
            library_folder=library_folder,
            related_pdf_names=related_pdf_names,
            bom_config=bom_config,
        )
        notes.extend(ocr.notes)
        if ocr.rows:
            ocr.notes = notes + list(ocr.notes)
            return ocr

    if native.rows:
        native.notes = notes + native.notes
        return native

    return BomResult(method=None, confidence=0.0, notes=notes or ["No BOM rows detected"])
