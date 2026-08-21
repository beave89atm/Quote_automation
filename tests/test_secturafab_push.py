from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from secturafab.push import (
    SecturaFabPushService,
    _default_material,
    _pn_quote_number,
    _sanitize_thickness_param,
    _weld_memo,
    classify_sectura_item,
    collect_job_files,
    existing_quote_action,
    quote_number_lookup_names,
)


def test_weld_memo_includes_inches():
    memo = _weld_memo({"total_inches": 154.12, "weld_minutes": 41.1}, {"sizes_found": ["3/16"]})
    assert "154.12" in memo
    assert "3/16" in memo


def test_sanitize_thickness_strips_inch_suffix():
    assert _sanitize_thickness_param("0.2500 inch") == "0.25"
    assert _sanitize_thickness_param('0.25"') == "0.25"
    assert "inch" not in _sanitize_thickness_param("0.1046 inch").lower()


def test_default_material_ignores_weak_aluminum_guess():
    mat = _default_material(
        {
            "fitup_drivers": {
                "weight_calc": {
                    "material_key": "aluminum",
                    "material_label": "Aluminum (unspecified)",
                }
            }
        }
    )
    assert mat == "A36"


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
    client.get_json.return_value = {"QuoteNumber": "35145-1", "ItemCount": 3, "ItemList": [{}, {}, {}]}

    service = SecturaFabPushService(client=client)
    pdf = Path("data/uploads/33/35145.pdf")
    stp = Path("data/uploads/33/35145-1.STEP")
    if not pdf.exists() or not stp.exists():
        return

    with patch.object(service, "upload_drawings_quote_request", return_value="qr-uuid") as up_d, patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as up_c, patch.object(service, "create_quote", return_value="quote-uuid") as create_q, patch.object(
        service, "allocate_quote_number", return_value="35145-1"
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
    assert result.quote_number == "35145-1"
    assert result.created_new_quote
    create_q.assert_called_once()
    up_d.assert_called_once()
    up_c.assert_called_once()


def test_pn_quote_number_format():
    assert _pn_quote_number("21678-1") == "21678-1"
    assert _pn_quote_number("PN 21678-1") == "21678-1"
    assert _pn_quote_number("pn 1511-5024_R00") == "1511-5024"
    assert _pn_quote_number("15115024R00") == "15115024"


def test_classify_sectura_item_categories():
    assert classify_sectura_item("21680-1 KNUCKLE PLATE UB OUTSIDE") == "Cad"
    assert classify_sectura_item("21679-1 TUBE, KNUCKLE SUPPORT") == "Linear"
    assert classify_sectura_item("1/2-13 HEX BOLT GRADE 8") == "Component"
    assert classify_sectura_item("23403750 KING PIN") == "Component"
    assert classify_sectura_item("23403750 KINGPIN, 3/8") == "Component"


def test_allocate_quote_number_is_bare_part():
    service = SecturaFabPushService(client=MagicMock())
    assert service.allocate_quote_number("21678-1") == "21678-1"
    assert service.allocate_quote_number("PN 21678-1") == "21678-1"


def test_create_quote_uses_open_new_and_bare_number():
    client = MagicMock()
    create = MagicMock()
    create.status_code = 200
    strip = MagicMock()
    strip.status_code = 200
    client.request.side_effect = [create, strip]
    client._parse_or_raise.return_value = "qid"
    service = SecturaFabPushService(client=client)
    qid = service.create_quote(quote_number="PN 28106-1", description="Lower Boom")
    assert qid == "qid"
    payload = client.request.call_args_list[0].kwargs["json"]
    assert payload["QuoteNumber"] == "28106-1"
    assert payload["QuoteStatus"] == "OPEN-NEW"
    assert not payload["QuoteNumber"].startswith("PN")


def test_quote_number_lookup_includes_legacy_pn_prefix():
    names = quote_number_lookup_names("28106-1")
    assert names[0] == "28106-1"
    assert "PN 28106-1" in names


def test_existing_quote_action_reuses_api_user_and_refuses_human():
    assert (
        existing_quote_action(
            {
                "ID": "h1",
                "QuoteNumber": "28106-1",
                "QuoteStatus": "OPEN-NEW",
                "EnteredBy": "Yasaman Morshed",
                "ItemCount": 12,
                "ItemList": [{"ID": "1"}],
            }
        )
        == "refuse"
    )
    assert (
        existing_quote_action(
            {
                "ID": "k1",
                "QuoteNumber": "1007922-1",
                "QuoteStatus": "OPEN-NEW",
                "EnteredBy": "Kyle Cleaver",
                "ItemList": [{"ID": "1"}],
            }
        )
        == "refuse"
    )
    assert (
        existing_quote_action(
            {
                "ID": "a1",
                "QuoteNumber": "21727-1",
                "QuoteStatus": "OPEN-DRAFT",
                "EnteredBy": "api user",
                "ItemCount": 0,
                "ItemList": [],
            }
        )
        == "reuse"
    )


def test_repush_reuses_empty_api_quote_instead_of_creating(tmp_path: Path):
    pdf = tmp_path / "28106-1.pdf"
    stp = tmp_path / "28106-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.get_json.return_value = {
        "ID": "api-id",
        "QuoteNumber": "28106-1",
        "QuoteAndRevNumber": "28106-1",
        "RevNumber": None,
        "QuoteStatus": "OPEN-DRAFT",
        "EnteredBy": "api user",
        "ItemCount": 2,
        "ItemList": [{"Description": "16697 PLATE"}, {"Description": "15864 STIFFENER"}],
    }
    service = SecturaFabPushService(client=client)

    empty_existing = {
        "ID": "api-id",
        "QuoteNumber": "28106-1",
        "QuoteStatus": "OPEN-DRAFT",
        "EnteredBy": "api user",
        "ItemCount": 0,
        "ItemList": [],
    }
    with patch.object(service, "upload_drawings_quote_request", return_value="qr-uuid") as up_d, patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as up_c, patch.object(service, "create_quote", return_value="new-id") as create_q, patch.object(
        service,
        "find_existing_quote",
        return_value=empty_existing,
    ), patch.object(
        service, "load_quote_detail", return_value=empty_existing
    ), patch.object(
        service, "apply_item_categories", return_value=[]
    ), patch(
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
    ), patch("secturafab.push.ensure_weld_ops", return_value=[]), patch(
        "secturafab.push.finalize_quote_ops", return_value=["Verified"]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="28106-1",
            pdf_filename="28106-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "28106-1", "folder": r"C:\drawings\Time\28106-1"}},
            times={},
            job_id=41,
        )
    assert result.ok
    assert result.created_new_quote is False
    assert result.quote_id == "api-id"
    assert result.quote_number == "28106-1"
    create_q.assert_not_called()
    up_c.assert_called_once()
    up_d.assert_called_once()


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


