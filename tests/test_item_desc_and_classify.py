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
    assert classify_sectura_item("14500-1 PEDESTAL TOP PLATE") == "Component"
    assert classify_sectura_item("1001880-2 PEDESTAL TUBE") == "Cad"
    assert classify_sectura_item("29860-4 PEDESTAL BRACE ANGLE") == "Linear"
    assert classify_sectura_item("50137-5 3/4 NPT HALF COUPLING") == "Component"
    assert classify_sectura_item("50115-7 1 1/4 NPT NIPPLE X 4 LG.") == "Component"
    assert classify_sectura_item("50006-5 3/4 NPT MAGNETIC PLUG") == "Component"
    assert classify_sectura_item("50122-1 1 1/4 NPT PIPE CAP") == "Component"
    assert classify_sectura_item("8166-1 FILLER NECK") == "Component"
    assert classify_sectura_item("FILLER - NECK") == "Component"
    assert classify_sectura_item("FILLER NECK") == "Component"
    assert classify_sectura_item("50029-7 1 1/4 90 STREET ELBOW") == "Component"
    assert classify_sectura_item("10081-2 PEDESTAL HOSE TUBE") == "Linear"
    assert classify_sectura_item("28109 COMP LINK ASSY WITH INSERT") == "Assembly"
    assert classify_sectura_item(
        "28248 COMPLINK END WELDMENT INSULATED"
    ) == "Assembly"
    assert classify_sectura_item("1007038-1 2.5×5×0.25 A500B") == "Linear"
    assert classify_sectura_item("1007038-1 2.5 X 5 X 0.25 A500") == "Linear"


