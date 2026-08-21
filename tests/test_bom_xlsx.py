"""Quote BOM is the written LOM.xlsx. No side-channel JSON."""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import (
    BomResult,
    BomRow,
    bom_from_lom_xlsx,
    extract_bom,
    quote_bom_from_drawing,
)
from quote_core.bom_xlsx import (
    PARENT_SHEET_NAME,
    _CONTENT_TYPES,
    _NS_MAIN,
    _ROOT_RELS,
    _WORKBOOK,
    _WORKBOOK_RELS,
    _inline_cell,
    _qty_cell,
    _sort_rows,
    apply_lom_xlsx_to_takeoff,
    bom_tabs_for_import,
    find_existing_lom_xlsx,
    list_lom_sheet_names,
    read_lom_xlsx,
    write_lom_xlsx,
)

from tests.test_bom_table import (
    _KYLE_102728_1,
    _assert_kyle_1004747_1,
    _assert_kyle_102728_1,
    _assert_kyle_28106_1,
    _assert_kyle_xlsx,
    _kyle_1004747_cell_rows,
    _kyle_28106_cell_rows,
    _kyle_p904225_cell_rows,
    _write_lom_pdf,
)

_PROOF_QTY = {
    "A": (1, "460200"),
    "BB": (2, "102727-4"),
    "V": (6, "432710"),
    "W": (4, "432690"),
    "Y": (4, "100363-1"),
    "Z": (2, "460320"),
    "AA": (5, "460330"),
    "AC": (4, "100177-2"),
    "AD": (8, "464440"),
    "AX": (2, "102726-1"),
}


def _write_item_qty_xlsx(path: Path, rows: list[BomRow]) -> Path:
    """Kyle Time sheet order: ITEM | QTY | PART NO | DESCRIPTION."""
    import zipfile

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{_NS_MAIN}"><sheetData>',
        "<row r=\"1\">"
        f"{_inline_cell('A1', 'ITEM')}"
        f"{_inline_cell('B1', 'QTY')}"
        f"{_inline_cell('C1', 'PART NO')}"
        f"{_inline_cell('D1', 'DESCRIPTION')}"
        "</row>",
    ]
    for i, row in enumerate(_sort_rows(rows), start=2):
        parts.append(
            f'<row r="{i}">'
            f"{_inline_cell(f'A{i}', row.item)}"
            f"{_qty_cell(f'B{i}', row.qty)}"
            f"{_inline_cell(f'C{i}', row.part_no)}"
            f"{_inline_cell(f'D{i}', row.description)}"
            "</row>"
        )
    parts.append("</sheetData></worksheet>")
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", "".join(parts))
    return dest


def _kyle_rows() -> list[BomRow]:
    return [
        BomRow(item=item, qty=qty, part_no=pn, description=desc)
        for item, qty, pn, desc in _KYLE_102728_1
    ]


def test_quote_rows_are_sourced_from_written_lom_xlsx(tmp_path: Path):
    path = write_lom_xlsx(tmp_path / "102728-1-LOM.xlsx", _kyle_rows())
    stale = BomResult(
        rows=[
            BomRow(
                item=item,
                qty=0 if qty > 1 else qty,
                part_no=pn,
                description=desc,
                source="table_cells",
            )
            for item, qty, pn, desc in _KYLE_102728_1
        ],
        method="table_cells",
    )
    assert stale.piece_count != 97
    sourced = bom_from_lom_xlsx(path, prior=stale)
    _assert_kyle_102728_1(sourced)
    assert sourced.lom_xlsx == "102728-1-LOM.xlsx"
    assert all(r.source == "lom_xlsx" for r in sourced.rows)
    assert "Quote BOM sourced from 102728-1-LOM.xlsx" in sourced.notes
    blob = sourced.to_dict()
    assert blob["source"] == "lom_xlsx"
    assert blob["lom_xlsx"] == "102728-1-LOM.xlsx"


