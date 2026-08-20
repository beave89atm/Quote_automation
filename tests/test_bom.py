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


# Reconstruct Job 84 / 1004335 Time 32x32 basket: 16 PNs, 25 pcs.
# Includes multi-dash OCR noise, qty-0 letter I, and junk PN 004556-2.
_BASKET_1004335_BOM = """
LIST OF MATERIAL
2 | Q | 1004344-1 | SLAT
2 | P | 1004343-1 | SLAT
1 | O | 15064-1 | TUBE
1 | N | 1004342-1 | RAIL
1 | M | 1004341-1 | RAIL
2 | L | 1004340-1 | RAIL
2 | K | 1004339-1 | RAIL
1 | J | 1004338-1 | BRACE
0 | I | 004556-2 |
2 | H | 1004213-1 | SIDE
2 | G | 1004212-1 | SIDE
1 | F | 1004208-1 | PLATE
2 | E | 1004067-1 | BRACKET
2 | D | 1004337-1 | POST
2 | C | 1004336-1 | POST
1 | B | 1004335-2 | FRAME
| - | - | - | 1 | A |1004335-1 | FRAME
QTY ITEM PART NO. DESCRIPTION
"""

_BASKET_1004335_EXPECTED = {
    ("A", "1004335-1", 1),
    ("B", "1004335-2", 1),
    ("C", "1004336-1", 2),
    ("D", "1004337-1", 2),
    ("E", "1004067-1", 2),
    ("F", "1004208-1", 1),
    ("G", "1004212-1", 2),
    ("H", "1004213-1", 2),
    ("J", "1004338-1", 1),
    ("K", "1004339-1", 2),
    ("L", "1004340-1", 2),
    ("M", "1004341-1", 1),
    ("N", "1004342-1", 1),
    ("O", "15064-1", 1),
    ("P", "1004343-1", 2),
    ("Q", "1004344-1", 2),
}


def test_time_basket_16_line_25_piece_recovers_from_ocr_noise():
    """Job 84 ground truth: 16 part numbers / 25 pieces; drop I / 004556-2."""
    bases = {
        "1004067",
        "1004208",
        "1004212",
        "1004213",
        "1004335",
        "1004336",
        "1004337",
        "1004338",
        "1004339",
        "1004340",
        "1004341",
        "1004342",
        "15064",
    }
    # Folder dash -1 must not discard the rest of a single-qty Time table.
    bom = parse_time_style_bom_texts(
        [_BASKET_1004335_BOM],
        bases,
        bom_config="1",
        primary_base="1004335",
        source="native_time",
    )
    got = {(r.item, r.part_no, r.qty) for r in bom.rows if r.item}
    assert got == _BASKET_1004335_EXPECTED
    assert bom.part_number_count == 16
    assert bom.piece_count == 25
    assert all(r.part_no != "004556-2" for r in bom.rows)
    assert all(r.item != "I" for r in bom.rows)
    assert all(int(r.qty) > 0 for r in bom.rows)

    via_extract = extract_bom(text=_BASKET_1004335_BOM, bom_config="1")
    assert via_extract.part_number_count == 16
    assert via_extract.piece_count == 25
    assert via_extract.method and via_extract.method.startswith("native_time")


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
    )
    parts = {r.part_no for r in bom.rows}
    assert "1004212-1" in parts
    assert "1004213-1" in parts
    assert "1004336-1" in parts
    assert "004556-2" not in parts
    assert any("incomplete vs library" in n for n in bom.notes)
    assert any(r.source == "library_child" and r.qty == 1 for r in bom.rows)


def test_fitup_piece_count_follows_time_bom_25(tmp_path: Path):
    """Fit-up part_count uses recovered BOM piece count (25), not a short OCR tally."""
    import fitz

    from quote_core.weld.takeoff import estimate_fitup_drivers

    pdf = tmp_path / "1004335-1.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), _BASKET_1004335_BOM)
    doc.save(str(pdf))
    doc.close()

    drivers = estimate_fitup_drivers({}, [], pdf_path=pdf, bom_config="1")
    assert drivers["part_count"] == 25
    assert drivers["piece_count"] == 25
    assert any("25 pieces" in n and "16 part numbers" in n for n in drivers["notes"])


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