_LIVE_1001898 = [
    ("14500-1", "PEDESTAL TOP PLATE", "Component"),
    ("1001880-2", "PEDESTAL TUBE", "Cad"),
    ("29860-4", "PEDESTAL BRACE ANGLE", "Linear"),
    ("14501-1", "RESERVOIR TOP PLATE", "Cad"),
    ("1005966-1", "PEDESTAL BOTTOM PLATE", "Component"),
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
    assert sum(1 for c in got.values() if c == "Cad") == 4
    assert sum(1 for c in got.values() if c == "Linear") == 4
    assert sum(1 for c in got.values() if c == "Component") == 9


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
    assert format_component_description("1 1/4 90 STREET ELBOW", part_no="1") == (
        "1 1/4 90 STREET ELBOW"
    )
    from secturafab.item_desc import format_component_line, match_bom_part_no

    assert format_component_line("50029-7", "1 1/4 90 STREET ELBOW") == (
        "50029-7 - 1 1/4 90 STREET ELBOW"
    )
    assert format_component_line("50006-5", "3/4 NPT MAGNETIC PLUG") == (
        "50006-5 - 3/4 NPT MAGNETIC PLUG"
    )
    assert format_component_line("8166-1", "FILLER NECK") == "8166-1 - FILLER NECK"
    rows = [
        {"part_no": "50029-7", "description": "1 1/4 90 STREET ELBOW"},
        {"part_no": "50006-5", "description": "3/4 NPT MAGNETIC PLUG"},
        {"part_no": "50030-5", "description": "3/4 NPT COUPLING"},
        {"part_no": "50137-5", "description": "3/4 NPT HALF COUPLING"},
        {"part_no": "8166-1", "description": "FILLER NECK"},
    ]
    assert match_bom_part_no("1 - 1/4 90 STREET ELBOW", rows) == "50029-7"
    assert match_bom_part_no("500065 - 3/4 NPT MAGNETIC PLUG", rows) == "50006-5"
    assert match_bom_part_no("34 - 3/4 NPT COUPLING", rows) == "50030-5"
    assert match_bom_part_no("FILLER - NECK", rows) == "8166-1"
    cad_rows = [
        {"part_no": "14500-1", "description": "PEDESTAL TOP PLATE"},
        {"part_no": "29860-3", "description": "PEDESTAL BRACE ANGLE"},
        {"part_no": "29860-4", "description": "PEDESTAL BRACE ANGLE"},
    ]
    assert match_bom_part_no("14500", cad_rows) == "14500-1"
    assert match_bom_part_no("29860", cad_rows) == "29860"
    assert format_component_description("14500-1") == ""
    asm = format_assembly_description("1001898-1", "PEDESTAL WELDMENT")
    assert asm == "1001898-1 - PEDESTAL WELDMENT"
    assert format_assembly_description("1001898-1", "1001898") == "1001898-1"
    from secturafab.item_desc import looks_like_drawing_sheet, looks_like_page_outline

    assert looks_like_drawing_sheet(22.0, 28.5) is True
    assert looks_like_drawing_sheet(7.5, 10.0) is False
    assert looks_like_page_outline(1.0, 2.0) is True
    assert looks_like_page_outline(1.0, 16.0) is True
    assert looks_like_page_outline(5.25, 5.75) is False
    assert looks_like_page_outline(2.0, 9.0) is False
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
        service, "allocate_quote_number", return_value="remint-ok"
    ), patch.object(
        service, "finish_pdf_files", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(
            [{"part_no": "14500-1", "qty": 1, "description": "PEDESTAL TOP PLATE"}],
            [],
        ),
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch.object(
        service, "nest_after_finish", return_value=[]
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

    assert result.ok is False
    desc = create_q.call_args.kwargs.get("description") or ""
    assert "PEDESTAL WELDMENT" in desc
    assert desc != "1001898"
    blob = " ".join(result.notes or []) + " " + (result.error or "")
    assert "Chrome" in blob or "session" in blob.lower()
    assert "falling back" not in blob
    assert any(
        "Time Manufacturing Waco" in n or "Organization" in n or "Set Organization" in n
        for n in (result.notes or [])
    ) or detect_organization(library_folder=lib) == "Time Manufacturing Waco"


def test_plate_catalog_grade_and_match():
    from secturafab.plate_ops import (
        catalog_plate_grade,
        fetch_plate_catalog,
        is_full_sheets_plates_catalog,
        match_plate_product,
        plate_config_rows,
        plate_config_total,
        plate_sku_missing_after_lookup,
        tenant_plate_product_id,
    )
    from tests.fixtures.live_21682_1 import plate_config_miss_payload
    from tests.fixtures.live_sheets_plates import (
        PL7_GA_A36,
        PL7_GA_A36_ID,
        sheets_plates_catalog_rows,
        sheets_plates_page_payload,
    )

    assert catalog_plate_grade("A572 Grade 50") == "A572"
    assert catalog_plate_grade("A572 G50") == "A572"
    assert catalog_plate_grade("A36") == "A36"
    catalog = [
        {
            "ID": "pl-a36",
            "ProductName": "PL1/4-A36",
            "MaterialGrade": "A36",
            "Thickness": 0.25,
            "Active": True,
        },
        {
            "ID": "pl-a572",
            "ProductName": "PL1/4-A572",
            "MaterialGrade": "A572",
            "Thickness": 0.25,
            "Active": True,
        },
        {
            "ID": "pl-half",
            "ProductName": "PL1/2-A36",
            "MaterialGrade": "A36",
            "Thickness": 0.5,
            "Active": True,
        },
    ]
    hit = match_plate_product(catalog, thickness="1/4", material="A572 Grade 50")
    assert hit["ID"] == "pl-a572"
    hit36 = match_plate_product(catalog, thickness=0.5, material="A36")
    assert hit36["ID"] == "pl-half"

    gold = [dict(PL7_GA_A36)]
    gold_hit = match_plate_product(gold, thickness=0.1875, material="A36")
    assert gold_hit["ID"] == PL7_GA_A36_ID
    assert gold_hit["ProductName"] == "PL7 Ga-A36"
    assert tenant_plate_product_id(gold_hit) == PL7_GA_A36_ID
    assert plate_sku_missing_after_lookup(
        gold, thickness=0.1875, material="A36"
    ) is False

    miss = plate_config_miss_payload()
    assert plate_config_total(miss) == 3
    rows = plate_config_rows(miss)
    assert len(rows) == 3
    assert is_full_sheets_plates_catalog(rows) is False
    assert match_plate_product(rows, thickness=0.5, material="DOMEX/WELDOX") is None
    # Total=3-only is not a successful full-catalog read.
    assert plate_sku_missing_after_lookup(
        rows, thickness=0.5, material="DOMEX/WELDOX"
    ) is False
    assert plate_sku_missing_after_lookup([], thickness=0.5, material="DOMEX/WELDOX") is False

    full = sheets_plates_catalog_rows()
    assert is_full_sheets_plates_catalog(full) is True
    assert match_plate_product(full, thickness=0.1875, material="A36")["ProductName"] == (
        "PL7 Ga-A36"
    )
    assert match_plate_product(full, thickness=0.5, material="DOMEX/WELDOX") is None
    assert plate_sku_missing_after_lookup(
        full, thickness=0.5, material="DOMEX/WELDOX"
    ) is True

    client = MagicMock()
    client.read_data_plate_config.return_value = plate_config_miss_payload()
    client.get_json.return_value = {"Results": [], "HasNext": False}
    assert fetch_plate_catalog(client) == []
    client.get_json.return_value = sheets_plates_page_payload()
    fetched = fetch_plate_catalog(client)
    assert any(r.get("ProductName") == "PL7 Ga-A36" for r in fetched)
    assert client.get_json.call_args.args[0].startswith("v1/product/plate")


def test_purchased_component_keeps_dashed_pn():
    from secturafab.component_ops import ensure_purchased_components

    client = MagicMock()
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "k1",
                "Description": "8166-1 - FILLER NECK",
                "ProductType": 100,
            }
        ]
    }
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    ensure_purchased_components(
        client, "qid", purchased_keys={"8166-1": "FILLER NECK"}
    )
    saved = client.request.call_args.kwargs["json"]["ItemList"][0]
    assert saved["Description"] == "8166-1 - FILLER NECK"
    assert saved["ProductType"] == 200


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
    assert by_id["b"]["ProductType"] == 40
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
    assert by_id["lin"]["ProductType"] == 40
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


