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


def test_existing_quote_action_never_reuses_including_api_drafts():
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
        == "refuse"
    )
    assert existing_quote_action(None) == "create"
    assert existing_quote_action({}) == "create"


def test_repush_refuses_empty_api_quote_instead_of_creating(tmp_path: Path):
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
    assert result.ok is False
    assert result.created_new_quote is False
    assert result.quote_id == "api-id"
    assert "already exists" in (result.error or "")
    create_q.assert_not_called()
    up_c.assert_not_called()
    up_d.assert_not_called()


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


def test_parse_datapart_and_hole_sizes():
    from secturafab.profile_ops import (
        hole_sizes_from_takeoff,
        hole_sizes_from_text,
        parse_datapart,
        plate_dims_from_takeoff,
    )

    raw = 'DataPart:{"Time":0.01,"CuttingLength":12.5,"PartLength":1}'
    dp = parse_datapart(raw)
    assert dp["Time"] == 0.01
    assert dp["CuttingLength"] == 12.5

    assert hole_sizes_from_text("CYLINDER MOUNT PLATE W/ 3/8 HOLES") == [0.375]
    takeoff = {
        "stp_summary": {
            "circle_diameters": [0.375, 8.0, 0.5],
            "pdf_dimensions_sample": [18.0, 6.0, 0.25],
        }
    }
    assert hole_sizes_from_takeoff(takeoff) == [0.375, 0.5]
    assert plate_dims_from_takeoff(takeoff) == (18.0, 6.0)


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
    assert any("quickAddCAD last" in n for n in (result.notes or []))


def test_ensure_laser_profile_ops_does_not_post_grafted_ops():
    """Verify-only: never POST a fake Profile 5-pack."""
    from secturafab.profile_ops import ensure_laser_profile_ops

    laser_item = {
        "ID": "p1",
        "ProductType": 100,
        "IsPart": True,
        "Machine": "Laser - Bay1",
        "Data": 'DataPart:{"Time":0.02,"CuttingLength":10}',
        "MaterialCost": 0,
        "OperationCostList": [],
    }
    client = MagicMock()
    client.get_json.return_value = {"ItemList": [dict(laser_item)]}

    notes = ensure_laser_profile_ops(
        client, "qid", material="A36", thickness="0.1046", verify=True
    )
    assert client.request.call_count == 0
    assert any("Profile primary ops missing" in n for n in notes)
    assert not any("Attached Profile" in n for n in notes)


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
    assert pick_weld_target_item(
        [{"ID": "a", "Description": "plate", "ProductType": 100}],
        part_key="plate",
    ) is None


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


def test_build_single_pdf_quote_uses_add_part_when_dims_known(tmp_path: Path):
    from secturafab.pdf_assembly_ops import build_single_pdf_quote

    pdf = tmp_path / "plate.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.get_json.return_value = {"ItemList": []}

    with patch(
        "secturafab.pdf_assembly_ops.quick_add_component_pdf"
    ) as qadd, patch(
        "secturafab.pdf_assembly_ops.add_cad_plate_part",
        return_value=["Added Cad part via addplate (18×6 in × qty 1, holes=0.375)"],
    ) as addp, patch(
        "secturafab.pdf_assembly_ops.wait_for_quote_settle", return_value=["settled"]
    ), patch(
        "secturafab.pdf_assembly_ops.ensure_laser_profile_ops",
        return_value=["Verified shop Profile + Laser time on 1 laser item(s)"],
    ):
        notes = build_single_pdf_quote(
            client,
            quote_id="qid",
            part_key="102728-1",
            pdf_path=pdf,
            material="A36",
            thickness="0.25",
            takeoff={
                "stp_summary": {
                    "pdf_dimensions_sample": [18.0, 6.0],
                    "circle_diameters": [0.375],
                }
            },
        )

    qadd.assert_not_called()
    addp.assert_called_once()
    kwargs = addp.call_args.kwargs
    assert kwargs["length"] == 18.0
    assert kwargs["width"] == 6.0
    assert kwargs["holes"] == [0.375]
    assert any("add-part" in n for n in notes)


def test_quick_add_component_pdf_includes_holes(tmp_path: Path):
    from secturafab.pdf_assembly_ops import quick_add_component_pdf

    pdf = tmp_path / "15864-2.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.post_multipart.return_value = {"ok": True}

    quick_add_component_pdf(
        client,
        quote_id="qid",
        pdf_path=pdf,
        material="A36",
        thickness="0.25",
        qty=2,
        memo="15864-2",
        length=10.0,
        width=4.0,
        holes=[0.375],
    )
    params = client.post_multipart.call_args.kwargs["params"]
    assert params["partMode"] == "Cad"
    assert params["fileType"] == "prt_pdf"
    assert params["length"] == 10.0
    assert params["width"] == 4.0
    assert params["holes"] == "0.375"
    assert params["qty"] == 2


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


def test_default_material_never_a569():
    from secturafab.push import _shop_material

    assert _shop_material("A569") == "A36"
    assert _shop_material("A572") == "A572"
    assert _shop_material(None) == "A36"
    assert _default_material(
        {"fitup_drivers": {"weight_calc": {"material_label": "A569 HR"}}}
    ) == "A36"


