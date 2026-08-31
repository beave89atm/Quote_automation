"""Spent 29743-1 SUBFRAME WELDMENT — #files bind is not gold PR/laser.

Minted d2f7b031-a5a8-4020-a6a3-dba8de964ebf Time Waco on PR 18 b7e9dff.
In-page #files kendoUpload + GetPDFData n=2 + OnAddPDFClick
filelist_from_kendo=true. GET 4: 2 Cad + 2 Linear.

Linear Saw + Saw-Setup + unitcost 4.0 PASS.
Cad FAIL: Tag empty, OperationCostList [], UnitCost 0, CuttingLength 0.
UnitPrice 28.82 / 44.49 is material weight, not gold UnitCost.

Leave d2f7b031. Do not PATCH. Do not remint. No STEP.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "d2f7b031-a5a8-4020-a6a3-dba8de964ebf"
SPENT_QUOTE_NUMBER = "29743-1"
HEADER_TITLE = "SUBFRAME WELDMENT"
ORG = "Time Waco"

FILES_KENDO = True
FILELIST_FROM_KENDO = True
GETPDFDATA_N = 2
CAD_N = 2
LINEAR_N = 2


def _datapart_pdf(*, unit_price: float) -> dict[str, Any]:
    return {
        "CuttingLength": 0,
        "Perimeter": 0,
        "NumberOfContours": 0,
        "NumberOfPierces": 0,
        "InternalData": "",
        "Stock_X": 0,
        "Stock_Y": 0,
        "Machine": "Laser - Bay1",
        "ProductID": "PL7 Ga-A572",
    }


def _cad(desc: str, unit_price: float) -> dict[str, Any]:
    return {
        "ID": f"cad-{desc.split()[0]}",
        "Description": desc,
        "ProductType": 100,
        "Category": "Cad",
        "BadgeString": "",
        "Tag": "",
        "ProductionReady": False,
        "UnitCost": 0.0,
        "UnitPrice": unit_price,
        "UnitTimePrimaryCost": 0,
        "OperationCostList": [],
        "OperationParamList": [],
        "DataPartPDF": _datapart_pdf(unit_price=unit_price),
        "Machine": "Laser - Bay1",
        "Material": "A572",
        "Thickness": 0.1875,
        "ProductID": "PL7 Ga-A572",
    }


def _linear(desc: str) -> dict[str, Any]:
    return {
        "ID": f"lin-{desc.split()[0]}",
        "Description": desc,
        "ProductType": 10,
        "Category": "Linear",
        "IsLinear": True,
        "UnitCost": 4.0,
        "productConfigID": "fd2cc452-0000-0000-0000-000000000020",
        "productID": "aaaaaaaa-0000-0000-0000-000000000001",
        "OperationCostList": [
            {"OperationName": "Saw", "CalculatorName": "Saw"},
            {"OperationName": "Saw", "CalculatorName": "Saw-Setup"},
        ],
    }


def live_29743_1_quote() -> dict[str, Any]:
    """GET after #files bind + GetPDFData + OnAddPDFClick (Cad no PR)."""
    return {
        "ID": SPENT_QUOTE_ID,
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "Description": HEADER_TITLE,
        "OrganizationName": ORG,
        "ItemCount": 4,
        "ItemList": [
            _cad("29743-1 PLATE A", 28.82),
            _cad("29743-1 PLATE B", 44.49),
            _linear("29743-1 TUBE 20ft"),
            _linear("29743-1 ANGLE 21ft"),
        ],
        "files_kendo": FILES_KENDO,
        "filelist_from_kendo": FILELIST_FROM_KENDO,
        "getpdfdata_n": GETPDFDATA_N,
        "cad_n": CAD_N,
        "linear_n": LINEAR_N,
        "getpdfdata_omitted_status": True,
    }
