"""Bitmap LIST OF MATERIAL: segment the grid, OCR each row — not a page dump.

No customer PDF. The 51-row image is a drawn fixture (Time 102728-1 shape).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from quote_core.bom import BomResult, extract_bom
from quote_core.bom_table import (
    harvest_material_list_lines,
    parse_ocr_row_strip,
    pick_best_material_list,
    time_item_letters,
)
from quote_core.bom_table_image import (
    TABLE_CROP_FILENAME,
    extract_bom_from_table_image,
    extract_bom_from_table_images,
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


def _live_page1_strips() -> list[str]:
    """a49dcad live five + older cec69a0 strips + the rest of A…BC."""
    lines = [
        "TEM | PART NO. | DESCRIPTION",
        "7 A 00177-2 PLATE",
        "F 432650 RAIL, HORIZONTAL CENTER BACK",
        "H 102727-4 TUBE, ROUND",
        "M 464460 RAIL, HORIZONTAL FRONT OUTER",
        "7 P 100350-1 TUBE, GRATING SUPPORT MIDDLE",
        "BBD 02727-4 TUBE, ROUND",
        "AA 460330 CAP, VERTICAL RAIL BOTTOM",
        "Z 460320 ICAP, VERTICAL RAIL TOP",
    ]
    taken = {"A", "F", "M", "P", "AA", "Z", "BB"}
    for i, item in enumerate(_platform_items()):
        if item in taken:
            continue
        if item == "AX":
            lines.append("AX 1102726-1 HOOK pO")
        elif item == "H":
            lines.append("H 102840-1 COMPONENT H")
        else:
            lines.append(f"{item} 1028{i:02d}-1 COMPONENT {item}")
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

    aa = parse_ocr_row_strip("AA 460330 CAP, VERTICAL RAIL BOTTOM")
    assert aa["item"] == "AA" and aa["part_no"] == "460330" and aa["qty"] == 1
    assert "VERTICAL RAIL BOTTOM" in aa["description"].upper()

    z = parse_ocr_row_strip("Z 460320 ICAP, VERTICAL RAIL TOP")
    assert z["item"] == "Z" and z["part_no"] == "460320" and z["qty"] == 1

    ax = parse_ocr_row_strip("AX 1102726-1 HOOK pO")
    assert ax["item"] == "AX"
    assert ax["part_no"] == "102726-1"
    assert ax["part_no"] != "1102726-1"

    plate = parse_ocr_row_strip("7 A 00177-2 PLATE")
    assert plate["item"] == "A" and plate["part_no"] == "100177-2"
    assert plate["qty"] == 1

    mid = parse_ocr_row_strip("7 P 100350-1 TUBE, GRATING SUPPORT MIDDLE")
    assert mid["item"] == "P" and mid["part_no"] == "100350-1" and mid["qty"] == 1

    assert parse_ocr_row_strip("TEM | PART NO. | DESCRIPTION") is None


def test_exact_live_strips_harvest_51ish_and_bb():
    """Required fixture: exact live strips → 51-ish rows, BB = 2 × 102727-4."""
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
    assert len(bom.rows) >= 48, [f"{r.item}:{r.part_no}" for r in bom.rows]
    assert len(bom.rows) <= 51
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert "TUBE" in (bb.description or "").upper()
    parts = {r.part_no for r in bom.rows}
    assert "102709-1" not in parts
    assert "100585-23" not in parts
    assert "102711-1" not in parts
    assert "1102726-1" not in parts
    by_item = {r.item: r for r in bom.rows}
    assert by_item["AA"].part_no == "460330"
    assert by_item["Z"].part_no == "460320"
    assert by_item["A"].part_no == "100177-2"
    assert by_item["A"].qty == 1
    assert by_item["P"].qty == 1
    assert by_item["F"].part_no == "432650"
    if "H" in by_item:
        assert by_item["H"].part_no != _BB_PART

    harvested = harvest_material_list_lines("\n".join(strips))
    assert len(harvested.rows) >= 48
    hbb = next(r for r in harvested.rows if r.item == "BB")
    assert hbb.qty == 2 and hbb.part_no == _BB_PART


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
