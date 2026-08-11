"""BOM extraction tests (native MAC + Time OCR voting)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quote_core.bom import (
    _parse_qty_item_part_hits,
    _vote_bom_rows,
    extract_bom,
    extract_bom_from_native_time_multiconfig,
    extract_bom_from_ocr_time_style,
    normalize_part_no,
)

_TIME_1004715_TEXT = """
ITEM NO.
PART NUMBER
DESCRIPTION
1004715-1
1004715-2
8
1004713-2
LOWER BOOM TUBE, TURRET END
-
1
7
1004713-1
LOWER BOOM TUBE, TURRET END
1
-
6
1004719-1
LOWER BOOM STIFFENER
-
2
5
1004711-1
STIFFENER, CYLINDER MOUNT
1
1
4
21822-1
HOSE GUIDE
1
1
3
1004712-1
PIVOT DOUBLER
2
2
2
13349-3
CYLINDER MOUNT PLATE
2
2
1
25060-5
TUBE, PIVOT
1
1
SIZE
MATERIAL DESCRIPTION
"""

_TIME_1004715_PDF = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/1004715_1b49.pdf"
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


def test_native_time_multiconfig_dash2_seven_rows():
    bom = extract_bom_from_native_time_multiconfig(
        text=_TIME_1004715_TEXT, bom_config="2"
    )
    assert bom.method == "native_time_multi_qty"
    assert bom.part_number_count == 7
    assert bom.piece_count == 10
    by_pn = {r.part_no: r for r in bom.rows}
    assert "1004713-1" not in by_pn
    assert by_pn["1004713-2"].qty == 1
    assert by_pn["1004719-1"].qty == 2
    assert by_pn["25060-5"].qty == 1
    assert by_pn["25060-5"].description.startswith("TUBE")


def test_native_time_multiconfig_dash1_excludes_dash2_tube():
    bom = extract_bom_from_native_time_multiconfig(
        text=_TIME_1004715_TEXT, bom_config="1"
    )
    assert bom.method == "native_time_multi_qty"
    by_pn = {r.part_no: r.qty for r in bom.rows}
    assert "1004713-2" not in by_pn
    assert by_pn["1004713-1"] == 1
    assert "1004719-1" not in by_pn  # dash-2 only


def test_extract_bom_prefers_native_time_over_ocr():
    bom = extract_bom(text=_TIME_1004715_TEXT, bom_config="2")
    assert bom.method == "native_time_multi_qty"
    assert bom.part_number_count == 7


@pytest.mark.skipif(not _TIME_1004715_PDF.is_file(), reason="1004715 upload PDF absent")
def test_1004715_pdf_dash2_seven_rows():
    bom = extract_bom(_TIME_1004715_PDF, bom_config="2")
    assert bom.method == "native_time_multi_qty"
    assert bom.part_number_count == 7
    assert {r.part_no for r in bom.rows} == {
        "1004713-2",
        "1004719-1",
        "1004711-1",
        "21822-1",
        "1004712-1",
        "13349-3",
        "25060-5",
    }
