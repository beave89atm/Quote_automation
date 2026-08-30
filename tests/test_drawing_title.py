from quote_core.drawing_title import (
    extract_assembly_description,
    extract_drawing_number_from_pdf_text,
    extract_title_from_pdf_text,
    is_drawing_boilerplate_title,
    title_from_exploded_names,
)


def test_drawing_sole_property_is_not_a_title():
    text = """
34137-1
DRAWING IS THE SOLE PROPERTY OF
TIME MANUFACTURING
ALUMINUM PLATFORM WELDMENT
"""
    title = extract_title_from_pdf_text(text, part_key="34137-1")
    assert title is not None
    assert "SOLE PROPERTY" not in title.upper()
    assert "WELDMENT" in title.upper()
    assert is_drawing_boilerplate_title("DRAWING IS THE SOLE PROPERTY OF")
    assert is_drawing_boilerplate_title("34137-1 - DRAWING IS THE SOLE PROPERTY OF")
    from secturafab.item_desc import format_quote_header_description

    assert format_quote_header_description(
        "DRAWING IS THE SOLE PROPERTY OF", part_key="34137-1"
    ) == ""
    assert title_from_exploded_names(
        [
            "Root",
            "34137-1",
            "88010 ALUMINUM HINGE-4209_88010-1 Flexible",
            "34136-1 Aluminum Platform Weldment_34136-1",
            "34134 ALUMINUM DOOR WELDMENT-4159_34134-1",
        ]
    )
    weld = title_from_exploded_names(
        [
            "Root",
            "34136-1 Aluminum Platform Weldment_34136-1",
        ]
    )
    assert weld is not None
    assert "PLATFORM" in weld.upper()
    assert "WELDMENT" in weld.upper()


def test_nested_rest_gate_sub_weldment_is_not_quote_title():
    """Live 107877-1: child REST/GATE/SUB-WELDMENT is not the header."""
    from quote_core.drawing_title import is_nested_child_weldment_title

    assert is_nested_child_weldment_title("PLATFORM REST SUB-WELDMENT")
    assert is_nested_child_weldment_title("GATE WELDMENT-2640_103535-1")
    assert is_nested_child_weldment_title("REST WELDMENT-2742_105094-1")
    assert not is_nested_child_weldment_title("PLATFORM WELDMENT WITHOUT JIB")
    picked = title_from_exploded_names(
        [
            "Root",
            "-28656",
            "GATE WELDMENT-2640_103535-1",
            "REST WELDMENT-2742_105094-1",
            "107877-1 PLATFORM WELDMENT WITHOUT JIB",
        ]
    )
    assert picked is not None
    assert "WITHOUT JIB" in picked.upper()
    assert "REST" not in picked.upper()
    assert "GATE" not in picked.upper()
    text = """
107877-1
TITLE:
PLATFORM WELDMENT WITHOUT JIB
PLATFORM REST SUB-WELDMENT
GATE WELDMENT
"""
    title = extract_title_from_pdf_text(text, part_key="107877-1")
    assert title is not None
    assert "WITHOUT JIB" in title.upper()
    assert "REST" not in title.upper()
    assert "GATE" not in title.upper()


def test_base_plate_is_not_pedestal_weldment_header():
    """Live 1020249-1: BASE PLATE, PEDESTAL is a child — not the quote title."""
    from quote_core.drawing_title import is_child_part_title

    assert is_child_part_title("BASE PLATE, PEDESTAL")
    assert not is_child_part_title("PEDESTAL WELDMENT")
    assert not is_child_part_title("PLATE - DOUBLER, 604 SM")
    text = """
1020249-1
TITLE:
BASE PLATE, PEDESTAL
PEDESTAL WELDMENT
"""
    title = extract_title_from_pdf_text(text, part_key="1020249-1")
    assert title is not None
    assert "WELDMENT" in title.upper()
    assert "BASE PLATE" not in title.upper()


