"""Offline contract for the 2026-10-07 SecturaFAB v2 spec.

No live HTTP. Lookup, create, add-linear, add-plate, and manual component
bodies are checked against mocked client calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from secturafab.api_v2 import (
    OrganizationLookupError,
    add_linear_item,
    add_manual_component_item,
    add_plate_item,
    discard_quote_created_this_run,
    build_add_cad_form,
    build_add_linear_item_body,
    build_add_plate_item_body,
    build_create_quote_body,
    build_manual_component_body,
    create_quote_from_payload,
    customer_name_from_quote_response,
    organization_matches,
    primary_organization_id_from_quote_response,
    refuse_create_organization,
    resolve_organization_id,
)
from secturafab.client import SecturaFabApiError
from secturafab.pdf_assembly_ops import _add_component_items
from secturafab.qa_harness import _org_name
from secturafab.quotes import QuoteService

_ORG = "b7dbc294-3fd2-43aa-99be-268a6c4fce14"
_OTHER = "11111111-1111-4111-8111-111111111111"


def _client_with_lookup(payload):
    client = MagicMock()
    client.get_json.return_value = payload
    client.post_json.return_value = {"Data": {"QuoteId": "new-qid"}}
    return client


def test_create_body_sends_organization_id_only():
    body = build_create_quote_body(
        organization_id=_ORG,
        description="SAFE CAVE",
        external_reference="ZZ-ORG",
    )
    assert body == {
        "OrganizationId": _ORG,
        "Description": "SAFE CAVE",
        "ExternalReference": "ZZ-ORG",
    }
    assert "OrganizationName" not in body
    assert "LocationName" not in body


def test_lookup_one_match_is_the_id_used_on_post():
    client = _client_with_lookup(
        {"Data": {"OrganizationId": _ORG, "Name": "Propell"}, "Paging": {"Total": 1}}
    )
    created = create_quote_from_payload(
        client,
        {
            "OrganizationName": "Propell",
            "LocationName": "Waco",
            "Description": "BRACKET",
            "ExternalReference": "1001",
        },
    )
    assert created["Data"]["QuoteId"] == "new-qid"
    assert client.get_json.call_args.args[0] == "v2/organization/lookup"
    assert client.get_json.call_args.kwargs["params"] == {"name": "Propell"}
    body = client.post_json.call_args.args[1]
    assert client.post_json.call_args.args[0] == "v2/quote"
    assert body["OrganizationId"] == _ORG
    assert "OrganizationName" not in body
    assert "LocationName" not in body
    assert "v2/organization" not in [
        call.args[0] for call in client.post_json.call_args_list
    ]


def test_lookup_none_and_many_fail_closed_without_creating_an_org():
    missing = _client_with_lookup({"Data": None, "Paging": {"Total": 0}})
    with pytest.raises(OrganizationLookupError, match="matched no organization"):
        resolve_organization_id(missing, name="Propell")
    missing.post_json.assert_not_called()

    many = _client_with_lookup(
        {
            "Data": [
                {"OrganizationId": _ORG, "Name": "Propell"},
                {"OrganizationId": _OTHER, "Name": "Propell West"},
            ]
        }
    )
    with pytest.raises(OrganizationLookupError, match="more than one|matched 2"):
        resolve_organization_id(many, name="Propell")
    many.post_json.assert_not_called()

    declared = _client_with_lookup(
        {
            "Data": {"OrganizationId": _ORG, "Name": "Propell"},
            "Paging": {"Total": 3},
        }
    )
    with pytest.raises(OrganizationLookupError, match="matched 3"):
        resolve_organization_id(declared, name="Propell")
    declared.post_json.assert_not_called()

    hidden = _client_with_lookup({"Data": None, "Paging": {"Total": 2}})
    with pytest.raises(OrganizationLookupError, match="matched 2"):
        resolve_organization_id(hidden, name="Propell")
    hidden.post_json.assert_not_called()


def test_lookup_404_is_no_match():
    client = MagicMock()
    client.get_json.side_effect = SecturaFabApiError("missing", status_code=404)
    with pytest.raises(OrganizationLookupError, match="matched no organization"):
        resolve_organization_id(client, name="Nobody")
    client.post_json.assert_not_called()


def test_known_id_mismatch_fails_closed():
    client = _client_with_lookup(
        {"Data": {"OrganizationId": _OTHER, "Name": "Other Shop"}}
    )
    with pytest.raises(OrganizationLookupError, match="does not match known"):
        resolve_organization_id(client, name="Other Shop", known_id=_ORG)
    client.post_json.assert_not_called()


def test_lookup_sends_exactly_one_parameter():
    client = _client_with_lookup(
        {"Data": {"OrganizationId": _ORG, "Name": "Propell"}}
    )
    assert resolve_organization_id(client, name="Propell") == _ORG
    assert client.get_json.call_args.kwargs["params"] == {"name": "Propell"}
    assert resolve_organization_id(client, external_reference="EXT-1") == _ORG
    assert client.get_json.call_args.kwargs["params"] == {"externalReference": "EXT-1"}
    client.get_json.reset_mock()
    with pytest.raises(OrganizationLookupError, match="exactly one"):
        resolve_organization_id(client, name="Propell", external_reference="EXT-1")
    with pytest.raises(OrganizationLookupError, match="exactly one"):
        resolve_organization_id(client)
    client.get_json.assert_not_called()
    client.post_json.assert_not_called()


def test_lookup_error_body_is_named_in_the_flag():
    client = MagicMock()
    client.get_json.side_effect = SecturaFabApiError(
        "API request failed (400)",
        status_code=400,
        body={
            "Error": {
                "Name": "BadRequest",
                "Description": "Provide exactly one of name or externalReference.",
            }
        },
    )
    with pytest.raises(OrganizationLookupError, match="Error.Name=BadRequest") as raised:
        resolve_organization_id(client, name="Propell")
    text = str(raised.value)
    assert "Error.Description=Provide exactly one of name or externalReference." in text
    assert "failed (400)" in text
    client.post_json.assert_not_called()


def test_lookup_miss_names_the_exact_organization_and_makes_no_write():
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    client.get_json.side_effect = SecturaFabApiError(
        "missing",
        status_code=404,
        body={"Error": {"Name": "NotFound", "Description": "No match"}},
    )
    with pytest.raises(OrganizationLookupError, match="exact Sectura organization name") as raised:
        SecturaFabPushService(client=client).create_quote(
            quote_number="ZZ-MISS",
            organization_name="No Such Shop",
        )
    text = str(raised.value)
    assert "FLAG:" in text
    assert "Error.Name=NotFound" in text
    assert "Error.Description=No match" in text
    assert "not creating" in text.lower() or "Not creating" in text
    client.post_json.assert_not_called()
    client.put_json.assert_not_called()
    client.delete_json.assert_not_called()
    client.request.assert_not_called()
    client.get_json.assert_called_once()
    assert client.get_json.call_args.args[0] == "v2/organization/lookup"
    assert client.get_json.call_args.kwargs["params"] == {"name": "No Such Shop"}


def test_time_waco_resolves_by_id_and_refuses_the_duplicate_name():
    from secturafab.push import SecturaFabPushService

    client = MagicMock()

    def _get(path, **_kwargs):
        if f"v2/organization/{_ORG}" in str(path):
            return {
                "Data": {
                    "OrganizationId": _ORG,
                    "Name": "Time Manufacturing",
                    "ExternalReference": None,
                }
            }
        return {"ProfitModel": 1, "QuoteStatus": "OPEN-NEW", "PrimaryOrganizationID": _ORG}

    client.get_json.side_effect = _get
    client.post_json.return_value = {"Data": {"QuoteId": "time-qid"}}
    with patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={"ok": True, "tab": {}},
    ), patch(
        "secturafab.page_weld.set_page_quote_number",
        return_value=["QuoteNumber set via UpdatePropertyValue"],
    ), patch(
        "secturafab.page_weld.set_page_quote_description",
        return_value=["Description set"],
    ), patch(
        "secturafab.chrome_cdp.bind_quote_organization_detail",
        return_value={
            "ok": True,
            "via": "OrganizationDetail",
            "search": False,
            "org_id": _ORG,
        },
    ):
        quote_id = SecturaFabPushService(client=client).create_quote(
            quote_number="ZZ-TIME",
            description="BRACKET",
            organization_name="Time Manufacturing",
        )
    assert quote_id == "time-qid"
    assert client.get_json.call_args_list[0].args[0] == f"v2/organization/{_ORG}"
    assert all("lookup" not in str(call.args[0]) for call in client.get_json.call_args_list)
    assert client.post_json.call_args.args[1]["OrganizationId"] == _ORG

    client.get_json.reset_mock()
    client.post_json.reset_mock()
    with pytest.raises(OrganizationLookupError, match="Time Manufacturing Waco"):
        SecturaFabPushService(client=client).create_quote(
            quote_number="ZZ-TIME",
            organization_name="Time Manufacturing Waco",
        )
    client.get_json.assert_not_called()
    client.post_json.assert_not_called()
    client.request.assert_not_called()


def test_parse_or_raise_surfaces_v2_error_name_and_description():
    class _Response:
        status_code = 400
        url = "https://example.invalid/api/v2/organization/not-a-guid"
        content = b"{}"

        def json(self):
            return {
                "Error": {
                    "Name": "BadRequest",
                    "Description": "The organizationId must be a valid Guid.",
                }
            }

    with pytest.raises(SecturaFabApiError, match="Error.Name=BadRequest") as raised:
        from secturafab.client import SecturaFabClient

        SecturaFabClient._parse_or_raise(_Response())
    assert "Error.Description=The organizationId must be a valid Guid." in str(raised.value)


def test_no_organization_or_customer_create_call_in_client_or_push():
    import ast
    from pathlib import Path

    from secturafab.client import is_organization_or_customer_create

    roots = [
        Path("secturafab/client.py"),
        Path("secturafab/push.py"),
        Path("secturafab/api_v2.py"),
        Path("secturafab/org_ops.py"),
        Path("secturafab/quotes.py"),
        Path("secturafab/chrome_cdp.py"),
    ]
    write_names = {"post_json", "put_json", "post_multipart", "delete_json"}
    hits: list[str] = []
    for path in roots:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            method = ""
            raw_path = None
            if name in {"request", "website_request"} and node.args:
                if isinstance(node.args[0], ast.Constant):
                    method = str(node.args[0].value)
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    raw_path = str(node.args[1].value)
            elif name in write_names and node.args and isinstance(node.args[0], ast.Constant):
                method = {"put_json": "PUT", "delete_json": "DELETE"}.get(name, "POST")
                raw_path = str(node.args[0].value)
            if raw_path and is_organization_or_customer_create(method, raw_path):
                hits.append(f"{path}:{node.lineno} {method} {raw_path}")
    assert hits == []


def test_client_refuses_organization_create_before_http():
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient(
        config=SecturaFabConfig(
            base_url="https://example.invalid",
            token_url_override="https://example.invalid/token",
        )
    )
    client.session = MagicMock()
    client.authenticate = MagicMock(side_effect=AssertionError("auth"))
    with pytest.raises(SecturaFabApiError, match="Not creating an organization"):
        client.request("POST", "v2/organization", json={"Name": "Nope"})
    with pytest.raises(SecturaFabApiError, match="Not creating an organization"):
        client.website_request("POST", "Organization/Create")
    client.session.request.assert_not_called()
    client.authenticate.assert_not_called()


def test_refuse_create_organization_does_not_post():
    with pytest.raises(OrganizationLookupError, match="Not creating an organization"):
        refuse_create_organization()


def test_quote_service_create_uses_lookup_then_v2_post():
    client = _client_with_lookup(
        {"Data": {"OrganizationId": _ORG, "Name": "Safe Cave"}}
    )
    QuoteService(client).create_quote(
        {"OrganizationName": "Safe Cave", "LocationName": "Shop", "Description": "PLATE"}
    )
    body = client.post_json.call_args.args[1]
    assert body == {"OrganizationId": _ORG, "Description": "PLATE"}


def test_add_linear_and_plate_drop_quote_item_id():
    linear = build_add_linear_item_body(
        {
            "QuoteItemId": "gone",
            "Quantity": 2,
            "ProductSubType": "tube",
            "Length": 48,
            "LengthUnit": "inch",
        }
    )
    plate = build_add_plate_item_body(
        {
            "QuoteItemId": "gone",
            "Quantity": 1,
            "Width": 2.5,
            "WidthUnit": "inch",
            "Length": 4,
            "LengthUnit": "inch",
        }
    )
    cad = build_add_cad_form(
        {"QuoteItemId": "gone", "files": "drawing.pdf", "FixedPrice": None, "Quantity": 1}
    )
    assert "QuoteItemId" not in linear
    assert "QuoteItemId" not in plate
    assert "QuoteItemId" not in cad
    assert "FixedPrice" not in cad
    client = MagicMock()
    add_linear_item(client, "qid", {"QuoteItemId": "gone", "Quantity": 1})
    add_plate_item(client, "qid", {"QuoteItemId": "gone", "Quantity": 1})
    assert client.post_json.call_args_list[0].args[0] == "v2/quote/qid/add-linear-item"
    assert client.post_json.call_args_list[1].args[0] == "v2/quote/qid/add-plate-item"
    assert all("QuoteItemId" not in call.args[1] for call in client.post_json.call_args_list)


def test_quote_response_ignores_location_name():
    payload = {
        "OrganizationName": "Propell",
        "LocationName": "should-not-be-read",
        "PrimaryOrganizationId": _ORG,
    }
    assert customer_name_from_quote_response(payload) == "Propell"
    assert primary_organization_id_from_quote_response(payload) == _ORG
    assert _org_name({"LocationName": "Waco"}) == ""
    assert organization_matches({"LocationName": "Waco"}) == ([], 0)


def test_manual_component_body_omits_invented_cost():
    body = build_manual_component_body(
        quantity=2,
        description="KING PIN",
        part_name="50029-7",
    )
    assert body == {"Quantity": 2, "Description": "KING PIN", "PartName": "50029-7"}
    for key in ("UnitCost", "UnitPrice", "UnitWeight", "HasFixedPrice", "MarginMarkup"):
        assert key not in body


def test_component_kids_post_manual_endpoint_not_full_quote():
    client = MagicMock()
    client.post_json.return_value = {"Data": {"QuoteItemId": "item-1"}}
    notes = _add_component_items(
        client,
        "qid",
        [{"part_no": "50029-7", "description": "KING PIN", "qty": 2}],
    )
    assert client.request.call_count == 0
    assert client.get_json.call_count == 0
    assert client.post_json.call_args.args[0] == "v2/quote/qid/add-manual-component-item"
    body = client.post_json.call_args.args[1]
    assert body["Quantity"] == 2
    assert body["PartName"] == "50029-7"
    assert "KING PIN" in body["Description"]
    assert "UnitCost" not in body
    assert "UnitPrice" not in body
    assert "UnitWeight" not in body
    assert any("add-manual-component-item" in note for note in notes)
    with pytest.raises(SecturaFabApiError, match="Quantity"):
        add_manual_component_item(client, "qid", {"Description": "no qty"})


def _status_fields(client: MagicMock) -> list[dict]:
    found = []
    for call in client.post_json.call_args_list + client.put_json.call_args_list:
        body = call.args[1] if len(call.args) > 1 else {}
        if isinstance(body, dict):
            found.append(body)
        elif isinstance(body, list):
            found.extend(row for row in body if isinstance(row, dict))
    return found


def test_create_quote_discards_only_the_quote_this_post_created():
    """Post-create failures delete that id. A miss before POST does not."""
    from secturafab.forbidden_quotes import LVTONG_CUSTOMER_QUOTE_ID, ForbiddenQuoteError
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    client.post_json.return_value = {"Data": {"QuoteId": "mint-1"}}
    with patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={"ok": False, "reason": "edit_tab_missing"},
    ), pytest.raises(SecturaFabApiError, match="ORPHAN quote mint-1"):
        SecturaFabPushService(client=client).create_quote(quote_number="ZZ-MINT")
    client.delete_json.assert_called_once_with("v2/quote/mint-1")

    client = MagicMock()
    with patch(
        "secturafab.push.organization_id_for_new_quote",
        side_effect=OrganizationLookupError("FLAG: no organization match"),
    ), pytest.raises(OrganizationLookupError, match="no organization"):
        SecturaFabPushService(client=client).create_quote(
            quote_number="ZZ-MINT",
            organization_name="Nope",
        )
    client.post_json.assert_not_called()
    client.delete_json.assert_not_called()

    client = MagicMock()
    client.post_json.return_value = {"Data": {"QuoteId": LVTONG_CUSTOMER_QUOTE_ID}}
    with pytest.raises(ForbiddenQuoteError, match="forbidden"):
        SecturaFabPushService(client=client).create_quote(quote_number="ZZ-MINT")
    client.delete_json.assert_not_called()

    client = MagicMock()
    client.post_json.return_value = {"Data": {"QuoteId": "kept-1"}}
    client.get_json.return_value = {"ProfitModel": 1, "QuoteStatus": "OPEN-NEW"}
    with patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={"ok": True, "tab": {}},
    ), patch(
        "secturafab.page_weld.set_page_quote_number",
        return_value=["QuoteNumber set via UpdatePropertyValue"],
    ):
        assert (
            SecturaFabPushService(client=client).create_quote(quote_number="ZZ-MINT")
            == "kept-1"
        )
    client.delete_json.assert_not_called()


def test_create_quote_delete_failure_still_names_the_orphan():
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    client.post_json.return_value = {"Data": {"QuoteId": "mint-2"}}
    client.delete_json.side_effect = SecturaFabApiError("delete down")
    with patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={"ok": False, "reason": "edit_tab_missing"},
    ), pytest.raises(SecturaFabApiError, match="ORPHAN quote mint-2") as raised:
        SecturaFabPushService(client=client).create_quote(quote_number="ZZ-MINT")
    assert "delete down" in str(raised.value)
    assert "mint-2" in str(raised.value)
    client.delete_json.assert_called_once_with("v2/quote/mint-2")


def test_rest_mint_header_is_flagged_without_a_status_write():
    """v2 create cannot set ProfitModel or QuoteStatus. Do not invent a setter."""
    from secturafab.org_ops import rest_mint_header_flag
    from secturafab.push import SecturaFabPushService

    assert rest_mint_header_flag(
        {"ProfitModel": 1, "QuoteStatus": "OPEN-NEW"}
    ) is None
    draft = rest_mint_header_flag({"ProfitModel": 0, "QuoteStatus": "OPEN-DRAFT"})
    assert draft is not None
    assert "ProfitModel 0" in draft
    assert "OPEN-DRAFT" in draft
    assert "No supported call" in draft
    assert "QuoteStatus" in draft
    assert "has no OPEN-NEW" not in draft
    entered = rest_mint_header_flag({"ProfitModel": "Margin", "Status": "Entered"})
    assert entered is not None
    assert "Margin" in entered
    assert "Entered" in entered

    client = MagicMock()
    client.post_json.return_value = {"Data": {"QuoteId": "draft-1"}}
    client.get_json.return_value = {"ProfitModel": 0, "QuoteStatus": "OPEN-DRAFT"}
    with patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={"ok": True, "tab": {}},
    ), patch(
        "secturafab.page_weld.set_page_quote_number",
        return_value=["QuoteNumber set via UpdatePropertyValue"],
    ), pytest.raises(SecturaFabApiError, match="FLAG:") as raised:
        SecturaFabPushService(client=client).create_quote(quote_number="ZZ-MINT")
    message = str(raised.value)
    assert "ORPHAN quote draft-1" in message
    assert "OPEN-DRAFT" in message
    assert "No supported call" in message
    client.delete_json.assert_called_once_with("v2/quote/draft-1")
    client.put_json.assert_not_called()
    for body in _status_fields(client):
        assert "QuoteStatus" not in body
        assert "ProfitModel" not in body
        assert "Status" not in body
        assert body.get("ParamName") not in {"QuoteStatus", "ProfitModel", "Status"}


def test_discard_refuses_a_forbidden_or_empty_id():
    from secturafab.forbidden_quotes import LVTONG_CUSTOMER_QUOTE_ID

    client = MagicMock()
    assert "nothing discarded" in discard_quote_created_this_run(client, "")
    note = discard_quote_created_this_run(client, LVTONG_CUSTOMER_QUOTE_ID)
    assert "refusing" in note
    assert LVTONG_CUSTOMER_QUOTE_ID in note
    client.delete_json.assert_not_called()