def test_takeoff_json_cannot_diverge_from_lom_xlsx(tmp_path: Path):
    """Live 791587b JSON was 51/30. The written 51/97 sheet wins."""
    path = write_lom_xlsx(tmp_path / "102728-1-LOM.xlsx", _kyle_rows())
    unread = [
        {
            "item": item,
            "qty": 2 if item == "BB" else (0 if qty > 1 else qty),
            "part_no": pn,
            "description": desc,
        }
        for item, qty, pn, desc in _KYLE_102728_1
    ]
    takeoff = {
        "fitup_drivers": {
            "part_count": 30,
            "piece_count": 30,
            "weight_calc": {
                "method": "table_cells",
                "piece_count": 30,
                "part_number_count": 51,
                "bom": {
                    "method": "table_cells",
                    "rows": unread,
                    "bom_rows": unread,
                    "piece_count": 30,
                },
            },
        }
    }
    assert sum(int(r["qty"] or 0) for r in unread) != 97
    fixed = apply_lom_xlsx_to_takeoff(takeoff, path)
    bom = fixed["bom"]
    assert bom["source"] == "lom_xlsx"
    assert bom["piece_count"] == 97
    assert bom["part_number_count"] == 51
    assert fixed["fitup_drivers"]["part_count"] == 97
    assert fixed["fitup_drivers"]["weight_calc"]["pdf_bom"]["piece_count"] == 97
    by_item = {r["item"]: r for r in bom["rows"]}
    for item, (qty, pn) in _PROOF_QTY.items():
        assert by_item[item]["part_no"] == pn
        assert int(by_item[item]["qty"]) == qty
        assert by_item[item]["source"] == "lom_xlsx"


def test_quote_bom_from_drawing_reads_written_xlsx(tmp_path: Path):
    """Product path: clip → write LOM.xlsx → quote is that workbook."""
    data_rows = [
        [str(qty), item, pn, desc] for item, qty, pn, desc in _KYLE_102728_1
    ]
    pdf = tmp_path / "Time 102728- Weldment.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING",
    )
    bom = quote_bom_from_drawing(pdf_path=pdf)
    _assert_kyle_102728_1(bom)
    xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert xlsx.is_file()
    assert bom.lom_xlsx == xlsx.name
    blob = bom.to_dict()
    assert blob["source"] == "lom_xlsx"
    assert blob["piece_count"] == 97
    assert blob["part_number_count"] == 51
    assert blob.get("lom_sheets")
    assert blob["lom_sheets"][0] == PARENT_SHEET_NAME
    assert all(r.source == "lom_xlsx" for r in bom.rows)
    assert any("Quote read" in n and xlsx.name in n for n in bom.notes)
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == "102727-4"
    a = next(r for r in bom.rows if r.item == "A")
    assert a.qty == 1 and a.part_no == "460200"


def test_extract_bom_quote_matches_written_102728_xlsx(tmp_path: Path):
    data_rows = [
        [str(qty), item, pn, desc] for item, qty, pn, desc in _KYLE_102728_1
    ]
    pdf = tmp_path / "Time 102728- Weldment.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING",
    )
    bom = extract_bom(pdf_path=pdf)
    assert not (bom.method or "").startswith("ocr_time")
    _assert_kyle_102728_1(bom)
    xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert xlsx.is_file()
    _assert_kyle_xlsx(xlsx, _KYLE_102728_1)
    assert bom.lom_xlsx == xlsx.name
    _header, sheet = read_lom_xlsx(xlsx)
    by_sheet = {r["ITEM"]: r for r in sheet}
    by_quote = {str(r.item): r for r in bom.rows}
    assert set(by_sheet) == set(by_quote)
    for item, rec in by_sheet.items():
        quote = by_quote[item]
        assert quote.source == "lom_xlsx"
        assert str(quote.part_no) == rec["PART NO"]
        assert int(quote.qty) == int(rec["QTY"])
    for item, (qty, pn) in _PROOF_QTY.items():
        assert int(by_sheet[item]["QTY"]) == qty
        assert by_sheet[item]["PART NO"] == pn


