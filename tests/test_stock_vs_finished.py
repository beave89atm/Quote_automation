"""Stock versus finished chooses lathe or mill. It does not invent a time or a bar."""

from __future__ import annotations

from quote_core.machining_quote import process_assignment_with_code, quote_machining_features
from quote_core.machining_read import compare_stock_to_finished, read_stated_stock


def _cylinder(diameter: float, origin: list[float], direction: list[float] | None = None) -> dict:
    row = {"diameter_in": diameter}
    if direction is not None:
        row["axis_origin_in"] = origin
        row["axis_direction"] = direction
    return row


def _round_geometry() -> dict:
    return {
        "units": "inch",
        "cylinders": [
            _cylinder(2.0, [0, 0, 0], [0, 0, 1]),
            _cylinder(1.25, [0, 0, 1], [0, 0, -1]),
            _cylinder(0.75, [0, 0, 2], [0, 0, 1]),
        ],
    }


def test_largest_finished_diameter_is_not_stock():
    assignment = compare_stock_to_finished(
        _round_geometry(),
        features=[{"kind": "groove", "dimensions": {"width_in": 0.1}}],
        callouts=[{"symbol": "diameter", "value": 2.0, "feature": False}],
        assembly={"leaf_parts": ["RING"]},
    )
    assert assignment is not None
    assert assignment["operation_justified"] is False
    assert assignment["family"] is None
    assert assignment["stock"]["form"] == "unknown"
    assert assignment["stock"]["stated"] is False
    assert assignment["stock"]["guessed"] is False
    assert "diameter_in" not in assignment["stock"]
    assert assignment["stock"].get("diameter_in") != 2.0
    assert "not guessed" in assignment["evidence"]
    assert "largest finished" not in assignment["evidence"]
    assert assignment["finished"]["shape"] == "round"
    assert assignment["finished"]["concentric"] is True
    assert assignment["finished"]["diameters_in"] == [0.75, 1.25, 2.0]
    assert "one centerline" in assignment["evidence"]
    assert "No operation was justified" in assignment["evidence"]
    assert "does not supply a run time" in assignment["evidence"]
    coded = process_assignment_with_code(assignment)
    assert coded["operation_code"] is None
    assert coded["run_time_min"] is None
    assert coded["setup_time_min"] is None
    assert coded["shop_rate_per_hour"] is None
    assert coded["posted"] is False
    dumped = str(coded)
    for code in ("op_lathe", "op_lathe2", "op_mill"):
        assert code not in dumped


def test_a_guessed_bar_is_refused():
    assignment = compare_stock_to_finished(
        _round_geometry(),
        features=[{"kind": "groove", "dimensions": {"width_in": 0.1}}],
        callouts=[{"symbol": "diameter", "feature": False}],
        assembly={"leaf_parts": ["RING"]},
        stated_stock={
            "form": "bar",
            "stated": False,
            "guessed": True,
            "diameter_in": 2.0,
            "evidence": "largest finished outside diameter",
        },
    )
    assert assignment is not None
    assert assignment["stock"]["form"] == "unknown"
    assert assignment["stock"]["guessed"] is False
    assert "diameter_in" not in assignment["stock"]
    assert assignment["operation_justified"] is False
    assert process_assignment_with_code(assignment)["operation_code"] is None


def test_stated_round_stock_smaller_finished_round_is_turning():
    stated = read_stated_stock("ROUND BAR ⌀2.500")
    assert stated["form"] == "bar"
    assert stated["stated"] is True
    assert stated["guessed"] is False
    assert stated["diameter_in"] == 2.5
    assert "ROUND BAR" in stated["evidence"]
    assignment = compare_stock_to_finished(
        _round_geometry(),
        features=[{"kind": "groove", "dimensions": {"width_in": 0.1}}],
        callouts=[{"symbol": "diameter", "feature": False}],
        assembly={"leaf_parts": ["RING"]},
        stated_stock=stated,
    )
    assert assignment is not None
    assert assignment["operation_justified"] is True
    assert assignment["family"] == "lathe"
    assert assignment["stock"]["form"] == "bar"
    assert assignment["stock"]["diameter_in"] == 2.5
    assert assignment["stock"]["guessed"] is False
    assert max(assignment["finished"]["diameters_in"]) < assignment["stock"]["diameter_in"]
    assert "Lathe 2 was not chosen" in assignment["evidence"]
    assert "does not supply a run time" in assignment["evidence"]
    coded = process_assignment_with_code(assignment)
    assert coded["operation_code"] == "op_lathe"
    assert coded["run_time_min"] is None
    assert "stock length" in coded["run_blank_reason"]
    assert coded["setup_time_min"] == 75.0
    assert coded["shop_rate_per_hour"] is None
    assert coded["posted"] is False
    assert "op_lathe2" not in str(coded["operation_code"])


