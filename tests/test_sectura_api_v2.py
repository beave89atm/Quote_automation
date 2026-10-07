"""Offline contract for the 2026-10-07 SecturaFAB v2 spec.

No live HTTP. Lookup, create, add-linear, add-plate, and manual component
bodies are checked against mocked client calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from secturafab.api_v2 import (
    OrganizationLookupError,
    add_linear_item,
    add_manual_component_item,
    add_plate_item,
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
        {"Data": {"OrganizationId": _OTHER, "Name": "Time Manufacturing Waco"}}
    )
    with pytest.raises(OrganizationLookupError, match="does not match known"):
        resolve_organization_id(client, name="Time Manufacturing Waco", known_id=_ORG)
    client.post_json.assert_not_called()


def test_refuse_create_organization_does_not_post():
    with pytest.raises(OrganizationLookupError, match="human decision"):
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
