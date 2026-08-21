"""Bitmap LIST OF MATERIAL: segment the grid, OCR each row — not a page dump.

No customer PDF. The 51-row image is a drawn fixture (Time 102728-1 shape).
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from quote_core.bom import BomResult, extract_bom
from quote_core.bom_table import (
    expected_letters_for_bands,
    harvest_material_list_lines,
    harvest_ocr_row_strips,
    parse_ocr_row_strip,
    pick_best_material_list,
    recover_time_part_no,
    time_item_letters,
    union_sticky_harvest,
)
from tests.test_bom_table import (
    _KYLE_102728_1,
    _assert_kyle_102728_1,
    _assert_kyle_28106_1,
    _kyle_28106_cell_rows,
)
from quote_core.bom_table_image import (
    TABLE_CROP_FILENAME,
    extract_bom_from_table_image,
    extract_bom_from_table_images,
    left_qty_column_bounds,
    segment_table_bands,
)

_THROUGH = "BC"
_BB_PART = "102727-4"
_BB_DESC = "TUBE, ROUND"


def _platform_items() -> list[str]:
    items = time_item_letters(through=_THROUGH)
    assert len(items) == 51
    return items


def _platform_row_texts(*, drop: set[str] | None = None) -> list[str]:
    drop = drop or set()
    lines = []
    for i, item in enumerate(_platform_items()):
        if item in drop:
            continue
        if item == "BB":
            lines.append(f"2 BB {_BB_PART} {_BB_DESC}")
        else:
            lines.append(f"1 {item} 1028{i:02d}-1 COMPONENT {item}")
    return lines


def _draw_lom_table(row_texts: list[str], *, row_h: int = 16) -> Image.Image:
    """Draw a QTY/ITEM/PART grid with real rules so the segmenter can count bands."""
    headers = ["QTY", "ITEM", "PART NO.", "DESCRIPTION"]
    col_ws = (48, 56, 110, 170)
    n = len(row_texts)
    pad = 10
    title_h = 22
    width = pad * 2 + sum(col_ws)
    height = pad + title_h + (n + 1) * row_h + pad
    im = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = None
    x0 = pad
    y0 = pad + title_h
    xs = [x0]
    for w in col_ws:
        xs.append(xs[-1] + w)
    x1 = xs[-1]
    y1 = y0 + (n + 1) * row_h
    draw.text((x0, 4), "LIST OF MATERIAL", fill="black", font=font)
    for i in range(n + 2):
        y = y0 + i * row_h
        draw.line([(x0, y), (x1, y)], fill="black", width=2)
    for x in xs:
        draw.line([(x, y0), (x, y1)], fill="black", width=2)
    cells_rows = [headers]
    for line in row_texts:
        parts = line.split(" ", 3)
        while len(parts) < 4:
            parts.append("")
        cells_rows.append(parts[:4])
    for r, cells in enumerate(cells_rows):
        cy = y0 + r * row_h + 3
        for c, text in enumerate(cells):
            draw.text((xs[c] + 3, cy), str(text), fill="black", font=font)
    return im


def test_segmenter_counts_51_row_grid_and_rejects_short_decoy():
    tall = _draw_lom_table(_platform_row_texts())
    decoy = _draw_lom_table(
        ["1 B 102709-1 DECOY", "1 C 100585-23 DECOY", "1 D 102711-1 CABLE"]
    )
    tall_seg = segment_table_bands(tall)
    decoy_seg = segment_table_bands(decoy)
    assert tall_seg["grid_row_count"] >= 48, tall_seg["grid_row_count"]
    assert tall_seg["grid_row_count"] <= 56, tall_seg["grid_row_count"]
    assert decoy_seg["grid_row_count"] < 10, decoy_seg["grid_row_count"]
    assert decoy_seg["grid_row_count"] >= 3


def test_two_rendered_pages_pick_51_row_table_and_bb():
    """Required fixture: 51-row right-side table + 3-row decoy → BB qty 2 / 102727-4."""
    tall_texts = _platform_row_texts()
    decoy_texts = [
        "1 B 102709-1 DECOY",
        "1 C 100585-23 DECOY",
        "1 D 102711-1 CABLE TUBE",
    ]
    tall = _draw_lom_table(tall_texts)
    decoy = _draw_lom_table(decoy_texts)
    bom = extract_bom_from_table_images(
        [decoy, tall],
        row_texts_by_image=[decoy_texts, tall_texts],
    )
    assert bom.method and bom.method.startswith("table_")
    assert len(bom.rows) == 51, [f"{r.item}:{r.part_no}" for r in bom.rows]
    assert bom.grid_row_count >= 48
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    parts = {r.part_no for r in bom.rows}
    assert "102709-1" not in parts
    assert "100585-23" not in parts
    assert "102711-1" not in parts


def test_tall_unread_grid_rejects_3_row_nested_lom():
    """Page-1 51-band / 0-PN clip must beat 102711-1's 3-row parse."""
    tall = extract_bom_from_table_image(_draw_lom_table(_platform_row_texts()))
    decoy = extract_bom_from_table_image(
        _draw_lom_table(
            ["1 B 102709-1 DECOY", "1 C 100585-23 DECOY", "1 D 102711-1 CABLE"]
        ),
        row_texts=["1 B 102709-1 DECOY", "1 C 100585-23 DECOY", "1 D 102711-1 CABLE"],
    )
    assert tall.grid_row_count >= 48
    assert len(tall.rows) == 0
    assert len(decoy.rows) == 3
    best = pick_best_material_list([decoy, tall])
    assert best is tall
    assert len(best.rows) != 3
    joined = " ".join(best.notes).lower()
    assert "rejected" in joined and "3-row" in joined
    assert not any(r.part_no == "102711-1" for r in best.rows)