def test_child_lom_tab_is_not_merged_into_parent_takeoff(tmp_path: Path):
    """102728 qty stays 97. Child weldment LOM is an extra tab, not parent rows."""
    path = write_lom_xlsx(
        tmp_path / "102728-1-LOM.xlsx",
        _kyle_rows(),
        extra_sheets=[
            (
                "102711-1",
                [
                    BomRow(item="A", qty=1, part_no="555010", description="PLATE"),
                    BomRow(item="B", qty=2, part_no="555011", description="TUBE, ROUND"),
                ],
            )
        ],
    )
    assert list_lom_sheet_names(path) == [PARENT_SHEET_NAME, "102711-1"]
    sourced = bom_from_lom_xlsx(path)
    _assert_kyle_102728_1(sourced)
    assert "555010" not in {r.part_no for r in sourced.rows}
    _header, child = read_lom_xlsx(path, sheet="102711-1")
    assert {r["PART NO"] for r in child} == {"555010", "555011"}
    tabs = bom_tabs_for_import(path)
    assert [name for name, _rows in tabs] == [PARENT_SHEET_NAME, "102711-1"]
    assert sum(int(r["qty"]) for r in tabs[0][1]) == 97


def test_existing_job_folder_xlsx_is_quote_without_reocr(tmp_path: Path, monkeypatch):
    """Locked: sibling / job-key LOM.xlsx is the quote. Do not re-OCR over it."""
    from quote_core.bom_xlsx import find_existing_lom_xlsx

    pdf = tmp_path / "Time 102728- Weldment.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\n")
    path = write_lom_xlsx(tmp_path / "102728-1-LOM.xlsx", _kyle_rows())
    assert find_existing_lom_xlsx(pdf) == path

    def fail_ocr(**_kwargs):
        raise AssertionError("must not re-OCR when LOM.xlsx exists")

    monkeypatch.setattr("quote_core.bom.extract_bom_from_ocr_time_style", fail_ocr)
    bom = extract_bom(pdf_path=pdf)
    _assert_kyle_102728_1(bom)
    assert bom.to_dict()["source"] == "lom_xlsx"
    assert bom.lom_xlsx == "102728-1-LOM.xlsx"
    assert any("did not re-OCR" in n for n in bom.notes)
    a = next(r for r in bom.rows if r.item == "A")
    assert a.qty == 1 and a.part_no == "460200"
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == "102727-4"
    assert int(bom.piece_count) == 97


def test_desktop_xlsx_is_read_and_not_overwritten(tmp_path: Path, monkeypatch):
    """Desktop 102728-1-LOM.xlsx is confirmed 51/97. Never overwrite it."""
    from quote_core.bom_xlsx import (
        find_existing_lom_xlsx,
        is_desktop_lom_path,
        write_lom_xlsx_for_bom,
    )

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    confirmed = write_lom_xlsx(desktop / "102728-1-LOM.xlsx", _kyle_rows())
    before = confirmed.read_bytes()
    monkeypatch.setattr("quote_core.bom_xlsx._desktop_dirs", lambda: [desktop])

    job = tmp_path / "job"
    job.mkdir()
    pdf = job / "Time 102728- Weldment.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\n")

    assert is_desktop_lom_path(confirmed) is True
    assert find_existing_lom_xlsx(pdf) == confirmed

    stale = BomResult(
        rows=[
            BomRow(item="A", qty=0, part_no="460200", description="RAIL"),
            BomRow(item="BB", qty=2, part_no="102727-4", description="TUBE"),
        ]
    )
    written = write_lom_xlsx_for_bom(pdf, stale)
    assert written == confirmed
    assert confirmed.read_bytes() == before

    quoted = quote_bom_from_drawing(pdf_path=pdf)
    _assert_kyle_102728_1(quoted)
    assert quoted.to_dict()["source"] == "lom_xlsx"
    assert quoted.lom_xlsx == "102728-1-LOM.xlsx"
    assert confirmed.read_bytes() == before
    sibling = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert not sibling.is_file()


def test_reads_item_qty_header_order_as_51_97(tmp_path: Path):
    """Live 311b7ab: Desktop Time sheets are ITEM|QTY|PART|DESC. QTY is not col 0."""
    path = _write_item_qty_xlsx(tmp_path / "102728-1-LOM.xlsx", _kyle_rows())
    header, sheet = read_lom_xlsx(path)
    assert "ITEM" in {str(h).upper() for h in header}
    assert "QTY" in {str(h).upper() for h in header}
    sourced = bom_from_lom_xlsx(path)
    _assert_kyle_102728_1(sourced)
    assert sourced.piece_count == 97
    assert sourced.part_number_count == 51
    by_item = {r.item: r for r in sourced.rows}
    assert by_item["A"].qty == 1 and by_item["A"].part_no == "460200"
    assert by_item["BB"].qty == 2 and by_item["BB"].part_no == "102727-4"


