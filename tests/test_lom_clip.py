"""Clip printed LIST OF MATERIAL grid → xlsx is the only takeoff source."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import fitz

from quote_core.bom import extract_bom
from quote_core.lom_clip import (
    clip_lom_grid_from_pdf,
    ensure_lom_xlsx,
    words_to_grid,
)
from quote_core.lom_xlsx import extract_bom_from_lom_xlsx


def _word(text: str, x0: float, y0: float, width: float = 20) -> dict:
    return {"text": text, "x0": x0, "y0": y0, "x1": x0 + width, "y1": y0 + 8}


def test_words_to_grid_keeps_dash_columns_and_skips_left_paint():
    # Left-side paint note must not become a qty column.
    words = [
        _word("20", 40, 80),
        _word("PLCS", 70, 80),
        _word("-4", 360, 200, 16),
        _word("-3", 390, 200, 16),
        _word("-2", 420, 200, 16),
        _word("-1", 450, 200, 16),
        _word("ITEM", 480, 200, 28),
        _word("PART", 530, 200, 28),
        _word("NO", 562, 200, 16),
        _word("DESCRIPTION", 600, 200, 70),
        _word("-", 360, 220, 12),
        _word("-", 390, 220, 12),
        _word("-", 420, 220, 12),
        _word("1", 450, 220, 12),
        _word("A", 480, 220, 12),
        _word("1001901-1", 530, 220, 50),
        _word("PLATE", 600, 220, 40),
        _word("-", 360, 240, 12),
        _word("-", 390, 240, 12),
        _word("1", 420, 240, 12),
        _word("2", 450, 240, 12),
        _word("B", 480, 240, 12),
        _word("1001902-1", 530, 240, 50),
        _word("20", 600, 240, 16),
        _word("PLCS", 620, 240, 28),
        _word("PAINT", 655, 240, 36),
    ]
    from quote_core.lom_clip import detect_lom_table_words

    table = detect_lom_table_words(words)
    grid = words_to_grid(table)
    assert grid[0][:6] == ["-4", "-3", "-2", "-1", "ITEM", "PART NO"] or grid[0][:5] == [
        "-4",
        "-3",
        "-2",
        "-1",
        "ITEM",
    ]
    body = grid[1:]
    assert any("1001901-1" in "".join(r) for r in body)
    assert not any(r[0] == "20" and "PLCS" in "".join(r) for r in body)


def _write_1001898_pdf(path: Path) -> None:
    """Printed Time LOM on the right; paint note '20 PLCS' on the left."""
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text((40, 80), "20 PLCS PAINT ALL OVER", fontsize=11)
    page.insert_text((360, 40), "LIST OF MATERIAL", fontsize=11)
    xs = [360, 390, 420, 450, 480, 530, 620]
    headers = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    y = 70
    for x, h in zip(xs, headers):
        page.insert_text((x, y), h, fontsize=8)
    letters = list("ABCDEFGHJKLMNPQR")
    # 5×1 + 11×2 = 27 pcs
    rows = []
    for i, letter in enumerate(letters[:5]):
        rows.append(["-", "-", "-", "1", letter, f"10019{10+i:02d}-1", f"PLATE {letter}"])
    for i, letter in enumerate(letters[5:16]):
        desc = "20 PLCS PAINT" if i == 0 else f"TUBE {letter}"
        rows.append(["-", "-", "1", "2", letter, f"10019{15+i:02d}-1", desc])
    rows.append(["-", "-", "1", "-", "Z", "1001999-1", "DASH2 ONLY"])
    y = 90
    for row in rows:
        for x, cell in zip(xs, row):
            page.insert_text((x, y), cell, fontsize=8)
        y += 14
    doc.save(path)
    doc.close()


def test_clip_pdf_1001898_dash1_is_27_not_20(tmp_path: Path):
    pdf = tmp_path / "1001898-1.pdf"
    _write_1001898_pdf(pdf)
    with patch("quote_core.bom.extract_bom_from_ocr_time_style") as ocr:
        bom = extract_bom(pdf, library_folder=tmp_path, bom_config="1")
        ocr.assert_not_called()
    assert bom.method == "lom_xlsx", bom.notes
    assert bom.piece_count != 20
    assert bom.piece_count == 27, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    assert (tmp_path / "1001898-1-LOM.xlsx").exists() or list(tmp_path.glob("*LOM.xlsx"))


def test_ensure_reuses_kyle_lom_without_second_parser(tmp_path: Path):
    from quote_core.lom_xlsx import write_lom_xlsx

    header = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    write_lom_xlsx(
        tmp_path / "1001898-1-LOM.xlsx",
        [
            header,
            ["-", "-", "-", "1", "A", "1001910-1", "PLATE"],
            ["-", "-", "1", "2", "B", "1001911-1", "20 PLCS PAINT"],
        ],
    )
    pdf = tmp_path / "1001898-1.pdf"
    _write_1001898_pdf(pdf)
    path, notes = ensure_lom_xlsx(pdf, library_folder=tmp_path, part_key="1001898-1")
    assert path is not None
    assert path.name == "1001898-1-LOM.xlsx"
    assert any("Kyle-confirmed" in n for n in notes)
    bom = extract_bom_from_lom_xlsx(path, bom_config="1")
    # Existing Kyle sheet (2 rows / 3 pcs) wins over re-clip of the PDF.
    assert bom.piece_count == 3


def test_lom_grid_without_xlsx_does_not_use_ocr_as_truth(tmp_path: Path):
    pdf = tmp_path / "grid.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((360, 40), "LIST OF MATERIAL", fontsize=12)
    page.insert_text((360, 70), "ITEM PART NO QTY", fontsize=10)
    doc.save(pdf)
    doc.close()
    with patch("quote_core.lom_clip.clip_lom_grid_from_pdf", return_value=([], ["no rows"])):
        with patch("quote_core.bom.extract_bom_from_ocr_time_style") as ocr:
            bom = extract_bom(pdf, library_folder=tmp_path, bom_config="1")
            ocr.assert_not_called()
    assert bom.method != "ocr_time"
    assert bom.piece_count == 0 or not bom.rows
    assert any("OCR is not takeoff truth" in n or "refusing whole-page OCR" in n for n in bom.notes)


def test_clip_writes_xlsx_then_reader_is_only_parser(tmp_path: Path):
    pdf = tmp_path / "1004747.pdf"
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text((360, 40), "LIST OF MATERIAL", fontsize=11)
    xs = [360, 390, 420, 450, 480, 530, 620]
    headers = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    for x, h in zip(xs, headers):
        page.insert_text((x, 70), h, fontsize=8)
    page.insert_text((360, 90), "-")
    page.insert_text((390, 90), "-")
    page.insert_text((420, 90), "-")
    page.insert_text((450, 90), "1")
    page.insert_text((480, 90), "A")
    page.insert_text((530, 90), "1004810-1")
    page.insert_text((620, 90), "PLATE")
    doc.save(pdf)
    doc.close()
    grid, notes = clip_lom_grid_from_pdf(pdf)
    assert grid and grid[0][3] == "-1" or any("-1" in row for row in grid)
    dest, more = ensure_lom_xlsx(pdf, part_key="1004747")
    assert dest is not None
    assert dest.suffix == ".xlsx"
    bom = extract_bom_from_lom_xlsx(dest, bom_config="1")
    assert bom.method == "lom_xlsx"
    assert bom.piece_count >= 1
    assert notes or more
