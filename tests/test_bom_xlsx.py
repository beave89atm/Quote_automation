"""Quote BOM is the written LOM.xlsx. No side-channel JSON."""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import BomResult, BomRow, bom_from_lom_xlsx, extract_bom
from quote_core.bom_xlsx import (
    apply_lom_xlsx_to_takeoff,
    read_lom_xlsx,
    write_lom_xlsx,
)

from tests.test_bom_table import (
    _KYLE_102728_1,
    _assert_kyle_102728_1,
    _assert_kyle_xlsx,
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