def test_operator_platform_is_header_not_12ga_material():
    """Live 107292-1: OPERATOR PLATFORM… is the header, not 12GA A1011 stock."""
    from quote_core.drawing_title import is_material_callout_title
    from secturafab.item_desc import format_quote_header_description

    stock = "12 GA PLATE A1011 CS TYPE B (38K)"
    header = "OPERATOR PLATFORM LOWER CONTROL MOUNT"
    assert is_material_callout_title(stock)
    assert not is_material_callout_title(header)
    assert format_quote_header_description(stock, part_key="107292-1") == ""
    assert format_quote_header_description(header, part_key="107292-1") == header
    text = """
107292-1
TITLE:
OPERATOR PLATFORM LOWER CONTROL MOUNT
12 GA PLATE A1011 CS TYPE B (38K)
MATERIAL
12 GA
"""
    title = extract_title_from_pdf_text(text, part_key="107292-1")
    assert title is not None
    assert title.upper() == header
    assert "12 GA" not in title.upper()
    assert "A1011" not in title.upper()


def test_turret_side_plate_is_header_for_piece_part_pn():
    """Live 11796-1 leftover: TURRET SIDE PLATE is the quote, not a child."""
    from quote_core.drawing_title import is_child_part_title
    from secturafab.item_desc import format_quote_header_description

    assert is_child_part_title("TURRET SIDE PLATE")
    text = """
11796-1
TITLE:
TURRET SIDE PLATE
SIZE
B
"""
    title = extract_title_from_pdf_text(text, part_key="11796-1")
    assert title is not None
    assert title.upper() == "TURRET SIDE PLATE"
    assert format_quote_header_description(title, part_key="11796-1") == (
        "TURRET SIDE PLATE"
    )


def test_ehb3112_right_door_assembly_is_header():
    """Live EHB3112: header is RIGHT DOOR ASSEMBLY, never bare PN."""
    from secturafab.item_desc import format_quote_header_description

    text = """
EHB3112-1
DWG NO
TITLE
RIGHT DOOR ASSEMBLY
SIZE
D
"""
    title = extract_title_from_pdf_text(text, part_key="EHB3112")
    assert title is not None
    assert title.upper() == "RIGHT DOOR ASSEMBLY"
    assert format_quote_header_description(title, part_key="EHB3112") == (
        "RIGHT DOOR ASSEMBLY"
    )
    assert format_quote_header_description("EHB3112", part_key="EHB3112") == ""


def test_bb2000_dwg_no_is_not_quote_header():
    """Live BB2000-ASM: PN + DWG. NO. is drawing-block junk, not the header."""
    from secturafab.item_desc import (
        format_assembly_description,
        format_quote_header_description,
        title_from_job_title,
    )

    junk = "BB2000-ASM - DWG. NO."
    assert is_drawing_boilerplate_title(junk)
    assert is_drawing_boilerplate_title("DWG. NO.")
    assert is_drawing_boilerplate_title("DWG NO")
    assert format_quote_header_description(junk, part_key="BB2000-ASM") == ""
    assert title_from_job_title(junk, part_key="BB2000-ASM") is None
    assert format_assembly_description("BB2000-ASM", junk) == "BB2000-ASM"
    assert title_from_exploded_names(
        ["Root"] + ["BB2000-ASM"] * 10 + ["BB1000-ASM"] * 6 + ["BB1010-ASM"] * 2
    ) is None
    text = """
BB2000-ASM
DWG. NO.
TITLE:
BATTING CAGE BENCH
"""
    title = extract_title_from_pdf_text(text, part_key="BB2000-ASM")
    assert title is not None
    assert "BENCH" in title.upper()
    assert "DWG" not in title.upper()
    assert format_quote_header_description(title, part_key="BB2000-ASM") == title


def test_inner_frame_plate_is_not_power_frame_weldment_header():
    """Live P001545: child INNER FRAME PLATE is not the quote header."""
    from quote_core.drawing_title import is_child_part_title
    from secturafab.item_desc import format_quote_header_description

    assert is_child_part_title("WELDMENT, FRAME PLATE, INNER")
    assert is_child_part_title("INNER FRAME PLATE")
    assert not is_child_part_title("POWER FRAME WELDMENT")
    assert format_quote_header_description(
        "POWER FRAME WELDMENT", part_key="P001545"
    ) == "POWER FRAME WELDMENT"
    text = """
P001545
TITLE:
WELDMENT, FRAME PLATE, INNER
POWER FRAME WELDMENT
"""
    title = extract_title_from_pdf_text(text, part_key="P001545")
    assert title is not None
    assert "POWER FRAME" in title.upper()
    assert "INNER" not in title.upper()


