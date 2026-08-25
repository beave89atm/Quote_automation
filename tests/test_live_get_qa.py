"""GET-shaped QA harness — fails the build on Kyle's live 1001898-1 misses."""

from __future__ import annotations

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


def test_bom_family_title_is_pedestal_weldment_not_child_noun():
    assert title_from_bom_family(_bom_rows()) == "PEDESTAL WELDMENT"
    assert title_from_bom_family(
        [{"part_no": "1", "description": "PLATE"}, {"part_no": "2", "description": "TUBE"}]
    ) is None
