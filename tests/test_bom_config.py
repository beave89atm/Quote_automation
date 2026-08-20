"""Tests for BOM config / dash selection and multi-qty Time BOM rows."""

from quote_core.bom import (
    _parse_multi_qty_time_hits,
    merge_time_bom_results,
    parse_time_style_bom_texts,
    texts_have_multi_qty_headers,
)
from quote_core.bom_config import normalize_bom_config, resolve_bom_config

# Same 16 PNs as the 1004335 weldment list (I / 004556-2 dropped).
# -1 column sums to 28; -2 column sums to 24. Quoting -1 must not use -2 qtys.
_DASH_QTY_16_PN = """
LIST OF MATERIAL
-2 | -1 | ITEM | PART NO. | DESCRIPTION
2 | 1 | A |1004336-1 | FRAME
1 | 1 | B |1004336-2 | FRAME
2 | 4 | C |1004337-1 | POST
1 | 1 | D |1004337-2 | POST
2 | 2 | E |1004067-1 | BRACKET
1 | 1 | F |1004208-1 | PLATE
1 | 1 | G |1004338-1 | BRACE
1 | 1 | H |1004339-1 | BRACE
0 | 0 | I |004556-2 |
2 | 4 | J |1004340-1 | RAIL
1 | 1 | K |1004212-1 | SIDE
1 | 1 | L |1004213-1 | SIDE
1 | 1 | M |1004341-1 | RAIL
2 | 4 | N |1004342-1 | RAIL
2 | 2 | P |1004343-1 | SLAT
1 | 1 | Q |15064-1 | TUBE
2 | 2 | R |1004344-1 | SLAT
77 | F |1004208-1 | OCR length junk
"""

_DASH_QTY_16_PN_NO_HEADER = """
LIST OF MATERIAL
2 | 1 | A |1004336-1 | FRAME
1 | 1 | B |1004336-2 | FRAME
2 | 4 | C |1004337-1 | POST
1 | 1 | D |1004337-2 | POST
2 | 2 | E |1004067-1 | BRACKET
1 | 1 | F |1004208-1 | PLATE
1 | 1 | G |1004338-1 | BRACE
1 | 1 | H |1004339-1 | BRACE
0 | 0 | I |004556-2 |
2 | 4 | J |1004340-1 | RAIL
1 | 1 | K |1004212-1 | SIDE
1 | 1 | L |1004213-1 | SIDE
1 | 1 | M |1004341-1 | RAIL
2 | 4 | N |1004342-1 | RAIL
2 | 2 | P |1004343-1 | SLAT
1 | 1 | Q |15064-1 | TUBE
2 | 2 | R |1004344-1 | SLAT
"""

_DASH16_BASES = {
    "1004067",
    "1004208",
    "1004212",
    "1004213",
    "1004336",
    "1004337",
    "1004338",
    "1004339",
    "1004340",
    "1004341",
    "1004342",
    "1004343",
    "1004344",
    "15064",
    "9998888",  # library stem not on this dash column
}


def test_normalize_bom_config():
    assert normalize_bom_config("-1") == "1"
    assert normalize_bom_config("1") == "1"
    assert normalize_bom_config("28106-1") == "1"
    assert normalize_bom_config("") is None


def test_resolve_from_folder_name():
    cfg = resolve_bom_config(
        title="28106",
        pdf_filename="28106.pdf",
        library_folder=r"C:\drawings\Time\Lower Boom Weldment - 28106-1",
    )
    assert cfg == "1"


def test_bom_config_without_multi_headers_does_not_drop_rows():
    """Folder dash 1004335-1 must not treat a single-qty Time BOM as column -1 only."""
    from quote_core.bom import parse_time_style_bom_texts

    texts = [
        "LIST OF MATERIAL\n"
        "1 | A |1004335-1 |FRAME\n"
        "2 | E |1004067-1 |BRACKET\n"
        "1 | F |1004208-1 |PLATE\n"
        "2 | P |1004343-1 |SLAT\n"
    ]
    bom = parse_time_style_bom_texts(
        texts, bases={"1004335", "1004067", "1004208"}, bom_config="1"
    )
    assert bom.part_number_count == 4
    assert bom.piece_count == 6
    assert any("did not drop other dashes" in n or "single-qty" in n for n in bom.notes)


def test_multi_qty_headers_and_column_filter():
    texts = [
        "[-4 [-3 [-2 [-1 |",
        "| - | - | - | 1 | A |16697-2 |Lower BOOM TUBE 91 1/8 LG.",
        "| - | - | 1 | - | L |16697-1 |Lower Boom TUBE 55 LG.",
        "| 2 | 2 | 2 | 2 | J |15864-2 |STIFFENER, BOOM PIVOT",
        "| 1 | 1 | 1 | 1 | B |26732-1 |CYLINDER MOUNT PLATE",
    ]
    assert texts_have_multi_qty_headers(texts)
    hits = _parse_multi_qty_time_hits(texts, bases={"16697", "15864", "26732"}, bom_config="1")
    by_item = {h["item"]: h for h in hits if int(h["qty"] or 0) > 0}
    assert by_item["A"]["part_no"] == "16697-2"
    assert by_item["A"]["qty"] == 1
    assert "L" not in by_item  # -2 only
    assert by_item["J"]["qty"] == 2
    assert by_item["B"]["part_no"] == "26732-1"


