"""Offline tests for imperial Description / Length cleanup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from secturafab.imperial_ops import (
    _looks_like_mm,
    description_has_metric_dims,
    ensure_imperial_item_units,
    rewrite_description_dims_to_inch,
)


def test_rewrite_screenshot_style_mm_dims():
    desc = '73476505 - 1/4" A36 1114.425 mm X 920.6665 mm'
    out = rewrite_description_dims_to_inch(desc)
    assert "mm" not in out.lower()
    assert "43.875 in X" in out
    assert "36.247 in" in out
    assert '1/4"' in out


def test_rewrite_narrow_plate_mm_dims():
    desc = '73476506 - 1/4" A36 873.125 mm X 76.2 mm'
    out = rewrite_description_dims_to_inch(desc)
    assert "mm" not in out.lower()
    assert "34.375 in X" in out
    assert "3.000 in" in out


def test_rewrite_leaves_imperial_alone():
    desc = '80341688 - 1/4" A36 43.875 in X 11.973 in'
    assert rewrite_description_dims_to_inch(desc) == desc


def test_looks_like_mm_does_not_flag_already_inch():
    assert not _looks_like_mm(43.875, 36.247, "inch")


def test_ensure_imperial_rewrites_desc_without_double_converting_length():
    """Already-inch Length + mm Description → fix label only."""
    client = MagicMock()
    item = {
        "Description": '73476505 - 1/4" A36 1114.425 mm X 920.6665 mm',
        "Length": 43.875,
        "Width": 36.247,
        "Length_Units": "inch",
    }
    client.get_json.return_value = {"ItemList": [item]}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = ensure_imperial_item_units(client, "quote-1")
    assert any("Normalized" in n for n in notes)
    assert item["Length"] == 43.875
    assert item["Width"] == 36.247
    assert "mm" not in item["Description"].lower()
    assert "43.875 in X" in item["Description"]
    client.request.assert_called_once()


def test_ensure_imperial_converts_mm_length_and_description():
    client = MagicMock()
    item = {
        "Description": '80341689 - 1/4" A36 1114.425 mm X 80.7276 mm',
        "Length": 1114.425,
        "Width": 80.7276,
        "Length_Units": "millimeter",
    }
    client.get_json.return_value = {"ItemList": [item]}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = ensure_imperial_item_units(client, "quote-2")
    assert any("Normalized" in n for n in notes)
    assert abs(item["Length"] - 1114.425 / 25.4) < 1e-6
    assert abs(item["Width"] - 80.7276 / 25.4) < 1e-6
    assert item["Length_Units"] == "inch"
    assert not description_has_metric_dims(item["Description"])


def test_finalize_success_path_calls_imperial():
    """Happy-path early return must still run imperial cleanup."""
    from secturafab.finalize_ops import finalize_quote_ops

    client = MagicMock()
    # Assembly + one laser part with Profile already attached.
    detail = {
        "ItemList": [
            {
                "ID": "asm",
                "Description": "80341687",
                "ProductType": 300,
                "IsAssembly": True,
                "Quantity": 1,
                "OperationCostList": [{"Name": "Weld", "Time": 1}],
            },
            {
                "ID": "p1",
                "Description": '73476505 - 1/4" A36 1114.425 mm X 920.6665 mm',
                "ProductType": 100,
                "Quantity": 2,
                "AssemblyQty": 2,
                "AssemblyID": "asm",
                "OperationCostList": [{"Name": "Profile", "Time": 1}],
            },
        ]
    }
    client.get_json.return_value = detail

    with (
        patch("secturafab.finalize_ops.wait_for_quote_settle", return_value=[]),
        patch("secturafab.finalize_ops.time.sleep"),
        patch(
            "secturafab.finalize_ops.ensure_imperial_item_units",
            return_value=["Normalized 1 item(s)"],
        ) as imperial,
        patch(
            "secturafab.finalize_ops.rollup_assembly_costs",
            return_value=["Rolled up"],
        ),
        patch(
            "secturafab.finalize_ops.bom_qty_mismatches",
            return_value=[],
        ),
        patch(
            "secturafab.finalize_ops.count_profile_items",
            return_value=1,
        ),
        patch(
            "secturafab.finalize_ops.assembly_has_weld",
            return_value=True,
        ),
        patch(
            "secturafab.finalize_ops.takeoff_wants_weld",
            return_value=True,
        ),
    ):
        notes = finalize_quote_ops(
            client,
            "quote-ok",
            material="A36",
            thickness="0.25",
            times={"weld_minutes": 10},
            part_key="80341687",
            bom_rows=[{"part_number": "73476505", "qty": 2}],
            attempts=1,
        )

    imperial.assert_called()
    assert any("Normalized" in n or "Verified" in n for n in notes)
