"""Kyle's machining calculator: stock-versus-finished minutes, no dollar rate."""

from __future__ import annotations

import math

import pytest

from quote_core.machining_calculator import (
    LATHE_ROUGH_IN3_PER_MIN,
    MILL_ROUGH_IN3_PER_MIN,
    times_for_justified_operation,
)
from quote_core.machining_quote import attach_machining_times, process_assignment_with_code
from quote_core.machining_read import compare_stock_to_finished


def _plate_assignment():
    return compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [
                {
                    "diameter_in": 0.5,
                    "axis_origin_in": [1, 1, 0],
                    "axis_direction": [0, 0, 1],
                }
            ],
            "vertex_box_in": [10.0, 4.0, 0.5],
        },
        features=[{"kind": "countersink", "stated_machine": False}],
        assembly={"leaf_parts": ["PLATE"]},
        stated_stock={
            "form": "plate",
            "stated": True,
            "guessed": False,
            "thickness_in": 0.75,
            "length_in": 10.0,
            "width_in": 4.0,
            "evidence": "PLATE",
        },
    )


def test_thicker_plate_uses_the_mill_rate_and_the_pad():
    assignment = _plate_assignment()
    assert assignment["operation_justified"] is True
    coded = process_assignment_with_code(
        assignment,
        features=[{"kind": "countersink"}],
    )
    removed = 0.75 * 10.0 * 4.0 - 0.5 * 10.0 * 4.0
    assert removed == pytest.approx(10)
    cut = removed * 1.0 / MILL_ROUGH_IN3_PER_MIN
    cycle = (cut + 0.15 + 4.0 + 2.0) * 1.15
    assert coded["operation_code"] == "op_mill"
    assert coded["calculator"]["cubic_inches_removed"] == pytest.approx(removed)
    assert coded["calculator"]["cut_minutes"] == pytest.approx(cut)
    assert coded["run_time_min"] == pytest.approx(cycle)
    assert coded["setup_time_min"] == 75.0
    assert coded["calculator"]["setup_hours"] == 1.25
    assert coded["calculator"]["program_hours_not_setup"] == 2.0
    assert coded["calculator"]["removal_in3_per_min"] == 3.0
    assert coded["calculator"]["taper_rates_not_used_in3_per_min"] == {"40": 1.5, "30": 0.4}
    assert coded["shop_rate_per_hour"] is None
    assert coded["posted"] is False
    assert cut != pytest.approx(removed / 1.5)

    feature = {"kind": "countersink", "machine": "mill", "dimensions": {"diameter_in": 0.5}}
    times = attach_machining_times(
        {"weld_minutes": 1.0},
        {
            "machining_features": [feature],
            "needs_machining": True,
            "machining_reading": {
                "process_from_stock": assignment,
                "features": [{"kind": "countersink"}],
                "callouts": [],
            },
        },
    )
    machining = times["machining"]
    assert times["weld_minutes"] == 1.0
    assert machining["quote_done"] is True
    assert machining["missing"] == []
    assert machining["operation_count"] == 1
    assert machining["operations"][0]["run_time_min"] == pytest.approx(cycle)
    assert machining["operations"][0]["run_time_source"] == "calculator"
    assert machining["setup_time_min"] == 75.0
    assert machining["shop_rate_per_hour"] is None
    assert machining["posted"] is False


def test_typed_cycle_overrides_run_and_leaves_setup():
    assignment = _plate_assignment()
    feature = {
        "kind": "countersink",
        "machine": "mill",
        "dimensions": {"diameter_in": 0.5},
        "cycle_time_min": 4.5,
    }
    times = attach_machining_times(
        {},
        {
            "machining_features": [feature],
            "needs_machining": True,
            "machining_reading": {
                "process_from_stock": assignment,
                "features": [{"kind": "countersink"}],
                "callouts": [],
            },
        },
    )
    machining = times["machining"]
    assert machining["operations"][0]["run_time_min"] == 4.5
    assert machining["operations"][0]["run_time_source"] == "cycle_override"
    assert machining["setup_time_min"] == 75.0
    assert machining["quote_done"] is True
    assert machining["shop_rate_per_hour"] is None
    assert machining["posted"] is False


def test_bar_volume_uses_the_lathe_rate():
    removed = math.pi / 4.0 * (2.5 ** 2 * 6.0 - 2.0 ** 2 * 5.5)
    times = times_for_justified_operation(
        {
            "operation_justified": True,
            "operation_code": "op_lathe",
            "stock": {
                "form": "bar",
                "stated": True,
                "guessed": False,
                "diameter_in": 2.5,
                "length_in": 6.0,
            },
            "finished": {"shape": "round", "diameters_in": [2.0], "length_in": 5.5},
        },
        material_grade="1018",
    )
    cut = removed * 1.0 / LATHE_ROUGH_IN3_PER_MIN
    assert times["calculator"]["cubic_inches_removed"] == pytest.approx(removed)
    assert times["run_time_min"] == pytest.approx((cut + 6.15) * 1.15)
    assert times["setup_time_min"] == 75.0
    assert times["shop_rate_per_hour"] is None
    assert times["calculator"]["removal_in3_per_min"] == 4.0


