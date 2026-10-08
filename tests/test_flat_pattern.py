"""Kyle's flat-pattern formulas. K = 0.33 comes from shop config.

The guide's published figures are checked to 1e-6. The code keeps full
precision and the line note is the six-decimal display.
"""

from __future__ import annotations

import pytest

from quote_core.config import load_shop_rates
from secturafab.flat_formula import Bend, bend_math, flat_length_in
from secturafab.flat_pattern import _extract_bend_count, evaluate_formed
from secturafab.pdf_only import plan_pdf_only_part

_GUIDE = dict(radius_in=0.125, angle_deg=90.0, thickness_in=0.125, k_factor=0.33)


def _guide_bends(count: int, **overrides) -> tuple[Bend, ...]:
    fields = dict(_GUIDE)
    fields.update(overrides)
    return tuple(Bend(**fields) for _ in range(count))


def _outside_text(*extra: str) -> str:
    return "\n".join(
        [
            "PLATE",
            "0.125",
            "A36",
            *extra,
        ]
    )


def test_shop_k_factor_is_0_33():
    assert load_shop_rates().flat_pattern_k_factor == pytest.approx(0.33)


def test_guide_single_90_outside_bend():
    """Outside legs 2 and 3, T = R = 0.125, K = 0.33."""
    worked = bend_math(0.125, 90.0, 0.125, 0.33)
    assert worked.bend_allowance_in == pytest.approx(0.261145, abs=1e-6)
    assert worked.outside_setback_in == pytest.approx(0.250000, abs=1e-6)
    assert worked.bend_deduction_in == pytest.approx(0.238855, abs=1e-6)
    length = flat_length_in((2.0, 3.0), _guide_bends(1), basis="outside")
    assert length == pytest.approx(4.761145, abs=1e-6)
    plan = plan_pdf_only_part(
        text=_outside_text(
            "1 BEND",
            "BEND UP 90 DEG",
            "INSIDE RADIUS 0.125",
            "DIMENSIONS OUTSIDE",
            "LEG 2.000",
            "LEG 3.000",
            "WIDTH 6.00",
        ),
        title="FORMED BRACKET",
    )
    assert plan.route == "image_files"
    assert plan.length_in == pytest.approx(4.761145, abs=1e-6)
    assert plan.width_in == pytest.approx(6.0)
    assert plan.bend_count == 1
    assert plan.operations == ("Profile", "Bend")
    assert "basis outside" in plan.line_note
    assert "K=0.33 assumed" in plan.line_note
    assert "BA 0.261145 in" in plan.line_note
    assert "BD 0.238855 in" in plan.line_note
    assert "sum 5.000000" in plan.line_note
    assert "flat length 4.761145 in" in plan.line_note
    assert "Bend NumberOfBends = 1" in plan.line_note
    assert "θ 90°" in plan.line_note


def test_guide_four_identical_90_bends():
    """Outside chain total 12. Four bends. total BD 0.955420, FL 11.044580."""
    worked = bend_math(0.125, 90.0, 0.125, 0.33)
    total_bd = 4.0 * worked.bend_deduction_in
    length = flat_length_in((12.0,), _guide_bends(4), basis="outside")
    assert total_bd == pytest.approx(0.955420, abs=1e-6)
    assert length == pytest.approx(11.044580, abs=1e-6)
    assert length == pytest.approx(11.045, abs=5e-4)


def test_tangent_basis_adds_allowance():
    worked = bend_math(0.125, 90.0, 0.125, 0.33)
    length = flat_length_in((2.0, 3.0), _guide_bends(1), basis="tangent")
    assert length == pytest.approx(5.0 + worked.bend_allowance_in, abs=1e-12)
    plan = plan_pdf_only_part(
        text=_outside_text(
            "1 BEND",
            "BEND UP 90 DEG",
            "INSIDE RADIUS 0.125",
            "TANGENT LENGTHS",
            "LEG 2.000",
            "LEG 3.000",
            "WIDTH 6.00",
        ),
        title="FORMED BRACKET",
    )
    assert plan.route == "image_files"
    assert plan.length_in == pytest.approx(length, abs=1e-12)
    assert "basis tangent" in plan.line_note


