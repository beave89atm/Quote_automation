"""Spent 1001898-5 GET shape — reconstructed Image Files FileList miss.

Minted 491f6387 on the 1001898-1 PDF-only path. GET item_count 8:
3 Cad (unitcost filled, OperationCostList [], no PR) + 2 Linear saw PASS
+ 2 Comp + 1 Assembly. Linear saw PASS does not make DoD PASS.

Leave 491f6387. Do not PATCH. Do not remint. No STEP.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "491f6387-520f-4eee-aab3-6d20585ee740"
SPENT_QUOTE_NUMBER = "1001898-5"
HEADER_TITLE_CANONICAL = "WELDMENT, PEDESTAL"
HEADER_TITLE_ALT = "PEDESTAL WELDMENT"


def _cad(desc: str, unit_cost: float) -> dict[str, Any]:
    return {
        "ID": f"cad-{desc.split()[0]}",
        "Description": desc,
        "ProductType": 100,
        "Category": "Cad",
        "BadgeString": "",
        "Tag": "",
        "ProductionReady": False,
        "UnitCost": unit_cost,
        "UnitTimePrimaryCost": 0,
        "OperationCostList": [],
    }


def _linear(desc: str) -> dict[str, Any]:
    return {
        "ID": f"lin-{desc.split()[0]}",
        "Description": desc,
        "ProductType": 10,
        "Category": "Linear",
        "IsLinear": True,
        "UnitCost": 12.0,
        "productConfigID": "fd2cc452-0000-0000-0000-000000000020",
        "productID": "aaaaaaaa-0000-0000-0000-000000000001",
        "OperationCostList": [
            {"OperationName": "Saw", "CalculatorName": "Saw"},
            {"OperationName": "Saw", "CalculatorName": "Saw Setup"},
        ],
    }


def live_1001898_5_quote() -> dict[str, Any]:
    """GET shape after reconstructed FileList + OnAddPDFClick (Cad no PR)."""
    return {
        "ID": SPENT_QUOTE_ID,
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "Description": HEADER_TITLE_CANONICAL,
        "OrganizationName": "Time Waco",
        "ItemCount": 8,
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": f"{SPENT_QUOTE_NUMBER} - {HEADER_TITLE_CANONICAL}",
                "ProductType": 300,
                "IsAssembly": True,
                "Quantity": 1,
                "UnitCost": 0,
                "OperationCostList": [],
            },
            _cad("14501-1 PEDESTAL TOP PLATE", 0.52),
            _cad("14500-1 PEDESTAL TUBE", 3.95),
            _cad("14499-1 PEDESTAL BASE", 90.26),
            _linear("29860-1 L2X2X3/8-A36 20ft"),
            _linear("29860-2 L2X2X3/8-A36 20ft"),
            {
                "ID": "comp-1",
                "Description": "PURCHASED HARDWARE",
                "ProductType": 200,
                "Category": "Component",
                "UnitCost": 1.0,
                "OperationCostList": [],
            },
            {
                "ID": "comp-2",
                "Description": "PURCHASED FASTENER",
                "ProductType": 200,
                "Category": "Component",
                "UnitCost": 1.0,
                "OperationCostList": [],
            },
        ],
    }
