"""Sprout sleeve plate B80720004. One customer drawing. Not the rest of the drive."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from quote_core.machining_quote import attach_machining_times, machining_blocks_quote
from quote_core.machining_read import apply_drawing_reading
from quote_core.machining_symbols import describe_symbol

_FIXTURE = Path(__file__).parent / "fixtures" / "sprout_b80720004"
_PDF = _FIXTURE / "B80720004.pdf"
_STEP = _FIXTURE / "B80720004.STEP"
_PROCESS_WORDS = ("lathe", "mill", "drill", "tap", "single-point", "single point", "ream", "bore")


def _pdf_text() -> str:
    doc = fitz.open(_PDF)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def test_sprout_plate_is_the_customer_sheet():
    text = _pdf_text()
    step = _STEP.read_text(errors="ignore")
    assert "SPROUT 1.1" in text
    assert "B80720004" in text
    assert "SLEEVE PLATE COUNTERBORE" in text
    assert "6X" in text and ".63 THRU ALL" in text
    assert "1.00 X 82°" in text
    assert "0.5\" A572 GR. 50" in text
    assert "DIMENSIONS ARE IN INCHES" in text
    for word in _PROCESS_WORDS:
        assert re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is None
    assert "COUNTERSINK" not in text.upper()
    assert "CONVERSION_BASED_UNIT" in step and "INCH" in step
    assert "THREAD" not in step.upper()
    assert "GROOVE" not in step.upper()


def test_sprout_plate_reads_the_countersink_and_stays_not_done():
    takeoff = apply_drawing_reading({}, _PDF, _STEP)
    reading = takeoff["machining_reading"]
    assert takeoff["machining_features_source"] == "drawing"
    assert takeoff["needs_machining"] is True
    assert reading["needs_machining"] is True
    assert reading["practiced_on_shared_drive"] is False
    assert [feature["kind"] for feature in reading["features"]] == ["countersink"]

    feature = reading["features"][0]
    assert feature["callout"] == "6X .63 THRU / 1.00 X 82°"
    assert feature["stated_machine"] is False
    assert feature["dimensions"]["count"] == 6
    assert feature["dimensions"]["diameter_in"] == 0.63
    assert feature["dimensions"]["countersink_diameter_in"] == 1.0
    assert feature["dimensions"]["angle_deg"] == 82.0
    assert "depth_in" not in feature["dimensions"]
    assert any(row["field"] == "machine" for row in feature["blank_fields"])
    assert any("THRU" in row["note"] for row in feature["blank_fields"])
    assert "2.3" in feature["citation"]
    assert "4-41" in feature["angle_citation"]
    assert feature.get("step_match") is None

    by_text = {}
    for callout in reading["callouts"]:
        by_text.setdefault(callout["text"], callout)
        assert callout["feature"] is False
    title = by_text["COUNTERBORE"]
    assert title["symbol"] == "counterbore"
    assert "No counterbore operation was added" in title["note"]
    assert ".63" not in by_text
    assert by_text["1.00"]["feature"] is False

    assert reading["unknown_symbols"] == []
    degree = describe_symbol("°")
    plus = describe_symbol("±")
    assert degree["known"] is True and "U+00B0" in degree["citation"]
    assert plus["known"] is True and "5-2" in plus["citation"]
    house = describe_symbol("\u2302")
    assert house["known"] is False and house["meaning"] is None

    assert reading["geometry"]["units"] == "inch"
    diameters = sorted(round(row["diameter_in"], 3) for row in reading["geometry"]["cylinders"])
    assert diameters == [0.625] * 12
    assembly = reading["assembly"]
    assert assembly["leaf_parts"] == ["B80720004.STEP.STEP"]
    assert "B80720004 - SPROUT 1.1 (99.V1.RH)" in assembly["assemblies"]
    unreadable = " ".join(reading["unreadable"])
    assert "not holes" in unreadable
    assert "No thread callout in the STEP file" in unreadable
    assert "No groove callout in the STEP file" in unreadable
    assert "not read as a face operation" in unreadable
    notes = " ".join(reading["notes"])
    assert "Sprout sleeve plate B80720004" in notes
    assert "BB1013" in notes
    assert "Alcon Supporting Pin" in notes
    assert "1002309-1" in notes
    assert "rest of the shared drive has not" in notes
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
