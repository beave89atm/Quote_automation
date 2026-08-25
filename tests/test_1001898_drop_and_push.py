"""Job 91 / 1001898-1 drop + cookie-less push dry-run (no live Sectura writes)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from quote_core.customer_org import detect_organization
from quote_core.drawing_library import find_drawings
from quote_core.drawing_title import title_from_library_folder
from quote_core.lom_xlsx import extract_bom_from_lom_xlsx
from secturafab.item_desc import format_assembly_description, looks_like_drawing_sheet
from secturafab.pdf_assembly_ops import build_pdf_only_assembly, plan_weldment_lines
from secturafab.push import SecturaFabPushService, classify_sectura_item
from tests.fixtures.live_get_1001898 import gold_1001898_get

from tests.test_lom_xlsx import (
    _1001898_DASH1,
    _1001898_lom_rows,
    write_excel_absolute_target_xlsx,
)

_LOCKED = {
    "Cad": {"14500-1", "14501-1", "1005966-1", "9905-1", "1005940-1"},
    "Linear": {"1001880-2", "29860-3", "29860-4", "10081-2", "33637-1"},
    "Component": {
        "50029-7",
        "50122-1",
        "50006-5",
        "8166-1",
        "50030-5",
        "50115-7",
        "50137-5",
    },
}


def _bom_rows() -> list[dict]:
    return [
        {"part_no": pn, "qty": qty, "description": desc}
        for _item, qty, pn, desc in _1001898_DASH1
    ]


def test_locked_1001898_classify_is_5_cad_5_linear_7_component():
    got = {pn: classify_sectura_item(f"{pn} {desc}") for _i, _q, pn, desc in _1001898_DASH1}
    for cat, pns in _LOCKED.items():
        assert {pn for pn, c in got.items() if c == cat} == pns
    assert sum(1 for c in got.values() if c == "Cad") == 5
    assert sum(1 for c in got.values() if c == "Linear") == 5
    assert sum(1 for c in got.values() if c == "Component") == 7


def test_plan_weldment_dry_run_kyle_formats_no_sheet_flats():
    planned = plan_weldment_lines(_bom_rows())
    assert len(planned) == 17
    counts = {c: 0 for c in ("Cad", "Linear", "Component")}
    for line in planned:
        counts[line["category"]] += 1
        desc = line["Description"]
        assert desc and desc != line["part_no"], f"bare PN: {desc}"
        assert "22 in" not in desc and "28.5" not in desc and "28 in" not in desc
        if line["category"] == "Cad":
            assert line["ProductType"] == 100
            assert line["part_no"] in desc
        elif line["category"] == "Linear":
            assert line["ProductType"] == 10
        else:
            assert line["ProductType"] == 200
            assert line["part_no"] not in desc or desc != line["part_no"]
    assert counts == {"Cad": 5, "Linear": 5, "Component": 7}
    assert looks_like_drawing_sheet(22.0, 28.5) is True
    gusset = next(l for l in planned if l["part_no"] == "1005940-1")
    assert "PEDESTAL GUSSET" in gusset["Description"]
    elbow = next(l for l in planned if l["part_no"] == "50029-7")
    assert "ELBOW" in elbow["Description"].upper()
    assert elbow["Description"] != "50029-7"


def test_header_time_org_and_pedestal_title():
    folder = (
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
        r"\Engineering\Customer Drawings\Time\Pedestal Weldment - 1001898-1"
    )
    assert detect_organization(library_folder=folder) == "Time Manufacturing Waco"
    assert title_from_library_folder(folder, part_key="1001898-1") == "PEDESTAL WELDMENT"
    assert (
        format_assembly_description("1001898-1", "PEDESTAL WELDMENT")
        == "1001898-1 - PEDESTAL WELDMENT"
    )


def test_find_drawings_bare_1001898_hits_pedestal_folder(tmp_path: Path):
    root = tmp_path / "Customer Drawings"
    lib = root / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    (lib / "1001898-1-LOM.xlsx").write_bytes(b"PK")
    match = find_drawings("1001898", [root])
    assert match.folder is not None
    assert match.folder.name == "Pedestal Weldment - 1001898-1"


def test_build_pdf_weldment_does_not_quickadd_child_pdfs(tmp_path: Path):
    lib = tmp_path / "Pedestal Weldment - 1001898-1"
    lib.mkdir()
    client = MagicMock()
    client.get_json.return_value = {"ItemList": []}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    with patch(
        "secturafab.pdf_assembly_ops.quick_add_component_pdf"
    ) as qadd, patch(
        "secturafab.pdf_assembly_ops.fetch_linear_catalog", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.create_assembly_shell",
        return_value=["Created Assembly shell"],
    ), patch(
        "secturafab.pdf_assembly_ops.ensure_assembly_root", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.pdf_assembly_ops.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.bind_linear_product_ids",
        return_value=["Bound ProductID on 5 Linear item(s)"],
    ), patch(
        "secturafab.pdf_assembly_ops.categorize_pdf_imported_items", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops._apply_kyle_line_descriptions", return_value=[]
    ):
        notes = build_pdf_only_assembly(
            client,
            quote_id="qid",
            part_key="1001898-1",
            bom_rows=_bom_rows(),
            library_folder=lib,
            related_pdf_names=[],
            material="A36",
            thickness="0.25",
            assembly_description="1001898-1 - PEDESTAL WELDMENT",
        )
    qadd.assert_not_called()
    assert any(
        "no component PDF" in n or "New Line Item" in n or "typed API lines" in n or "typed flat" in n
        for n in notes
    )


def test_build_pdf_weldment_quickadds_cad_component_pdfs(tmp_path: Path):
    from secturafab.client import SecturaFabWebsiteAuthError

    lib = tmp_path / "Pedestal Weldment - 1001898-1"
    lib.mkdir()
    (lib / "14500-1.pdf").write_bytes(b"%PDF-1.4")
    client = MagicMock()
    client.get_json.return_value = {"ItemList": []}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    client.add_item_pdf_files.side_effect = SecturaFabWebsiteAuthError("302")
    with patch(
        "secturafab.pdf_assembly_ops.quick_add_component_pdf", return_value={"ok": True}
    ) as qadd, patch(
        "secturafab.pdf_assembly_ops.fetch_linear_catalog", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.create_assembly_shell",
        return_value=["Created Assembly shell"],
    ), patch(
        "secturafab.pdf_assembly_ops.ensure_assembly_root", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.pdf_assembly_ops.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.bind_linear_product_ids",
        return_value=[],
    ), patch(
        "secturafab.pdf_assembly_ops.categorize_pdf_imported_items", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops._apply_kyle_line_descriptions", return_value=[]
    ):
        notes = build_pdf_only_assembly(
            client,
            quote_id="qid",
            part_key="1001898-1",
            bom_rows=_bom_rows(),
            library_folder=lib,
            related_pdf_names=[],
            material="A36",
            thickness="0.25",
            assembly_description="1001898-1 - PEDESTAL WELDMENT",
        )
    assert qadd.called
    assert any("quickAddCAD" in n and "14500" in n for n in notes)


def test_cookie_less_1001898_push_dry_run(tmp_path: Path):
    pdf = tmp_path / "1001898.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Customer Drawings" / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    write_excel_absolute_target_xlsx(lib / "1001898-1-LOM.xlsx", _1001898_lom_rows())
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = gold_1001898_get()
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="1001898-1"
    ), patch.object(
        service, "finish_pdf_files", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(_bom_rows(), []),
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ) as finalize, patch(
        "secturafab.pdf_assembly_ops.build_pdf_only_assembly",
        return_value=[
            "Added 5 Cad plate line(s) (typed flat / no child-PDF quickAddCAD)",
            "Skipped child-PDF quickAddCAD",
            "Skipped grafted Profile",
        ],
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=["Set Organization: Time Manufacturing Waco"],
    ), patch(
        "secturafab.push.ensure_laser_profile_ops"
    ) as graft:
        result = service.push_job(
            title="1001898",
            pdf_filename="1001898.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={
                "library": {
                    "part_key": "1001898-1",
                    "folder": str(lib),
                    "searched_roots": [str(lib.parent.parent)],
                }
            },
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=91,
        )
    assert result.ok is True
    graft.assert_not_called()
    assert finalize.call_args.kwargs.get("attach_profile") in {None, False}
    desc = create_q.call_args.kwargs.get("description") or ""
    assert desc == "PEDESTAL WELDMENT"
    assert desc != "1001898"
    assert desc != "1001898-1"
    assert any("Time Manufacturing Waco" in n for n in (result.notes or []))
    assert any("grafted Profile" in n or "New Line Item" in n for n in (result.notes or []))
    bom = extract_bom_from_lom_xlsx(lib / "1001898-1-LOM.xlsx", bom_config="1")
    assert bom.part_number_count == 17
    assert bom.piece_count == 27


def test_step_21678_cookie_uses_finish_dry_run(tmp_path: Path):
    pdf = tmp_path / "21678-1.pdf"
    stp = tmp_path / "21678-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    populated = {
        "QuoteNumber": "21678-1",
        "ItemCount": 4,
        "ItemList": [
            {"Description": "21680 PLATE", "ProductType": 100},
            {"Description": "21679 TUBE", "ProductType": 10, "IsLinear": True},
        ],
    }
    _n = {"i": 0}

    def _get_json(_path):
        _n["i"] += 1
        return {"QuoteNumber": "21678-1", "ItemCount": 0, "ItemList": []} if _n["i"] == 1 else populated

    client.get_json.side_effect = _get_json
    service = SecturaFabPushService(client=client)
    finish = MagicMock(return_value=["Finish CAD Files → classify → Finish"])
    with patch.object(service, "finish_cad_files", finish), patch.object(
        service, "nest_after_finish", return_value=["Nest"]
    ), patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(
        service, "allocate_quote_number", return_value="21678-1"
    ), patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.push.ensure_weld_ops", return_value=["Weld on assembly"]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="KNUCKLE WELDMENT"
    ), patch(
        "secturafab.push.ensure_laser_profile_ops"
    ) as graft:
        result = service.push_job(
            title="21678-1",
            pdf_filename="21678-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "21678-1"}},
            times={"weld_minutes": 10, "total_inches": 20},
            job_id=41,
        )
    assert result.ok is True
    finish.assert_called_once()
    qadd.assert_not_called()
    graft.assert_not_called()


def test_step_cookie_missing_flags_and_does_not_graft(tmp_path: Path):
    pdf = tmp_path / "21678-1.pdf"
    stp = tmp_path / "21678-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = {
        "QuoteNumber": "21678-1",
        "ItemCount": 2,
        "ItemList": [{"Description": "A"}, {"Description": "B"}],
    }
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(
        service, "allocate_quote_number", return_value="21678-1"
    ), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ), patch.object(
        service, "finish_cad_files", return_value=[]
    ) as finish, patch.object(
        service, "apply_item_categories", return_value=[]
    ), patch(
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
        "secturafab.push.ensure_laser_profile_ops"
    ) as graft, patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ) as finalize, patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="KNUCKLE"
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
    assert result.ok is True
    finish.assert_called()
    graft.assert_not_called()
    assert finalize.call_args.kwargs.get("attach_profile") in {None, False}
    assert any(
        "falling back" in n or "Finish failed" in n or "grafted Profile" in n
        for n in (result.notes or [])
    )