def test_extract_bom_sibling_crop_beats_short_pdf_lom(tmp_path: Path):
    """Desktop crop next to the job PDF wins over a nested 3-row LOM page."""
    import fitz

    pdf = tmp_path / "Time 102728- Weldment.pdf"
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text((72, 72), "102711-1 CABLE TUBE")
    page.insert_text((400, 200), "LIST OF MATERIAL", fontsize=10)
    page.insert_text((400, 220), "QTY | ITEM | PART NO. | DESCRIPTION", fontsize=8)
    page.insert_text((400, 236), "1 | B | 102709-1 | DECOY", fontsize=8)
    page.insert_text((400, 252), "1 | C | 100585-23 | DECOY", fontsize=8)
    page.insert_text((400, 268), "1 | D | 102711-1 | CABLE", fontsize=8)
    doc.save(pdf)
    doc.close()

    crop = tmp_path / TABLE_CROP_FILENAME
    _draw_lom_table(_platform_row_texts()).save(crop, "PNG")

    bom = extract_bom(pdf_path=pdf, bom_config="1")
    parts = {r.part_no for r in bom.rows}
    assert "102709-1" not in parts
    assert "100585-23" not in parts
    assert "102711-1" not in parts
    assert bom.grid_row_count >= 48
    joined = " ".join(bom.notes).lower()
    assert "crop" in joined or "grid" in joined
    # Do not invent 51 PNs when the crop cells were not read.
    if len(bom.rows) >= 40:
        bb = next(r for r in bom.rows if r.item == "BB")
        assert bb.qty == 2 and bb.part_no == _BB_PART
    else:
        assert len(bom.rows) < 10
        assert "flag review" in joined or "unread" in joined or "rejected" in joined


def test_left_qty_column_keeps_thin_first_band():
    """791587b hunch: do not drop a 4–8 px QTY column (small digit)."""
    # v-lines after a 5 px qty band, then item / part.
    windows = left_qty_column_bounds([5, 40, 140, 300], 400)
    assert any(b - a <= 12 for a, b in windows)
    assert any(a == 0 and b >= 5 for a, b in windows)
    wide = left_qty_column_bounds([0, 120, 200], 400)
    assert any(b - a <= 50 for a, b in wide)