def test_cad_plate_ready_grafted_five_pack_laser_zero_fails():
    """Grafted Profile 5-pack with Laser=0 is a fail, not success."""
    from secturafab.profile_ops import _build_profile_ops, cad_plate_ready

    wiped = {
        "ID": "c1",
        "ProductType": 100,
        "Description": "102728-1 plate",
        "MaterialCost": 12.5,
        "Length": 10,
        "Width": 8,
        "Thickness": 0.25,
        "OperationCostList": [],
    }
    assert cad_plate_ready(wiped) is False

    ops = _build_profile_ops("c1", 0.0, cad_count=1, item=wiped)
    assert ops[0]["CalculatorName"] == "Laser"
    assert ops[0]["UnitTime"] == 0.0  # do not invent laser minutes
    assert all(float(o.get("UnitPrice") or 0) == 0 for o in ops)
    grafted = {**wiped, "OperationCostList": ops}
    assert cad_plate_ready(grafted) is False

    shop = {
        **wiped,
        "MaterialCost": 12.5,
        "OperationCostList": [
            {
                "OperationName": "Profile",
                "CalculatorName": "Laser",
                "PrimaryOperation": True,
                "UnitTime": 0.04,
            }
        ],
    }
    assert cad_plate_ready(shop) is True


def test_addplate_bind_no_longer_grafts_or_posts_ops():
    from secturafab.profile_ops import addplate_bind_and_restore_profile

    seed = {
        "ID": "c1",
        "ProductType": 100,
        "Description": "102728-1 plate",
        "Length": 18.0,
        "Width": 6.0,
        "MaterialCost": 14.2,
        "OperationCostList": [
            {"OperationName": "Profile", "CalculatorName": "Laser", "UnitTime": 0.0},
        ],
    }
    client = MagicMock()
    client.get_json.return_value = {"ItemList": [dict(seed)]}

    notes = addplate_bind_and_restore_profile(
        client, "qid", material="A36", thickness="0.25"
    )
    assert client.request.call_count == 0
    assert any("Skipping addplate-on-existing-Cad" in n for n in notes)
    assert any("Laser=0" in n for n in notes)
    assert not any("restored Profile 5-pack" in n for n in notes)


def test_add_cad_plate_part_sends_holes_on_new_item():
    from secturafab.profile_ops import add_cad_plate_part

    client = MagicMock()
    ok = MagicMock()
    ok.status_code = 200
    client.request.return_value = ok
    client.get_json.return_value = {
        "ItemList": [{"ID": "new", "ProductType": 100, "MaterialCost": 10}]
    }

    notes = add_cad_plate_part(
        client,
        "qid",
        material="A36",
        thickness="0.25",
        length=18.0,
        width=6.0,
        qty=2,
        holes=[0.375, 0.5],
    )
    assert client.request.call_count == 1
    path = client.request.call_args.args[1]
    assert "addplate" in path
    params = client.request.call_args.kwargs["params"]
    assert params["itemID"] == "00000000-0000-0000-0000-000000000000"
    assert params["partMode"] == "Cad"
    assert params["length"] == 18.0
    assert params["width"] == 6.0
    assert params["qty"] == 2
    assert params["holes"] == "0.375,0.5"
    assert any("holes=0.375,0.5" in n for n in notes)
    assert not any("OperationCostList" in str(c) for c in client.request.call_args_list)


def test_linear_bind_uses_ids_not_product_name():
    from secturafab.linear_ops import bind_linear_products

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "lin1",
                "IsLinear": True,
                "Description": "15863 PIVOT TUBE",
                "ProductID": "prod-1",
                "ProductConfigID": "cfg-1",
                "SKU": "DOM-2.00x0.25",
                "ProductName": "should-not-be-sent",
            }
        ]
    }
    ok = MagicMock()
    ok.status_code = 200
    client.request.return_value = ok

    notes = bind_linear_products(client, "qid")
    assert client.request.call_count == 1
    path = client.request.call_args.args[1]
    assert "addLinear" in path
    params = client.request.call_args.kwargs["params"]
    assert params["productID"] == "prod-1"
    assert params["productConfigID"] == "cfg-1"
    assert params["sku"] == "DOM-2.00x0.25"
    assert "productName" not in {k.lower() for k in params}
    assert any("addLinear bound" in n for n in notes)


def _ok_update():
    resp = MagicMock()
    resp.status_code = 200
    resp.text = "true"
    return resp