def test_onedrive_company_desktop_is_found(tmp_path: Path, monkeypatch):
    """Laptop Desktop is ``OneDrive - Kannon Manufacturing Inc\\Desktop``."""
    home = tmp_path / "Users" / "Kyle"
    desktop = home / "OneDrive - Kannon Manufacturing Inc" / "Desktop"
    desktop.mkdir(parents=True)
    path = _write_item_qty_xlsx(desktop / "102728-1-LOM.xlsx", _kyle_rows())
    before = path.read_bytes()
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("OneDrive", str(desktop.parent))
    monkeypatch.setenv("OneDriveCommercial", str(desktop.parent))

    job = tmp_path / "job"
    job.mkdir()
    pdf = job / "Time 102728- Weldment.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\n")

    found = find_existing_lom_xlsx(pdf)
    assert found == path
    quoted = quote_bom_from_drawing(pdf_path=pdf)
    _assert_kyle_102728_1(quoted)
    assert quoted.to_dict()["source"] == "lom_xlsx"
    assert quoted.lom_xlsx == "102728-1-LOM.xlsx"
    assert path.read_bytes() == before
    assert not (job / f"{pdf.stem}-LOM.xlsx").is_file()
    assert any("did not re-OCR" in n for n in quoted.notes)


def test_unread_qty_in_existing_xlsx_stays_zero(tmp_path: Path):
    pdf = tmp_path / "102728- Weldment.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\n")
    rows = [
        BomRow(item="A", qty=0, part_no="460200", description="RAIL"),
        BomRow(item="BB", qty=2, part_no="102727-4", description="TUBE, ROUND"),
    ]
    write_lom_xlsx(tmp_path / "102728-1-LOM.xlsx", rows)
    bom = quote_bom_from_drawing(pdf_path=pdf)
    by_item = {r.item: r for r in bom.rows}
    assert by_item["A"].qty == 0
    assert by_item["A"].qty != 1
    assert by_item["BB"].qty == 2
    assert bom.to_dict()["source"] == "lom_xlsx"


def test_piece_part_without_lom_does_not_invent_bom_or_xlsx(tmp_path: Path):
    """No LIST OF MATERIAL → one-part quote. Do not invent a BOM or LOM.xlsx."""
    import fitz

    from quote_core.bom_xlsx import write_lom_xlsx_for_job

    pdf = tmp_path / "100350-1 PLATE.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "PLATE  100350-1")
    page.insert_text((72, 96), "A36  1/4 THK")
    page.insert_text((72, 120), "SCALE 1/4")
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf)
    assert not (bom.method or "").startswith("table_")
    assert not (bom.method or "").startswith("ocr_time")
    xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert not xlsx.is_file()
    assert bom.lom_xlsx is None
    assert any("one-part quote" in n.lower() for n in bom.notes)

    native_takeoff = {
        "fitup_drivers": {
            "weight_calc": {
                "method": "pdf_bom_qty",
                "bom": {
                    "method": "pdf_bom_qty",
                    "rows": [
                        {
                            "item": "1",
                            "qty": 1,
                            "part_no": "100350-1",
                            "description": "PLATE",
                        }
                    ],
                },
            }
        }
    }
    assert write_lom_xlsx_for_job(pdf, native_takeoff) is None
    assert not xlsx.is_file()
    quoted = quote_bom_from_drawing(pdf_path=pdf)
    assert quoted.lom_xlsx is None
    assert not (quoted.method or "").startswith("table_")
    assert not xlsx.is_file()