def test_table_image_cell_texts_match_kyle_102728_1():
    """Product path: cell-delimited QTY|ITEM|PART|DESC, A at the bottom."""
    texts = [
        f"{qty} | {item} | {pn} | {desc}"
        for item, qty, pn, desc in reversed(_KYLE_102728_1)
    ]
    texts.append("QTY | ITEM | PART NO. | DESCRIPTION")
    im = _draw_lom_table(_platform_row_texts())
    bom = extract_bom_from_table_image(im, row_texts=texts, bom_config="-1")
    assert bom.method and bom.method.startswith("table_")
    assert not (bom.method or "").startswith("ocr_time")
    _assert_kyle_102728_1(bom)
    assert bom.piece_count == 97


def test_table_image_cell_texts_match_kyle_28106_1():
    """28106-1: four dash columns, A at the bottom, quote -1 only."""
    cells = _kyle_28106_cell_rows()
    texts = [" | ".join(row) for row in reversed(cells)]
    im = _draw_lom_table(["1 A 16697-2 TUBE"] * 14)
    bom = extract_bom_from_table_image(im, row_texts=texts, bom_config="-1")
    assert bom.method and bom.method.startswith("table_")
    assert not (bom.method or "").startswith("ocr_time")
    _assert_kyle_28106_1(bom)


def _live_page1_strips() -> list[str]:
    """Page-1 clip order: BC at the top, A at the bottom, header below."""
    lines = [
        f"{qty} {item} {pn} {desc}"
        for item, qty, pn, desc in reversed(_KYLE_102728_1)
    ]
    lines.append("QTY | ITEM | PART NO. | DESCRIPTION")
    return lines


def test_live_strips_parse_bbd_aa_z_and_ax():
    bb = parse_ocr_row_strip("BBD 02727-4 TUBE, ROUND")
    assert bb is not None
    assert bb["item"] == "BB"
    assert bb["part_no"] == _BB_PART
    assert bb["qty"] == 2
    assert "TUBE" in bb["description"].upper()
    assert "ROUND" in bb["description"].upper()

    stolen = parse_ocr_row_strip("H 102727-4 TUBE, ROUND")
    assert stolen["item"] == "BB" and stolen["part_no"] == _BB_PART and stolen["qty"] == 2

    bb2 = parse_ocr_row_strip("BB2 02727-4 TUBE, ROUND")
    assert bb2["item"] == "BB" and bb2["part_no"] == _BB_PART and bb2["qty"] == 2
    assert bb2["item"] != "H"

    aa = parse_ocr_row_strip("5 AA 460330 CAP, VERTICAL RAIL BOTTOM")
    assert aa["item"] == "AA" and aa["part_no"] == "460330" and aa["qty"] == 5
    assert "VERTICAL RAIL BOTTOM" in aa["description"].upper()

    z = parse_ocr_row_strip("2 Z 460320 ICAP, VERTICAL RAIL TOP")
    assert z["item"] == "Z" and z["part_no"] == "460320" and z["qty"] == 2

    ax = parse_ocr_row_strip("AX 1102726-1 HOOK pO")
    assert ax["item"] == "AX"
    assert ax["part_no"] == "102726-1"
    assert ax["part_no"] != "1102726-1"

    plate = parse_ocr_row_strip("7 A 00177-2 PLATE")
    assert plate["item"] == "A" and plate["part_no"] == "100177-2"
    assert plate["qty"] != 7 and plate["qty_clear"] is False

    mid = parse_ocr_row_strip("7 P 100350-1 TUBE, GRATING SUPPORT MIDDLE")
    assert mid["item"] == "P" and mid["part_no"] == "100350-1"
    assert mid["qty"] != 7 and mid["qty_clear"] is False

    assert parse_ocr_row_strip("TEM | PART NO. | DESCRIPTION") is None