def test_marmon_order_material_is_not_jib_head_weldment_header():
    """Live 5003313-001: vendor note is not the quote header."""
    from secturafab.item_desc import format_quote_header_description

    assert is_drawing_boilerplate_title("Order Material from Marmon Keystone")
    assert is_drawing_boilerplate_title(
        "5003313-001 - Order Material from Marmon Keystone"
    )
    assert format_quote_header_description(
        "5003313-001 - Order Material from Marmon Keystone",
        part_key="5003313-001",
    ) == ""
    assert format_quote_header_description(
        "ROT MB JIB HEAD WELDMENT", part_key="5003313-001"
    ) == "ROT MB JIB HEAD WELDMENT"
    text = """
5003313-001
TITLE:
5003313-001 - Order Material from Marmon Keystone
ROT MB JIB HEAD WELDMENT
BASE PLATE
"""
    title = extract_title_from_pdf_text(text, part_key="5003313-001")
    assert title is not None
    assert "WELDMENT" in title.upper()
    assert "JIB HEAD" in title.upper()
    assert "MARMON" not in title.upper()
    assert "ORDER MATERIAL" not in title.upper()
    assert "BASE PLATE" not in title.upper()


def test_three_place_decimal_is_not_a_title():
    """Live 34137-2 stamped THREE PLACE DECIMAL — drawing note, not the weldment."""
    from secturafab.item_desc import (
        format_assembly_description,
        format_quote_header_description,
    )

    assert is_drawing_boilerplate_title("THREE PLACE DECIMAL")
    assert is_drawing_boilerplate_title("34137-2 - THREE PLACE DECIMAL")
    assert format_quote_header_description(
        "THREE PLACE DECIMAL", part_key="34137-2"
    ) == ""
    assert format_quote_header_description(
        "34137-2 - THREE PLACE DECIMAL", part_key="34137-2"
    ) == ""
    assert "DECIMAL" not in format_assembly_description(
        "34137-2", "THREE PLACE DECIMAL"
    )
    text = """
34137-2
THREE PLACE DECIMAL
DRAWING IS THE SOLE PROPERTY OF
ALUMINUM PLATFORM WELDMENT
"""
    title = extract_title_from_pdf_text(text, part_key="34137-2")
    assert title is not None
    assert "DECIMAL" not in title.upper()
    assert "SOLE PROPERTY" not in title.upper()
    assert "PLATFORM" in title.upper() or "WELDMENT" in title.upper()


def test_test_fit_weldment_in_is_not_a_title():
    """Live 106386-1 stamped TEST FIT WELDMENT IN — drawing note, not the title."""
    from secturafab.item_desc import (
        format_assembly_description,
        format_quote_header_description,
    )

    assert is_drawing_boilerplate_title("TEST FIT WELDMENT IN")
    assert is_drawing_boilerplate_title("106386-1 - TEST FIT WELDMENT IN")
    assert format_quote_header_description(
        "TEST FIT WELDMENT IN", part_key="106386-1"
    ) == ""
    assert "TEST FIT" not in format_assembly_description(
        "106386-1", "TEST FIT WELDMENT IN"
    )
    text = """
106386-1
TEST FIT WELDMENT IN
DRAWING IS THE SOLE PROPERTY OF
PLATFORM EXTENSION WELDMENT 42 IN
"""
    title = extract_title_from_pdf_text(text, part_key="106386-1")
    assert title is not None
    assert "TEST FIT" not in title.upper()
    assert "PLATFORM" in title.upper()
    assert "WELDMENT" in title.upper()


def test_check_other_options_is_not_a_title():
    """Live 106687-1 stamped CHECK OTHER OPTIONS — drawing note, not the title."""
    from secturafab.item_desc import format_quote_header_description

    assert is_drawing_boilerplate_title("CHECK OTHER OPTIONS")
    assert is_drawing_boilerplate_title("CHECK OTHER OPTIONS…")
    assert format_quote_header_description(
        "CHECK OTHER OPTIONS", part_key="106687-1"
    ) == ""
    text = """
106687-1
CHECK OTHER OPTIONS
DRAWING IS THE SOLE PROPERTY OF
PLATFORM WELDMENT
"""
    title = extract_title_from_pdf_text(text, part_key="106687-1")
    assert title is not None
    assert "CHECK OTHER" not in title.upper()
    assert "PLATFORM" in title.upper()
    assert "WELDMENT" in title.upper()


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
