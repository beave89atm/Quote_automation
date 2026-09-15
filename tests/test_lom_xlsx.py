"""Kyle-confirmed LOM.xlsx is the BOM source; clip-grid writes that sheet."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import patch

from quote_core.bom import extract_bom
from quote_core.lom_xlsx import (
    extract_bom_from_lom_xlsx,
    find_lom_xlsx,
    normalize_opc_part,
    read_xlsx_grid,
    write_lom_xlsx,
)


def write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    write_lom_xlsx(path, rows)


def write_excel_absolute_target_xlsx(path: Path, rows: list[list[str]]) -> None:
    """Minimal real-Excel-style xlsx: Relationship Target is ``/xl/worksheets/...``.

    Job 91 died because the reader prefixed ``xl/`` onto that absolute target.
    """
    write_lom_xlsx(path, rows)
    sheet_xml = zipfile.ZipFile(path).read("xl/worksheets/sheet1.xml")
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        '<sheet name="LOM as drawn" sheetId="1" r:id="rId1"/>'
        "</sheets></workbook>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="/xl/worksheets/sheet1.xml"/>'
        "</Relationships>"
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
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
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
    # 10 unique PNs at qty 1 + 4 PNs at qty 2 = 14 PN / 18 pcs on -1.
    # -2 column is empty on the qty-1 rows so a wrong dash would under-count.
    letters = "ABCDEFGHIJ"
    for i, letter in enumerate(letters):
        pn = f"10048{10 + i:02d}-1"
        rows.append(["-", "-", "-", "1", letter, pn, f"PLATE {letter}"])
    rows.append(["-", "-", "1", "2", "K", "1004820-1", "GUSSET"])
    rows.append(["-", "-", "1", "2", "L", "1004821-1", "STIFFENER"])
    rows.append(["-", "-", "1", "2", "M", "1004822-1", "PAD"])
    rows.append(["-", "-", "1", "2", "N", "1004823-1", "CLIP"])
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
    assert qty2 == ["1004820-1", "1004821-1", "1004822-1", "1004823-1"]


def test_extract_bom_prefers_lom_over_ocr(tmp_path: Path):
    write_minimal_xlsx(tmp_path / "LOM.xlsx", _1004747_lom_rows())
    with patch("quote_core.bom.extract_bom_from_ocr_time_style") as ocr:
        bom = extract_bom(pdf_path=None, library_folder=tmp_path, bom_config="1")
        ocr.assert_not_called()
    assert bom.method == "lom_xlsx"
    assert bom.part_number_count == 14
    assert bom.piece_count == 18
    assert any("preferred over OCR" in n for n in bom.notes)


def _qty_rows(prefix: int, n_qty1: int, n_qty2: int, *, extra_desc: str | None = None) -> list[list[str]]:
    header = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    letters = [c for c in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
    i = 0
    for _ in range(n_qty1):
        letter = letters[i % len(letters)]
        rows.append(["-", "-", "-", "1", letter, f"{1000000 + i}-1", f"PLATE {letter}"])
        i += 1
    for j in range(n_qty2):
        letter = letters[i % len(letters)]
        desc = extra_desc if j == 0 and extra_desc else f"GUSSET {letter}"
        rows.append(["-", "-", "1", "2", letter, f"{1000000 + i}-1", desc])
        i += 1
    return rows


def test_confirmed_102728_dash1_51_pn_97_pcs(tmp_path: Path):
    # 5×1 + 46×2 = 51 PN / 97 pcs
    path = tmp_path / "102728-1-LOM.xlsx"
    write_minimal_xlsx(path, _qty_rows(102728, 5, 46))
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert bom.part_number_count == 51
    assert bom.piece_count == 97


def test_confirmed_28106_dash1_11_pn_13_pcs(tmp_path: Path):
    # 9×1 + 2×2 = 11 PN / 13 pcs
    path = tmp_path / "28106-1-LOM.xlsx"
    write_minimal_xlsx(path, _qty_rows(28106, 9, 2))
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert bom.part_number_count == 11
    assert bom.piece_count == 13


# Kyle-confirmed Time LOM for 1001898 dash -1: 17 PN / 27 pcs.
# Unused letters (other dashes only) must not be summed into -1.
_1001898_DASH1 = [
    ("A", 1, "14500-1", "PEDESTAL TOP PLATE"),
    ("B", 1, "1001880-2", "PEDESTAL TUBE"),
    ("C", 2, "29860-4", "PEDESTAL BRACE ANGLE"),
    ("D", 1, "14501-1", "RESERVOIR TOP PLATE"),
    ("E", 1, "1005966-1", "PEDESTAL BOTTOM PLATE"),
    ("F", 2, "50137-5", "3/4 NPT HALF COUPLING"),
    ("G", 1, "50115-7", "1 1/4 NPT NIPPLE X 4 LG."),
    ("H", 1, "50030-5", "3/4 NPT COUPLING"),
    ("J", 1, "8166-1", "FILLER NECK"),
    ("K", 1, "9905-1", "MOUNTING PLATE, EMER POWER"),
    ("L", 1, "33637-1", "1 1/4 RETURN TUBE"),
    ("M", 1, "10081-2", "PEDESTAL HOSE TUBE"),
    ("N", 1, "50006-5", "3/4 NPT MAGNETIC PLUG"),
    ("P", 1, "50122-1", "1 1/4 NPT PIPE CAP"),
    ("U", 2, "29860-3", "PEDESTAL BRACE ANGLE"),
    ("X", 8, "1005940-1", "PEDESTAL GUSSET"),
    ("AB", 1, "50029-7", "1 1/4 90 STREET ELBOW"),
]
_1001898_OTHER_DASH = [
    ("Q", "1001899-1", "OTHER DASH Q"),
    ("R", "1001900-1", "OTHER DASH R"),
    ("S", "1001901-1", "OTHER DASH S"),
    ("T", "1001902-1", "OTHER DASH T"),
    ("V", "1001903-1", "OTHER DASH V"),
    ("W", "1001904-1", "OTHER DASH W"),
    ("Y", "1001905-1", "OTHER DASH Y"),
    ("Z", "1001906-1", "OTHER DASH Z"),
    ("AA", "1001907-1", "OTHER DASH AA"),
    ("AC", "1001908-1", "OTHER DASH AC"),
]


def _1001898_lom_rows() -> list[list[str]]:
    header = ["-5", "-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    for item, qty, pn, desc in _1001898_DASH1:
        rows.append(["-", "-", "-", "-", str(qty), item, pn, desc])
    for item, pn, desc in _1001898_OTHER_DASH:
        rows.append(["-", "-", "-", "1", "-", item, pn, desc])
    return rows


def test_1001898_dash1_is_17_pn_27_pcs_not_paint_20(tmp_path: Path):
    """Locked Desktop LOM: dash -1 is 17 PN / 27 pcs. Paint '20 PLCS' is not qty."""
    path = tmp_path / "1001898-1-LOM.xlsx"
    write_minimal_xlsx(path, _1001898_lom_rows())
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert bom.part_number_count == 17, [f"{r.item} {r.part_no}×{r.qty}" for r in bom.rows]
    assert bom.piece_count == 27, [f"{r.item} {r.part_no}×{r.qty}" for r in bom.rows]
    assert bom.piece_count != 20
    by_pn = {r.part_no: r for r in bom.rows}
    assert by_pn["14500-1"].qty == 1
    assert by_pn["1005940-1"].qty == 8
    assert by_pn["50029-7"].item == "AB"
    assert "1001899-1" not in by_pn
    # Bare title / omitted dash must not sum columns.
    bare = extract_bom_from_lom_xlsx(path, bom_config=None)
    assert bare.part_number_count == 17
    assert bare.piece_count == 27


def test_lom_does_not_invent_folder_pdf_rows(tmp_path: Path):
    write_minimal_xlsx(tmp_path / "LOM.xlsx", _1004747_lom_rows())
    (tmp_path / "9999999-1.pdf").write_bytes(b"%PDF")
    bom = extract_bom(pdf_path=None, library_folder=tmp_path, bom_config="1")
    assert "9999999-1" not in {r.part_no for r in bom.rows}


def test_qty_cell_rejects_paint_plcs():
    from quote_core.lom_xlsx import _parse_qty_cell

    assert _parse_qty_cell("20 PLCS") == 0
    assert _parse_qty_cell("-") == 0
    assert _parse_qty_cell("2") == 2


def test_opc_target_never_becomes_xl_xl():
    assert normalize_opc_part("/xl/worksheets/sheet1.xml") == "xl/worksheets/sheet1.xml"
    assert normalize_opc_part("worksheets/sheet1.xml") == "xl/worksheets/sheet1.xml"
    assert normalize_opc_part("xl/worksheets/sheet1.xml") == "xl/worksheets/sheet1.xml"
    assert normalize_opc_part("xl/xl/worksheets/sheet1.xml") == "xl/worksheets/sheet1.xml"
    assert "xl/xl/" not in normalize_opc_part("/xl/worksheets/sheet1.xml")


def test_excel_absolute_target_xlsx_does_not_look_for_xl_xl(tmp_path: Path):
    """Job 91: 'There is no item named xl/xl/worksheets/sheet1.xml in the archive'."""
    path = tmp_path / "1001898-1-LOM.xlsx"
    write_excel_absolute_target_xlsx(path, _1001898_lom_rows())
    with zipfile.ZipFile(path) as zf:
        rels = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")
        assert 'Target="/xl/worksheets/sheet1.xml"' in rels
        assert "xl/xl/worksheets/sheet1.xml" not in zf.namelist()
    grid = read_xlsx_grid(path)
    assert grid, "Excel-style absolute Target must open"
    assert not any("xl/xl/" in "".join(row) for row in grid)
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert "xl/xl/" not in " ".join(bom.notes)
    assert bom.method == "lom_xlsx"
    assert bom.part_number_count == 17
    assert bom.piece_count == 27


def test_job91_drop_1001898_uses_library_excel_lom(tmp_path: Path):
    """Drop 1001898.pdf → open Kyle 1001898-1-LOM.xlsx (Excel /xl/ targets) → 17/27."""
    from quote_core.weld.takeoff import run_weld_takeoff

    lib = tmp_path / "Customer Drawings" / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    write_excel_absolute_target_xlsx(lib / "1001898-1-LOM.xlsx", _1001898_lom_rows())
    job_dir = tmp_path / "uploads" / "91"
    job_dir.mkdir(parents=True)
    pdf = job_dir / "1001898.pdf"
    import fitz

    doc = fitz.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    found = find_lom_xlsx(job_dir, lib, part_key="1001898")
    assert found is not None
    assert found.name == "1001898-1-LOM.xlsx"
    bom = extract_bom(pdf, library_folder=lib, bom_config="1")
    assert bom.method == "lom_xlsx", bom.notes
    assert bom.part_number_count == 17
    assert bom.piece_count == 27
    result = run_weld_takeoff(pdf, library_folder=lib, bom_config="1")
    assert result.fitup_drivers["part_count"] == 27
    assert result.fitup_drivers["piece_count"] == 27
    assert not result.fitup_drivers.get("needs_info")
    assert result.fitup_drivers["part_count"] != 1 or bom.piece_count == 27
