"""Emit LIST OF MATERIAL as QTY / ITEM / PART NO / DESCRIPTION (.xlsx).

Minimal OOXML via zipfile — no openpyxl. Same four columns as 102728-1-LOM.xlsx.
"""

from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from quote_core.bom_table import item_sort_key

LOM_COLUMNS = ("QTY", "ITEM", "PART NO", "DESCRIPTION")
LOM_SUFFIX = "-LOM.xlsx"
PARENT_SHEET_NAME = "LIST OF MATERIAL"
_SHEET_NAME_BAD = re.compile(r'[:\\/?*\[\]]')
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_OD_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

_CONTENT_TYPES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="{_NS_CT}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""

_ROOT_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{_NS_PKG_REL}">
  <Relationship Id="rId1" Type="{_NS_OD_REL}/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

_WORKBOOK = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{_NS_MAIN}" xmlns:r="{_NS_OD_REL}">
  <sheets>
    <sheet name="LIST OF MATERIAL" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

_WORKBOOK_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{_NS_PKG_REL}">
  <Relationship Id="rId1" Type="{_NS_OD_REL}/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""


def lom_xlsx_name_for_pdf(pdf_path: Path | str) -> str:
    return f"{Path(pdf_path).stem}{LOM_SUFFIX}"


def lom_xlsx_path_for_pdf(pdf_path: Path | str) -> Path:
    path = Path(pdf_path)
    return path.with_name(lom_xlsx_name_for_pdf(path))


def lom_xlsx_names_for_pdf(pdf_path: Path | str) -> list[str]:
    """``Time 102728- Weldment.pdf`` → stem-LOM.xlsx and ``102728-1-LOM.xlsx``."""
    path = Path(pdf_path)
    names = [lom_xlsx_name_for_pdf(path)]
    from quote_core.bom_table import job_weldment_key_from_path

    key = job_weldment_key_from_path(path)
    if key:
        names.append(f"{key}-1{LOM_SUFFIX}")
        names.append(f"{key}{LOM_SUFFIX}")
    out: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def _desktop_dirs() -> list[Path]:
    """USERPROFILE Desktop plus OneDrive / OneDriveCommercial / ``OneDrive - *``."""
    homes: list[Path] = []
    for key in ("USERPROFILE", "HOME"):
        raw = os.environ.get(key)
        if raw:
            homes.append(Path(raw))
    homes.append(Path.home())
    out: list[Path] = []
    seen: set[Path] = set()

    def _add(folder: Path) -> None:
        if folder in seen:
            return
        seen.add(folder)
        out.append(folder)

    for key in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        raw = os.environ.get(key)
        if raw:
            _add(Path(raw) / "Desktop")
    for home in homes:
        _add(home / "Desktop")
        _add(home / "OneDrive" / "Desktop")
        try:
            for folder in home.glob("OneDrive*"):
                if folder.is_dir():
                    _add(folder / "Desktop")
        except OSError:
            continue
    return out


def is_desktop_lom_path(path: Path | str) -> bool:
    """Never write Kyle's Desktop sheets (102728-1-LOM.xlsx)."""
    dest = Path(path)
    try:
        resolved = dest.resolve()
    except OSError:
        resolved = dest
    if dest.parent.name.lower() == "desktop":
        return True
    for folder in _desktop_dirs():
        try:
            root = folder.resolve()
        except OSError:
            root = folder
        try:
            if resolved.is_relative_to(root):
                return True
        except ValueError:
            continue
    return False


def _workbook_has_lom_rows(path: Path) -> bool:
    try:
        _header, data = read_lom_xlsx(path, drop_junk=False)
    except Exception:  # noqa: BLE001
        return False
    return any(str(rec.get("PART NO") or "").strip() for rec in data)


def find_existing_lom_xlsx(pdf_path: Path | str | None) -> Path | None:
    """Desktop / job folder / prior extract. Do not invent a workbook."""
    if not pdf_path:
        return None
    pdf = Path(pdf_path)
    names = lom_xlsx_names_for_pdf(pdf)
    stem_name = lom_xlsx_name_for_pdf(pdf)
    key_names = [n for n in names if n != stem_name]
    desktop = [d for d in _desktop_dirs() if d.is_dir()]
    ordered: list[Path] = []
    # Confirmed Desktop ``102728-1-LOM.xlsx`` beats a TEMP sibling from OCR.
    for folder in desktop:
        ordered.extend(folder / name for name in key_names)
    if pdf.parent:
        ordered.extend(pdf.parent / name for name in names)
    for folder in desktop:
        ordered.append(folder / stem_name)
    seen: set[Path] = set()
    for cand in ordered:
        try:
            key = cand.resolve()
        except OSError:
            key = cand
        if key in seen:
            continue
        seen.add(key)
        if cand.is_file() and _workbook_has_lom_rows(cand):
            return cand
    return None