def test_finished_round_equal_to_stated_stock_is_not_turning():
    assignment = compare_stock_to_finished(
        _round_geometry(),
        features=[{"kind": "groove"}],
        callouts=[{"symbol": "diameter", "feature": False}],
        assembly={"leaf_parts": ["RING"]},
        stated_stock={
            "form": "bar",
            "stated": True,
            "guessed": False,
            "diameter_in": 2.0,
            "evidence": "ROUND BAR ⌀2.000",
        },
    )
    assert assignment is not None
    assert assignment["stock"]["diameter_in"] == 2.0
    assert assignment["operation_justified"] is False
    assert process_assignment_with_code(assignment)["operation_code"] is None


def test_bar_word_without_a_diameter_does_not_invent_one():
    stated = read_stated_stock("MATERIAL\nROUND BAR\n1018")
    assert stated["form"] == "bar"
    assert stated["guessed"] is False
    assert "diameter_in" not in stated
    assignment = compare_stock_to_finished(
        _round_geometry(),
        features=[{"kind": "groove"}],
        callouts=[{"symbol": "diameter", "feature": False}],
        assembly={"leaf_parts": ["RING"]},
        stated_stock=stated,
    )
    assert assignment["stock"]["form"] == "bar"
    assert "diameter_in" not in assignment["stock"]
    assert assignment["operation_justified"] is False


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
    assert assignment is not None
    assert assignment["finished"]["shape"] == "unknown"
    assert assignment["finished"]["concentric"] is False
    assert assignment["stock"]["form"] == "unknown"
    assert assignment["operation_justified"] is False
    assert process_assignment_with_code(assignment)["operation_code"] is None


def test_finished_plate_envelope_is_not_stock():
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
    assert assignment["operation_justified"] is True
    assert assignment["family"] == "mill"
    assert assignment["finished"]["shape"] == "plate"
    assert assignment["finished"]["envelope_in"] == [9.625, 2.625, 0.5]
    assert assignment["stock"]["form"] == "unknown"
    assert assignment["stock"]["guessed"] is False
    assert "thickness_in" not in assignment["stock"]
    assert assignment["stock"].get("thickness_in") != 0.5
    assert "countersink" in assignment["evidence"]
    assert "not turning" in assignment["evidence"]
    assert "does not supply a run time" in assignment["evidence"]
    coded = process_assignment_with_code(assignment)
    assert coded["operation_code"] == "op_mill"
    assert coded["run_time_min"] is None
    assert coded["setup_time_min"] is None


def test_stated_plate_keeps_the_sheet_thickness():
    stated = read_stated_stock(
        'SLEEVE PLATE COUNTERBORE: L: 9.63" H: 2.625"\nW:0.5", MTL: A572 GR. 50\n0.5" A572 GR. 50'
    )
    assert stated["form"] == "plate"
    assert stated["guessed"] is False
    assert stated["thickness_in"] == 0.5
    assert stated["length_in"] == 9.63
    assert stated["width_in"] == 2.625
    assert "A572" in stated["evidence"]
    assert "SLEEVE PLATE" in stated["evidence"]
    assignment = compare_stock_to_finished(
        {
            "units": "inch",
            "cylinders": [_cylinder(0.63, [1, 1, 0], [0, 0, 1])],
            "vertex_box_in": [9.625, 2.625, 0.5],
        },
        features=[{"kind": "countersink", "stated_machine": False}],
        assembly={"leaf_parts": ["PLATE"]},
        stated_stock=stated,
    )
    assert assignment["stock"]["form"] == "plate"
    assert assignment["stock"]["thickness_in"] == 0.5
    assert assignment["stock"]["length_in"] == 9.63
    assert assignment["stock"]["width_in"] == 2.625
    assert assignment["stock"]["guessed"] is False
    assert "A572" in assignment["stock"]["evidence"]
    assert assignment["operation_justified"] is True
    assert process_assignment_with_code(assignment)["operation_code"] == "op_mill"


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


def test_diameters_without_an_axis_are_not_a_guessed_bar():
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
    assert assignment["stock"]["form"] == "unknown"
    assert assignment["stock"]["guessed"] is False
    assert "diameter_in" not in assignment["stock"]
    assert assignment["finished"]["shape"] == "round"
    assert assignment["finished"]["diameters_in"] == [0.75, 1.25]
    assert "does not place the cylinder axes" in assignment["evidence"]
    assert assignment["operation_justified"] is False
    assert process_assignment_with_code(assignment)["operation_code"] is None


def test_zinc_plate_is_not_stock():
    stated = read_stated_stock("ZINC PLATE\nSEALING RING")
    assert stated["form"] == "unknown"
    assert stated["guessed"] is False
    assert "thickness_in" not in stated
    assert "diameter_in" not in stated