def test_exact_live_strips_harvest_51ish_and_bb():
    """Kyle 102728-1 grid: 51 PNs, 97 pcs, A=460200, BB=2×102727-4."""
    strips = _live_page1_strips()
    decoy = [
        "LIST OF MATERIAL",
        "QTY | ITEM | PART NO. | DESCRIPTION",
        "1 B 102709-1 DECOY",
        "1 C 100585-23 DECOY",
        "1 D 102711-1 CABLE TUBE",
    ]
    tall = _draw_lom_table(["x"] * 51)
    short = _draw_lom_table(["x"] * 3)
    bom = extract_bom_from_table_images(
        [short, tall],
        row_texts_by_image=[decoy, strips],
    )
    assert bom.method and bom.method.startswith("table_")
    _assert_kyle_102728_1(bom)
    parts = {r.part_no for r in bom.rows}
    assert "102709-1" not in parts
    assert "100585-23" not in parts
    assert "1102726-1" not in parts

    harvested = harvest_material_list_lines("\n".join(strips))
    _assert_kyle_102728_1(harvested)


def test_unread_single_letter_dashed_pn_assigned_from_sequence():
    """Live 1b1302f miss: keep dashed PNs when A–Y letters are unread."""
    seq = time_item_letters(through="BC")
    known = {"A", "F", "H", "M", "S", "Z", "AA", "BB"}
    # Top→bottom = BC…A (header at bottom).
    lines = ["TEM | PART NO. | DESCRIPTION"]
    for item in reversed(seq):
        if item == "BB":
            lines.append("BBD 02727-4 TUBE, ROUND")
        elif item in known:
            lines.append(f"{item} 1028{seq.index(item):02d}-1 DESC")
        else:
            lines.append(f"1028{seq.index(item):02d}-1 SUPPORT")
    bom = harvest_ocr_row_strips(lines)
    items = {r.item for r in bom.rows}
    for letter in "BCDEGJKLNPQRTUVWXY":
        assert letter in items, letter
    for tok in ("AJ", "AU", "BA"):
        assert tok in items, tok
    assert "AI" not in items and "AO" not in items
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert len(bom.rows) >= 48


def test_unread_bare_and_mangled_pns_kept_and_sequenced():
    """0449bfa hole: keep Time-like PNs with broken dashes / no dash / extra 1."""
    seq = time_item_letters(through="BC")
    known = {"A", "C", "F", "H", "M", "S", "Z", "AA"}
    lines = ["TEM | PART NO. | DESCRIPTION"]
    for item in reversed(seq):
        i = seq.index(item)
        if item == "BB":
            lines.append("BBD 02727-4 TUBE, ROUND")
        elif item == "B":
            lines.append("1100373-2 PLATE")
        elif item == "AR":
            lines.append("133688-10 TUBE")
        elif item == "AX":
            lines.append("AX2 1102726-1 HOOK")
        elif item == "D":
            lines.append("1028 03-1 SUPPORT")
        elif item == "E":
            lines.append("432650 RAIL")
        elif item == "G":
            lines.append("94560 PLATE")
        elif item == "J":
            lines.append("460300 CAP")
        elif item == "AJ":
            lines.append("1O28 27-1 ANGLE")
        elif item == "AU":
            lines.append("1028 44-1 CLIP")
        elif item == "AW":
            # Keep AU's 102844-1 unique (even-i default would also emit 1028 44-1).
            lines.append("461044 RAIL")
        elif item == "BA":
            lines.append("1028 48-1 BASE")
        elif item in known:
            lines.append(f"{item} 1028{i:02d}-1 DESC")
        elif i % 2 == 0:
            lines.append(f"1028 {i:02d}-1 SUPPORT")
        else:
            lines.append(f"46{i:04d} RAIL")
    bom = harvest_ocr_row_strips(lines)
    items = {r.item for r in bom.rows}
    by_item = {r.item: r for r in bom.rows}
    for letter in "BCDEGJKLNPQRTUVWXY":
        assert letter in items, letter
    for tok in ("AJ", "AU", "BA"):
        assert tok in items, tok
    assert "AI" not in items and "AO" not in items
    bb = by_item["BB"]
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert by_item["B"].part_no == "100373-2"
    assert by_item["AR"].part_no == "33688-10"
    assert by_item["AX"].qty == 2
    assert by_item["AX"].part_no == "102726-1"
    assert by_item["E"].part_no == "432650"
    assert by_item["G"].part_no == "94560"
    assert by_item["J"].part_no == "460300"
    assert by_item["D"].part_no == "102803-1"
    assert by_item["AJ"].part_no == "102827-1"
    assert by_item["AU"].part_no == "102844-1"
    assert len(bom.rows) >= 48
    invented = {r.part_no for r in bom.rows} - {
        "100373-2",
        "33688-10",
        "102726-1",
        _BB_PART,
        "432650",
        "94560",
        "460300",
        "102803-1",
        "102827-1",
        "102844-1",
        "102848-1",
    }
    for part in invented:
        assert re.search(r"\d{5,7}(?:-\d+)?", part), part
        assert "99999" not in part


