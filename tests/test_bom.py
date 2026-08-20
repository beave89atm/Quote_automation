"""BOM extraction tests (native MAC + Time OCR voting)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quote_core.bom import (
    _parse_qty_item_part_hits,
    _vote_bom_rows,
    extract_bom,
    extract_bom_from_ocr_time_style,
    library_part_bases,
    merge_time_bom_results,
    normalize_part_no,
    parse_time_style_bom_texts,
)

_JIB_PDF = Path("data/uploads/30/35145-1 JIB ARM WELDMENT ALL DRAWINGS-DESKTOP-GTEFB1D.pdf")
_JIB_LIB = Path(
    r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\Time\35145-1"
)


def test_normalize_part_ocr_confusions():
    assert normalize_part_no("35121—1") == "35121-1"
    assert normalize_part_no("35i21-1") == "35121-1"
    assert normalize_part_no("351211") == "35121-1"


def test_vote_time_style_ocr_lines():
    bases = {"29754", "35121", "35122", "35144", "42021", "35145"}
    texts = [
        "|2|F|42021-9\n|2|E|29754-3\n|2|D|29754-2\nC|35121-2\n|1|B|35121-1\n2|A 35122-\n",
        "| 1 | G 435144—1\n| 2 | F |42021-¢\n| 2 | E |29754-3\n",
        "2 | A 35122-1\n1 | B |35i21-1\n",
    ]
    hits = _parse_qty_item_part_hits(texts, bases)
    rows = _vote_bom_rows(hits, bases)
    got = {(r.item, r.part_no, r.qty) for r in rows}
    expected = {
        ("A", "35122-1", 2),
        ("B", "35121-1", 1),
        ("C", "35121-2", 1),
        ("D", "29754-2", 2),
        ("E", "29754-3", 2),
        ("F", "42021-9", 2),
        ("G", "35144-1", 1),
    }
    assert got == expected
    assert sum(r.qty for r in rows) == 11


def test_vote_item_letters_beyond_g():
    """Knuckle-style BOMs use H/J/K/L; qty 2 on H and L → 13 pieces."""
    bases = {
        "21683",
        "21679",
        "21682",
        "21681",
        "21680",
        "21688",
        "21684",
        "21685",
        "21687",
        "21686",
        "21689",
    }
    texts = [
        "2 | L |21689-1 HOSE GUARD\n"
        "K |21686-1 ANCHOR, LEVELING CYLINDER\n"
        "J |21687-1 SUPPORT, LEVELING ANCHOR\n"
        "2 | H |21685-1 PLATE, CYLINDER ANCHOR\n"
        "G |21684-1 TUBE, CYLINDER ANCHOR\n"
        "F |21688-1 BOX BRACE, KNUCKLE\n"
        "E |21680-1 KNUCKLE PLATE, UB OUTSIDE\n"
        "D |21681-1 KNUCKLE PLATE, UB INSIDE\n"
        "C |21682-1 KNUCKLE PLATE, LB INSIDE\n"
        "B |21679-1 TUBE, KNUCKLE SUPPORT\n"
        "A |21683-1 KNUCKLE PLATE, LB OUTSIDE\n"
    ]
    hits = _parse_qty_item_part_hits(texts, bases)
    rows = _vote_bom_rows(hits, bases)
    assert len(rows) == 11
    assert sum(r.qty for r in rows) == 13
    by_item = {r.item: r for r in rows}
    assert by_item["H"].qty == 2 and by_item["H"].part_no == "21685-1"
    assert by_item["L"].qty == 2 and by_item["L"].part_no == "21689-1"


def test_library_does_not_snap_to_ambiguous_sibling():
    from quote_core.bom import _correct_part_with_library

    bases = {"21684", "21685", "21686", "21687", "21688"}
    # 21689 is Hamming-1 from both 21684 and 21688 — keep OCR reading.
    assert _correct_part_with_library("21689-1", bases) == "21689-1"


def test_native_mac_bom_still_preferred():
    text = """
