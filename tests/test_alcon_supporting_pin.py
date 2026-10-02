"""Alcon Supporting Pin, one customer drawing. Not the rest of the drive."""

from __future__ import annotations

from pathlib import Path

import fitz

from quote_core.machining_quote import attach_machining_times, quote_machining_features
from quote_core.machining_read import apply_drawing_reading
from quote_core.machining_symbols import describe_symbol

_FIXTURE = Path(__file__).parent / "fixtures" / "alcon_supporting_pin"
_PDF = _FIXTURE / "st_pin.pdf"
_STEP = _FIXTURE / "St_pin.stp"


def _pdf_text() -> str:
    doc = fitz.open(_PDF)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def test_alcon_pin_is_the_customer_sheet():
    text = _pdf_text()
    step = _STEP.read_text(errors="ignore")
    assert "ALCON RESEARCH" in text
    assert "Supporting Pin" in text
    assert "ALL DIMENSIONS ARE IN mm" in text
    assert "M6x1 ISO - H TAP" in text
    assert "5 DRILL ( 5.000 )" in text
    assert "15 g6" in text
    assert "SS-316" in text
    assert "SI_UNIT(.MILLI.,.METRE.)" in step
    assert "THREAD" not in step.upper()
    assert "GROOVE" not in step.upper()


def test_alcon_pin_reads_the_stated_tap_and_leaves_times_blank():
    takeoff = apply_drawing_reading({}, _PDF, _STEP)
    reading = takeoff["machining_reading"]
    assert takeoff["machining_features_source"] == "drawing"
    assert takeoff["needs_machining"] is True
    assert [feature["kind"] for feature in reading["features"]] == ["thread"]

    thread = reading["features"][0]
    assert thread["callout"] == "M6x1 ISO - H TAP"
    assert thread["thread_form"] == "tap"
    assert thread["thread_standard"] == "ISO"
    assert thread["thread_class"] == "H"
    assert thread["pitch_mm"] == 1.0
    assert thread["dimensions"]["major_diameter_mm"] == 6.0
    assert thread["dimensions"]["drill_diameter_mm"] == 5.0
    assert thread["dimensions"]["count"] == 1
    assert "depth_in" not in thread["dimensions"]
    assert "diameter_in" not in thread["dimensions"]
    assert "6H" not in thread["callout"]
    assert any("grade left blank" in row["note"] for row in thread["blank_fields"])
    assert any("does not say depth" in row["note"] for row in thread["blank_fields"])
    assert thread["drill_callout"] == "5 DRILL ( 5.000 )"
    assert thread["hole_callout"] == "17.000 -( 1 ) HOLE"
    assert thread["step_match"]["diameter_mm"] == 6.0
    assert thread["step_match"]["matches"] == 2
    assert thread["drill_step_match"]["diameter_mm"] == 5.0
    assert thread["drill_step_match"]["matches"] == 2

    by_text = {callout["text"]: callout for callout in reading["callouts"]}
    fit = by_text["15 g6"]
    assert fit["feature"] is False
    assert fit["symbol"] == "iso_fit"
    assert fit["value"] == 15
    assert fit["fit"] == "g6"
    assert "286-1" in fit["citation"]
    assert "not calculated" in fit["note"]
    assert fit["step_match"]["matches"] == 2
    described = describe_symbol("g6")
    assert described["known"] is True
    assert described["meaning"]
    assert "limit" in described["meaning"].lower()

    assert by_text["R5"]["symbol"] == "radius"
    assert by_text["R5"]["feature"] is False
    assert by_text["55±0.02"]["feature"] is False
    assert by_text["55±0.02"]["symbol"] == "plus_minus"
    assert "5-2" in by_text["55±0.02"]["citation"]
    assert "not calculated" in by_text["55±0.02"]["meaning"]
    assert by_text["28.64°"]["feature"] is False
    assert by_text["28.64°"]["symbol"] == "degree"
    assert by_text["22.2°"]["feature"] is False
    assert by_text["22.2°"]["symbol"] == "degree"
    for bare in ("12", "5", "15", "10.5", "16.12"):
        assert by_text[bare]["feature"] is False
    assert all(callout["feature"] is False for callout in reading["callouts"])

    assert reading["unknown_symbols"] == []
    plus = describe_symbol("±")
    degree = describe_symbol("°")
    assert plus["known"] is True and plus["meaning"]
    assert degree["known"] is True and degree["meaning"]

    assert reading["geometry"]["units"] == "millimetre"
    assert reading["geometry"]["plane_count"] == 3
    diameters = sorted(round(row["diameter_in"] * 25.4, 4) for row in reading["geometry"]["cylinders"])
    assert diameters == [5.0, 5.0, 6.0, 6.0, 10.5, 10.5, 15.0, 15.0]
    assert reading["assembly"]["products"] == ["ORIGI"]
    assert reading["assembly"]["assemblies"] == []
    assert reading["assembly"]["leaf_parts"] == ["ORIGI"]
    unreadable = " ".join(reading["unreadable"])
    assert "No face callout in the PDF" in unreadable
    assert "No groove callout in the PDF" in unreadable
    assert "not holes" in unreadable
    assert "No thread callout in the STEP file" in unreadable
    assert "No groove callout in the STEP file" in unreadable
    assert "not read as a face operation" in unreadable
    assert reading["practiced_on_shared_drive"] is False
    notes = " ".join(reading["notes"])
    assert "Alcon Supporting Pin" in notes
    assert "BB1013" in notes
    assert "rest of the shared drive has not" in notes

    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["needs_machining"] is True
    assert result["quote_done"] is False
    assert result["operation_count"] == 2
    assert result["posted"] is False
    assert result["shop_rate_per_hour"] is None
    assert result["setup_time_min"] is None
    assert result["missing"] == ["run_time", "setup_time"]
    assert result["unresolved_features"] == []
    assert [(op["name"], op["operation_code"], op["run_time_min"]) for op in result["operations"]] == [
        ("drill", "op_mill", None),
        ("tap", "op_mill", None),
    ]
    item = result["item_operations"][0]
    assert item["operation_code"] == "op_mill"
    assert item["setup"]["calculator"] == "Milling-Setup"
    assert item["setup"]["time_min"] is None
    assert item["run"]["calculator"] == "Milling-Time"
    assert item["run"]["time_min"] is None
    assert item["posted"] is False

    times = attach_machining_times({"weld_minutes": 3.0}, takeoff)
    assert times["weld_minutes"] == 3.0
    assert times["machining"]["quote_done"] is False
    assert times["machining"]["setup_time_min"] is None
    assert times["machining"]["posted"] is False
    assert times["machining"]["missing"] == ["run_time", "setup_time"]
