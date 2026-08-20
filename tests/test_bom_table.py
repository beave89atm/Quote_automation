"""Table-first LIST OF MATERIAL grid — 102728-1 Time-style ground truth."""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import (
    _parse_qty_item_part_hits,
    _vote_bom_rows,
    extract_bom,
    extract_bom_from_ocr_time_style,
)
from quote_core.bom_table import (
    harvest_material_list_lines,
    harvest_ocr_row_strips,
    is_material_list_item,
    material_list_header_seen,
    parse_material_list_cells,
    parse_material_list_text,
    parse_material_list_words,
    parse_ocr_row_strip,
    pick_best_material_list,
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


def test_undelimited_ocr_line_reads_bb_cells():
    """Live OCR often emits a row as one blob, not pipe-delimited cells."""
    text = (
        "LIST OF MATERIAL\n"
        "QTY ITEM PART NO. DESCRIPTION\n"
        "1 A 102800-1 PLATE\n"
        "2 BB 102727-4 TUBE, ROUND\n"
        "1 BC 102850-1 CAP\n"
    )
    bom = parse_material_list_text(text)
    by_item = {r.item: r for r in bom.rows}
    assert by_item["BB"].qty == 2
    assert by_item["BB"].part_no == _BB_PART
    assert "TUBE" in by_item["BB"].description.upper()


def _write_lom_page(doc, headers: list[str], rows: list[list[str]], *, title: str) -> None:
    import fitz

    row_h = 11
    height = 80 + (len(rows) + 2) * row_h + 40
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


def test_lom_header_on_page_4_of_five_page_pdf(tmp_path: Path):
    """102728-1 live PDF: LOM is on a later sheet, not page 0 / first two."""
    import fitz

    items = _platform_items()
    data_rows = []
    for i, item in enumerate(items):
        if item == "BB":
            data_rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            data_rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])

    pdf = tmp_path / "Time 102728- Weldment.pdf"
    doc = fitz.open()
    for i in range(4):
        page = doc.new_page(width=792, height=612)
        page.insert_text((72, 72), f"ISO VIEW SHEET {i + 1}  WELDMENT PLATFORM  NO BOM HERE")
        # Page-0 bait the old single-letter regex would keep (A,D,E,O,P).
        if i == 0:
            page.insert_text((72, 120), "2 | A | 35122-1\n1 | D | 29754-2\n2 | E | 29754-3")
            page.insert_text((72, 160), "1 | O | 99999-1\n1 | P | 88888-1")
    _write_lom_page(
        doc,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING  SHEET 1 OF 2",
    )
    assert len(doc) == 5
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf, bom_config="1")
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert bom.part_number_count == 51, [f"{r.item}:{r.part_no}" for r in bom.rows]
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert not any(r.part_no in {"99999-1", "88888-1", "35122-1"} for r in bom.rows)


def test_lom_header_found_does_not_fallback_to_regex(tmp_path: Path):
    """If the grid header is found, do not return 10 junk single-letter PNs."""
    import fitz

    pdf = tmp_path / "header_only_later_page.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=792, height=612)
        if i == 0:
            page.insert_text((72, 72), "2 | A | 35122-1")
            page.insert_text((72, 90), "1 | D | 29754-2")
            page.insert_text((72, 108), "2 | E | 29754-3")
            page.insert_text((72, 126), "1 | O | 99999-1")
            page.insert_text((72, 144), "1 | P | 88888-1")
    page = doc.new_page(width=792, height=612)
    page.insert_text((400, 500), "LIST OF MATERIAL", fontsize=10)
    page.insert_text((400, 520), "QTY", fontsize=8)
    page.insert_text((440, 520), "ITEM", fontsize=8)
    page.insert_text((490, 520), "PART NO.", fontsize=8)
    page.insert_text((580, 520), "DESCRIPTION", fontsize=8)
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf)
    assert material_list_header_seen(bom)
    assert not (bom.method or "").startswith("ocr_time")
    parts = {r.part_no for r in bom.rows}
    assert "99999-1" not in parts
    assert "88888-1" not in parts
    assert "35122-1" not in parts
    joined = " ".join(bom.notes).lower()
    assert "not falling back" in joined or "header found" in joined or "flag review" in joined


