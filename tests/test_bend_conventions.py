"""Conventions library: cited matches, false positives, conflicts, geometry."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from quote_core.bend_conventions import (
    convention_ids,
    detect_bends,
    load_conventions,
)
from secturafab.flat_pattern import evaluate_formed
from secturafab.pdf_only import plan_pdf_only_file, plan_pdf_only_part

_PLATE = "\n".join(
    [
        "TITLE",
        "LIFT LOG GUSSET",
        "MATERIAL",
        "1/4",
        "A36",
        "PLATE",
        "PLATE SIZE 4.00 X 6.00",
    ]
)


def test_library_loads_text_and_geometry_conventions():
    rows = load_conventions()
    ids = convention_ids()
    assert "callout_bend_up_down" in ids
    assert "explicit_n_bends" in ids
    assert "table_row_direction" in ids
    assert "fp_break_sharp_edges" in ids
    assert "geom_center_line" in ids
    assert "geom_phantom_line" in ids
    text = [row for row in rows if row.layer == "text" and row.pattern]
    geometry = [row for row in rows if row.layer == "geometry"]
    assert text
    assert geometry
    assert all(row.pattern is None for row in geometry)
    assert all(row.confidence in {"high", "medium", "low", "ignore"} for row in rows)


def test_solidworks_note_and_bend_table_cite_convention_ids():
    note = detect_bends("UP 90° R.06\nUP 90° R1.5")
    assert note.flag is None
    assert note.count == 2
    assert note.bends
    assert all(bend.convention_id == "callout_sw_up_angle_radius" for bend in note.bends)

    table = "\n".join(
        [
            "BEND ID DIRECTION ANGLE RADIUS",
            "1 UP 90 0.25",
            "2 DOWN 90 0.25",
            "3 UP 90 0.25",
        ]
    )
    found = detect_bends(table)
    assert found.flag is None
    assert found.count == 3
    assert {bend.convention_id for bend in found.bends} == {"table_row_direction"}


def test_multiplier_and_metric_callout():
    found = detect_bends("BEND UP 90 DEG R1,5 3X")
    assert found.flag is None
    assert found.count == 3
    assert found.bends[0].convention_id == "callout_bend_up_down"


def test_false_positives_are_not_bends():
    text = "\n".join(
        [
            _PLATE,
            "BENDABLE GUSSET",
            "BREAK SHARP EDGES",
            "DEBURR",
            "45° X .06 CHAMFER",
            "82° COUNTERSINK",
            "UPPER FLANGE",
            "SETUP",
        ]
    )
    found = detect_bends(text)
    assert found.flag is None
    assert found.count == 0
    plan = plan_pdf_only_part(text=text, title="LIFT LOG GUSSET")
    assert plan.route == "image_files"
    assert plan.bend_count == 0


def test_conflicting_counts_flag_bend_count():
    found = detect_bends("2 BENDS\nBEND UP 90 DEG")
    assert found.count is None
    assert found.flag is not None
    assert found.flag.startswith("signals conflict")
    assert "explicit_n_bends=2" in found.flag
    assert "callout_bend_up_down=1" in found.flag
    plan = plan_pdf_only_part(
        text=_PLATE + "\n2 BENDS\nBEND UP 90 DEG",
        title="LIFT LOG GUSSET",
    )
    assert plan.route == "refuse"
    assert plan.notes[-1].startswith("FLAG: bend count — ")
    assert "signals conflict" in plan.notes[-1]


def test_compound_bend_is_not_a_single_plane(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("formula hook called before the plane check")

    monkeypatch.setattr("secturafab.flat_pattern.flat_length_in", _boom)
    text = "\n".join(
        [
            "PLATE",
            "1/4",
            "A36",
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
    )
    flat = evaluate_formed(text, thickness_in=0.25)
    assert flat is not None
    assert flat.flag == "bends are not in a single plane"
    assert flat.developed_length_in is None


def _stroke(page, p1, p2, dashes: str) -> None:
    shape = page.new_shape()
    shape.draw_line(p1, p2)
    shape.finish(width=0.8, dashes=dashes)
    shape.commit()


def test_parallel_centerlines_corroborate_and_perpendicular_flags(tmp_path: Path):
    agreed = tmp_path / "agreed.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "3 BENDS")
    page.insert_text((72, 90), "BEND UP 90 DEG")
    page.insert_text((72, 108), "BEND DOWN 90 DEG")
    page.insert_text((72, 126), "BEND UP 90 DEG")
    for y in (160, 200, 240):
        _stroke(page, (72, y), (72 * 5, y), "[12 3 2 3] 0")
    doc.save(agreed)
    doc.close()

    plan = plan_pdf_only_file(agreed, title="CHANNEL")
    found = detect_bends(
        "3 BENDS\nBEND UP 90 DEG\nBEND DOWN 90 DEG\nBEND UP 90 DEG",
        drawings=_drawings(agreed),
    )
    assert found.flag is None
    assert found.count == 3
    assert found.geometry_count == 3
    assert any("geom_center_line" in bend.corroboration for bend in found.bends)
    assert plan.route == "refuse"

    crossed = tmp_path / "crossed.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "2 BENDS")
    page.insert_text((72, 90), "BEND UP 90 DEG")
    page.insert_text((72, 108), "BEND DOWN 90 DEG")
    _stroke(page, (72, 180), (360, 180), "[12 2 2 2 2 2] 0")
    _stroke(page, (200, 120), (200, 400), "[12 2 2 2 2 2] 0")
    doc.save(crossed)
    doc.close()
    perp = detect_bends(
        "2 BENDS\nBEND UP 90 DEG\nBEND DOWN 90 DEG",
        drawings=_drawings(crossed),
    )
    assert perp.plane_flag == "bends are not in a single plane"


def _drawings(path: Path) -> list:
    doc = fitz.open(path)
    try:
        rows = []
        for page in doc:
            rows.extend(page.get_drawings() or [])
        return rows
    finally:
        doc.close()


def test_hidden_lines_are_not_bend_lines():
    drawings = [
        {
            "dashes": "[ 4 2 ] 0",
            "items": [("l", (0, 0), (300, 0)), ("l", (300, 0), (0, 0))],
        }
    ]
    found = detect_bends("3 BENDS", drawings=drawings)
    assert found.geometry_count is None
    assert found.count == 3
    assert found.flag is None
