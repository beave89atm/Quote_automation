"""BB2000-ASM, one customer assembly. Not a stand-in for the rest of the drive.

The STEP fixture keeps the product and occurrence lines from the customer
file, plus one inch unit. Cylinders were not copied. The full file has 15
solids and 1011 cylindrical surfaces; those surfaces are not holes.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from quote_core.machining_quote import attach_machining_times
from quote_core.machining_read import apply_drawing_reading

_FIXTURE = Path(__file__).parent / "fixtures" / "bb2000"
_PDF = _FIXTURE / "BB2000-ASM.pdf"
_STEP = _FIXTURE / "BB2000-ASM-cut.step"


def test_bb2000_assembly_does_not_assign_callouts_to_one_part():
    takeoff = apply_drawing_reading({}, _PDF, _STEP)
    reading = takeoff["machining_reading"]
    assert takeoff["machining_features_source"] == "drawing"
    assert takeoff["machining_features"] == []
    assert takeoff["needs_machining"] is True
    assert reading["features"] == []
    assert reading["needs_machining"] is True

    assembly = reading["assembly"]
    assert assembly["drawing_number"] == "BB2000-ASM"
    assert assembly["assemblies"] == ["BB1000-ASM", "BB1010-ASM", "BB2000-ASM"]
    assert assembly["leaf_parts"] == [
        "BB1001",
        "BB1002",
        "BB1003",
        "BB1004",
        "BB1005",
        "BB1006",
        "BB1007",
        "BB1008",
        "BB1009",
        "BB1011",
        "BB1012",
        "BB1013",
        "BB1014",
        "BB1017",
        "BB1018",
    ]
    assert assembly["pdf_only_parts"] == ["BB1015"]
    assert assembly["occurrences"]["BB1000-ASM"] == {
        "BB1001": 1,
        "BB1002": 1,
        "BB1003": 1,
        "BB1004": 1,
        "BB1005": 1,
        "BB1006": 1,
    }
    assert "BB1012" not in assembly["occurrences"]["BB1000-ASM"]
    assert assembly["occurrences"]["BB1010-ASM"] == {"BB1007": 1, "BB1008": 2}
    assert assembly["occurrences"]["BB2000-ASM"]["BB1012"] == 6
    assert assembly["occurrences"]["BB2000-ASM"]["BB1000-ASM"] == 3
    assert assembly["occurrences"]["BB2000-ASM"]["BB1008"] == 4

    holes = [callout for callout in reading["callouts"] if callout.get("unassigned_hole")]
    assert [(callout["sheet"], callout["text"]) for callout in holes] == [
        (6, "2X THRU 0.44"),
        (6, "2X THRU 0.44"),
        (10, "18X 0.13"),
        (10, "2X 0.44"),
    ]
    sheet6 = holes[0]
    assert sheet6["feature"] is False
    assert sheet6["assigned_part"] is None
    assert sheet6["count"] == 2
    assert sheet6["thru"] is True
    assert sheet6["value"] == 0.44
    assert set(sheet6["parts_on_sheet"]) == {"BB1002", "BB1004", "BB1005", "BB1006"}
    assert "not assigned" in sheet6["note"]
    assert holes[2]["count"] == 18
    assert holes[2]["thru"] is False
    assert holes[2]["value"] == 0.13
    assert holes[3]["thru"] is False
    assert holes[3]["text"] == "2X 0.44"
    assert set(holes[2]["parts_on_sheet"]) == {
        "BB1008",
        "BB1009",
        "BB1011",
        "BB1017",
        "BB1018",
    }

    radii = [callout["text"] for callout in reading["callouts"] if callout.get("symbol") == "radius"]
    assert radii == ["4X R0.20", "4X R0.25", "4X R0.20"]
    assert all(
        callout["feature"] is False and callout["assigned_part"] is None
        for callout in reading["callouts"]
        if callout.get("symbol") == "radius"
    )
    repeated = next(callout for callout in reading["callouts"] if callout["text"] == "8X 14.00")
    assert repeated["feature"] is False
    assert repeated["symbol"] == "repetition"
    assert "no hole" in repeated["note"]

    stock = {
        callout["text"]: callout
        for callout in reading["callouts"]
        if "Stock thickness" in callout["note"]
    }
    assert stock["BB1012 0.25"]["assigned_part"] == "BB1012"
    assert stock["BB1012 0.25"]["feature"] is False
    assert "not added as a machine operation" in stock["BB1012 0.25"]["note"]
    assert stock["BB1014 0.125"]["assigned_part"] == "BB1014"
    assert stock["BB1015 0.125"]["assigned_part"] == "BB1015"
    assert stock["sheet 10 stock 0.125, 0.25"]["assigned_part"] is None
    assert stock["sheet 3 stock 0.125"]["assigned_part"] is None

    assert [row["symbol"] for row in reading["unknown_symbols"]] == ["°"]
    assert reading["unknown_symbols"][0]["meaning"] is None
    unreadable = " ".join(reading["unreadable"])
    assert "FINISH is on the drawing" in unreadable
    assert "OUTSOURCE is on the drawing" in unreadable
    assert "No thread designation in the PDF" in unreadable
    assert "No groove callout in the PDF" in unreadable
    assert "No face callout in the PDF" in unreadable
    assert "not holes" in unreadable
    assert "BB1015 is on the PDF and not in the STEP" in unreadable
    assert "Run time and setup stay blank" in unreadable
    assert reading["geometry"]["units"] == "inch"
    assert reading["geometry"]["cylinders"] == []
    assert "CYLINDRICAL_SURFACE" not in _STEP.read_text()
    assert reading["practiced_on_shared_drive"] is False
    joined = " ".join(reading["notes"])
    assert "BB2000-ASM" in joined
    assert "BB1013" in joined
    assert "rest of the shared drive has not" in joined
    assert "15 leaf parts" in joined
    assert "not treated as one machined part" in joined

    times = attach_machining_times({"weld_minutes": 1.0}, takeoff)
    machining = times["machining"]
    assert times["weld_minutes"] == 1.0
    assert machining["needs_machining"] is True
    assert machining["quote_done"] is False
    assert machining["operation_count"] is None
    assert machining["operations"] == []
    assert machining["item_operations"] == []
    assert machining["setup_time_min"] is None
    assert machining["posted"] is False
    assert machining["missing"] == ["operation_count", "run_time", "setup_time"]
    assert machining["reads_drawings"] is True

    doc = fitz.open(_PDF)
    try:
        top = doc[2].get_text("text")
        leg = doc[3].get_text("text")
    finally:
        doc.close()
    assert "BB1000-ASM\nLEG WELDMENT\n3" in top
    assert "BB1012\n.25 FLOOR PLATE\n2" in leg