def _write_right_side_lom_bottom_header(page, rows: list[list[str]]) -> None:
    """102728-1 visual spec: tall right-hand grid, header at the BOTTOM, data up."""
    xs = [560, 600, 640, 720]
    # Title block / LOM title at the bottom; column headers just above; A at bottom.
    page.insert_text((560, 1180), "LIST OF MATERIAL", fontsize=8)
    y = 1164
    for i, cell in enumerate(["QTY", "ITEM", "PART NO.", "DESCRIPTION"]):
        page.insert_text((xs[i], y), cell, fontsize=7)
    # Data stacks upward: A nearest the header, BC at the top.
    y = 1150
    for row in rows:
        for i, cell in enumerate(row):
            page.insert_text((xs[i], y), str(cell), fontsize=7)
        y -= 11
    # Decoy single-cell "-1" above the top row (item BC), as on the real sheet.
    page.insert_text((560, y - 4), "-1", fontsize=7)


def test_prefers_tall_right_side_table_over_short_decoy_lom(tmp_path: Path):
    """A 3-row LOM on a later page must not beat the 51-row right-side grid."""
    import fitz

    items = _platform_items()
    # Bottom-up write: first appended row is A (nearest header).
    data_rows = []
    for i, item in enumerate(items):
        if item == "BB":
            data_rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            data_rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])

    pdf = tmp_path / "Time 102728- Weldment decoy.pdf"
    doc = fitz.open()
    # Pages 1-3: empty / iso (no table).
    for i in range(3):
        doc.new_page(width=792, height=1224).insert_text(
            (72, 72), f"ISO VIEW {i + 1}"
        )
    # Page 4 (index 3): the real tall right-side LIST OF MATERIAL.
    weld = doc.new_page(width=792, height=1224)
    weld.insert_text((40, 40), "WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING")
    _write_right_side_lom_bottom_header(weld, data_rows)
    # Page 5 (index 4): short decoy LOM matching the live 3-row miss.
    decoy = doc.new_page(width=792, height=1224)
    decoy.insert_text((400, 200), "LIST OF MATERIAL", fontsize=10)
    decoy.insert_text((400, 220), "QTY | ITEM | PART NO. | DESCRIPTION", fontsize=8)
    decoy.insert_text((400, 236), "1 | B | 102709-1 | DECOY", fontsize=8)
    decoy.insert_text((400, 252), "1 | C | 100585-23 | DECOY", fontsize=8)
    decoy.insert_text((400, 268), "1 | SE | TAS | GARBAGE", fontsize=8)
    assert len(doc) == 5
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf, bom_config="1")
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert bom.part_number_count == 51, [f"{r.item}:{r.part_no}" for r in bom.rows]
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    parts = {r.part_no for r in bom.rows}
    assert "102709-1" not in parts
    assert "100585-23" not in parts
    assert not any(r.item == "SE" for r in bom.rows)


def test_p_prefix_weldment_pn_is_not_a_native_false_hit():
    """P904225-1 is a title-block weldment PN, not item P + 904225-1."""
    title = (
        "WELDMENT, PLATFORM\n"
        "P904225-1\n"
        "TIME MANUFACTURING\n"
        "DWG NO P904225-1\n"
        "SHEET 1 OF 1\n"
    )
    bom = extract_bom(text=title)
    parts = {r.part_no for r in bom.rows}
    assert "904225-1" not in parts
    assert "P904225-1" not in parts
    assert not any(r.item == "P" for r in bom.rows)

    hits = _parse_qty_item_part_hits([title], set())
    assert not any(str(h.get("part_no") or "") in {"904225-1", "P904225-1"} for h in hits)
    assert not any(h.get("item") == "P" and "904225" in str(h.get("part_no") or "") for h in hits)
    voted = _vote_bom_rows(hits, set())
    assert not any(r.part_no in {"904225-1", "P904225-1"} for r in voted)

    assert parse_ocr_row_strip("P904225-1 WELDMENT") is None
    harvested = harvest_ocr_row_strips(["P904225-1 WELDMENT", "DWG NO P904225-1"])
    assert not any(r.part_no in {"904225-1", "P904225-1"} for r in harvested.rows)
    # Spaced item P + part is a real balloon, not the glued drawing number.
    real_p = parse_ocr_row_strip("1 P 904225-1 TUBE")
    assert real_p is not None
    assert real_p["item"] == "P" and real_p["part_no"] == "904225-1"


