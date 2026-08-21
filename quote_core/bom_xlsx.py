"""Emit LIST OF MATERIAL as QTY / ITEM / PART NO / DESCRIPTION (.xlsx).

Minimal OOXML via zipfile — no openpyxl. Same four columns as 102728-1-LOM.xlsx.
"""

from __future__ import annotations

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
    if not bom_is_lom_clip(bom):
        return None
    rows = getattr(bom, "rows", None)
    if rows is None and isinstance(bom, dict):
        rows = bom.get("rows") or bom.get("bom_rows")
    if not rows:
        return None
    return write_lom_xlsx(lom_xlsx_path_for_pdf(pdf_path), rows)


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
    """Write only when a LIST OF MATERIAL was clipped. No LOM → no xlsx."""
    if not pdf_path:
        return None
    dest = lom_xlsx_path_for_pdf(pdf_path)
    if dest.is_file():
        return dest
    if not takeoff_has_lom_clip(takeoff):
        return None
    rows = rows_from_takeoff(takeoff)
    if not rows:
        return None
    return write_lom_xlsx(dest, rows, extra_sheets=extra_sheets_from_takeoff(takeoff))


def _qty_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def sheet_records(path: Path | str) -> list[dict[str, Any]]:
    """Four-column LOM.xlsx as quote rows. Qty unread/blank is 0."""
    _header, data = read_lom_xlsx(path)
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
    takeoff: dict[str, Any] | None, path: Path | str
) -> dict[str, Any]:
    """Replace takeoff BOM JSON with the written sheet. No side channel."""
    dest = Path(path)
    records = sheet_records(dest)
    blob = dict(takeoff or {})
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


def _parse_sheet_xml(raw: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    root = ET.fromstring(raw)
    rows_el = list(root.findall(f"{{{_NS_MAIN}}}sheetData/{{{_NS_MAIN}}}row"))
    parsed: list[list[str]] = []
    for row_el in rows_el:
        values: dict[str, str] = {}
        for cell in row_el.findall(f"{{{_NS_MAIN}}}c"):
            ref = (cell.get("r") or "")[:1]
            text_el = cell.find(f"{{{_NS_MAIN}}}is/{{{_NS_MAIN}}}t")
            val_el = cell.find(f"{{{_NS_MAIN}}}v")
            if text_el is not None and text_el.text is not None:
                values[ref] = text_el.text
            elif val_el is not None and val_el.text is not None:
                values[ref] = val_el.text
            else:
                values[ref] = ""
        parsed.append([values.get(col, "") for col in "ABCD"])
    if not parsed:
        return list(LOM_COLUMNS), []
    header = parsed[0]
    data = [
        {
            "QTY": cols[0],
            "ITEM": cols[1],
            "PART NO": cols[2],
            "DESCRIPTION": cols[3],
        }
        for cols in parsed[1:]
    ]
    return header, data


def list_lom_sheet_names(path: Path | str) -> list[str]:
    with zipfile.ZipFile(Path(path)) as zf:
        return [name for name, _part in _sheet_part_paths(zf)]


def read_lom_xlsx(
    path: Path | str, sheet: str | None = None
) -> tuple[list[str], list[dict[str, Any]]]:
    """Read header + data rows. Default is the parent LIST OF MATERIAL tab."""
    with zipfile.ZipFile(Path(path)) as zf:
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
    return _parse_sheet_xml(raw)


def bom_tabs_for_import(path: Path | str) -> list[tuple[str, list[dict[str, Any]]]]:
    """Every BOM tab for SecturaFAB import. Parent first. Do not merge rows."""
    return [
        (name, _records_to_rows(data))
        for name, data in read_lom_sheets(path).items()
    ]


def read_lom_sheets(path: Path | str) -> dict[str, list[dict[str, Any]]]:
    """Every BOM tab. Parent takeoff is the first name (LIST OF MATERIAL)."""
    out: dict[str, list[dict[str, Any]]] = {}
    with zipfile.ZipFile(Path(path)) as zf:
        for name, part in _sheet_part_paths(zf):
            _header, data = _parse_sheet_xml(zf.read(part))
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
    path: Path | str, children: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Re-read child tabs from the parent workbook. Parent sheet is not merged."""
    if not children:
        return children
    try:
        sheets = read_lom_sheets(path)
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
