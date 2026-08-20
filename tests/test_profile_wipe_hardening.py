"""Offline tests: Profile last, missing-plate detect, op-list preserve."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from secturafab.profile_ops import (
    count_profile_items,
    laser_plates_missing_profile,
)
from secturafab.quote_update import preserve_operation_cost_lists
from secturafab.push import attachment_drawings_for_push


def test_laser_plates_missing_profile_partial_wipe():
    detail = {
        "ItemList": [
            {
                "ID": "asm",
                "ProductType": 300,
                "IsAssembly": True,
                "OperationCostList": [{"OperationName": "Weld"}],
            },
            {
                "ID": "p1",
                "ProductType": 100,
                "IsPart": True,
                "Machine": "Laser",
                "OperationCostList": [{"OperationName": "Profile"}],
            },
            {
                "ID": "p2",
                "ProductType": 100,
                "IsPart": True,
                "Machine": "Laser - Bay1",
                "OperationCostList": [{"OperationName": "Bend"}],
            },
        ]
    }
    assert count_profile_items(detail) == 1
    missing = laser_plates_missing_profile(detail)
    assert len(missing) == 1
    assert missing[0]["ID"] == "p2"


def test_preserve_operation_cost_lists_keeps_live_profile():
    client = MagicMock()
    outbound = {
        "ItemList": [
            {
                "ID": "p1",
                "Description": 'part - 1/4" A36 10 in X 5 in',
                "Length": 10,
                "Width": 5,
                "OperationCostList": [],
            }
        ]
    }
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "p1",
                "OperationCostList": [
                    {"OperationName": "Profile", "UnitTime": 0.1}
                ],
                "PrimaryTime": 0.1,
                "UnitPrimaryTime": 0.1,
                "BadgeString": "Profile",
            }
        ]
    }
    out = preserve_operation_cost_lists(client, "q1", outbound)
    ops = out["ItemList"][0]["OperationCostList"]
    assert any(o.get("OperationName") == "Profile" for o in ops)
    assert out["ItemList"][0]["PrimaryTime"] == 0.1
    assert out["ItemList"][0]["Description"].startswith("part")


def test_preserve_does_not_replace_live_weld_with_empty():
    client = MagicMock()
    outbound = {
        "ItemList": [
            {
                "ID": "asm",
                "OperationCostList": [],
                "Quantity": 1,
            }
        ]
    }
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "asm",
                "OperationCostList": [
                    {"OperationName": "Weld", "UnitTime": 0.5},
                ],
            }
        ]
    }
    out = preserve_operation_cost_lists(client, "q1", outbound)
    names = [o.get("OperationName") for o in out["ItemList"][0]["OperationCostList"]]
    assert "Weld" in names


def test_imperial_preserve_keeps_profile_on_save():
    from secturafab.imperial_ops import ensure_imperial_item_units

    client = MagicMock()
    item = {
        "ID": "p1",
        "Description": '73476505 - 1/4" A36 1114.425 mm X 920.6665 mm',
        "Length": 43.875,
        "Width": 36.247,
        "Length_Units": "inch",
        "IsPart": True,
        "Machine": "Laser",
        "OperationCostList": [{"OperationName": "Profile", "UnitTime": 0.2}],
        "PrimaryTime": 0.2,
        "BadgeString": "Profile",
    }
    detail = {"ItemList": [item]}
    client.get_json.return_value = detail
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = ensure_imperial_item_units(client, "quote-1")
    assert any("Normalized" in n for n in notes)
    posted = client.request.call_args.kwargs.get("json") or client.request.call_args[1][
        "json"
    ]
    ops = posted["ItemList"][0]["OperationCostList"]
    assert any(o.get("OperationName") == "Profile" for o in ops)


def test_finalize_reattaches_when_only_some_plates_missing_profile():
    from secturafab.finalize_ops import finalize_quote_ops

    client = MagicMock()
    detail = {
        "ItemList": [
            {
                "ID": "p1",
                "Description": "ok",
                "ProductType": 100,
                "IsPart": True,
                "Machine": "Laser",
                "OperationCostList": [{"OperationName": "Profile"}],
            },
            {
                "ID": "p2",
                "Description": "wiped",
                "ProductType": 100,
                "IsPart": True,
                "Machine": "Laser",
                "OperationCostList": [],
            },
        ]
    }
    client.get_json.return_value = detail

    with (
        patch("secturafab.finalize_ops.wait_for_quote_settle", return_value=[]),
        patch("secturafab.finalize_ops.time.sleep"),
        patch(
            "secturafab.finalize_ops.ensure_laser_profile_ops",
            return_value=["Attached Profile"],
        ) as profile,
        patch(
            "secturafab.finalize_ops.ensure_imperial_item_units",
            return_value=["imperial"],
        ),
        patch(
            "secturafab.finalize_ops.rollup_assembly_costs",
            return_value=["rollup"],
        ),
        patch(
            "secturafab.finalize_ops.bom_qty_mismatches",
            return_value=[],
        ),
        patch(
            "secturafab.finalize_ops.resolve_weld_times",
            return_value=None,
        ),
        patch(
            "secturafab.finalize_ops.assembly_has_weld",
            return_value=False,
        ),
    ):
        notes = finalize_quote_ops(
            client,
            "quote-partial",
            material="A36",
            thickness="0.25",
            times=None,
            part_key="asm",
            bom_rows=[],
            attempts=1,
        )

    profile.assert_called()
    assert any("MISSING" in n for n in notes)


def test_pdf_assembly_does_not_relink_after_profile():
    src = Path("secturafab/pdf_assembly_ops.py").read_text(encoding="utf-8")
    fn = src.split("def build_pdf_only_assembly", 1)[1]
    body = fn.split("\ndef ", 1)[0]
    profile_idx = body.find("ensure_laser_profile_ops(")
    assert profile_idx >= 0
    after = body[profile_idx:]
    assert "relink_assembly_children(" not in after


def test_attachment_drawings_stp_drops_library_children(tmp_path: Path):
    job = tmp_path / "21678-1.pdf"
    child = tmp_path / "21679.pdf"
    dxf = tmp_path / "21678-1.dxf"
    stp = tmp_path / "21678-1.stp"
    job.write_bytes(b"%PDF")
    child.write_bytes(b"%PDF")
    dxf.write_bytes(b"0\n")
    stp.write_bytes(b"ISO")
    attached = attachment_drawings_for_push(
        job_pdf=job,
        dxf_path=dxf,
        all_drawings=[job, child],
        cad=[stp],
    )
    assert job in attached
    assert dxf in attached
    assert child not in attached


def test_merge_ops_onto_live_keeps_kyle_qty_and_price():
    from secturafab.quote_update import merge_ops_onto_live_quote, safe_quote_post

    client = MagicMock()
    live = {
        "ID": "q1",
        "OrganizationName": "Time Manufacturing",
        "ItemList": [
            {
                "ID": "p1",
                "Description": "Kyle edited label",
                "Quantity": 7,
                "UnitCost": 99.0,
                "UnitPrice": 150.0,
                "OperationCostList": [{"OperationName": "Weld", "UnitTime": 0.4}],
            }
        ],
    }
    stale_outbound = {
        "ID": "q1",
        "OrganizationName": "Wrong Org",
        "ItemList": [
            {
                "ID": "p1",
                "Description": "stale",
                "Quantity": 1,
                "UnitCost": 1.0,
                "UnitPrice": 1.0,
                "OperationCostList": [
                    {"OperationName": "Weld", "UnitTime": 9.9},
                    {"OperationName": "Profile", "UnitTime": 0.2},
                ],
            }
        ],
    }
    client.get_json.return_value = live
    out = merge_ops_onto_live_quote(client, "q1", stale_outbound)
    item = out["ItemList"][0]
    assert item["Quantity"] == 7
    assert item["UnitCost"] == 99.0
    assert item["Description"] == "Kyle edited label"
    assert out["OrganizationName"] == "Time Manufacturing"
    names = [o.get("OperationName") for o in item["OperationCostList"]]
    assert names.count("Weld") == 1
    assert item["OperationCostList"][0]["UnitTime"] == 0.4
    assert "Profile" in names

    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    safe_quote_post(client, "q1", stale_outbound, additive=True)
    posted = client.request.call_args.kwargs["json"]
    assert posted["ItemList"][0]["Quantity"] == 7
    assert posted["OrganizationName"] == "Time Manufacturing"


def test_finalize_protect_existing_skips_rollup_qty_and_settle():
    from secturafab.finalize_ops import finalize_quote_ops

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "p1",
                "ProductType": 100,
                "IsPart": True,
                "Machine": "Laser",
                "Quantity": 5,
                "OperationCostList": [{"OperationName": "Profile"}],
            }
        ]
    }

    with (
        patch("secturafab.finalize_ops.wait_for_quote_settle") as settle,
        patch("secturafab.finalize_ops.time.sleep") as sleep,
        patch(
            "secturafab.finalize_ops.ensure_laser_profile_ops",
            return_value=[],
        ) as profile,
        patch(
            "secturafab.finalize_ops.ensure_weld_ops",
            return_value=[],
        ) as weld,
        patch(
            "secturafab.finalize_ops.ensure_imperial_item_units",
            return_value=["leftover mm"],
        ) as imperial,
        patch(
            "secturafab.finalize_ops.rollup_assembly_costs",
            return_value=["SHOULD NOT RUN"],
        ) as rollup,
        patch(
            "secturafab.finalize_ops.apply_bom_quantities",
            return_value=["SHOULD NOT RUN"],
        ) as qty,
        patch(
            "secturafab.finalize_ops.resolve_weld_times",
            return_value=(0.1, 0.1, 0.25),
        ),
        patch(
            "secturafab.finalize_ops.assembly_has_weld",
            return_value=True,
        ),
    ):
        notes = finalize_quote_ops(
            client,
            "quote-repush",
            material="A36",
            thickness="0.25",
            times={"weld_minutes": 10},
            part_key="21678-1",
            bom_rows=[{"part_no": "p1", "qty": 2}],
            protect_existing=True,
        )

    settle.assert_not_called()
    sleep.assert_not_called()
    profile.assert_not_called()
    weld.assert_not_called()
    rollup.assert_not_called()
    qty.assert_not_called()
    imperial.assert_called()
    assert imperial.call_args.kwargs.get("descriptions_only") is True
    assert any("fill-empty" in n for n in notes)


def test_imperial_descriptions_only_leaves_length_width():
    from secturafab.imperial_ops import ensure_imperial_item_units

    client = MagicMock()
    item = {
        "ID": "p1",
        "Description": '73476505 - 1/4" A36 1114.425 mm X 920.6665 mm',
        "Length": 99.0,
        "Width": 88.0,
        "Length_Units": "inch",
        "OperationCostList": [{"OperationName": "Profile"}],
    }
    client.get_json.return_value = {"ItemList": [item]}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = ensure_imperial_item_units(client, "q1", descriptions_only=True)
    assert any("leftover metric Description" in n for n in notes)
    assert item["Length"] == 99.0
    assert item["Width"] == 88.0
    assert "mm" not in item["Description"].lower()


def test_attachment_drawings_pdf_only_keeps_children(tmp_path: Path):
    job = tmp_path / "21678-1.pdf"
    child = tmp_path / "21679.pdf"
    job.write_bytes(b"%PDF")
    child.write_bytes(b"%PDF")
    attached = attachment_drawings_for_push(
        job_pdf=job,
        dxf_path=None,
        all_drawings=[job, child],
        cad=[],
    )
    assert attached == [job, child]
