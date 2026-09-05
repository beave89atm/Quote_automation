"""Spent 1009213-1 PEDESTAL BASE PLATE — plate modal is not the pack.

Minted 3102870a Time Waco on PR 18 a48164d. Image Files #files
+Add Files. Stamped drawing A572 / 1.25 / Laser Bay 1. L=W=28.5,
UpdatePerimeterWeight(true,true) bag Weight 308.9387,
OutsidePerimeter 114. Empty InternalData did not skip.
OnAddPDFClick FileList=GetPDFData() n=1. GetPDFData omits
CuttingLength.

Modal driven: Sheets & Plates, SKU text PL1 1/4-A572.
ThicknessPDF=gauge, #Product=ProductType bar. FileList ProductID
stayed null (modal did not land List Value on GetPDFData —
search-only, not apply/select).

list0_pack: list_n=1, Tag "", ProductionReady false, OCL 0,
UnitCost 126.66. GET ProductID 3b2055ae-… set. Tag empty, OCL [],
UnitCost=UnitWeightCost 126.66. cad_pr false.

Same server List miss as 33204-1 / 1007092-1 / 33819-1 / 1002323-1.
Picker (bar, keepPid, modal) does not put Tag/OCL on n.List[0].

DoD: modal SKU + FileList ProductID null + list0_pack Tag empty /
OCL 0 = FAIL. Modal is not gold. Leave 3102870a.
Do not PATCH. Do not remint. No graft. No Operation→Profile. No nest.
Do not add CuttingLength to GetPDFData.
Capture named /workspace/live-1009213-1-run.json — fixture here.
"""

from __future__ import annotations

from typing import Any

# Full GUID was not restated — prefix only. Not a stamp value.
SPENT_QUOTE_ID = "3102870a-0000-4000-8000-000000000001"
SPENT_QUOTE_NUMBER = "1009213-1"
HEADER_TITLE = "PEDESTAL BASE PLATE"
ORG = "Time Waco"

FILES_KENDO = True
FILELIST_FROM_KENDO = True
GETPDFDATA_N = 1
CAD_N = 1
OUTSIDE_PERIMETER = 114
CUTTING_LENGTH = 0
WEIGHT = 308.9387
UNIT_COST = 126.66
UNIT_PRICE = 126.66
UNIT_WEIGHT_COST = 126.66
LENGTH_IN = 28.5
WIDTH_IN = 28.5
THICKNESS = 1.25
QTY = 1
SKU = "PL1 1/4-A572"
GET_PRODUCT_ID = "3b2055ae-0000-4000-8000-000000000001"

FILELIST_BAG: dict[str, Any] = {
    "Machine": "Laser - Bay1",
    "ProductID": None,
    "Qty": QTY,
    "Weight": WEIGHT,
    "Weight_UseLocal": True,
    "OutsidePerimeter": OUTSIDE_PERIMETER,
    "OutsidePerimeter_UseLocal": True,
    "Material": "A572",
    "Thickness": "1.25",
    "Length": LENGTH_IN,
    "Width": WIDTH_IN,
}

LIST0_PACK: dict[str, Any] = {
    "list_n": 1,
    "tag": "",
    "badge_string": "",
    "production_ready": False,
    "ocl_n": 0,
    "unit_cost": UNIT_COST,
}

GETPDFDATA_VALUES_NAMED = (
    "ProductionReady checkbox",
    "ItemType",
    "ProductType/prt_pdf",
    "FileID/ImageID present",
    "InternalData empty vs rectangle",
    "Machine string exact",
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
        "ID": "cad-1009213-1",
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


def live_1009213_1_quote() -> dict[str, Any]:
    """GET after modal SKU + list0_pack empty Tag/OCL (Cad ProductID set / no PR)."""
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
        "product_picker": "#gridSelectProductPlate",
        "picker_apply": "search_only",
        "list0_pack": dict(LIST0_PACK),
        "update_perimeter_weight": True,
        "update_perimeter_weight_call": "UpdatePerimeterWeight(true,true)",
    }


LEFTOVER_PLATE_MODAL_NOT_PACK = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": True,
    "modal_driven": True,
    "filelist_keys_logged": True,
    "pack_xhr_named": False,
    "addrow_stamps_pr": False,
    "pack_already_on_additem_list": True,
    "pack_is_productid": False,
    "list_pack_keys": ("Tag", "ProductionReady", "OperationCostList"),
    "list0_pack": dict(LIST0_PACK),
    "filelist_bag": dict(FILELIST_BAG),
    "invent_cuttinglength": False,
    "getpdfdata_values_named": GETPDFDATA_VALUES_NAMED,
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
            "CuttingLengthDisp": "114 in",
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
    "live_1009213_1": {
        "files_kendo": True,
        "filelist_from_kendo": True,
        "outside_perimeter": OUTSIDE_PERIMETER,
        "cutting_length": CUTTING_LENGTH,
        "weight": WEIGHT,
        "internaldata": "",
        "tag": "",
        "badge_string": "",
        "operation_cost_list": [],
        "unit_cost": UNIT_COST,
        "unit_price": UNIT_PRICE,
        "productid": None,
        "get_productid": GET_PRODUCT_ID,
        "sku": SKU,
        "production_ready": False,
        "pack_is_productid": False,
        "list0_pack_is_gold": False,
        "modal_is_gold": False,
        "tag_is_not_the_pack": True,
        "thickness": THICKNESS,
        "should_be": "Component",
        "was": "Cad",
        "addnewpdffeature": False,
        "invent_internaldata": False,
        "cookie_addfeature": False,
        "number_of_contours": 0,
        "number_of_pierces": 0,
        "gold_number_of_contours": 1,
        "gold_number_of_pierces": 1,
        "product_picker": "#gridSelectProductPlate",
        "picker_apply": "search_only",
        "thicknesspdf": "Read_DataThicknessGauge2",
        "plate_picker": "#gridSelectProductPlate",
        "has_selected_product_id": True,
    },
}


def leftover_plate_modal_not_pack_dump() -> dict[str, Any]:
    """Leftover: modal SKU + FileList ProductID null + list0_pack empty."""
    return dict(LEFTOVER_PLATE_MODAL_NOT_PACK)
