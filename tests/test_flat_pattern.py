"""Flat length comes from the formula hook. The hook ships unset.

The stub below is fixture code. It is not shop math and it is not what
``secturafab/flat_formula.py`` returns.
"""

from __future__ import annotations

import pytest

from secturafab.flat_formula import flat_length_in
from secturafab.flat_pattern import FORMULA_NOT_SET, _extract_bend_count, evaluate_formed
from secturafab.pdf_only import plan_pdf_only_part

_ONE_BEND = "\n".join(
    [
        "PLATE",
        "1/4",
        "A36",
        "1 BEND",
        "BEND UP 90 DEG",
        "INSIDE RADIUS 0.25",
        "DIMENSIONS INSIDE",
        "LEG 2.00",
        "LEG 3.00",
        "WIDTH 6.00",
    ]
)


def _stub_flat_length(legs_in, thickness_in, inside_radius_in, bend_count):
    """Fixture only. Not a K-factor and not shop logic."""
    return sum(legs_in) + 0.1 * bend_count


def _install_stub(monkeypatch):
    seen: dict = {}

    def _stub(legs_in, thickness_in, inside_radius_in, bend_count):
        seen["args"] = (legs_in, thickness_in, inside_radius_in, bend_count)
        return _stub_flat_length(
            legs_in, thickness_in, inside_radius_in, bend_count
        )

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _stub)
    return seen


def test_shipped_formula_is_unset():
    assert flat_length_in((2.0, 3.0), 0.25, 0.25, 1) is None


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
    assert plan.bend_count is None
    assert plan.notes[-1].startswith("FLAG: bend count — ")
    assert "signals conflict" in plan.notes[-1]


def test_unset_formula_flags_before_a_quote():
    plan = plan_pdf_only_part(text=_ONE_BEND, title="FORMED BRACKET")
    assert plan.route == "refuse"
    assert plan.length_in is None
    assert plan.flats_from_formula is False
    assert plan.notes[-1] == f"FLAG: formed part — {FORMULA_NOT_SET}"
    decision = evaluate_formed(_ONE_BEND, thickness_in=0.25)
    assert decision is not None
    assert decision.flag == FORMULA_NOT_SET
    assert decision.developed_length_in is None


def test_stub_formula_feeds_the_image_files_line(monkeypatch):
    seen = _install_stub(monkeypatch)
    flat = evaluate_formed(_ONE_BEND, thickness_in=0.25)
    assert flat is not None and flat.flag is None
    assert seen["args"] == ((2.0, 3.0), 0.25, 0.25, 1)
    assert flat.developed_length_in == pytest.approx(5.1)
    assert flat.width_in == pytest.approx(6.0)
    assert flat.bend_count == 1
    plan = plan_pdf_only_part(text=_ONE_BEND, title="FORMED BRACKET")
    assert plan.route == "image_files"
    assert plan.flats_from_formula is True
    assert plan.length_in == pytest.approx(5.1)
    assert plan.width_in == pytest.approx(6.0)
    assert plan.bend_count == 1
    assert plan.operations == ("Profile", "Bend")
    assert "legs 2, 3 in" in plan.line_note
    assert "thickness 0.25 in" in plan.line_note
    assert "inside radius 0.25 in" in plan.line_note
    assert "bend count 1" in plan.line_note
    assert "flat length 5.1 in" in plan.line_note
    assert "width 6 in from the drawing" in plan.line_note
    assert "Bend NumberOfBends = 1" in plan.line_note
    assert "convention inside" in plan.line_note
    assert plan.line_note in plan.notes


def test_three_bend_stub_uses_every_leg(monkeypatch):
    seen = _install_stub(monkeypatch)
    text = "\n".join(
        [
            "PLATE",
            "1/4",
            "A36",
            "3 BENDS",
            "BEND UP 90 DEG",
            "BEND DOWN 90 DEG",
            "BEND UP 90 DEG",
            "INSIDE RADIUS 0.25",
            "DIMENSIONS INSIDE",
            "LEG 1.00",
            "LEG 2.00",
            "LEG 2.00",
            "LEG 1.00",
            "WIDTH 5.00",
        ]
    )
    plan = plan_pdf_only_part(text=text, title="CHANNEL")
    assert seen["args"][0] == (1.0, 2.0, 2.0, 1.0)
    assert seen["args"][3] == 3
    assert plan.bend_count == 3
    assert plan.length_in == pytest.approx(6.3)
    assert plan.width_in == pytest.approx(5.0)
    assert "Bend NumberOfBends = 3" in plan.line_note


@pytest.mark.parametrize(
    ("extra", "reason"),
    [
        ("HEM", "hem is not a simple bend"),
        ("JOG", "offset/jog is not a simple bend"),
        ("OFFSET", "offset/jog is not a simple bend"),
        (
            "\n".join(
                [
                    "1 BEND",
                    "BEND 45 DEG",
                    "INSIDE RADIUS 0.25",
                    "DIMENSIONS INSIDE",
                    "LEG 2.00",
                    "LEG 3.00",
                    "WIDTH 6.00",
                ]
            ),
            "bend angle is not 90°",
        ),
        (
            "\n".join(
                [
                    "1 BEND",
                    "BEND UP 90 DEG",
                    "DIMENSIONS INSIDE",
                    "LEG 2.00",
                    "LEG 3.00",
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
                    "INSIDE RADIUS 0.25",
                    "DIMENSIONS INSIDE",
                    "DIMENSIONS OUTSIDE",
                    "LEG 2.00",
                    "LEG 3.00",
                    "WIDTH 6.00",
                ]
            ),
            "dimension convention is ambiguous",
        ),
        (
            "\n".join(
                [
                    "2 BENDS",
                    "BEND UP 90 DEG",
                    "BEND UP 90 DEG",
                    "HORIZONTAL BEND",
                    "VERTICAL BEND",
                    "INSIDE RADIUS 0.25",
                    "DIMENSIONS INSIDE",
                    "LEG 1.00",
                    "LEG 2.00",
                    "LEG 1.00",
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
    text = "\n".join(["PLATE", "1/4", "A36", extra])
    decision = evaluate_formed(text, thickness_in=0.25)
    assert decision is not None
    assert decision.flag == reason
    assert decision.developed_length_in is None
    plan = plan_pdf_only_part(text=text, title="FORMED BRACKET")
    assert plan.route == "refuse"
    assert reason in plan.notes[-1]