# Kyle 1001898-1 cheat sheet + leftover misclassify must fail closed.
# hose guard → Component, ≤3/4 plate → Component, >3/4 plate → Cad.
_CLASSIFY_LOCK_CASES = [
    ("14501-1", "RESERVOIR TOP PLATE", None, "Cad"),
    ("1001880-2", "PEDESTAL TUBE", None, "Cad"),
    ("9905-1", "MOUNTING PLATE, EMER POWER", None, "Cad"),
    ("1005940-1", "PEDESTAL GUSSET", None, "Cad"),
    ("29860-3", "PEDESTAL BRACE ANGLE", None, "Linear"),
    ("29860-4", "PEDESTAL BRACE ANGLE", None, "Linear"),
    ("10081-2", "PEDESTAL HOSE TUBE", None, "Linear"),
    ("33637-1", "1 1/4 RETURN TUBE", None, "Linear"),
    ("21689-1", "HOSE GUARD", None, "Linear"),
    ("14500-1", "PEDESTAL TOP PLATE", None, "Component"),
    ("1005966-1", "PEDESTAL BOTTOM PLATE", None, "Component"),
    ("50137-5", "3/4 NPT HALF COUPLING", None, "Component"),
    ("50115-7", "1 1/4 NPT NIPPLE X 4 LG.", None, "Component"),
    ("50030-5", "3/4 NPT COUPLING", None, "Component"),
    ("8166-1", "FILLER NECK", None, "Component"),
    ("50006-5", "3/4 NPT MAGNETIC PLUG", None, "Component"),
    ("50122-1", "1 1/4 NPT PIPE CAP", None, "Component"),
    ("50029-7", "1 1/4 90 STREET ELBOW", None, "Component"),
    ("base-075", '3/4" A36 PLATE', 0.75, "Cad"),
    ("base-125", '1.25" A572 PLATE', 1.25, "Component"),
    ("formed", "FORMED ANGLE 1/4 A36 PLATE", 0.25, "Cad"),
    ("weld", "1001898-1 PEDESTAL WELDMENT", None, "Assembly"),
]