def _col_letter(index: int) -> str:
    n = index + 1
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _write_grid_xlsx(path: Path, rows: list[list[str]]) -> Path:
    """As-drawn Time tab: whatever headers the sheet printed, not ITEM|QTY only."""
    import zipfile

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{_NS_MAIN}"><sheetData>',
    ]
    for r_i, row in enumerate(rows, start=1):
        cells = []
        for c_i, value in enumerate(row):
            ref = f"{_col_letter(c_i)}{r_i}"
            if r_i > 1 and str(value).isdigit():
                cells.append(_qty_cell(ref, value))
            else:
                cells.append(_inline_cell(ref, value))
        parts.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    parts.append("</sheetData></worksheet>")
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("xl/workbook.xml", _WORKBOOK)
        zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", "".join(parts))
    return dest


def test_qty_header_variants_are_quantity_columns():
    from quote_core.bom_xlsx import _header_column_map, _qty_header_info

    assert _qty_header_info("QTY") == (True, None, None)
    assert _qty_header_info("QTY -1") == (True, "1", None)
    assert _qty_header_info("QTY-1") == (True, "1", None)
    assert _qty_header_info("QTY -2") == (True, "2", None)
    assert _qty_header_info("-1") == (True, "1", None)
    assert _qty_header_info("1004747-1") == (True, "1", "1004747-1")
    assert _qty_header_info("P904225-1") == (True, "1", "P904225-1")
    assert _qty_header_info("1")[0] is False
    assert _qty_header_info("ITEM")[0] is False

    mapped = _header_column_map(
        ["ITEM", "QTY -1", "QTY -2", "PART NO", "DESCRIPTION"]
    )
    assert mapped is not None
    assert mapped["QTY_COLS"] == [(1, "1"), (2, "2")]
    assert mapped["ITEM"] == 0
    assert mapped["PART NO"] == 3


def test_qty_dash_headers_select_filled_dash_only(tmp_path: Path):
    """Workspace as-drawn first tab is QTY -1 / QTY -2, not a bare QTY."""
    cells = _kyle_28106_cell_rows()
    cells[0] = ["QTY -4", "QTY -3", "QTY -2", "QTY -1", "ITEM", "PART NO.", "DESCRIPTION"]
    path = _write_grid_xlsx(tmp_path / "28106-1-LOM.xlsx", cells)
    sourced = bom_from_lom_xlsx(path, bom_config="-1")
    _assert_kyle_28106_1(sourced)
    compact = [list(row) for row in cells]
    compact[0] = ["QTY-4", "QTY-3", "QTY-2", "QTY-1", "ITEM", "PART NO.", "DESCRIPTION"]
    compact_path = _write_grid_xlsx(tmp_path / "28106-1-compact-LOM.xlsx", compact)
    _assert_kyle_28106_1(bom_from_lom_xlsx(compact_path, bom_config="-1"))


def test_pn_named_qty_column_is_the_dash(tmp_path: Path):
    path = _write_grid_xlsx(tmp_path / "1004747-1-LOM.xlsx", _kyle_1004747_cell_rows())
    sourced = bom_from_lom_xlsx(path, bom_config="-1")
    _assert_kyle_1004747_1(sourced)


def test_blank_dash_uses_one_qty_column_not_the_sum(tmp_path: Path):
    """33612 live 94/47 was both dash columns added. Blank dash is one column."""
    rows = [
        ["ITEM", "QTY -1", "QTY -2", "PART NO", "DESCRIPTION"],
        ["A", "2", "2", "28275-1", "TUBE, ROUND"],
        ["B", "4", "4", "28276-1", "PLATE"],
        ["C", "1", "1", "28277-1", "STIFFENER"],
        ["D", "1", "1", "56657", ""],
        ["E", "1", "1", "97879", ""],
        ["F", "1", "8", "28278-1", "BRACKET"],
    ]
    path = _write_grid_xlsx(tmp_path / "33612-1-LOM.xlsx", rows)
    blank = bom_from_lom_xlsx(path, bom_config="")
    parts = {r.part_no for r in blank.rows}
    assert "56657" not in parts
    assert "97879" not in parts
    assert blank.piece_count == 8
    assert blank.part_number_count == 4
    assert blank.piece_count != 16
    dash1 = bom_from_lom_xlsx(path, bom_config="-1")
    assert dash1.piece_count == 8
    dash2 = bom_from_lom_xlsx(path, bom_config="-2")
    assert dash2.piece_count == 15
    by_item = {r.item: r for r in dash2.rows}
    assert by_item["F"].qty == 8


