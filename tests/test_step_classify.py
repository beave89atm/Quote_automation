"""STEP stock classify: thin plate vs 15911-style flat-bar (not Cad Contours)."""

from __future__ import annotations

from unittest.mock import MagicMock

from secturafab.push import (
    SecturaFabPushService,
    apply_step_stock_category,
    classify_sectura_item,
)
from secturafab.step_classify import (
    STOCK_FLAT_BAR,
    STOCK_STRONG_PLATE,
    all_cartesian_bbox,
    classify_step_text,
    contours_path_allowed,
    robust_step_bbox,
    score_step_stock,
)
from secturafab.website import (
    _cad_plate_row_for_finish_gate,
    overlay_classified_row,
    product_type_is_cad,
    step_cad_finish_hard_gate,
)
from tests.fixtures.step_flat_bar_15911 import (
    FLAT_BAR_15911_DIMS,
    H638_LIKE_PLATE_DIMS,
    flat_bar_15911_step_text,
    h638_like_plate_step_text,
    live_15911_bar_vs_plate,
)


def test_score_h638_like_thin_plate_is_strong_plate():
    assert score_step_stock(H638_LIKE_PLATE_DIMS) == STOCK_STRONG_PLATE
    assert contours_path_allowed(STOCK_STRONG_PLATE) is True
    assert classify_sectura_item("H.6.38 PLATE", stock_dims=H638_LIKE_PLATE_DIMS) == "Cad"
    assert classify_sectura_item("H.6.38", stock_dims=H638_LIKE_PLATE_DIMS) == "Cad"


def test_score_15911_flat_bar_is_linear_not_strong_plate():
    dump = live_15911_bar_vs_plate()
    assert dump["invented"] is False
    assert score_step_stock(FLAT_BAR_15911_DIMS) == STOCK_FLAT_BAR
    assert score_step_stock(FLAT_BAR_15911_DIMS) != STOCK_STRONG_PLATE
    assert contours_path_allowed(STOCK_FLAT_BAR) is False
    assert classify_sectura_item("15911-14", stock_dims=FLAT_BAR_15911_DIMS) == "Linear"
    assert classify_sectura_item("15911-7", stock_dims=FLAT_BAR_15911_DIMS) == "Linear"
    assert classify_sectura_item("10289-5", stock_dims=FLAT_BAR_15911_DIMS) == "Linear"
    assert apply_step_stock_category("Cad", STOCK_FLAT_BAR, "15911-14") == "Linear"
    assert apply_step_stock_category("Cad", STOCK_FLAT_BAR, "H.6.38 PLATE") == "Cad"


def test_robust_bbox_ignores_hole_axis_cartesian_points():
    text = flat_bar_15911_step_text()
    parsed = classify_step_text(text)
    box = parsed["box"]
    assert box is not None
    assert abs(box[0] - 42.5) < 0.05
    assert abs(box[1] - 5.0) < 0.05
    assert abs(box[2] - 1.75) < 0.05
    assert parsed["source"] in {"vertex", "plane"}
    assert parsed["kind"] == STOCK_FLAT_BAR
    assert parsed["category"] == "Linear"
    assert parsed["contours_path_allowed"] is False
    inflated = all_cartesian_bbox(text)
    assert inflated is not None
    assert inflated[0] > 50 or inflated[1] > 8 or inflated[2] > 3
    robust = robust_step_bbox(text)
    assert robust["all_cartesian_box"] != robust["box"]
    assert score_step_stock(inflated) != STOCK_STRONG_PLATE or parsed["kind"] == STOCK_FLAT_BAR


def test_h638_like_step_stays_strong_plate():
    parsed = classify_step_text(h638_like_plate_step_text())
    assert parsed["kind"] == STOCK_STRONG_PLATE
    assert parsed["category"] == "Cad"
    assert parsed["contours_path_allowed"] is True
    box = parsed["box"]
    assert box is not None
    assert abs(box[2] - 0.1875) < 0.02


def test_classify_cadimport_flat_bar_rejects_cad_contours(tmp_path):
    stp = tmp_path / "15911-14.STEP"
    stp.write_text(flat_bar_15911_step_text(), encoding="ascii")
    rows = [
        {
            "SourceDataID": "bar-1",
            "ID": "id-15911-14",
            "Name": "15911-14",
            "ProductType": "Component",
            "Qty": 1,
            "ErrorStatus": 0,
            "InternalData": "",
        }
    ]
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="15911-14",
        cad_files=[stp],
    )
    assert len(classified) == 1
    kid = classified[0]
    assert kid["Category"] == "Linear"
    assert kid["FileType"] == "Linear"
    assert kid["PartMode"] == 1
    assert product_type_is_cad(kid.get("ProductType")) is False
    assert kid["ProductType"] != 100
    assert _cad_plate_row_for_finish_gate(kid) is False
    assert step_cad_finish_hard_gate(classified) is None
    blob = " ".join(notes)
    assert "flat_bar" in blob
    assert "Cad: 0" in blob or "Linear: 1" in blob


def test_classify_cadimport_h638_plate_stays_cad():
    rows = [
        {
            "SourceDataID": "h638",
            "ID": "id-h638",
            "Name": "H.6.38 PLATE",
            "ProductType": "Component",
            "Thickness": "0.1875",
            "Thickness_Units": "inch",
            "Qty": 1,
            "ErrorStatus": 0,
            "InternalData": "",
        }
    ]
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.1875",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        qty=1,
        part_key="H.6.38",
        stock_dims=H638_LIKE_PLATE_DIMS,
    )
    kid = classified[0]
    assert kid["Category"] == "Cad"
    assert kid["ProductType"] == 100
    overlaid = overlay_classified_row(rows[0], category="Cad", thickness="0.1875")
    assert overlaid["ProductType"] == 100
    assert "Cad: 1" in " ".join(notes)
