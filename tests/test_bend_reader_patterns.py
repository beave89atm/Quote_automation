"""Synthetic drawings for the bend-reader failure patterns.

Every string and PDF in here is invented. No customer part numbers,
names, or drawing text.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from quote_core.bend_conventions import detect_bends
from secturafab.flat_pattern import _bare_inches, _join_stacked_fraction_blocks, evaluate_formed, read_bends
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


def test_rotated_bend_note_is_not_a_second_plane():
    # A note written vertically is still the same bend plane.
    blocks = [
        {"text": "UP 90° R.25", "dir": (1, 0), "bbox": (70, 60, 180, 74)},
        {"text": "UP 15° R.25", "dir": (0, -1), "bbox": (200, 40, 214, 160)},
    ]
    found = detect_bends("UP 90° R.25\nUP 15° R.25", text_blocks=blocks)
    assert found.count == 2
    assert found.flag is None
    assert found.plane_flag is None
    # Parallel bend lines under those notes stay one plane too.
    parallel = detect_bends(
        "UP 90° R.25\nUP 15° R.25",
        [
            _centerline((60, 67), (420, 67)),
            _centerline((60, 100), (420, 100)),
        ],
        text_blocks=blocks,
    )
    assert parallel.count == 2
    assert parallel.plane_flag is None


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
    notes = " ".join(plan.notes)
    assert "bends are not in a single plane" not in notes
    assert "dimension basis was not stated" in notes


def _formed_plate(*lines: str) -> str:
    return "\n".join(
        [
            "SAMPLE BRACKET",
            "PLATE",
            "0.125",
            "A36",
            *lines,
        ]
    )


def test_chamfer_pair_is_not_the_flat_blank():
    text = _formed_plate(
        "UP 90° R.13",
        "DOWN 90° R.13",
        "FLAT PATTERN",
        "3/8 X 45° CHAMFER",
        "5/16 X 45 CHAMFER",
    )
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.developed_length_in is None
    assert decision.length_source != "drawing flat pattern"
    assert decision.flag == "flat pattern size is not clear"
    assert decision.width_in != pytest.approx(0.375)
    assert decision.developed_length_in != pytest.approx(45)

    plan = plan_pdf_only_part(text=text, title="SAMPLE BRACKET")
    assert plan.route == "refuse"
    assert plan.route != "image_files"
    assert plan.flat_source != "drawing flat pattern"
    assert plan.width_in is None
    assert plan.length_in is None
    notes = " ".join(plan.notes)
    assert "flat pattern size is not clear" in notes
    assert "0.375" not in notes
    assert "0.3125" not in notes


def test_real_flat_pair_wins_beside_a_chamfer(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran even though the drawing printed the flat")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = _formed_plate(
        "UP 90° R.13",
        "DOWN 90° R.13",
        "FLAT PATTERN",
        "3/8 X 45° CHAMFER",
        "18.25 X 6.50",
    )
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.flag is None
    assert decision.length_source == "drawing flat pattern"
    assert decision.width_in == pytest.approx(18.25)
    assert decision.developed_length_in == pytest.approx(6.50)
    assert decision.width_in != pytest.approx(0.375)


def test_ambiguous_radius_blocks_a_printed_size():
    text = _formed_plate(
        "UP 90° R.13",
        "UP 90° R.13",
        "INSIDE RADIUS 0.50",
        "FLAT PATTERN",
        "3/8 X 45° CHAMFER",
        "18.25 X 6.50",
    )
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.flag == "inside radius is ambiguous"
    assert decision.developed_length_in is None
    assert decision.length_source != "drawing flat pattern"


def test_missing_radius_does_not_block_a_clear_flat_size(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran even though the drawing printed the flat")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = _formed_plate(
        "UP 90°",
        "UP 90°",
        "FLAT PATTERN",
        "18.25 X 6.50",
    )
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.flag is None
    assert decision.length_source == "drawing flat pattern"
    assert decision.width_in == pytest.approx(18.25)
    assert decision.developed_length_in == pytest.approx(6.50)
    assert decision.bend_count == 2


def test_separate_flat_overalls_pair_from_text_positions(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran even though the flat overalls were paired")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = _formed_plate(
        "UP 90° R.13",
        "UP 90° R.13",
        "FLAT PATTERN",
        "16.75",
        "4.125",
        "1.50",
    )
    blocks = [
        {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (100, 70, 220, 86)},
        {"text": "16.75", "dir": (1, 0), "bbox": (110, 240, 180, 254)},
        {"text": "4.125", "dir": (0, -1), "bbox": (40, 100, 54, 180)},
        {"text": "1.50", "dir": (1, 0), "bbox": (140, 150, 180, 164)},
    ]
    decision = evaluate_formed(text, thickness_in=0.125, text_blocks=blocks)
    assert decision is not None
    assert decision.flag is None
    assert decision.length_source == "drawing flat pattern"
    assert decision.width_in == pytest.approx(16.75)
    assert decision.developed_length_in == pytest.approx(4.125)

    plan = plan_pdf_only_part(text=text, title="SAMPLE BRACKET", text_blocks=blocks)
    assert plan.route == "image_files"
    assert plan.flat_source == "drawing flat pattern"
    assert plan.width_in == pytest.approx(16.75)
    assert plan.length_in == pytest.approx(4.125)


def test_separate_flat_overalls_without_positions_flag():
    text = _formed_plate(
        "UP 90° R.13",
        "UP 90° R.13",
        "FLAT PATTERN",
        "16.75",
        "4.125",
    )
    decision = evaluate_formed(text, thickness_in=0.125)
    assert decision is not None
    assert decision.developed_length_in is None
    assert decision.flag == "flat pattern size is not clear"
    assert "dimension basis" not in (decision.flag or "")

    plan = plan_pdf_only_part(text=text, title="SAMPLE BRACKET")
    assert plan.route == "refuse"
    assert plan.width_in is None
    notes = " ".join(plan.notes)
    assert "flat pattern size is not clear" in notes
    assert "dimension basis was not stated" not in notes


def test_radius_stays_on_the_bend_note_line():
    text = "\n".join(
        [
            "UP 90° R.13",
            "4.50",
            "BEND RADIUS",
            "0.75",
        ]
    )
    found = read_bends(text)
    assert found.bend_count == 1
    assert found.radius_ambiguous is False
    assert found.radius_flag is None
    assert found.radii_in == pytest.approx((0.13,))
    assert 4.50 not in found.radii_in
    assert 0.75 not in found.radii_in

    following = read_bends("BEND UP 90 DEG\nBEND RADIUS\n4.50")
    assert following.radii_in != pytest.approx((4.50,))
    assert following.radius_flag == "inside radius was not on the drawing"
    assert following.radius_ambiguous is False


def test_bare_flat_pattern_label_is_not_formed_evidence():
    text = "\n".join([_PLATE, "FLAT PATTERN VIEW"])
    decision = evaluate_formed(text, thickness_in=0.25)
    assert decision is None

    blocks = [
        {"text": "PLATE SIZE 4.00 X 6.00", "dir": (1, 0), "bbox": (72, 700, 240, 714), "page": 0},
        {"text": "FLAT PATTERN VIEW", "dir": (1, 0), "bbox": (72, 72, 210, 86), "page": 1},
    ]
    paged = evaluate_formed(text, thickness_in=0.25, text_blocks=blocks)
    assert paged is None

    plan = plan_pdf_only_part(text=text, title="SAMPLE PLATE", text_blocks=blocks)
    assert plan.route == "image_files"
    assert plan.bend_count == 0
    assert "formed evidence" not in " ".join(plan.notes)


def test_round_stock_bend_notes_flag_before_a_straight_cut():
    bent = "\n".join(
        [
            "BENT TUBE",
            "2.00 X 2.00 X 0.250 TUBE",
            "A36",
            "48 LG.",
            "CLR 3.00",
        ]
    )
    plan = plan_pdf_only_part(text=bent, title="BENT TUBE")
    assert plan.route == "refuse"
    assert plan.route != "long"
    assert "tube or round-stock bend notes are formed evidence" in " ".join(plan.notes)
    assert plan.cut_length_in is None

    bare = "\n".join(
        [
            "ROUND BAR",
            "CENTERLINE RADIUS 2.00",
        ]
    )
    missing = plan_pdf_only_part(text=bare, title="ROUND BAR")
    assert missing.route == "refuse"
    assert "tube or round-stock bend notes are formed evidence" in " ".join(missing.notes)
    assert "thickness was not on the drawing" not in " ".join(missing.notes)

    table = "\n".join(
        [
            "ROUND TUBE",
            "A36",
            "30 LG.",
            "ANGLE ROTATION LENGTH",
            "90 0 8.00",
            "45 180 6.00",
        ]
    )
    listed = plan_pdf_only_part(text=table, title="ROUND TUBE")
    assert listed.route == "refuse"
    assert listed.route != "long"
    assert "tube or round-stock bend notes are formed evidence" in " ".join(listed.notes)

    straight = "\n".join(
        [
            "PEDESTAL TUBE",
            "2 X 2 X 0.250 TUBE",
            "A36",
            "48 LG.",
        ]
    )
    untouched = plan_pdf_only_part(text=straight, title="PEDESTAL TUBE")
    assert untouched.route == "long"
    assert "formed evidence" not in " ".join(untouched.notes)


def _arrowed(p1: tuple[float, float], p2: tuple[float, float], axis: str) -> list[tuple]:
    """A dimension line plus arrowhead ticks at both ends."""
    x1, y1 = p1
    x2, y2 = p2
    lines = [("l", p1, p2)]
    if axis == "h":
        lines.extend(
            [
                ("l", p1, (x1 + 12, y1 - 4)),
                ("l", (x1 + 12, y1 - 4), (x1 + 12, y1 + 4)),
                ("l", p2, (x2 - 12, y2 - 4)),
                ("l", (x2 - 12, y2 - 4), (x2 - 12, y2 + 4)),
            ]
        )
    else:
        lines.extend(
            [
                ("l", p1, (x1 - 4, y1 + 12)),
                ("l", (x1 - 4, y1 + 12), (x1 + 4, y1 + 12)),
                ("l", p2, (x2 - 4, y2 - 12)),
                ("l", (x2 - 4, y2 - 12), (x2 + 4, y2 - 12)),
            ]
        )
    return lines


def _flat_view_drawings() -> list[dict]:
    """Unbroken dimension lines, arrow ticks at both ends, label under the part.

    18 3/16 x 6.50 at 18 pt/in. The sheet frame is a separate rect.
    """
    items = [
        ("re", (160, 180, 487.375, 297), 1),
        ("re", (20, 20, 590, 770), 1),
    ]
    items.extend(_arrowed((160, 150), (487.375, 150), "h"))
    items.extend(_arrowed((128, 180), (128, 297), "v"))
    return [
        {
            "type": "s",
            "width": 0.58,
            "dashes": "[] 0",
            "page_rect": (0, 0, 612, 792),
            "items": items,
        }
    ]


def _flat_view_blocks() -> list[dict]:
    # Every dimension string is horizontal. The arrowheads carry the axis.
    return [
        {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (250, 330, 390, 346)},
        {"text": "18 3", "dir": (1, 0), "bbox": (300, 124, 360, 138)},
        {"text": "16", "dir": (1, 0), "bbox": (340, 140, 364, 154)},
        {"text": "6.50", "dir": (1, 0), "bbox": (96, 224, 126, 238)},
        {"text": "1.25", "dir": (1, 0), "bbox": (220, 220, 260, 234)},
        {"text": "SIZE", "dir": (1, 0), "bbox": (500, 700, 540, 714)},
        {"text": "125", "dir": (1, 0), "bbox": (500, 720, 540, 734)},
    ]


def _arrowhead(tip: tuple[float, float], direction: tuple[float, float]) -> list[tuple]:
    """Filled arrowhead, about 9.5 pt long and 2.9 pt across. Tip at the line end."""
    dx, dy = direction
    base = (tip[0] - dx * 9.5, tip[1] - dy * 9.5)
    px, py = -dy * 1.45, dx * 1.45
    left = (base[0] + px, base[1] + py)
    right = (base[0] - px, base[1] - py)
    return [("l", tip, left), ("l", left, right), ("l", right, tip)]


def test_stacked_fraction_spans_read_as_one_size():
    split = _join_stacked_fraction_blocks(
        [
            {"text": "44", "dir": (1, 0), "bbox": (100, 200, 130, 214)},
            {"text": "1", "dir": (1, 0), "bbox": (134, 196, 144, 208)},
            {"text": "/", "dir": (1, 0), "bbox": (146, 204, 154, 216)},
            {"text": "16", "dir": (1, 0), "bbox": (132, 214, 148, 228)},
        ]
    )
    assert any(_bare_inches(block["text"]) == pytest.approx(44.0625) for block in split)
    assert all(block["text"].strip() not in {"44", "1", "16", "/"} for block in split)

    offset = _join_stacked_fraction_blocks(
        [
            {"text": "44 1", "dir": (1, 0), "bbox": (100, 198, 160, 212)},
            {"text": "16", "dir": (1, 0), "bbox": (136, 214, 156, 228)},
        ]
    )
    assert any(_bare_inches(block["text"]) == pytest.approx(44.0625) for block in offset)


def test_dimension_lines_pair_unidirectional_flat_overalls(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran even though the flat overalls were on the view")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = _formed_plate(
        "UP 90° R.13",
        "UP 90° R.13",
        "FLAT PATTERN",
        "18 3",
        "16",
        "6.50",
        "1.25",
        "SIZE",
        "125",
    )
    blocks = _flat_view_blocks()
    drawings = _flat_view_drawings()
    decision = evaluate_formed(
        text,
        thickness_in=0.125,
        drawings=drawings,
        text_blocks=blocks,
    )
    assert decision is not None
    assert decision.flag is None
    assert decision.length_source == "drawing flat pattern"
    assert decision.width_in == pytest.approx(18.1875)
    assert decision.developed_length_in == pytest.approx(6.50)
    assert decision.width_in != pytest.approx(125)
    assert decision.developed_length_in != pytest.approx(125)

    plan = plan_pdf_only_part(
        text=text,
        title="SAMPLE BRACKET",
        drawings=drawings,
        text_blocks=blocks,
    )
    assert plan.route == "image_files"
    assert plan.flat_source == "drawing flat pattern"
    assert plan.width_in == pytest.approx(18.1875)
    assert plan.length_in == pytest.approx(6.50)


def _dim_stroke(items: list[tuple]) -> dict:
    return {
        "type": "s",
        "width": 0.58,
        "dashes": "[] 0",
        "page_rect": (0, 0, 612, 792),
        "items": items,
    }


def _part_and_frame(box: tuple[float, float, float, float]) -> dict:
    return {
        "type": "s",
        "width": 0.72,
        "dashes": "[] 0",
        "page_rect": (0, 0, 612, 792),
        "items": [("re", box, 1), ("re", (16, 16, 596, 776), 1)],
    }


def test_split_halves_read_the_outline_above_the_label(monkeypatch):
    """Two collinear halves, outer arrowheads only, text in the gap.

    All dimension text is horizontal. The sheet frame is on the page and is
    not the flat blank. Arrowheads share one path.
    """

    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran even though the flat overalls were on the view")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    # 10.50 x 4.25 in at 18 pt/in.
    part = (180.0, 220.0, 369.0, 296.5)
    arrows = []
    arrows.extend(_arrowhead((180.0, 190.0), (-1.0, 0.0)))
    arrows.extend(_arrowhead((369.0, 190.0), (1.0, 0.0)))
    arrows.extend(_arrowhead((150.0, 220.0), (0.0, -1.0)))
    arrows.extend(_arrowhead((150.0, 296.5), (0.0, 1.0)))
    drawings = [
        _part_and_frame(part),
        _dim_stroke(
            [
                ("l", (180.0, 190.0), (245.0, 190.0)),
                ("l", (369.0, 190.0), (305.0, 190.0)),
                ("l", (150.0, 220.0), (150.0, 240.0)),
                ("l", (150.0, 296.5), (150.0, 270.0)),
                # Extension lines, same weight as the dimension lines.
                ("l", (180.0, 214.0), (180.0, 181.0)),
                ("l", (369.0, 214.0), (369.0, 181.0)),
            ]
        ),
        {"type": "f", "width": 0, "page_rect": (0, 0, 612, 792), "items": arrows},
    ]
    blocks = [
        {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (220, 330, 340, 346)},
        {"text": "10.50", "dir": (1, 0), "bbox": (250, 176, 300, 190)},
        {"text": "4.25", "dir": (1, 0), "bbox": (112, 246, 148, 260)},
    ]
    decision = evaluate_formed(
        _formed_plate("UP 90° R.13", "UP 90° R.13", "FLAT PATTERN", "10.50", "4.25"),
        thickness_in=0.125,
        drawings=drawings,
        text_blocks=blocks,
    )
    assert decision is not None
    assert decision.flag is None
    assert decision.length_source == "drawing flat pattern"
    assert decision.width_in == pytest.approx(10.50)
    assert decision.developed_length_in == pytest.approx(4.25)


def test_fraction_bar_and_ref_overalls_are_the_blank(monkeypatch):
    """A vector fraction bar stacks the size. REF beside an overall still counts."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran on a printed flat size")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    # 9 1/8 x 2.50 in at 18 pt/in. Numerator and denominator overlap, so only the bar joins them.
    part = (200.0, 210.0, 364.25, 255.0)
    arrows = []
    arrows.extend(_arrowhead((200.0, 180.0), (-1.0, 0.0)))
    arrows.extend(_arrowhead((364.25, 180.0), (1.0, 0.0)))
    arrows.extend(_arrowhead((170.0, 210.0), (0.0, -1.0)))
    arrows.extend(_arrowhead((170.0, 255.0), (0.0, 1.0)))
    drawings = [
        _part_and_frame(part),
        _dim_stroke(
            [
                ("l", (200.0, 180.0), (240.0, 180.0)),
                ("l", (364.25, 180.0), (320.0, 180.0)),
                ("l", (170.0, 210.0), (170.0, 220.0)),
                ("l", (170.0, 255.0), (170.0, 242.0)),
            ]
        ),
        {"type": "f", "width": 0, "page_rect": (0, 0, 612, 792), "items": arrows},
        {
            "type": "s",
            "width": 0.43,
            "dashes": "[] 0",
            "page_rect": (0, 0, 612, 792),
            "items": [("l", (264.0, 169.0), (276.0, 169.0))],
        },
    ]
    blocks = [
        {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (230, 290, 350, 306)},
        {"text": "9", "dir": (1, 0), "bbox": (244, 164, 260, 178)},
        {"text": "1", "dir": (1, 0), "bbox": (266, 158, 274, 172)},
        {"text": "8", "dir": (1, 0), "bbox": (266, 166, 274, 180)},
        {"text": "2.50", "dir": (1, 0), "bbox": (132, 222, 168, 236)},
    ]
    decision = evaluate_formed(
        _formed_plate("UP 90° R.13", "FLAT PATTERN", "9", "1", "8", "2.50"),
        thickness_in=0.125,
        drawings=drawings,
        text_blocks=blocks,
    )
    assert decision is not None
    assert decision.flag is None
    assert decision.width_in == pytest.approx(9.125)
    assert decision.developed_length_in == pytest.approx(2.50)

    # 8.00 REF x 3.25 in. REF is its own span in the gap.
    ref_part = (180.0, 200.0, 324.0, 258.5)
    ref_arrows = []
    ref_arrows.extend(_arrowhead((180.0, 170.0), (-1.0, 0.0)))
    ref_arrows.extend(_arrowhead((324.0, 170.0), (1.0, 0.0)))
    ref_arrows.extend(_arrowhead((150.0, 200.0), (0.0, -1.0)))
    ref_arrows.extend(_arrowhead((150.0, 258.5), (0.0, 1.0)))
    ref_drawings = [
        _part_and_frame(ref_part),
        _dim_stroke(
            [
                ("l", (180.0, 170.0), (220.0, 170.0)),
                ("l", (324.0, 170.0), (280.0, 170.0)),
                ("l", (150.0, 200.0), (150.0, 214.0)),
                ("l", (150.0, 258.5), (150.0, 244.0)),
            ]
        ),
        {"type": "f", "width": 0, "page_rect": (0, 0, 612, 792), "items": ref_arrows},
    ]
    ref_blocks = [
        {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (200, 300, 320, 316)},
        {"text": "8.00 REF.", "dir": (1, 0), "bbox": (224, 156, 286, 170)},
        {"text": "3.25", "dir": (1, 0), "bbox": (112, 218, 148, 232)},
    ]
    ref = evaluate_formed(
        _formed_plate("UP 90° R.13", "FLAT PATTERN", "8.00", "REF", "3.25"),
        thickness_in=0.125,
        drawings=ref_drawings,
        text_blocks=ref_blocks,
    )
    assert ref is not None
    assert ref.flag is None
    assert ref.width_in == pytest.approx(8.00)
    assert ref.developed_length_in == pytest.approx(3.25)