def test_lathe_2_uses_the_same_bar_formula():
    plain = times_for_justified_operation(
        {
            "operation_justified": True,
            "operation_code": "op_lathe",
            "stock": {
                "form": "bar",
                "stated": True,
                "diameter_in": 2.0,
                "length_in": 4.0,
            },
            "finished": {"shape": "round", "diameters_in": [1.5], "length_in": 4.0},
        }
    )
    second = times_for_justified_operation(
        {
            "operation_justified": True,
            "operation_code": "op_lathe2",
            "stock": {
                "form": "bar",
                "stated": True,
                "diameter_in": 2.0,
                "length_in": 4.0,
            },
            "finished": {"shape": "round", "diameters_in": [1.5], "length_in": 4.0},
        }
    )
    assert second["run_time_min"] == pytest.approx(plain["run_time_min"])
    assert second["setup_time_min"] == plain["setup_time_min"]
    assert second["shop_rate_per_hour"] is None


def test_repeat_setup_is_a_quarter_hour_and_grade_304_slows_the_cut():
    times = times_for_justified_operation(
        {
            "operation_justified": True,
            "operation_code": "op_mill",
            "stock": {
                "form": "plate",
                "stated": True,
                "thickness_in": 0.75,
                "length_in": 10.0,
                "width_in": 4.0,
            },
            "finished": {"shape": "plate", "envelope_in": [10.0, 4.0, 0.5]},
        },
        repeat=True,
        material_grade="304",
        callouts=[{"symbol": "plus_minus", "value": 0.001, "unit": "inch"}],
    )
    removed = 10.0
    cut = removed * 1.8 / MILL_ROUGH_IN3_PER_MIN
    allowances = 0.15 + (0.25 + 0.35) * cut + 4.0 + 2.0
    assert times["setup_time_min"] == 15.0
    assert times["calculator"]["program_hours_not_setup"] == 0.0
    assert times["run_time_min"] == pytest.approx((cut + allowances) * 1.15)
    assert times["shop_rate_per_hour"] is None


def test_matching_plate_does_not_turn_allowances_into_a_run_time():
    times = times_for_justified_operation(
        {
            "operation_justified": True,
            "operation_code": "op_mill",
            "stock": {
                "form": "plate",
                "stated": True,
                "thickness_in": 0.5,
                "length_in": 9.63,
                "width_in": 2.625,
            },
            "finished": {"shape": "plate", "envelope_in": [9.625, 2.625, 0.5]},
        },
        features=[{"kind": "countersink"}],
    )
    assert times["calculator"]["cubic_inches_removed"] == 0.0
    assert times["run_time_min"] is None
    assert "cubic inches removed are 0" in times["run_blank_reason"]
    assert times["setup_time_min"] == 75.0
    assert times["shop_rate_per_hour"] is None


def test_tube_has_setup_and_no_volume_rule():
    times = times_for_justified_operation(
        {
            "operation_justified": True,
            "operation_code": "op_lathe",
            "stock": {"form": "tube", "stated": True, "diameter_in": 2.0, "length_in": 6.0},
            "finished": {"shape": "round", "diameters_in": [1.5], "length_in": 6.0},
        }
    )
    assert times["run_time_min"] is None
    assert "Tube has no volume formula" in times["run_blank_reason"]
    assert times["setup_time_min"] == 75.0
    assert times["shop_rate_per_hour"] is None


def test_unknown_stock_does_not_receive_calculator_times():
    times = times_for_justified_operation(
        {
            "operation_justified": True,
            "operation_code": "op_mill",
            "stock": {"form": "unknown", "stated": False, "guessed": False},
            "finished": {"shape": "plate", "envelope_in": [9.0, 2.0, 0.5]},
        }
    )
    assert times["run_time_min"] is None
    assert times["setup_time_min"] is None
    assert times["shop_rate_per_hour"] is None


def test_several_shop_ops_do_not_split_one_cycle():
    assignment = _plate_assignment()
    features = [
        {"kind": "countersink", "machine": "mill", "dimensions": {"diameter_in": 0.5}},
        {
            "kind": "hole",
            "machine": "mill",
            "dimensions": {"diameter_in": 0.25, "tolerance": "loose"},
        },
    ]
    times = attach_machining_times(
        {},
        {
            "machining_features": features,
            "needs_machining": True,
            "machining_reading": {
                "process_from_stock": assignment,
                "features": features,
                "callouts": [],
            },
        },
    )
    machining = times["machining"]
    assert machining["operation_count"] == 2
    assert all(op["run_time_min"] is None for op in machining["operations"])
    assert machining["setup_time_min"] == 75.0
    assert machining["quote_done"] is False
    assert "not split" in " ".join(machining["notes"])
    assert machining["shop_rate_per_hour"] is None
