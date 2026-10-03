"""MAC Manufacturing spacer ring 80015114. One Fort Worth drawing. Not the rest of the drive."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from quote_core.machining_quote import attach_machining_times, machining_blocks_quote
from quote_core.machining_read import apply_drawing_reading, read_stated_stock

_FIXTURE = Path(__file__).parent / "fixtures" / "mac_80015114"
_PDF = _FIXTURE / "80015114.pdf"
_STEP = _FIXTURE / "80015114.stp"
_PROCESS_WORDS = (
    "lathe",
    "mill",
    "drill",
    "tap",
    "single-point",
    "single point",
    "ream",
    "bore",
)


def _pdf_text() -> str:
    doc = fitz.open(_PDF)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def test_spacer_ring_is_the_customer_sheet():
    text = _pdf_text()
    step = _STEP.read_text(errors="ignore")
    assert "MAC MANUFACTURING" in text
    assert "80015114" in text
    assert "SEALING RING" in text
    assert "STEEL OR ALUMINUM SPACER RING" in text
    assert "DIMENSIONS ARE IN INCHES" in text
    assert 'O 5.000"' in text and 'O 3.600"' in text
    assert 'O 4.616"' in text and 'O 4.116"' in text
    assert '1.000"' in text and '.150"' in text
    assert "±2°" in text and "±1/16" in text and "±0.02" in text
    for word in _PROCESS_WORDS:
        assert re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is None
    assert "MILLI" in step.upper()
    assert "INCH" not in step.upper()
    assert "THREAD" not in step.upper()
    assert "GROOVE" not in step.upper()


def test_spacer_ring_reads_diameters_and_stays_not_done():
    takeoff = apply_drawing_reading({}, _PDF, _STEP)
    reading = takeoff["machining_reading"]
    assert takeoff["machining_features_source"] == "drawing"
    assert takeoff["needs_machining"] is True
    assert reading["needs_machining"] is True
    assert reading["features"] == []
    assert reading["practiced_on_shared_drive"] is False
    assert reading["unknown_symbols"] == []

    by_text = {}
    for callout in reading["callouts"]:
        by_text.setdefault(callout["text"], callout)
        assert callout["feature"] is False

    for text, value, matches in (
        ("⌀5.000\"", 5.0, 1),
        ("⌀3.600\"", 3.6, 1),
        ("⌀4.616\"", 4.616, 2),
        ("⌀4.116\"", 4.116, 2),
    ):
        row = by_text[text]
        assert row["symbol"] == "diameter"
        assert row["value"] == value
        assert row["unit"] == "inch"
        assert row["requires_machining"] is True
        assert "2.1" in row["citation"]
        assert "no hole feature was added" in row["note"]
        assert "No operation code was added" in row["note"]
        assert row["step_match"]["matches"] == matches
        assert abs(row["step_match"]["diameter_in"] - value) < 0.001
        assert "not added as a feature" in row["step_match"]["note"]

    for text, value in (('1.000"', 1.0), ('.150"', 0.15)):
        row = by_text[text]
        assert row["symbol"] is None
        assert row["value"] == value
        assert "No diameter symbol" in row["note"]
        assert "step_match" not in row
        assert row.get("requires_machining") is not True

    angles = by_text["±2°"]
    assert angles["symbol"] == "plus_minus"
    assert angles["value"] == 2.0
    assert "5-2" in angles["citation"]
    assert "4-41" in angles["citation"]
    assert "not calculated" in angles["note"]
    assert by_text["±0.02"]["value"] == 0.02
    assert by_text["±1/16"]["value"] == 0.0625
    assert by_text["2.4"]["feature"] is False
    assert by_text["0"]["value"] == 0.0
    assert by_text["1"]["value"] == 1.0

    assert reading["geometry"]["units"] == "millimetre"
    assert reading["geometry"]["plane_count"] == 6
    diameters = sorted(round(row["diameter_in"], 4) for row in reading["geometry"]["cylinders"])
    assert diameters == [3.6, 4.1156, 4.116, 4.6156, 4.616, 5.0]
    assembly = reading["assembly"]
    assert assembly["products"] == ["80015114"]
    assert assembly["assemblies"] == []
    assert assembly["leaf_parts"] == ["80015114"]
    unreadable = " ".join(reading["unreadable"])
    assert "not holes" in unreadable
    assert "No thread callout in the STEP file" in unreadable
    assert "No groove callout in the STEP file" in unreadable
    assert "not read as a face operation" in unreadable
    notes = " ".join(reading["notes"])
    assert "spacer ring 80015114" in notes
    assert "BB1013" in notes
    assert "Alcon Supporting Pin" in notes
    assert "1002309-1" in notes
    assert "rest of the shared drive has not" in notes
    assert "Sprout" not in notes

    sheet_stock = read_stated_stock(_pdf_text())
    assert sheet_stock["form"] == "unknown"
    assert sheet_stock["stated"] is False
    assert sheet_stock["guessed"] is False
    assert "diameter_in" not in sheet_stock
    assert "bar, plate, or tube" in sheet_stock["evidence"]

    assignment = reading["process_from_stock"]
    assert assignment["operation_justified"] is False
    assert assignment["family"] is None
    assert assignment["stated_on_sheet"] is False
    assert assignment["stock"]["form"] == "unknown"
    assert assignment["stock"]["stated"] is False
    assert assignment["stock"]["guessed"] is False
    assert "diameter_in" not in assignment["stock"]
    assert assignment["stock"].get("diameter_in") != 5.0
    assert "not guessed" in assignment["evidence"]
    assert "largest finished" not in assignment["evidence"]
    assert assignment["finished"]["shape"] == "round"
    assert assignment["finished"]["concentric"] is True
    finished = [round(value, 4) for value in assignment["finished"]["diameters_in"]]
    assert finished == [3.6, 4.116, 4.616, 5.0]
    assert max(finished) == 5.0
    assert "one centerline" in assignment["evidence"]
    assert "No operation was justified" in assignment["evidence"]
    assert "Lathe 2 was not chosen" in assignment["evidence"]
    assert "does not supply a run time" in assignment["evidence"]

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
    coded = machining["process_from_stock"]
    assert coded["operation_justified"] is False
    assert coded["operation_code"] is None
    assert coded["stock"]["form"] == "unknown"
    assert coded["finished"]["shape"] == "round"
    assert coded["run_time_min"] is None
    assert coded["setup_time_min"] is None
    assert coded["shop_rate_per_hour"] is None
    assert coded["posted"] is False
    dumped = str(machining)
    assert "op_lathe2" not in dumped
    assert "op_lathe" not in dumped
    assert "op_mill" not in dumped