WEIGHT:
10.0 lbm
1
2
80341690
CHANNEL
5.0 lbm
2
1
80341691
PLATE
5.0 lbm
"""
    bom = extract_bom(text=text)
    assert bom.method == "pdf_bom_qty"
    assert bom.piece_count == 3
    assert bom.part_number_count == 2


# Live library ``1004335 Weldment.pdf`` OCR (Kyle Job 84). Time skips O.
# I / 004556-2 is OCR garbage. Drawing qty sum without I = 28 (not invented 25).
_WELDMENT_1004335_BOM = """
LIST OF MATERIAL
2 | R | 1004344-1 | SLAT
1 | Q | 15064-1 | TUBE
2 | P | 1004343-1 | SLAT
4 | N | 1004342-1 | RAIL
1 | M | 1004341-1 | RAIL
1 | L | 1004213-1 | SIDE
1 | K | 1004212-1 | SIDE
4 | J | 1004340-1 | RAIL
1 | I | 004556-2 |
1 | H | 1004339-1 | BRACE
1 | G | 1004338-1 | BRACE
1 | F | 1004208-1 | PLATE
2 | E | 1004067-1 | BRACKET
1 | D | 1004337-2 | POST
4 | C | 1004337-1 | POST
1 | B | 1004336-2 | FRAME
1 | A | 1004336-1 | FRAME
QTY ITEM PART NO. DESCRIPTION
"""

# Uploaded job ``1004335.pdf``: first-page OCR cut (A–H + P,R). Loses J–N and Q.
_UPLOAD_1004335_TRUNCATED = """
LIST OF MATERIAL
2 | R | 1004344-1 | SLAT
2 | P | 1004343-1 | SLAT
0 | I | 004556-2 |
1 | H | 1004339-1 | BRACE
1 | G | 1004338-1 | BRACE
1 | F | 1004208-1 | PLATE
2 | E | 1004067-1 | BRACKET
1 | D | 1004337-2 | POST
4 | C | 1004337-1 | POST
1 | B | 1004336-2 | FRAME
1 | A | 1004336-1 | FRAME
QTY ITEM PART NO. DESCRIPTION
"""

_WELDMENT_1004335_EXPECTED = {
    ("A", "1004336-1", 1),
    ("B", "1004336-2", 1),
    ("C", "1004337-1", 4),
    ("D", "1004337-2", 1),
    ("E", "1004067-1", 2),
    ("F", "1004208-1", 1),
    ("G", "1004338-1", 1),
    ("H", "1004339-1", 1),
    ("J", "1004340-1", 4),
    ("K", "1004212-1", 1),
    ("L", "1004213-1", 1),
    ("M", "1004341-1", 1),
    ("N", "1004342-1", 4),
    ("P", "1004343-1", 2),
    ("Q", "15064-1", 1),
    ("R", "1004344-1", 2),
}

_BASKET_BASES = {
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
    "15064",
}


def test_weldment_pdf_drops_i_and_keeps_16_parts():
    """Library weldment OCR: 16 PNs after dropping I/004556-2; drawing qtys sum to 28."""
    bom = parse_time_style_bom_texts(
        [_WELDMENT_1004335_BOM],
        _BASKET_BASES,
        bom_config="1",
        primary_base="1004335",
        source="native_time",
    )
    got = {(r.item, r.part_no, r.qty) for r in bom.rows if r.item}
    assert got == _WELDMENT_1004335_EXPECTED
    assert bom.part_number_count == 16
    assert bom.piece_count == 28
    assert all(r.part_no != "004556-2" for r in bom.rows)
    assert all(r.item != "I" for r in bom.rows)


def test_truncated_upload_plus_weldment_fills_j_through_q():
    """Uploaded 1004335.pdf loses J–N/Q; library weldment supplies those rows."""
    upload = parse_time_style_bom_texts(
        [_UPLOAD_1004335_TRUNCATED],
        _BASKET_BASES,
        bom_config="1",
        primary_base="1004335",
        source="ocr_time",
    )
    assert {r.item for r in upload.rows} == {"A", "B", "C", "D", "E", "F", "G", "H", "P", "R"}
    assert upload.piece_count == 16
    assert all(r.item != "I" for r in upload.rows)

    weldment = parse_time_style_bom_texts(
        [_WELDMENT_1004335_BOM],
        _BASKET_BASES,
        source="ocr_time",
    )
    merged = merge_time_bom_results(upload, weldment)
    got = {(r.item, r.part_no, r.qty) for r in merged.rows if r.item}
    assert got == _WELDMENT_1004335_EXPECTED
    assert merged.part_number_count == 16
    assert merged.piece_count == 28
    by_item = {r.item: r for r in merged.rows}
    assert by_item["J"].part_no == "1004340-1" and by_item["J"].qty == 4
    assert by_item["K"].part_no == "1004212-1" and by_item["K"].qty == 1
    assert by_item["L"].part_no == "1004213-1" and by_item["L"].qty == 1
    assert by_item["M"].part_no == "1004341-1" and by_item["M"].qty == 1
    assert by_item["N"].part_no == "1004342-1" and by_item["N"].qty == 4
    assert by_item["Q"].part_no == "15064-1" and by_item["Q"].qty == 1
    assert any("Filled 6 missing BOM row(s) from library weldment" in n for n in merged.notes)


def test_extract_bom_uses_library_weldment_pdf(tmp_path: Path):
    """extract_bom on a truncated upload must pull J–N/Q from 1004335 Weldment.pdf."""
    import fitz

    lib = tmp_path / "1004335-1 32X32 BASKET"
    lib.mkdir()
    weld = lib / "1004335 Weldment.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 780), _WELDMENT_1004335_BOM)
    doc.save(str(weld))
    doc.close()

    bom = extract_bom(
        text=_UPLOAD_1004335_TRUNCATED,
        library_folder=lib,
        related_pdf_names=["1004335 Weldment.pdf"],
        bom_config="1",
    )
    parts = {r.part_no for r in bom.rows}
    assert "1004340-1" in parts and "15064-1" in parts
    assert "004556-2" not in parts
    assert bom.part_number_count == 16
    assert bom.piece_count == 28


def test_time_second_letter_qty_pattern_drops_i_garbage():
    """Different Time letter/qty mix (9 PNs / 14 pcs) plus qty-0 I junk."""
    text = """
