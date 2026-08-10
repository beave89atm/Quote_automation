from quote_core.drawing_title import (
    extract_assembly_description,
    extract_drawing_number_from_pdf_text,
    extract_title_from_pdf_text,
)


def test_extract_title_coupler_asm():
    text = """THIS DRAWING IS THE PROPERTY OF MAC TRAILER
PART NO
WEIGHT:
COUPLER ASM, 18-16, PNEUMATIC TANK
281.0 lbm
73476004
TRAILER MANUFACTURING INC.
"""
    assert extract_title_from_pdf_text(text, part_key="73476004") == (
        "COUPLER ASM, 18-16, PNEUMATIC TANK"
    )


def test_extract_title_stops_at_bom():
    text = """PART # : 73476054
COUPLER ASM, 18-16, TANK, 102\", 5/16\"
ITEM
QTY.
PART No.
KING PIN, 3/8\"
"""
    assert extract_title_from_pdf_text(text, part_key="73476054") == (
        'COUPLER ASM, 18-16, TANK, 102", 5/16"'
    )


def test_extract_title_guard_level_chassis():
    text = """
CONSMETIC SIDE
1/8
TYP
SECTION A-A
ITEM
DESCRIPTION
STOCKCODE
1
GAUGE/P&O 12GA /SQ IN [8 17/32" X 2 7/32"]
1510-9422
GUARD LEVEL TRAILER CHASSIS SMALL
40049600
TOLERANCES
STEEL MATERIALS - 70,000 PSI
ALUMINUM MATERIALS - 38,000 PSI
"""
    assert extract_title_from_pdf_text(text, part_key="15109422R01") == (
        "GUARD LEVEL TRAILER CHASSIS SMALL"
    )


def test_extract_assembly_description_uses_job_pdf_despite_key_mismatch(tmp_path):
    from pathlib import Path

    pdf = tmp_path / "1510-9422_R01.pdf"
    # Minimal stand-in: extractor reads via _read_pdf_text; skip if no real PDF.
    real = Path("data/uploads/64/1510-9422_R01.pdf")
    if not real.is_file():
        return
    title = extract_assembly_description(
        part_key="15109422R01",
        pdf_path=real,
    )
    assert title == "GUARD LEVEL TRAILER CHASSIS SMALL"


def test_extract_drawing_number_from_title_block():
    text = """
TYCROP MANUFACTURING LTD.
DESCRIPTION
BRACKET MS HVAC DRAIN LINE
DRAWING NUMBER
1511-5024
REV
00
UNITS
INCHES
"""
    assert extract_drawing_number_from_pdf_text(text) == "1511-5024"


def test_extract_title_cummins_prefers_title_block_not_legal_notice():
    text = """
SECTION A-A
SCALE 1 / 5
SHEET 1  OF 2
DRAWN
DWG NO
MC31-1699
TITLE
PANEL - BACK, UPPER, 604 SERIES SM, 60
SIZE
D
CUMMINS CLEAN FUEL TECHNOLOGIES
This notice must appear on any complete or partial reproduction of this document or the information contained herein.
DESCRIPTION
MU02-1008 - 1/4" PLATE, STEEL, DOMEX 100 XF
"""
    assert extract_title_from_pdf_text(text, part_key="MC31-1699") == (
        "PANEL - BACK, UPPER, 604 SERIES SM, 60"
    )


def test_extract_title_cummins_joins_title_continuation():
    text = """
DWG NO
MC31-1724
TITLE
PANEL - CLOSEOUT, INNER, BOTTOM, 50
DGE, 604 SERIES SM
SIZE
D
This notice must appear on any complete or partial reproduction of this document or the information contained herein.
"""
    title = extract_title_from_pdf_text(text, part_key="MC31-1724")
    assert title is not None
    assert "PANEL - CLOSEOUT" in title
    assert "604 SERIES SM" in title
    assert "notice must appear" not in title.lower()


def test_extract_title_cummins_plate_doubler_beats_bom_row():
    text = """
PARTS LIST
MATERIAL
QTY
MU02-1008 - 1/4" PLATE, STEEL, DOMEX 100 XF
16.88" X 11.38"
DWG NO
ME04-2773
TITLE
PLATE - DOUBLER, 604 SM, 26" TANKS,
2-5/8" BOSS
SIZE
D
CUMMINS CLEAN FUEL TECHNOLOGIES
CONFIDENTIAL AND TRADE SECRET INFORMATION OF NATURAL GAS FUEL SYSTEMS, LLC
"""
    title = extract_title_from_pdf_text(text, part_key="ME04-2773")
    assert title is not None
    assert "DOUBLER" in title.upper()
    assert "MU02-1008" not in title
