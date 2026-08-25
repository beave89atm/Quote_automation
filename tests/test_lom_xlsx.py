"""Kyle-confirmed LOM.xlsx is preferred over OCR and uses the -1 qty column."""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from quote_core.bom import extract_bom
from quote_core.lom_xlsx import extract_bom_from_lom_xlsx, find_lom_xlsx


def _col_letter(idx: int) -> str:
    n = idx + 1
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    sheet_rows = []
    for r_i, row in enumerate(rows, start=1):
        cells = []
        for c_i, val in enumerate(row):
            ref = f"{_col_letter(c_i)}{r_i}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(val))}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="LOM" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
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
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", ctypes)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _1004747_lom_rows() -> list[list[str]]:
    """Synthetic Time LOM: dash -1 is 14 PN / 18 pcs (Kyle-confirmed 1004747-1)."""
    header = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    # 12 unique PNs at qty 1 + 2 PNs at qty 2 = 14 PN / 18 pcs on -1.
    # -2 column is empty so a wrong dash would under-count.
    letters = "ABCDEFGHIJKL"
    for i, letter in enumerate(letters):
        pn = f"10048{10 + i:02d}-1"
        rows.append(["-", "-", "-", "1", letter, pn, f"PLATE {letter}"])
    rows.append(["-", "-", "1", "2", "M", "1004822-1", "GUSSET"])
    rows.append(["-", "-", "1", "2", "N", "1004823-1", "STIFFENER"])
    return rows


def test_find_lom_xlsx_prefers_exact_name(tmp_path: Path):
    (tmp_path / "notes.xlsx").write_bytes(b"PK")
    write_minimal_xlsx(tmp_path / "LOM.xlsx", [["ITEM", "PART NO", "QTY"]])
    write_minimal_xlsx(tmp_path / "other-lom-backup.xlsx", [["ITEM", "PART NO", "QTY"]])
    found = find_lom_xlsx(tmp_path)
    assert found is not None
    assert found.name == "LOM.xlsx"


def test_lom_xlsx_dash_one_is_14_pn_18_pcs(tmp_path: Path):
    path = tmp_path / "LOM.xlsx"
    write_minimal_xlsx(path, _1004747_lom_rows())
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert bom.method == "lom_xlsx"
    assert bom.part_number_count == 14, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    assert bom.piece_count == 18, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    qty2 = sorted(r.part_no for r in bom.rows if r.qty == 2)
    assert qty2 == ["1004822-1", "1004823-1"]


def test_extract_bom_prefers_lom_over_ocr(tmp_path: Path):
    write_minimal_xlsx(tmp_path / "LOM.xlsx", _1004747_lom_rows())
    pdf = tmp_path / "1004747.pdf"
    pdf.write_bytes(b"%PDF-1.4 empty")
    bom = extract_bom(pdf, library_folder=tmp_path, bom_config="1")
    assert bom.method == "lom_xlsx"
    assert bom.part_number_count == 14
    assert bom.piece_count == 18
    assert any("preferred over OCR" in n for n in bom.notes)
