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


@pytest.mark.parametrize("fail", ["org", "bare_pn", "no_ops"])
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


def test_new_line_item_pack_is_not_profile_datapart():
    assert cad_new_line_calculators() == [
        "Laser",
        "Drafting",
        "Laser-Setup",
        "Sheet Loading",
        "Deburr",
    ]
    assert linear_new_line_calculators() == ["Saw", "Saw Setup"]
    from secturafab.line_item_ops import build_cad_new_line_ops

    for op in build_cad_new_line_ops("x"):
        assert op.get("OperationName") != "Profile"
        assert 0 < float(op.get("UnitTime") or 0) < 3.0


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
    ), patch(
        "secturafab.push.stamp_new_line_item_packs", return_value=[]
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
    ), patch(
        "secturafab.push.stamp_new_line_item_packs", return_value=[]
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


def test_persist_copies_cad_desc_fields_and_stamps_packs():
    from unittest.mock import MagicMock

    from secturafab.line_item_ops import persist_classified_item_fields

    client = MagicMock()
    client.get_json.return_value = {
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
        ]
    }
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[
            {"part_no": "14500-1", "description": "PEDESTAL TOP PLATE", "qty": 1},
            {"part_no": "1001880-2", "description": "PEDESTAL TUBE 12 LG.", "qty": 1},
        ],
    )
    saved = client.request.call_args.kwargs["json"]["ItemList"]
    cad = saved[0]
    lin = saved[1]
    assert cad["Thickness"] == "1/4"
    assert "A572" in str(cad["Material"])
    assert cad["Machine"] == "Laser"
    assert cad["OperationCostList"]
    assert lin["Machine"] == "Saw"
    assert float(lin["Length"]) == 12.0
    assert "12" in lin["Description"]
    assert lin["OperationCostList"]


def test_bom_family_title_is_pedestal_weldment_not_child_noun():
    assert title_from_bom_family(_bom_rows()) == "PEDESTAL WELDMENT"
    assert title_from_bom_family(
        [{"part_no": "1", "description": "PLATE"}, {"part_no": "2", "description": "TUBE"}]
    ) is None