LIST OF MATERIAL
3 | P | 21690-1 | HOSE GUARD
1 | M | 21686-1 | ANCHOR
2 | K | 21687-1 | SUPPORT
0 | I | 004556-2 |
2 | H | 21685-1 | PLATE
1 | F | 21688-1 | BOX BRACE
2 | D | 21681-1 | INSIDE
1 | C | 21682-1 | INSIDE
2 | A | 21683-1 | OUTSIDE
"""
    bom = parse_time_style_bom_texts([text], bases=set(), source="native_time")
    assert bom.part_number_count == 8
    assert bom.piece_count == 14
    assert all(r.item != "I" for r in bom.rows)
    assert all(not str(r.part_no).startswith("004556") for r in bom.rows)
    by_item = {r.item: r for r in bom.rows}
    assert by_item["P"].qty == 3
    assert by_item["A"].qty == 2


def test_library_children_fill_missing_bom_rows(tmp_path: Path):
    """Nested Time packet stems backfill a short PDF BOM at qty 1 + review flag."""
    packet = tmp_path / "1004335-1 32X32 BASKET"
    children = packet / "1004335-1"
    children.mkdir(parents=True)
    for stem in (
        "1004067",
        "1004208",
        "1004212",
        "1004213",
        "1004336",
        "1004337",
        "PL",
        "RD",
    ):
        (children / f"{stem}.pdf").write_bytes(b"%PDF-1.4\n")
    (packet / "1004335.pdf").write_bytes(b"%PDF-1.4\n")

    bases = library_part_bases(packet)
    assert "1004212" in bases and "1004336" in bases
    assert "PL" not in bases and "RD" not in bases

    short = """
LIST OF MATERIAL
1 | A | 1004335-1 | FRAME
1 | B | 1004335-2 | FRAME
2 | E | 1004067-1 | BRACKET
1 | F | 1004208-1 | PLATE
0 | I | 004556-2 |
"""
    bom = parse_time_style_bom_texts(
        [short],
        bases,
        bom_config="1",
        primary_base="1004335",
        source="native_time",
        fill_library_stems=True,
    )
    parts = {r.part_no for r in bom.rows}
    assert "1004212-1" in parts
    assert "1004213-1" in parts
    assert "1004336-1" in parts
    assert "004556-2" not in parts
    assert any("incomplete vs library" in n for n in bom.notes)
    assert any(r.source == "library_child" and r.qty == 1 for r in bom.rows)


def test_fitup_piece_count_follows_kept_bom_qtys(tmp_path: Path):
    """Fit-up uses sum of kept drawing qtys (28), not a truncated 10-pc OCR tally."""
    import fitz

    from quote_core.weld.takeoff import estimate_fitup_drivers

    pdf = tmp_path / "1004335 Weldment.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 780), _WELDMENT_1004335_BOM)
    doc.save(str(pdf))
    doc.close()

    drivers = estimate_fitup_drivers({}, [], pdf_path=pdf, bom_config="1")
    assert drivers["part_count"] == 28
    assert drivers["piece_count"] == 28
    assert any("28 pieces" in n and "16 part numbers" in n for n in drivers["notes"])


@pytest.mark.skipif(not _JIB_PDF.exists(), reason="Job 30 jib arm PDF not present")
def test_jib_arm_ocr_bom_eleven_pieces():
    lib = _JIB_LIB if _JIB_LIB.exists() else None
    bom = extract_bom_from_ocr_time_style(_JIB_PDF, library_folder=lib)
    assert bom.part_number_count == 7
    assert bom.piece_count == 11
    got = {(r.item, r.part_no, r.qty) for r in bom.rows}
    assert got == {
        ("A", "35122-1", 2),
        ("B", "35121-1", 1),
        ("C", "35121-2", 1),
        ("D", "29754-2", 2),
        ("E", "29754-3", 2),
        ("F", "42021-9", 2),
        ("G", "35144-1", 1),
    }
