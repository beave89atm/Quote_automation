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
_DASH_HEADER_RE = re.compile(r"^-?\s*([1-9])\s*$")
_QTY_DASH_RE = re.compile(r"(?:qty|quantity)?\s*[(\[]?\s*-?\s*([1-9])\s*[)\]]?\s*$", re.I)
_DRAWN_SHEET_NAMES = {"lom as drawn", "lom", "list of material"}
_NESTED_WELDMENT_RE = re.compile(r"WELDMENT|\bASSEMBLY\b|\bASM\b", re.IGNORECASE)

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
# Time LOM uses QTY or dash columns. Do not treat PCS/PIECES as qty —
# drawings print paint notes like "20 PLCS" that are not BOM totals.
_QTY_HEADERS = {"QTY", "QTY.", "QUANTITY"}
_LOM_NAME_RE = re.compile(
    r"(^lom\.xlsx$)|(^list[-_ ]of[-_ ]materials?\.xlsx$)|(^.*-lom\.xlsx$)|(lom)",
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


def _zip_name_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """Lowercased, slash-normalized zip names → actual zip member."""
    out: dict[str, str] = {}
    for name in zf.namelist():
        key = name.replace("\\", "/").lower().lstrip("/")
        out[key] = name
    return out


def normalize_opc_part(target: str) -> str:
    """Resolve an OOXML Relationship Target to a package part (never ``xl/xl/...``).

    Excel writes ``Target="worksheets/sheet1.xml"`` (relative to ``xl/``) or
    ``Target="/xl/worksheets/sheet1.xml"`` (absolute). Prefixing ``xl/`` onto
    the absolute form produced ``xl/xl/worksheets/sheet1.xml`` (job 91).
    """
    text = (target or "").replace("\\", "/").strip()
    text = text.split("?")[0].split("#")[0]
    text = text.lstrip("/")
    text = re.sub(r"^\./", "", text)
    while text.lower().startswith("xl/xl/"):
        text = text[3:]
    if text.lower().startswith("xl/"):
        return text
    while text.startswith("../"):
        text = text[3:]
    return f"xl/{text}" if text else ""


def resolve_zip_part(zf: zipfile.ZipFile, target: str) -> str | None:
    """Return the real zip member for an OPC target, or None."""
    names = _zip_name_map(zf)
    norm = normalize_opc_part(target)
    if not norm:
        return None
    found = names.get(norm.lower())
    if found:
        return found
    leaf = norm.rsplit("/", 1)[-1].lower()
    if leaf:
        for key, actual in names.items():
            if key == leaf or key.endswith("/" + leaf):
                return actual
    return None


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    target = resolve_zip_part(zf, "xl/sharedStrings.xml")
    if not target:
        return []
    root = ET.fromstring(zf.read(target))
    out: list[str] = []
    for si in root.findall("m:si", _NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", _NS)))
    return out


def _sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return (sheet_name, xml_path) in workbook order."""
    names = _zip_name_map(zf)
    wb_name = names.get("xl/workbook.xml")
    rels_name = names.get("xl/_rels/workbook.xml.rels")
    if not wb_name or not rels_name:
        preferred = [
            n
            for n in zf.namelist()
            if "worksheets/sheet" in n.replace("\\", "/").lower() and n.lower().endswith(".xml")
        ]
        preferred.sort()
        return [("LOM", preferred[0])] if preferred else []
    rel_ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    rid_to_target: dict[str, str] = {}
    rel_root = ET.fromstring(zf.read(rels_name))
    for rel in rel_root.findall("r:Relationship", rel_ns):
        rid = rel.get("Id") or ""
        target = rel.get("Target") or ""
        if rid and target:
            resolved = resolve_zip_part(zf, target)
            if resolved:
                rid_to_target[rid] = resolved
    wb_ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    wb = ET.fromstring(zf.read(wb_name))
    out: list[tuple[str, str]] = []
    for sheet in wb.findall("m:sheets/m:sheet", wb_ns):
        name = sheet.get("name") or "LOM"
        rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") or ""
        target = rid_to_target.get(rid)
        if target:
            out.append((name, target))
    return out


def _sheet_path(zf: zipfile.ZipFile, sheet_name: str | None = None) -> str | None:
    sheets = _sheet_targets(zf)
    if not sheets:
        return None
    if sheet_name:
        want = sheet_name.strip().lower()
        for name, target in sheets:
            if name.strip().lower() == want:
                return target
        return None
    for name, target in sheets:
        if name.strip().lower() in _DRAWN_SHEET_NAMES:
            return target
    return sheets[0][1]


def read_xlsx_grid(path: Path | str, *, sheet_name: str | None = None) -> list[list[str]]:
    """Return the ``LOM as drawn`` sheet (else first sheet) as a cell grid."""
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        shared = _load_shared_strings(zf)
        sheet = _sheet_path(zf, sheet_name)
        if sheet and "xl/xl/" in sheet.replace("\\", "/").lower():
            sheet = resolve_zip_part(zf, sheet)
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


def _scan_lom_in_folder(folder: Path, *, part_key: str | None) -> list[Path]:
    exact: list[Path] = []
    dashed: list[Path] = []
    lomish: list[Path] = []
    key = re.sub(r"[^0-9A-Za-z-]", "", (part_key or "")).upper()
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() != ".xlsx":
            continue
        name = path.name
        lower = name.lower()
        if lower == "lom.xlsx":
            exact.append(path)
            continue
        if lower.endswith("-lom.xlsx") or lower.endswith("_lom.xlsx"):
            stem = re.sub(r"[-_]lom$", "", path.stem, flags=re.I)
            stem_key = re.sub(r"[^0-9A-Za-z-]", "", stem).upper()
            if key and (stem_key == key or stem_key.startswith(key) or key.startswith(stem_key)):
                dashed.insert(0, path)
            else:
                dashed.append(path)
            continue
        if _LOM_NAME_RE.search(name):
            lomish.append(path)
    return dashed + exact + lomish


def find_lom_xlsx(
    library_folder: Path | str | None = None,
    *more_folders: Path | str | None,
    part_key: str | None = None,
) -> Path | None:
    """Return a Kyle-confirmed ``*LOM.xlsx`` from the job or library folder."""
    folders: list[Path] = []
    for raw in (library_folder, *more_folders):
        if not raw:
            continue
        folder = Path(raw)
        if folder.is_dir() and folder not in folders:
            folders.append(folder)
    found: list[Path] = []
    for folder in folders:
        found.extend(_scan_lom_in_folder(folder, part_key=part_key))
    if not found:
        return None
    return found[0]


def _norm_header(raw: str) -> str:
    return re.sub(r"\s+", " ", (raw or "").strip().upper().replace(".", ""))


def _dash_from_header(raw: str) -> str | None:
    text = _norm_header(raw).replace(" ", "")
    m = _DASH_HEADER_RE.match((raw or "").strip())
    if m:
        return m.group(1)
    m2 = _QTY_DASH_RE.match(text)
    if m2 and ("QTY" in text or text.startswith("-") or text in set("123456789")):
        # Bare "-1" already handled; "QTY-1" / "QTY(-1)"
        if "QTY" in text or "QUANTITY" in text:
            return m2.group(1)
    if re.fullmatch(r"-?[1-9]", (raw or "").strip()):
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
    if not text or text in {"-", "—", "–", ".", "·"}:
        return 0
    # Paint notes ("20 PLCS") and unread cells are not qty 1.
    if re.search(r"[A-Za-z]", text):
        return 0
    try:
        return max(0, int(float(text)))
    except ValueError:
        return 0


def _rows_from_grid(
    grid: list[list[str]],
    *,
    bom_config: str | None,
    notes: list[str],
    source_label: str,
) -> list[BomRow] | BomResult:
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
            notes=[f"LOM.xlsx {source_label} has no ITEM/PART/QTY header row"],
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
                f"from {source_label}"
            )
    if qty_col is None:
        return BomResult(
            notes=[f"LOM.xlsx {source_label} has no qty column for this dash"],
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
    return rows


def extract_bom_from_lom_xlsx(
    path: Path | str,
    *,
    bom_config: str | None = None,
) -> BomResult:
    """Read LOM.xlsx and apply the Time dash qty column (default ``-1``).

    Nested tabs named after a parent WELDMENT/ASSEMBLY row are rolled up.
    Child tables that are not weldments (e.g. 105098 / 103603-1) stay unused.
    An empty weldment tab is an empty L2 shell and is noted — not a 1-pc default.
    """
    path = Path(path)
    notes: list[str] = []
    try:
        grid = read_xlsx_grid(path)
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError) as exc:
        return BomResult(
            notes=[f"LOM.xlsx unreadable ({path.name}): {exc}"],
            confidence=0.0,
        )
    if not grid:
        return BomResult(notes=[f"LOM.xlsx {path.name} is empty"], confidence=0.0)

    parsed = _rows_from_grid(
        grid, bom_config=bom_config, notes=notes, source_label=path.name
    )
    if isinstance(parsed, BomResult):
        return parsed
    rows = parsed
    if not rows:
        return BomResult(
            notes=[f"LOM.xlsx {path.name} header found but no part rows"],
            confidence=0.0,
        )

    try:
        with zipfile.ZipFile(path) as zf:
            sheet_names = {name.strip(): name for name, _target in _sheet_targets(zf)}
    except (OSError, zipfile.BadZipFile):
        sheet_names = {}
    skip_names = {n.lower() for n in _DRAWN_SHEET_NAMES}
    skip_names.update(n.lower() for n in sheet_names if n.lower().endswith(" quote"))

    for parent in list(rows):
        if not _NESTED_WELDMENT_RE.search(parent.description or ""):
            continue
        child_key = (parent.part_no or "").strip()
        child_sheet = None
        for raw_name, stored in sheet_names.items():
            if raw_name.lower() in skip_names:
                continue
            if raw_name.strip().lower() == child_key.lower():
                child_sheet = stored
                break
        if not child_sheet:
            continue
        try:
            child_grid = read_xlsx_grid(path, sheet_name=child_sheet)
        except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError):
            child_grid = []
        child_notes: list[str] = []
        child_parsed = _rows_from_grid(
            child_grid,
            bom_config=bom_config,
            notes=child_notes,
            source_label=f"{path.name}:{child_sheet}",
        )
        if isinstance(child_parsed, BomResult) or not child_parsed:
            notes.append(f"empty L2 shell: {child_key}")
            continue
        notes.append(
            f"Rolled up nested LOM tab {child_sheet}: "
            f"{len(child_parsed)} part numbers"
        )
        notes.extend(child_notes)
        rows.extend(child_parsed)

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


def _col_letter(idx: int) -> str:
    n = idx + 1
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _sheet_xml(rows: list[list[str]]) -> str:
    from xml.sax.saxutils import escape

    sheet_rows = []
    for r_i, row in enumerate(rows, start=1):
        cells = []
        for c_i, val in enumerate(row):
            ref = f"{_col_letter(c_i)}{r_i}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(val))}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )


def _quote_sheet_rows(drawn: list[list[str]], *, bom_config: str | None) -> list[list[str]]:
    """Selected-dash view: QTY / ITEM / PART NO / DESCRIPTION."""
    if not drawn:
        return [["QTY", "ITEM", "PART NO", "DESCRIPTION"]]
    mapping = None
    header_idx = 0
    for i, row in enumerate(drawn):
        found = _classify_headers(row)
        if found:
            mapping = found
            header_idx = i
            break
    config = normalize_bom_config(bom_config) or "1"
    out = [["QTY", "ITEM", "PART NO", "DESCRIPTION"]]
    if mapping is None:
        return out
    qty_col = mapping["qty"]
    if mapping["dash"]:
        qty_col = mapping["dash"].get(config, qty_col)
    if qty_col is None:
        return out
    for row in drawn[header_idx + 1 :]:
        part_raw = row[mapping["part"]] if mapping["part"] < len(row) else ""
        if not normalize_part_no(part_raw):
            continue
        qty = _parse_qty_cell(row[qty_col] if qty_col < len(row) else "")
        if qty <= 0:
            continue
        item = ""
        if mapping["item"] is not None and mapping["item"] < len(row):
            item = row[mapping["item"]]
        desc = ""
        if mapping["desc"] is not None and mapping["desc"] < len(row):
            desc = row[mapping["desc"]]
        out.append([str(qty), item, part_raw, desc])
    return out


def write_lom_xlsx(
    path: Path | str,
    rows: list[list[str]],
    *,
    part_key: str | None = None,
    bom_config: str | None = None,
    extra_sheets: dict[str, list[list[str]]] | None = None,
) -> Path:
    """Write Kyle format: ``LOM as drawn`` plus a ``{PN} quote`` dash sheet."""
    from xml.sax.saxutils import escape

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    quote_name = f"{(part_key or 'drawing').strip() or 'drawing'} quote"
    quote_rows = _quote_sheet_rows(rows, bom_config=bom_config)
    named: list[tuple[str, list[list[str]]]] = [("LOM as drawn", rows)]
    for extra_name, extra_rows in (extra_sheets or {}).items():
        label = (extra_name or "sheet").strip()[:31] or "sheet"
        named.append((label, extra_rows))
    named.append((quote_name[:31], quote_rows))

    sheet_tags = []
    rel_tags = []
    override_tags = [
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    ]
    for i, (name, _grid) in enumerate(named, start=1):
        sheet_tags.append(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
        )
        rel_tags.append(
            '<Relationship Id="rId'
            f'{i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
        )
        override_tags.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{''.join(sheet_tags)}</sheets></workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{''.join(rel_tags)}</Relationships>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    ctypes = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f"{''.join(override_tags)}</Types>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", ctypes)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        for i, (_name, grid) in enumerate(named, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(grid))
    return path