def test_included_135_is_a_45_degree_bend():
    """Included 135° is θ = 45°. Outside legs 2 and 3."""
    worked = bend_math(0.125, 45.0, 0.125, 0.33)
    length = flat_length_in((2.0, 3.0), _guide_bends(1, angle_deg=45.0), basis="outside")
    assert length == pytest.approx(5.0 - worked.bend_deduction_in, abs=1e-12)
    assert worked.angle_deg == pytest.approx(45.0)
    plan = plan_pdf_only_part(
        text=_outside_text(
            "1 BEND",
            "BEND UP",
            "INCLUDED ANGLE 135",
            "INSIDE RADIUS 0.125",
            "DIMENSIONS OUTSIDE",
            "LEG 2.000",
            "LEG 3.000",
            "WIDTH 6.00",
        ),
        title="FORMED BRACKET",
    )
    assert plan.route == "image_files"
    assert plan.bend_count == 1
    assert plan.length_in == pytest.approx(length, abs=1e-9)
    assert "θ 45°" in plan.line_note
    assert "bend angle is not 90" not in " ".join(plan.notes)


def test_opposite_direction_bends_both_count():
    worked = bend_math(0.125, 90.0, 0.125, 0.33)
    length = flat_length_in((2.0, 1.0, 3.0), _guide_bends(2), basis="outside")
    assert length == pytest.approx(6.0 - 2.0 * worked.bend_deduction_in, abs=1e-12)
    plan = plan_pdf_only_part(
        text=_outside_text(
            "2 BENDS",
            "BEND UP 90 DEG",
            "BEND DOWN 90 DEG",
            "INSIDE RADIUS 0.125",
            "DIMENSIONS OUTSIDE",
            "LEG 2.000",
            "LEG 1.000",
            "LEG 3.000",
            "WIDTH 4.00",
        ),
        title="CHANNEL",
    )
    assert plan.route == "image_files"
    assert plan.bend_count == 2
    assert plan.length_in == pytest.approx(length, abs=1e-9)
    assert plan.line_note.count("BD ") == 2


def test_dimensioned_jog_is_two_bends_plus_the_straight():
    worked = bend_math(0.125, 90.0, 0.125, 0.33)
    length = flat_length_in((2.0, 0.5, 3.0), _guide_bends(2), basis="outside")
    assert length == pytest.approx(5.5 - 2.0 * worked.bend_deduction_in, abs=1e-12)
    plan = plan_pdf_only_part(
        text=_outside_text(
            "2 BENDS",
            "BEND UP 90 DEG",
            "BEND DOWN 90 DEG",
            "INSIDE RADIUS 0.125",
            "DIMENSIONS OUTSIDE",
            "LEG 2.000",
            "JOG 0.500",
            "LEG 3.000",
            "WIDTH 4.00",
        ),
        title="JOGGLE",
    )
    assert plan.route == "image_files"
    assert plan.bend_count == 2
    assert plan.length_in == pytest.approx(length, abs=1e-9)
    assert "segments 2, 0.5, 3 in" in plan.line_note


def test_k_override_from_config_changes_the_length(tmp_path, monkeypatch):
    cfg = tmp_path / "shop_rates.yaml"
    cfg.write_text(
        "\n".join(
            [
                "app: {}",
                "weld: {}",
                "fitup: {}",
                "materials:",
                "  carbon_steel_default_grade: A36",
                "  flat_pattern_k_factor: 0.40",
                "",
            ]
        )
    )
    monkeypatch.setattr("quote_core.config.DEFAULT_RATES_PATH", cfg)
    worked = bend_math(0.125, 90.0, 0.125, 0.40)
    plan = plan_pdf_only_part(
        text=_outside_text(
            "1 BEND",
            "BEND UP 90 DEG",
            "INSIDE RADIUS 0.125",
            "DIMENSIONS OUTSIDE",
            "LEG 2.000",
            "LEG 3.000",
            "WIDTH 6.00",
        ),
        title="FORMED BRACKET",
    )
    assert plan.length_in == pytest.approx(5.0 - worked.bend_deduction_in, abs=1e-12)
    assert plan.length_in != pytest.approx(4.761145, abs=1e-4)
    assert "K=0.4 assumed" in plan.line_note


def test_bend_counts_from_text_callouts():
    none = _extract_bend_count("PLATE\n1/4\nA36\nPLATE SIZE 4.00 X 6.00")
    one = _extract_bend_count("BEND UP 90 DEG")
    two = _extract_bend_count("BEND UP 90 DEG\nBEND DOWN 90 DEG")
    assert none.count == 0 and none.flag is None
    assert none.source == "no bend callouts"
    assert one.count == 1 and one.flag is None
    assert "callout_bend_up_down" in one.source
    assert two.count == 2 and two.flag is None
    plan0 = plan_pdf_only_part(
        text="PLATE\n1/4\nA36\nPLATE SIZE 4.00 X 6.00",
        title="LIFT LOG GUSSET",
    )
    assert plan0.route == "image_files"
    assert plan0.bend_count == 0
    assert plan0.operations == ()
    assert "bend count 0" in plan0.line_note


