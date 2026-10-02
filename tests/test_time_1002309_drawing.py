"""Time handle shaft 1002309-1. One customer weldment. Not the rest of the drive."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from quote_core.machining_quote import attach_machining_times, machining_blocks_quote
from quote_core.machining_read import apply_drawing_reading

_FIXTURE = Path(__file__).parent / "fixtures" / "time_1002309"
_PDF = _FIXTURE / "1002309-1.pdf"
_STEP = _FIXTURE / "1002309-1.step"
_PROCESS_WORDS = ("lathe", "mill", "drill", "tap", "single-point", "single point")


def _pdf_text() -> str:
    doc = fitz.open(_PDF)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def test_handle_shaft_is_the_customer_weldment():
    text = _pdf_text()
    step = _STEP.read_text(errors="ignore")
    assert "HANDLE SHAFT WELDMENT" in text
    assert "1002309-1" in text
    assert "1002308-1" in text and "SHAFT" in text
    assert "1002307-1" in text and "ROTATION ARM" in text
    assert "ZINC PLATE" in text
    assert "ALL DIMENSIONS ARE IN INCHES" in text
    assert "CENTERLINE OF TAPPED HOLE IN" in text
    assert "DRILLED" in text
    assert "MACHINED SURFACE FINISHES=" in text
    assert "USE WELDING WIRE" in text
    assert "89176-2" in text
    for word in _PROCESS_WORDS:
        assert re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is None
    assert "CONVERSION_BASED_UNIT" in step and "INCH" in step
    assert "THREAD" not in step.upper()
    assert "GROOVE" not in step.upper()


def test_handle_shaft_names_holes_without_a_process_and_stays_not_done():
    takeoff = apply_drawing_reading({}, _PDF, _STEP)
    reading = takeoff["machining_reading"]
    assert takeoff["machining_features_source"] == "drawing"
    assert takeoff["needs_machining"] is True
    assert reading["needs_machining"] is True
    assert reading["features"] == []
    assert reading["practiced_on_shared_drive"] is False

    by_text = {}
    for callout in reading["callouts"]:
        by_text.setdefault(callout["text"], callout)
        assert callout["feature"] is False

    zinc = by_text["ZINC PLATE"]
    assert zinc["outside_process"] is True
    assert "outside process" in zinc["note"]
    assert "not a shop machine operation" in zinc["note"]

    holes = by_text["TAPPED HOLE IN 2 / DRILLED HOLE IN 1"]
    assert holes["requires_machining"] is True
    assert "does not give a diameter" in holes["note"]
    assert "thread designation" in holes["note"]
    assert "No operation was added" in holes["note"]

    assert by_text["3/16"]["value"] == 0.1875
    assert by_text["1 1/16"]["value"] == 1.0625
    assert by_text[".19"]["value"] == 0.19
    assert by_text["90°"]["value"] == 90.0
    finish = by_text["MACHINED SURFACE FINISHES= 125"]
    assert finish["value"] == 125
    assert "does not name the parameter" in finish["note"]
    assert "Ra" not in finish["note"]
    assert all(callout.get("step_match") is None for callout in reading["callouts"])

    unknown = {row["symbol"]: row for row in reading["unknown_symbols"]}
    assert set(unknown) == {"°"}
    assert unknown["°"]["known"] is False
    assert unknown["°"]["meaning"] is None

    assert reading["geometry"]["units"] == "inch"
    assert reading["geometry"]["plane_count"] == 12
    diameters = sorted(round(row["diameter_in"], 3) for row in reading["geometry"]["cylinders"])
    assert diameters == [
        0.125,
        0.213,
        0.213,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.58,
        0.58,
        0.78,
        0.78,
        1.0,
        1.0,
    ]
    assembly = reading["assembly"]
    assert assembly["assemblies"] == ["1002309 handle shaft wldmt-11504"]
    assert assembly["leaf_parts"] == [
        "1002307 rotation arm-11503_1002307-1",
        "1002308 shaft-11501_1002308-1",
    ]
    assert assembly["occurrences"]["1002309 handle shaft wldmt-11504"] == {
        "1002307 rotation arm-11503_1002307-1": 1,
        "1002308 shaft-11501_1002308-1": 1,
    }

    unreadable = " ".join(reading["unreadable"])
    assert "No face callout in the PDF" in unreadable
    assert "No thread designation in the PDF" in unreadable
    assert "No groove callout in the PDF" in unreadable
    assert "not holes" in unreadable
    assert "No thread callout in the STEP file" in unreadable
    assert "No groove callout in the STEP file" in unreadable
    assert "not read as a face operation" in unreadable
    assert "No finish value" not in unreadable
    assert "89176" not in unreadable
    joined_callouts = " ".join(callout["text"] for callout in reading["callouts"])
    assert "89176" not in joined_callouts
    assert "WELDING WIRE" not in joined_callouts

    notes = " ".join(reading["notes"])
    assert "Time handle shaft 1002309-1" in notes
    assert "Alcon Supporting Pin" in notes
    assert "BB1013" in notes
    assert "rest of the shared drive has not" in notes
    assert "2 leaf parts" in notes
    assert "were not treated as one machined part" in notes

    times = attach_machining_times({"weld_minutes": 3.0}, takeoff)
    machining = times["machining"]
    assert times["weld_minutes"] == 3.0
    assert machining["needs_machining"] is True
    assert machining["quote_done"] is False
    assert machining["operation_count"] is None
    assert machining["operations"] == []
    assert machining["item_operations"] == []
    assert machining["missing"] == ["operation_count", "run_time", "setup_time"]
    assert machining["setup_time_min"] is None
    assert machining["shop_rate_per_hour"] is None
    assert machining["posted"] is False
    assert machining_blocks_quote(times) is True
    dumped = str(machining)
    for code in ("op_mill", "op_lathe", "op_lathe2"):
        assert code not in dumped