def _xml_text(value: Any) -> str:
    return escape(str(value if value is not None else ""), {'"': "&quot;"})


def _row_fields(row: Any) -> tuple[Any, Any, Any, Any]:
    if hasattr(row, "qty"):
        return row.qty, row.item, row.part_no, row.description
    return (
        row.get("qty"),
        row.get("item"),
        row.get("part_no") or row.get("part_no."),
        row.get("description"),
    )


def _sort_rows(rows: list[Any]) -> list[Any]:
    def key(row: Any) -> tuple:
        item = row.item if hasattr(row, "item") else (row or {}).get("item")
        return item_sort_key(str(item or ""))

    return sorted(rows, key=key)


def _inline_cell(ref: str, text: Any) -> str:
    return f'<c r="{ref}" t="inlineStr"><is><t>{_xml_text(text)}</t></is></c>'


def _qty_cell(ref: str, qty: Any) -> str:
    try:
        number = int(qty)
        return f'<c r="{ref}"><v>{number}</v></c>'
    except (TypeError, ValueError):
        return _inline_cell(ref, qty)


def _sheet_xml(rows: list[Any]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{_NS_MAIN}"><sheetData>',
        "<row r=\"1\">"
        f"{_inline_cell('A1', LOM_COLUMNS[0])}"
        f"{_inline_cell('B1', LOM_COLUMNS[1])}"
        f"{_inline_cell('C1', LOM_COLUMNS[2])}"
        f"{_inline_cell('D1', LOM_COLUMNS[3])}"
        "</row>",
    ]
    for i, row in enumerate(_sort_rows(rows), start=2):
        qty, item, part_no, desc = _row_fields(row)
        parts.append(
            f'<row r="{i}">'
            f"{_qty_cell(f'A{i}', qty)}"
            f"{_inline_cell(f'B{i}', item)}"
            f"{_inline_cell(f'C{i}', part_no)}"
            f"{_inline_cell(f'D{i}', desc)}"
            "</row>"
        )
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def lom_sheet_name(part_no: str | None) -> str:
    """Excel tab name for a child weldment PN (max 31, no :\\/?*[])."""
    raw = re.sub(r"[^A-Z0-9-]", "", str(part_no or "").upper()).strip("-") or "BOM"
    cleaned = _SHEET_NAME_BAD.sub("-", raw)[:31].strip("'")
    return cleaned or "BOM"


def row_as_lom_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "qty"):
        return {
            "item": getattr(row, "item", "") or "",
            "qty": getattr(row, "qty", 0) or 0,
            "part_no": getattr(row, "part_no", "") or "",
            "description": getattr(row, "description", "") or "",
        }
    blob = row or {}
    return {
        "item": blob.get("item") or "",
        "qty": blob.get("qty") or 0,
        "part_no": blob.get("part_no") or blob.get("part_no.") or "",
        "description": blob.get("description") or "",
    }


def nested_tabs_from_children(children: list[dict[str, Any]] | None) -> list[tuple[str, list[Any]]]:
    """Depth-first child LOM tabs. Parent sheet is not included."""
    tabs: list[tuple[str, list[Any]]] = []
    seen: set[str] = set()
    for child in children or []:
        if not isinstance(child, dict):
            continue
        rows = list(child.get("rows") or [])
        status = str(child.get("status") or "")
        name = lom_sheet_name(child.get("lom_sheet") or child.get("part_no"))
        if status == "clipped" and rows and name not in seen:
            seen.add(name)
            tabs.append((name, rows))
        for extra in nested_tabs_from_children(child.get("nested_children") or []):
            if extra[0] not in seen:
                seen.add(extra[0])
                tabs.append(extra)
    return tabs


def extra_sheets_from_takeoff(takeoff: dict[str, Any] | None) -> list[tuple[str, list[Any]]]:
    blob = takeoff or {}
    drivers = blob.get("fitup_drivers") or {}
    weight = drivers.get("weight_calc") or {}
    for source in (
        weight.get("bom"),
        weight.get("pdf_bom"),
        blob.get("bom"),
        blob.get("pdf_bom"),
    ):
        if isinstance(source, dict) and source.get("nested_children"):
            return nested_tabs_from_children(source.get("nested_children"))
    return nested_tabs_from_children(blob.get("nested_children"))


