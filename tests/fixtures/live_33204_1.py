"""Spent 33204-1 TOP PLATE — list0_pack already has no pack.

Minted e57633b6-7bfc-4235-80de-a0e3be6cc5cc Time Waco on PR 18
eef2acf. Image Files #files +Add Files. Stamped drawing A572 /
0.5 / Laser Bay 1. UpdatePerimeterWeight(true,true) bag Weight
1.4378, OutsidePerimeter 18.25, L=9.125, W=7.5625.
OnAddPDFClick FileList=GetPDFData() n=1.

list0_pack: list_n=1, Tag "", ProductionReady false, OCL 0,
UnitCost 5.05. filelist_bag ProductID null. product_picker=
none_plate_widget. ThicknessPDF is gauge
(Read_DataThicknessGauge2). #Product is ProductType bar.
gridSelectProductPlate is a modal, not a kendo combo — SKU
PL1/2-A572 did not drive it. No invented GUID.

GET FAIL: 1 Cad PT 100 qty 1. ProductID bound 7c3e5cad-…
PL1/2-A572. Tag empty, OCL [], ProductionReady false,
UnitCost=UnitWeightCost 5.05 (material). Pack miss is not
ProductID. Server stamped a Cad line + material cost and did
not put Tag/OCL on n.List[0]. Later GET matches that List.
No later XHR will add the pack.

DoD: list0_pack Tag empty / OCL 0 / UnitCost 5.05 = FAIL even
with full L×W/Weight/OP/Machine/Material. Leave e57633b6.
Do not PATCH. Do not remint. No graft. No Operation→Profile. No nest.
Do not add CuttingLength to GetPDFData.
Capture named /workspace/live-33204-1-run.json — fixture here.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "e57633b6-7bfc-4235-80de-a0e3be6cc5cc"
SPENT_QUOTE_NUMBER = "33204-1"
HEADER_TITLE = "TOP PLATE"
ORG = "Time Waco"

FILES_KENDO = True
FILELIST_FROM_KENDO = True
GETPDFDATA_N = 1
CAD_N = 1
OUTSIDE_PERIMETER = 18.25
CUTTING_LENGTH = 0
WEIGHT = 1.4378
UNIT_COST = 5.05
UNIT_PRICE = 5.05
UNIT_WEIGHT_COST = 5.05
LENGTH_IN = 9.125
WIDTH_IN = 7.5625
THICKNESS = 0.5
QTY = 1
SKU = "PL1/2-A572"
# Observed GET prefix only — full GUID was not logged. Not a stamp value.
GET_PRODUCT_ID = "7c3e5cad-0000-4000-8000-000000000001"

FILELIST_BAG: dict[str, Any] = {
    "Machine": "Laser - Bay1",
    "ProductID": None,
    "Qty": QTY,
    "Weight": WEIGHT,
    "Weight_UseLocal": True,
    "OutsidePerimeter": OUTSIDE_PERIMETER,
    "OutsidePerimeter_UseLocal": True,
    "Material": "A572",
    "Thickness": "0.5",
    "Length": LENGTH_IN,
    "Width": WIDTH_IN,
}

LIST0_PACK: dict[str, Any] = {
    "list_n": 1,
    "tag": "",
    "production_ready": False,
    "ocl_n": 0,
    "unit_cost": UNIT_COST,
}

GETPDFDATA_CANDIDATES_TO_VERIFY = (
    "ProductionReady checkbox",
    "ItemType",
    "ProductType/prt_pdf",
    "FileID/ImageID from upload",
    "InternalData rectangle vs empty",
    "Machine string vs Laser - Bay 1",
)


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
        "ID": "cad-33204-1",
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


def live_33204_1_quote() -> dict[str, Any]:
    """GET after list0_pack empty Tag/OCL (Cad ProductID set / no PR)."""
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
        "list0_pack": dict(LIST0_PACK),
        "update_perimeter_weight": True,
        "update_perimeter_weight_call": "UpdatePerimeterWeight(true,true)",
    }


LEFTOVER_LIST0_PACK_NOT_GOLD = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": True,
    "filelist_keys_logged": True,
    "pack_xhr_named": False,
    "addrow_stamps_pr": False,
    "pack_already_on_additem_list": True,
    "pack_is_productid": False,
    "list_pack_keys": ("Tag", "ProductionReady", "OperationCostList"),
    "list0_pack": dict(LIST0_PACK),
    "filelist_bag": dict(FILELIST_BAG),
    "invent_cuttinglength": False,
    "getpdfdata_candidates_to_verify": GETPDFDATA_CANDIDATES_TO_VERIFY,
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
            "CuttingLengthDisp": "18.25 in",
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
    "live_33204_1": {
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
        "list0_pack_is_gold": False,
        "product_picker": "none_plate_widget",
        "thicknesspdf": "Read_DataThicknessGauge2",
        "plate_picker": "#gridSelectProductPlate",
        "has_selected_product_id": True,
    },
}


def leftover_list0_pack_not_gold_dump() -> dict[str, Any]:
    """Leftover: list0_pack Tag empty / OCL 0 / UnitCost 5.05; full bag."""
    return dict(LEFTOVER_LIST0_PACK_NOT_GOLD)
