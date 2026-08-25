"""Recorded/mocked live-GET shape for a NEW 1001898-1 quote (not quote 06cb2ae0)."""

from __future__ import annotations

from typing import Any

from secturafab.item_desc import (
    format_assembly_description,
    format_cad_description,
    format_component_line,
    format_linear_description,
    format_quote_header_description,
)
from secturafab.line_item_ops import build_cad_new_line_ops, build_linear_new_line_ops
from secturafab.push import classify_sectura_item
from tests.fixtures.time_gold import DASH_1001898

TIME_ORG = "Time Manufacturing Waco"
TIME_ORG_ID = "11111111-2222-3333-4444-555555555555"
ASSEMBLY_DESC = format_assembly_description("1001898-1", "PEDESTAL WELDMENT")
HEADER_DESC = format_quote_header_description("PEDESTAL WELDMENT", part_key="1001898-1")

# Catalog SKUs the Long path would bind (shape only — not live ProductIDs).
_LINEAR_SKU = {
    "1001880-2": "HSS 4X4X.188-A500",
    "29860-3": "L3X3X1/4-A36",
    "29860-4": "L3X3X1/4-A36",
    "10081-2": "HSS 2X2X.125-A500",
    "33637-1": "DOM 1.25X.120-A513",
}


def gold_1001898_get(*, fail: str | None = None) -> dict[str, Any]:
    """
    ItemList shaped like a passing live GET of a new 1001898-1 quote.

    ``fail`` overlays one of Kyle's already-seen misses: ``org``, ``bare_pn``,
    ``no_ops``.
    """
    items: list[dict[str, Any]] = [
        {
            "ID": "asm-1001898",
            "Description": ASSEMBLY_DESC,
            "ProductType": 300,
            "IsAssembly": True,
            "Quantity": 1,
            "OperationCostList": [],
        }
    ]
    for _item, qty, pn, noun in DASH_1001898:
        cat = classify_sectura_item(f"{pn} {noun}")
        if cat == "Linear":
            sku = _LINEAR_SKU[pn]
            items.append(
                {
                    "ID": f"lin-{pn}",
                    "Description": format_linear_description(
                        pn, sku=sku, length_in=12.0, noun=noun
                    ),
                    "ProductType": 10,
                    "Category": "Linear",
                    "ItemType": "Linear",
                    "IsLinear": True,
                    "IsPlate": False,
                    "Machine": "Saw",
                    "ProductID": f"pid-{pn}",
                    "SKU": sku,
                    "Quantity": qty,
                    "Length": 12.0,
                    "OperationCostList": build_linear_new_line_ops(f"lin-{pn}"),
                    "PrimaryTime": 3.0 / 60.0,
                }
            )
        elif cat == "Component":
            items.append(
                {
                    "ID": f"cmp-{pn}",
                    "Description": format_component_line(pn, noun) or noun,
                    "ProductType": 200,
                    "Category": "Component",
                    "ItemType": "Component",
                    "IsLinear": False,
                    "IsPlate": False,
                    "Machine": None,
                    "Quantity": qty,
                    "OperationCostList": [],
                }
            )
        else:
            items.append(
                {
                    "ID": f"cad-{pn}",
                    "Description": format_cad_description(
                        pn,
                        thickness=0.25,
                        grade="A36",
                        width_in=8.0,
                        length_in=10.0,
                        noun=noun,
                    ),
                    "ProductType": 100,
                    "Category": "Cad",
                    "ItemType": "Cad",
                    "IsLinear": False,
                    "IsPlate": True,
                    "Machine": "Laser",
                    "Material": "A36",
                    "Thickness": "0.25",
                    "Width": 8.0,
                    "Length": 10.0,
                    "Quantity": qty,
                    "OperationCostList": build_cad_new_line_ops(f"cad-{pn}"),
                    "PrimaryTime": 1.97 / 60.0,
                }
            )

    payload: dict[str, Any] = {
        "ID": "new-quote-not-06cb2ae0",
        "QuoteNumber": "1001898-1",
        "Description": HEADER_DESC,
        "OrganizationName": TIME_ORG,
        "PrimaryOrganizationID": TIME_ORG_ID,
        "OrganizationList": [
            {
                "ID": TIME_ORG_ID,
                "OrganizationName": TIME_ORG,
                "DisplayName": TIME_ORG,
            }
        ],
        "ItemCount": len(items),
        "ItemList": items,
    }
    if fail == "org":
        payload["OrganizationName"] = None
        payload["PrimaryOrganizationID"] = "00000000-0000-0000-0000-000000000000"
        payload["OrganizationList"] = []
    elif fail == "bare_pn":
        payload["Description"] = "1001898-1"
        payload["ItemList"][0]["Description"] = "1001898-1"
    elif fail == "no_ops":
        for it in payload["ItemList"]:
            it["OperationCostList"] = []
            it["PrimaryTime"] = 0
    return payload
