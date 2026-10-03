"""Stock versus finished chooses lathe or mill. It does not invent a time."""

from __future__ import annotations

from quote_core.machining_quote import process_assignment_with_code, quote_machining_features
from quote_core.machining_read import compare_stock_to_finished


def _cylinder(diameter: float, origin: list[float], direction: list[float] | None = None) -> dict:
    row = {"diameter_in": diameter}
    if direction is not None:
        row["axis_origin_in"] = origin
        row["axis_direction"] = direction
    return row


def test_concentric_steps_assign_lathe_and_not_lathe_2():
    assignment = compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [
                _cylinder(2.0, [0, 0, 0], [0, 0, 1]),
                _cylinder(1.25, [0, 0, 1], [0, 0, -1]),
                _cylinder(0.75, [0, 0, 2], [0, 0, 1]),
            ],
        },
        features=[{"kind": "groove", "dimensions": {"width_in": 0.1}}],
        callouts=[{"symbol": "diameter", "value": 2.0, "feature": False}],
        assembly={"leaf_parts": ["RING"]},
    )
    assert assignment is not None
    assert assignment["family"] == "lathe"
    assert assignment["stated_on_sheet"] is False
    assert assignment["stock"]["form"] == "round"
    assert assignment["stock"]["diameter_in"] == 2.0
    assert assignment["finished"]["concentric"] is True
    assert "Lathe 2 was not chosen" in assignment["evidence"]
    assert "does not supply a run time" in assignment["evidence"]
    coded = process_assignment_with_code(assignment)
    assert coded["operation_code"] == "op_lathe"
    assert coded["run_time_min"] is None
    assert coded["setup_time_min"] is None
    assert coded["shop_rate_per_hour"] is None
    assert coded["posted"] is False
    assert "op_lathe2" not in str(coded["operation_code"])


def test_spaced_hole_axes_are_not_a_turned_stack():
    assignment = compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [
                _cylinder(0.25, [0, 0, 0], [0, 0, 1]),
                _cylinder(0.5, [2, 0, 0], [0, 0, 1]),
            ],
            "vertex_box_in": None,
        },
        features=[{"kind": "hole"}],
        callouts=[],
        assembly={"leaf_parts": ["PLATE"]},
    )
    assert assignment is None


def test_prismatic_plate_countersink_assigns_mill():
    assignment = compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [_cylinder(0.63, [1, 1, 0], [0, 0, 1])],
            "vertex_box_in": [9.625, 2.625, 0.5],
        },
        features=[{"kind": "countersink", "stated_machine": False}],
        assembly={"leaf_parts": ["PLATE"], "assemblies": ["WRAPPER"]},
    )
    assert assignment is not None
    assert assignment["family"] == "mill"
    assert assignment["stock"]["form"] == "plate"
    assert assignment["stock"]["thickness_in"] == 0.5
    assert "countersink" in assignment["evidence"]
    assert "not turned" in assignment["evidence"]
    coded = process_assignment_with_code(assignment)
    assert coded["operation_code"] == "op_mill"
    assert coded["run_time_min"] is None
    assert coded["setup_time_min"] is None


def test_several_leaves_are_not_one_process():
    assignment = compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [
                _cylinder(1.0, [0, 0, 0], [0, 0, 1]),
                _cylinder(0.5, [0, 1, 0], [0, 0, 1]),
            ],
        },
        features=[{"kind": "groove"}],
        assembly={"leaf_parts": ["SHAFT", "ARM"], "assemblies": ["WELDMENT"]},
    )
    assert assignment is None


def test_a_named_machine_is_not_replaced():
    assignment = compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [
                _cylinder(2.0, [0, 0, 0], [0, 0, 1]),
                _cylinder(1.0, [0, 1, 0], [0, 0, 1]),
            ],
        },
        features=[{"kind": "groove", "machine": "lathe2", "stated_machine": True}],
        assembly={"leaf_parts": ["PART"]},
    )
    assert assignment is None
    quoted = quote_machining_features(
        [{"kind": "groove", "machine": "lathe2", "dimensions": {"width_in": 0.1}}]
    )
    assert quoted["item_operations"][0]["operation_code"] == "op_lathe2"
    assert quoted["setup_time_min"] is None
    assert quoted["shop_rate_per_hour"] is None
    assert quoted["quote_done"] is False


def test_diameters_without_an_axis_on_one_product_are_turned_steps():
    assignment = compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [{"diameter_in": 1.25}, {"diameter_in": 0.75}],
        },
        features=[{"kind": "face"}, {"kind": "groove"}],
        callouts=[{"symbol": "diameter", "feature": False}],
        assembly={"leaf_parts": ["PRACTICE-TURNED"]},
    )
    assert assignment is not None
    assert assignment["family"] == "lathe"
    assert "does not place the cylinder axes" in assignment["evidence"]
    assert process_assignment_with_code(assignment)["operation_code"] == "op_lathe"