def test_classify_lock_1001898_cheat_sheet_and_thickness():
    from secturafab.push import classify_bom_row, classify_image_files_item

    got = {}
    for pn, noun, thk, want in _CLASSIFY_LOCK_CASES:
        cat = classify_bom_row(
            {"part_no": pn, "description": noun, "thickness_in": thk},
            thickness=thk,
        )
        got[pn] = cat
        assert cat == want, f"{pn} {noun} → {cat}, want {want}"
        assert classify_sectura_item(f"{pn} {noun}", thk) == want
        assert classify_image_files_item(f"{pn} {noun}", thk) == want
    assert got["21689-1"] == "Linear"
    assert got["21689-1"] != "Component"
    assert got["base-075"] == "Cad"
    assert got["base-075"] != "Component"
    assert got["base-125"] == "Component"
    assert got["base-125"] != "Cad"
    assert got["10081-2"] == "Linear"
    assert got["50122-1"] == "Component"
    assert classify_bom_row(
        {"part_no": "99901-1", "description": "PEDESTAL BASE PLATE", "thickness_in": 1.25}
    ) == "Component"
    assert classify_bom_row(
        {"part_no": "99902-1", "description": "PEDESTAL BASE PLATE", "thickness_in": 0.75}
    ) == "Cad"
    assert classify_sectura_item("HOSEGUARD FORMED VIEW") == "Linear"
    assert classify_sectura_item("HOSEGUARD FORMED VIEW") != "Component"


def test_leftover_hose_guard_and_plate_reclassify_on_push_path():
    from secturafab.component_ops import ensure_purchased_components
    from secturafab.pdf_assembly_ops import categorize_pdf_imported_items

    items = [
        {
            "ID": "hose",
            "Description": "21689-1 HOSE GUARD",
            "ProductType": 200,
            "Category": "Component",
            "IsPart": True,
        },
        {
            "ID": "thin",
            "Description": '3/4" A36 PLATE',
            "ProductType": 200,
            "Category": "Component",
            "IsPart": True,
        },
        {
            "ID": "thick",
            "Description": '1.25" A572 PLATE',
            "ProductType": 100,
            "Category": "Cad",
            "IsPlate": True,
        },
        {
            "ID": "root",
            "Description": "1001898-1 - PEDESTAL WELDMENT",
            "ProductType": 300,
            "IsAssembly": True,
        },
    ]
    client = MagicMock()
    client.get_json.return_value = {"ItemList": [dict(it) for it in items]}
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    categorize_pdf_imported_items(
        client,
        "qid",
        bom_rows=[
            {"part_no": "21689-1", "description": "HOSE GUARD", "qty": 1},
            {"part_no": "thin-1", "description": '3/4" A36 PLATE', "qty": 1},
            {"part_no": "thick-1", "description": '1.25" A572 PLATE', "qty": 1},
        ],
    )
    saved = {it["ID"]: it for it in client.request.call_args.kwargs["json"]["ItemList"]}
    assert saved["hose"]["Category"] == "Linear"
    assert saved["hose"]["ProductType"] == 10
    assert saved["hose"]["Machine"] == "Saw"
    assert saved["thin"]["Category"] == "Cad"
    assert saved["thin"]["ProductType"] == 100
    assert saved["thick"]["Category"] == "Component"
    assert saved["thick"]["ProductType"] == 200
    assert saved["root"]["ProductType"] == 300

    service = SecturaFabPushService(client=MagicMock())
    leftover = [dict(it) for it in items]
    leftover[0]["Description"] = "21689-1"
    service.client.get_json.return_value = {"ItemList": leftover}
    service.client.request.return_value = save
    service.apply_item_categories(
        "qid",
        bom_rows=[
            {"part_no": "21689-1", "description": "HOSE GUARD"},
            {"part_no": "thin-1", "description": '3/4" A36 PLATE'},
            {"part_no": "thick-1", "description": '1.25" A572 PLATE'},
        ],
    )
    applied = {it["ID"]: it for it in service.client.request.call_args.kwargs["json"]["ItemList"]}
    assert applied["hose"]["Category"] == "Linear"
    assert applied["thin"]["Category"] == "Cad"
    assert applied["thick"]["Category"] == "Component"

    purchased_client = MagicMock()
    purchased_client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "hose",
                "Description": "21689-1 HOSE GUARD",
                "ProductType": 100,
                "Category": "Cad",
            }
        ]
    }
    purchased_client.request.return_value = save
    notes = ensure_purchased_components(
        purchased_client, "qid", purchased_keys={"21689-1": "CAP"}
    )
    assert purchased_client.request.call_count == 0
    assert any("No purchased" in n or "Component" in n for n in notes) or notes == [
        "No purchased/hardware lines matched for Component"
    ]


