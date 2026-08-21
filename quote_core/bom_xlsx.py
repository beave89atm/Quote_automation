"""Emit LIST OF MATERIAL as QTY / ITEM / PART NO / DESCRIPTION (.xlsx).

Minimal OOXML via zipfile — no openpyxl. Same four columns as 102728-1-LOM.xlsx.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from quote_core.bom_table import item_sort_key

LOM_COLUMNS = ("QTY", "ITEM", "PART NO", "DESCRIPTION")
LOM_SUFFIX = "-LOM.xlsx"
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
    def key(row: Any) -> tuple[int, str]:
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


def write_lom_xlsx(path: Path | str, rows: list[Any]) -> Path:
    """Write the four-column LOM grid. A is first in the sheet (page has A at bottom)."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet = _sheet_xml(list(rows or []))
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return dest


def write_lom_xlsx_for_bom(pdf_path: Path | str | None, bom: Any) -> Path | None:
    if not pdf_path:
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
    if not pdf_path:
        return None
    dest = lom_xlsx_path_for_pdf(pdf_path)
    if dest.is_file():
        return dest
    rows = rows_from_takeoff(takeoff)
    if not rows:
        return None
    return write_lom_xlsx(dest, rows)


def read_lom_xlsx(path: Path | str) -> tuple[list[str], list[dict[str, Any]]]:
    """Read header + data rows from a LOM.xlsx this module wrote."""
    with zipfile.ZipFile(Path(path)) as zf:
        raw = zf.read("xl/worksheets/sheet1.xml")
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
