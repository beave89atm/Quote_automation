"""Sprout sleeve plate B80720004. A countersink case. Not Fort Worth Customer Drawings."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

import pytest

from quote_core.machining_calculator import (
    CONFIDENCE_PAD,
    DEBURR_MIN_PER_PART,
    IN_PROCESS_MIN_PER_PART,
    RAPID_MIN_PER_OPERATION,
    STARTER_COUNTERSINK_MIN,
    STARTER_THRU_HOLE_MIN,
)
from quote_core.machining_quote import attach_machining_times, machining_blocks_quote
from quote_core.machining_read import apply_drawing_reading, read_stated_stock
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
    assert feature["machine"] == "mill"
    assert feature["machine_source"] == "stock_vs_finished"
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
    shared = next(note for note in reading["notes"] if "shared drive" in note)
    assert "Sprout" not in shared
    assert "B80720004" not in shared
    assert "BB1013" in shared
    assert "Alcon Supporting Pin" in shared
    assert "1002309-1" in shared
    assert "rest of the shared drive has not" in shared
    assert "were not treated as one machined part" in notes
    sheet_stock = read_stated_stock(_pdf_text())
    assert sheet_stock["form"] == "plate"
    assert sheet_stock["stated"] is True
    assert sheet_stock["guessed"] is False
    assert sheet_stock["thickness_in"] == 0.5
    assert "SLEEVE PLATE" in sheet_stock["evidence"]
    assert "A572" in sheet_stock["evidence"]
    assignment = reading["process_from_stock"]
    assert assignment["operation_justified"] is True
    assert assignment["family"] == "mill"
    assert assignment["stated_on_sheet"] is False
    assert assignment["stock"]["form"] == "plate"
    assert assignment["stock"]["guessed"] is False
    assert assignment["stock"]["thickness_in"] == 0.5
    assert "A572" in assignment["stock"]["evidence"]
    assert assignment["finished"]["shape"] == "plate"
    assert "vertex" not in str(assignment["stock"]).lower()
    assert "countersink" in assignment["evidence"]
    assert "not turning" in assignment["evidence"]
    assert "does not supply a run time" in assignment["evidence"]

    times = attach_machining_times({"weld_minutes": 3.0}, takeoff)
    machining = times["machining"]
    assert times["weld_minutes"] == 3.0
    assert machining["needs_machining"] is True
    assert machining["quote_done"] is False
    assert machining["operation_count"] == 1
    feature_minutes = 6 * (STARTER_THRU_HOLE_MIN + STARTER_COUNTERSINK_MIN)
    allowances = RAPID_MIN_PER_OPERATION + DEBURR_MIN_PER_PART + IN_PROCESS_MIN_PER_PART
    run = (feature_minutes + allowances) * CONFIDENCE_PAD
    assert machining["operations"][0]["name"] == "countersink"
    assert machining["operations"][0]["operation_code"] == "op_mill"
    assert machining["operations"][0]["run_time_min"] == pytest.approx(run)
    assert machining["operations"][0]["run_time_source"] == "calculator"
    assert "not shop-proven" in machining["operations"][0]["note"]
    assert machining["item_operations"][0]["operation_code"] == "op_mill"
    assert machining["item_operations"][0]["setup"]["calculator"] == "Milling-Setup"
    assert machining["item_operations"][0]["setup"]["time_min"] == 75.0
    assert machining["item_operations"][0]["setup"]["fixedtime_hours"] == 1.25
    assert machining["item_operations"][0]["run"]["time_min"] == pytest.approx(run)
    assert machining["missing"] == ["shop_rate"]
    assert machining["setup_time_min"] == 75.0
    assert machining["shop_rate_per_hour"] is None
    assert machining["quote_done"] is False
    assert machining["posted"] is False
    assert machining_blocks_quote(times) is True
    coded = machining["process_from_stock"]
    assert coded["operation_code"] == "op_mill"
    assert coded["run_time_min"] == pytest.approx(run)
    assert coded["setup_time_min"] == 75.0
    assert coded["calculator"]["cubic_inches_removed"] == 0.0
    assert coded["calculator"]["feature_minutes"] == pytest.approx(feature_minutes)
    assert coded["calculator"]["starter_feature_minutes"] is True
    assert coded["calculator"]["shop_proven"] is False
    assert [row["feature"] for row in coded["calculator"]["feature_rows"]] == [
        "thru_hole",
        "countersink",
    ]
    assert coded["calculator"]["shop_rate_per_hour"] is None
    assert coded["calculator"]["program_hours_not_setup"] == 2.0
    assert coded.get("run_blank_reason") is None
    dumped = str(machining)
    assert "op_lathe2" not in dumped
    assert "op_lathe" not in dumped.replace("op_lathe2", "")