def test_is_laser_plate_accepts_laser_bay1():
    from secturafab.profile_ops import _is_laser_plate

    assert _is_laser_plate(
        {
            "ProductType": 100,
            "IsPart": True,
            "IsPlate": False,
            "Machine": "Laser - Bay1",
            "Data": 'DataPart:{"Time":0.02,"CuttingLength":10}',
        }
    )
    assert not _is_laser_plate(
        {"ProductType": 300, "IsAssembly": True, "Machine": "Laser - Bay1"}
    )


def test_needs_assembly_structure_single_vs_multi():
    from secturafab.assembly_ops import needs_assembly_structure

    assert needs_assembly_structure([{"ID": "1"}], []) is False
    assert needs_assembly_structure([{"ID": "1"}], None) is False
    assert needs_assembly_structure([{"ID": "1"}, {"ID": "2"}], []) is True
    assert (
        needs_assembly_structure(
            [{"ID": "1"}],
            [{"part_no": "A", "qty": 1}, {"part_no": "B", "qty": 2}],
        )
        is True
    )
    assert needs_assembly_structure([{"ID": "1"}], [{"part_no": "A", "qty": 1}]) is False
    assert needs_assembly_structure([], [{"part_no": "A", "qty": 1}, {"part_no": "B", "qty": 1}]) is True