def test_parse_keeps_unread_time_like_and_does_not_invent():
    bare = parse_ocr_row_strip("432650 RAIL, HORIZONTAL")
    assert bare is not None and bare["part_no"] == "432650" and bare["item"] is None
    spaced = parse_ocr_row_strip("1028 01-1 SUPPORT")
    assert spaced is not None and spaced["part_no"] == "102801-1"
    extra_b = parse_ocr_row_strip("1100373-2 PLATE")
    assert extra_b["part_no"] == "100373-2"
    extra_ar = parse_ocr_row_strip("133688-10 TUBE")
    assert extra_ar["part_no"] == "33688-10"
    ax2 = parse_ocr_row_strip("AX2 1102726-1 HOOK")
    assert ax2["item"] == "AX" and ax2["qty"] == 2 and ax2["part_no"] == "102726-1"
    assert parse_ocr_row_strip("SECTION B-B SCALE") is None
    assert parse_ocr_row_strip("7.50 x 3.00 PLATE") is None
    assert parse_ocr_row_strip("TEM | PART NO. | DESCRIPTION") is None


def test_skipped_band_notes_include_itemish_and_raw_strip():
    bom = harvest_ocr_row_strips(
        [
            "SECTION B-B",
            "BBD 02727-4 TUBE, ROUND",
            "no part here at all",
        ]
    )
    skipped = [n for n in bom.notes if n.startswith("Skipped band")]
    assert any("item-ish=SECTION" in n and "raw=SECTION B-B" in n for n in skipped)
    assert any("item-ish=no" in n and "raw=no part here at all" in n for n in skipped)
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def test_leading_1_only_on_5digit_0_stem():
    assert recover_time_part_no("00177-2") == "100177-2"
    assert recover_time_part_no("02727-4") == "102727-4"
    assert recover_time_part_no("1100373-2") == "100373-2"
    assert recover_time_part_no("133688-10") == "33688-10"
    assert recover_time_part_no("33688-10") == "33688-10"
    assert recover_time_part_no("432670") == "432670"
    assert recover_time_part_no("1432670") == "432670"
    assert recover_time_part_no("100177-2") == "100177-2"
    assert recover_time_part_no("102727-4") == "102727-4"


def test_qty_7_on_s_is_dimension_bleed():
    row = parse_ocr_row_strip("7 S 100200-1 RAIL, HORIZONTAL")
    assert row["item"] == "S" and row["qty"] != 7 and row["qty_clear"] is False
    av = parse_ocr_row_strip("7 AV 100210-1 TUBE")
    assert av["item"] == "AV" and av["qty"] != 7 and av["qty_clear"] is False


