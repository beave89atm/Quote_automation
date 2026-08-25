"""Kyle-confirmed LOM.xlsx is the BOM source; clip-grid writes that sheet."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from quote_core.bom import extract_bom
from quote_core.lom_xlsx import extract_bom_from_lom_xlsx, find_lom_xlsx, write_lom_xlsx


def write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    write_lom_xlsx(path, rows)


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


def test_1001898_dash1_is_27_not_paint_20(tmp_path: Path):
    """Kyle: 1001898-1 -1 = 27 pcs. OCR 20 was the '20 PLCS' paint note."""
    header = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    # 5×1 + 11×2 = 16 PN / 27 pcs on -1. One -2-only row must be omitted.
    letters = "ABCDEFGHJKLMNPQR"
    for i, letter in enumerate(letters[:5]):
        rows.append(["-", "-", "-", "1", letter, f"10019{10+i:02d}-1", f"PLATE {letter}"])
    for i, letter in enumerate(letters[5:16]):
        desc = "20 PLCS PAINT ALL OVER" if i == 0 else f"TUBE {letter}"
        rows.append(["-", "-", "1", "2", letter, f"10019{15+i:02d}-1", desc])
    rows.append(["-", "-", "1", "-", "Z", "1001999-1", "OTHER DASH ONLY"])
    path = tmp_path / "1001898-1-LOM.xlsx"
    write_minimal_xlsx(path, rows)
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    assert bom.piece_count != 20
    assert bom.piece_count == 27, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    assert all(r.part_no != "1001999-1" for r in bom.rows)


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
