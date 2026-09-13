"""Spent 1007092-1 FRAME SPACER — GET ProductID is not the laser pack.

Minted 8930f65a-c1e3-44b0-8024-9075b2a5ab80 Time Waco on PR 18
f83719d. Image Files #files +Add Files. Did not skip empty bind
ProductID. Stamped drawing A572 / 0.3125 / Laser Bay 1 over
316 Polished. UpdatePerimeterWeight(true,true) bag Weight 0.2718,
OutsidePerimeter 5. OnAddPDFClick FileList=GetPDFData() n=1.

Posted filelist_bag: Machine='Laser - Bay1', Material='A572',
Thickness='0.3125', Weight=0.2718, OutsidePerimeter=5,
ProductID=null. product_picker=none_plate_widget (first #Product
is ProductType bar, not the plate Product kendo).

GET FAIL: 1 Cad PT 100 qty 1. ProductID bound bc2748d9-… SKU
PL5/16-A572. Tag empty, OCL [], ProductionReady false,
UnitCost=UnitWeightCost 0.11 (material). ProductID is not the
laser pack. Same miss as 33819-1 / 1002323-1.

DoD: FileList ProductID null + GET ProductID set + Tag empty /
OCL [] = FAIL. Pack miss is not ProductID. Leave 8930f65a.
Do not PATCH. Do not remint. No graft. No Operation→Profile. No nest.
Do not add CuttingLength to GetPDFData.
Capture named /workspace/live-1007092-1-run.json — fixture here.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "8930f65a-c1e3-44b0-8024-9075b2a5ab80"
SPENT_QUOTE_NUMBER = "1007092-1"
HEADER_TITLE = "FRAME SPACER"
ORG = "Time Waco"

FILES_KENDO = True
FILELIST_FROM_KENDO = True
GETPDFDATA_N = 1
CAD_N = 1
OUTSIDE_PERIMETER = 5
CUTTING_LENGTH = 0
WEIGHT = 0.2718
UNIT_COST = 0.11
UNIT_PRICE = 0.11
UNIT_WEIGHT_COST = 0.11
LENGTH_IN = 2
WIDTH_IN = 0.5
THICKNESS = 0.3125
QTY = 1
SKU = "PL5/16-A572"
# Observed GET prefix only — full GUID was not logged. Not a stamp value.
GET_PRODUCT_ID = "bc2748d9-0000-4000-8000-000000000001"

FILELIST_BAG: dict[str, Any] = {
    "Machine": "Laser - Bay1",
    "ProductID": None,
    "Qty": QTY,
    "Weight": WEIGHT,
    "Weight_UseLocal": True,
    "OutsidePerimeter": OUTSIDE_PERIMETER,
    "OutsidePerimeter_UseLocal": True,
    "Material": "A572",
    "Thickness": "0.3125",
    "Length": LENGTH_IN,
    "Width": WIDTH_IN,
}


def _datapart_pdf() -> dict[str, Any]:
    return {
        "CuttingLength": CUTTING_LENGTH,
        "Perimeter": OUTSIDE_PERIMETER,
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
        "HasSelectedProductID": True,
        "Machine": "Laser - Bay1",
        "ProductID": GET_PRODUCT_ID,
        "Weight": WEIGHT,
    }


def _cad() -> dict[str, Any]:
    return {
        "ID": "cad-1007092-1",
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
        "FileList": [dict(FILELIST_BAG)],
        "Machine": "Laser - Bay1",
        "Material": "A572",
        "Thickness": THICKNESS,
        "ProductID": GET_PRODUCT_ID,
        "Weight": WEIGHT,
    }


def live_1007092_1_quote() -> dict[str, Any]:
    """GET after Weight bag + OnAddPDFClick (Cad ProductID set / no PR)."""
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
        "weight": WEIGHT,
        "tag": "",
        "operation_cost_list": [],
        "unit_cost": UNIT_COST,
        "unit_price": UNIT_PRICE,
        "unit_weight_cost": UNIT_WEIGHT_COST,
        "has_selected_product_id": True,
        "productid": GET_PRODUCT_ID,
        "sku": SKU,
        "product_picker": "none_plate_widget",
        "update_perimeter_weight": True,
        "update_perimeter_weight_call": "UpdatePerimeterWeight(true,true)",
    }


LEFTOVER_PRODUCTID_NOT_PACK = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": True,
    "filelist_keys_logged": True,
    "pack_xhr_named": False,
    "addrow_stamps_pr": False,
    "pack_is_productid": False,
    "filelist_bag": dict(FILELIST_BAG),
    "UpdatePerimeterWeight": {
        "call": "UpdatePerimeterWeight(true,true)",
        "bare_does_not_copy": True,
        "on": ("Length", "Width", "OutsidePerimeter", "Weight"),
        "xhr": "POST /Quote/GetPerimeterAndWeight",
        "writes": ("#OutsidePerimeter", "#Weight", ".pdfcuttinglength CuttingLengthDisp"),
        "when": "change_before_AddItem",
        "is_gold_pack": False,
        "result": {
            "OutsidePerimeter": OUTSIDE_PERIMETER,
            "CuttingLengthDisp": "5 in",
            "Weight": WEIGHT,
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
            "Weight",
            "Weight_UseLocal",
            "ProductID",
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
    "Weight": {
        "bag_field": "Weight",
        "also": "Weight_UseLocal",
        "xhr": "POST /Quote/GetPerimeterAndWeight",
        "page_field": "#Weight",
        "invent_getpdfdata_key": False,
        "posted_weight": WEIGHT,
        "is_gold_pack": False,
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
    "live_1007092_1": {
        "files_kendo": True,
        "filelist_from_kendo": True,
        "outside_perimeter": OUTSIDE_PERIMETER,
        "cutting_length": CUTTING_LENGTH,
        "weight": WEIGHT,
        "internaldata": "",
        "tag": "",
        "operation_cost_list": [],
        "unit_cost": UNIT_COST,
        "unit_price": UNIT_PRICE,
        "productid": None,
        "get_productid": GET_PRODUCT_ID,
        "sku": SKU,
        "production_ready": False,
        "pack_is_productid": False,
        "product_picker": "none_plate_widget",
        "has_selected_product_id": True,
    },
}


def leftover_productid_not_pack_dump() -> dict[str, Any]:
    """Leftover: FileList ProductID null; GET ProductID set; Tag empty / OCL []."""
    return dict(LEFTOVER_PRODUCTID_NOT_PACK)
