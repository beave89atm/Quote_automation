"""GET-shaped QA harness — fails the build on Kyle's live 1001898-1 misses."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from secturafab.item_desc import title_from_bom_family
from secturafab.line_item_ops import cad_new_line_calculators, linear_new_line_calculators
from secturafab.qa_harness import assert_quote_get_qa, evaluate_quote_get
from tests.fixtures.live_get_1001898 import (
    ASSEMBLY_DESC,
    HEADER_DESC,
    TIME_ORG,
    gold_1001898_get,
)
from tests.fixtures.time_gold import DASH_1001898


def _bom_rows() -> list[dict]:
    return [
        {"part_no": pn, "qty": qty, "description": desc}
        for _i, qty, pn, desc in DASH_1001898
    ]


def test_gold_1001898_get_passes_checklist():
    payload = gold_1001898_get()
    result = assert_quote_get_qa(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is True
    assert payload["OrganizationName"] == TIME_ORG
    assert payload["Description"] == "PEDESTAL WELDMENT"
    assert payload["ItemList"][0]["Description"] == "1001898-1 - PEDESTAL WELDMENT"


@pytest.mark.parametrize(
    "fail",
    ["org", "bare_pn", "no_ops", "empty_fields", "eaten_pn", "filler_cad", "grafted_ops", "blank_unit_cost"],
)
def test_failed_live_get_shapes_fail_the_build(fail: str):
    payload = gold_1001898_get(fail=fail)
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is False
    assert result.failures
    with pytest.raises(AssertionError, match="Live GET QA failed"):
        assert_quote_get_qa(
            payload,
            part_key="1001898-1",
            expected_org=TIME_ORG,
            expected_header=HEADER_DESC,
            expected_assembly_title=ASSEMBLY_DESC,
            bom_rows=_bom_rows(),
        )


def test_empty_cad_linear_fields_fail_live_get():
    payload = gold_1001898_get(fail="empty_fields")
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is False
    blob = " ".join(result.failures)
    assert "Material" in blob
    assert "Thickness" in blob
    assert "Saw" in blob or "Machine" in blob
    assert "cut length" in blob


def test_eaten_component_pn_and_filler_cad_fail_live_get():
    eaten = evaluate_quote_get(
        gold_1001898_get(fail="eaten_pn"),
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert eaten.ok is False
    blob = " ".join(eaten.failures)
    assert "50029-7" in blob
    assert "8166-1" in blob or "FILLER" in blob
    filler = evaluate_quote_get(
        gold_1001898_get(fail="filler_cad"),
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert filler.ok is False
    assert any("Cad" in f and "8166-1" in f for f in filler.failures)


def test_new_line_item_pack_is_not_profile_datapart():
    assert cad_new_line_calculators() == [
        "Laser",
        "Drafting",
        "Laser-Setup",
        "Sheet Loading",
        "Deburr",
    ]
    assert linear_new_line_calculators() == ["Saw", "Saw Setup"]
    from secturafab.line_item_ops import (
        apply_cad_new_line_ops,
        apply_linear_new_line_ops,
        build_cad_new_line_ops,
        item_has_grafted_cad_tags,
        item_has_grafted_saw_tags,
        stamp_new_line_item_packs,
    )

    grafted = {"ID": "x", "OperationCostList": build_cad_new_line_ops("x")}
    assert item_has_grafted_cad_tags(grafted) is True
    assert apply_cad_new_line_ops(grafted) is False
    assert apply_linear_new_line_ops({"OperationCostList": []}) is False
    from secturafab.line_item_ops import build_linear_new_line_ops

    assert item_has_grafted_saw_tags({"BadgeString": "Saw"})
    assert item_has_grafted_saw_tags(
        {"OperationCostList": build_linear_new_line_ops("l"), "BadgeString": "Saw,Saw Setup"}
    )
    notes = stamp_new_line_item_packs(MagicMock(), "qid")
    assert notes
    assert all("Skipped grafted" in n for n in notes)


def test_push_job_fails_closed_when_live_get_has_empty_ops(tmp_path):
    from unittest.mock import MagicMock, patch

    from secturafab.push import SecturaFabPushService

    pdf = tmp_path / "1001898.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = gold_1001898_get(fail="no_ops")
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(service, "allocate_quote_number", return_value="1001898-1"), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(_bom_rows(), []),
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.build_pdf_only_assembly",
        return_value=["built"],
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=["Set Organization: Time Manufacturing Waco"],
    ), patch(
        "secturafab.push.persist_quote_header", return_value=[]
    ), patch(
        "secturafab.push.persist_classified_item_fields", return_value=[]
    ):
        result = service.push_job(
            title="1001898",
            pdf_filename="1001898.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {"part_key": "1001898-1", "folder": str(lib)}},
            times={},
            job_id=91,
        )
    assert result.ok is False
    assert "Live GET QA failed" in (result.error or "")
    assert any("Laser" in f or "Saw" in f or "QA failed" in f for f in [result.error or ""])


def test_bare_folder_push_still_uses_bom_pedestal_title(tmp_path):
    from unittest.mock import MagicMock, patch

    from secturafab.push import SecturaFabPushService

    pdf = tmp_path / "1001898.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Time" / "1001898-1"
    lib.mkdir(parents=True)
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = gold_1001898_get()
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="1001898-1"
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(_bom_rows(), []),
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.build_pdf_only_assembly",
        return_value=["built"],
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ), patch(
        "secturafab.push.persist_quote_header", return_value=[]
    ):
        result = service.push_job(
            title="1001898",
            pdf_filename="1001898.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {"part_key": "1001898-1", "folder": str(lib)}},
            times={},
            job_id=91,
        )
    assert result.ok is True
    assert create_q.call_args.kwargs.get("description") == HEADER_DESC


def test_push_addplate_then_addlinear_without_graft(tmp_path):
    from unittest.mock import MagicMock, patch

    from secturafab.push import SecturaFabPushService

    pdf = tmp_path / "1001898.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Time" / "1001898-1"
    lib.mkdir(parents=True)
    order: list[str] = []
    persist_calls: list[dict] = []

    def _persist(*_a, **kwargs):
        persist_calls.append(kwargs)
        order.append("linear" if kwargs.get("persist_cad") is False else "cad")
        return []

    def _header(*_a, **_k):
        order.append("header")
        return []

    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = gold_1001898_get()
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(
        service, "allocate_quote_number", return_value="1001898-1"
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(_bom_rows(), []),
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.pdf_assembly_ops.build_pdf_only_assembly",
        return_value=["built"],
    ), patch(
        "secturafab.push.persist_quote_header", side_effect=_header
    ), patch(
        "secturafab.push.persist_classified_item_fields", side_effect=_persist
    ), patch(
        "secturafab.push.retype_linears_to_pt10_keep_persist", return_value=[]
    ):
        result = service.push_job(
            title="1001898",
            pdf_filename="1001898.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {"part_key": "1001898-1", "folder": str(lib)}},
            times={},
            job_id=91,
        )
    assert result.ok is True
    assert order[:3] == ["cad", "linear", "header"]
    assert "stamp" not in order
    assert persist_calls[0].get("persist_linear") is False
    assert persist_calls[1].get("persist_cad") is False
    assert persist_calls[1].get("persist_linear") is True
    assert persist_calls[1].get("retry_linear") is True


def test_parse_live_cad_description_onto_fields():
    from secturafab.item_desc import parse_cad_desc_fields

    parsed = parse_cad_desc_fields('14500-1 - 1/4" A572 Grade 50 PEDESTAL TOP PLATE')
    assert parsed["thickness"] == "1/4"
    assert "A572" in parsed["material"]
    flats = parse_cad_desc_fields('14500-1 - 1/4" A36 8 in x 10 in')
    assert flats["width_in"] == 8.0
    assert flats["length_in"] == 10.0


def test_list_orgs_still_searches_time_after_other_customers():
    from secturafab.org_ops import find_organization_by_name

    client = MagicMock()

    def _get(path: str):
        p = str(path)
        if "Search=Time" in p or "Search=TIME" in p or "Name=Time" in p:
            return {
                "HasNext": False,
                "Results": [
                    {"ID": "time-real", "OrganizationName": "TIME - Waco", "Active": True}
                ],
            }
        return {
            "HasNext": False,
            "Results": [{"ID": "propell", "OrganizationName": "Propell", "Active": True}],
        }

    client.get_json.side_effect = _get
    org = find_organization_by_name(client, "Time Manufacturing Waco")
    assert org is not None
    assert org["ID"] == "time-real"


def test_persist_uses_addplate_addlinear_and_get_verifies():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    empty = {
        "ItemList": [
            {
                "ID": "c1",
                "Description": '14500-1 - 1/4" A572 Grade 50 PEDESTAL TOP PLATE',
                "ProductType": 100,
                "Category": "Cad",
                "OperationCostList": [],
            },
            {
                "ID": "l1",
                "Description": "1001880-2 - P1/8-5-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "P1/8-5-A36",
                "ProductID": "pid",
                "OperationCostList": [],
            },
            {
                "ID": "k1",
                "Description": "FILLER - NECK",
                "ProductType": 100,
                "Category": "Cad",
                "OperationCostList": [],
            },
        ]
    }
    verified = {
        "ItemList": [
            {
                **empty["ItemList"][0],
                "Material": "A572",
                "Thickness": 0.25,
                "ThicknessDisp": "0.25 in",
            },
            {
                **empty["ItemList"][1],
                "Machine": "Saw",
                "Length": 12.0,
                "Material": "A36",
            },
            {
                **empty["ItemList"][2],
                "Description": "8166-1 - FILLER NECK",
                "ProductType": 200,
                "Category": "Component",
            },
        ]
    }
    client = MagicMock()
    client.get_json.side_effect = [empty, verified]
    save = MagicMock()
    save.status_code = 200
    save.text = "true"
    client.request.return_value = save
    notes = persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[
            {"part_no": "14500-1", "description": "PEDESTAL TOP PLATE", "qty": 1},
            {"part_no": "1001880-2", "description": "PEDESTAL TUBE 12 LG.", "qty": 1},
            {"part_no": "8166-1", "description": "FILLER NECK", "qty": 1},
        ],
        plate_catalog=[
            {
                "ID": "pl-a572",
                "ProductName": "PL1/4-A572",
                "MaterialGrade": "A572",
                "Thickness": 0.25,
                "Active": True,
                "Thickness_Unit": "inch",
            }
        ],
        linear_catalog=[
            {
                "ID": "pid",
                "ProductName": "P1/8-5-A36",
                "MaterialGrade": "A36",
                "ProductSubType": "pipe",
                "Category": "Pipe",
                "Dim1": 0.125,
                "Dim1_Unit": "inch",
                "WeightLength": 0.14,
                "WeightLength_Unit": "pound/foot",
                "Active": True,
            }
        ],
    )
    paths = [c.args[1] for c in client.request.call_args_list if len(c.args) > 1]
    assert any(p.endswith("addplate") for p in paths), paths
    assert any(p.endswith("addLinear") for p in paths), paths
    assert not any(p.endswith("UpdateItem_Part") for p in paths)
    assert not any(c.args[:2] == ("POST", "v1/quote") for c in client.request.call_args_list)
    blob = " ".join(notes)
    assert "GET-verified" in blob
    assert "addplate" in blob
    plate = next(c for c in client.request.call_args_list if "addplate" in str(c))
    assert plate.kwargs["params"]["material"] == "A572"
    assert float(plate.kwargs["params"]["thickness"]) == 0.25
    lin = next(c for c in client.request.call_args_list if "addLinear" in str(c))
    assert lin.kwargs["params"]["machine"] == "Saw"
    assert float(lin.kwargs["params"]["length"]) == 12.0
    assert lin.kwargs["params"]["ItemID"] == "l1"
    assert "12" in str(lin.kwargs["params"]["name"])
    assert lin.kwargs["params"]["productType"] == "part"


def test_persist_skips_addplate_on_imported_datapart():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    imported = {
        "ItemList": [
            {
                "ID": "c1",
                "Description": '14500-1 - 1/4" A572 Grade 50 PEDESTAL TOP PLATE',
                "ProductType": 100,
                "Category": "Cad",
                "FileID": "file-1",
                "ProductSubType": "prt_dxf",
                "Data": 'DataPart:{"PartName":"14500-1"}',
                "Material": "A572",
                "Thickness": 0.25,
                "UnitCost": 5.96,
                "MaterialCost": 0.41,
                "OperationCostList": [],
            }
        ]
    }
    client = MagicMock()
    client.get_json.return_value = imported
    save = MagicMock()
    save.status_code = 200
    save.text = "true"
    client.request.return_value = save
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "14500-1", "description": "PEDESTAL TOP PLATE", "qty": 1}],
        plate_catalog=[
            {
                "ID": "pl-a572",
                "ProductName": "PL1/4-A572",
                "MaterialGrade": "A572",
                "Thickness": 0.25,
                "Active": True,
                "Thickness_Unit": "inch",
            }
        ],
        persist_linear=False,
    )
    paths = [c.args[1] for c in client.request.call_args_list if len(c.args) > 1]
    assert not any(p.endswith("addplate") for p in paths), paths


def test_parse_cut_length_from_drawing_phrases():
    from secturafab.line_item_ops import parse_cut_length, parse_length_lg

    assert parse_length_lg("PEDESTAL TUBE 18 1/2 LG.") == 18.5
    assert parse_length_lg("X 4 LG") == 4.0
    assert parse_length_lg("LG. 12") == 12.0
    assert parse_cut_length("CUT LENGTH 22.25 IN") == 22.25
    assert parse_cut_length("OAL 36") == 36.0
    assert parse_cut_length("44.375 LONG") == 44.375
    assert parse_cut_length("PEDESTAL TUBE") is None
    assert parse_cut_length("1001880-2 - P1/8-5-A36") is None
    from secturafab.line_item_ops import bom_row_cut_length, largest_drawing_length

    assert largest_drawing_length('1001880-2 PEDESTAL TUBE  36.00"') == 36.0
    assert largest_drawing_length("PEDESTAL TUBE") is None
    from secturafab.line_item_ops import largest_unmarked_length

    assert largest_unmarked_length("1001880-2 PEDESTAL TUBE 16", "1001880-2") == 16.0
    assert bom_row_cut_length({"part_no": "10081-2", "length_in": 22.5}) == 22.5
    assert bom_row_cut_length(
        {"part_no": "33637-1", "description": "1 1/4 RETURN TUBE"}
    ) is None


def test_linear_cut_length_from_component_pdf_not_bom_noun(tmp_path):
    import fitz
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    pdf = tmp_path / "1001880-2.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "1001880-2 PEDESTAL TUBE 18 1/2 LG.")
    doc.save(str(pdf))
    doc.close()
    empty = {
        "ItemList": [
            {
                "ID": "l1",
                "Description": "1001880-2 - P1/8-5-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "P1/8-5-A36",
                "ProductID": "pid",
                "Length": 0,
                "Machine": "",
                "Dim1": 4.0,
                "OperationCostList": [],
            }
        ]
    }
    verified = {
        "ItemList": [
            {
                **empty["ItemList"][0],
                "Machine": "Saw",
                "Length": 18.5,
                "Description": "1001880-2 - P1/8-5-A36 - 18.5",
            }
        ]
    }
    client = MagicMock()
    client.get_json.side_effect = [empty, verified]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    notes = persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "1001880-2", "description": "PEDESTAL TUBE", "qty": 1}],
        plate_catalog=[],
        linear_catalog=[
            {
                "ID": "pid",
                "ProductName": "P1/8-5-A36",
                "MaterialGrade": "A36",
                "ProductSubType": "tube",
                "Active": True,
            }
        ],
        library_folder=tmp_path,
        persist_cad=False,
        persist_linear=True,
    )
    lin = next(c for c in client.request.call_args_list if "addLinear" in str(c))
    assert lin.kwargs["params"]["ItemID"] == "l1"
    assert lin.kwargs["params"]["productID"] == "pid"
    assert lin.kwargs["params"]["machine"] == "Saw"
    assert float(lin.kwargs["params"]["length"]) == 18.5
    assert lin.kwargs["params"]["name"] == "1001880-2 - P1/8-5-A36 - 18.5"
    assert "GET-verified" in " ".join(notes)


def test_linear_length_from_marked_inch_callout_when_no_lg(tmp_path):
    import fitz
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    pdf = tmp_path / "10081-2.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), '10081-2 PEDESTAL HOSE TUBE  27.25"')
    doc.save(str(pdf))
    doc.close()
    empty = {
        "ItemList": [
            {
                "ID": "l1",
                "Description": "10081-2 - P1/8-5-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "P1/8-5-A36",
                "ProductID": "pid",
                "Length": 0,
                "Machine": "",
                "OperationCostList": [],
            }
        ]
    }
    verified = {
        "ItemList": [{**empty["ItemList"][0], "Machine": "Saw", "Length": 27.25}]
    }
    client = MagicMock()
    client.get_json.side_effect = [empty, verified]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "10081-2", "description": "PEDESTAL HOSE TUBE", "qty": 1}],
        plate_catalog=[],
        linear_catalog=[
            {
                "ID": "pid",
                "ProductName": "P1/8-5-A36",
                "MaterialGrade": "A36",
                "ProductSubType": "tube",
                "Active": True,
            }
        ],
        library_folder=tmp_path,
        persist_cad=False,
        persist_linear=True,
    )
    lin = next(c for c in client.request.call_args_list if "addLinear" in str(c))
    assert float(lin.kwargs["params"]["length"]) == 27.25
    assert lin.kwargs["params"]["machine"] == "Saw"


def test_linear_length_from_unmarked_number_on_component_pdf(tmp_path):
    import fitz
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    pdf = tmp_path / "29860-3.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "29860-3 PEDESTAL BRACE ANGLE 9")
    doc.save(str(pdf))
    doc.close()
    empty = {
        "ItemList": [
            {
                "ID": "l1",
                "Description": "29860-3 - L2X1 1/4X1/8-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "L2X1 1/4X1/8-A36",
                "ProductID": "pid",
                "Length": 0,
                "Machine": "",
                "OperationCostList": [],
            }
        ]
    }
    verified = {
        "ItemList": [{**empty["ItemList"][0], "Machine": "Saw", "Length": 9.0}]
    }
    client = MagicMock()
    client.get_json.side_effect = [empty, verified]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "29860-3", "description": "PEDESTAL BRACE ANGLE", "qty": 2}],
        plate_catalog=[],
        linear_catalog=[
            {
                "ID": "pid",
                "ProductName": "L2X1 1/4X1/8-A36",
                "MaterialGrade": "A36",
                "ProductSubType": "structural",
                "Active": True,
            }
        ],
        library_folder=tmp_path,
        persist_cad=False,
        persist_linear=True,
    )
    lin = next(c for c in client.request.call_args_list if "addLinear" in str(c))
    assert float(lin.kwargs["params"]["length"]) == 9.0


def test_linear_length_from_sibling_pdf_in_library_folder(tmp_path):
    import fitz
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    asm = tmp_path / "1001898-1.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "B 1 1001880-2 PEDESTAL TUBE 11 3/8 LG.")
    doc.save(str(asm))
    doc.close()
    empty = {
        "ItemList": [
            {
                "ID": "l1",
                "Description": "1001880-2 - P1/8-5-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "P1/8-5-A36",
                "ProductID": "pid",
                "Length": 0,
                "Machine": "",
                "OperationCostList": [],
            }
        ]
    }
    verified = {
        "ItemList": [{**empty["ItemList"][0], "Machine": "Saw", "Length": 11.375}]
    }
    client = MagicMock()
    client.get_json.side_effect = [empty, verified]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "1001880-2", "description": "PEDESTAL TUBE", "qty": 1}],
        plate_catalog=[],
        linear_catalog=[
            {
                "ID": "pid",
                "ProductName": "P1/8-5-A36",
                "MaterialGrade": "A36",
                "ProductSubType": "tube",
                "Active": True,
            }
        ],
        library_folder=tmp_path,
        persist_cad=False,
        persist_linear=True,
    )
    lin = next(c for c in client.request.call_args_list if "addLinear" in str(c))
    assert float(lin.kwargs["params"]["length"]) == 11.375


def test_stamp_never_posts_grafted_ops():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import stamp_new_line_item_packs

    client = MagicMock()
    notes = stamp_new_line_item_packs(client, "qid")
    assert notes
    assert all("Skipped grafted" in n for n in notes)
    client.get_json.assert_not_called()
    client.request.assert_not_called()


def test_addplate_without_pr_or_primary_costs_fails_live_get():
    payload = gold_1001898_get()
    for it in payload["ItemList"]:
        if it.get("ProductType") in (100, "100"):
            it["OperationCostList"] = []
            it["BadgeString"] = ""
            it["Machine"] = ""
            it["UnitCost"] = 3.12
            it["MaterialCost"] = 0.55
        if it.get("ProductType") in (10, "10"):
            it["OperationCostList"] = []
            it["BadgeString"] = ""
            it["UnitCost"] = 7.63
            it["MaterialCost"] = 0.55
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is False
    blob = " ".join(result.failures)
    assert "PR" in blob or "Primary Costs" in blob
    assert "Saw" in blob or "Primary Costs" in blob


def test_linear_saw_badge_alone_fails_live_get():
    payload = gold_1001898_get()
    for it in payload["ItemList"]:
        if it.get("ProductType") in (10, "10"):
            it["BadgeString"] = "Saw"
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is False
    assert any("Saw" in f and "orange" in f for f in result.failures)


def test_grafted_ops_and_blank_unit_cost_fail_live_get():
    grafted = evaluate_quote_get(
        gold_1001898_get(fail="grafted_ops"),
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert grafted.ok is False
    blob = " ".join(grafted.failures)
    assert "grafted" in blob.lower() or "orange" in blob.lower()
    assert "Saw Setup" in blob
    blank = evaluate_quote_get(
        gold_1001898_get(fail="blank_unit_cost"),
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert blank.ok is False
    assert any("UnitCost" in f for f in blank.failures)


def test_retype_pt10_copies_cad_material_and_linear_length():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import (
        build_cad_new_line_ops,
        retype_linears_to_pt10_keep_persist,
    )

    detail = {
        "ItemList": [
            {
                "ID": "c1",
                "Description": "14500-1 - PEDESTAL TOP PLATE",
                "ProductType": 100,
                "Category": "Cad",
                "Material": "A572",
                "Thickness": 0.25,
                "OperationCostList": build_cad_new_line_ops("c1"),
            },
            {
                "ID": "l1",
                "Description": "1001880-2 - P1/8-5-A36 - 16",
                "ProductType": 20,
                "Category": "Pipe",
                "IsLinear": True,
                "Machine": "Saw",
                "Length": 16.0,
                "ProductID": "pid",
                "SKU": "P1/8-5-A36",
                "OperationCostList": [],
            },
        ]
    }
    client = MagicMock()
    client.get_json.return_value = detail
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    notes = retype_linears_to_pt10_keep_persist(client, "qid")
    assert any("PT 10" in n for n in notes)
    assert not any(c.args[:2] == ("POST", "v1/quote") for c in client.request.call_args_list)
    upd = next(c for c in client.request.call_args_list if "quoteOnline/update" in str(c))
    body = upd.kwargs.get("json") or []
    assert any(row.get("ParamName") == "ProductType" and row.get("Value") == "10" for row in body)
    assert any(row.get("ID") == "l1" for row in body)


def test_linear_product_type_20_fails_live_get():
    payload = gold_1001898_get()
    for it in payload["ItemList"]:
        if it.get("ProductType") == 10 and "1001880" in str(it.get("Description")):
            it["ProductType"] = 20
            it["Category"] = "Pipe"
            break
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is False
    assert any("ProductType" in f and "20" in f for f in result.failures)


def test_addlinear_fetches_product_by_id_when_catalog_misses():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    empty = {
        "ItemList": [
            {
                "ID": "l1",
                "Description": "29860-3 - L2X1 1/4X1/8-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "L2X1 1/4X1/8-A36",
                "ProductID": "bound-pid",
                "Length": 0,
                "Machine": "",
                "OperationCostList": [],
            }
        ]
    }
    product = {
        "ID": "bound-pid",
        "ProductName": "L2X1 1/4X1/8-A36",
        "MaterialGrade": "A36",
        "ProductSubType": "structural",
        "Active": True,
    }
    verified = {
        "ItemList": [
            {**empty["ItemList"][0], "Machine": "Saw", "Length": 14.0}
        ]
    }
    client = MagicMock()
    client.get_json.side_effect = [empty, product, verified]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[
            {"part_no": "29860-3", "description": "PEDESTAL BRACE ANGLE 14 LG.", "qty": 2}
        ],
        plate_catalog=[],
        linear_catalog=[],
        persist_cad=False,
        persist_linear=True,
    )
    product_gets = [
        c.args[0] for c in client.get_json.call_args_list if c.args
    ]
    assert any(str(u).endswith("v1/product/linear/bound-pid") for u in product_gets)
    lin = next(c for c in client.request.call_args_list if "addLinear" in str(c))
    assert lin.kwargs["params"]["ItemID"] == "l1"
    assert lin.kwargs["params"]["productID"] == "bound-pid"
    assert float(lin.kwargs["params"]["length"]) == 14.0


def test_addlinear_retries_when_first_get_still_empty():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    empty = {
        "ItemList": [
            {
                "ID": "l1",
                "Description": "33637-1 - P1/4-5-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "P1/4-5-A36",
                "ProductID": "pid",
                "Length": 0,
                "Machine": "",
                "OperationCostList": [],
            }
        ]
    }
    still_empty = {"ItemList": [dict(empty["ItemList"][0])]}
    verified = {
        "ItemList": [
            {**empty["ItemList"][0], "Machine": "Saw", "Length": 9.0}
        ]
    }
    client = MagicMock()
    client.get_json.side_effect = [empty, still_empty, verified]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    notes = persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "33637-1", "description": "1 1/4 RETURN TUBE 9 LG.", "qty": 1}],
        plate_catalog=[],
        linear_catalog=[
            {
                "ID": "pid",
                "ProductName": "P1/4-5-A36",
                "MaterialGrade": "A36",
                "ProductSubType": "tube",
                "Active": True,
            }
        ],
        persist_cad=False,
        persist_linear=True,
        retry_linear=True,
    )
    adds = [c for c in client.request.call_args_list if "addLinear" in str(c)]
    assert len(adds) == 2
    assert float(adds[0].kwargs["params"]["length"]) == 9.0
    assert float(adds[1].kwargs["params"]["length"]) == 9.0
    assert "GET-verified" in " ".join(notes)
    assert not any(n.startswith("WARNING:") for n in notes)


def test_dim1_is_not_used_as_cut_length():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    empty = {
        "ItemList": [
            {
                "ID": "l1",
                "Description": "1001880-2 - P1/8-5-A36",
                "ProductType": 10,
                "Category": "Linear",
                "SKU": "P1/8-5-A36",
                "ProductID": "pid",
                "Length": 0,
                "Machine": "",
                "Dim1": 4.0,
                "OperationCostList": [],
            }
        ]
    }
    verified = {"ItemList": [dict(empty["ItemList"][0])]}
    client = MagicMock()
    client.get_json.side_effect = [empty, verified]
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    notes = persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "1001880-2", "description": "PEDESTAL TUBE", "qty": 1}],
        plate_catalog=[],
        linear_catalog=[{"ID": "pid", "ProductName": "P1/8-5-A36", "Active": True}],
        persist_cad=False,
        persist_linear=True,
    )
    assert not any("addLinear" in str(c) for c in client.request.call_args_list)
    assert any("WARNING:" in n and "Linear" in n for n in notes)


def test_bom_family_title_is_pedestal_weldment_not_child_noun():
    assert title_from_bom_family(_bom_rows()) == "PEDESTAL WELDMENT"
    assert title_from_bom_family(
        [{"part_no": "1", "description": "PLATE"}, {"part_no": "2", "description": "TUBE"}]
    ) is None