def _content_types_xml(sheet_count: int) -> str:
    overrides = [
        f'  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    ]
    for i in range(1, sheet_count + 1):
        overrides.append(
            f'  <Override PartName="/xl/worksheets/sheet{i}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<Types xmlns="{_NS_CT}">\n'
        f'  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        f'  <Default Extension="xml" ContentType="application/xml"/>\n'
        + "\n".join(overrides)
        + "\n</Types>\n"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = []
    for i, name in enumerate(sheet_names, start=1):
        sheets.append(
            f'    <sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>'
        )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<workbook xmlns="{_NS_MAIN}" xmlns:r="{_NS_OD_REL}">\n'
        f"  <sheets>\n"
        + "\n".join(sheets)
        + "\n  </sheets>\n</workbook>\n"
    )


def _workbook_rels_xml(sheet_count: int) -> str:
    rels = [
        f'  <Relationship Id="rId{i}" Type="{_NS_OD_REL}/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, sheet_count + 1)
    ]
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<Relationships xmlns="{_NS_PKG_REL}">\n'
        + "\n".join(rels)
        + "\n</Relationships>\n"
    )


def write_lom_xlsx(
    path: Path | str,
    rows: list[Any],
    extra_sheets: list[tuple[str, list[Any]]] | None = None,
) -> Path:
    """Write the four-column LOM grid. Child weldment LOMs are extra tabs.

    First tab is always LIST OF MATERIAL (parent takeoff). Do not merge
    child rows onto that sheet. A is first in the sheet (page has A at bottom).
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    extras = list(extra_sheets or [])
    if not extras:
        sheet = _sheet_xml(list(rows or []))
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
            zf.writestr("_rels/.rels", _ROOT_RELS)
            zf.writestr("xl/workbook.xml", _WORKBOOK)
            zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
            zf.writestr("xl/worksheets/sheet1.xml", sheet)
        return dest

    names = [PARENT_SHEET_NAME]
    bodies = [_sheet_xml(list(rows or []))]
    seen = {PARENT_SHEET_NAME.upper()}
    for raw_name, extra_rows in extras:
        name = lom_sheet_name(raw_name)
        if name.upper() in seen:
            continue
        seen.add(name.upper())
        names.append(name)
        bodies.append(_sheet_xml(list(extra_rows or [])))
    count = len(names)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml(count))
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("xl/workbook.xml", _workbook_xml(names))
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(count))
        for i, body in enumerate(bodies, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", body)
    return dest


def write_parent_lom_with_nested_tabs(path: Path | str, bom: Any) -> Path:
    """Rewrite the parent workbook with child LOM tabs. Remove sibling child xlsx."""
    dest = Path(path)
    rows = getattr(bom, "rows", None)
    if rows is None and isinstance(bom, dict):
        rows = bom.get("rows") or bom.get("bom_rows")
    children = list(getattr(bom, "nested_children", None) or [])
    if isinstance(bom, dict):
        children = list(bom.get("nested_children") or children)
    tabs = nested_tabs_from_children(children)
    write_lom_xlsx(dest, list(rows or []), extra_sheets=tabs)
    for name, _rows in tabs:
        sibling = dest.parent / f"{name}-LOM.xlsx"
        if sibling.resolve() != dest.resolve() and sibling.is_file():
            try:
                sibling.unlink()
            except OSError:
                pass
    notes = list(getattr(bom, "notes", None) or [])

    def _stamp(node: dict[str, Any]) -> None:
        if node.get("status") != "clipped":
            for inner in node.get("nested_children") or []:
                if isinstance(inner, dict):
                    _stamp(inner)
            return
        sheet = lom_sheet_name(node.get("lom_sheet") or node.get("part_no"))
        node["lom_xlsx"] = dest.name
        node["lom_sheet"] = sheet
        part_no = str(node.get("part_no") or sheet)
        note = f"Clipped child LOM {part_no} from library → tab {sheet} on {dest.name}"
        for i, existing in enumerate(notes):
            if existing.startswith(f"Clipped child LOM {part_no}"):
                notes[i] = note
                break
        else:
            notes.append(note)
        for inner in node.get("nested_children") or []:
            if isinstance(inner, dict):
                _stamp(inner)

    for child in children:
        if isinstance(child, dict):
            _stamp(child)
    if hasattr(bom, "notes"):
        bom.notes = notes
        bom.nested_children = children
        bom.lom_xlsx = dest.name
    return dest


def bom_is_lom_clip(bom: Any) -> bool:
    """True when rows came from a LIST OF MATERIAL grid clip, not a guessed BOM."""
    if bom is None:
        return False
    method = str(getattr(bom, "method", None) or "")
    source = str(getattr(bom, "source", None) or "")
    lom = getattr(bom, "lom_xlsx", None)
    if isinstance(bom, dict):
        method = str(bom.get("method") or method)
        source = str(bom.get("source") or source)
        lom = bom.get("lom_xlsx") or lom
    if lom:
        return True
    if source == "lom_xlsx":
        return True
    return method.startswith("table_")


def takeoff_has_lom_clip(takeoff: dict[str, Any] | None) -> bool:
    blob = takeoff or {}
    if blob.get("lom_xlsx"):
        return True
    drivers = blob.get("fitup_drivers") or {}
    weight = drivers.get("weight_calc") or {}
    for source in (
        weight.get("bom"),
        weight.get("pdf_bom"),
        blob.get("bom"),
        blob.get("pdf_bom"),
    ):
        if bom_is_lom_clip(source):
            return True
    return False


def write_lom_xlsx_for_bom(pdf_path: Path | str | None, bom: Any) -> Path | None:
    if not pdf_path:
        return None
    existing = find_existing_lom_xlsx(pdf_path)
    if existing:
        return existing
    dest = lom_xlsx_path_for_pdf(pdf_path)
    if dest.is_file() or is_desktop_lom_path(dest):
        return dest if dest.is_file() else None
    if not bom_is_lom_clip(bom):
        return None
    rows = getattr(bom, "rows", None)
    if rows is None and isinstance(bom, dict):
        rows = bom.get("rows") or bom.get("bom_rows")
    if not rows:
        return None
    return write_lom_xlsx(dest, rows)


def rows_from_takeoff(takeoff: dict[str, Any] | None) -> list[Any]:
    blob = takeoff or {}
    drivers = blob.get("fitup_drivers") or {}
    weight = drivers.get("weight_calc") or {}
    for source in (
        weight.get("bom"),
        weight.get("pdf_bom"),
        blob.get("bom"),
        blob.get("pdf_bom"),
    ):
        if isinstance(source, dict):
            rows = source.get("rows") or source.get("bom_rows")
            if rows:
                return list(rows)
    if blob.get("bom_rows"):
        return list(blob["bom_rows"])
    return []


def write_lom_xlsx_for_job(pdf_path: Path | str | None, takeoff: dict[str, Any] | None) -> Path | None:
    """Write only when a LIST OF MATERIAL was clipped. No LOM → no xlsx.

    An existing Desktop / job-folder workbook is the quote. Do not overwrite.
    """
    if not pdf_path:
        return None
    existing = find_existing_lom_xlsx(pdf_path)
    if existing:
        return existing
    dest = lom_xlsx_path_for_pdf(pdf_path)
    if dest.is_file():
        return dest
    if is_desktop_lom_path(dest):
        return None
    if not takeoff_has_lom_clip(takeoff):
        return None
    rows = rows_from_takeoff(takeoff)
    if not rows:
        return None
    return write_lom_xlsx(dest, rows, extra_sheets=extra_sheets_from_takeoff(takeoff))


_INCH_NOTE_RE = re.compile(r'^(\d+)\s*["″”]$')
_FOOTER_TALLY_RE = re.compile(
    r"(?:"
    r"\bunique\s+p/?n'?s?\b"
    r"|\b\d{1,3}\s*p/?n'?s?\b"
    r"|\b\d{1,3}\s*rows?\b"
    r"|\bpcs\b"
    r"|\bqty\s*[:=]\s*\d+"
    r"|\bpiece(?:s|\s*count)\b"
    r")",
    re.IGNORECASE,
)
_BARE_COUNT_RE = re.compile(r"^\d{1,3}$")


def _qty_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _xlsx_qty_from_cell(raw: Any) -> tuple[int, bool]:
    """Return (qty, is_inch_note).

    ``10"`` / ``10″`` is a size note (1004611 S gasket), not 10 pcs and
    not unread. Keep the row as qty 1.
    """
    text = str(raw or "").strip()
    if _INCH_NOTE_RE.fullmatch(text):
        return 1, True
    return _qty_int(text), False


def sheet_records(path: Path | str, *, bom_config: str | None = None) -> list[dict[str, Any]]:
    """Four-column LOM.xlsx as quote rows. Qty unread/blank is 0."""
    _header, data = read_lom_xlsx(path, bom_config=bom_config)
    return [
        {
            "item": rec.get("ITEM") or "",
            "qty": _qty_int(rec.get("QTY")),
            "part_no": rec.get("PART NO") or "",
            "description": rec.get("DESCRIPTION") or "",
        }
        for rec in data
    ]


def apply_lom_xlsx_to_takeoff(
    takeoff: dict[str, Any] | None,
    path: Path | str,
    *,
    bom_config: str | None = None,
) -> dict[str, Any]:
    """Replace takeoff BOM JSON with the written sheet. No side channel."""
    dest = Path(path)
    blob = dict(takeoff or {})
    dash = bom_config if bom_config is not None else blob.get("bom_config")
    records = sheet_records(dest, bom_config=dash)
    prior = rows_from_takeoff(blob)
    weights: dict[tuple[str, str], Any] = {}
    for row in prior:
        if hasattr(row, "item"):
            key = (str(row.item or ""), str(row.part_no or ""))
            weights[key] = getattr(row, "unit_weight_lb", None)
        elif isinstance(row, dict):
            key = (str(row.get("item") or ""), str(row.get("part_no") or ""))
            weights[key] = row.get("unit_weight_lb")
    rows = []
    bom_rows = []
    for rec in records:
        key = (str(rec["item"]), str(rec["part_no"]))
        unit = weights.get(key)
        rows.append(
            {
                **rec,
                "unit_weight_lb": unit,
                "source": "lom_xlsx",
                "confidence": 1.0,
            }
        )
        bom_rows.append({**rec, "unit_weight_lb": unit})
    piece = sum(max(0, int(r["qty"] or 0)) for r in records)
    part_count = len({r["part_no"] for r in records if r["part_no"]})
    drivers = dict(blob.get("fitup_drivers") or {})
    weight = dict(drivers.get("weight_calc") or {})
    existing = weight.get("bom") or weight.get("pdf_bom") or blob.get("bom") or {}
    method = str((existing or {}).get("method") or "") or "table_lom_xlsx"
    notes = list((existing or {}).get("notes") or [])
    sourced = f"Quote BOM sourced from {dest.name}"
    if sourced not in notes:
        notes.append(sourced)
    nested_children = refresh_nested_children_from_xlsx(
        dest, list((existing or {}).get("nested_children") or [])
    )
    bom_blob = {
        "rows": rows,
        "bom_rows": bom_rows,
        "method": method,
        "confidence": (existing or {}).get("confidence"),
        "notes": notes,
        "assembly_weight_lb": (existing or {}).get("assembly_weight_lb"),
        "grid_row_count": (existing or {}).get("grid_row_count") or 0,
        "lom_xlsx": dest.name,
        "source": "lom_xlsx",
        "piece_count": piece,
        "part_number_count": part_count,
        "component_weights_lb": (existing or {}).get("component_weights_lb") or [],
        "nested_children": nested_children,
    }
    weight["bom"] = bom_blob
    weight["pdf_bom"] = bom_blob
    weight["piece_count"] = piece
    weight["part_number_count"] = part_count
    if piece > 0:
        drivers["part_count"] = piece
        drivers["piece_count"] = piece
    drivers["weight_calc"] = weight
    blob["fitup_drivers"] = drivers
    blob["bom"] = bom_blob
    blob["lom_xlsx"] = dest.name
    try:
        blob["lom_sheets"] = list_lom_sheet_names(dest)
        bom_blob["lom_sheets"] = blob["lom_sheets"]
    except (OSError, KeyError, ET.ParseError):
        blob["lom_sheets"] = [PARENT_SHEET_NAME]
        bom_blob["lom_sheets"] = blob["lom_sheets"]
    return blob


def _sheet_part_paths(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    """[(sheet name, zip path), ...] in workbook order."""
    try:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    except KeyError:
        return [(PARENT_SHEET_NAME, "xl/worksheets/sheet1.xml")]
    rid_to_target: dict[str, str] = {}
    for rel in rels:
        rid = rel.get("Id") or ""
        target = (rel.get("Target") or "").replace("\\", "/")
        if rid and target:
            rid_to_target[rid] = target
    out: list[tuple[str, str]] = []
    for sheet in wb.findall(f"{{{_NS_MAIN}}}sheets/{{{_NS_MAIN}}}sheet"):
        name = sheet.get("name") or PARENT_SHEET_NAME
        rid = sheet.get(f"{{{_NS_OD_REL}}}id") or ""
        target = rid_to_target.get(rid, "worksheets/sheet1.xml")
        if target.startswith("/"):
            zip_path = target.lstrip("/")
        elif target.startswith("xl/"):
            zip_path = target
        else:
            zip_path = "xl/" + target
        out.append((name, zip_path))
    return out or [(PARENT_SHEET_NAME, "xl/worksheets/sheet1.xml")]


def _col_index_from_ref(ref: str) -> int | None:
    letters = "".join(ch for ch in str(ref or "") if ch.isalpha())
    if not letters:
        return None
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return max(0, n - 1)


# Time as-drawn tabs: ``QTY -1``, ``QTY-1``, ``-1``, or the dash PN itself.
_QTY_DASH_HEADER_RE = re.compile(
    r"^(?:QTY|QTY\.|QTYS|QUANTITY)[\s.\-–—]*([1-4])$",
    re.IGNORECASE,
)
_BARE_DASH_QTY_RE = re.compile(r"^\[?-([1-4])\]?$")
_PN_DASH_QTY_RE = re.compile(r"^P?(\d{5,7})-([1-4])$", re.IGNORECASE)


def _qty_header_info(cell: str) -> tuple[bool, str | None, str | None]:
    """Qty header → (is_qty, dash or None, header PN or None).

    ``QTY`` / ``QUANTITY`` is the single qty column (dash is None).
    ``QTY -1``, ``QTY-1``, ``-1``, and ``1004747-1`` / ``P904225-1`` are
    dash columns. A bare ``1`` is an ITEM index, not a qty header.
    """
    raw = str(cell or "").strip()
    if not raw:
        return False, None, None
    compact = re.sub(r"[^A-Z0-9]+", "", raw.upper())
    if compact in {"QTY", "QTYS", "QUANTITY"}:
        return True, None, None
    dashed = _QTY_DASH_HEADER_RE.fullmatch(raw)
    if dashed:
        return True, dashed.group(1), None
    bare = _BARE_DASH_QTY_RE.fullmatch(raw)
    if bare:
        return True, bare.group(1), None
    pn_col = _PN_DASH_QTY_RE.fullmatch(raw)
    if pn_col:
        return True, pn_col.group(2), raw.strip().upper()
    return False, None, None


def _canon_header_token(cell: str) -> str | None:
    raw = str(cell or "").strip().upper()
    compact = re.sub(r"[^A-Z0-9]+", "", raw)
    if compact in {"QTY", "QTYS", "QUANTITY"}:
        return "QTY"
    if compact in {"ITEM", "ITEMNO", "BALLOON", "FIND"}:
        return "ITEM"
    if compact in {"PARTNO", "PARTNUMBER", "PN"} or raw.startswith("PART NO"):
        return "PART NO"
    if compact in {"DESC", "DESCRIPTION", "DESCR"}:
        return "DESCRIPTION"
    return None


def _header_column_map(row: list[str]) -> dict[str, Any] | None:
    """ITEM / PART / DESC plus every qty-like column. QTY is not assumed col 0.

    Treat ``QTY``, ``QTY -1``, ``QTY-1``, ``-1``, and a column named like
    the dash (``1004747-1``) as quantity headers.
    """
    found: dict[str, Any] = {"QTY_COLS": [], "QTY_HEADER_PNS": []}
    for i, cell in enumerate(row):
        is_qty, dash, header_pn = _qty_header_info(cell)
        if is_qty:
            found["QTY_COLS"].append((i, dash))
            if header_pn and header_pn not in found["QTY_HEADER_PNS"]:
                found["QTY_HEADER_PNS"].append(header_pn)
            continue
        canon = _canon_header_token(cell)
        if canon and canon != "QTY" and canon not in found:
            found[canon] = i
    if found["QTY_COLS"] and "PART NO" in found:
        return found
    return None


def _pick_xlsx_qty_col(
    qty_cols: list[tuple[int, str | None]],
    bom_config: str | None,
) -> tuple[int | None, bool]:
    """Return (column index, omit blank qty).

    Filled dash → that printed column only. Blank dash → the single QTY
    column (bare ``QTY``, else the first qty column — never the sum).
    A decorative lone ``-1`` next to ``QTY`` (102728) is not a second column.
    """
    from quote_core.bom_config import normalize_bom_config

    if not qty_cols:
        return None, False
    dash = normalize_bom_config(bom_config)
    bare = [col for col in qty_cols if col[1] is None]
    dashed = [col for col in qty_cols if col[1] is not None]
    work = bare if bare and len(dashed) < 2 else qty_cols
    if dash:
        want = dash.lstrip("-")
        for idx, col_dash in work:
            if col_dash and col_dash.lstrip("-") == want:
                return idx, True
        if bare:
            return bare[0][0], False
        return work[0][0], False
    if bare:
        return bare[0][0], False
    return work[0][0], False


def _title_pns_from_xlsx_path(path: Path | str) -> set[str]:
    """``1004611-1-LOM.xlsx`` / ``P904225-1-LOM.xlsx`` title DWG — not a BOM row."""
    from quote_core.bom_table import _weldment_pn_reject_aliases, job_weldment_key_from_path

    dest = Path(path)
    key = job_weldment_key_from_path(dest)
    if not key:
        stem = dest.stem
        if stem.upper().endswith("-LOM"):
            key = job_weldment_key_from_path(stem[:-4])
    if not key:
        return set()
    out = set(_weldment_pn_reject_aliases(key))
    out.update(_weldment_pn_reject_aliases(f"{key}-1"))
    return {token.upper() for token in out if token}


def _is_xlsx_summary_footer(
    part: str,
    desc: str,
    cols: list[str],
    qty: int,
    *,
    prior_pn_count: int,
    prior_pcs: int,
) -> bool:
    """Drop as-drawn tally footers. Do not skip a real Time PN row.

    Workspace reconstructions print ``51 PNs / qty=97``, ``unique PNs``,
    ``21 rows``, ``pcs / 11 / 13``, or a PN that is just the unique-count.
    Those double piece count. A real dashed / 5–7 digit part stays.
    """
    from quote_core.bom_table import _is_dashed_time_pn, _is_time_like_part

    raw = " ".join(str(c or "") for c in (list(cols) + [part, desc]))
    token = str(part or "").strip()
    real_pn = bool(token) and (
        _is_time_like_part(token) or _is_dashed_time_pn(token)
    )
    if _FOOTER_TALLY_RE.search(raw) and not real_pn:
        return True
    if prior_pn_count > 0 and _BARE_COUNT_RE.fullmatch(token):
        return True
    if qty > 0 and prior_pcs > 0 and qty == prior_pcs and not real_pn:
        return True
    return False


def _is_xlsx_junk_row(
    part: str,
    desc: str,
    cols: list[str],
    colmap: dict[str, Any],
    reject_pns: set[str] | None,
    *,
    qty: int = 0,
    prior_pn_count: int = 0,
    prior_pcs: int = 0,
) -> bool:
    """Skip title-block / qty-header PNs, welding-wire notes, revision marks, footers."""
    from quote_core.bom_table import (
        MaterialListLayout,
        _is_eco_or_title_block_row,
        _is_welding_wire_note,
        _part_is_qty_header_pn,
        _weldment_pn_reject_aliases,
    )

    raw = " ".join(str(c or "") for c in cols)
    if _is_eco_or_title_block_row(part, desc, raw):
        return True
    if _is_welding_wire_note(part, desc, raw):
        return True
    layout = MaterialListLayout(
        qty_header_pns=list(colmap.get("QTY_HEADER_PNS") or [])
    )
    if _part_is_qty_header_pn(part, layout):
        return True
    if _is_xlsx_summary_footer(
        part,
        desc,
        cols,
        qty,
        prior_pn_count=prior_pn_count,
        prior_pcs=prior_pcs,
    ):
        return True
    token = str(part or "").strip().upper()
    if not token:
        return False
    aliases: set[str] = set()
    for pn in reject_pns or []:
        aliases.add(str(pn).strip().upper())
        aliases.update(_weldment_pn_reject_aliases(pn))
    return token in aliases


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    for name in ("xl/sharedStrings.xml", "xl/SharedStrings.xml"):
        if name in zf.namelist():
            raw = zf.read(name)
            break
    else:
        return []
    root = ET.fromstring(raw)
    out: list[str] = []
    for si in root.findall(f"{{{_NS_MAIN}}}si"):
        out.append("".join(t.text or "" for t in si.iter(f"{{{_NS_MAIN}}}t")))
    return out


def _cell_value(cell: ET.Element, sst: list[str] | None) -> str:
    texts = [t.text or "" for t in cell.findall(f"{{{_NS_MAIN}}}is/{{{_NS_MAIN}}}t")]
    if texts:
        return "".join(texts)
    val_el = cell.find(f"{{{_NS_MAIN}}}v")
    if val_el is None or val_el.text is None:
        return ""
    if cell.get("t") == "s" and sst:
        try:
            return sst[int(val_el.text)]
        except (TypeError, ValueError, IndexError):
            return ""
    return val_el.text


def _parse_sheet_xml(
    raw: bytes,
    sst: list[str] | None = None,
    *,
    bom_config: str | None = None,
    reject_pns: set[str] | None = None,
    drop_junk: bool = True,
) -> tuple[list[str], list[dict[str, Any]]]:
    root = ET.fromstring(raw)
    rows_el = list(root.findall(f"{{{_NS_MAIN}}}sheetData/{{{_NS_MAIN}}}row"))
    parsed: list[list[str]] = []
    for row_el in rows_el:
        values: dict[int, str] = {}
        widest = 3
        for cell in row_el.findall(f"{{{_NS_MAIN}}}c"):
            idx = _col_index_from_ref(cell.get("r") or "")
            if idx is None:
                continue
            values[idx] = _cell_value(cell, sst)
            if idx > widest:
                widest = idx
        parsed.append([values.get(i, "") for i in range(widest + 1)])
    if not parsed:
        return list(LOM_COLUMNS), []
    header_idx = 0
    colmap = None
    for i, row in enumerate(parsed[:16]):
        colmap = _header_column_map(row)
        if colmap:
            header_idx = i
            break
    if colmap is None:
        colmap = {
            "QTY_COLS": [(0, None)],
            "ITEM": 1,
            "PART NO": 2,
            "DESCRIPTION": 3,
            "QTY_HEADER_PNS": [],
        }
    header = parsed[header_idx]
    qty_idx, omit_blank = _pick_xlsx_qty_col(
        list(colmap.get("QTY_COLS") or []),
        bom_config,
    )
    if qty_idx is None:
        qty_idx = 0
        omit_blank = False

    def _get(cols: list[str], name: str) -> str:
        idx = colmap.get(name)
        if name == "QTY":
            idx = qty_idx
        if idx is None or int(idx) >= len(cols):
            return ""
        return str(cols[int(idx)] or "")

    data: list[dict[str, Any]] = []
    prior_pcs = 0
    prior_pns: set[str] = set()
    for cols in parsed[header_idx + 1 :]:
        rec = {
            "QTY": _get(cols, "QTY"),
            "ITEM": _get(cols, "ITEM"),
            "PART NO": _get(cols, "PART NO"),
            "DESCRIPTION": _get(cols, "DESCRIPTION"),
        }
        if not str(rec["PART NO"]).strip() and not str(rec["ITEM"]).strip():
            continue
        qty, inch_note = _xlsx_qty_from_cell(rec["QTY"])
        if inch_note:
            rec["QTY"] = qty
            desc = str(rec["DESCRIPTION"] or "").strip()
            if desc and not re.search(r'["″”]', desc):
                rec["DESCRIPTION"] = f'{desc} {str(_get(cols, "QTY")).strip()}'.strip()
        if drop_junk and _is_xlsx_junk_row(
            str(rec["PART NO"] or ""),
            str(rec["DESCRIPTION"] or ""),
            cols,
            colmap,
            reject_pns,
            qty=qty,
            prior_pn_count=len(prior_pns),
            prior_pcs=prior_pcs,
        ):
            continue
        if omit_blank and qty <= 0 and not inch_note:
            continue
        data.append(rec)
        prior_pcs += max(0, qty)
        part = str(rec["PART NO"] or "").strip()
        if part:
            prior_pns.add(part)
    return header, data


def list_lom_sheet_names(path: Path | str) -> list[str]:
    with zipfile.ZipFile(Path(path)) as zf:
        return [name for name, _part in _sheet_part_paths(zf)]


def read_lom_xlsx(
    path: Path | str,
    sheet: str | None = None,
    *,
    bom_config: str | None = None,
    drop_junk: bool = True,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Read header + data rows. Default is the parent LIST OF MATERIAL tab."""
    dest = Path(path)
    reject = _title_pns_from_xlsx_path(dest) if drop_junk else set()
    with zipfile.ZipFile(dest) as zf:
        parts = _sheet_part_paths(zf)
        zip_path = parts[0][1]
        if sheet:
            want = str(sheet).upper()
            for name, part in parts:
                if name.upper() == want:
                    zip_path = part
                    break
            else:
                return list(LOM_COLUMNS), []
        raw = zf.read(zip_path)
        sst = _shared_strings(zf)
    return _parse_sheet_xml(
        raw,
        sst,
        bom_config=bom_config,
        reject_pns=reject,
        drop_junk=drop_junk,
    )


