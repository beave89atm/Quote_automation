"""Synthetic drawings for the bend-reader failure patterns.

Every string and PDF in here is invented. No customer part numbers,
names, or drawing text.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from quote_core.bend_conventions import detect_bends
from secturafab.flat_pattern import evaluate_formed, read_bends
from secturafab.pdf_only import plan_pdf_only_file, plan_pdf_only_part

_PLATE = "\n".join(
    [
        "SAMPLE PLATE",
        "PLATE",
        "0.250",
        "A36",
        "PLATE SIZE 4.00 X 6.00",
    ]
)


def _centerline(p1, p2, dashes: str = "[12 3 2 3] 0") -> dict:
    return {"dashes": dashes, "items": [("l", p1, p2)]}


def test_degree_sign_and_fraction_radii_parse():
    leading = read_bends("UP 90° R.13")
    assert leading.bend_count == 1
    assert leading.thetas == (90.0,)
    assert leading.angle_flag is None
    assert leading.radii_in == pytest.approx((0.13,))
    assert leading.radii_in != pytest.approx((13.0,))

    spaced = read_bends("UP 90° R .25")
    assert spaced.bend_count == 1
    assert spaced.radii_in == pytest.approx((0.25,))
    assert spaced.radii_in != pytest.approx((25.0,))

    fraction = read_bends("DOWN 90° R 1/8")
    assert fraction.bend_count == 1
    assert fraction.thetas == (90.0,)
    assert fraction.radii_in == pytest.approx((0.125,))
    assert fraction.radii_in != pytest.approx((1.0,))

    three_eighths = read_bends("UP 90° R 3/8")
    assert three_eighths.radii_in == pytest.approx((0.375,))
    assert three_eighths.radii_in != pytest.approx((3.0,))

    half = read_bends("DOWN 90° R1/2")
    assert half.radii_in == pytest.approx((0.5,))

    dotted = read_bends("BEND RADIUS....3/8")
    assert dotted.radii_in == pytest.approx((0.375,))


def test_bend_note_angle_ignores_tolerance_and_chamfer():
    text = "\n".join(
        [
            "UP 90° R.13",
            "DOWN 90° R.13",
            "30°",
            "45° X .06 CHAMFER",
            "ANGULAR: ±1°",
            "INCLUDED 110° REF",
        ]
    )
    found = read_bends(text)
    assert found.bend_count == 2
    assert found.angle_flag is None
    assert found.thetas == (90.0, 90.0)
    assert found.radii_in == pytest.approx((0.13, 0.13))


def test_hole_centerlines_do_not_create_or_contradict_a_bend():
    holes = [
        _centerline((0, 0), (400, 0)),
        _centerline((0, 40), (400, 40)),
        _centerline((0, 80), (400, 80)),
        _centerline((0, 120), (400, 120)),
        _centerline((200, 0), (220, 400)),
    ]
    formed = detect_bends("UP 90° R.13\nDOWN 90° R.13", holes)
    assert formed.count == 2
    assert formed.flag is None
    assert formed.plane_flag is None
    assert "signals conflict" not in (formed.flag or "")

    flat = detect_bends(_PLATE, holes)
    assert flat.count == 0
    assert flat.flag is None
    assert flat.plane_flag is None

    # A bend note has to sit on the line before that line can corroborate.
    blocks = [
        {"text": "UP 90° R.13", "dir": (1, 0), "bbox": (70, 60, 180, 74)},
        {"text": "DOWN 90° R.13", "dir": (1, 0), "bbox": (70, 100, 190, 114)},
    ]
    near = [
        _centerline((72, 68), (400, 68)),
        _centerline((72, 108), (400, 108)),
        _centerline((0, 400), (500, 400)),
        _centerline((300, 0), (300, 500)),
    ]
    agreed = detect_bends(
        "UP 90° R.13\nDOWN 90° R.13",
        near,
        text_blocks=blocks,
    )
    assert agreed.count == 2
    assert agreed.flag is None
    assert agreed.plane_flag is None
    assert agreed.geometry_count == 2
    assert any("geom_center_line" in bend.corroboration for bend in agreed.bends)


def test_bend_note_direction_flags_two_planes():
    blocks = [
        {"text": "UP 90° R.13", "dir": (1, 0), "bbox": (70, 60, 160, 74)},
        {"text": "DOWN 90° R.13", "dir": (0, -1), "bbox": (200, 40, 214, 140)},
    ]
    found = detect_bends("UP 90° R.13\nDOWN 90° R.13", text_blocks=blocks)
    assert found.count == 2
    assert found.plane_flag == "bends are not in a single plane"


def test_fraction_dash_and_boilerplate_are_not_bend_counts():
    fraction = detect_bends("1/4 BEND RADIUS")
    assert fraction.count != 4
    assert fraction.flag == "a bend radius does not give a count"
    assert read_bends("1/4 BEND RADIUS").radii_in == pytest.approx((0.25,))

    stacked = detect_bends("1\n4 BEND RADIUS")
    assert stacked.count != 4
    assert stacked.flag == "a bend radius does not give a count"

    with_notes = read_bends("UP 90°\nDOWN 90°\n1/4 BEND RADIUS")
    assert with_notes.bend_count == 2
    assert with_notes.count_flag is None
    assert with_notes.thetas == (90.0, 90.0)
    assert with_notes.radii_in == pytest.approx((0.25, 0.25))

    stacked_note = read_bends("UP 90°\n1\n4 BEND RADIUS")
    assert stacked_note.bend_count == 1
    assert stacked_note.radii_in == pytest.approx((0.25,))

    one_dash = detect_bends("-1 BEND DOWN 90° R.25")
    assert one_dash.count == 1
    assert one_dash.bends[0].convention_id == "callout_bend_up_down"
    assert read_bends("-1 BEND DOWN 90° R.25").radii_in == pytest.approx((0.25,))

    both_dashes = detect_bends("-1 BEND DOWN 90° R.25\n-2 BEND UP 90° R.25")
    assert both_dashes.count is None
    assert both_dashes.flag == "dash bend notes are separate options, not one bend count"

    labels = detect_bends("UP 90° R 1/8\nUP 90° R 1/8\n0.74 TYP (BEND LINE)\n(BEND LINE)")
    assert labels.count == 2
    assert labels.flag is None
    assert "label_bend_line" not in {bend.convention_id for bend in labels.bends}

    bare_line = detect_bends("BEND LINE\nBEND LINE")
    assert bare_line.count == 2
    assert bare_line.bends[0].convention_id == "label_bend_line"


def test_flat_plate_boilerplate_and_centerlines_stay_flat():
    text = "\n".join(
        [
            _PLATE,
            "BEND ANGLE = 90° (UNLESS OTHERWISE NOTED)",
            "ANGULAR: BEND 1°",
            "MASTER CYLINDER BRACKET",
        ]
    )
    holes = [
        _centerline((0, 0), (360, 0)),
        _centerline((80, 0), (80, 360)),
        _centerline((0, 200), (400, 200), "[12 2 2 2 2 2] 0"),
    ]
    found = detect_bends(text, holes)
    assert found.count == 0
    assert found.flag is None
    assert found.plane_flag is None

    plan = plan_pdf_only_part(text=text, title="SAMPLE PLATE", drawings=holes)
    assert plan.route == "image_files"
    assert plan.bend_count == 0
    assert "cone or cylinder" not in " ".join(plan.notes)
    assert "not in a single plane" not in " ".join(plan.notes)
    assert "bend count 0" in plan.line_note


def test_corrupt_pdf_bytes_stay_unclassified(tmp_path: Path):
    stub = tmp_path / "stub.pdf"
    stub.write_bytes(b"%PDF")
    plan = plan_pdf_only_file(stub, title="SAMPLE PLATE")
    assert plan.route == "unclassified"
    assert plan.notes == ()


def test_scanned_and_rotated_pages_flag_unreadable(tmp_path: Path):
    blank = tmp_path / "scan.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(fitz.Rect(72, 72, 360, 240))
    doc.save(blank)
    doc.close()
    scanned = plan_pdf_only_file(blank, title="SAMPLE PLATE")
    assert scanned.route == "refuse"
    assert scanned.route != "unclassified"
    assert "unreadable, needs human review" in scanned.notes[-1]
    assert scanned.bend_count != 0

    rotated = tmp_path / "rotated.pdf"
    doc = fitz.open()
    page = doc.new_page()
    for index, char in enumerate("ABCDEFGHIJKLMNOP"):
        page.insert_text((72, 72 + index * 14), char, fontsize=10)
    doc.save(rotated)
    doc.close()
    garbled = plan_pdf_only_file(rotated, title="SAMPLE PLATE")
    assert garbled.route == "refuse"
    assert "unreadable, needs human review" in garbled.notes[-1]

    readable = tmp_path / "plate.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "SAMPLE PLATE")
    page.insert_text((72, 90), "PLATE")
    page.insert_text((72, 108), "0.250")
    page.insert_text((72, 126), "A36")
    page.insert_text((72, 144), "PLATE SIZE 4.00 X 6.00")
    doc.save(readable)
    doc.close()
    plate = plan_pdf_only_file(readable, title="SAMPLE PLATE")
    assert "unreadable" not in " ".join(plate.notes)
    assert plate.route == "image_files"
    assert plate.bend_count == 0


def test_printed_flat_pattern_size_is_used_and_formula_is_the_fallback(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran even though the drawing printed the flat")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = "\n".join(
        [
            "SAMPLE BRACKET",
            "PLATE",
            "0.125",
            "A36",
            "UP 90° R.13",
            "UP 90° R.13",
            "FLAT PATTERN",
            "10.50 X 4.25",
        ]
    )
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.flag is None
    assert decision.length_source == "drawing flat pattern"
    assert decision.width_in == pytest.approx(10.50)
    assert decision.developed_length_in == pytest.approx(4.25)
    assert decision.bend_count == 2
    assert "source drawing flat pattern" in decision.line_note
    assert "K=" not in decision.line_note

    plan = plan_pdf_only_part(text=text, title="SAMPLE BRACKET")
    assert plan.route == "image_files"
    assert plan.flat_source == "drawing flat pattern"
    assert plan.flats_from_formula is False
    assert plan.width_in == pytest.approx(10.50)
    assert plan.length_in == pytest.approx(4.25)
    assert plan.bend_count == 2
    assert "source drawing flat pattern" in plan.line_note

    fraction = evaluate_formed(
        "\n".join(
            [
                "PLATE",
                "0.125",
                "A36",
                "DOWN 90° R 1/8",
                "DEVELOPED VIEW",
                "12-1/2 X 3-1/4",
            ]
        ),
        thickness_in=0.125,
    )
    assert fraction is not None
    assert fraction.length_source == "drawing flat pattern"
    assert fraction.width_in == pytest.approx(12.5)
    assert fraction.developed_length_in == pytest.approx(3.25)


def test_formula_still_runs_when_legs_thickness_and_radius_are_readable():
    text = "\n".join(
        [
            "PLATE",
            "0.125",
            "A36",
            "1 BEND",
            "BEND UP 90 DEG",
            "INSIDE RADIUS 0.125",
            "DIMENSIONS OUTSIDE",
            "LEG 2.000",
            "LEG 3.000",
            "WIDTH 6.00",
        ]
    )
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.flag is None
    assert decision.length_source == "formula"
    assert decision.developed_length_in == pytest.approx(4.761145, abs=1e-6)
    assert "K=0.33 assumed" in decision.line_note


def test_missing_flat_size_and_missing_legs_flags(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran without the legs")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    decision = evaluate_formed(
        "\n".join(
            [
                "PLATE",
                "0.125",
                "A36",
                "UP 90° R.13",
                "DIMENSIONS OUTSIDE",
            ]
        ),
        thickness_in=0.125,
    )
    assert decision is not None
    assert decision.flag is not None
    assert decision.developed_length_in is None


def test_formed_evidence_with_no_count_is_not_a_flat_plate():
    # A flat-pattern view with no bend count used to fall through as a flat plate
    # once thickness and L/W parsed. The printed blank is not a license to do that.
    text = "\n".join(
        [
            _PLATE,
            "FLAT PATTERN VIEW",
            "10.50 X 4.25",
        ]
    )
    decision = evaluate_formed(text, thickness_in=0.25)
    assert decision is not None
    assert decision.developed_length_in is None
    assert decision.flag == "formed evidence but the bend count is 0 or unknown"

    plan = plan_pdf_only_part(text=text, title="SAMPLE PLATE")
    assert plan.route == "refuse"
    assert plan.bend_count != 0
    assert "bend count 0" not in " ".join(plan.notes)
    assert "Image Files" not in " ".join(plan.notes)
    assert "formed evidence but the bend count is 0 or unknown" in " ".join(plan.notes)


def test_pdf_note_rotation_reaches_the_plan(tmp_path: Path):
    crossed = tmp_path / "two-axes.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "PLATE")
    page.insert_text((72, 90), "0.125")
    page.insert_text((72, 108), "A36")
    page.insert_text((72, 140), "UP 90° R.13")
    page.insert_text((220, 220), "DOWN 90° R.13", rotate=90)
    doc.save(crossed)
    doc.close()
    plan = plan_pdf_only_file(crossed, title="SAMPLE BRACKET")
    assert plan.route == "refuse"
    assert "bends are not in a single plane" in " ".join(plan.notes)