def test_ensure_weld_ops_uses_item_level_update_not_full_quote_post():
    from secturafab.weld_ops import ensure_weld_ops

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "asm",
                "ProductType": 300,
                "IsAssembly": True,
                "Description": "102728-1",
                "Quantity": 1,
                "OperationCostList": [],
            },
            {
                "ID": "cad",
                "ProductType": 100,
                "Description": "plate",
                "OperationCostList": [
                    {
                        "OperationName": "Profile",
                        "CalculatorName": "Laser",
                        "UnitTime": 0.04,
                    }
                ],
            },
        ]
    }
    client.request.return_value = _ok_update()

    notes = ensure_weld_ops(
        client,
        "qid",
        times={"weld_minutes": 12, "fitup_with_fixture_minutes": 5},
        part_key="102728-1",
        takeoff={"items": [{"size": "1/4", "inches": 10}]},
    )
    assert client.request.call_count == 1
    assert client.request.call_args.args[0] == "PUT"
    assert "quoteOnline/update" in client.request.call_args.args[1]
    assert not any(
        len(c.args) >= 2 and c.args[0] == "POST" and str(c.args[1]).rstrip("/") == "v1/quote"
        for c in client.request.call_args_list
    )
    body = client.request.call_args.kwargs["json"]
    assert body[0]["ParamName"] == "OperationCostList"
    assert body[0]["ID"] == "asm"
    assert any("Attached Weld" in n for n in notes)


def test_apply_item_categories_never_posts_full_quote():
    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {"ID": "c1", "Description": "PLATE GUSSET", "ProductType": 100},
        ]
    }
    client.request.return_value = _ok_update()
    service = SecturaFabPushService(client=client)
    notes = service.apply_item_categories("qid")
    assert client.request.call_count == 1
    assert client.request.call_args.args[0] == "PUT"
    assert "quoteOnline/update" in client.request.call_args.args[1]
    assert any("Categorized items" in n for n in notes)


def test_apply_bom_quantities_never_posts_full_quote():
    from secturafab.qty_ops import apply_bom_quantities

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {"ID": "asm", "ProductType": 300, "IsAssembly": True, "Quantity": 1},
            {
                "ID": "c1",
                "Description": "15864-2",
                "ProductType": 100,
                "Quantity": 1,
                "AssemblyQty": 1,
            },
        ]
    }
    client.request.return_value = _ok_update()
    notes = apply_bom_quantities(
        client,
        "qid",
        bom_rows=[{"part_no": "15864-2", "qty": 2}],
        part_key="28106-1",
    )
    assert client.request.call_count == 1
    assert client.request.call_args.args[0] == "PUT"
    assert "quoteOnline/update" in client.request.call_args.args[1]
    assert any("Applied BOM quantities" in n for n in notes)


def test_cad_still_ready_requires_profile_after_item_level_weld():
    """Weld on the assembly must not be treated as Cad success if Profile is gone."""
    from secturafab.profile_ops import cad_plate_ready

    wiped_cad = {
        "ID": "cad",
        "ProductType": 100,
        "Description": "102728-1 plate",
        "MaterialCost": 12.5,
        "FileID": "prt",
        "Data": 'DataPart:{"Time":0.05}',
        "OperationCostList": [],
    }
    assert cad_plate_ready(wiped_cad) is False
    shop = {
        **wiped_cad,
        "OperationCostList": [
            {
                "OperationName": "Profile",
                "CalculatorName": "Laser",
                "PrimaryOperation": True,
                "UnitTime": 0.05,
            }
        ],
    }
    assert cad_plate_ready(shop) is True


def test_push_creates_assembly_tree_before_cad_when_multi_bom(tmp_path: Path):
    """Assembly shell + addLinear happen before quickAddCAD."""
    pdf = tmp_path / "28106-1.pdf"
    stp = tmp_path / "28106-1.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "28106-1",
        "ItemCount": 2,
        "ItemList": [
            {"ID": "asm", "ProductType": 300, "IsAssembly": True},
            {
                "ID": "p1",
                "ProductType": 100,
                "Description": "15864-2",
                "MaterialCost": 10,
                "OperationCostList": [
                    {
                        "OperationName": "Profile",
                        "CalculatorName": "Laser",
                        "UnitTime": 0.04,
                    }
                ],
            },
        ],
    }
    service = SecturaFabPushService(client=client)
    order: list[str] = []

    def _mark(name, value):
        def _inner(*_a, **_k):
            order.append(name)
            return value

        return _inner

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "quick_add_cad", side_effect=_mark("cad", {"ok": True})
    ), patch.object(service, "create_quote", return_value="qid"), patch.object(
        service, "find_existing_quote", return_value=None
    ), patch.object(service, "apply_item_categories", return_value=[]), patch(
        "secturafab.pdf_assembly_ops.create_assembly_shell",
        side_effect=_mark("shell", ["Created Assembly shell"]),
    ), patch(
        "secturafab.push.bind_linear_products",
        side_effect=_mark("linear", ["addLinear bound"]),
    ), patch(
        "secturafab.push.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=([{"part_no": "A", "qty": 1}, {"part_no": "B", "qty": 1}], []),
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
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
            takeoff={"library": {"part_key": "28106-1", "folder": r"C:\drawings\Time"}},
            times={"weld_minutes": 10, "fitup_with_fixture_minutes": 5},
            job_id=80,
        )

    assert result.ok is True
    assert "shell" in order
    assert "cad" in order
    assert order.index("shell") < order.index("cad")
    assert order.index("linear") < order.index("cad")
