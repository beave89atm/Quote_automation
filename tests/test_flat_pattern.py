"""Flat pattern from a test chart row. The shop file stays empty.

The row below is fixture data for the arithmetic. It is not a Kannon
press-brake value and it is not written into config/press_brake_bends.csv.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from secturafab.bend_op import BEND_COUNT_NOT_SET
from secturafab.flat_pattern import (
    BendChartRow,
    _extract_bend_count,
    allowance_and_deduction,
    chart_path,
    evaluate_formed,
    load_bend_chart,
)
from secturafab.pdf_only import plan_pdf_only_part

# Fixture only. Not shop data.
FIXTURE_ROW = BendChartRow(
    material="A36",
    thickness_in=0.25,
    inside_radius_in=0.25,
    punch_radius_in=0.25,
    die_opening_in=2.0,
    method="k",
    value=0.5,
)
K = 0.5
THICKNESS = 0.25
INSIDE_RADIUS = 0.25
# 90° BA = (pi/2) * (IR + K*T). BD = 2*(IR+T) - BA.
BEND_ALLOWANCE = (math.pi / 2.0) * (INSIDE_RADIUS + K * THICKNESS)
BEND_DEDUCTION = 2.0 * (INSIDE_RADIUS + THICKNESS) - BEND_ALLOWANCE


def _chart():
    return (FIXTURE_ROW,)


def test_bend_counts_from_text_callouts():
    none = _extract_bend_count("PLATE\n1/4\nA36\nPLATE SIZE 4.00 X 6.00")
    one = _extract_bend_count("BEND UP 90 DEG")
    two = _extract_bend_count("BEND UP 90 DEG\nBEND DOWN 90 DEG")
    assert none.count == 0 and none.flag is None
    assert none.source == "no bend callouts"
    assert one.count == 1 and one.flag is None
    assert one.source == "UP/DOWN callouts"
    assert two.count == 2 and two.flag is None
    assert two.source == "UP/DOWN callouts"
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
    assert counted.source == "bend lines"
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
    assert plan.notes[-1].startswith("FLAG: formed part — ")
    assert "signals conflict" in plan.notes[-1]
    assert "explicit count=2" in plan.notes[-1]
    assert "UP/DOWN callouts=1" in plan.notes[-1]


def test_shipped_bend_chart_has_no_data_rows():
    path = chart_path()
    text = path.read_text(encoding="utf-8")
    assert path == Path("config/press_brake_bends.csv").resolve() or path.name == (
        "press_brake_bends.csv"
    )
    assert load_bend_chart() == ()
    assert "# A36,0.250,0.250,0.250,2.000,k,0.446" in text
    assert "EXAMPLE ONLY" in text
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert stripped.startswith("material,")


def test_commented_example_row_is_not_loaded(tmp_path: Path):
    copy = tmp_path / "press_brake_bends.csv"
    copy.write_text(chart_path().read_text(encoding="utf-8"), encoding="utf-8")
    assert load_bend_chart(copy) == ()


def test_one_bend_inside_flat_matches_hand_allowance(monkeypatch):
    monkeypatch.setattr("secturafab.flat_pattern.load_bend_chart", _chart)
    text = "\n".join(
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
    flat = evaluate_formed(text, material="A36", thickness_in=0.25)
    assert flat is not None and flat.flag is None
    assert flat.developed_length_in == pytest.approx(2.0 + 3.0 + BEND_ALLOWANCE)
    assert flat.width_in == pytest.approx(6.0)
    plan = plan_pdf_only_part(text=text, title="FORMED BRACKET")
    assert plan.route == "refuse"
    assert plan.bend_count is None
    assert plan.flats_from_chart is False
    assert plan.notes[-1] == f"FLAG: bend count — {BEND_COUNT_NOT_SET}"
    assert "calculator bends 1" in plan.line_note
    assert "not the line bend count" in plan.line_note
    assert "convention inside" in plan.line_note
    assert "legs 2, 3 in" in plan.line_note
    assert "thickness 0.25 in" in plan.line_note
    assert "inside radius 0.25 in" in plan.line_note
    assert "bend allowance" in plan.line_note
    assert "bend deduction" in plan.line_note
    assert "method=k" in plan.line_note
    assert "value=0.5" in plan.line_note
    assert "config/press_brake_bends.csv" in plan.line_note
    assert "FLAG: formed part" not in " ".join(plan.notes)
    allowance, deduction = allowance_and_deduction(
        FIXTURE_ROW,
        thickness_in=THICKNESS,
        inside_radius_in=INSIDE_RADIUS,
    )
    assert allowance == pytest.approx(BEND_ALLOWANCE)
    assert deduction == pytest.approx(BEND_DEDUCTION)


def test_two_bend_mold_line_flat_matches_hand_deduction(monkeypatch):
    monkeypatch.setattr("secturafab.flat_pattern.load_bend_chart", _chart)
    text = "\n".join(
        [
            "PLATE",
            "1/4",
            "A36",
            "2 BENDS",
            "BEND UP 90 DEG",
            "BEND DOWN 90 DEG",
            "INSIDE RADIUS 0.25",
            "DIMENSIONS MOLD LINE",
            "LEG 1.50",
            "LEG 4.00",
            "LEG 1.50",
            "WIDTH 8.00",
        ]
    )
    flat = evaluate_formed(text, material="A36", thickness_in=0.25)
    assert flat is not None and flat.developed_length_in == pytest.approx(
        1.5 + 4.0 + 1.5 - 2.0 * BEND_DEDUCTION
    )
    plan = plan_pdf_only_part(text=text, title="FORMED BRACKET")
    assert plan.route == "refuse"
    assert plan.bend_count is None
    assert plan.length_in == pytest.approx(flat.developed_length_in)
    assert "calculator bends 2" in plan.line_note
    assert "convention mold-line" in plan.line_note
    assert "legs 1.5, 4, 1.5 in" in plan.line_note
    assert "bend deduction" in plan.line_note
    assert "FLAG: formed part" not in " ".join(plan.notes)


def test_outside_convention_matches_mold_line(monkeypatch):
    monkeypatch.setattr("secturafab.flat_pattern.load_bend_chart", _chart)
    shared = [
        "PLATE",
        "1/4",
        "A36",
        "1 BEND",
        "BEND UP 90 DEG",
        "INSIDE RADIUS 0.25",
        "LEG 2.00",
        "LEG 3.00",
        "WIDTH 6.00",
    ]
    outside = plan_pdf_only_part(
        text="\n".join([*shared, "DIMENSIONS OUTSIDE"]),
        title="BRACKET",
    )
    mold = plan_pdf_only_part(
        text="\n".join([*shared, "DIMENSIONS MOLD-LINE"]),
        title="BRACKET",
    )
    assert outside.length_in == pytest.approx(2.0 + 3.0 - BEND_DEDUCTION)
    assert mold.length_in == pytest.approx(outside.length_in)


def test_two_chart_rows_do_not_pick_tooling(monkeypatch):
    other = BendChartRow(
        material="A36",
        thickness_in=0.25,
        inside_radius_in=0.25,
        punch_radius_in=0.25,
        die_opening_in=1.5,
        method="k",
        value=0.4,
    )
    monkeypatch.setattr(
        "secturafab.flat_pattern.load_bend_chart",
        lambda *a, **k: (FIXTURE_ROW, other),
    )
    text = "\n".join(
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
    plan = plan_pdf_only_part(text=text, title="FORMED BRACKET")
    assert plan.route == "refuse"
    assert "more than one press brake chart row" in plan.notes[-1]
    assert "not picking a tooling row" in plan.notes[-1]


def test_empty_chart_flags_missing_row():
    text = "\n".join(
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
    plan = plan_pdf_only_part(text=text, title="FORMED BRACKET")
    assert plan.route == "refuse"
    assert plan.notes[-1].startswith("FLAG: formed part — ")
    assert "no press brake chart row" in plan.notes[-1]
    assert "A36" in plan.notes[-1]
    decision = evaluate_formed(text, material="A36", thickness_in=0.25, chart=())
    assert decision is not None
    assert decision.developed_length_in is None
    assert decision.flag is not None
    assert "no press brake chart row" in decision.flag
