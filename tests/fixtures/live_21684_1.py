"""Leftover 21684-1 / 6d4373bc — Long/Saw PASS, org GUID empty.

Minted 6d4373bc Time Waco on PR 18 3bacf2a. Long/Saw pack PASSed
(RTD4X0.375-A513 UC 9.52). Org bind + POST 201 left
PrimaryOrganizationID empty GUID after mint stamped Time Waco.

Do not remint/PATCH 6d4373bc. Do not PATCH live golds
1001898-1 / 21678-1. Cad 3ac04f8a is a separate PASS.
"""

from __future__ import annotations

from typing import Any

from secturafab.org_ops import TIME_WACO_ORG_ID
from secturafab.website import EMPTY_GUID

SPENT_QUOTE_ID_PREFIX = "6d4373bc"
SPENT_QUOTE_NUMBER = "21684-1"
HEADER_TITLE = "TUBE, CYLINDER ANCHOR"
ORG = "Time Waco"
SKU = "RTD4X0.375-A513"
UNIT_COST = 9.52
MACHINE = "Saw"
PRODUCT_TYPE = 30
POST_STATUS = 201

LEFTOVER_LIVE_6D4373BC: dict[str, Any] = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "linear_dod_pass": True,
    "post_status": POST_STATUS,
    "primary_organization_id": EMPTY_GUID,
    "want_org_id": TIME_WACO_ORG_ID,
    "machine": MACHINE,
    "product_type": PRODUCT_TYPE,
    "sku": SKU,
    "unit_cost": UNIT_COST,
    "mint_stamped_time_waco": True,
    "quotes_ui_bind": True,
    "autocomplete_search": False,
}


def leftover_org_empty_guid_dump() -> dict[str, Any]:
    """Leftover: Long/Saw PASS; GET PrimaryOrganizationID empty GUID."""
    return {
        "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "finish_posted": True,
        "invent_internal": False,
        "autocomplete_search": False,
        "linear_dod_pass": True,
        "post_status": POST_STATUS,
        "primary_organization_id": EMPTY_GUID,
        "want_org_id": TIME_WACO_ORG_ID,
        "machine": MACHINE,
        "product_type": PRODUCT_TYPE,
        "sku": SKU,
        "unit_cost": UNIT_COST,
        "live_6d4373bc": dict(LEFTOVER_LIVE_6D4373BC),
    }


def leftover_org_empty_guid_get() -> dict[str, Any]:
    """GET after mint/org stamp/POST 201 — packs landed, org GUID empty."""
    return {
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "QuoteAndRevNumber": SPENT_QUOTE_NUMBER,
        "Description": HEADER_TITLE,
        "PrimaryOrganizationID": EMPTY_GUID,
        "OrganizationID": EMPTY_GUID,
        "OrganizationName": "",
        "Organization": None,
        "ItemCount": 1,
        "ItemList": [
            {
                "Description": HEADER_TITLE,
                "ProductType": PRODUCT_TYPE,
                "IsLinear": True,
                "Machine": MACHINE,
                "SKU": SKU,
                "UnitCost": UNIT_COST,
            }
        ],
    }
