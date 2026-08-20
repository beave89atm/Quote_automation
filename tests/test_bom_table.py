"""Table-first LIST OF MATERIAL grid — 102728-1 Time-style ground truth."""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import extract_bom, extract_bom_from_ocr_time_style
from quote_core.bom_table import (
    is_material_list_item,
    parse_material_list_cells,
    parse_material_list_text,
    parse_material_list_words,
    text_has_material_list_grid,
    time_item_letters,
)

# Ground truth: Time 102728-1 WELDMENT, PLATFORM — 51 balloons, skip I/O.
_THROUGH = "BC"
_BB_PART = "102727-4"
_BB_DESC = "TUBE, ROUND"


def _platform_items() -> list[str]:
    items = time_item_letters(through=_THROUGH)
    assert len(items) == 51
    return items


def _platform_cell_rows(*, drop: set[str] | None = None) -> list[list[str]]:
    drop = drop or set()
    rows = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for i, item in enumerate(_platform_items()):
        if item in drop:
            continue
        if item == "BB":
            rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])
    return rows


def _platform_table_text(*, drop: set[str] | None = None) -> str:
    lines = [
        "WELDMENT, PLATFORM",
        "102728-1",
        "TIME MANUFACTURING",
        "SHEET 1 OF 2",
        "LIST OF MATERIAL",
    ]
    for row in _platform_cell_rows(drop=drop):
        lines.append(" | ".join(row))
    return "\n".join(lines)


def test_time_item_letters_skip_i_and_o_and_reach_bc():
    items = _platform_items()
    assert items[0] == "A" and items[-1] == "BC"
    assert "I" not in items and "O" not in items
    assert "AI" not in items and "AO" not in items and "IA" not in items
    assert items[items.index("H") + 1] == "J"
    assert items[items.index("N") + 1] == "P"
    assert items[items.index("AH") + 1] == "AJ"
    assert "BB" in items and "BA" in items and "BC" in items
    assert is_material_list_item("BB")
    assert not is_material_list_item("I")
    assert not is_material_list_item("O")
    assert not is_material_list_item("IO")


def test_parse_51_row_time_table_cells():
    rows = _platform_cell_rows()
    bom = parse_material_list_cells(rows)
    assert bom.method == "table_material_list"
    assert len(bom.rows) == 51
    assert bom.part_number_count == 51
    by_item = {r.item: r for r in bom.rows}
    assert by_item["BB"].qty == 2
    assert by_item["BB"].part_no == _BB_PART
    assert "TUBE" in by_item["BB"].description.upper()
    assert "ROUND" in by_item["BB"].description.upper()
    assert bom.piece_count == 52  # 50×1 + BB×2
    assert all(r.item != "I" and r.item != "O" for r in bom.rows)


def test_parse_51_row_time_table_text():
    text = _platform_table_text()
    assert text_has_material_list_grid(text)
    bom = parse_material_list_text(text)
    assert len(bom.rows) == 51
    assert {r.part_no for r in bom.rows}
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def test_extract_bom_prefers_table_over_page_regex():
    """Loose single-letter bait must not win once a grid header is present."""
    bait = "\n".join(
        [
            "2 | A | 35122-1",
            "1 | D | 29754-2",
            "2 | E | 29754-3",
            "1 | O | 99999-1",
            "1 | P | 88888-1",
        ]
    )
    text = _platform_table_text() + "\n\n" + bait
    bom = extract_bom(text=text)
    assert bom.method and bom.method.startswith("table_")
    assert bom.part_number_count == 51
    items = {r.item for r in bom.rows}
    assert "BB" in items
    assert "O" not in items
    assert not any(r.part_no == "99999-1" for r in bom.rows)


def test_dash_columns_quoting_minus_1_does_not_use_minus_2():
    text = """
LIST OF MATERIAL
-2 | -1 | ITEM | PART NO. | DESCRIPTION
1 | - | A | 16697-1 | TUBE, SHORT
- | 1 | B | 16697-2 | TUBE, LONG
2 | 1 | C | 15864-2 | STIFFENER
"""
    dash1 = parse_material_list_text(text, bom_config="1")
    by_item = {r.item: r for r in dash1.rows}
    assert set(by_item) == {"B", "C"}
    assert by_item["B"].part_no == "16697-2" and by_item["B"].qty == 1
    assert by_item["C"].qty == 1  # -1 column only; do not sum with -2
    assert "A" not in by_item
    assert dash1.piece_count == 2
    assert dash1.method == "table_material_list_multi_qty"

    dash2 = parse_material_list_text(text, bom_config="2")
    by2 = {r.item: r for r in dash2.rows}
    assert set(by2) == {"A", "C"}
    assert by2["A"].part_no == "16697-1"
    assert by2["C"].qty == 2
    assert "B" not in by2