def test_push_single_solid_step_skips_assembly_root(tmp_path: Path):
    """One STEP solid + no multi-row BOM → Part + Profile, not Assembly."""
    pdf = tmp_path / "ME04-2773.pdf"
    stp = tmp_path / "ME04-2773.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "ME04-2773",
        "ItemCount": 1,
        "ItemList": [
            {
                "ID": "p1",
                "Description": "ME04-2773 - 0.99 in A36",
                "ProductType": 100,
                "IsPart": True,
                "Machine": "Laser",
                "Data": 'DataPart:{"Time":0.02}',
            }
        ],
    }
    service = SecturaFabPushService(client=client)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(service, "create_quote", return_value="qid"), patch.object(
        service, "allocate_quote_number", return_value="ME04-2773"
    ), patch.object(service, "apply_item_categories", return_value=[]), patch(
        "secturafab.push.ensure_assembly_root", return_value=["SHOULD NOT RUN"]
    ) as asm, patch(
        "secturafab.push.relink_assembly_children", return_value=["SHOULD NOT RELINK"]
    ) as relink, patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=["Attached Profile"]
    ) as profile, patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="PLATE - DOUBLER"
    ):
        result = service.push_job(
            title="ME04-2773",
            pdf_filename="ME04-2773.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "ME04-2773"}},
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=71,
        )

    assert result.ok is True
    asm.assert_not_called()
    relink.assert_not_called()
    profile.assert_called()
    assert any("left as Part" in n for n in (result.notes or []))


def test_ensure_laser_profile_ops_retries_when_missing_after_save():
    """If Profile is wiped after first save, verify path retries once."""
    from secturafab.profile_ops import ensure_laser_profile_ops

    laser_item = {
        "ID": "p1",
        "ProductType": 100,
        "IsPart": True,
        "Machine": "Laser - Bay1",
        "Data": 'DataPart:{"Time":0.02,"CuttingLength":10}',
        "OperationCostList": [],
    }
    with_profile = {
        **laser_item,
        "OperationCostList": [{"OperationName": "Profile", "PrimaryOperation": True}],
        "PrimaryTime": 0.02,
    }
    client = MagicMock()
    # 1) first attach read  2) verify missing  3) retry attach read  4) verify ok
    client.get_json.side_effect = [
        {"ItemList": [dict(laser_item)]},
        {"ItemList": [dict(laser_item)]},
        {"ItemList": [dict(laser_item)]},
        {"ItemList": [dict(with_profile)]},
    ]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    notes = ensure_laser_profile_ops(
        client, "qid", material="A36", thickness="0.1046", verify=True
    )
    assert client.request.call_count == 2
    assert any("Profile missing" in n and "retrying" in n for n in notes)
    assert any("Profile verified" in n for n in notes)


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


def test_push_readiness_pdf_only_not_ready(tmp_path: Path):
    from app.push_readiness import evaluate_push_readiness

    r = evaluate_push_readiness(stp_path=None, pdf_path=None, takeoff={"library": {}})
    assert r["ready"] is False
    assert "PDF" in (r["reason"] or "") or "STEP" in (r["reason"] or "")


def test_push_readiness_with_job_pdf_ready(tmp_path: Path):
    from app.push_readiness import evaluate_push_readiness

    pdf = tmp_path / "only.pdf"
    pdf.write_bytes(b"%PDF")
    r = evaluate_push_readiness(stp_path=None, pdf_path=pdf, takeoff={"library": {}})
    assert r["ready"] is True
    assert r["has_pdf"] is True


def test_push_readiness_with_stp_ready(tmp_path: Path):
    from app.push_readiness import evaluate_push_readiness

    stp = tmp_path / "part.stp"
    stp.write_bytes(b"ISO")
    r = evaluate_push_readiness(stp_path=stp, takeoff={})
    assert r["ready"] is True


