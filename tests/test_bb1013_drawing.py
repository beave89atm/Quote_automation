"""BB1013, one customer drawing. Not a stand-in for the rest of the drive."""

from __future__ import annotations

from pathlib import Path

from quote_core.machining_quote import quote_machining_features
from quote_core.machining_read import apply_drawing_reading
from quote_core.machining_symbols import describe_symbol

_FIXTURE = Path(__file__).parent / "fixtures" / "bb1013"
_PDF = _FIXTURE / "BB1013.pdf"
_STEP = _FIXTURE / "BB1013-cut.step"


def test_bb1013_reads_only_the_callouts_on_the_drawing():
    takeoff = apply_drawing_reading({}, _PDF, _STEP)
    reading = takeoff["machining_reading"]
    features = {feature["callout"]: feature for feature in reading["features"]}
    assert takeoff["machining_features_source"] == "drawing"
    assert list(features) == ["18X 0.13", "6X THRU 0.20", "5052 .125"]

    small = features["18X 0.13"]
    assert small["kind"] == "hole"
    assert small["dimensions"]["diameter_in"] == 0.13
    assert small["dimensions"]["count"] == 18
    assert "depth_in" not in small["dimensions"]
    assert "tolerance" not in small
    assert small["diameter_symbol"]["known"] is True
    assert "2.1" in small["diameter_symbol"]["citation"]
    assert small["step_match"]["matches"] == 1
    assert abs(small["step_match"]["diameter_in"] - 0.13) < 0.001

    thru = features["6X THRU 0.20"]
    assert thru["kind"] == "hole"
    assert thru["dimensions"]["diameter_in"] == 0.2
    assert thru["dimensions"]["count"] == 6
    assert "depth_in" not in thru["dimensions"]
    assert any("THRU" in row["note"] for row in thru["blank_fields"])
    assert any(row["field"] == "tolerance" for row in thru["blank_fields"])
    assert thru["step_match"]["matches"] == 1
    assert abs(thru["step_match"]["diameter_in"] - 0.2) < 0.001

    plate = features["5052 .125"]
    assert plate["kind"] == "plate"
    assert plate["dimensions"]["thickness_in"] == 0.125

    kinds = {feature["kind"] for feature in reading["features"]}
    assert kinds == {"hole", "plate"}
    assert "thread" not in kinds
    assert "groove" not in kinds
    assert "face" not in kinds

    notes = {callout["text"]: callout for callout in reading["callouts"]}
    assert notes["4X 32.00"]["feature"] is False
    assert "no hole" in notes["4X 32.00"]["note"]
    assert notes["8X 14.00"]["feature"] is False
    assert notes["0.88"]["feature"] is False
    assert all(callout["feature"] is False for callout in reading["callouts"])

    assert reading["unknown_symbols"] == []
    degree = describe_symbol("°")
    assert degree["known"] is True
    assert degree["meaning"]
    assert "Y14.5-2018" in degree["citation"]

    unreadable = " ".join(reading["unreadable"])
    assert "FINISH is on the drawing" in unreadable
    assert "No thread designation in the PDF" in unreadable
    assert "No groove callout in the PDF" in unreadable
    assert "No face callout in the PDF" in unreadable
    assert "not holes" in unreadable
    assert reading["geometry"]["units"] == "inch"
    assert len(reading["geometry"]["cylinders"]) == 3
    assert reading["practiced_on_shared_drive"] is False
    assert any("rest of the shared drive has not" in note for note in reading["notes"])

    result = quote_machining_features(reading["features"], features_source="drawing")
    assert result["needs_machining"] is True
    assert result["quote_done"] is False
    assert result["operation_count"] is None
    assert result["operations"] == []
    assert result["setup_time_min"] is None
    assert result["item_operations"] == []
    assert result["posted"] is False
    assert result["purchased_components"] == []
    assert result["excluded_features"][0]["kind"] == "plate"
    assert {row["kind"] for row in result["unresolved_features"]} == {"hole"}
    assert result["missing"] == ["operation_count", "run_time", "setup_time"]
    assert "BB1013" in " ".join(result["notes"])