def test_qty_7_jsalav_forced_to_1_bb_stays_2():
    """b1487d7 live: J/S/AL/AV landed at 7; qty 7 is bleed unless glued BB2/BBD."""
    lines = [
        "7 J 100340-1 SUPPORT",
        "7 S 100200-1 RAIL",
        "7 AL 100220-1 TUBE",
        "7 AV 100210-1 TUBE",
        "BBD 02727-4 TUBE, ROUND",
        "AX2 1102726-1 HOOK",
    ]
    bom = harvest_ocr_row_strips(lines)
    by_item = {r.item: r for r in bom.rows}
    for tok in ("J", "S", "AL", "AV"):
        assert by_item[tok].qty != 7, tok
        assert by_item[tok].qty <= 1, tok
    assert by_item["BB"].qty == 2 and by_item["BB"].part_no == _BB_PART
    assert by_item["AX"].qty == 2

    overwritten = harvest_material_list_lines(
        "LIST OF MATERIAL\nQTY ITEM PART NO. DESCRIPTION\n"
        + "\n".join(lines)
    )
    by2 = {r.item: r for r in overwritten.rows}
    for tok in ("J", "S", "AL", "AV"):
        assert by2[tok].qty != 7, tok
        assert by2[tok].qty <= 1, tok
    assert by2["BB"].qty == 2


def test_empty_p_to_y_holes_are_dumped_not_invented():
    """b1487d7: P–Y / AJ / BA were empty sequence holes, not Skipped-band text."""
    seq = time_item_letters(through="BC")
    holes = {"P", "Q", "R", "T", "U", "V", "W", "X", "Y", "AJ", "BA"}
    lines = []
    for item in reversed(seq):
        if item in holes:
            lines.append("")
        elif item == "BB":
            lines.append("BBD 02727-4 TUBE, ROUND")
        else:
            lines.append(f"{item} 1028{seq.index(item):02d}-1 DESC")
    lines.append("TEM | PART NO. | DESCRIPTION")
    expected = expected_letters_for_bands(len(lines), bottom_is_a=True, header_idxs={51})
    assert expected[0] == "BC"
    assert expected[50] == "A"
    assert expected[51] is None
    bom = harvest_ocr_row_strips(lines)
    items = {r.item for r in bom.rows}
    for tok in holes:
        assert tok not in items, tok
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    hole_notes = [n for n in bom.notes if n.startswith("Hole band")]
    dumped = {n.split("letter=", 1)[1].split(" ", 1)[0] for n in hole_notes}
    for tok in holes:
        assert tok in dumped, tok
        assert any(
            f"letter={tok} raw=(empty)" in n for n in hole_notes
        ), tok
    assert not any("102999" in (r.part_no or "") for r in bom.rows)

    # Digits in a hole strip are recovered; empty stays empty.
    filled = list(lines)
    p_idx = next(i for i, letter in enumerate(expected) if letter == "P")
    filled[p_idx] = "1028 13-1 SUPPORT"
    recovered = harvest_ocr_row_strips(filled)
    by_item = {r.item: r for r in recovered.rows}
    assert by_item["P"].part_no == "102813-1"
    assert "Q" not in by_item


