"""Parse a Kyle-confirmed Time LIST OF MATERIAL workbook (LOM.xlsx).

Prefer this over OCR when the library folder contains ``LOM.xlsx`` (or a
``*LOM*.xlsx`` / list-of-material workbook). Multi-dash qty columns use the
same ``-1`` default as Time drawings.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from quote_core.bom import BomResult, BomRow, normalize_part_no
from quote_core.bom_config import format_bom_config_label, normalize_bom_config

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_COL_RE = re.compile(r"([A-Z]+)")
_DASH_HEADER_RE = re.compile(r"^-?\s*([1-4])\s*$")
_QTY_DASH_RE = re.compile(r"(?:qty|quantity)?\s*[(\[]?\s*-?\s*([1-4])\s*[)\]]?\s*$", re.I)

_ITEM_HEADERS = {"ITEM", "ITEM NO", "ITEM NO.", "ITEM #", "BALLOON"}
_PART_HEADERS = {
    "PART",
    "PART NO",
    "PART NO.",
    "PART NUMBER",
    "PN",
    "P/N",
}
_DESC_HEADERS = {"DESCRIPTION", "DESC", "MATERIAL DESCRIPTION"}
_QTY_HEADERS = {"QTY", "QTY.", "QUANTITY", "PCS", "PIECES"}
_LOM_NAME_RE = re.compile(
    r"(^lom\.xlsx$)|(^list[-_ ]of[-_ ]materials?\.xlsx$)|(lom)",
    re.IGNORECASE,
)


def _col_index(cell_ref: str) -> int:
    m = _COL_RE.match((cell_ref or "").upper())
    if not m:
        return 0
    letters = m.group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    ctype = (cell.get("t") or "").strip()
    if ctype == "inlineStr":
        texts = [t.text or "" for t in cell.findall(".//m:t", _NS)]
        return "".join(texts).strip()
    value = cell.find("m:v", _NS)
    raw = (value.text or "").strip() if value is not None else ""
    if ctype == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return raw
    return raw


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    names = {n.lower(): n for n in zf.namelist()}
    target = names.get("xl/sharedstrings.xml")
    if not target:
        return []
    root = ET.fromstring(zf.read(target))
    out: list[str] = []
    for si in root.findall("m:si", _NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", _NS)))
    return out


def _sheet_path(zf: zipfile.ZipFile) -> str | None:
    names = zf.namelist()
    preferred = [n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
    preferred.sort()
    return preferred[0] if preferred else None


def read_xlsx_grid(path: Path | str) -> list[list[str]]:
    """Return the first sheet as a row-major grid of cell strings."""
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        shared = _load_shared_strings(zf)
        sheet = _sheet_path(zf)
        if not sheet:
            return []
        root = ET.fromstring(zf.read(sheet))
        grid: dict[tuple[int, int], str] = {}
        max_r = 0
        max_c = 0
        for row in root.findall("m:sheetData/m:row", _NS):
            try:
                ridx = int(row.get("r") or "0") - 1
            except ValueError:
                continue
            for cell in row.findall("m:c", _NS):
                ref = cell.get("r") or ""
                cidx = _col_index(ref)
                text = _cell_text(cell, shared).strip()
                if not text:
                    continue
                grid[(ridx, cidx)] = text
                max_r = max(max_r, ridx)
                max_c = max(max_c, cidx)
        out: list[list[str]] = []
        for r in range(max_r + 1):
            out.append([grid.get((r, c), "") for c in range(max_c + 1)])
        return out


def find_lom_xlsx(library_folder: Path | str | None) -> Path | None:
    """Return a Kyle-confirmed LOM workbook in the library folder, if any."""
    if not library_folder:
        return None
    folder = Path(library_folder)
    if not folder.is_dir():
        return None
    exact: list[Path] = []
    lomish: list[Path] = []
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() != ".xlsx":
            continue
        name = path.name
        if name.lower() == "lom.xlsx":
            exact.append(path)
        elif _LOM_NAME_RE.search(name):
            lomish.append(path)
    if exact:
        return sorted(exact, key=lambda p: p.name.lower())[0]
    if lomish:
        return sorted(lomish, key=lambda p: p.name.lower())[0]
    return None


def _norm_header(raw: str) -> str:
    return re.sub(r"\s+", " ", (raw or "").strip().upper().replace(".", ""))


def _dash_from_header(raw: str) -> str | None:
    text = _norm_header(raw).replace(" ", "")
    m = _DASH_HEADER_RE.match((raw or "").strip())
    if m:
        return m.group(1)
    m2 = _QTY_DASH_RE.match(text)
    if m2 and ("QTY" in text or text.startswith("-") or text in {"1", "2", "3", "4"}):
        # Bare "-1" already handled; "QTY-1" / "QTY(-1)"
        if "QTY" in text or "QUANTITY" in text:
            return m2.group(1)
    if re.fullmatch(r"-?[1-4]", (raw or "").strip()):
        return (raw or "").strip().lstrip("-")
    return None


def _classify_headers(row: list[str]) -> dict[str, Any] | None:
    item_col = None
    part_col = None
    desc_col = None
    qty_col = None
    dash_cols: dict[str, int] = {}
    for idx, raw in enumerate(row):
        if not raw:
            continue
        header = _norm_header(raw)
        dash = _dash_from_header(raw)
        if dash and header not in _ITEM_HEADERS | _PART_HEADERS | _DESC_HEADERS:
            dash_cols[dash] = idx
            continue
        if header in _ITEM_HEADERS:
            item_col = idx
        elif header in _PART_HEADERS:
            part_col = idx
        elif header in _DESC_HEADERS:
            desc_col = idx
        elif header in _QTY_HEADERS:
            qty_col = idx
    if part_col is None:
        return None
    if item_col is None and qty_col is None and not dash_cols:
        return None
    return {
        "item": item_col,
        "part": part_col,
        "desc": desc_col,
        "qty": qty_col,
        "dash": dash_cols,
    }


def _parse_qty_cell(raw: str) -> int:
    text = (raw or "").strip()
    if not text or text in {"-", "—", "–", "."}:
        return 0
    try:
        return max(0, int(float(text)))
    except ValueError:
        return 0


def extract_bom_from_lom_xlsx(
    path: Path | str,
    *,
    bom_config: str | None = None,
) -> BomResult:
    """Read LOM.xlsx and apply the Time dash qty column (default ``-1``)."""
    path = Path(path)
    notes: list[str] = []
    try:
        grid = read_xlsx_grid(path)
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        return BomResult(
            notes=[f"LOM.xlsx unreadable ({path.name}): {exc}"],
            confidence=0.0,
        )
    if not grid:
        return BomResult(notes=[f"LOM.xlsx {path.name} is empty"], confidence=0.0)

    header_idx = None
    mapping = None
    for i, row in enumerate(grid):
        found = _classify_headers(row)
        if found:
            header_idx = i
            mapping = found
            break
    if mapping is None or header_idx is None:
        return BomResult(
            notes=[f"LOM.xlsx {path.name} has no ITEM/PART/QTY header row"],
            confidence=0.0,
        )

    config = normalize_bom_config(bom_config)
    dash_cols: dict[str, int] = mapping["dash"]
    if dash_cols and not config:
        config = "1"
        notes.append("Multi-dash LOM — defaulted to -1 qty column")
    qty_col = mapping["qty"]
    if dash_cols:
        chosen = dash_cols.get(config or "1")
        if chosen is None:
            notes.append(
                f"LOM.xlsx has dash columns {sorted(dash_cols)} but not "
                f"{format_bom_config_label(config)} — used single QTY if present"
            )
        else:
            qty_col = chosen
            notes.append(
                f"Used LOM qty column {format_bom_config_label(config or '1')} "
                f"from {path.name}"
            )
    if qty_col is None:
        return BomResult(
            notes=[f"LOM.xlsx {path.name} has no qty column for this dash"],
            confidence=0.0,
        )

    rows: list[BomRow] = []
    for row in grid[header_idx + 1 :]:
        part_raw = row[mapping["part"]] if mapping["part"] < len(row) else ""
        part = normalize_part_no(part_raw)
        if not part:
            continue
        qty = _parse_qty_cell(row[qty_col] if qty_col < len(row) else "")
        if qty <= 0:
            continue
        item_raw = ""
        if mapping["item"] is not None and mapping["item"] < len(row):
            item_raw = row[mapping["item"]].strip()
        item: str | int | None = item_raw.upper() if item_raw else None
        desc = ""
        if mapping["desc"] is not None and mapping["desc"] < len(row):
            desc = row[mapping["desc"]].strip()
        rows.append(
            BomRow(
                item=item,
                qty=qty,
                part_no=part,
                description=desc,
                source="lom_xlsx",
                confidence=0.98,
            )
        )

    if not rows:
        return BomResult(
            notes=[f"LOM.xlsx {path.name} header found but no part rows"],
            confidence=0.0,
        )

    dedup: dict[str, BomRow] = {}
    for r in rows:
        prev = dedup.get(r.part_no)
        if prev is None or r.qty > prev.qty:
            dedup[r.part_no] = r
    rows = list(dedup.values())
    notes.insert(
        0,
        f"LOM.xlsx {path.name}: {len(rows)} part numbers, "
        f"{sum(r.qty for r in rows)} pieces (preferred over OCR)",
    )
    return BomResult(
        rows=rows,
        method="lom_xlsx",
        confidence=0.98,
        notes=notes,
    )
