from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from secturafab.push import (
    SecturaFabPushService,
    _default_material,
    _pn_quote_number,
    _weld_memo,
    classify_sectura_item,
    collect_job_files,
)


def test_weld_memo_includes_inches():
    memo = _weld_memo({"total_inches": 154.12, "weld_minutes": 41.1}, {"sizes_found": ["3/16"]})
    assert "154.12" in memo
    assert "3/16" in memo


def test_default_material_from_takeoff():
    mat = _default_material({"fitup_drivers": {"weight_calc": {"material_label": "A572 GR50"}}})
    assert mat == "A572"


def test_collect_job_files(tmp_path: Path):
    pdf = tmp_path / "35145-1.pdf"
    stp = tmp_path / "35145-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    drawings, cad = collect_job_files(pdf_path=pdf, stp_path=stp, library=None)
    assert drawings == [pdf]
    assert cad == [stp]


def test_push_job_creates_quote_and_uploads():
    client = MagicMock()
    client.get_json.return_value = {"QuoteNumber": "PN 35145-1", "ItemCount": 3, "ItemList": [{}, {}, {}]}

    service = SecturaFabPushService(client=client)
    pdf = Path("data/uploads/33/35145.pdf")
    stp = Path("data/uploads/33/35145-1.STEP")
    if not pdf.exists() or not stp.exists():
        return

    with patch.object(service, "upload_drawings_quote_request", return_value="qr-uuid") as up_d, patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as up_c, patch.object(service, "create_quote", return_value="quote-uuid") as create_q, patch.object(
        service, "allocate_quote_number", return_value="PN 35145-1"
    ), patch.object(service, "apply_item_categories", return_value=[]), patch(
        "secturafab.push.ensure_assembly_root", return_value=["Assembly root"]
    ), patch(
        "secturafab.push.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=["Attached Profile"]
    ), patch("secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]), patch(
        "secturafab.push.finalize_quote_ops", return_value=["Verified"]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="35145-1 JIB ARM",
            pdf_filename="35145.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "35145-1"}, "sizes_found": ["3/16"]},
            times={"total_inches": 154.12, "weld_minutes": 41.1},
            job_id=33,
        )
    assert result.ok
    assert result.quote_number == "PN 35145-1"
    assert result.created_new_quote
    create_q.assert_called_once()
    up_d.assert_called_once()
    up_c.assert_called_once()


def test_pn_quote_number_format():
    assert _pn_quote_number("21678-1") == "PN 21678-1"
    assert _pn_quote_number("PN 21678-1") == "PN 21678-1"


def test_classify_sectura_item_categories():
    assert classify_sectura_item("21680-1 KNUCKLE PLATE UB OUTSIDE") == "Cad"
    assert classify_sectura_item("21679-1 TUBE, KNUCKLE SUPPORT") == "Linear"
    assert classify_sectura_item("1/2-13 HEX BOLT GRADE 8") == "Component"
    assert classify_sectura_item("23403750 KING PIN") == "Component"
    assert classify_sectura_item("23403750 KINGPIN, 3/8") == "Component"


def test_allocate_quote_number_is_pn_part():
    service = SecturaFabPushService(client=MagicMock())
    assert service.allocate_quote_number("21678-1") == "PN 21678-1"