def test_skips_title_block_welding_wire_and_revision_pns(tmp_path: Path):
    cells = _kyle_p904225_cell_rows()
    cells.append(["1", "14", "61358", ""])
    cells.append(["1", "15", "73207", ""])
    path = _write_grid_xlsx(tmp_path / "P904225-1-LOM.xlsx", cells)
    sourced = bom_from_lom_xlsx(path, bom_config="")
    parts = {str(r.part_no or "") for r in sourced.rows}
    assert "P904225-1" not in parts
    assert "904225-1" not in parts
    assert "89176-1" not in parts
    assert "61358" not in parts
    assert "73207" not in parts
    assert "89100-1" in parts
    assert any("904226" in p for p in parts)
    assert all(str(r.item).isdigit() for r in sourced.rows)
    assert "12" not in {str(r.item) for r in sourced.rows}
    assert "13" not in {str(r.item) for r in sourced.rows}


def test_existing_qty_dash_xlsx_is_quote_without_reocr(tmp_path: Path, monkeypatch):
    pdf = tmp_path / "Time 28106- Weldment.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\n")
    cells = _kyle_28106_cell_rows()
    cells[0] = ["QTY -4", "QTY -3", "QTY -2", "QTY -1", "ITEM", "PART NO.", "DESCRIPTION"]
    path = _write_grid_xlsx(tmp_path / "28106-1-LOM.xlsx", cells)
    from quote_core.bom_xlsx import find_existing_lom_xlsx

    assert find_existing_lom_xlsx(pdf) == path

    def fail_ocr(**_kwargs):
        raise AssertionError("must not re-OCR when LOM.xlsx exists")

    monkeypatch.setattr("quote_core.bom.extract_bom_from_ocr_time_style", fail_ocr)
    bom = extract_bom(pdf_path=pdf, bom_config="-1")
    _assert_kyle_28106_1(bom)
    assert bom.to_dict()["source"] == "lom_xlsx"
    assert any("did not re-OCR" in n for n in bom.notes)


def test_desktop_qty_dash_xlsx_is_not_overwritten(tmp_path: Path, monkeypatch):
    from quote_core.bom_xlsx import (
        find_existing_lom_xlsx,
        is_desktop_lom_path,
        write_lom_xlsx_for_bom,
    )

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    cells = _kyle_28106_cell_rows()
    cells[0] = ["QTY -4", "QTY -3", "QTY -2", "QTY -1", "ITEM", "PART NO.", "DESCRIPTION"]
    confirmed = _write_grid_xlsx(desktop / "28106-1-LOM.xlsx", cells)
    before = confirmed.read_bytes()
    monkeypatch.setattr("quote_core.bom_xlsx._desktop_dirs", lambda: [desktop])

    job = tmp_path / "job"
    job.mkdir()
    pdf = job / "Time 28106- Weldment.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\n")

    assert is_desktop_lom_path(confirmed) is True
    assert find_existing_lom_xlsx(pdf) == confirmed
    written = write_lom_xlsx_for_bom(
        pdf,
        BomResult(rows=[BomRow(item="A", qty=0, part_no="16697-2", description="TUBE")]),
    )
    assert written == confirmed
    assert confirmed.read_bytes() == before
    quoted = quote_bom_from_drawing(pdf_path=pdf, bom_config="-1")
    _assert_kyle_28106_1(quoted)
    assert confirmed.read_bytes() == before
    assert not (job / f"{pdf.stem}-LOM.xlsx").is_file()


def test_xlsx_qty_inch_note_is_gasket_not_ten():
    from quote_core.bom_xlsx import _xlsx_qty_from_cell

    assert _xlsx_qty_from_cell('10"') == (1, True)
    assert _xlsx_qty_from_cell("10″") == (1, True)
    assert _xlsx_qty_from_cell("10") == (10, False)
    assert _xlsx_qty_from_cell("") == (0, False)