def test_dash_column_index_qty_bleed_is_not_piece_count():
    """103516 live: 13/14/17/18/20 are column-index bleed, not 121 pcs."""
    letters = [c for c in "ABCDEFGHJKLMNPQRSTUVW"]
    assert len(letters) == 21
    bleed = {"A": 13, "B": 14, "D": 17, "E": 18, "F": 20}
    lines = [
        "LIST OF MATERIAL",
        "-4 | -3 | -2 | -1 | ITEM | PART NO. | DESCRIPTION",
    ]
    for i, item in enumerate(letters):
        q = bleed.get(item, 1)
        lines.append(f"- | - | - | {q} | {item} | 1035{i:02d}-1 | TUBE")
    bom = parse_material_list_text("\n".join(lines), bom_config="1")
    assert len(bom.rows) == 21
    assert bom.piece_count == 21
    assert not any(r.qty >= 10 for r in bom.rows)

    strips = harvest_ocr_row_strips(
        [f"{bleed.get(item, 1)} {item} 1035{i:02d}-1 TUBE" for i, item in enumerate(letters)]
    )
    assert len(strips.rows) == 21
    assert sum(r.qty for r in strips.rows) == 21
    thirteen = parse_ocr_row_strip("13 A 103500-1 TUBE")
    assert thirteen is not None and thirteen["qty"] == 1
    glued = parse_ocr_row_strip("BB2 102727-4 TUBE, ROUND")
    assert glued["qty"] == 2 and glued["part_no"] == _BB_PART


def test_eco_and_title_block_rows_are_dropped():
    """28106 / 33612 / 21727 / 1007922 / P904225: ECO and title-block are not parts."""
    lines = [
        "A 16697-1 TUBE, SHORT",
        "B 16697-2 TUBE, LONG",
        "C 72143 ADDED —4 AND ITEM P",
        "E 61358 REVISION NOTE",
        "S 73207 CONFIG NOTE",
        "AN 89176-1 PROPERTY OF TIME MANUFACTURING",
        "B 56657 PROPERTY OF TIME",
        "BT 97879 THIS DRAWING IS THE PROPERTY OF TIME",
        "BBD 02727-4 TUBE, ROUND",
    ]
    bom = harvest_ocr_row_strips(lines)
    parts = {r.part_no for r in bom.rows}
    assert "16697-1" in parts and "16697-2" in parts
    assert _BB_PART in parts
    for junk in ("72143", "61358", "73207", "89176-1", "56657", "97879"):
        assert junk not in parts, junk
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert parse_ocr_row_strip("C 72143 ADDED —4 AND ITEM P") is None
    assert parse_ocr_row_strip("AN 89176-1 PROPERTY OF TIME MANUFACTURING") is None

    cells = parse_material_list_text(
        "LIST OF MATERIAL\n"
        "QTY | ITEM | PART NO. | DESCRIPTION\n"
        "1 | A | 16697-1 | TUBE, SHORT\n"
        "1 | C | 72143 | ADDED —4 AND ITEM P\n"
        "2 | BB | 102727-4 | TUBE, ROUND\n"
    )
    cell_parts = {r.part_no for r in cells.rows}
    assert "16697-1" in cell_parts
    assert "72143" not in cell_parts
    assert _BB_PART in cell_parts


def test_unread_band_keeps_time_pn_and_4digit_hose_guide():
    """1004611 / 1004747-1: keep unread Time PNs; 6993-1 hose guide; drop AE/BE/BS junk."""
    lines = [
        "A 100100-1 TUBE",
        "B 100101-1 PLATE",
        "",
        "100102-1 SUPPORT",
        "6993-1 HOSE GUIDE",
        "AE 56657 PROPERTY OF TIME",
        "BE 97879 THIS DRAWING IS THE PROPERTY OF TIME",
        "BS 72143 ADDED ITEM C",
    ]
    bom = harvest_ocr_row_strips(lines)
    parts = {r.part_no for r in bom.rows}
    assert "100100-1" in parts
    assert "100101-1" in parts
    assert "100102-1" in parts
    assert "6993-1" in parts
    assert "56657" not in parts
    assert "97879" not in parts
    assert "72143" not in parts
    hose = parse_ocr_row_strip("6993-1 HOSE GUIDE")
    assert hose is not None and hose["part_no"] == "6993-1"