def test_repush_always_creates_new_quote_and_imports_cad():
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "PN 21678-1",
        "QuoteAndRevNumber": "PN 21678-1",
        "RevNumber": None,
        "ItemCount": 12,
        "ItemList": [
            {"Description": "21680 PLATE"},
            {"Description": "21679 TUBE SUPPORT"},
        ],
    }
    create = MagicMock()
    create.status_code = 200
    create.json.return_value = "new-id"
    create.text = '"new-id"'
    strip = MagicMock()
    strip.status_code = 200
    client.request.side_effect = [create, strip]
    client._parse_or_raise.side_effect = lambda r: "new-id"

    service = SecturaFabPushService(client=client)
    pdf = Path("data/uploads/41/21678-1.pdf")
    stp = Path("data/uploads/41/21678-1.STEP")
    if not pdf.exists() or not stp.exists():
        pdf = Path("data/uploads/40/21678-1.pdf")
        stp = Path("data/uploads/40/21678-1.STEP")
    if not pdf.exists() or not stp.exists():
        return

    with patch.object(service, "upload_drawings_quote_request", return_value="qr-uuid"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as up_c, patch.object(
        service, "apply_item_categories", return_value=["Categorized items — Cad: 1, Linear: 1, Component: 0"]
    ), patch("secturafab.push.ensure_assembly_root", return_value=["Assembly root"]), patch(
        "secturafab.push.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=["Attached Profile"]
    ), patch("secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]), patch(
        "secturafab.push.finalize_quote_ops", return_value=["Verified"]
    ):
        result = service.push_job(
            title="21678-1",
            pdf_filename="21678-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "21678-1"}},
            times={},
            job_id=41,
        )
    assert result.ok
    assert result.created_new_quote
    assert result.quote_number == "PN 21678-1"
    up_c.assert_called_once()


def test_collect_related_pdf_from_sibling_folder(tmp_path: Path):
    knuckle = tmp_path / "Knuckle Weldment - 21678-1"
    sibling = tmp_path / "21678-1"
    knuckle.mkdir()
    sibling.mkdir()
    (sibling / "21689.pdf").write_bytes(b"%PDF")
    drawings, _cad = collect_job_files(
        pdf_path=None,
        stp_path=None,
        library={"folder": str(knuckle), "related_pdfs": ["21689.pdf"]},
    )
    assert len(drawings) == 1
    assert drawings[0].name == "21689.pdf"


def test_parse_datapart_and_build_profile_ops():
    from secturafab.profile_ops import _build_profile_ops, parse_datapart

    raw = 'DataPart:{"Time":0.01,"CuttingLength":12.5,"PartLength":1}'
    dp = parse_datapart(raw)
    assert dp["Time"] == 0.01
    assert dp["CuttingLength"] == 12.5

    ops = _build_profile_ops("item-uuid", 0.01)
    assert len(ops) == 5
    assert all(o["OperationName"] == "Profile" for o in ops)
    laser = next(o for o in ops if o["CalculatorName"] == "Laser")
    assert laser["UnitTime"] == 0.01
    drafting = next(o for o in ops if o["CalculatorName"] == "Drafting")
    assert drafting["UnitTime"] == 0.25


def test_build_weld_ops_from_cursor_minutes():
    from secturafab.weld_ops import build_weld_ops, pick_weld_target_item, resolve_weld_times

    resolved = resolve_weld_times(
        {"weld_minutes": 200.46, "fitup_with_fixture_minutes": 35.0, "fitup_no_fixture_minutes": 58.0}
    )
    assert resolved is not None
    weld_h, fit_h, setup_h = resolved
    assert abs(weld_h * 60 - 200.46) < 0.01
    assert abs(fit_h * 60 - 35.0) < 0.01
    assert abs(setup_h * 60 - 15.0) < 0.01

    ops = build_weld_ops("item-1", weld_hours=weld_h, fitup_hours=fit_h, setup_hours=setup_h, quantity=1)
    assert [o["CalculatorName"] for o in ops] == [
        "Weld-Time",
        "Weld-Fitting",
        "Weld-Setup",
        "Weld Grind Finish",
    ]
    assert abs(ops[0]["UnitTime"] - weld_h) < 1e-9
    assert abs(ops[1]["UnitTime"] - fit_h) < 1e-9
    assert abs(ops[2]["UnitTime"] - 0.25) < 1e-9

    items = [
        {"ID": "a", "Description": "73000567 plate", "ProductType": 100},
        {"ID": "b", "Description": "73476004", "ProductType": 300},
    ]
    assert pick_weld_target_item(items, part_key="73476004")["ID"] == "b"


def test_extract_bom_rows_and_qty_map():
    from secturafab.qty_ops import bom_qty_map, extract_bom_rows, normalize_part_key

    assert normalize_part_key("7300056-7") == "73000567"
    takeoff = {
        "fitup_drivers": {
            "weight_calc": {
                "bom": {
                    "rows": [
                        {"part_no": "7300056-7", "qty": 2},
                        {"part_no": "7347650-6", "qty": 2},
                        {"part_no": "2340375-0", "qty": 1},
                    ]
                }
            }
        }
    }
    rows = extract_bom_rows(takeoff)
    assert len(rows) == 3
    qmap = bom_qty_map(rows)
    assert qmap["73000567"] == 2
    assert qmap["73476506"] == 2
    assert qmap["23403750"] == 1


def test_rollup_assembly_costs_builds_update_payload():
    from unittest.mock import MagicMock

    from secturafab.quote_update import rollup_assembly_costs

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "root",
                "Description": "73476004",
                "ProductType": 300,
                "Quantity": 1,
                "OperationCostList": [{"UnitCost": 10.0, "UnitPrice": 20.0, "Quantity": 1}],
            },
            {
                "ID": "c1",
                "Description": "73000567",
                "ProductType": 100,
                "Quantity": 2,
                "AssemblyID": "root",
                "UnitCost": 5.0,
                "UnitPrice": 8.0,
            },
        ]
    }
    put = MagicMock()
    put.status_code = 200
    put.text = "true"
    client.request.return_value = put

    notes = rollup_assembly_costs(client, "qid", part_key="73476004")
    assert notes and "Rolled up" in notes[0]
    body = client.request.call_args.kwargs["json"]
    by_name = {p["ParamName"]: p["Value"] for p in body}
    # children 2*5 + weld 10 = 20
    assert by_name["UnitCost"] == "20.00"
    assert by_name["UnitPrice"] == "36.00"  # 2*8 + 20


def test_bom_purchased_ignores_over_king_pin_channel():
    from secturafab.component_ops import _bom_row_is_purchased, find_purchased_part_keys

    assert _bom_row_is_purchased('KING PIN, 3/8"') == "KING PIN"
    assert _bom_row_is_purchased("CHANNEL, OVER KING PIN, COUPLER ASSL'Y") is None
    keys = find_purchased_part_keys(
        library_folder=None,
        bom_rows=[
            {"part_no": "2340375-0", "description": 'KING PIN, 3/8"', "qty": 1},
            {
                "part_no": "7300057-1",
                "description": "CHANNEL, OVER KING PIN, COUPLER ASSL'Y",
                "qty": 1,
            },
        ],
    )
    assert "2340375-0" in keys or "23403750" in keys
    assert "7300057-1" not in keys and "73000571" not in keys
