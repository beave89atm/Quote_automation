"""Cad/Linear/Component/Assembly descriptions, Time org, no grafted Profile."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from quote_core.customer_org import detect_organization, detect_organization_from_folder
from quote_core.drawing_title import extract_assembly_description, title_from_library_folder
from secturafab.item_desc import (
    format_assembly_description,
    format_cad_description,
    format_component_description,
    format_linear_description,
)
from secturafab.linear_ops import bind_linear_product_ids, match_linear_product
from secturafab.push import SecturaFabPushService, classify_sectura_item


def test_classify_fittings_are_component_not_cad():
    assert classify_sectura_item("14500-1 PEDESTAL TOP PLATE") == "Cad"
    assert classify_sectura_item("1001880-2 PEDESTAL TUBE") == "Linear"
    assert classify_sectura_item("29860-4 PEDESTAL BRACE ANGLE") == "Linear"
    assert classify_sectura_item("50137-5 3/4 NPT HALF COUPLING") == "Component"
    assert classify_sectura_item("50115-7 1 1/4 NPT NIPPLE X 4 LG.") == "Component"
    assert classify_sectura_item("50006-5 3/4 NPT MAGNETIC PLUG") == "Component"
    assert classify_sectura_item("50122-1 1 1/4 NPT PIPE CAP") == "Component"
    assert classify_sectura_item("8166-1 FILLER NECK") == "Component"
    assert classify_sectura_item("50029-7 1 1/4 90 STREET ELBOW") == "Component"
    assert classify_sectura_item("10081-2 PEDESTAL HOSE TUBE") == "Linear"


_LIVE_1001898 = [
    ("14500-1", "PEDESTAL TOP PLATE", "Cad"),
    ("1001880-2", "PEDESTAL TUBE", "Linear"),
    ("29860-4", "PEDESTAL BRACE ANGLE", "Linear"),
    ("14501-1", "RESERVOIR TOP PLATE", "Cad"),
    ("1005966-1", "PEDESTAL BOTTOM PLATE", "Cad"),
    ("50137-5", "3/4 NPT HALF COUPLING", "Component"),
    ("50115-7", "1 1/4 NPT NIPPLE X 4 LG.", "Component"),
    ("50030-5", "3/4 NPT COUPLING", "Component"),
    ("8166-1", "FILLER NECK", "Component"),
    ("9905-1", "MOUNTING PLATE, EMER POWER", "Cad"),
    ("33637-1", "1 1/4 RETURN TUBE", "Linear"),
    ("10081-2", "PEDESTAL HOSE TUBE", "Linear"),
    ("50006-5", "3/4 NPT MAGNETIC PLUG", "Component"),
    ("50122-1", "1 1/4 NPT PIPE CAP", "Component"),
    ("29860-3", "PEDESTAL BRACE ANGLE", "Linear"),
    ("1005940-1", "PEDESTAL GUSSET", "Cad"),
    ("50029-7", "1 1/4 90 STREET ELBOW", "Component"),
]


def test_live_1001898_classify_matches_kyle():
    got = {pn: classify_sectura_item(f"{pn} {desc}") for pn, desc, _want in _LIVE_1001898}
    want = {pn: cat for pn, _desc, cat in _LIVE_1001898}
    assert got == want
    assert sum(1 for c in got.values() if c == "Cad") == 5
    assert sum(1 for c in got.values() if c == "Linear") == 5
    assert sum(1 for c in got.values() if c == "Component") == 7


def test_kyle_description_formats():
    cad = format_cad_description(
        "14500-1", thickness=0.25, grade="A36", width_in=12, length_in=12
    )
    assert cad == '14500-1 - 1/4" A36 12 in x 12 in'
    linear = format_linear_description(
        "12689-1", sku="RCT2 12X1 12X.065-A513", length_in=44.375
    )
    assert linear == "12689-1 - RCT2 12X1 12X.065-A513 - 44.375"
    assert format_component_description("50115-7 1 1/4 NPT NIPPLE X 4 LG.") == (
        "1 1/4 NPT NIPPLE X 4 LG."
    )
    assert format_component_description("14500-1") == ""
    asm = format_assembly_description("1001898-1", "PEDESTAL WELDMENT")
    assert asm == "1001898-1 - PEDESTAL WELDMENT"
    assert format_assembly_description("1001898-1", "1001898") == "1001898-1"
    from secturafab.item_desc import looks_like_drawing_sheet

    assert looks_like_drawing_sheet(22.0, 28.5) is True
    assert looks_like_drawing_sheet(7.5, 10.0) is False
    sheet_cad = format_cad_description(
        "14501-1",
        thickness=0.25,
        grade="A36",
        width_in=22.0,
        length_in=28.5,
        noun="RESERVOIR TOP PLATE",
    )
    assert "22" not in sheet_cad
    assert "RESERVOIR TOP PLATE" in sheet_cad
    assert sheet_cad != "14501-1"


def test_time_org_and_pedestal_folder_title():
    folder = (
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
        r"\Engineering\Customer Drawings\Time\Pedestal Weldment - 1001898-1"
    )
    assert detect_organization_from_folder(folder) == "Time Manufacturing Waco"
    assert detect_organization(pdf_path=None, library_folder=folder) == (
        "Time Manufacturing Waco"
    )
    assert detect_organization(
        pdf_path=None,
        library_folder="Pedestal Weldment - 1001898-1",
        extra_paths=[
            r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents"
            r"\Engineering\Customer Drawings\Time"
        ],
    ) == "Time Manufacturing Waco"
    assert title_from_library_folder(folder, part_key="1001898-1") == "PEDESTAL WELDMENT"
    assert title_from_library_folder(
        "Pedestal Weldment - 1001898-1", part_key="1001898-1"
    ) == "PEDESTAL WELDMENT"
    assert extract_assembly_description(
        part_key="1001898-1",
        library_folder=folder,
    ) == "PEDESTAL WELDMENT"
    assert (
        format_assembly_description("1001898-1", "PEDESTAL WELDMENT")
        == "1001898-1 - PEDESTAL WELDMENT"
    )


def test_linear_bind_sets_product_id_not_name():
    catalog = [
        {
            "ID": "pid-rct",
            "ProductName": "RCT2 12X1 12X.065-A513",
            "ShapeName": "Mechanical Tube",
            "MaterialGrade": "A513",
            "Dim1": 1.5,
            "Active": True,
        }
    ]
    pid, sku, _note = match_linear_product(
        catalog, "12689-1 TUBE", material="A513"
    )
    assert pid == "pid-rct"
    assert sku == "RCT2 12X1 12X.065-A513"

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "L8",
                "Description": "1001880-2 PEDESTAL TUBE",
                "Category": "Linear",
                "IsLinear": True,
                "ProductName": "should-clear",
                "Length": 44.375,
            }
        ]
    }
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    notes = bind_linear_product_ids(
        client, "qid", material="A513", catalog=catalog
    )
    payload = client.request.call_args.kwargs["json"]
    item = payload["ItemList"][0]
    assert item["ProductID"] == "pid-rct"
    assert item.get("ProductName") in {None, ""}
    assert item["Machine"] == "Saw"
    assert "1001880-2" in item["Description"]
    assert "RCT2" in item["Description"]
    assert any("ProductID" in n for n in notes)


def test_cookie_less_push_does_not_graft_profile(tmp_path: Path):
    pdf = tmp_path / "1001898-1.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Customer Drawings" / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    client = MagicMock()
    client.config.website_cookie = ""
    from tests.fixtures.live_get_1001898 import gold_1001898_get

    client.get_json.return_value = gold_1001898_get()
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="1001898-1"
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(
            [{"part_no": "14500-1", "qty": 1, "description": "PEDESTAL TOP PLATE"}],
            [],
        ),
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ) as finalize, patch(
        "secturafab.pdf_assembly_ops.build_pdf_only_assembly",
        return_value=["Imported Cad", "Skipped grafted Profile"],
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=["Set Organization: Time Manufacturing Waco"],
    ):
        result = service.push_job(
            title="1001898",
            pdf_filename="1001898-1.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={
                "library": {
                    "part_key": "1001898-1",
                    "folder": str(lib),
                }
            },
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=89,
        )

    assert result.ok is True
    assert finalize.called
    assert finalize.call_args.kwargs.get("attach_profile") in {None, False}
    desc = create_q.call_args.kwargs.get("description") or ""
    assert "PEDESTAL WELDMENT" in desc
    assert desc != "1001898"
    assert any("Skipped grafted Profile" in n for n in (result.notes or []))
    assert any(
        "Time Manufacturing Waco" in n or "Organization" in n or "Set Organization" in n
        for n in (result.notes or [])
    ) or detect_organization(library_folder=lib) == "Time Manufacturing Waco"


def test_rename_imported_descriptions_is_gone():
    import secturafab.pdf_assembly_ops as pdf_ops

    assert not hasattr(pdf_ops, "_rename_imported_descriptions")
    assert hasattr(pdf_ops, "_apply_kyle_line_descriptions")


def test_categorize_live_shaped_items_sets_product_type():
    from secturafab.pdf_assembly_ops import categorize_pdf_imported_items

    items = [
        {"ID": "a", "Description": "50029-7", "ProductType": 100, "IsPart": True, "Machine": "Laser"},
        {"ID": "b", "Description": "29860-3", "ProductType": 100, "IsPart": True, "Machine": "Laser"},
        {"ID": "c", "Description": "1005940-1", "ProductType": 100, "IsPart": True, "Machine": "Laser"},
        {"ID": "root", "Description": "1001898-1", "ProductType": 300, "IsAssembly": True},
    ]
    client = MagicMock()
    client.get_json.return_value = {"ItemList": items}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    notes = categorize_pdf_imported_items(
        client,
        "qid",
        bom_rows=[
            {"part_no": "50029-7", "description": "1 1/4 90 STREET ELBOW", "qty": 1},
            {"part_no": "29860-3", "description": "PEDESTAL BRACE ANGLE", "qty": 2},
            {"part_no": "1005940-1", "description": "PEDESTAL GUSSET", "qty": 8},
        ],
    )
    saved = client.request.call_args.kwargs["json"]["ItemList"]
    by_id = {it["ID"]: it for it in saved}
    assert by_id["a"]["ProductType"] == 200
    assert by_id["a"]["Category"] == "Component"
    assert by_id["b"]["ProductType"] == 10
    assert by_id["b"]["IsLinear"] is True
    assert by_id["b"]["Machine"] == "Saw"
    assert by_id["c"]["ProductType"] == 100
    assert by_id["c"]["IsPlate"] is True
    assert any("Component: 1" in n for n in notes)
    assert by_id["root"]["ProductType"] == 300


def test_apply_item_categories_skips_assembly_and_binds_types():
    service = SecturaFabPushService(client=MagicMock())
    items = [
        {
            "ID": "root",
            "Description": "1001898-1 - PEDESTAL WELDMENT",
            "ProductType": 300,
            "IsAssembly": True,
        },
        {
            "ID": "lin",
            "Description": "29860-3",
            "ProductType": 100,
            "Machine": "Laser",
        },
        {
            "ID": "fit",
            "Description": "50029-7",
            "ProductType": 100,
            "Machine": "Laser",
        },
    ]
    service.client.get_json.return_value = {"ItemList": items}
    save = MagicMock()
    save.status_code = 200
    service.client.request.return_value = save
    service.apply_item_categories(
        "qid",
        bom_rows=[
            {"part_no": "29860-3", "description": "PEDESTAL BRACE ANGLE"},
            {"part_no": "50029-7", "description": "1 1/4 90 STREET ELBOW"},
        ],
    )
    saved = service.client.request.call_args.kwargs["json"]["ItemList"]
    by_id = {it["ID"]: it for it in saved}
    assert by_id["root"]["ProductType"] == 300
    assert by_id["root"]["IsAssembly"] is True
    assert by_id["lin"]["ProductType"] == 10
    assert by_id["lin"]["Machine"] == "Saw"
    assert by_id["fit"]["ProductType"] == 200


def test_finalize_qty_mismatch_does_not_graft_profile():
    from secturafab.finalize_ops import finalize_quote_ops

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {"ID": "p1", "Description": "14500-1", "ProductType": 100, "Quantity": 1},
        ]
    }
    with patch("secturafab.finalize_ops.wait_for_quote_settle", return_value=[]), patch(
        "secturafab.finalize_ops.count_profile_items", return_value=0
    ), patch(
        "secturafab.finalize_ops.assembly_has_weld", return_value=True
    ), patch(
        "secturafab.finalize_ops.bom_qty_mismatches", return_value=["14500-1"]
    ), patch(
        "secturafab.finalize_ops.apply_bom_quantities", return_value=["qty"]
    ), patch(
        "secturafab.finalize_ops.ensure_laser_profile_ops", return_value=["Attached Profile"]
    ) as profile, patch(
        "secturafab.finalize_ops.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.finalize_ops.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.finalize_ops.rollup_assembly_costs", return_value=[]
    ):
        finalize_quote_ops(
            client,
            "qid",
            material="A36",
            thickness="0.25",
            times=None,
            part_key="1001898-1",
            bom_rows=[{"part_no": "14500-1", "qty": 1}],
            attempts=1,
            attach_profile=False,
        )
    profile.assert_not_called()