def test_sticky_first_harvest_union_keeps_tail_and_p_y():
    """6c4fc51 lost Z/AY/AZ/BC; union first harvest with empty-band recoveries."""
    first_lines = [
        "BC 102727-5 CAP",
        "BBD 02727-4 TUBE, ROUND",
        "BA",
        "AZ 102727-2 TUBE",
        "AY 102727-1 TUBE",
        "AX 102726-1 HOOK",
        "Z 460320 ICAP, VERTICAL RAIL TOP",
        "S 33688-9 EXPANDED METAL PLATE",
        "M 94560 GATE",
        "A 100177-2 PLATE",
    ]
    first = harvest_ocr_row_strips(first_lines)
    by_first = {r.item: r for r in first.rows}
    assert by_first["Z"].part_no == "460320"
    assert by_first["AY"].part_no == "102727-1"
    assert by_first["AZ"].part_no == "102727-2"
    assert by_first["BC"].part_no == "102727-5"
    assert by_first["BB"].qty == 2 and by_first["BB"].part_no == _BB_PART

    # Retry harvest dropped the tail and cross-assigned neighbor PNs onto holes.
    retry_lines = [
        "P 33688-9 FXPANDED METAL PLATE",  # neighbor S PN — must not win
        "Q 102840-1 SUPPORT",
        "R 102841-1 SUPPORT",
        "U 102842-1 SUPPORT",
        "V 102843-1 RAIL",
        "X 102844-1 RAIL",
        "Y 102845-1 RAIL",
        "AQ 33688-9 FXPANDED METAL PLATE",
        "S 94560 GATE",
        "BBD 02727-4 TUBE, ROUND",
    ]
    retry = harvest_ocr_row_strips(retry_lines)
    united = union_sticky_harvest(first, retry)
    parts = {r.part_no for r in united.rows}
    by_item = {r.item: r for r in united.rows}
    assert "460320" in parts
    assert "102727-1" in parts and "102727-2" in parts and "102727-5" in parts
    bb = next(r for r in united.rows if r.part_no == _BB_PART)
    assert bb.qty == 2 and bb.item == "BB"
    assert "33688-9" in parts
    assert "94560" in parts
    for pn in ("102840-1", "102841-1", "102842-1", "102843-1", "102844-1", "102845-1"):
        assert pn in parts, pn
    assert sum(1 for r in united.rows if r.part_no == "33688-9") == 1
    assert "AI" not in by_item and "AO" not in by_item
    assert not any(r.qty == 7 for r in united.rows)


def test_do_not_reletter_or_copy_neighbor_pn_onto_hole():
    z_line = "Z 460320 ICAP, VERTICAL RAIL TOP"
    hole = ""
    s_line = "S 33688-9 EXPANDED METAL PLATE"
    bb = "BBD 02727-4 TUBE, ROUND"
    bom = harvest_ocr_row_strips([z_line, hole, s_line, bb])
    by_item = {r.item: r for r in bom.rows}
    assert by_item["Z"].part_no == "460320"
    assert by_item["S"].part_no == "33688-9"
    assert by_item["BB"].qty == 2
    # Empty hole must not inherit Z or S.
    hole_notes = [n for n in bom.notes if n.startswith("Hole band")]
    assert any("raw=(empty)" in n for n in hole_notes)
    assert list(by_item).count("Z") == 1

    # Item token is sticky — do not sequence-reletter Z.
    sticky = parse_ocr_row_strip(z_line)
    assert sticky["item"] == "Z"
    assigned = harvest_ocr_row_strips([z_line, "102899-1 SUPPORT", bb])
    assert next(r for r in assigned.rows if r.part_no == "460320").item == "Z"


_LIVE_B1487D7_PNS = [
    "432670", "460200", "460270", "100373-2", "100351-1", "432650", "102733-1",
    "432640", "460230", "460340", "432660", "460300", "464100", "94560",
    "460320", "460330", "464450", "100177-2", "100351-2", "436010", "464460",
    "100350-2", "100373-1", "100351-3", "100738-1", "33688-6", "33688-7",
    "33688-8", "33688-9", "33688-10", "100267-1", "100366-27", "102711-1",
    "102712-1", "102725-1", "102726-1", "102727-1", "102727-2", "102727-4",
    "102727-5",
]
_LIVE_6C4FC51_PNS = [
    "460320", "460270", "460280", "432580", "460230", "432650", "100373-2",
    "100351-1", "460300", "432640", "100362-1", "94560", "460340", "100350-1",
    "464100", "432660", "33688-9", "298540", "432710", "432670", "100363-1",
    "460330", "464450", "100177-2", "464440", "436010", "464460", "100350-2",
    "100373-1", "100351-3", "100738-1", "33688-6", "33688-7", "33688-8",
    "33688-10", "100267-1", "100366-27", "102711-1", "102712-1", "102725-1",
    "102726-1", "102727-4",
]


