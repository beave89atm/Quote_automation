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
    r"(?:QTY|ITEM).{0,48}(?:PART\s*NO\.?|PART\s*NUMBER|P/?N).{0,40}DESC",
    re.IGNORECASE | re.DOTALL,
)
_MULTI_QTY_HEADER_RE = re.compile(
    r"-4.{0,16}-3.{0,16}-2.{0,16}-1.{0,24}ITEM.{0,24}PART",
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
_HEADER_FOUND_NOTE = (
    "LIST OF MATERIAL header found but no table rows parsed "
    "— flag review; do not use whole-page regex or pad from nested files"
)


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
        r"\bITEM\b.{0,40}\bPART\b", blob, flags=re.IGNORECASE | re.DOTALL
    ):
        return True
    return False


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
        return qty, qty > 0
    raw = qty_cells[0] if qty_cells else (cells[0] if cells else "")
    qty = _parse_qty_cell(raw)
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
        part = normalize_part_no(rest[0]) or rest[0]
        desc_parts = rest[1:]
        # PART NO sometimes split: 102727 / -4
        if len(rest) >= 2 and not normalize_part_no(rest[0]):
            glued = normalize_part_no(rest[0] + rest[1])
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
        part = normalize_part_no(part_raw) or str(part_raw or "").upper()
        if not part or part in {"-", "PART", "PART NO."}:
            continue
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

    if not text or not text_has_material_list_grid(text):
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
    if layout is None or header_idx is None:
        return BomResult(
            method="table_material_list" if _TITLE_RE.search(text or "") else None,
            confidence=0.0,
            notes=["LIST OF MATERIAL title found but no QTY/ITEM/PART header row"],
        )
    above = cell_rows[:header_idx]
    below = cell_rows[header_idx + 1 :]
    parsed_below = parse_material_list_cells(below, bom_config=bom_config, header=cell_rows[header_idx])
    parsed_above = parse_material_list_cells(above, bom_config=bom_config, header=cell_rows[header_idx])
    if len(parsed_above.rows) > len(parsed_below.rows):
        return parsed_above
    return parsed_below


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
    header_idx = None
    header_words: list[dict[str, Any]] = []
    if layout is None:
        found = _find_header_in_word_rows(rows)
        if found:
            header_idx, layout, header_words = found
        else:
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
