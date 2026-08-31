"""Spent 1002323-1 WINCH ROLLER BRACKETS — perimeter XHR is not gold pack.

Minted b2e12461-442b-436e-9445-772e992644f6 Time Waco on PR 18
c66dbba / 781d816. Image Files #files +Add Files, files_kendo=true.
Typed #length=19.82 #width=2.5 then UpdatePerimeterWeight(true,true)
(bare UpdatePerimeterWeight() does not copy — n/t falsy).
Page XHR POST /Quote/GetPerimeterAndWeight 200: OutsidePerimeter=44.64,
CuttingLengthDisp='44.64 in', Weight=7.7607 (not invented).
OnAddPDFClick FileList=GetPDFData() n=1, filelist_from_kendo=true.

Cad FAIL: GET 1 Cad PT 100 qty 2 Machine Laser Bay 1. Tag empty,
ProductionReady false, OperationCostList [], PrimaryTime 0.
UnitCost 3.18 = UnitPrice = UnitWeightCost (material only).
DataPartPDF OutsidePerimeter 44.64, CuttingLength 0, InternalData '',
HasSelectedProductID false. GetPDFData omits CuttingLength.
Page field for List CuttingLength is #CuttingLength (numeric), not
InternalData holes and not display-only CuttingLengthDisp.

DoD: Tag empty / OCL [] / CuttingLength 0 = FAIL. Leave b2e12461.
Do not PATCH. Do not remint. No graft. No Operation→Profile. No nest.
Capture named /workspace/live-1002323-1-get.json — fixture here.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "b2e12461-442b-436e-9445-772e992644f6"
SPENT_QUOTE_NUMBER = "1002323-1"
HEADER_TITLE = "WINCH ROLLER BRACKETS"
ORG = "Time Waco"

FILES_KENDO = True
FILELIST_FROM_KENDO = True
GETPDFDATA_N = 1
CAD_N = 1
OUTSIDE_PERIMETER = 44.64
CUTTING_LENGTH = 0
UNIT_COST = 3.18
UNIT_PRICE = 3.18
UNIT_WEIGHT_COST = 3.18
LENGTH_IN = 19.82
WIDTH_IN = 2.5
QTY = 2


def _datapart_pdf() -> dict[str, Any]:
    return {
        "CuttingLength": CUTTING_LENGTH,
        "Perimeter": 0,
        "OutsidePerimeter": OUTSIDE_PERIMETER,
        "NumberOfContours": 0,
        "NumberOfPierces": 0,
        "InternalData": "",
        "Stock_X": 0,
        "Stock_Y": 0,
        "ExternalLength": LENGTH_IN,
        "ExternalWidth": WIDTH_IN,
        "PartType": 4,
        "Time": 0,
        "HasSelectedProductID": False,
        "Machine": "Laser - Bay1",
        "ProductID": "PL3/8-A572",
    }


def _cad() -> dict[str, Any]:
    return {
        "ID": "cad-1002323-1",
        "Description": f"{SPENT_QUOTE_NUMBER} {HEADER_TITLE}",
        "ProductType": 100,
        "Category": "Cad",
        "Quantity": QTY,
        "BadgeString": "",
        "Tag": "",
        "ProductionReady": False,
        "UnitCost": UNIT_COST,
        "UnitPrice": UNIT_PRICE,
        "UnitWeightCost": UNIT_WEIGHT_COST,
        "UnitTimePrimaryCost": 0,
        "OperationCostList": [],
        "OperationParamList": [],
        "DataPartPDF": _datapart_pdf(),
        "Machine": "Laser - Bay1",
        "Material": "A572",
        "Thickness": 0.375,
        "ProductID": "PL3/8-A572",
    }


def live_1002323_1_quote() -> dict[str, Any]:
    """GET after perimeter XHR + OnAddPDFClick (Cad no PR / CuttingLength 0)."""
    return {
        "ID": SPENT_QUOTE_ID,
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "Description": HEADER_TITLE,
        "OrganizationName": ORG,
        "ItemCount": 1,
        "ItemList": [_cad()],
        "files_kendo": FILES_KENDO,
        "filelist_from_kendo": FILELIST_FROM_KENDO,
        "getpdfdata_n": GETPDFDATA_N,
        "cad_n": CAD_N,
        "outside_perimeter": OUTSIDE_PERIMETER,
        "cutting_length": CUTTING_LENGTH,
        "tag": "",
        "operation_cost_list": [],
        "unit_cost": UNIT_COST,
        "unit_price": UNIT_PRICE,
        "unit_weight_cost": UNIT_WEIGHT_COST,
        "has_selected_product_id": False,
        "update_perimeter_weight": True,
        "update_perimeter_weight_call": "UpdatePerimeterWeight(true,true)",
    }


LEFTOVER_PERIMETER_NOT_PACK = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": True,
    "pack_xhr_named": False,
    "addrow_stamps_pr": False,
    "pack_already_on_additem_list": True,
    "list_pack_keys": ("Tag", "ProductionReady", "OperationCostList"),
    "UpdatePerimeterWeight": {
        "call": "UpdatePerimeterWeight(true,true)",
        "bare_does_not_copy": True,
        "on": ("Length", "Width", "OutsidePerimeter"),
        "xhr": "POST /Quote/GetPerimeterAndWeight",
        "writes": ("#OutsidePerimeter", ".pdfcuttinglength CuttingLengthDisp"),
        "when": "change_before_AddItem",
        "is_gold_pack": False,
        "result": {
            "OutsidePerimeter": OUTSIDE_PERIMETER,
            "CuttingLengthDisp": "44.64 in",
            "Weight": 7.7607,
        },
    },
    "GetPDFData": {
        "is_xhr": False,
        "posts": (
            "OutsidePerimeter",
            "OutsidePerimeter_UseLocal",
            "Length",
            "Width",
            "Machine",
            "Material",
            "Thickness",
            "InternalData",
        ),
        "omits": (
            "Status",
            "CadType",
            "CuttingLength",
            "CuttingLengthDisp",
            "ProductionReady",
            "Tag",
        ),
        "cuttinglengthdisp_display_only": True,
        "status_is_filter_only": True,
    },
    "CuttingLength": {
        "page_field": "#CuttingLength",
        "xhr": "POST /Quote/GetPerimeterAndWeight",
        "display_only": "#CuttingLengthDisp",
        "invent_getpdfdata_key": False,
        "require_internaldata_holes": False,
    },
    "AddNewPDFFeature": {
        "optional": True,
        "xhr": ("GET /Quote/PDFInternal", "PDFGetData"),
        "writes": "InternalData",
        "invent_internaldata": False,
        "no_arg_not_gold": True,
    },
    "UpdateDataNext": {
        "gold": False,
        "editor_only": True,
        "path": "/CadImport/UpdateDataNext",
    },
    "live_1002323_1": {
        "files_kendo": True,
        "filelist_from_kendo": True,
        "outside_perimeter": OUTSIDE_PERIMETER,
        "cutting_length": CUTTING_LENGTH,
        "internaldata": "",
        "tag": "",
        "operation_cost_list": [],
        "unit_cost": UNIT_COST,
        "unit_price": UNIT_PRICE,
        "has_selected_product_id": False,
    },
}


def leftover_perimeter_not_pack_dump() -> dict[str, Any]:
    """Leftover: perimeter XHR landed; GetPDFData omitted CuttingLength."""
    return dict(LEFTOVER_PERIMETER_NOT_PACK)