def test_union_live_pn_lists_keeps_tail_and_retry_only():
    """Success bar: unique PNs ≥ union of the two live harvests; BB qty 2."""
    first = harvest_ocr_row_strips(
        [
            f"{pn} {'GATE' if pn == '94560' else 'COMPONENT'}"
            for pn in _LIVE_B1487D7_PNS
        ]
        + ["BBD 02727-4 TUBE, ROUND"]
    )
    extra = harvest_ocr_row_strips(
        [
            f"{pn} {'GATE' if pn == '94560' else 'COMPONENT'}"
            for pn in _LIVE_6C4FC51_PNS
        ]
        + ["BBD 02727-4 TUBE, ROUND"]
    )
    united = union_sticky_harvest(first, extra)
    parts = {r.part_no for r in united.rows}
    want = set(_LIVE_B1487D7_PNS) | set(_LIVE_6C4FC51_PNS)
    missing = sorted(want - parts)
    assert not missing, missing
    assert len(parts) >= len(want)
    bb = next(r for r in united.rows if r.part_no == _BB_PART)
    assert bb.qty == 2 and bb.item == "BB"
    assert "102727-1" in parts and "102727-2" in parts and "102727-5" in parts
    assert not any(r.item in {"AI", "AO"} for r in united.rows)
    assert not any(r.qty == 7 for r in united.rows)


def test_102727_siblings_are_not_swallowed_by_bb():
    """BB is 102727-4 only. AY/AZ/BC stay in the unique PN set."""
    bom = harvest_ocr_row_strips(
        [
            "AY 102727-1 TUBE, ROUND",
            "AZ 102727-2 TUBE",
            "BBD 02727-4 TUBE, ROUND",
            "BC 102727-5 CAP",
        ]
    )
    parts = {r.part_no for r in bom.rows}
    assert "102727-1" in parts
    assert "102727-2" in parts
    assert "102727-5" in parts
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert next(r for r in bom.rows if r.part_no == "102727-1").item != "BB"


def test_letter_collision_does_not_drop_a_pn():
    bom = harvest_ocr_row_strips(
        ["A 460200 RAIL", "A 460280 RAIL", "BBD 02727-4 TUBE, ROUND"]
    )
    parts = {r.part_no for r in bom.rows}
    assert "460200" in parts and "460280" in parts
    assert _BB_PART in parts
    assert next(r for r in bom.rows if r.part_no == _BB_PART).qty == 2


def test_live_dropped_strips_recover_time_pns():
    aq = parse_ocr_row_strip('AQ" [3688-9 JEXPANDED METAL PLATE')
    assert aq is not None and aq["part_no"] == "33688-9"
    assert parse_ocr_row_strip("A [25009-2 TUBE")["part_no"] == "25009-2"
    assert parse_ocr_row_strip("B [32259-1 PLATE")["part_no"] == "32259-1"
    gate = parse_ocr_row_strip("o4560 |GATE, FABRICATION")
    assert gate is not None and gate["part_no"] == "94560"
    bom = harvest_ocr_row_strips(
        [
            'AQ" [3688-9 JEXPANDED METAL PLATE',
            "o4560 |GATE, FABRICATION",
            "BBD 02727-4 TUBE, ROUND",
        ]
    )
    parts = {r.part_no for r in bom.rows}
    assert "33688-9" in parts and "94560" in parts and _BB_PART in parts


def test_pick_best_does_not_invent_rows_for_unread_tall_grid():
    unread = BomResult(
        rows=[],
        method="table_material_list_image",
        notes=["Tall grid unread"],
        grid_row_count=51,
    )
    short = extract_bom_from_table_image(
        _draw_lom_table(["1 B 102709-1 DECOY", "1 C 100585-23 DECOY", "1 D 102711-1 X"]),
        row_texts=["1 B 102709-1 DECOY", "1 C 100585-23 DECOY", "1 D 102711-1 X"],
    )
    best = pick_best_material_list([short, unread])
    assert best is unread
    assert best.rows == []
    assert best.grid_row_count == 51
