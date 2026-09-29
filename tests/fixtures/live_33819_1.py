"""Spent 33819-1 COMP LINK LUG — bag Weight is not the pack.

Minted 47c393f8-db59-4b9a-a243-48d572011f77 Time Waco on PR 18
95b9c02. Image Files #files +Add Files. Posted GetPDFData bag:

  Machine='Laser - Bay1', ProductID=None, Qty=1, Weight=15.0875,
  Weight_UseLocal=True, OutsidePerimeter=40,
  OutsidePerimeter_UseLocal=True, NumberOfHeads=1, WeightBorder='0.5',
  Material='A572', Thickness='0.625', Length=16, Width=4

CuttingLength omitted (correct). Status not overlaid. Empty
InternalData did not skip Finish. filelist_row_keys logged.

GET FAIL: 1 Cad PT 100 qty 1, Tag empty, OCL [], ProductionReady
false, UnitCost=UnitPrice=UnitWeightCost 6.19 (material). Perimeter
40. No PR, no laser pack. Weight persist PASS. ProductID None —
onSuccess_PDFUpload copies ProductID from upload List; L×W / Weight
stamp must keep that value. Do not invent a GUID or plate SKU.
Kyle Image Files still picks plate stock when the Product box is
empty — that picker is a page control, not a reconstructed SKU.

DoD: FileList Weight 15.0875 + OutsidePerimeter 40 + ProductID null
+ GET Tag empty / OCL [] = FAIL. Leave 47c393f8.
Do not PATCH. Do not remint. No graft. No Operation→Profile. No nest.
Do not add CuttingLength to the bag.
Capture named /workspace/live-33819-1-run.json +
/workspace/live-33819-1-get.json — fixture here.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "47c393f8-db59-4b9a-a243-48d572011f77"
SPENT_QUOTE_NUMBER = "33819-1"
HEADER_TITLE = "COMP LINK LUG"
ORG = "Time Waco"

FILES_KENDO = True
FILELIST_FROM_KENDO = True
GETPDFDATA_N = 1
CAD_N = 1
OUTSIDE_PERIMETER = 40
CUTTING_LENGTH = 0
WEIGHT = 15.0875
UNIT_COST = 6.19
UNIT_PRICE = 6.19
UNIT_WEIGHT_COST = 6.19
LENGTH_IN = 16
WIDTH_IN = 4
QTY = 1

FILELIST_BAG: dict[str, Any] = {
    "Machine": "Laser - Bay1",
    "ProductID": None,
    "Qty": QTY,
    "Weight": WEIGHT,
    "Weight_UseLocal": True,
    "OutsidePerimeter": OUTSIDE_PERIMETER,
    "OutsidePerimeter_UseLocal": True,
    "NumberOfHeads": 1,
    "WeightBorder": "0.5",
    "Material": "A572",
    "Thickness": "0.625",
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
        "HasSelectedProductID": False,
        "Machine": "Laser - Bay1",
        "ProductID": None,
        "Weight": WEIGHT,
    }


def _cad() -> dict[str, Any]:
    return {
        "ID": "cad-33819-1",
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
        "Thickness": 0.625,
        "ProductID": None,
        "Weight": WEIGHT,
    }


def live_33819_1_quote() -> dict[str, Any]:
    """GET after Weight bag + OnAddPDFClick (Cad no PR / ProductID None)."""
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
        "has_selected_product_id": False,
        "productid": None,
        "update_perimeter_weight": True,
        "update_perimeter_weight_call": "UpdatePerimeterWeight(true,true)",
    }


LEFTOVER_WEIGHT_WITHOUT_PRODUCTID = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": True,
    "filelist_keys_logged": True,
    "pack_xhr_named": False,
    "addrow_stamps_pr": False,
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
            "CuttingLengthDisp": "40 in",
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
    "live_33819_1": {
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
        "has_selected_product_id": False,
    },
}


def leftover_weight_without_productid_dump() -> dict[str, Any]:
    """Leftover: bag Weight+OP posted; ProductID None; Tag empty / OCL []."""
    return dict(LEFTOVER_WEIGHT_WITHOUT_PRODUCTID)