def test_push_pdf_only_uses_single_pdf_shell(tmp_path: Path):
    """PDF without STEP/library still creates a quote via single-PDF path."""
    pdf = tmp_path / "lonely.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "lonely",
        "ItemCount": 1,
        "ItemList": [
            {"Description": "lonely - 12 Ga A36", "ProductType": 100, "IsPart": True},
        ],
    }
    service = SecturaFabPushService(client=client)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr") as up_d, patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="lonely"
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=["Attached Profile"]
    ), patch(
        "secturafab.pdf_assembly_ops.build_single_pdf_quote",
        return_value=["Imported job PDF", "Attached Profile"],
    ) as build_pdf:
        result = service.push_job(
            title="lonely Title",
            pdf_filename="lonely.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {}, "sizes_found": []},
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=99,
        )

    assert result.ok is True
    assert result.item_count and result.item_count > 0
    create_q.assert_called_once()
    up_d.assert_called_once()
    build_pdf.assert_called_once()
    assert "lonely Title" in (create_q.call_args.kwargs.get("description") or "")


def test_build_single_pdf_quote_skips_assembly_shell(tmp_path: Path):
    from secturafab.pdf_assembly_ops import build_single_pdf_quote

    pdf = tmp_path / "part.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "p1",
                "ProductType": 100,
                "IsPart": True,
                "Machine": "Laser",
                "Data": 'DataPart:{"Time":0.01}',
                "OperationCostList": [{"OperationName": "Profile"}],
            }
        ]
    }
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save

    with patch(
        "secturafab.pdf_assembly_ops.create_assembly_shell"
    ) as shell, patch(
        "secturafab.pdf_assembly_ops.ensure_assembly_root"
    ) as root, patch(
        "secturafab.pdf_assembly_ops.relink_assembly_children"
    ) as relink, patch(
        "secturafab.pdf_assembly_ops.quick_add_component_pdf", return_value={"ok": True}
    ) as qadd, patch(
        "secturafab.pdf_assembly_ops.wait_for_quote_settle", return_value=["settled"]
    ), patch(
        "secturafab.pdf_assembly_ops.ensure_laser_profile_ops",
        return_value=["Attached Profile"],
    ) as profile:
        notes = build_single_pdf_quote(
            client,
            quote_id="qid",
            part_key="part",
            pdf_path=pdf,
            material="A36",
            thickness="0.1046",
            description="SHOULD NOT OVERWRITE PART",
        )

    shell.assert_not_called()
    root.assert_not_called()
    relink.assert_not_called()
    qadd.assert_called_once()
    profile.assert_called_once()
    assert any("no Assembly shell" in n for n in notes)


def test_push_ok_requires_nonzero_item_count(tmp_path: Path):
    pdf = tmp_path / "part.pdf"
    stp = tmp_path / "part.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "part",
        "ItemCount": 0,
        "ItemList": [],
    }
    service = SecturaFabPushService(client=client)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(service, "create_quote", return_value="qid") as create_q, patch.object(
        service, "allocate_quote_number", return_value="part"
    ), patch.object(service, "apply_item_categories", return_value=[]), patch(
        "secturafab.push.ensure_assembly_root", return_value=[]
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
        "secturafab.push.ensure_laser_profile_ops", return_value=[]
    ), patch("secturafab.push.ensure_weld_ops", return_value=[]), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="part Title From Job",
            pdf_filename="part.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "part"}},
            times={"weld_minutes": 10, "total_inches": 20},
            job_id=1,
        )

    assert result.ok is False
    assert result.item_count == 0
    assert result.status == "failed"
    # Description fallback used when creating the quote
    assert "part Title From Job" in (create_q.call_args.kwargs.get("description") or "")


