"""Labeled turned-shaft practice fixture. Not a customer drawing.

No Fort Worth turned PDF and STEP pair was in this workspace. The sheet
is marked as a practice fixture and is read by the same reader used for
BB1013. Callouts that are not in the file are not added.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from quote_core.machining_quote import attach_machining_times, quote_machining_features
from quote_core.machining_read import apply_drawing_reading
from quote_core.machining_symbols import describe_symbol

_FIXTURE = Path(__file__).parent / "fixtures" / "turned_practice"
_PDF = _FIXTURE / "PRACTICE-TURNED.pdf"
_STEP = _FIXTURE / "PRACTICE-TURNED.step"


def _pdf_text() -> str:
    doc = fitz.open(_PDF)
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def test_turned_practice_fixture_is_labeled_and_not_a_customer_file():
    text = _pdf_text()
    step = _STEP.read_text()
    assert "PRACTICE FIXTURE" in text
    assert "NOT A CUSTOMER DRAWING" in text
    assert "PRACTICE FIXTURE" in step
    assert "NOT A CUSTOMER FILE" in step
    assert "BB1013" not in text
    assert "BB2000" not in text


def test_turned_practice_reads_stepped_diameters_face_groove_and_thread():
    text = _pdf_text()
    assert "\u2300" in text
    assert "1/4-20 UNC-2B" in text
    assert "45\u00b0 CHAMFER" in text

    takeoff = apply_drawing_reading({}, _PDF, _STEP)
    reading = takeoff["machining_reading"]
    assert takeoff["machining_features_source"] == "drawing"
    assert [feature["kind"] for feature in reading["features"]] == [
        "face",
        "groove",
        "thread",
    ]

    by_kind = {feature["kind"]: feature for feature in reading["features"]}
    face = by_kind["face"]
    assert face["callout"] == "FACE"
    assert "machine" not in face
    assert any(row["field"] == "machine" for row in face["blank_fields"])
    assert "step_match" not in face

    groove = by_kind["groove"]
    assert groove["dimensions"] == {"width_in": 0.125, "depth_in": 0.06}
    assert any(row["field"] == "machine" for row in groove["blank_fields"])
    assert "step_match" not in groove

    thread = by_kind["thread"]
    assert thread["callout"] == "1/4-20 UNC-2B"
    assert thread["dimensions"]["diameter_in"] == 0.25
    assert thread["threads_per_inch"] == 20
    assert thread["series"] == "UNC"
    assert thread["thread_class"] == "2B"
    assert "thread_form" not in thread
    assert any(row["field"] == "thread_form" for row in thread["blank_fields"])
    thread_symbol = describe_symbol(thread["callout"])
    assert thread_symbol["known"] is True
    assert "B1.1" in thread_symbol["citation"]

    diameters = {
        callout["text"]: callout
        for callout in reading["callouts"]
        if callout["symbol"] == "diameter"
    }
    assert set(diameters) == {"\u23001.250", "\u23000.750"}
    assert diameters["\u23001.250"]["value"] == 1.25
    assert diameters["\u23000.750"]["value"] == 0.75
    assert diameters["\u23001.250"]["feature"] is False
    assert "2.1" in diameters["\u23001.250"]["citation"]
    assert "no hole feature was added" in diameters["\u23001.250"]["note"]

    plain = [callout["text"] for callout in reading["callouts"] if callout["symbol"] is None]
    assert plain == [".125", ".060"]
    assert all(callout["feature"] is False for callout in reading["callouts"])

    assert {feature["kind"] for feature in reading["features"]}.isdisjoint(
        {"hole", "plate", "countersink", "counterbore", "chamfer"}
    )
    assert reading["unknown_symbols"] == []
    degree = describe_symbol("\u00b0")
    assert degree["known"] is True
    assert "4-41" in degree["citation"]
    chamfer = describe_symbol("CHAMFER")
    assert chamfer["known"] is False
    assert chamfer["meaning"] is None

    cylinders = [row["diameter_in"] for row in reading["geometry"]["cylinders"]]
    assert reading["geometry"]["units"] == "inch"
    assert cylinders == [1.25, 0.75]
    assert reading["geometry"]["plane_count"] == 1
    assert reading["assembly"]["leaf_parts"] == ["PRACTICE-TURNED"]
    assert reading["assembly"]["assemblies"] == []
    unreadable = " ".join(reading["unreadable"])
    assert "not holes" in unreadable
    assert "No thread callout in the STEP file" in unreadable
    assert "No groove callout in the STEP file" in unreadable
    assert "not read as a face operation" in unreadable
    assert "No face callout in the PDF" not in unreadable
    assert "No thread designation in the PDF" not in unreadable
    assert reading["needs_machining"] is False
    assert reading["practiced_on_shared_drive"] is False
    notes = " ".join(reading["notes"])
    assert "BB1013" in notes
    assert "rest of the shared drive has not" in notes
    assert "PRACTICE" not in notes

    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["needs_machining"] is True
    assert result["quote_done"] is False
    assert result["operation_count"] is None
    assert result["posted"] is False
    assert result["shop_rate_per_hour"] is None
    assert result["setup_time_min"] is None
    assert result["item_operations"] == []
    assert result["missing"] == ["operation_count", "run_time", "setup_time"]
    assert [op["name"] for op in result["operations"]] == ["grooving"]
    grooving = result["operations"][0]
    assert grooving["operation_code"] is None
    assert grooving["machine"] == "lathe-unspecified"
    assert grooving["run_time_min"] is None
    assert grooving["feature_ids"] == ["read-2"]
    assert {row["kind"] for row in result["unresolved_features"]} == {"face", "thread"}
    quote_notes = " ".join(result["notes"])
    assert "which one is not specified" in quote_notes
    assert "Thread form is missing" in quote_notes
    assert "machine not supplied" in quote_notes
    assert "Not posted" in quote_notes

    times = attach_machining_times({"weld_minutes": 2.0}, takeoff)
    assert times["weld_minutes"] == 2.0
    assert times["machining"]["quote_done"] is False
    assert times["machining"]["needs_machining"] is True
    assert times["machining"]["posted"] is False
    assert times["machining"]["missing"] == ["operation_count", "run_time", "setup_time"]


def test_typed_cycle_on_the_practice_groove_does_not_finish_the_quote():
    reading = apply_drawing_reading({}, _PDF, _STEP)["machining_reading"]
    result = quote_machining_features(
        reading["features"],
        operation_cycle_times={"lathe-unspecified:grooving:0.125": 4.0},
        features_source="drawing",
    )
    assert result["operations"][0]["run_time_min"] == 4.0
    assert result["operations"][0]["run_time_source"] == "cycle_override"
    assert result["operations"][0]["operation_code"] is None
    assert result["setup_time_min"] is None
    assert result["operation_count"] is None
    assert result["item_operations"] == []
    assert result["shop_rate_per_hour"] is None
    assert result["quote_done"] is False
    assert result["missing"] == ["operation_count", "run_time", "setup_time"]