def test_workspace_summary_footer_does_not_double_102728(tmp_path: Path):
    """Workspace 9518 B reconstruction, not Desktop 6766 B ITEM|QTY."""
    rows = [["ITEM", "QTY", "PART NO", "DESCRIPTION"]]
    rows.extend(
        [item, str(qty), pn, desc] for item, qty, pn, desc in _KYLE_102728_1
    )
    rows.append(["", "97", "51 PNs", "qty=97"])
    path = _write_grid_xlsx(tmp_path / "102728-1-workspace-LOM.xlsx", rows)
    sourced = bom_from_lom_xlsx(path)
    _assert_kyle_102728_1(sourced)
    assert sourced.piece_count == 97
    assert sourced.part_number_count == 51
    assert "51 PNs" not in {str(r.part_no) for r in sourced.rows}


def test_as_drawn_tally_footers_are_dropped(tmp_path: Path):
    cells = _kyle_28106_cell_rows()
    cells[0] = ["QTY -4", "QTY -3", "QTY -2", "QTY -1", "ITEM", "PART NO.", "DESCRIPTION"]
    cells.append(["", "", "", "11", "pcs", "11", "13"])
    path = _write_grid_xlsx(tmp_path / "28106-1-LOM.xlsx", cells)
    _assert_kyle_28106_1(bom_from_lom_xlsx(path, bom_config="-1"))

    dual = [
        ["ITEM", "QTY -1", "QTY -2", "PART NO", "DESCRIPTION"],
        ["A", "2", "2", "28275-1", "TUBE, ROUND"],
        ["B", "4", "4", "28276-1", "PLATE"],
        ["C", "1", "1", "28277-1", "STIFFENER"],
        ["", "7", "7", "21 rows", "qty=47"],
    ]
    sheet = _write_grid_xlsx(tmp_path / "33612-1-LOM.xlsx", dual)
    blank = bom_from_lom_xlsx(sheet, bom_config="")
    assert blank.piece_count == 7
    assert blank.part_number_count == 3
    assert "21 rows" not in {str(r.part_no) for r in blank.rows}

    unique = [
        ["ITEM", "QTY", "PART NO", "DESCRIPTION"],
        ["A", "2", "16697-1", "TUBE"],
        ["B", "1", "16697-2", "PLATE"],
        ["", "", "unique PNs", ""],
        ["", "3", "unique PNs", "qty=9"],
    ]
    u_path = _write_grid_xlsx(tmp_path / "21727-1-LOM.xlsx", unique)
    sourced = bom_from_lom_xlsx(u_path)
    assert sourced.part_number_count == 2
    assert sourced.piece_count == 3
    assert "unique PNs" not in {str(r.part_no) for r in sourced.rows}


def test_gasket_inch_qty_stays_and_count_footer_drops(tmp_path: Path):
    """1004611 S 10\" is the gasket note (qty 1). Footer PN 22 / qty=22 is not."""
    rows = [
        ["-2", "-1", "ITEM", "PART NO", "DESCRIPTION"],
        ["", "1", "A", "1004611-DWG", ""],
        ["", '10"', "S", "80054-1", '10" GASKET'],
        ["1", "", "U", "1004675-1", ""],
        ["", "22", "", "22", "qty=22"],
    ]
    path = _write_grid_xlsx(tmp_path / "1004611-1-LOM.xlsx", rows)
    sourced = bom_from_lom_xlsx(path, bom_config="-1")
    by_item = {r.item: r for r in sourced.rows}
    parts = {str(r.part_no) for r in sourced.rows}
    assert "S" in by_item
    assert by_item["S"].part_no == "80054-1"
    assert by_item["S"].qty == 1
    assert "10" in by_item["S"].description
    assert "U" not in by_item
    assert "22" not in parts
    assert sourced.part_number_count == 2
    assert sourced.piece_count == 2


def test_desktop_item_qty_102728_still_51_97_without_footer(tmp_path: Path):
    """Desktop 6766 B ITEM|QTY reader is unchanged. Do not 'fix' 102728 via it."""
    path = _write_item_qty_xlsx(tmp_path / "102728-1-LOM.xlsx", _kyle_rows())
    sourced = bom_from_lom_xlsx(path)
    _assert_kyle_102728_1(sourced)
    assert sourced.piece_count == 97
    assert sourced.part_number_count == 51