def test_inward_arrows_on_a_short_overall_still_measure_tip_to_tip(monkeypatch):
    """One path per arrow. The short side points the arrowheads inward."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran on a printed flat size")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    # 5.00 x 2.00 in at 18 pt/in. The 2.00 side is too short for arrows inside.
    part = (200.0, 200.0, 290.0, 236.0)
    drawings = [
        _part_and_frame(part),
        _dim_stroke(
            [
                ("l", (200.0, 170.0), (230.0, 170.0)),
                ("l", (290.0, 170.0), (260.0, 170.0)),
                ("l", (170.0, 200.0), (170.0, 182.0)),
                ("l", (170.0, 236.0), (170.0, 254.0)),
            ]
        ),
        {"type": "f", "width": 0, "page_rect": (0, 0, 612, 792), "items": _arrowhead((200.0, 170.0), (-1.0, 0.0))},
        {"type": "f", "width": 0, "page_rect": (0, 0, 612, 792), "items": _arrowhead((290.0, 170.0), (1.0, 0.0))},
        {"type": "f", "width": 0, "page_rect": (0, 0, 612, 792), "items": _arrowhead((170.0, 200.0), (0.0, 1.0))},
        {"type": "f", "width": 0, "page_rect": (0, 0, 612, 792), "items": _arrowhead((170.0, 236.0), (0.0, -1.0))},
    ]
    blocks = [
        {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (210, 270, 330, 286)},
        {"text": "5.00", "dir": (1, 0), "bbox": (232, 156, 268, 170)},
        {"text": "2.00", "dir": (1, 0), "bbox": (132, 208, 168, 222)},
    ]
    decision = evaluate_formed(
        _formed_plate("UP 90° R.13", "FLAT PATTERN", "5.00", "2.00"),
        thickness_in=0.125,
        drawings=drawings,
        text_blocks=blocks,
    )
    assert decision is not None
    assert decision.flag is None
    assert decision.width_in == pytest.approx(5.00)
    assert decision.developed_length_in == pytest.approx(2.00)


def test_flat_over_120_in_or_without_a_vertical_line_flags(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula ran on an unclear flat size")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = _formed_plate("UP 90° R.13", "UP 90° R.13", "FLAT PATTERN", "130.00", "6.50")
    blocks = [
        {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (200, 128, 340, 144)},
        {"text": "130.00", "dir": (1, 0), "bbox": (240, 300, 300, 314)},
        {"text": "6.50", "dir": (1, 0), "bbox": (36, 208, 72, 222)},
    ]
    too_long = evaluate_formed(
        text,
        thickness_in=0.125,
        drawings=_flat_view_drawings(),
        text_blocks=blocks,
    )
    assert too_long is not None
    assert too_long.flag == "flat pattern size is not clear"
    assert too_long.developed_length_in is None
    assert too_long.width_in != pytest.approx(130)

    horizontal_only = [
        {
            "page_rect": (0, 0, 612, 792),
            "items": [("re", (120, 160, 420, 280), 1), *_arrowed((120, 320), (420, 320), "h")],
        }
    ]
    unclear = evaluate_formed(
        _formed_plate("UP 90° R.13", "UP 90° R.13", "FLAT PATTERN", "18.25", "6.50"),
        thickness_in=0.125,
        drawings=horizontal_only,
        text_blocks=[
            {"text": "FLAT PATTERN", "dir": (1, 0), "bbox": (200, 128, 340, 144)},
            {"text": "18.25", "dir": (1, 0), "bbox": (240, 300, 300, 314)},
            {"text": "6.50", "dir": (1, 0), "bbox": (36, 208, 72, 222)},
        ],
    )
    assert unclear is not None
    assert unclear.flag == "flat pattern size is not clear"
    assert unclear.length_source != "drawing flat pattern"


def test_notes_on_perpendicular_bend_lines_are_two_planes():
    blocks = [
        {"text": "UP 90° R.25", "dir": (1, 0), "bbox": (80, 150, 180, 164)},
        {"text": "DOWN 90° R.25", "dir": (1, 0), "bbox": (220, 80, 330, 94)},
    ]
    drawings = [
        _centerline((40, 157), (400, 157)),
        _centerline((250, 40), (250, 400)),
        _centerline((0, 320), (500, 320)),
    ]
    found = detect_bends(
        "UP 90° R.25\nDOWN 90° R.25",
        drawings,
        text_blocks=blocks,
    )
    assert found.count == 2
    assert found.plane_flag == "bends are not in a single plane"

    decision = evaluate_formed(
        _formed_plate("UP 90° R.25", "DOWN 90° R.25", "FLAT PATTERN", "18.25 X 6.50"),
        thickness_in=0.125,
        drawings=drawings,
        text_blocks=blocks,
    )
    assert decision is not None
    assert decision.flag == "bends are not in a single plane"
    assert decision.developed_length_in is None


def test_template_wording_is_a_review_not_a_formed_claim():
    stray = "\n".join([_PLATE, "FLAT PATTERN VIEW"])
    blocks = [
        {"text": "FLAT PATTERN VIEW", "dir": (1, 0), "bbox": (72, 72, 220, 88)},
        {"text": "3.89", "dir": (1, 0), "bbox": (80, 200, 120, 214)},
        {"text": "36", "dir": (1, 0), "bbox": (90, 360, 120, 374)},
    ]
    decision = evaluate_formed(stray, thickness_in=0.25, text_blocks=blocks)
    assert decision is not None
    assert decision.flag == "template wording only, review"
    assert decision.flag_field == "review"
    plan = plan_pdf_only_part(text=stray, title="SAMPLE PLATE", text_blocks=blocks)
    notes = " ".join(plan.notes)
    assert plan.route == "refuse"
    assert "template wording only, review" in notes
    assert "formed evidence" not in notes
    assert "formed part" not in notes

    angular = "\n".join([_PLATE, "ALL ANGULAR DIMENSIONS 90°"])
    angled = evaluate_formed(angular, thickness_in=0.075)
    assert angled is not None
    assert angled.flag == "template wording only, review"
    angled_plan = plan_pdf_only_part(text=angular, title="SAMPLE PLATE")
    angled_notes = " ".join(angled_plan.notes)
    assert "template wording only, review" in angled_notes
    assert "a bend angle does not give a count" not in angled_notes
    assert "formed part" not in angled_notes


def test_plain_corner_radius_is_not_a_bent_tube():
    plate = "\n".join([_PLATE, "R1.38"])
    plan = plan_pdf_only_part(text=plate, title="SAMPLE PLATE")
    assert plan.route == "image_files"
    assert "tube or round-stock" not in " ".join(plan.notes)

    bare = "\n".join(["ROUND BAR", "R5.91", "2.00"])
    bare_plan = plan_pdf_only_part(text=bare, title="ROUND BAR")
    assert "tube or round-stock" not in " ".join(bare_plan.notes)


def test_r_decimal_and_tube_leg_degrees_flag_as_formed():
    radius = "\n".join(
        [
            "R5.91",
            "2.00 OD",
            "0.120 WALL",
        ]
    )
    plan = plan_pdf_only_part(text=radius, title="BENT TUBE")
    assert plan.route == "refuse"
    assert plan.route != "long"
    assert plan.route != "image_files"
    assert "tube or round-stock bend notes are formed evidence" in " ".join(plan.notes)

    leg = "\n".join(
        [
            "2.00 OD",
            "0.120 WALL",
            "15°",
        ]
    )
    marked = plan_pdf_only_part(text=leg, title="BENT TUBE")
    assert marked.route == "refuse"
    assert marked.route != "long"
    assert "tube or round-stock bend notes are formed evidence" in " ".join(marked.notes)

    called = "\n".join(
        [
            "2.00 OD X 0.120 WALL",
            "BEND",
            "A36",
            "40 LG.",
        ]
    )
    word = plan_pdf_only_part(text=called, title="BENT TUBE")
    assert word.route == "refuse"
    assert word.route != "long"