def test_dash_column_16pn_quoting_dash1_does_not_use_dash2_qtys():
    """Same 16 PNs; -1 piece count is 28, -2 is 24. Do not mix columns."""
    dash1 = parse_time_style_bom_texts(
        [_DASH_QTY_16_PN],
        _DASH16_BASES,
        bom_config="1",
        primary_base="1004335",
        source="native_time",
        fill_library_stems=True,
    )
    dash2 = parse_time_style_bom_texts(
        [_DASH_QTY_16_PN],
        _DASH16_BASES,
        bom_config="2",
        primary_base="1004335",
        source="native_time",
        fill_library_stems=True,
    )
    assert "multi_qty" in (dash1.method or "")
    assert "multi_qty" in (dash2.method or "")
    assert dash1.part_number_count == 16
    assert dash2.part_number_count == 16
    assert dash1.piece_count == 28
    assert dash2.piece_count == 24
    by1 = {r.item: r for r in dash1.rows if r.item}
    by2 = {r.item: r for r in dash2.rows if r.item}
    assert by1["C"].qty == 4 and by2["C"].qty == 2
    assert by1["J"].qty == 4 and by2["J"].qty == 2
    assert by1["N"].qty == 4 and by2["N"].qty == 2
    assert by1["F"].qty == 1
    assert all(r.item != "I" for r in dash1.rows)
    assert all(r.part_no != "004556-2" for r in dash1.rows)
    assert all(r.source != "library_child" for r in dash1.rows)
    assert all(r.part_no != "9998888-1" for r in dash1.rows)
    assert dash1.piece_count != dash2.piece_count


def test_dash_columns_without_headers_still_select_quoted_column():
    """Folder dash is not 'drop unless headers' — use the matching qty column."""
    bom = parse_time_style_bom_texts(
        [_DASH_QTY_16_PN_NO_HEADER],
        _DASH16_BASES,
        bom_config="1",
        source="native_time",
    )
    assert "multi_qty" in (bom.method or "")
    assert bom.piece_count == 28
    by_item = {r.item: r for r in bom.rows if r.item}
    assert by_item["C"].qty == 4
    assert by_item["F"].qty == 1


def test_sparse_dash_column_does_not_invent_library_child_bom():
    """Qty 0 in the quoted column stays dropped; do not qty-1 fill that stem."""
    text = """
LIST OF MATERIAL
-2 | -1 | ITEM | PART NO.
1 | 1 | A |16697-2 | TUBE
1 | 0 | L |9998888-1 | OTHER DASH ONLY
2 | 2 | J |15864-2 | STIFFENER
1 | 1 | B |26732-1 | PLATE
"""
    bom = parse_time_style_bom_texts(
        [text],
        {"16697", "9998888", "15864", "26732", "21690"},
        bom_config="1",
        fill_library_stems=True,
        source="native_time",
    )
    parts = {r.part_no for r in bom.rows}
    assert "16697-2" in parts
    assert "9998888-1" not in parts
    assert all(r.source != "library_child" for r in bom.rows)
    assert bom.piece_count == 4


def test_merge_does_not_mix_dash_column_with_single_qty():
    """Single-qty OCR (F×77 / extra rows) must not override a dash-column BOM."""
    multi = parse_time_style_bom_texts(
        [_DASH_QTY_16_PN], _DASH16_BASES, bom_config="1", source="ocr_time"
    )
    mixed = parse_time_style_bom_texts(
        [
            "LIST OF MATERIAL\n"
            "77 | F |1004208-1 | PLATE\n"
            "8 | C |1004337-1 | POST\n"
            "1 | S |21690-1 | EXTRA\n"
        ],
        _DASH16_BASES | {"21690"},
        source="ocr_time",
    )
    merged = merge_time_bom_results(multi, mixed)
    by_item = {r.item: r for r in merged.rows if r.item}
    assert merged.piece_count == 28
    assert by_item["F"].qty == 1
    assert by_item["C"].qty == 4
    assert "S" not in by_item


def test_two_qty_hits_use_matching_column():
    texts = [
        "-2 | -1 | ITEM | PART NO.",
        "2 | 4 | C |1004337-1 | POST",
        "1 | 0 | L |16697-1 | OTHER DASH",
    ]
    assert texts_have_multi_qty_headers(texts)
    hits1 = _parse_multi_qty_time_hits(texts, bases={"1004337", "16697"}, bom_config="1")
    hits2 = _parse_multi_qty_time_hits(texts, bases={"1004337", "16697"}, bom_config="2")
    by1 = {h["item"]: h for h in hits1 if int(h["qty"] or 0) > 0}
    by2 = {h["item"]: h for h in hits2 if int(h["qty"] or 0) > 0}
    assert by1["C"]["qty"] == 4
    assert by2["C"]["qty"] == 2
    assert "L" not in by1
    assert by2["L"]["qty"] == 1


def test_28106_dash1_piece_count_if_present():
    """28106-1 BOM: 11 unique PNs, two at qty 2 → 13 pieces."""
    from pathlib import Path

    from quote_core.bom import extract_bom_from_ocr_time_style

    pdf = Path(
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering"
        r"\Customer Drawings\Time\Lower Boom Weldment - 28106-1\28106.pdf"
    )
    if not pdf.exists():
        return
    bom = extract_bom_from_ocr_time_style(
        pdf, library_folder=pdf.parent, bom_config="1"
    )
    parts = {r.part_no for r in bom.rows}
    assert "16697-2" in parts
    assert "16697-1" not in parts and "16697-3" not in parts and "16697-4" not in parts
    assert len(bom.rows) == 11, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    assert bom.piece_count == 13, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    qty2 = sorted(r.part_no for r in bom.rows if r.qty == 2)
    assert qty2 == ["15864-2", "15891-1"], qty2