def test_push_success_sets_item_count_gt_zero(tmp_path: Path):
    pdf = tmp_path / "ok.pdf"
    stp = tmp_path / "ok.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "ok",
        "ItemCount": 2,
        "ItemList": [{"Description": "A"}, {"Description": "B"}],
    }
    service = SecturaFabPushService(client=client)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(service, "create_quote", return_value="qid") as create_q, patch.object(
        service, "allocate_quote_number", return_value="ok"
    ), patch.object(service, "apply_item_categories", return_value=[]), patch(
        "secturafab.push.ensure_assembly_root", return_value=[]
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
        "secturafab.push.ensure_laser_profile_ops", return_value=[]
    ), patch("secturafab.push.ensure_weld_ops", return_value=[]), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="From drawing"
    ):
        result = service.push_job(
            title="ok",
            pdf_filename="ok.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "ok"}},
            times={"weld_minutes": 5, "total_inches": 10},
            job_id=2,
        )

    assert result.ok is True
    assert result.item_count and result.item_count > 0
    create_q.assert_called_once()
    assert create_q.call_args.kwargs.get("description") == "From drawing"


def _time_push_job(service, tmp_path: Path, part_key: str, **kwargs):
    pdf = tmp_path / f"{part_key}.pdf"
    stp = tmp_path / f"{part_key}.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    return service.push_job(
        title=part_key,
        pdf_filename=pdf.name,
        pdf_path=pdf,
        stp_path=stp,
        takeoff={
            "library": {
                "part_key": part_key,
                "folder": rf"C:\drawings\Time\{part_key}",
            }
        },
        times=kwargs.get("times") or {},
        job_id=kwargs.get("job_id", 1),
    )


def test_push_refuses_existing_human_time_quotes(tmp_path: Path):
    """Never create a second live Time quote for 28106-1 / 1007922-1 / 21727-1."""
    for part_key, entered in (
        ("28106-1", "Yasaman Morshed"),
        ("1007922-1", "Kyle Cleaver"),
        ("21727-1", "Yasaman Morshed"),
    ):
        client = MagicMock()
        service = SecturaFabPushService(client=client)
        existing = {
            "ID": f"live-{part_key}",
            "QuoteNumber": part_key,
            "QuoteStatus": "OPEN-NEW",
            "EnteredBy": entered,
            "ItemCount": 8,
            "ItemList": [{"ID": "1"}, {"ID": "2"}],
        }
        with patch.object(service, "create_quote", return_value="new-id") as create_q, patch.object(
            service, "find_existing_quote", return_value=existing
        ), patch.object(service, "load_quote_detail", return_value=existing), patch.object(
            service, "upload_drawings_quote_request", return_value="qr"
        ) as up_d, patch.object(
            service, "quick_add_cad", return_value={"ok": True}
        ) as up_c, patch(
            "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
        ), patch(
            "secturafab.push.extract_assembly_description", return_value=None
        ):
            result = _time_push_job(service, tmp_path, part_key)
        assert result.ok is False, part_key
        assert result.created_new_quote is False
        assert result.quote_id == f"live-{part_key}"
        assert "already exists" in (result.error or "")
        assert entered in (result.error or "")
        create_q.assert_not_called()
        up_d.assert_not_called()
        up_c.assert_not_called()


def test_push_applies_time_manufacturing_organization(tmp_path: Path):
    pdf = tmp_path / "28106-1.pdf"
    stp = tmp_path / "28106-1.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "28106-1",
        "ItemCount": 2,
        "ItemList": [{"Description": "A"}, {"Description": "B"}],
    }
    service = SecturaFabPushService(client=client)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(service, "create_quote", return_value="qid"), patch.object(
        service, "find_existing_quote", return_value=None
    ), patch.object(service, "apply_item_categories", return_value=[]), patch(
        "secturafab.push.detect_organization", return_value="Time Manufacturing"
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=["Set Organization: Time Manufacturing"],
    ) as org, patch(
        "secturafab.push.ensure_assembly_root", return_value=[]
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
        "secturafab.push.ensure_laser_profile_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="28106-1 Lower Boom",
            pdf_filename="28106-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={
                "library": {
                    "part_key": "28106-1",
                    "folder": r"C:\drawings\Time\Lower Boom Weldment - 28106-1",
                }
            },
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=3,
        )

    assert result.ok is True
    org.assert_called_once()
    assert org.call_args.kwargs["organization_name"] == "Time Manufacturing"
    assert any("Time Manufacturing" in n for n in (result.notes or []))