def test_p904225_drops_property_row_keeps_table_child_not_folder(tmp_path: Path):
    """P904225-1 is not a BOM row; AN=89176-1 PROPERTY OF TIME drops; table child stays."""
    text = (
        "WELDMENT, PLATFORM\n"
        "P904225-1\n"
        "TIME MANUFACTURING\n"
        "DWG NO P904225-1\n"
        "LIST OF MATERIAL\n"
        "QTY | ITEM | PART NO. | DESCRIPTION\n"
        "1 | A | 89100-1 | TUBE\n"
        "1 | G | P904226-1 | SUPPORT\n"
        "1 | AN | 89176-1 | PROPERTY OF TIME MANUFACTURING\n"
    )
    bom = extract_bom(text=text)
    parts = {r.part_no for r in bom.rows}
    assert "P904225-1" not in parts
    assert "904225-1" not in parts
    assert "89100-1" in parts
    assert "89176-1" not in parts
    assert "904226-1" in parts or "P904226-1" in parts
    assert bom.method and bom.method.startswith("table_")

    child = parse_ocr_row_strip("1 G P904226-1 SUPPORT")
    assert child is not None
    assert child["item"] == "G"
    assert "904226" in child["part_no"]

    # Folder children that are not in the table must not be padded.
    pdf = tmp_path / "P904225-1.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        [
            ["1", "A", "89100-1", "TUBE"],
            ["1", "G", "89101-1", "PLATE"],
        ],
        title="WELDMENT, PLATFORM  P904225-1  TIME MANUFACTURING",
    )
    lib = tmp_path / "library"
    lib.mkdir()
    for extra in ("P904226-1.pdf", "P904230-1.pdf", "P904231-1.pdf", "P904245-1.pdf"):
        (lib / extra).write_bytes(b"%PDF-1.4\n%\n")
    padded = extract_bom(pdf_path=pdf, library_folder=lib, bom_config="1")
    pad_parts = {r.part_no for r in padded.rows}
    assert padded.method and padded.method.startswith("table_")
    assert "89100-1" in pad_parts
    assert "89101-1" in pad_parts
    assert not any("904226" in p or "904230" in p or "904231" in p or "904245" in p for p in pad_parts)
    assert "P904225-1" not in pad_parts
    assert "904225-1" not in pad_parts


def test_qty_over_20_is_junk_unless_glued_item_qty():
    """99 is OCR junk; 7 on a rail is dimension bleed; BB2/AX2 glued qty 2 stays."""
    huge = parse_ocr_row_strip("99 A 100177-2 PLATE")
    assert huge is not None
    assert huge["item"] == "A"
    assert huge["qty"] != 99
    assert huge["qty"] <= 20
    bleed = parse_ocr_row_strip("7 S 100200-1 RAIL, HORIZONTAL")
    assert bleed["qty"] == 1
    bb = parse_ocr_row_strip("BB2 102727-4 TUBE, ROUND")
    assert bb["item"] == "BB" and bb["qty"] == 2 and bb["part_no"] == _BB_PART
    ax = parse_ocr_row_strip("AX2 1102726-1 HOOK")
    assert ax["item"] == "AX" and ax["qty"] == 2
    lines = harvest_material_list_lines(
        "LIST OF MATERIAL\nQTY ITEM PART NO. DESCRIPTION\n99 A 100177-2 PLATE\n"
        "2 BB 102727-4 TUBE, ROUND\n"
    )
    by_item = {r.item: r for r in lines.rows}
    if "A" in by_item:
        assert by_item["A"].qty != 99
        assert by_item["A"].qty <= 20
    assert by_item["BB"].qty == 2


def test_time_ten_set_layout_fixtures_do_not_regress():
    """Synthetic 10-weldment layouts. Do not claim live 10-set passed."""
    items = time_item_letters(through="BC")
    assert len(items) == 51
    assert "I" not in items and "O" not in items
    assert "AI" not in items and "AO" not in items
    assert items[items.index("Z") + 1] == "AA"
    assert items[-3:] == ["BA", "BB", "BC"]

    dash = """
LIST OF MATERIAL
-2 | -1 | ITEM | PART NO. | DESCRIPTION
1 | - | A | 16697-1 | TUBE, SHORT
- | 1 | B | 16697-2 | TUBE, LONG
2 | 1 | C | 15864-2 | STIFFENER
"""
    dash1 = parse_material_list_text(dash, bom_config="1")
    assert {r.item for r in dash1.rows} == {"B", "C"}
    assert next(r for r in dash1.rows if r.item == "C").qty == 1
    dash2 = parse_material_list_text(dash, bom_config="2")
    assert {r.item for r in dash2.rows} == {"A", "C"}
    assert next(r for r in dash2.rows if r.item == "C").qty == 2

    tall = parse_material_list_cells(_platform_cell_rows())
    decoy = parse_material_list_cells(
        [
            ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            ["1", "B", "102709-1", "DECOY"],
            ["1", "C", "100585-23", "DECOY"],
            ["1", "D", "102711-1", "CABLE"],
        ]
    )
    best = pick_best_material_list([decoy, tall])
    assert best is tall
    assert len(best.rows) == 51
    bb = next(r for r in best.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert "102709-1" not in {r.part_no for r in best.rows}

    gapped = parse_material_list_cells(_platform_cell_rows(drop={"C", "AA"}))
    joined = " ".join(gapped.notes).lower()
    assert "do not pad" in joined
    assert not any(r.item in {"C", "AA"} for r in gapped.rows)
