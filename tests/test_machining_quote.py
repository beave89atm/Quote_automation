"""Machining feature quote — count, run time, setup, and the not-done gate.

Code shape is quote 121671-1 only (94273b6c-072d-4a44-9519-d0e8f5f0f391, OPEN-NEW).
Those stored times are not shop rates. Setup is fixedtime, not unit time / qty.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.db import Job
from app.services import recompute_from_items
from quote_core.machining_quote import (
    CODE_SOURCE_ID,
    CODE_SOURCE_QUOTE,
    attach_machining_times,
    carry_machining_inputs,
    is_machining_item_operation,
    is_quote_header_milling_laser,
    machining_html_items,
    quote_machining_features,
    read_line_operation,
    read_setup_fixedtime_hours,
    status_after_review,
)

# Observed on 121671-1. Quantity 4 makes stored UnitTime = fixedtime / 4.
# These numbers stay in the test. The estimator does not copy them.
_VERIFIED = {
    "op_lathe": {
        "equipment": "Lathe",
        "name": None,
        "fixedtime": 4.0,
        "unit_time": 1.0,
        "perunittime": 20.0,
        "setup": "Lathe-Setup",
        "run": "Lathe-Time",
        "field": "Per Unit Turning Time",
    },
    "op_lathe2": {
        "equipment": "Lathe 2",
        "name": None,
        "fixedtime": 1.5,
        "unit_time": 0.375,
        "perunittime": 10.0,
        "setup": "Lathe-Setup",
        "run": "Lathe-Time",
        "field": "Per Unit Turning Time",
    },
    "op_mill": {
        "equipment": "CNC Mill",
        "name": "Milling",
        "fixedtime": 3.0,
        "unit_time": 0.75,
        "perunittime": 10.0,
        "setup": "Milling-Setup",
        "run": "Milling-Time",
        "field": "Per Unit Milling Time",
    },
}


def _rows(code: str) -> tuple[dict, dict]:
    spec = _VERIFIED[code]
    shared = {
        "operation_code": code,
        "equipment": spec["equipment"],
        "OperationType": 10,
        "Quantity": 4,
        "Cost": 90,
        "Cost_Units": "hour",
    }
    if spec["name"]:
        shared["OperationName"] = spec["name"]
    setup = {
        **shared,
        "CalculatorName": spec["setup"],
        "CostCalcType": 6,
        "kind": "fixedtime",
        "fixedtime": spec["fixedtime"],
        "UnitTime": spec["unit_time"],
        "FieldName": None,
    }
    run = {
        **shared,
        "CalculatorName": spec["run"],
        "CostCalcType": 9,
        "kind": "perunittime",
        "perunittime": spec["perunittime"],
        "FieldName": spec["field"],
        "UnitTime": spec["perunittime"] / 60.0,
    }
    return setup, run


def _hole(diameter: float, **extra) -> dict:
    feature = {
        "kind": "hole",
        "machine": "mill",
        "tolerance": "loose",
        "dimensions": {"diameter_in": diameter, "depth_in": 1},
    }
    feature.update(extra)
    return feature


def test_source_is_only_quote_121671():
    src = Path(__import__("quote_core.machining_quote", fromlist=["x"]).__file__).read_text()
    assert CODE_SOURCE_QUOTE == "121671-1"
    assert CODE_SOURCE_ID == "94273b6c-072d-4a44-9519-d0e8f5f0f391"
    assert "1020249" not in src
    assert "116633" not in src
    assert "secturafab" not in src.lower()
    assert "shop_rate" in src
    for token in ("1020249", "116633", "Cost\": 90", "LabourRate"):
        assert token not in src


def test_verified_setup_is_fixedtime_not_divided_unit_time():
    for code, spec in _VERIFIED.items():
        setup, run = _rows(code)
        assert is_machining_item_operation(setup)
        read = read_line_operation(setup, run)
        assert read["operation_code"] == code
        assert read["equipment"] == spec["equipment"]
        assert read["operation_type"] == 10
        assert read["setup_fixedtime_hours"] == spec["fixedtime"]
        assert read["setup_fixedtime_hours"] != spec["unit_time"]
        assert read["setup_time_min"] == spec["fixedtime"] * 60.0
        assert read["run_perunittime_min"] == spec["perunittime"]
        assert read["shop_rate_per_hour"] is None
        assert read["posted"] is False
        dumped = json.dumps(read)
        assert "Cost" not in dumped
        assert "LabourRate" not in dumped
    mill = read_line_operation(*_rows("op_mill"))
    assert mill["operation_name"] == "Milling"
    lathe = read_line_operation(*_rows("op_lathe"))
    assert lathe["operation_name"] is None


def test_unit_time_alone_is_not_setup():
    setup, _run = _rows("op_lathe")
    del setup["fixedtime"]
    assert read_setup_fixedtime_hours(setup) is None
    read = read_line_operation(setup, _run)
    assert read["setup_fixedtime_hours"] is None
    assert read["setup_time_min"] is None
    assert read["run_perunittime_min"] == 20.0


def test_laser_header_milling_is_not_an_item_operation():
    header = {
        "OperationName": "Milling",
        "equipment": "Laser",
        "operation_code": "op_mill",
        "OperationType": 10,
        "fixedtime": 3,
        "Cost": 90,
    }
    assert is_quote_header_milling_laser(header)
    assert is_machining_item_operation(header) is False
    read = read_line_operation(header, header)
    assert read["operation_code"] is None
    assert read["setup_fixedtime_hours"] is None
    real = {
        "OperationName": "Milling",
        "equipment": "CNC Mill",
        "operation_code": "op_mill",
        "OperationType": 10,
    }
    assert is_machining_item_operation(real) is True
    assert is_machining_item_operation({"operation_code": "op_weld", "equipment": "Welding"}) is False
    assert is_machining_item_operation({"operation_code": "op_grind", "equipment": "Grind"}) is False


def test_operation_count_run_time_and_setup_time():
    result = quote_machining_features(
        [_hole(0.375, id="a"), _hole(0.375, id="b"), _hole(0.5, id="c")]
    )
    assert result["operation_count"] == 2
    assert [op["label"] for op in result["operations"]] == ["drill 0.375 in", "drill 0.5 in"]
    assert all(op["run_time_min"] is None for op in result["operations"])
    assert all(op["run_time_source"] == "missing" for op in result["operations"])
    assert result["setup_time_min"] is None
    assert result["needs_machining"] is True
    assert result["quote_done"] is False
    assert result["missing"] == ["run_time", "setup_time"]
    item = result["item_operations"][0]
    assert item["operation_code"] == "op_mill"
    assert item["equipment"] == "CNC Mill"
    assert item["operation_name"] == "Milling"
    assert item["operation_type"] == 10
    assert item["setup"]["cost_calc_type"] == 6
    assert item["setup"]["kind"] == "fixedtime"
    assert item["setup"]["fixedtime_hours"] is None
    assert item["setup"]["uses_stored_unit_time"] is False
    assert item["run"]["cost_calc_type"] == 9
    assert item["run"]["kind"] == "perunittime"
    assert item["run"]["field_name"] == "Per Unit Milling Time"
    assert item["run"]["time_min"] is None
    assert item["posted"] is False
    assert result["shop_rate_per_hour"] is None
    assert result["code_source"]["quote_number"] == "121671-1"
    assert "1020249" not in json.dumps(result)
    assert "116633" not in json.dumps(result)


def test_feature_quote_does_not_copy_121671_stored_times():
    result = quote_machining_features([_hole(0.375)])
    assert result["setup_time_min"] is None
    assert result["operations"][0]["run_time_min"] is None
    assert result["item_operations"][0]["setup"]["fixedtime_hours"] is None
    assert result["item_operations"][0]["run"]["time_min"] is None
    assert result["setup_time_min"] not in {4, 1.5, 3, 240, 90, 60}
    assert result["operations"][0]["run_time_min"] not in {20, 10}


def test_typed_cycle_overrides_blank_run_and_setup_still_blocks():
    result = quote_machining_features(
        [
            {
                "kind": "face",
                "machine": "mill",
                "dimensions": {"length_in": 4, "width_in": 4},
                "cycle_time_min": 4.5,
            }
        ]
    )
    assert result["operation_count"] == 1
    assert result["operations"][0]["run_time_min"] == 4.5
    assert result["operations"][0]["run_time_source"] == "cycle_override"
    assert result["item_operations"][0]["run"]["time_min"] == 4.5
    assert result["item_operations"][0]["setup"]["fixedtime_hours"] is None
    assert result["setup_time_min"] is None
    assert result["missing"] == ["setup_time"]
    assert result["quote_done"] is False


def test_each_missing_output_keeps_the_quote_not_done():
    unresolved = quote_machining_features([{"kind": "hole", "machine": "mill", "dimensions": {"diameter_in": 0.25}}])
    assert unresolved["operation_count"] is None
    assert "operation_count" in unresolved["missing"]
    assert unresolved["quote_done"] is False

    no_run = quote_machining_features([_hole(0.25)])
    assert no_run["operation_count"] == 1
    assert no_run["operations"][0]["run_time_min"] is None
    assert "run_time" in no_run["missing"]
    assert no_run["quote_done"] is False

    both = quote_machining_features(
        [_hole(0.25, cycle_time_min=2), _hole(0.5, id="other", cycle_time_min=3)]
    )
    assert both["operation_count"] == 2
    assert [op["run_time_min"] for op in both["operations"]] == [2, 3]
    assert both["item_operations"][0]["run"]["time_min"] == 5
    assert both["setup_time_min"] is None
    assert both["missing"] == ["setup_time"]
    assert both["quote_done"] is False

    forced = quote_machining_features([], needs_machining=True)
    assert forced["needs_machining"] is True
    assert forced["operation_count"] is None
    assert forced["missing"] == ["operation_count", "run_time", "setup_time"]
    assert forced["quote_done"] is False


def test_mill_and_lathe_stay_separate_codes():
    result = quote_machining_features(
        [
            {"kind": "face", "machine": "mill", "cycle_time_min": 1},
            {"kind": "groove", "equipment": "Lathe", "dimensions": {"width_in": 0.125}},
        ]
    )
    assert result["operation_count"] == 2
    codes = [op["operation_code"] for op in result["operations"]]
    assert codes == ["op_mill", "op_lathe"]
    assert [item["operation_code"] for item in result["item_operations"]] == ["op_mill", "op_lathe"]
    lathe = result["item_operations"][1]
    assert lathe["equipment"] == "Lathe"
    assert lathe["setup"]["calculator"] == "Lathe-Setup"
    assert lathe["run"]["calculator"] == "Lathe-Time"
    assert lathe["run"]["field_name"] == "Per Unit Turning Time"
    assert lathe["setup"]["time_min"] is None
    assert lathe["run"]["time_min"] is None


def test_lathe_2_uses_the_same_calculators():
    result = quote_machining_features(
        [{"kind": "groove", "machine": "lathe2", "dimensions": {"width_in": 0.1}}]
    )
    item = result["item_operations"][0]
    assert item["operation_code"] == "op_lathe2"
    assert item["equipment"] == "Lathe 2"
    assert item["setup"]["calculator"] == "Lathe-Setup"
    assert item["setup"]["cost_calc_type"] == 6
    assert item["run"]["calculator"] == "Lathe-Time"
    assert item["run"]["cost_calc_type"] == 9
    assert item["run"]["field_name"] == "Per Unit Turning Time"
    assert item["setup"]["fixedtime_hours"] is None


def test_unspecified_lathe_does_not_pick_a_code():
    result = quote_machining_features([{"kind": "groove", "dimensions": {"width_in": 0.1}}])
    assert result["operation_count"] == 1
    assert result["operations"][0]["operation_code"] is None
    assert result["item_operations"] == []
    assert result["quote_done"] is False
    assert "setup_time" in result["missing"]


def test_plate_over_three_quarters_is_purchased_not_a_machine_op():
    thick = quote_machining_features(
        [{"kind": "plate", "dimensions": {"thickness_in": 1.0}}]
    )
    assert thick["needs_machining"] is False
    assert thick["quote_done"] is True
    assert thick["operation_count"] == 0
    assert thick["operations"] == []
    assert thick["purchased_components"][0]["thickness_in"] == 1.0
    assert thick["item_operations"] == []

    at_limit = quote_machining_features(
        [{"kind": "plate", "dimensions": {"thickness_in": "3/4"}}]
    )
    assert at_limit["purchased_components"] == []
    assert at_limit["operations"] == []
    assert at_limit["needs_machining"] is False

    mixed = quote_machining_features(
        [
            {"kind": "plate", "dimensions": {"thickness_in": 1}},
            _hole(0.375),
        ]
    )
    assert mixed["operation_count"] == 1
    assert mixed["operations"][0]["name"] == "drill"
    assert len(mixed["purchased_components"]) == 1


def test_stock_volume_does_not_become_a_run_time():
    result = quote_machining_features(
        [
            {
                "kind": "face",
                "machine": "mill",
                "dimensions": {"length_in": 6, "width_in": 4, "depth_in": 0.1},
                "stock_volume_in3": 10,
                "finished_volume_in3": 6,
            }
        ]
    )
    assert result["operations"][0]["run_time_min"] is None
    assert any("Stock-minus-finished" in note for note in result["notes"])
    assert result["quote_done"] is False


def test_thread_cycle_is_not_split_across_drill_and_tap():
    result = quote_machining_features(
        [
            {
                "kind": "thread",
                "machine": "mill",
                "thread_form": "tap",
                "dimensions": {"diameter_in": 0.375},
                "cycle_time_min": 8,
            }
        ]
    )
    assert result["operation_count"] == 2
    assert [op["name"] for op in result["operations"]] == ["drill", "tap"]
    assert all(op["run_time_min"] is None for op in result["operations"])
    filled = quote_machining_features(
        [
            {
                "kind": "thread",
                "machine": "mill",
                "form": "tap",
                "dimensions": {"diameter_in": 0.375},
            }
        ],
        operation_cycle_times={"mill:drill:0.375": 3, "mill:tap:0.375": 2},
    )
    assert [op["run_time_min"] for op in filled["operations"]] == [3, 2]
    assert filled["setup_time_min"] is None
    assert filled["quote_done"] is False


def test_recompute_attaches_machining_and_leaves_weld_minutes():
    job = Job(title="pin", pdf_filename="pin.pdf", pdf_path="", efficiency_pct=100)
    job.set_takeoff({"items": [], "fitup_drivers": {"part_count": 0}})
    job.set_flags(["keep me"])
    recompute_from_items(job, [], machining_features=[_hole(0.375)])
    times = job.times()
    assert times["weld_minutes"] == 0.0
    assert times["machining"]["operation_count"] == 1
    assert times["machining"]["operations"][0]["run_time_min"] is None
    assert times["machining"]["setup_time_min"] is None
    assert times["machining"]["quote_done"] is False
    assert any(flag.startswith("needs_info: machining required but missing") for flag in job.flags())
    assert "keep me" in job.flags()


def test_recompute_without_features_does_not_add_machining():
    job = Job(title="weld", pdf_filename="weld.pdf", pdf_path="", efficiency_pct=100)
    job.set_takeoff({"items": [], "fitup_drivers": {"part_count": 0}})
    job.set_flags([])
    recompute_from_items(job, [])
    assert "machining" not in job.times()
    assert job.flags() == []


def test_carry_and_attach_only_when_features_are_present():
    carried = carry_machining_inputs(
        {"machining_features": [_hole(0.25)], "library": {"folder": "old"}},
        {"items": []},
    )
    assert carried["machining_features"][0]["kind"] == "hole"
    plain = {"weld_minutes": 3.0}
    assert attach_machining_times(plain, {"items": []}) == plain
    attached = attach_machining_times(plain, carried)
    assert attached["weld_minutes"] == 3.0
    assert attached["machining"]["operation_count"] == 1
    assert attached["machining"]["quote_done"] is False


def test_accepted_status_stays_not_done_when_machining_is_incomplete():
    blocked = {
        "machining": {
            "needs_machining": True,
            "quote_done": False,
            "missing": ["setup_time"],
        }
    }
    assert status_after_review("review", "accepted", blocked) == "needs_info"
    assert status_after_review("review", "accepted", {"weld_minutes": 5}) == "accepted"
    assert status_after_review("error", None, {}) == "review"


def test_html_shows_the_three_numbers_beside_weld_minutes():
    html = machining_html_items(
        {
            "machining": {
                "operation_count": 2,
                "operations": [
                    {"label": "drill 0.375 in", "run_time_min": None},
                    {"label": "drill 0.5 in", "run_time_min": 3},
                ],
                "setup_time_min": None,
            }
        }
    )
    assert "Machining operations: 2" in html
    assert "drill 0.375 in: —" in html
    assert "drill 0.5 in: 3" in html
    assert "Machining setup: —" in html
    empty = machining_html_items({"weld_minutes": 1})
    assert "Machining operations: —" in empty
    assert "Machining run time: —" in empty
    assert "Machining setup: —" in empty