def test_push_step_assembly_never_calls_update_item_part(tmp_path: Path):
    pdf = tmp_path / "80341687.pdf"
    stp = tmp_path / "80341687.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    not_found = MagicMock()
    not_found.status_code = 404
    client.request.return_value = not_found
    client.get_json.return_value = {
        "QuoteNumber": "80341687",
        "ItemCount": 3,
        "ItemList": [
            {
                "ID": "root",
                "Description": "80341687",
                "ProductType": 300,
                "IsAssembly": True,
            },
            {
                "ID": "c1",
                "Description": "plate A",
                "ProductType": 100,
                "Machine": "Laser - Bay1",
            },
            {
                "ID": "c2",
                "Description": "plate B",
                "ProductType": 100,
                "Machine": "Laser - Bay1",
            },
        ],
    }
    service = SecturaFabPushService(client=client)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(service, "create_quote", return_value="qid"), patch.object(
        service, "apply_item_categories", return_value=[]
    ), patch(
        "secturafab.push.ensure_assembly_root", return_value=["Assembly root"]
    ), patch(
        "secturafab.push.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=([{"part_no": "A", "qty": 2}, {"part_no": "B", "qty": 1}], []),
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=["Applied BOM quantities"]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=["Attached Profile"]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=["Verified"]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ), patch(
        "secturafab.profile_ops.apply_part_materials"
    ) as upd:
        result = service.push_job(
            title="80341687",
            pdf_filename="80341687.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "80341687"}},
            times={"weld_minutes": 20, "total_inches": 40},
            job_id=4,
        )

    assert result.ok is True
    upd.assert_not_called()
    for call in client.request.call_args_list:
        blob = " ".join(str(a) for a in call.args) + " " + str(call.kwargs)
        assert "UpdateItem_Part" not in blob
    assert any("Skipped UpdateItem_Part on STEP assembly" in n for n in (result.notes or []))


def test_takeoff_wants_weld_skips_when_no_symbols():
    from secturafab.weld_ops import takeoff_wants_weld

    assert takeoff_wants_weld({"weld_minutes": 12}, {"flags": ["No weld symbols — left at 0"]}) is False
    assert takeoff_wants_weld({"weld_minutes": 0}, {"items": [{"size": "1/4", "inches": 10}]}) is False
    assert takeoff_wants_weld(
        {"weld_minutes": 12, "fitup_with_fixture_minutes": 5},
        {"items": [{"size": "1/4", "inches": 10}], "flags": []},
    ) is True


def test_push_skips_weld_ops_when_takeoff_has_no_symbols(tmp_path: Path):
    pdf = tmp_path / "laser.pdf"
    stp = tmp_path / "laser.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "laser",
        "ItemCount": 1,
        "ItemList": [{"ID": "p1", "ProductType": 100, "Description": "laser"}],
    }
    service = SecturaFabPushService(client=client)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(service, "create_quote", return_value="qid"), patch.object(
        service, "find_existing_quote", return_value=None
    ), patch.object(service, "apply_item_categories", return_value=[]), patch(
        "secturafab.push.ensure_assembly_root", return_value=[]
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
        "secturafab.push.ensure_laser_profile_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=["No weld symbols / times on takeoff — skipped"]
    ) as weld, patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="laser",
            pdf_filename="laser.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={
                "library": {"part_key": "laser"},
                "flags": ["No weld symbols — weld and fit-up left at 0"],
                "fitup_drivers": {"source": "no_weld", "notes": ["No weld symbols — weld and fit-up left at 0"]},
                "items": [],
            },
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=5,
        )

    assert result.ok is True
    weld.assert_called()
    assert weld.call_args.kwargs.get("takeoff") is not None
    assert any("no weld symbols" in n.lower() for n in (result.notes or []))
