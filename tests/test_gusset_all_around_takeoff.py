"""Gusset all-around weld inches from PARTS LIST + component blank sizes."""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import extract_bom_from_parts_list
from quote_core.weld.takeoff import (
    _estimate_gusset_all_around_segments,
    _plate_blank_size_from_text,
    _segments_total_inches,
)


SAMPLE_PARTS_LIST = """
PARTS LIST
DESCRIPTION
PART NUMBER
QTY
ITEM
PLATE - GUSSET, DRIVER SIDE, MIDDLE, MCNEILUS TAILGATE
MD04-2482
1
1
PLATE - GUSSET, DRIVER SIDE, BOTTOM, MCNEILUS TAILGATE
MD04-2483
1
2
PLATE - GUSSET, DRIVER SIDE, TOP, MCNEILUS TAILGATE
MD04-2484
1
3
STRUCTURE - CHANNEL, DRIVER SIDE, MCNEILUS TAILGATE, HEXAGON
TANKS
ME04-3452
1
4
NOTES:
1) ALL DIMENSIONS ARE IN INCHES
"""


def test_parts_list_parser_cummins_style():
    bom = extract_bom_from_parts_list(text=SAMPLE_PARTS_LIST)
    assert bom.method == "native_parts_list"
    assert bom.piece_count == 4
    assert [r.part_no for r in bom.rows] == [
        "MD04-2482",
        "MD04-2483",
        "MD04-2484",
        "ME04-3452",
    ]
    assert all("GUSSET" in r.description.upper() for r in bom.rows[:3])


def test_plate_blank_perimeter_math():
    blank = _plate_blank_size_from_text('MATERIAL\n7.00" X 3.19"\nPLATE - GUSSET')
    assert blank == (7.0, 3.19)
    assert round(2.0 * (blank[0] + blank[1]), 2) == 20.38


def test_gusset_segments_from_library_if_present():
    lib = Path(
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering"
        r"\Customer Drawings\Cummins Clean Fuel Technologies\701-100-MN-HX"
    )
    assembly = lib / "ME04-3453.dwg.pdf"
    if not assembly.exists():
        return
    segs, notes = _estimate_gusset_all_around_segments(
        assembly,
        library_folder=lib,
        related_pdf_names=[p.name for p in lib.glob("MD04-248*.dwg.pdf")],
    )
    assert len(segs) == 3
    total = _segments_total_inches(segs)
    # 20.38 + 25.70 + 24.70 = 70.78
    assert abs(total - 70.78) < 0.05
    assert any("MD04-2482" in n for n in notes)