def test_incomplete_tall_list_flags_review_without_padding():
    bom = parse_material_list_cells(_platform_cell_rows(drop={"C", "AA", "AZ"}))
    assert len(bom.rows) == 48
    joined = " ".join(bom.notes).lower()
    assert "incomplete" in joined or "missing" in joined
    assert "flag review" in joined
    assert "do not pad" in joined
    assert not any(r.item in {"C", "AA", "AZ"} for r in bom.rows)
    # BB still present with qty 2 — gaps are review, not invented rows.
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def test_word_boxes_read_cells_not_page_blob():
    """Positioned words (native PDF / OCR boxes) segment into cells."""
    items = _platform_items()
    words: list[dict] = [
        {"text": "QTY", "x0": 10, "y0": 10, "x1": 40, "y1": 22},
        {"text": "ITEM", "x0": 50, "y0": 10, "x1": 90, "y1": 22},
        {"text": "PART", "x0": 100, "y0": 10, "x1": 140, "y1": 22},
        {"text": "NO.", "x0": 142, "y0": 10, "x1": 168, "y1": 22},
        {"text": "DESCRIPTION", "x0": 200, "y0": 10, "x1": 280, "y1": 22},
    ]
    for i, item in enumerate(items):
        y = 30.0 + i * 12.0
        qty = "2" if item == "BB" else "1"
        part = _BB_PART if item == "BB" else f"1028{i:02d}-1"
        desc = _BB_DESC if item == "BB" else f"COMPONENT {item}"
        words.append({"text": qty, "x0": 12, "y0": y, "x1": 28, "y1": y + 10})
        words.append({"text": item, "x0": 55, "y0": y, "x1": 85, "y1": y + 10})
        words.append({"text": part, "x0": 105, "y0": y, "x1": 170, "y1": y + 10})
        words.append({"text": desc, "x0": 205, "y0": y, "x1": 300, "y1": y + 10})
    bom = parse_material_list_words(words)
    assert len(bom.rows) == 51
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def _write_lom_pdf(path: Path, headers: list[str], rows: list[list[str]], *, title: str) -> None:
    import fitz

    row_h = 11
    height = 80 + (len(rows) + 2) * row_h + 40
    doc = fitz.open()
    page = doc.new_page(width=792, height=max(1224, height))
    page.insert_text((40, 28), title, fontsize=10)
    page.insert_text((40, 42), "LIST OF MATERIAL", fontsize=10)
    xs = [360, 410, 460, 560]
    if len(headers) == 5:
        xs = [320, 370, 420, 480, 580]
    y = 64
    for i, cell in enumerate(headers):
        page.insert_text((xs[i], y), cell, fontsize=8)
    for row in rows:
        y += row_h
        for i, cell in enumerate(row):
            page.insert_text((xs[i], y), str(cell), fontsize=8)
    doc.save(path)
    doc.close()


def test_pdf_table_path_does_not_pad_library_subweldments(tmp_path: Path):
    items = _platform_items()
    data_rows = []
    for i, item in enumerate(items):
        if item == "BB":
            data_rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            data_rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])
    pdf = tmp_path / "102728-1.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING  SHEET 1 OF 2",
    )
    lib = tmp_path / "library"
    lib.mkdir()
    # Nested sub-weldment / child drawings — must not become BOM rows.
    for extra in ("102726-1.pdf", "102729.pdf", "102999-2.pdf"):
        (lib / extra).write_bytes(b"%PDF-1.4\n%\n")

    bom = extract_bom(pdf_path=pdf, library_folder=lib, bom_config="1")
    assert bom.part_number_count == 51, [f"{r.item}:{r.part_no}" for r in bom.rows]
    assert bom.method and bom.method.startswith("table_")
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    parts = {r.part_no for r in bom.rows}
    assert "102726-1" not in parts
    assert "102729-1" not in parts
    assert not any(p.startswith("102999") for p in parts)

    # Direct Time-style entry point must also prefer the table and skip padding.
    ocr = extract_bom_from_ocr_time_style(pdf, library_folder=lib, bom_config="1")
    assert ocr.part_number_count == 51
    assert ocr.method and ocr.method.startswith("table_")


def test_pdf_dash_columns_quote_minus_1_only(tmp_path: Path):
    pdf = tmp_path / "28106-1.pdf"
    _write_lom_pdf(
        pdf,
        ["-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"],
        [
            ["1", "-", "A", "16697-1", "TUBE, SHORT"],
            ["-", "1", "B", "16697-2", "TUBE, LONG"],
            ["2", "1", "C", "15864-2", "STIFFENER"],
        ],
        title="LOWER BOOM WELDMENT 28106-1 LIST OF MATERIAL",
    )
    bom = extract_bom(pdf_path=pdf, bom_config="1")
    by_item = {r.item: r for r in bom.rows}
    assert set(by_item) == {"B", "C"}
    assert by_item["C"].qty == 1
    assert by_item["B"].part_no == "16697-2"
    assert bom.piece_count == 2