def test_bend_line_labels_count_when_the_text_layer_names_them():
    counted = _extract_bend_count("FRONT VIEW\nBEND LINE\nBEND LINE")
    assert counted.count == 2
    assert counted.source == "label_bend_line"
    assert counted.flag is None


def test_conflicting_bend_signals_flag_instead_of_guessing():
    counted = _extract_bend_count("2 BENDS\nBEND UP 90 DEG")
    assert counted.count is None
    assert counted.flag is not None
    assert "signals conflict" in counted.flag
    plan = plan_pdf_only_part(
        text="\n".join(
            [
                "PLATE",
                "1/4",
                "A36",
                "PLATE SIZE 4.00 X 6.00",
                "2 BENDS",
                "BEND UP 90 DEG",
            ]
        ),
        title="FORMED BRACKET",
    )
    assert plan.route == "refuse"
    assert plan.notes[-1].startswith("FLAG: bend count — ")
    assert "signals conflict" in plan.notes[-1]


@pytest.mark.parametrize(
    ("extra", "reason"),
    [
        ("HEM", "hem is not a simple bend"),
        ("FOLDED EDGE", "hem is not a simple bend"),
        ("BEND UP 180 DEG", "hem is not a simple bend"),
        ("JOG", "offset/jog is not dimensioned"),
        ("OFFSET", "offset/jog is not dimensioned"),
        ("ROLL FORMED", "rolled or large-radius section is not a straight bend"),
        ("LARGE RADIUS", "rolled or large-radius section is not a straight bend"),
        ("CONE", "cone or cylinder is not a straight-bend flat"),
        ("CYLINDER", "cone or cylinder is not a straight-bend flat"),
        ("STRETCHED FORM", "compound or stretched form is not a straight-bend flat"),
        ("NOT PARALLEL", "bend lines are not parallel; needs a 2D unfold"),
        (
            "\n".join(
                [
                    "1 BEND",
                    "135 DEG",
                    "INSIDE RADIUS 0.125",
                    "DIMENSIONS OUTSIDE",
                    "LEG 2.000",
                    "LEG 3.000",
                    "WIDTH 6.00",
                ]
            ),
            "angle convention can't be determined",
        ),
        (
            "\n".join(
                [
                    "1 BEND",
                    "BEND UP 90 DEG",
                    "DIMENSIONS OUTSIDE",
                    "LEG 2.000",
                    "LEG 3.000",
                    "WIDTH 6.00",
                ]
            ),
            "inside radius was not on the drawing",
        ),
        (
            "\n".join(
                [
                    "1 BEND",
                    "BEND UP 90 DEG",
                    "INSIDE RADIUS 0.125",
                    "DIMENSIONS INSIDE",
                    "LEG 2.000",
                    "LEG 3.000",
                    "WIDTH 6.00",
                ]
            ),
            "inside dimensions were not converted to tangent or outside",
        ),
        (
            "\n".join(
                [
                    "1 BEND",
                    "BEND UP 90 DEG",
                    "INSIDE RADIUS 0.125",
                    "DIMENSIONS INSIDE",
                    "DIMENSIONS OUTSIDE",
                    "LEG 2.000",
                    "LEG 3.000",
                    "WIDTH 6.00",
                ]
            ),
            "dimension basis is ambiguous",
        ),
        (
            "\n".join(
                [
                    "2 BENDS",
                    "BEND UP 90 DEG",
                    "BEND UP 90 DEG",
                    "HORIZONTAL BEND",
                    "VERTICAL BEND",
                    "INSIDE RADIUS 0.125",
                    "DIMENSIONS OUTSIDE",
                    "LEG 1.000",
                    "LEG 2.000",
                    "LEG 1.000",
                    "WIDTH 4.00",
                ]
            ),
            "bends are not in a single plane",
        ),
    ],
)
def test_formed_checks_run_before_the_formula(extra: str, reason: str, monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula hook called")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = "\n".join(["PLATE", "0.125", "A36", extra])
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.flag == reason
    assert decision.developed_length_in is None