def test_qa_fail_closes_leftover_misclassify():
    from secturafab.qa_harness import evaluate_quote_get

    payload = {
        "Description": "PEDESTAL WELDMENT",
        "OrganizationName": "Time Manufacturing Waco",
        "PrimaryOrganizationID": "b7dbc294-3fd2-43aa-99be-268a6c4fce14",
        "OrganizationList": [{"OrganizationName": "Time Manufacturing Waco"}],
        "ItemList": [
            {
                "ID": "asm",
                "Description": "1001898-1 - PEDESTAL WELDMENT",
                "ProductType": 300,
                "IsAssembly": True,
            },
            {
                "ID": "hose",
                "Description": "21689-1 HOSE GUARD",
                "ProductType": 200,
                "Category": "Component",
            },
            {
                "ID": "thin",
                "Description": '3/4" A36 PLATE',
                "ProductType": 200,
                "Category": "Component",
            },
            {
                "ID": "thick",
                "Description": '1.25" A572 PLATE',
                "ProductType": 100,
                "Category": "Cad",
            },
        ],
    }
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        require_org=False,
        bom_rows=[
            {"part_no": "21689-1", "description": "HOSE GUARD", "qty": 1},
            {"part_no": "thin-1", "description": '3/4" A36 PLATE', "qty": 1},
            {"part_no": "thick-1", "description": '1.25" A572 PLATE', "qty": 1},
        ],
    )
    assert result.ok is False
    blob = " ".join(result.failures)
    assert "HOSE GUARD" in blob and "Linear" in blob
    assert "3/4" in blob and "Cad" in blob
    assert "1.25" in blob and "Component" in blob


def test_purchased_map_cannot_force_hose_guard_component():
    service = SecturaFabPushService(client=MagicMock())
    with patch(
        "secturafab.push.find_purchased_part_keys",
        return_value={"21689-1": "CAP", "216891": "CAP"},
    ):
        classified, _notes = service.classify_cadimport_rows(
            [
                {
                    "SourceDataID": "h",
                    "Name": "21689-1 HOSE GUARD",
                    "Qty": 1,
                    "ErrorStatus": 0,
                }
            ],
            default_material="A36",
            default_thickness="0.25",
            bom_rows=[{"part_no": "21689-1", "description": "HOSE GUARD", "qty": 1}],
            library={},
            extra_pdfs=None,
            qty=1,
        )
    assert classified[0]["Category"] == "Linear"
    assert classified[0]["Category"] != "Component"


def test_plan_weldment_uses_row_thickness_for_thick_plate():
    from secturafab.pdf_assembly_ops import plan_weldment_lines

    planned = plan_weldment_lines(
        [
            {
                "part_no": "99903-1",
                "qty": 1,
                "description": "PEDESTAL BASE PLATE",
                "thickness_in": 1.25,
            },
            {
                "part_no": "99904-1",
                "qty": 1,
                "description": "PEDESTAL BASE PLATE",
                "thickness_in": 0.75,
            },
            {"part_no": "21689-1", "qty": 1, "description": "HOSE GUARD"},
        ]
    )
    by_pn = {p["part_no"]: p for p in planned}
    assert by_pn["99903-1"]["category"] == "Component"
    assert by_pn["99903-1"]["ProductType"] == 200
    assert by_pn["99904-1"]["category"] == "Cad"
    assert by_pn["99904-1"]["ProductType"] == 100
    assert by_pn["21689-1"]["category"] == "Linear"