def bom_tabs_for_import(
    path: Path | str, *, bom_config: str | None = None
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Every BOM tab for SecturaFAB import. Parent first. Do not merge rows."""
    return [
        (name, _records_to_rows(data))
        for name, data in read_lom_sheets(path, bom_config=bom_config).items()
    ]


def read_lom_sheets(
    path: Path | str, *, bom_config: str | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Every BOM tab. Parent takeoff is the first name (LIST OF MATERIAL)."""
    dest = Path(path)
    reject = _title_pns_from_xlsx_path(dest)
    out: dict[str, list[dict[str, Any]]] = {}
    with zipfile.ZipFile(dest) as zf:
        sst = _shared_strings(zf)
        for name, part in _sheet_part_paths(zf):
            _header, data = _parse_sheet_xml(
                zf.read(part),
                sst,
                bom_config=bom_config,
                reject_pns=reject,
            )
            out[name] = data
    return out


def _records_to_rows(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "item": rec.get("ITEM") or "",
            "qty": _qty_int(rec.get("QTY")),
            "part_no": rec.get("PART NO") or "",
            "description": rec.get("DESCRIPTION") or "",
        }
        for rec in data
    ]


def refresh_nested_children_from_xlsx(
    path: Path | str,
    children: list[dict[str, Any]],
    *,
    bom_config: str | None = None,
) -> list[dict[str, Any]]:
    """Re-read child tabs from the parent workbook. Parent sheet is not merged."""
    if not children:
        return children
    try:
        sheets = read_lom_sheets(path, bom_config=bom_config)
    except (OSError, KeyError, ET.ParseError):
        return children
    dest = Path(path)

    def _apply(node: dict[str, Any]) -> None:
        sheet = lom_sheet_name(node.get("lom_sheet") or node.get("part_no"))
        data = sheets.get(sheet)
        if data is None:
            for name, recs in sheets.items():
                if name.upper() == sheet.upper():
                    data = recs
                    break
        if data is not None:
            node["rows"] = _records_to_rows(data)
            node["lom_xlsx"] = dest.name
            node["lom_sheet"] = sheet
        for inner in node.get("nested_children") or []:
            if isinstance(inner, dict):
                _apply(inner)

    out = list(children)
    for child in out:
        if isinstance(child, dict):
            _apply(child)
    return out
